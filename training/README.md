# Training Folder

# Installation Instructions
1. Install anaconda / miniconda
2. setup our `capstone` anaconda environment:
    ```bash
    cd capstone/training
    conda create -n capstone python=3.9
    conda activate capstone
    conda install tensorflow
    pip install librosa pyaudio ipykernel matplotlib
    ```
3. Download `data/training_data_wav` from Teams into this `/training` folder