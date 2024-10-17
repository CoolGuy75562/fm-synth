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
        expected = [[1, 2, 3], 4, [5, 6]]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
    def test_single_chains(self):
        vals = [1, 2, 3, 4, 5, 6]
        algorithm = [1, 1, 1, 1, 1, 1]
        expected = [1, 2, 3, 4, 5, 6]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
    def test_small_algorithms(self):
        vals = [1, 2]
        algorithm = [1, 1]
        expected = [1, 2]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
        algorithm = [2]
        expected = [[1, 2]]
        self.assertEqual(fm.reshape_list(vals, algorithm), expected)
        vals = [1]
        algorithm = [1]
        expected = [1]
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
    def test_new_patch_algorithm(self):

        output_env = 1
        
        # test for algorithm [2, 2, 2]
        alg1 = [2, 2, 2]
        
        freqs1 = [[1, 1], [1, 1], [1, 1]]
        mod_indices1 = freqs1
        envs1 = freqs1
        feedback1 = [[0,0], [0,0], [0,0]]
 
        mod_01 = [0, 0, 0]
        output_env = 1
        patch1 = {"freqs" : freqs1,
                  "mod_indices" : mod_indices1,
                  "envs" : envs1,
                  "output_env" : output_env,
                  "mod_0" : mod_01,
                  "algorithm" : alg1,
                  "feedback" : feedback1
             }
        self.assertEqual(fm.new_patch_algorithm(alg1), patch1)

        # test for algorithm [1, 2, 3]
        alg2 = [1, 2, 3]
        
        freqs2 = [1, [1, 1], [1, 1, 1]]
        mod_indices2 = freqs2
        envs2 = freqs2
        feedback2 = [0, [0,0], [0,0,0]]
        mod_02 = [0, 0, 0]

        patch2 = {"freqs" : freqs2,
                  "mod_indices" : mod_indices2,
                  "envs" : envs2,
                  "output_env" : output_env,
                  "mod_0" : mod_02,
                  "algorithm" : alg2,
                  "feedback" : feedback2
             }
        self.assertEqual(fm.new_patch_algorithm(alg2), patch2)

        # test for algorithm [1, 1, 1]

        alg3 = [1, 1, 1]

        freqs3 = [1, 1, 1]
        mod_indices3 = freqs3
        envs3 = freqs3
        feedback3 = [0, 0, 0]
        mod_03 = [0, 0, 0]
        patch3 = {"freqs" : freqs3,
                  "mod_indices" : mod_indices3,
                  "envs" : envs3,
                  "output_env" : output_env,
                  "mod_0" : mod_03,
                  "algorithm" : alg3,
                  "feedback" : feedback3
             }
        self.assertEqual(fm.new_patch_algorithm(alg3), patch3)

        # test for algorithm [1]

        alg4 = [1]

        freqs4 = [1]
        mod_indices4 = freqs4
        envs4 = freqs4
        feedback4 = [0]
        mod_04 = [0]
        patch4 = {"freqs" : freqs4,
                  "mod_indices" : mod_indices4,
                  "envs" : envs4,
                  "output_env" : output_env,
                  "mod_0" : mod_04,
                  "algorithm" : alg4,
                  "feedback" : feedback4
             }
        self.assertEqual(fm.new_patch_algorithm(alg4), patch4)

        # test for algorithm [2]

        alg5 = [2]

        freqs5 = [[1,1]]
        mod_indices5 = freqs5
        envs5 = freqs5
        feedback5 = [[0,0]]
        mod_05 = [0]
        patch5 = {"freqs" : freqs5,
                  "mod_indices" : mod_indices5,
                  "envs" : envs5,
                  "output_env" : output_env,
                  "mod_0" : mod_05,
                  "algorithm" : alg5,
                  "feedback" : feedback5
             }
        self.assertEqual(fm.new_patch_algorithm(alg5), patch5)

class TestSynth(unittest.TestCase):
    
    def setUp(self):
        default_patch = {"freqs" : [[14, 1], [1, 1], [1, 1]],
                 "mod_indices" : [[0, 58/99], [0, 89/99], [0,79/99]],
                 "envs" : [[1, 1], [1, 1], [1, 1]],
                 "output_env" : [0.0125, 0.025, 0.15, 0.7, 0.05],
                 "mod_0" : [0, 0, 0],
                 "algorithm" : [2, 2, 2],
                 "feedback" : [[0, 0], [0, 0], [0, 0]]
                 }
        self.synth = fm.Synth(default_patch)

    def test_synth_outputs(self):
        self.assertEqual(len(getattr(self.synth, 'chain_outputs')), 3)
        
if __name__ == '__main__':
    unittest.main()
