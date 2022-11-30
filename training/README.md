# Training Folder

# Installation Instructions
1. We are using WSL2 since it supports Tensorflow GPU better than regular windows. Download wsl2 and ensure you can open an ubuntu terminal on your windows machine.
2. Download Linux	Miniconda3 64-bit .sh file and save it to Downloads
    * from an ubuntu bash terminal: 
    ```bash
      bash /mnt/c/Users/<your_username>/Downloads/<miniconda3 shell script you downloaded>
    ```
    * this should then prompt all the install steps.
3. setup our `capstone` environment:
    ```bash
    ./setup.sh
    conda activate capstone
    ```

