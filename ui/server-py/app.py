import tempfile

from flask import Flask
from flask_socketio import SocketIO, send, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

audio_bytes = b""
is_first = True

def save_blob_to_file(blob):
    fp = tempfile.NamedTemporaryFile()
    print("\nTEMP FILE NAME" + fp.name + "\nFirst: " + str(is_first))
    fp.write(blob) 
    # fp.seek(0)
    # fp.close()

@socketio.on("connect")
def handle_message(data):
    print("client connected!")

@socketio.on("begin_transcription")
def handle_message(data):
    global is_first, audio_bytes
    audio_bytes = b"" # clear the saved audio 
    is_first = True
    print("===============| begin_transcription |===============\n" + str(data))
    emit("ready_to_receive_chunks")

@socketio.on("audio_chunk")
def handle_message(data):
    global is_first, audio_bytes
    
    print("\nreceived audio chunk:\n", data[44:])
    print("\n\n\n\nDATA HEADER:\n", data[:44])
    save_blob_to_file(data)

    audio_bytes += data if is_first else data[44:] # if its not the first chunk, get rid of WAV header (first 44 bytes)
    is_first = False


@socketio.on("end_transcription")
def handle_message():
    print("\===============| end_transcription |===============\n")
    with open("audio.wav", 'wb') as file:
      file.write(audio_bytes)


if __name__ == "__main__":
    socketio.run(app)