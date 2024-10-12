import unittest
import gui
import fm

class TestAlgorithmDialog(unittest.TestCase):

    def test_algorithm_dialog_output(self):

        dialog = gui.AlgorithmDialog()
        for entry in dialog.chain_entries:
            self.assertEqual(entry.get_value(), 2)
            
