#!/bin/bash

cd whisper.cpp

# build the main program
make main

bash ./models/download-ggml-model.sh large