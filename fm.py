""" This module contains the implementation of the FM synthesizer,
and methods to create, change, save, and open patches.
"""
import math
import json
import os
import tempfile

import numpy as np
import soundfile as sf


FS = 44100 # sample rate
SECONDS = 1
T = np.linspace(0, SECONDS, math.ceil(FS*SECONDS))
NOTE = 440 # tuning frequency

# this makes a sound vaguely similar to dx7 epiano
default_patch = {"freqs" : [[14, 1], [1, 1], [1, 1]],
                 "mod_indices" : [[0, 58/99], [0, 89/99], [0,79/99]],
                 "envs" : [[1, 1], [1, 1], [1, 1]],
                 "output_env" : [0.0125, 0.025, 0.15, 0.7, 0.05],
                 "mod_0" : [0, 0, 0],
                 "algorithm" : [2, 2, 2],
                 "feedback" : [[0, 0], [0, 0], [0, 0]]
                 }


def envelope(a, d, s_len, s_level, r):
    """ Returns adsr envelope.
    Args:
        a: attack length in seconds
        d: decay length in seconds
        s_len: sustain length in seconds
        s_level: sustain level, between 0 and 1
        r: release length in seconds

    Returns:
        An adsr envelope as an np.array of size np.size(T)
    """
    if s_level > 1 or s_level < 0:
        raise ValueError(f"s_level {s_level} is not in the interval [0,1]")
    a_end = np.ceil(a*FS)
    a_int = np.linspace(0, 1, int(a_end))
    
    d_end = np.ceil(d*FS)
    d_int = 1 - np.linspace(0, 1-s_level, int(d_end))
    
    s_end = np.ceil(s_len*FS)
    s_int = s_level*np.ones(int(s_end))
    
    r_end = np.ceil(r*FS)
    r_int = s_level*np.linspace(1, 0, int(r_end))
    
    adsr = np.concatenate((a_int, d_int, s_int, r_int))
    if a + d + s_len + r > SECONDS:
        env = np.resize(adsr, np.size(T))
    else:
        env = np.concatenate((adsr, np.zeros(np.size(T)-np.size(adsr))))
    return env

class Operator:
    """ This class used to represent an FM synth operator.

    Attributes:
        freq: Frequency of the operator's sine oscillator.
        mod_idx: The modulation index to be used in the FM computation.
        env: An envelope which is applied to the operator's output.
        fb: Number of times for operator to feed output to itself and compute
          output again.
        mod: The wave to modulate the frequency of the operator's oscillator.
        out: The output of the operator after FM synthesis and envelope applied.
    """
    def __init__(self, freq, mod_idx, env, fb, mod):
        """Initialises the Operator object.

        Args:
            freq: A multiple of the base frequency NOTE.
            mod_idx: Modulation index.
            env: Envelope.
            fb: Feedback.
            mod: Modulating wave.
            out: Operator output.
        """
        self.freq = freq*NOTE
        self.mod_idx = mod_idx
        self.env =  env if not isinstance(env, list) else envelope(*env)
        self.fb = fb
        self.mod = mod
        self.update_out() # sets self.out

    def update_out(self):
        """ Sets the operator's 'out' attribute to the result of FM,
        which is computed from all its other attributes. 

        If feedback = n, makes the computation n times,
        each time plugging output back into itself.
        """
        # this is actually phase modulation
        for _ in range(0,self.fb):
            self.mod = np.multiply(self.env,
                                   np.sin(2*np.pi*self.freq*T + self.mod_idx*self.mod))
        self.out = np.multiply(self.env,
                               np.sin(2*np.pi*self.freq*T + self.mod_idx*self.mod))

