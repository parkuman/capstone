import torch

SAMPLING_RATE = 16000

model, utils = torch.hub.load(repo_or_dir="../vad",
                              model="silero_vad",
                              force_reload=True,
                              source="local",
                              onnx=False)

(get_speech_timestamps,
 save_audio,
 read_audio,
 VADIterator,
 collect_chunks) = utils

"""
  Detects if someone is speaking using MIT licensed https://github.com/snakers4/silero-vad
"""
def is_speaking(file_name):
  wav = read_audio(file_name, sampling_rate=SAMPLING_RATE)

  speech_timestamps = get_speech_timestamps(wav, model, sampling_rate=SAMPLING_RATE)

  # return true if speech_timestamps has length
  return len(speech_timestamps) != 0
    

