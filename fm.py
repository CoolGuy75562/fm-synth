""" This module contains the implementation of the FM synthesizer,
and methods to create, change, save, and open patches.
"""
# Copyright (C) 2024  CoolGuy75562
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

import math
import json
from jsonschema import validate
import os
import tempfile
import numpy as np
import soundfile as sf


FS = 44100  # sample rate
PLOT_LIM = FS//100  # for output plots, excluding envelope
SECONDS = 1
T = np.linspace(0, SECONDS, math.ceil(FS*SECONDS))
NOTE = 440  # tuning frequency

# this makes a sound vaguely similar to dx7 epiano
default_patch = {"freqs": [[14.0, 1.0], [1.0, 1.0], [1.0, 1.0]],
                 "mod_indices": [[0, 58/99], [0, 89/99], [0, 79/99]],
                 "envs": [[[], []], [[], []], [[], []]],
                 "output_env": [0.0125, 0.025, 0.15, 0.7, 0.05],
                 "mod_0": [0, 0, 0],
                 "algorithm": [2, 2, 2],
                 "feedback": [[0, 0], [0, 0], [0, 0]]
                 }


def envelope(a: float, d: float, s_len: float, s_level: float, r: float
             ) -> np.ndarray:
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
        out: The output of the operator after FM synthesis
          and envelope applied.
    """
    def __init__(self,
                 freq: float,
                 mod_idx: float,
                 env: list,
                 fb: int,
                 mod: np.ndarray
                 ) -> None:
        """Initialises the Operator object.

        Args:
            freq: A multiple of the base frequency NOTE.
            mod_idx: Modulation index.
            env: Envelope.
            fb: Feedback.
            mod: Modulating wave.
            out: Operator output.
        """
        self._freq = freq*NOTE
        self.mod_idx = mod_idx
        self._env = envelope(*env) if env else np.ones(np.size(T))
        self.fb = fb
        self.mod = mod
        self._out = None  # output is not computed until needed

    @property
    def freq(self) -> float:
        return self._freq

    @freq.setter
    def freq(self, value: float) -> None:
        self._freq = value*NOTE

    @property
    def env(self) -> np.ndarray:
        return self._env

    @env.setter
    def env(self, value: list) -> None:
        self._env = envelope(*value) if value else np.ones(np.size(T))

    @property
    def out(self) -> np.ndarray:
        self._update_out()
        return self._out

    def _update_out(self) -> None:
        fb_mod = self.mod
        for _ in range(0, self.fb):
            fb_mod = np.multiply(
                self._env,
                np.sin(2*np.pi*self._freq*T + self.mod_idx*fb_mod)
            )
        self._out = np.multiply(
            self._env,
            np.sin(2*np.pi*self._freq*T + self.mod_idx*fb_mod)
        )


class OperatorChain:
    """ A chain of operators.

    It makes sense to group operators by their chains
    because changing the parameters of one
    chain does not affect the output of other chains.

    An operator chain's parameters are updated all at once,
    rather than per parameter such as freqs or mod_indices.
    This is because changing any parameter for an operator
    early in the chain already requires us to recompute
    the output of each successive operator
    to get the output for the chain.

    Attributes:
        n_ops: The number of operators in the chain
        freqs: A list of frequency parameters,
          one for each operator in the chain
        mod_indices: ""
        envs: ""
        feedback: ""
        mod_0: The modulating signal for the first operator in the chain.
            For normal fm just set it to zero array.
        output: The output of the last operator in the chain,
          i.e. the result of FM synthesis.
        operators: A list of the operators in the chain,
          with smaller index being operator earlier in the chain.
    """
    def __init__(self, n_ops: int, mod_0: np.ndarray, op_params: tuple
                 ) -> None:
        if not n_ops:
            raise ValueError()
        for param in op_params:
            if len(param) != n_ops:
                raise ValueError()
        self.n_ops = n_ops
        self.freqs, self.mod_indices, self.envs, self.feedback = op_params
        self.mod_0 = mod_0
        operators = []
        curr_op = Operator(self.freqs[0],
                           self.mod_indices[0],
                           self.envs[0],
                           self.feedback[0],
                           self.mod_0
                           )
        operators.append(curr_op)
        for freq, mi, env, fb in zip(self.freqs[1:],
                                     self.mod_indices[1:],
                                     self.envs[1:],
                                     self.feedback[1:]
                                     ):
            op = Operator(freq, mi, env, fb, curr_op.out)
            operators.append(op)
            curr_op = op
        self.output = curr_op.out
        self.operators = operators

    def set_new_op_params(self, op_params: list[list]) -> None:
        """ Finds first operator whose parameters are being changed, then
        calls update_output to compute the new chain output.

        A change in the parameters of an operator in a chain only affects
        the outputs of the later parameters, so we only need to compute new
        outputs for operators later in the chain.

        Args:
            op_params: a tuple (freqs, mod_indices, envs, feedbacks)
        """
        # find first operator whose parameters will change
        start_idx = self.n_ops-1
        freqs, mod_indices, envs, feedback = op_params
        for i in range(self.n_ops-1):
            if (freqs[i], mod_indices[i], envs[i], feedback[i]) != (
                    self.freqs[i],
                    self.mod_indices[i],
                    self.envs[i],
                    self.feedback[i]
            ):
                start_idx = i
                break
        # update operator parameters
        self.freqs[start_idx:] = freqs[start_idx:]
        self.mod_indices[start_idx:] = mod_indices[start_idx:]
        self.envs[start_idx:] = envs[start_idx:]
        self.feedback[start_idx:] = feedback[start_idx:]
        # outputs of operators before idx need not change
        self._update_output(start_idx)

    def _update_output(self, idx: int) -> None:
        curr_op = self.operators[idx]
        curr_op.freq, curr_op.mod_idx, curr_op.env, curr_op.fb = (
            self.freqs[idx],
            self.mod_indices[idx],
            self.envs[idx],
            self.feedback[idx]
        )
        for op, freq, mi, env, fb in zip(self.operators[idx+1:],
                                         self.freqs[idx+1:],
                                         self.mod_indices[idx+1:],
                                         self.envs[idx+1:],
                                         self.feedback[idx+1:]
                                         ):
            op.freq, op.mod_idx, op.env, op.fb = freq, mi, env, fb
            op.mod = curr_op.out
            curr_op = op
        self.output = curr_op.out


class Synth:
    """ The Synth class is responsible for computing the result of fm synthesis
    from patch data, updating and saving patch data, and giving information to
    the user interface such as output plot parameters.

    Attributes:
        patch: A dictionary containing the parameters for each operator,
          and the output envelope.
        chains: A list which can contain single operators, and operator chains,
          which are lists of operators whose outputs are "chained" together.
        output: The normalised pointwise sum of the chain outputs,
          before the output envelope has been applied.
    """
    def __init__(self, patch: dict) -> None:
        self.patch = patch
        self.algorithm = self.patch["algorithm"]
        chains = []
        for a, f, mi, e, m_0, fb in zip(self.algorithm,
                                        self.patch["freqs"],
                                        self.patch["mod_indices"],
                                        self.patch["envs"],
                                        self.patch["mod_0"],
                                        self.patch["feedback"]):
            chains.append(OperatorChain(a, m_0, (f, mi, e, fb)))
        self.chains = chains
        self.output = addsyn(
            [getattr(chain, 'output') for chain in self.chains]
        )
        
        if self.patch["output_env"]:
            self._output_envelope = envelope(*self.patch["output_env"])
            self._prev_output_env_parameters = self.patch["output_env"]
        else:
            self._output_envelope = np.ones(np.size(T))
            self._prev_output_env_parameters = default_patch["output_env"]
            
        self._output_with_envelope = np.multiply(self.output,
                                                 self._output_envelope
                                                 )

    def _update_output(self) -> None:
        self.output = addsyn(
            [getattr(chain, 'output') for chain in self.chains]
        )
        self._output_with_envelope = np.multiply(self.output,
                                                 self._output_envelope
                                                 )

    def _update_output_envelope(self) -> None:
        if self.patch["output_env"]:
            self._output_envelope = envelope(*self.patch["output_env"])
            self._prev_output_env_parameters = self.patch["output_env"]
        else:
            self._output_envelope = np.ones(np.size(T))
        self._output_with_envelope = np.multiply(self._output_envelope,
                                                 self.output
                                                 )

    def get_envelope_patch_param(self) -> list[float]:
        """ Gets the envelope parameter in the patch for the
            specified operator, or the output envelope by default.

        Args:
            op: The operator number,
                an integer between 1 and sum(patch["algorithm"]).

        Returns:
            The envelope parameter for the operator if op is specified,
            else the output envelope parameter. The envelope parameter is
            in the form [a, d, s_len, s_level, r] for the envelope function.
        """
        if self.patch["output_env"]:
            return self.patch["output_env"]
        else:
            return self._prev_output_env_parameters

    def has_output_envelope(self) -> bool:
        """ Returns whether the specified operator has an envelope,
        or the output envelope by default.

        Args:
            op: the operator number,
                an integer between 1 and sum(patch["algorithm"]).

        Returns:
            A boolean which is True if the
                 operator/output envelope has an envelope,
                 or False if not.
        """
        return bool(self.patch["output_env"])

    def set_chain_params(self, op_params: list[list], chain_idx: int) -> None:
        """ Updates chain_idx-th chain to values op_params
        and updates patch to these new values

        Args:
            op_params: tuple (freqs, mod_indices, envs, feedbacks)
            chain_idx: the chain being updated
        """
        self.chains[chain_idx].set_new_op_params(op_params)
        param_names = ["freqs", "mod_indices", "envs", "feedback"]
        for i, param_name in enumerate(param_names):
            self.patch[param_name][chain_idx] = op_params[i]
        self._update_output()

    def set_output_envelope(self, vals: list[int | float]) -> None:
        self.patch["output_env"] = vals
        self._update_output_envelope()

    def set_output_envelope_to_prev(self) -> None:
        self.patch["output_env"] = self._prev_output_env_parameters
        self._update_output_envelope()
        
    def play_sound(self) -> None:
        """ Plays the sound of the synth output. """
        with tempfile.NamedTemporaryFile(suffix='.wav') as temp:
            sf.write(temp, self._output_with_envelope, FS)
            os.system(f'aplay {temp.name}')

    def get_envelope_plot_params(self) -> tuple[np.ndarray, np.ndarray]:
        """ Gets x and y values for the envelope plot.
        If an envelope is set, returns the envelope as an np.array,
        otherwise an np.array of ones.
        """
        return T, self._output_envelope

    def get_output_plot_params(self) -> tuple[np.ndarray, np.ndarray]:
        """ Gets x and y parameters for a plot of the output without envelope
        for the first 0.01 seconds, or the output of a chain if specified.

        Args:
            output_num: Which chain output to get the plot parameters for,
              or the output without envelope if 0.

        Returns:
            The x and y parameters for a plot for the first 0.01 seconds.
        """
        return T[0:PLOT_LIM], self.output[0:PLOT_LIM]

    def get_chain_output_plot_params(self, chain_idx: int
                                     ) -> tuple[np.ndarray, np.ndarray]:
        return T[0:PLOT_LIM], self.chains[chain_idx].output[0:PLOT_LIM]

    def save_patch(self, patch_name: str) -> None:
        """ Saves the Synth object's patch attribute in a .json file.

        Args:
            patch_name: The name of the patch, which must be a string.
        """
        with open(patch_name, 'w', encoding="utf-8") as f:
            json.dump(self.patch, f)
        print("patch saved in ", patch_name)


# these will be used if non-sine fm is implemented
def makesine(freq: float) -> np.ndarray:
    """ Returns a sine wave of frequency freq and duration SECONDS.

    Args:
        freq: Frequency.

    Returns:
        A sine wave of frequency freq and duration SECONDS.
    """
    return np.sin(2*np.pi * freq * T)


def makesaw(freq: float) -> np.ndarray:
    """ Returns a saw wave of frequency freq and duration SECONDS.

    Args:
        freq: Frequency.

    Returns:
        A saw wave of frequency freq and duration SECONDS.
    """
    return 2*freq*(T % (1/freq)) - 1


def makesquare(freq: float) -> np.ndarray:
    """ Returns a square wave of frequency freq and duration SECONDS.

    Args:
        freq: Frequency.

    Returns:
        A square wave of frequency freq and duration SECONDS.
    """
    return np.sign(makesine(freq))


def addsyn(waves: list[np.ndarray]) -> np.ndarray:
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

def read_patch(patch_filename: str) -> dict:
    """ Reads a patch from a .json file.

    Args:
        patch_filename: The name of the patch file (including .json).

    Returns:
        The patch read from the file with the name patch_filename in the
          current directory.
    """

    # TODO: no. arguments based on algorithm
    schema = {
        "type": "object",
        "properties": {
            "algorithm": {
                "type": "array",
                "items": {"type": "number"}
            },
            "mod_0": {
                "type": "array",
                "items": {"type": "number"}
            },
            "freqs": {
                "type": "array",
                "items": {"type": "array",
                          "items": {"type": "number"}
                          }
            },
            "mod_indices": {
                "type": "array",
                "items": {"type": "array",
                          "items": {"type": "number"}
                          }
            },
            "feedback": {
                "type": "array",
                "items": {"type": "array",
                          "items": {"type": "number"}
                          }
            },
            "output_env": {
                "type": "array",
                "items": {"type": ["number", "array"]}
            },
            "envs": {
                "type": "array",
                "items": {"type": "array",
                          "items": {"type": ["number", "array"]}
                          }
            }
        },
        "required": ["algorithm", "mod_0", "freqs",
                     "mod_indices", "feedback",
                     "output_env", "envs"
                     ]
    }

    with open(patch_filename, encoding="utf-8") as f:
        patch = json.load(f)
    validate(instance=patch, schema=schema)
    print(patch)
    return patch


def new_patch_algorithm(algorithm: list[int]) -> dict:
    """ given an algorithm, initialises and returns
        a new patch with default values.

    Args:
        algorithm: A list defining the number of operators per chain

    Returns:
        A new patch with default values in
            the right form to be used by the synth.
