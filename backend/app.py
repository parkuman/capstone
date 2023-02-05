import tempfile
import subprocess
import logging

import numpy as np
import librosa    
import soundfile as sf
import tensorflow as tf

from flask import Flask
from flask_socketio import SocketIO, send, emit

from utils.extract_features import extract_features

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", logger = False)
logging.getLogger("werkzeug").setLevel(logging.ERROR) # flask
logging.getLogger("socketio").setLevel(logging.ERROR) # socketio
logging.getLogger("engineio").setLevel(logging.ERROR)

FILE_NAME = "audio"
audio_bytes = b""
is_first = True

model = tf.keras.models.load_model("../saved_models/4_classes-02_05_2023_14_24_15")
speakers = ["hannah", "aiden", "parker", "adam"]

"""
Write a blob of wav data as a temporary file where we can then load that 
file and predict who is speaking in it using librosa and our trained 
model. 
"""
def save_blob_to_file(blob):
    # create and save temp file
    fp = tempfile.NamedTemporaryFile()
    print("\nTEMP FILE NAME" + fp.name)
    fp.write(blob) 
    fp.seek(0)

    # make a prediction on it
    temp_audio_file = fp.name
    y, sr = librosa.load(temp_audio_file, offset=0, duration=30)
    test_frame_features = extract_features(y, sr)
    pred = model.predict(test_frame_features.reshape(1,len(test_frame_features)))
    idx = np.argmax(pred)
    print("SPEAKER: " + speakers[idx])
    emit("current_speaker", speakers[idx])

    fp.close()

def save_wav_16(bytes: bytes, file_name):
    # write audio bytes to wav file
    with open(file_name + ".wav", "wb") as file:
      file.write(audio_bytes)

    y, sr = librosa.load(file_name + ".wav", sr=16000) # Downsample 44.1kHz to 16kHz for whisper to be able to read it
    sf.write(file_name + "_16.wav", y, sr, "PCM_16")   # save the 16KHz file as 16 bit (also for whisper)



def transcribe(file_name):
    # whisper transcribe
    subprocess.run(["./main", "-f", "../backend/" + file_name + "_16.wav", 
                    "--model", "models/ggml-large.bin", 
                    "--output-txt"], 
                    cwd="../whisper.cpp")
    
    with open(file_name + "_16.wav.txt", "r") as f:
        contents = f.readlines()
        emit("finished_transcription", contents)


def identify_speakers(file_name):
    # model prediction
    test_file_path = file_name + "_16.wav"
    sr = librosa.get_samplerate(test_file_path)
    stream = librosa.stream(test_file_path,
                        block_length=256,
                        frame_length=2048,
                        hop_length=512)

    
    for y in stream:
        test_frame_features = extract_features(y, sr)
        pred = model.predict(test_frame_features.reshape(1,len(test_frame_features)))
        idx = np.argmax(pred)
        print(speakers[idx])



@socketio.on("connect")
def handle_message(data):
    print("client connected!")

@socketio.on("begin_transcription")
def handle_message(data):
    global is_first, audio_bytes

    audio_bytes = b"" # clear the saved audio from the previous transcription
    is_first = True

    print("===============| begin_transcription |===============\n" + str(data))
    emit("ready_to_receive_chunks")

@socketio.on("audio_chunk")
def handle_message(data):
    global is_first, audio_bytes
    
    # print("\nreceived audio chunk:\n", data)
    save_blob_to_file(data)

    audio_bytes += data if is_first else data[44:] # if its not the first chunk, get rid of WAV header (first 44 bytes)
    is_first = False


@socketio.on("end_transcription")
def handle_message():
    print("\===============| end_transcription |===============\n")

    save_wav_16(audio_bytes, FILE_NAME)

    # transcribe(FILE_NAME)
    # identify_speakers(FILE_NAME)


if __name__ == "__main__":
    socketio.run(app)