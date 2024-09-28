import unittest
import gui
import fm

class TestAlgorithmDialog(unittest.TestCase):

    def test_algorithm_dialog_output(self):
        
        algorithm_dialog = gui.AlgorithmDialog()
        algorithm_dialog.chain1_entry.set_text("1")
        algorithm = algorithm_dialog.run()
        algorithm_dialog.destroy()
        self.assertEqual(algorithm, [1])
        
        algorithm_dialog = gui.AlgorithmDialog()
        algorithm_dialog.chain1_entry.set_text("1")
        algorithm_dialog.chain2_entry.set_text("2")
        algorithm_dialog.chain3_entry.set_text("3")
        algorithm = algorithm_dialog.run()
        algorithm_dialog.destroy()
        self.assertEqual(algorithm, [1, 2, 3])
