import numpy as np
import math
import matplotlib.pyplot as plt

import soundfile as sf
import json
import os
import sys

import pdb
import traceback

# gui.py
import gui

fs = 44100 # sample rate
seconds = 1
T = np.linspace(0, seconds, math.ceil(fs*seconds))
note = 440 # tuning frequency

# this makes a sound vaguely similar to dx7 epiano
default_patch = {"freqs" : [[14, 1], [1, 1], [1, 1]],
                 "mod_indices" : [[0, 58/99], [0, 89/99], [0,79/99]],
                 "envs" : [[1, 1], [1, 1], [1, 1]],
                 "output_env" : [0.0125, 0.025, 0.15, 0.7, 0.05],
                 "mod_0" : [0, 0, 0],
                 "algorithm" : [2, 2, 2],
                 "feedback" : [[0, 0], [0, 0], [0, 0]]
                 }

# returns adsr envelope 
def envelope(a, d, s_len, s_level, r):
    a_end = np.ceil(a*fs)
    a_int = np.linspace(0, 1, int(a_end))
    d_end = np.ceil(d*fs)
    d_int = 1 - np.linspace(0, 1-s_level, int(d_end))
    s_end = np.ceil(s_len*fs)
    s_int = s_level*np.ones(int(s_end))
    r_end = np.ceil(r*fs)
    r_int = s_level*np.linspace(1, 0, int(r_end))
    adsr = np.concatenate((a_int, d_int, s_int, r_int))
    return np.concatenate((adsr, np.zeros(np.size(T)-np.size(adsr))))

    
#  mod freq 
#   |   |
#   V   V
#    OSC
#     |
#     V
#    VCO <--- env
#     |
#     V
#    out
class Operator:

    # freq: base frequency for sine oscillator
    # mod: modulating wave
    # env: adsr envelope or scalar between 0-1
    # fb: no. of times to apply feedback
    # out: wave resulting from fm and envelope
    def __init__(self, freq, mod_idx, env, fb):
        self.freq = freq*note
        self.mod_idx = mod_idx
        self.env =  env if not isinstance(env, list) else envelope(*env)
        self.fb = fb
        self.mod = []
        self.out = []

    def set_mod(self, mod):
        self.mod = mod

        # change so feedback mod is different to external input mod
    def set_out(self):
        if self.mod is []:
            raise Exception("modulating signal not set")
        # this is actually phase modulation
        for i in range(0,self.fb):
            self.mod = np.multiply(self.env,
                                   np.sin(2*np.pi*self.freq*T + self.mod_idx*self.mod))
        self.out = np.multiply(self.env,
                               np.sin(2*np.pi*self.freq*T + self.mod_idx*self.mod))

# the carrier is the final operator in a "chain" of operators. the output of a carrier is the resulting wave 
class Carrier(Operator): 
    
    def __init__(self, freq, mod_idx, env, fb):
        super().__init__(freq, mod_idx, env, fb)

    def get_out(self):
        if self.out is []:
            raise Exception("carrier output not defined")

        return self.out

# modulator output always goes to another operator
class Modulator(Operator):

    def __init__(self, freq,  mod_idx, env, fb):
        self.next_op = []
        super().__init__(freq, mod_idx, env, fb)

    def set_next_op(self, next_op):
        self.next_op = next_op
        
    def set_next_mod(self):
        if self.out is [] or self.next_op is []:
            raise Exception("modulator output not set or next operator not set")
        (self.next_op).set_mod(self.out)

