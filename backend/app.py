from datetime import datetime, timedelta
import tempfile
import subprocess
import logging

import numpy as np
import librosa    
import soundfile as sf
import tensorflow as tf
import torch
import whisper

from flask import Flask
from flask_socketio import SocketIO, send, emit

from utils.extract_features import extract_features
from utils.vad import is_speaking
from utils.strip_wav_header import strip_wav_header

print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))


transcription_model = whisper.load_model("tiny.en")
# whisper_options = whisper.DecodingOptions().__dict__.copy()
# whisper_options['no_speech_threshold'] = 0.275
# whisper_options['logprob_threshold'] = None

speaker_model = tf.keras.models.load_model("../saved_models/4_classes_best_aiden", compile=False)
speaker_model.compile()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", logger = False)
logging.getLogger("werkzeug").setLevel(logging.ERROR) # flask
logging.getLogger("socketio").setLevel(logging.ERROR) # socketio
logging.getLogger("engineio").setLevel(logging.ERROR)

FILE_NAME = "audio"
audio_bytes = b""
is_first = True

speakers = ["adam", "aiden", "hannah", "parker"]
total_transcript = []

# running phrase vars
phrase_audio_buffer = b""
phrase_timeout = 2 # seconds of silence required for a new phrase to start in live transcription
last_phrase_time = None
phrase_id = 0

"""
Write a blob of wav data as a temporary file where we can then load that 
file and predict who is speaking in it using librosa and our trained 
model.
"""
def save_chunk_to_tempfile(blob):
    # create and save temp file
    fp = tempfile.NamedTemporaryFile()
    # print("\nTEMP FILE NAME" + fp.name)
    fp.write(blob) 
    fp.seek(0)

    return fp

def save_wav_16(bytes: bytes, file_name):
    # write audio bytes to wav file
    with open(file_name + ".wav", "wb") as file:
      file.write(bytes)

    y, sr = librosa.load(file_name + ".wav", sr=16000) # Downsample 44.1kHz to 16kHz for whisper to be able to read it
    sf.write(file_name + "_16.wav", y, sr, "PCM_16")   # save the 16KHz file as 16 bit (also for whisper)


def transcribe(file_name):
    result = transcription_model.transcribe(file_name, fp16=torch.cuda.is_available())
    text = result['text'].strip()
    # print(str(result))
    return text

def transcribe_cpp(file_name, is_final=False):
    # whisper transcribe
    subprocess.run(["./main", "-f", "../backend/" + file_name + "_16.wav", 
                    "--model", "models/ggml-large.bin", 
                    "--output-txt"], 
                    cwd="../whisper.cpp")
    
    with open(file_name + "_16.wav.txt", "r") as f:
        contents = f.readlines()

        if is_final:
            emit("finished_transcription", contents)
        else: 
            emit("transcription_chunk", contents)

"""
Identifies who is speaking in a given audio file and returns the result. 
"""
def identify_speaker(file_name, average=False):
    duration = 1000 # ms - duration of the split audio clip in ms

    if average:
        sr = librosa.get_samplerate(file_name)
        print("SAMPLE RATE: ", str(sr))
        stream = librosa.stream(file_name,
                            block_length=64, 
                            frame_length=int(sr * duration / 1000),
                            hop_length=int(sr * duration / 1000) * 0.5)
        
        predictions = []
        # create 40ms clips of audio features to feed into the model and get the output
        for y in stream:
            y = (y - min(y)) / (np.max(y) - np.min(y)) # normalize audio before extracting features
            test_frame_features = extract_features(y, sr)
            pred = speaker_model.predict(test_frame_features.reshape(1,len(test_frame_features)))
            idx = np.argmax(pred)
            predictions.append(speakers[idx])

        print("PREDICTIONS: " + str(predictions))

    else:
        y, sr = librosa.load(file_name, offset=0)
        print("SAMPLE RATE: ", str(sr))
        test_frame_features = extract_features(y, sr)
        pred = speaker_model.predict(test_frame_features.reshape(1,len(test_frame_features)))
        idx = np.argmax(pred)

        current_speaker = speakers[idx]
        # print("SPEAKER: " + current_speaker)
        return current_speaker


