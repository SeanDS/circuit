import os.path
import glob
import numpy as np
import unittest
import logging

from circuit.liso import Runner

LOGGER = logging.getLogger("test")

# directory containing tests relative to this script
REL_FIL_DIR = "."

class LisoTester(unittest.TestCase):
    def __init__(self, method_name, fil_path=None):
        super(LisoTester, self).__init__(method_name)

        self.fil_path = fil_path

    def test_liso_vs_native(self):
        self.compare(self._liso_output())

    def compare(self, liso_output):
        # get LISO solution
        liso_solution = liso_output.solution()

        # run native
        native_solution = liso_output.run_native()

        # check if they match
        self.assertEqual(liso_solution, native_solution)

    def _liso_output(self):
        # run LISO and parse output
        LOGGER.info("Testing %s (%s)", self.fil_path, self.description)
        return Runner(self.fil_path).run()

    @property
    def description(self):
        """LISO file top comment, if any"""

        text = ""

        with open(self.fil_path, "r") as obj:
            next_line = obj.readline()

            while next_line.startswith("#"):
                text += next_line.lstrip("#")

                # read next line
                next_line = obj.readline()

        if text == "":
            text = "no description"
        else:
            # remove extra whitespace, newlines, etc. if present
            text = "\"" + text.strip() + "\""

        return text

def fil_scripts():
    return glob.glob(os.path.join(fil_dir(), "*.fil"))

def fil_dir():
    this_script_dir = os.path.dirname(os.path.realpath(__file__))

    return os.path.abspath(os.path.join(this_script_dir, REL_FIL_DIR))

def load_tests(loader, tests, pattern):
    test_cases = unittest.TestSuite()

    for script in fil_scripts():
        test_cases.addTest(LisoTester("test_liso_vs_native", script))

    return test_cases

if __name__ == '__main__':
    unittest.main()