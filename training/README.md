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
3. Download `training_data_wav` and `testing_data` from Teams `data` folder into this `capstone/training` folder on your computer.
4. If you wish to use an already trained and saved model, we have those saved in Teams under `saved_models`, save that folder into this `capstone/` folder on your computer.
