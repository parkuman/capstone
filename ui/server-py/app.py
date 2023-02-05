import tempfile
import threading
import subprocess

import librosa    
import soundfile as sf

from flask import Flask
from flask_socketio import SocketIO, send, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

FILE_NAME = "audio"
audio_bytes = b""
is_first = True

def save_blob_to_file(blob):
    fp = tempfile.NamedTemporaryFile()
    print("\nTEMP FILE NAME" + fp.name)
    fp.write(blob) 
    # fp.seek(0)
    # fp.close()

def save_wav_16(bytes: bytes, file_name):
    # write audio bytes to wav file
    with open(file_name + ".wav", "wb") as file:
      file.write(audio_bytes)

    y, sr = librosa.load(file_name + ".wav", sr=16000) # Downsample 44.1kHz to 16kHz for whisper to be able to read it
    sf.write(file_name + "_16.wav", y, sr, "PCM_16")   # save the 16KHz file as 16 bit (also for whisper)


def popenAndCall(onExit, *popenArgs, **popenKWArgs):
    """
    Runs a subprocess.Popen, and then calls the function onExit when the
    subprocess completes.

    Use it exactly the way you'd normally use subprocess.Popen, except include a
    callable to execute as the first argument. onExit is a callable object, and
    *popenArgs and **popenKWArgs are simply passed up to subprocess.Popen.
    """
    def runInThread(onExit, popenArgs, popenKWArgs):
        proc = subprocess.Popen(*popenArgs, **popenKWArgs)
        proc.wait()
        onExit()
        return

    thread = threading.Thread(target=runInThread,
                              args=(onExit, popenArgs, popenKWArgs))
    thread.start()

    return thread # returns immediately after the thread starts


def transcribe(file_name):
    subprocess.run(["./main", "-f", "../capstone/ui/server-py/" + file_name + "_16.wav", 
                    "--model", "models/ggml-large.bin", 
                    "--output-txt"], 
                    cwd="/home/parker/code/whisper.cpp")
    
    with open(file_name + "_16.wav.txt", "r") as f:
        contents = f.readlines()
        emit("finished_transcription", contents)


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
    transcribe(FILE_NAME)


if __name__ == "__main__":
    socketio.run(app)