""" The Synth class provides the interface between the gui and patch data and synth outputs. 

 synth patch data is structured in a specific way so it can only be modified
using Synth object methods. this ensures that the patch files saved are always valid,
and synth output is always current after patch has been changed in some way.
"""
class Synth:

    def __init__(self, patch):

        self.patch = patch
        self._apply_patch()
        self._update_output_envelope()
        self.output_with_envelope = np.multiply(self.output_envelope, self.output)
        self.n_ops = sum(self.patch["algorithm"])
        self.n_chains = len(self.chain_outputs)
        
    def _apply_patch(self):
        outputs = []
        for a, f, mi, e, m_0, fb in zip(self.patch["algorithm"],
                                        self.patch["freqs"],
                                        self.patch["mod_indices"],
                                        self.patch["envs"],
                                        self.patch["mod_0"],
                                        self.patch["feedback"]):
            if a > 1:
                outputs.append(op_chain(f, mi, e, m_0, fb))
            else:
                carrier = Carrier(f, mi, e, fb)
                carrier.set_mod(m_0)
                carrier.set_out()
                outputs.append(carrier.get_out())

            added_outputs = addsyn(outputs)
            self.chain_outputs = outputs
            self.output = added_outputs

    def _update_outputs(self):
        self._apply_patch()
        self.output_with_envelope = np.multiply(self.output_envelope, self.output)
        
    def _update_output_envelope(self):
        self.output_envelope = envelope(*self.patch["output_env"]) if isinstance(self.patch["output_env"], list) else self.patch["output_env"]
        self.output_with_envelope = np.multiply(self.output_envelope, self.output)
        
    """ return patch parameter values as an "unpacked" list
    if patch["freqs"] = [1, [1, 1], [1, 1, 1]] then get_patch_param("freqs") returns [1,1,1,1,1,1].
    this is used for initialising parameter entries in gui.
    """
    def get_patch_param(self, param_name):
        vals = self.patch[param_name]
        new_vals = []
        for i in vals:
            if isinstance(i, list):
                for j in i:
                    new_vals.append(j)
            else:
                new_vals.append(i)
        return new_vals

    """ returns parameters for envelope function.
    by default, parameters for output envelope
    if op parameter is specified, returns envelope parameters for that operator.

    e.g. patch["envs"] = [1, 1, [0.1, 0.1, 0.1, 0.1, 0.1], 1]
    get_envelope_patch_param(op=3) = [0.1, 0.1, 0.1, 0.1, 0.1]
    get_envelope_patch_param(op=1) = 1
    """
    def get_envelope_patch_param(self, op=0):
        if op == 0:
            return self.patch["output_env"]
        else:
            return self.patch["envs"][op-1]
    
    def has_envelope(self, op=0):
        if op == 0:
            return isinstance(self.patch["output_env"], list)
        else:
            return isinstance(self.patch["envs"][op-1], list)
        
    # input: list of numbers as strings e.g. ["1", "2", "3"]
    # for freqs, mod_indices, feedback, output_env
    def set_patch_param(self, vals, param_name):
        vals = strlist_to_nums(vals, param_name)
        if param_name == "output_env":
            self.patch["output_env"] = vals
            self._update_output_envelope()
        else:
            vals = reshape_list(vals, self.patch["algorithm"])
            self.patch[param_name] = vals
            self._update_outputs()

    def play_sound(self):
        sf.write("temp.wav", self.output_with_envelope, fs)
        os.system(f'aplay ./temp.wav')

    # default output env, op=op number
    def get_envelope_plot_params(self):
        return T, self.output_envelope if isinstance(self.patch["output_env"], list) else self.output_envelope*np.ones(np.size(T))

    # default output without env, ch=chain number
    def get_spectrum_plot_params(self):
        pass

    # feels sketchy
    def get_output_plot_params(self, output_num=0):
        output_list = [self.output]
        output_list = output_list + self.chain_outputs
        return T[0:410], output_list[output_num][0:410]

    def save_patch(self, patch_name):
        with open(patch_name, 'w') as f:
            data = json.dump(self.patch, f)
        print("patch saved in " + patch_name)
    
# these will be used if non-sine fm is implemented
def makesine(freq):
    T = np.linspace(0, dur, math.ceil(fs*seconds))
    return np.sin(2*np.pi * freq * T)

def makesaw(freq):
    T = np.linspace(0, dur, math.ceil(fs*seconds))
    return 2*freq*(T % (1/freq)) - 1

def makesquare(freq):
    return np.sign(makesine(freq))

# return normalised pointwise sum of list of waves for additive synthesis
def addsyn(waves):
    out = np.sum(waves, 0)
    out = out/np.max(out)
    return out


# -- PATCH METHODS --

# to add: error checking
def read_patch(patch_filename):
    with open(patch_filename) as f:
        patch = json.load(f)

    print(patch)
    return patch