class Synth:
    """ The Synth class is responsible for computing the result of fm synthesis
    from patch data, updating and saving patch data, and giving information to
    the user interface such as output plot parameters.

    Attributes:
        patch: A dictionary containing the parameters for each operator,
          and the output envelope.
        chains: A list which can contain single operators, and operator chains,
          which are lists of operators whose outputs are "chained" together.
        chain_outputs: A list of the output of each operator chain.
        output_envelope: The envelope to be applied to the output.
        output: The normalised pointwise sum of the chain outputs,
          before the output envelope has been applied.
        output_with_envelope: Output after envelope applied.
    """
    def __init__(self, patch):
        self.patch = patch
        self._apply_patch()
        self._update_output_envelope()
        self.output_with_envelope = np.multiply(self.output_envelope, self.output)

    def _apply_patch(self):
        chain_outputs = []
        chains = []
        for a, f, mi, e, m_0, fb in zip(self.patch["algorithm"],
                                        self.patch["freqs"],
                                        self.patch["mod_indices"],
                                        self.patch["envs"],
                                        self.patch["mod_0"],
                                        self.patch["feedback"]):
            if a > 1:
                chain_output, chain = op_chain(f, mi, e, m_0, fb)
                chain_outputs.append(chain_output)
                chains.append(chain)
            else:
                carrier = Operator(f, mi, e, fb, m_0)
                chain_outputs.append(getattr(carrier, 'out'))
                chains.append(carrier)
            added_outputs = addsyn(chain_outputs)
            self.chains = chains
            self.chain_outputs = chain_outputs
            self.output = added_outputs

    def _update_outputs(self):
        self._apply_patch()
        self.output_with_envelope = np.multiply(self.output_envelope, self.output)

    def _update_output_envelope(self):
        if isinstance(self.patch["output_env"], list):
            self.output_envelope = envelope(*self.patch["output_env"])
        else:
            self.output_envelope = self.patch["output_env"]
        self.output_with_envelope = np.multiply(self.output_envelope, self.output)

    def get_patch_param(self, param_name):
        """ Gets the parameter in the patch specified by param_name as an "un-nested" list.

        Args:
            param_name: The name of the patch parameter.

        Returns:
          An un-nested list of the patch parameter,
          e.g., if we have patch["freqs"] = [[1, 14], [1, 1], [1, 1]],
          then get_patch_param("freqs") returns [1, 14, 1, 1, 1, 1].
        """
        vals = self.patch[param_name]
        new_vals = []
        for i in vals:
            if isinstance(i, list):
                for j in i:
                    new_vals.append(j)
            else:
                new_vals.append(i)
        return new_vals

    def get_envelope_patch_param(self, op=0):
        """ Gets the envelope parameter in the patch for the
            specified operator, or the output envelope by default.

        Args:
            op: The operator number, an integer between 1-sum(patch["algorithm"]).

        Returns:
            The envelope parameter for the operator if op is specified,
            else the output envelope parameter. The envelope parameter is
            in the form [a, d, s_len, s_level, r] for the envelope function.
        """
        if op == 0:
            return self.patch["output_env"]
        return self.patch["envs"][op-1]

    def has_envelope(self, op=0):
        """ Returns whether the specified operator has an envelope,
        or the output envelope by default.

        Args:
            op: the operator number, an integer between 1-sum(patch["algorithm"]).

        Returns:
            A boolean which is True if the operator/output envelope has an envelope,
            or False if not.
        """
        if op == 0:
            return isinstance(self.patch["output_env"], list)
        return isinstance(self.patch["envs"][op-1], list)

    # for freqs, mod_indices, feedback, output_env
    def set_patch_param(self, vals, param_name):
        """ Takes a list of parameter values, reformats the list
        for the patch, and sets the patch parameter to the new values.

        Args:
            vals: The new parameter values for the patch parameter param_name.
              The length of the list must be the same as the number of operators.
            param_name: The name of the patch parameter for vals to be set to.
        """
        if param_name == "output_env":
            self.patch["output_env"] = vals
            self._update_output_envelope()
        else:
            chain_vals = reshape_list(vals, self.patch["algorithm"])
            self.patch[param_name] = chain_vals
            self._update_outputs()

    def play_sound(self):
        """ Plays the sound of the synth output. """
        with tempfile.NamedTemporaryFile(suffix='.wav') as temp:
            sf.write(temp, self.output_with_envelope, FS)
            os.system(f'aplay {temp.name}')

    def get_envelope_plot_params(self):
        """ Gets x and y values for the envelope plot.
        If an envelope is set, returns the envelope as an np.array,
        otherwise an np.array of ones.
        """
        if isinstance(self.patch["output_env"], list):
            return T, self.output_envelope
        return T, self.output_envelope*np.ones(np.size(T))


    # sketchy
    def get_output_plot_params(self, output_num=0):
        """ Gets x and y parameters for a plot of the output without envelope
        for the first 0.01 seconds, or the output of a chain if specified.

        Args:
            output_num: Which chain output to get the plot parameters for,
              or the output without envelope if 0.

        Returns:
            The x and y parameters for a plot for the first 0.01 seconds.
        """
        output_list = [self.output]
        output_list = output_list + self.chain_outputs
        return T[0:441], output_list[output_num][0:441]

    def save_patch(self, patch_name):
        """ Saves the Synth object's patch attribute in a .json file.

        Args:
            patch_name: The name of the patch, which must be a string.
        """
        with open(patch_name, 'w', encoding="utf-8") as f:
            json.dump(self.patch, f)
        print("patch saved in ", patch_name)

# these will be used if non-sine fm is implemented
def makesine(freq):
    """ Returns a sine wave of frequency freq and duration SECONDS.

    Args:
        freq: Frequency.

    Returns:
        A sine wave of frequency freq and duration SECONDS.
    """
    return np.sin(2*np.pi * freq * T)

def makesaw(freq):
    """ Returns a saw wave of frequency freq and duration SECONDS.

    Args:
        freq: Frequency.

    Returns:
        A saw wave of frequency freq and duration SECONDS.
    """
    return 2*freq*(T % (1/freq)) - 1

