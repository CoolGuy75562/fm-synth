""" Tests for the gui module. """
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

import unittest
import gui


class TestAlgorithmDialog(unittest.TestCase):

    def test_algorithm_dialog_output(self):
        dialog = gui.AlgorithmDialog()
        for entry in dialog.chain_entries:
            self.assertEqual(entry.get_value(), 2)
