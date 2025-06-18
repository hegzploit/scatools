"""
scatools - A collection of tools for side-channel analysis.

This package provides utility functions for data analysis, hardware interaction,
plotting, and more, related to side-channel attacks.
"""

# Import functions and constants from submodules to make them available
# directly under the 'scatools' namespace.

# from .constants import HW, SBOX, HW_SBOX
# from .plotting import ph, p, pi, export_plot_html_embed, plot_overlayed
# from .hardware import init, reset, cap_trace, compile_and_flash
# from .analysis import calc_min_traces_needed_for_zero_PGE, getSNR_HW, getSNR
# from .scatools import this

# You can define __all__ to specify what is exported when a user does `from scatools import *`
# For example:
# __all__ = [
#     "HW", "SBOX", "HW_SBOX",
#     "ph", "p", "pi", "export_plot_html_embed", "plot_overlayed",
#     "init", "reset", "cap_trace", "compile_and_flash",
#     "calc_min_traces_needed_for_zero_PGE", "getSNR_HW", "getSNR",
#     "this"
# ]

# Optionally, set a version for your package
__version__ = "0.1.1" # Or whatever version you deem appropriate after refactoring
