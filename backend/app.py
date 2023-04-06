from datetime import datetime, timedelta
import tempfile
import logging
import concurrent.futures

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
from utils.SpeakerHistory import SpeakerHistoryQueue

print("Num GPUs Available to TensorFlow: ", len(tf.config.list_physical_devices('GPU')))

transcription_model = whisper.load_model("tiny.en")
# whisper_options = whisper.DecodingOptions().__dict__.copy()
# whisper_options['no_speech_threshold'] = 0.275
# whisper_options['logprob_threshold'] = None

speaker_model = tf.keras.models.load_model("../saved_models/4_classes-04_05_2023_22_58_25", compile=False)
speaker_model.compile()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", logger = False)
logging.getLogger("werkzeug").setLevel(logging.ERROR) # flask
logging.getLogger("socketio").setLevel(logging.ERROR) # socketio
logging.getLogger("engineio").setLevel(logging.ERROR)

FILE_NAME = "audio"
audio_bytes = b""
is_first = True

torch_use_gpu = torch.cuda.is_available()
speakers = ['hannah', 'aiden', 'parker', 'adam']
total_transcript = []


# running phrase vars
last_output = None
phrase_audio_buffer = b""
phrase_timeout = 2 # seconds of silence required for a new phrase to start in live transcription
last_phrase_time = None
phrase_id = 0
phrase_class_counts = {speaker: 0 for speaker in speakers} # creates a dictionary where the keys are the speaker names 
                                                           # and the values are a counter of how many times the speaker 
                                                           # detection thought it was them in a running phrase

running_speaker_history = SpeakerHistoryQueue(speakers)


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
    result = transcription_model.transcribe(file_name, fp16=False)
    text = result['text'].strip()
    # print(str(result))
    return text

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
            normalized_y = librosa.util.normalize(y)
            test_frame_features = extract_features(normalized_y, sr)
            pred = speaker_model.predict(test_frame_features.reshape(1,len(test_frame_features)))
            idx = np.argmax(pred)
            predictions.append(speakers[idx])

        print("PREDICTIONS: " + str(predictions))

    else:
        y, sr = librosa.load(file_name, offset=0)
        # print("SAMPLE RATE: ", str(sr))
        normalized_y = librosa.util.normalize(y)

        test_frame_features = extract_features(normalized_y, sr)
        
        pred = speaker_model.predict(test_frame_features.reshape(1,len(test_frame_features)))
        idx = np.argmax(pred)

        current_speaker = speakers[idx]
        return current_speaker


@socketio.on("connect")
def handle_message(data):
    print("===============| Browser Client Connected! |===============\n")

@socketio.on("begin_transcription")
def handle_message(data):
    global is_first, audio_bytes, total_transcript, last_phrase_time, phrase_id, running_speaker_history

    audio_bytes = b"" # clear the saved audio from the previous transcription
    is_first = True
    total_transcript = []
    last_phrase_time = None
    phrase_id = 0
    running_speaker_history = SpeakerHistoryQueue(speakers) # clear the queue of speaker history

    print("===============| begin_transcription |===============\n" + str(data))
    emit("ready_to_receive_chunks")

# # ================================ RECORD DATA FOR TRAINING ================================
# num_audio_chunks_temp = 0
# @socketio.on("audio_chunk")
# def handle_message(data):
#     global num_audio_chunks_temp
    
#     file_pointer = save_chunk_to_tempfile(data)
#     temp_file_path = file_pointer.name
#     if is_speaking(temp_file_path):
#         print(f"audio. saving to training_data_browser/parker/test_shure-{num_audio_chunks_temp}.wav")
#         with open(f"training_data_browser/parker/test_shure-{num_audio_chunks_temp}.wav", "wb") as audio_file:
#             # Write bytes to file
#             audio_file.write(data)

#         num_audio_chunks_temp += 1
        
    

@socketio.on("audio_chunk")
def handle_message(data):
    global is_first, audio_bytes, silence_time, last_phrase_time, phrase_audio_buffer, phrase_id, phrase_class_counts, running_speaker_history, last_output
    
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
        phrase_class_counts = {speaker: 0 for speaker in speakers}
        running_speaker_history = SpeakerHistoryQueue(speakers) # silence, we don't care about detecting a speaker switch since we have a new phrase
        phrase_id += 1 # incremement phrase ID if we're onto a new one
        print("Silence for at least 2 seconds... new phrase ")


    # if our current best guess of a speaker for the phrase has not been the majority of the last 5 seconds,
    # its time to start a new phrase since there's a good chance someone else started talking
    best_guess_for_phrase = max(phrase_class_counts, key=phrase_class_counts.get)
    majority_of_last_few_guesses = max(running_speaker_history.counts, key=running_speaker_history.counts.get)

    if best_guess_for_phrase is not majority_of_last_few_guesses: 
        phrase_audio_buffer = b""
        new_phrase = True
        phrase_class_counts = {speaker: 0 for speaker in speakers}
        phrase_id += 1 # incremement phrase ID if we're onto a new one
        print("Someone else is speaking! New phrase ")


    # Voice Activity Detection - check if someone was speaking in this audio clip
    if is_speaking(temp_file_path):
        last_phrase_time = now

        # append this audio to the buffer since the person is speaking.
        # if the phrase is a new one, start by keeping wav header, otherwise append chunks with no wav header
        phrase_audio_buffer += data if new_phrase else strip_wav_header(data)

        # TODO better file name handling
        print("saving audio buffer, new_phrase: " + str(new_phrase))
        with open("phrase.wav", 'w+b') as f:
            f.write(phrase_audio_buffer)

        # create a threadpool to execute the two longest running functions (transcribe and identify_speaker) in parallel, then wait for their executions to be complete

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future1 = executor.submit(transcribe, "phrase.wav")            # live transcribe on the audio segment
                future2 = executor.submit(identify_speaker, temp_file_path)    # make a prediction on who is speaking in the chunk 

                running_transcript = future1.result()
                current_speaker_guess = future2.result()

            phrase_class_counts[current_speaker_guess] += 1         # increment the count of how many times this speaker has been guessed for this phrase
            print("PHRASE CLASS COUNTS: " + str(phrase_class_counts))

            running_speaker_history.enqueue(current_speaker_guess)  # add the current speaker to the speaker history queue  

            best_speaker_guess = max(phrase_class_counts, key=phrase_class_counts.get)  # the best guess of the current speaker is the one who has been guessed for majority of the phrase

            output = {
                "id": phrase_id,
                "text": running_transcript,
                "speaker": best_speaker_guess
            }
            last_output = output # save this to use later if needed

            print("OUTPUT: ", str(output))
            emit("transcript_update", output)

            # since we just got someone talking, prepare for more talking from them
            new_phrase = False

        except:
            print(".\n") # hide the nasty whisper tensor size errors
            
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