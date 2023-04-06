import numpy as np
import librosa

# Mel Frequency Cepstral Coefficients (MFCC)
def extract_mfcc(y, sr):
  mfcc = np.array(librosa.feature.mfcc(y=y, sr=sr, n_mels=128, n_mfcc=12, n_fft=512, hop_length=128))
  mfcc = librosa.util.normalize(mfcc)

  return mfcc

def extract_melspectrogram(y, sr):
  melspectrogram = np.array(librosa.feature.melspectrogram(y=y, sr=sr))
  return melspectrogram

def extract_chroma_vector(y, sr):
  chroma = np.array(librosa.feature.chroma_stft(y=y, sr=sr))
  return chroma

def extract_spectral_contrast(y, sr):
  tonnetz = np.array(librosa.feature.spectral_contrast(y=y, sr=sr))
  return tonnetz

# tonal centroid features (tonnetz)
def extract_tonnetz(y, sr):
  tonnetz = np.array(librosa.feature.tonnetz(y=librosa.effects.harmonic(y), sr=sr))
  return tonnetz

def extract_features(y, sr):
  # Extracting MFCC feature
  mfcc = extract_mfcc(y, sr)
  mfcc_mean = mfcc.mean(axis=1)
  mfcc_min = mfcc.min(axis=1)
  mfcc_max = mfcc.max(axis=1)
  mfcc_feature = np.concatenate( (mfcc_mean, mfcc_min, mfcc_max) )

  # # Extracting Mel Spectrogram feature
  # melspectrogram = extract_melspectrogram(y, sr)
  # melspectrogram_mean = melspectrogram.mean(axis=1)
  # melspectrogram_min = melspectrogram.min(axis=1)
  # melspectrogram_max = melspectrogram.max(axis=1)
  # melspectrogram_feature = np.concatenate( (melspectrogram_mean, melspectrogram_min, melspectrogram_max) )

  # # Extracting chroma vector feature
  # chroma = extract_chroma_vector(y, sr)
  # chroma_mean = chroma.mean(axis=1)
  # chroma_min = chroma.min(axis=1)
  # chroma_max = chroma.max(axis=1)
  # chroma_feature = np.concatenate( (chroma_mean, chroma_min, chroma_max) )

  # # Extracting spectral contrast feature
  # spectral_contrast = extract_spectral_contrast(y, sr)
  # spectral_contrast_mean = spectral_contrast.mean(axis=1)
  # spectral_contrast_min = spectral_contrast.min(axis=1)
  # spectral_contrast_max = spectral_contrast.max(axis=1)
  # spectral_contrast_feature = np.concatenate( (spectral_contrast_mean, spectral_contrast_min, spectral_contrast_max) )

  # # Extracting tonnetz feature
  # tonnetz = extract_tonnetz(y, sr)
  # tonnetz_mean = tonnetz.mean(axis=1)
  # tonnetz_min = tonnetz.min(axis=1)
  # tonnetz_max = tonnetz.max(axis=1)
  # tonnetz_feature = np.concatenate( (tonnetz_mean, tonnetz_min, tonnetz_max) ) 
  
  # features = np.concatenate( (melspectrogram_feature, mfcc_feature, chroma_feature, spectral_contrast_feature, tonnetz_feature) )
  features = mfcc_feature 

  return features