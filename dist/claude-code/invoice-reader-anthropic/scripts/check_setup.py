# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Confirm that the scripts can run. If uv got this far, Python and the packages are in place."""

import sys

import openpyxl

print(f"Ready: Python {sys.version.split()[0]}, openpyxl {openpyxl.__version__}.")