def final_identify_speakers(file_name):
    # model prediction
    test_file_path = file_name + "_16.wav"
    sr = librosa.get_samplerate(test_file_path)
    stream = librosa.stream(test_file_path,
                            block_length=1,
                            frame_length=int(sr*0.04),
                            hop_length=int(sr*0.04))
    
    for y in stream:
        test_frame_features = extract_features(y, sr)
        pred = speaker_model.predict(test_frame_features.reshape(1,len(test_frame_features)))
        idx = np.argmax(pred)
        print(speakers[idx])


@socketio.on("connect")
def handle_message(data):
    print("===============| Browser Client Connected! |===============\n")
    # identify_speaker("1sec.wav", average=True)

@socketio.on("begin_transcription")
def handle_message(data):
    global is_first, audio_bytes, total_transcript, last_phrase_time, phrase_id

    audio_bytes = b"" # clear the saved audio from the previous transcription
    is_first = True
    total_transcript = []
    last_phrase_time = None
    phrase_id = 0

    print("===============| begin_transcription |===============\n" + str(data))
    emit("ready_to_receive_chunks")

@socketio.on("audio_chunk")
def handle_message(data):
    global is_first, audio_bytes, silence_time, last_phrase_time, phrase_audio_buffer, phrase_id
    
    # update the variables for the total running audio after each audio_chunk is received
    audio_bytes += data if is_first else strip_wav_header(data) # if its not the first chunk, get rid of WAV header (first 44 bytes)
    is_first = False

    # handle each audio chunk for live transcription
    # print("\nreceived audio chunk:\n", data)
    file_pointer = save_chunk_to_tempfile(data)
    temp_file_path = file_pointer.name


    # initialize new_phrase as False if we've spoken before, otherwise start it as true for the first run 
    new_phrase = False if last_phrase_time else True
    now = datetime.utcnow()

    # if its been more than 2 seconds since the last time a voice was detected AND 
    # this isn't the very first run through (last_phrase_time would be None), then:
    # 
    # the phrase is complete and we can clear the current phrase buffers
    if last_phrase_time and now - last_phrase_time > timedelta(seconds=phrase_timeout):
        phrase_audio_buffer = b""
        new_phrase = True
        phrase_id += 1 # incremement phrase ID if we're onto a new one
        print("Silence for at least 2 seconds... new phrase ")

    # Voice Activity Detection - check if someone was speaking in this audio clip
    if is_speaking(temp_file_path):
        last_phrase_time = now

        # make a prediction on who is speaking in the chunk and emit it back to the client
        current_speaker = identify_speaker(temp_file_path)
        # emit("current_speaker", current_speaker)

        # append this audio to the buffer since the person is speaking.
        # if the phrase is a new one, start by keeping wav header, otherwise append chunks with no wav header
        phrase_audio_buffer += data if new_phrase else strip_wav_header(data)

        # TODO better file name handling
        print("saving audio buffer, new_phrase: " + str(new_phrase))
        with open("phrase.wav", 'w+b') as f:
            f.write(phrase_audio_buffer)

        # live transcribe on the audio segment
        running_transcript = transcribe("phrase.wav")

        output = {
            "id": phrase_id,
            "text": running_transcript,
            "speaker": current_speaker
        }

        print("TRANSCRIPT: ", str(output))
        emit("transcript_update", output)
        
        # since we just got someone talking, prepare for more talking from them
        new_phrase = False
    # END IF (is_speaking)



    # finally, close the pointer to the temp file -- this should delete the tempfile too
    file_pointer.close()


@socketio.on("end_transcription")
def handle_message():
    print("\===============| end_transcription |===============\n")

    save_wav_16(audio_bytes, FILE_NAME)

    final_transcript = transcribe(FILE_NAME + ".wav")
    print("FINAL TRANSCRIPT:\n" + final_transcript)
    emit("finished_transcription", final_transcript)

    # final_identify_speakers(FILE_NAME)



if __name__ == "__main__":
    socketio.run(app)