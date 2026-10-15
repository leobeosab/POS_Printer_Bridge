"""
Pytest configuration for the POS Printer Bridge test suite.
"""

import os
import sys

# Make ``src`` importable so tests can use ``from utils.markdown import ...``.
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
