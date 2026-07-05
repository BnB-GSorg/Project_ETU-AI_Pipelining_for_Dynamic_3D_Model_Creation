"""

Author: MCHIGM

Created: 2nd July, 2026

Modified: 5th July, 2026, MCHIGM

"""


# =============
# 1. Import Libraries
# =============


import os
import lib
# import imp # removed
# import ctypes
import pprint, typing, statistics, doctest, unittest, cProfile, pdb, trace, timeit, tracemalloc, dis, inspect, sysconfig # DeBugging use, please remove before packaging

default_installation_path = os.path.join(os.path.dirname(__file__), '..', '.venv')

lib.install_from_OS()

