"""Test suite runner"""

import os
import sys
import logging
from unittest import TestSuite, TestLoader, TextTestRunner
from click import group, argument, option
from zero import set_log_verbosity

from .validation import LisoTestSuite

# this directory
THIS_DIR = os.path.dirname(os.path.realpath(__file__))

# LISO validation scripts
LISO_SCRIPT_DIR = os.path.join(THIS_DIR, "scripts/liso")

# test loader
LOADER = TestLoader()

# test suites
UNIT_TESTS = LOADER.discover("unit", top_level_dir=THIS_DIR)
INTEGRATION_TESTS = LOADER.discover("integration", top_level_dir=THIS_DIR)
FAST_VALIDATION_TESTS = LisoTestSuite(os.path.join(LISO_SCRIPT_DIR, "fast"))
SLOW_VALIDATION_TESTS = LisoTestSuite(os.path.join(LISO_SCRIPT_DIR, "slow"))

# derived suites
VALIDATION_TESTS = TestSuite((FAST_VALIDATION_TESTS, SLOW_VALIDATION_TESTS))
ALL_FAST_TESTS = TestSuite((UNIT_TESTS, INTEGRATION_TESTS, FAST_VALIDATION_TESTS))
ALL_TESTS = TestSuite((ALL_FAST_TESTS, SLOW_VALIDATION_TESTS))

# test name map
TESTS = {
    "unit": UNIT_TESTS,
    "integration": INTEGRATION_TESTS,
    "validation": VALIDATION_TESTS,
    "all-fast": ALL_FAST_TESTS,
    "all": ALL_TESTS
}

@group()
def tests():
    """Zero testing facility."""
    pass

@tests.command()
@argument("suite_names", nargs=-1)
@option("-v", "--verbose", count=True, default=0,
        help="Enable verbose output. Supply extra flag for greater verbosity, i.e. \"-vv\".")
def run(suite_names, verbose):
    """Run test suites."""
    if verbose > 2:
        verbose = 2

    # tune in to zero's logs
    logger = logging.getLogger("zero")
    # show only warnings with no verbosity, or more if higher
    set_log_verbosity(logging.WARNING - 10 * verbose, logger)

    # test suite to run
    suite = TestSuite([TESTS.get(suite_name) for suite_name in suite_names])

    print("Running %i tests" % suite.countTestCases())
    run_and_exit(suite, verbosity=verbose)

@tests.command()
def suites():
    print(", ".join(TESTS))

def run_and_exit(suite, verbosity=1):
    """Run tests and exit with a status code representing the test result"""
    runner = TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())


if __name__ == '__main__':
    tests()
