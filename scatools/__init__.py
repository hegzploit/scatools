"""
scatools - A collection of tools for side-channel analysis.

This package provides utility functions for data analysis, hardware interaction,
plotting, and more, related to side-channel attacks.
"""

# Import functions and constants from submodules to make them available
# directly under the 'scatools' namespace.

# Import functions and constants from submodules to make them available
# directly under the 'scatools' namespace.

# Since all code is currently in scatools.py, we import from there.
# If you later split scatools.py into constants.py, plotting.py, etc.,
# you would change these imports accordingly.
from .scatools import (
    this,
    ph,
    p,
    pi,
    export_plot_html_embed,
    init,
    reset,
    cap_trace,
    compile_and_flash,
    HW,
    SBOX,
    HW_SBOX,
    calc_min_traces_needed_for_zero_PGE,
    plot_overlayed,
    getSNR_HW,
    getSNR
)

# You can define __all__ to specify what is exported when a user does `from scatools import *`
__all__ = [
    "this",
    "ph", "p", "pi", "export_plot_html_embed", "plot_overlayed",  # Plotting
    "init", "reset", "cap_trace", "compile_and_flash",  # Hardware
    "HW", "SBOX", "HW_SBOX",  # Constants
    "calc_min_traces_needed_for_zero_PGE", "getSNR_HW", "getSNR",  # Analysis
]

# Optionally, set a version for your package
__version__ = "0.1.1" # Or whatever version you deem appropriate after refactoring
