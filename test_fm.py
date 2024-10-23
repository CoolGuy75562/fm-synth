import unittest
import fm
import numpy as np

class TestEnvelope(unittest.TestCase):

    def test_typical_envelope_size(self):
        a, d, s_len, s_level, r  = 0.2, 0.2, 0.2, 0.5, 0.1
        expected = np.size(fm.T)
        self.assertEqual(np.size(fm.envelope(a,d,s_len,s_level,r)), expected)
        
    def test_long_envelope_size(self):
        a, d, s_len, s_level, r  = 0.2, 0.2, 0.2, 0.5, fm.SECONDS # 0.2 + 0.2 + 0.2 + SECONDS > SECONDS
        expected = np.size(fm.T)
        self.assertEqual(np.size(fm.envelope(a,d,s_len,s_level,r)), expected)
        
    def test_zero_envelope_size(self):
        expected = np.size(fm.T)
        self.assertEqual(np.size(fm.envelope(0,0,0,0,0)), expected)

    def test_sus_level_out_of_bounds(self):
        a, d, s_len, r = 0.2, 0.2, 0.2, 0.1
        with self.assertRaises(ValueError):
            fm.envelope(a, d, s_len, -1, r)
        with self.assertRaises(ValueError):
            fm.envelope(a, d, s_len, 2, r)
    
class TestReshapeList(unittest.TestCase):

    def test_equal_chain_lengths(self):
        vals = [1, 2, 3, 4, 5, 6]
        algorithm = [2, 2, 2]
        expected = [[1, 2], [3, 4], [5, 6]]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
        
    def test_different_chain_lengths(self):
        vals = [1, 2, 3, 4, 5, 6]
        algorithm = [3, 1, 2]
        expected = [[1, 2, 3], [4], [5, 6]]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
        
    def test_single_chains(self):
        vals = [1, 2, 3, 4, 5, 6]
        algorithm = [1, 1, 1, 1, 1, 1]
        expected = [[1], [2], [3], [4], [5], [6]]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
        
    def test_small_algorithms(self):
        vals = [1, 2]
        algorithm = [1, 1]
        expected = [[1], [2]]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
        
        algorithm = [2]
        expected = [[1, 2]]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
        
        vals = [1]
        algorithm = [1]
        expected = [[1]]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
        
    def test_incompatible_args_raises_error(self):
        vals = [1, 2, 3, 4, 5]
        algorithm = [2, 2, 2]
        with self.assertRaises(ValueError):
            fm.reshape_list(vals, algorithm)
            
        vals = [1, 2, 3, 4, 5, 6, 7]
        with self.assertRaises(ValueError):
            fm.reshape_list(vals, algorithm)

class TestNewPatchAlgorithm(unittest.TestCase):

    def test_equal_chain_lengths(self):
        output_env = []
        alg = [2, 2, 2]
        freqs = [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]]
        mod_indices = freqs
        envs = [[[], []], [[], []], [[], []]]
        feedback = [[0,0], [0,0], [0,0]]
        mod_0 = [0, 0, 0]
        expected_patch = {"freqs" : freqs,
                 "mod_indices" : mod_indices,
                 "envs" : envs,
                 "output_env" : output_env,
                 "mod_0" : mod_0,
                 "algorithm" : alg,
                 "feedback" : feedback
                 }
        self.assertEqual(fm.new_patch_algorithm(alg), expected_patch)

    def test_different_chain_lengths(self):
        output_env = []
        alg = [1, 2, 3]
        freqs = [[1.0], [1.0, 1.0], [1.0, 1.0, 1.0]]
        mod_indices = freqs
        envs = [[[]], [[], []], [[], [], []]]
        feedback = [[0], [0,0], [0,0,0]]
        mod_0 = [0, 0, 0]
        expected_patch = {"freqs" : freqs,
                          "mod_indices" : mod_indices,
                          "envs" : envs,
                          "output_env" : output_env,
                          "mod_0" : mod_0,
                          "algorithm" : alg,
                          "feedback" : feedback
                          }
        self.assertEqual(fm.new_patch_algorithm(alg), expected_patch)

    def test_single_chains(self):
        output_env = []
        alg = [1, 1, 1]
        freqs = [[1.0], [1.0], [1.0]]
        mod_indices = freqs
        envs = [[[]], [[]], [[]]]
        feedback = [[0], [0], [0]]
        mod_0 = [0, 0, 0]
        expected_patch = {"freqs" : freqs,
                 "mod_indices" : mod_indices,
                 "envs" : envs,
                 "output_env" : output_env,
                 "mod_0" : mod_0,
                 "algorithm" : alg,
                 "feedback" : feedback
                 }
        self.assertEqual(fm.new_patch_algorithm(alg), expected_patch)

    def test_small_algorithms(self):
        output_env = []
        alg = [1]
        freqs = [[1.0]]
        mod_indices = freqs
        envs = [[[]]]
        feedback = [[0]]
        mod_0 = [0]
        expected_patch = {"freqs" : freqs,
                          "mod_indices" : mod_indices,
                          "envs" : envs,
                          "output_env" : output_env,
                          "mod_0" : mod_0,
                          "algorithm" : alg,
                          "feedback" : feedback
                          }
        self.assertEqual(fm.new_patch_algorithm(alg), expected_patch)

        alg = [2]
        freqs = [[1.0,1.0]]
        mod_indices = freqs
        envs = [[[], []]]
        feedback = [[0,0]]
        mod_0 = [0]
        expected_patch = {"freqs" : freqs,
                 "mod_indices" : mod_indices,
                 "envs" : envs,
                 "output_env" : output_env,
                 "mod_0" : mod_0,
                 "algorithm" : alg,
                 "feedback" : feedback
                 }
        self.assertEqual(fm.new_patch_algorithm(alg), expected_patch)

if __name__ == '__main__':
    unittest.main()
