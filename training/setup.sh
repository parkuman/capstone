#!/bin/bash
# Creates a conda environment called capstone and installs the required packages we are using using conda package manager

conda create -n capstone python=3.9
conda install -n capstone tensorflow
pip install pyaudio
pip install librosa
pip install ipykernel

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CONDA_PREFIX/lib/