def make_patch(freqs, mod_indices, envs, output_env, mod_0, algorithm, feedback):
        patch = {"freqs" : freqs,
             "mod_indices" : mod_indices,
             "envs" : envs,
             "output_env" : output_env,
             "mod_0" : mod_0,
             "algorithm" : algorithm,
             "feedback" : feedback}
        return patch
        
""" given an algorithm, initialises and returns a new patch

 e.g. given algorithm: [1, 2, 3],
      returns patch: {"freqs" : [1, [1, 1], [1, 1, 1]],
                      ...
                      "output_env" : 1
                      "mod_0" : [0, 0, 0],
                      "algorithm" : [1, 2, 3],
                      "feedback" : [0, [0, 0], [0, 0, 0]]}
"""
def new_patch_algorithm(algorithm):
    n_ops = int(np.sum(algorithm))
    freqs = reshape_list([1]*n_ops, algorithm)
    mod_indices = freqs
    envs = freqs
    feedback = reshape_list([0]*n_ops, algorithm)
    output_env = 1
    mod_0 = [0]*len(algorithm)
    patch = make_patch(freqs, mod_indices, envs, output_env,
                       mod_0, algorithm, feedback)
    return patch



# returns output of carrier from "chain" of operators, e.g.
# M -> M -> M -> C
# is a chain of four operators.
#
# implementation feels janky
def op_chain(freqs, mod_indices, envs, mod_0, feedbacks):
    curr_op = Modulator(freqs[0], mod_indices[0], envs[0], feedbacks[0])
    curr_op.set_mod(mod_0)
    curr_op.set_out()
    i = 1
    while i < len(freqs)-1:
        next_op = Modulator(freqs[i], mod_indices[i], envs[i], feedbacks[i])
        curr_op.set_next_op(next_op)
        curr_op.set_next_mod()
        next_op.set_out()
        curr_op = next_op
        i += 1

    last_op = Carrier(freqs[i], mod_indices[i], envs[i], feedbacks[i])
    curr_op.set_next_op(last_op)
    curr_op.set_next_mod()
    last_op.set_out()
    return last_op.get_out()

# for testing
def plot_results(output, outputs, int_end):
    n_outputs = len(outputs)
    fig, ax = plt.subplots(n_outputs+1)
    fig.suptitle("Carrier outputs and final output")
    for i in range(0, n_outputs):
        ax[i].plot(T[0:int_end], outputs[i][0:int_end])
    ax[n_outputs].plot(T[0:int_end], output[0:int_end])
    plt.show()

# -- GUI METHODS --
def get_envelope_plot_params(env_params):
    if len(env_params) > 1:
        env = envelope(*env_params)
        return T[np.nonzero(env)], env[np.nonzero(env)]
    else:
        return T, env_params[0]*np.ones(np.size(T))
    
def get_spectrum_plot_params(wave):
    N = 2048
    return 



# -- HELPER METHODS --

# given an algorithm, reshapes a list for that algorithm
# shape = [1, 2, 3], vals = [1, 1, 1, 1, 1, 1], returns [1, [1, 1], [1, 1, 1]]
def reshape_list(vals, shape):
    new_vals = []
    vals_idx = 0
    for i in shape:
        if i == 1:
            new_vals.append(vals[vals_idx])
            vals_idx += 1
        else:
            vals_mbr = []
            for j in range(0,i):
                vals_mbr.append(vals[vals_idx])
                vals_idx += 1
            new_vals.append(vals_mbr)
    return new_vals

# this converts a parameter to its appropriate type.
# confusingly, strlist can be either a list of strings, or a string.
def strlist_to_nums(strlist, param):
    param_type = {"freqs" : float,
                  "mod_indices" : float,
                  "envs" : float,
                  "output_env" : float,
                  "mod_0" : float,
                  "algorithm" : int,
                  "feedback" : int}
    return [param_type[param](a) for a in strlist] if isinstance(strlist, list) else param_type[param](strlist)

def main():
    # read file without having to go through the gui file dialogue
    if len(sys.argv) > 1:
        patch_to_read = sys.argv[1]
        try:
            patch = read_patch(patch_to_read)
            synth = Synth(patch)
        except OSError:
            print("cannot open ", patch_to_read)
    else:
        synth = None
    win = gui.MainWindow(synth)
    gui.start_gui(win)
        
        
if __name__ == '__main__':
    main()
