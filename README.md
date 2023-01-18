# Speaker Recognition and Speech Transcription Capstone Project
The goal of this project is to provide a system that runs entirely locally for speaker recognition and speech transcription. 

# Group Members
* Adam Strom
* Aidan Horan
* Hannah Berthiaume
* Parker Rowe

# Project Structure
```
|
├── /training 
|   |
│   |── /testing_data // any files used to test the model (audio data that the model has never seen before)
│   |    └── *
|   |
│   |── /training_data_wav // .wav files organized into folders 
│   |    |── /{class_name1}
│   |    |    |── {audio1.wav}
│   |    |    |── ....
│   |    |    └── {audioX.wav}
│   |    |── ....
│   |    └── /{class_nameX}
|   |
|   └── any files used for training our model using tensorflow
|
├── /ui
|   └── any files responsible for creating a GUI for interacting with our voice transcription system
|
├── .gitignore // files that git should ignore
└── README.md

```

# Installation Instructions
1. To clone the repo make sure you have Git installed on your computer. Then authenticate your GitHub account using either:
   * [ssh keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) (this one is easier i feel)
     * Once done, run the following command in your terminal in whatever folder you want to save the repository
     ```
     git clone git@github.com:parkuman/capstone.git
     ```
   * [GitHub personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
     * Once done, run the following command in your terminal in whatever folder you want to save the repository
    ```
    git clone https://github.com/parkuman/capstone.git
    ```
2. Once cloned, check the READMEs in the other folders to see how to install those components.