def makesquare(freq):
    """ Returns a square wave of frequency freq and duration SECONDS.

    Args:
        freq: Frequency.

    Returns:
        A square wave of frequency freq and duration SECONDS.
    """
    return np.sign(makesine(freq))

def addsyn(waves):
    """ Returns the normalised pointwise sum of a list of waves for
    additive synthesis.

    Args:
        waves: A list of np.array objects of the same shape.

    Returns:
        The normalised pointwise sum of the waves in waves.
    """
    out = np.sum(waves, 0)
    out = out/np.max(out)
    return out


# -- PATCH METHODS --

def read_patch(patch_filename):
    """ Reads a patch from a .json file.

    Args:
        patch_filename: The name of the patch file (including .json).

    Returns:
        The patch read from the file with the name patch_filename in the
          current directory.
    """
    with open(patch_filename, encoding="utf-8") as f:
        patch = json.load(f)
    print(patch)
    return patch


def new_patch_algorithm(algorithm):
    """ given an algorithm, initialises and returns a new patch with default values.

 e.g. given algorithm: [1, 2, 3],
      returns patch: {"freqs" : [1, [1, 1], [1, 1, 1]],
                      ...
                      "output_env" : 1
                      "mod_0" : [0, 0, 0],
                      "algorithm" : [1, 2, 3],
                      "feedback" : [0, [0, 0], [0, 0, 0]]
                     }
    Args:
        algorithm: The "shape" of the patch.

    Returns:
        A new patch with default parameters that are the shape
        specified by algorithm.
"""
    n_ops = int(np.sum(algorithm))
    freqs = reshape_list([1]*n_ops, algorithm)
    mod_indices = freqs
    envs = freqs
    feedback = reshape_list([0]*n_ops, algorithm)
    output_env = 1
    mod_0 = [0]*len(algorithm)
    patch = {"freqs" : freqs,
             "mod_indices" : mod_indices,
             "envs" : envs,
             "output_env" : output_env,
             "mod_0" : mod_0,
             "algorithm" : algorithm,
             "feedback" : feedback
             }
    return patch

def op_chain(freqs, mod_indices, envs, mod_0, feedbacks):
    """ Initialises and computes the output of a chain of operators.

    Args:
        freqs: A list of frequencies, one per operator in the chain.
        mod_indices: A list of modulation indices, one per operator in the chain.
        envs: A list of envelopes, one per operator in the chain.
        feedbacks: A list of feedback parameters, one per operator in the chain.
        mod_0: The modulating wave for the first operator in the chain.
          In current configuration should always be 0.

    Returns:
        getattr(curr_op, 'out'): The output of the final operator in the chain.
        chain: A list of the operators in the chain, ordered from first to last.
    """
    chain = []
    curr_op = Operator(freqs[0], mod_indices[0], envs[0], feedbacks[0], mod_0)
    chain.append(curr_op)
    for freq, mi, env, fb in zip(freqs[1:],
                                 mod_indices[1:],
                                 envs[1:],
                                 feedbacks[1:]):
        next_op = Operator(freq, mi, env, fb, getattr(curr_op, 'out'))
        chain.append(next_op)
        curr_op = next_op
    return getattr(curr_op, 'out'), chain

# -- HELPER METHODS --
def reshape_list(vals, algorithm):
    """ Reshapes a list of parameters for each operator into the correct
    format for a patch specified by algorithm.

    E.g., for the algorithm [1, 2, 3] and vals [1, 1, 1, 1, 1, 1],
    reshape_list(vals, algorithm) returns [1, [1, 1], [1, 1, 1]].

    Args:
        vals: A list of parameter values for each operator. List must be
          the same length as the number of operators, i.e. sum(algorithm).
        algorithm: A list of integers. Each entry specifies an operator chain
          consisting of that many operators.

    Returns:
        new_vals: The list vals formatted according to algorithm as above.
    """
    if len(vals) != sum(algorithm):
        raise ValueError(f"vals {vals} not compatible with algorithm {algorithm}")
    new_vals = []
    vals_idx = 0
    for i in algorithm:
        if i == 1:
            new_vals.append(vals[vals_idx])
            vals_idx += 1
        else:
            vals_mbr = []
            for _ in range(i):
                vals_mbr.append(vals[vals_idx])
                vals_idx += 1
            new_vals.append(vals_mbr)
    return new_vals

def strlist_to_nums(strlist, param):
    """ Converts a list of strings containing numbers to a list of
    numbers of the appropriate type according to param.

    Args:
        strlist: A list of strings of numbers, or potentially a string of a number.
        param: The name of the param in the patch vals are intended to be
          parameters for.

    Returns:
        A list of integers or floats according to the correct type for
        param, or a single integer or float if strlist was a single string.
    """
    param_type = {"freqs" : float,
                  "mod_indices" : float,
                  "envs" : float,
                  "output_env" : float,
                  "mod_0" : float,
                  "algorithm" : int,
                  "feedback" : int}
    if isinstance(strlist, list):
        return [param_type[param](a) for a in strlist]
    return param_type[param](strlist)
