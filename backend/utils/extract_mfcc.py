import librosa
import numpy as np

def extract_mfcc(y, sr):
  normalized_y = librosa.util.normalize(y)

  # Compute MFCC coefficients
  mfcc = librosa.feature.mfcc(y=normalized_y, sr=sr, n_mfcc=40)

  # Normalize MFCC
  normalized_mfcc = librosa.util.normalize(mfcc)

  return normalized_mfcc



# Given an numpy array of features, zero-pads each ocurrence to max_padding
def add_padding(features, mfcc_max_padding):
  padded = []

  # Add padding
  for i in range(len(features)):
    px = features[i]
    print(px[0])
    size = len(px[0])
    # Add padding if required
    if (size < mfcc_max_padding):
      xDiff = mfcc_max_padding - size
      xLeft = xDiff//2
      xRight = xDiff-xLeft
      px = np.pad(px, pad_width=((0,0), (xLeft, xRight)), mode='constant')
  
    padded.append(px)

  return padded