"""
    n_ops = int(np.sum(algorithm))
    freqs = reshape_list([1.0]*n_ops, algorithm)
    mod_indices = reshape_list([1.0]*n_ops, algorithm)
    envs = reshape_list([[]]*n_ops, algorithm)
    feedback = reshape_list([0]*n_ops, algorithm)
    output_env = []
    mod_0 = [0]*len(algorithm)
    patch = {"freqs": freqs,
             "mod_indices": mod_indices,
             "envs": envs,
             "output_env": output_env,
             "mod_0": mod_0,
             "algorithm": algorithm,
             "feedback": feedback
             }
    print(patch)
    return patch


# -- HELPER METHODS --
def reshape_list(vals: list, algorithm: list[int]) -> list[list]:
    """ Reshapes a list of parameters for each operator into the correct
    format for a patch specified by algorithm.

    E.g., for the algorithm [1, 2, 3] and vals [1, 1, 1, 1, 1, 1],
    reshape_list(vals, algorithm) returns [[1], [1, 1], [1, 1, 1]].

    Args:
        vals: A list of parameter values for each operator. List must be
          the same length as the number of operators, i.e. sum(algorithm).
        algorithm: A list of integers. Each entry specifies an operator chain
          consisting of that many operators.

    Returns:
        new_vals: The list vals formatted according to algorithm as above.
    """
    if len(vals) != sum(algorithm):
        raise ValueError(
            f"vals {vals} not compatible with algorithm {algorithm}"
        )
    new_vals = []
    vals_idx = 0
    for i in algorithm:
        vals_mbr = []
        for _ in range(i):
            vals_mbr.append(vals[vals_idx])
            vals_idx += 1
        new_vals.append(vals_mbr)
    return new_vals
