# fm-synth
fm synth with Gtk gui

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)

## Installation
1. Clone the repository:
```bash
git clone https://github.com/CoolGuy75562/fm-synth.git
```
2. Install dependencies:
```bash
pip3 install soundfile numpy matplotlib
```
If they are not already installed, you will also need PyGObject, Gtk, and their dependencies, which you should be able to find in your distribution's repository.

## Usage
To start the programme, navigate to the fm-synth directory and run
```bash
python3 gui.py
```
You will be given the choice between creating a new patch, or opening an existing patch from a file:
![screenshot1](https://github.com/user-attachments/assets/c0223d25-7e8e-4f68-abac-cc5fdeb66398)

If you choose to create a new patch, a dialog appears for you to enter the "algorithm" for your new patch:
![screenshot2](https://github.com/user-attachments/assets/d2d04a97-5468-489e-b073-9a38ab295220)

For each nonzero entry a "chain" of operators of that length will be created. The final output of the synthesizer is the sum of the output of each operator chain. If sets the algorithm to be (2, 2, 2), three chains of two operators are created, so the algorithm has 2+2+2=6 operators in total. Operators are numbered from top to bottom, then left to right, as in the following diagram:
![diagram](https://github.com/user-attachments/assets/6250adde-6b1c-42dd-bbfd-b951d9d9ede0)

After pressing "OK" in the dialog, or after choosing an existing patch from a file, you are brought to the main screen. If you have created a new patch, the parameters of the operators will be initialised to some default values:

![screenshot3](https://github.com/user-attachments/assets/0bd5dd85-5a89-4198-87fa-77a415fe864b)

If you have selected a patch from a file, the parameters are all initialised to the values in the patch. This is how the screen appears if one has selected piano.json:

![screenshot4](https://github.com/user-attachments/assets/37241d05-4282-450e-9582-b2a5059858a4)

Now that you have created or opened a patch, you are ready to listen to the sound it makes by pressing the "play" button, or experiment with the parameters of each chain. 

### Operator Parameters
An operator takes a modulating signal, frequency, and an envelope as inputs, 
![untitled(1)](https://github.com/user-attachments/assets/a953457b-4570-42da-b538-5eb278a7f60e)

If we have two operators, a modulator and a carrier, the output will be 

![latex](https://github.com/user-attachments/assets/3cd316f2-44dc-433c-acdc-6b4f06f8af58)

where F_c, F_m, E_c, E_m, and f_c, f_m are the respective outputs, envelopes, and frequencies for the carrier and modulator, and I is the modulation index.

For more information see:
CHOWNING, J. M. (1977). The Synthesis of Complex Audio Spectra by Means of Frequency Modulation. Computer Music Journal, 1(2), 46–54.
