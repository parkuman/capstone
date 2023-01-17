import whisper

model = whisper.load_model("base")
result = model.transcribe("training_data/parker/recording_11.wav")
print(result["text"])
