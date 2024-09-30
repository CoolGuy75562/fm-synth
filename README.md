# pythonfm
basic fm synth implementation in python

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)

## Installation
1. Clone the repository:
```bash
git clone https://github.com/CoolGuy75562/pythonfm.git
```
2. Install dependencies:
```bash
pip3 install soundfile numpy matplotlib
```
## Usage
To start the programme, navigate to the pythonfm directory and run
```bash
python3 ./fm.py
```
You will be given the choice between creating a new patch, or opening an existing patch from a file:
![screenshot1](https://github.com/user-attachments/assets/8d52d986-b6e7-40b3-a6f6-5e7a528bbc0f)

If you choose to create a new patch, a dialog appears for you to enter the "algorithm" for your new patch:
![screenshot2](https://github.com/user-attachments/assets/31d2ef5c-4981-4cf4-a8da-c3951dfffdb3)

For each nonzero entry a "chain" of operators of that length will be created. The final output of the synthesizer is the sum of the output of each operator chain. In this example, three chains of two operators are created, so the algorithm has 2+2+2=6 operators in total. Operators are numbered from top to bottom, then left to right, as in the following diagram:
![diagram](https://github.com/user-attachments/assets/6250adde-6b1c-42dd-bbfd-b951d9d9ede0)

After pressing "OK" in the dialog, or after choosing an existing patch from a file, you are brought to the main screen. If you have created a new patch, the parameters of the operators will be initialised to some default values:
![screenshot3](https://github.com/user-attachments/assets/25f328c4-fe15-4b6b-b0a0-71f3e33277de)

If you have selected a patch from a file, everything is initialised according to the selected patch. This is how the screen appears if one has selected piano.json:
![screenshot4](https://github.com/user-attachments/assets/2d6dc350-58ec-4cc0-88df-c2558e1a114a)

### Operator Parameters
An operator takes a modulating signal, frequency, and an envelope as inputs, and gives the output
![untitled(1)](https://github.com/user-attachments/assets/a953457b-4570-42da-b538-5eb278a7f60e)
![screenshot5](https://github.com/user-attachments/assets/76d08b64-1145-4919-9af4-6bc4c8466256)

### Plots
From top to bottom, there is one plot for each operator chain output, a plot of the output (the sum of each chain output), and a plot of the output envelope if the patch has one, else just a plot of a line at y=1. 

### Envelope
If the switch in the bottom left is in the "off" position, turning it on will reveal adsr envelope parameters. If "update output_env" is then pressed, the envelope will be applied to the output, and the output envelope plot will be updated. 

Turning the switch off will remove the envelope from the output and the output envelope plot will become a line at y=1.
