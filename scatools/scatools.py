"""
Module providing utility functions for data analysis and hardware interaction using ChipWhisperer.

This module includes functions for plotting data, initializing hardware connections,
capturing power traces, compiling and flashing firmware, and computing statistical metrics.
"""

from scipy.stats import norm
import numpy as np
import time
import chipwhisperer as cw
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import pandas as pd
import subprocess
from tqdm.notebook import tqdm, trange

def this():
    """
    Return a simple string.

    Returns
    -------
    str
        The string "Beep Boop".
    """
    return "Beep Boop"

def ph(trace, bins=100, title='Histogram', xlabel='Value', ylabel='Count'):
    """
    Plot a histogram of the given data.

    Parameters
    ----------
    trace : array_like
        Input data to be histogrammed.
    bins : int, optional
        Number of bins for the histogram (default is 100).
    title : str, optional
        Title of the histogram plot (default is 'Histogram').
    xlabel : str, optional
        Label for the x-axis (default is 'Value').
    ylabel : str, optional
        Label for the y-axis (default is 'Count').

    Returns
    -------
    None
    """
    plt.figure(figsize=(10, 6))
    plt.hist(trace, bins=bins, color='skyblue', edgecolor='black')
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.show()


def p(trace):
    """
    Plot the given data using matplotlib.

    Parameters
    ----------
    trace : array_like
        Data to be plotted.

    Returns
    -------
    list
        List of Line2D objects representing the plotted data.
    """
    return plt.plot(trace)

def pi(data, title="Interactive Plot", x_label="Index", y_label="Value", line_color="blue", line_width=2, line_dash="solid", output_file="plot.html"):
    """
    Create and save an interactive plot using Plotly.

    Parameters
    ----------
    data : array_like
        Data to be plotted.
    title : str, optional
        Title of the plot (default is "Interactive Plot").
    x_label : str, optional
        Label for the x-axis (default is "Index").
    y_label : str, optional
        Label for the y-axis (default is "Value").
    line_color : str, optional
        Color of the line (default is "blue").
    line_width : int, optional
        Width of the line (default is 2).
    line_dash : str, optional
        Style of the line (e.g., "solid", "dash") (default is "solid").
    output_file : str, optional
        File name to save the plot HTML (default is "plot.html").

    Returns
    -------
    plotly.graph_objects.Figure
        The Plotly Figure object of the plot.
    """
    import plotly.graph_objects as go
    import plotly.io as pio
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=list(range(len(data))),
        y=data,
        mode='lines',
        line=dict(color=line_color, width=line_width, dash=line_dash),
        name="Data"
    ))

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white"
    )

    pio.write_html(fig, file=output_file, auto_open=False)

    # Return the figure object
    return fig

def init():
    """
    Initialize the ChipWhisperer scope and target.

    Returns
    -------
    tuple
        A tuple containing:
            - scope: The ChipWhisperer scope object.
            - target: The target device object.
            - prog: The programmer object for flashing firmware.
    """
    global prog
    try:
        if not scope.connectStatus:
            scope.con()
    except NameError:
        scope = cw.scope()

    target_type = cw.targets.SimpleSerial2
    try:
        target = cw.target(scope, target_type)
    except:
        print("INFO: Caught exception on reconnecting to target - attempting to reconnect to scope first.")
        print("INFO: This is a work-around when USB has died without Python knowing. Ignore errors above this line.")
        scope = cw.scope()
        target = cw.target(scope, target_type)

    prog = cw.programmers.STM32FProgrammer
    scope.default_setup()
    return scope, target, prog

def reset(scope):
    """
    Reset the target device connected to the scope.

    Parameters
    ----------
    scope : chipwhisperer.scope.Scope
        The ChipWhisperer scope object.

    Returns
    -------
    None
    """
    scope.io.nrst = 'low'
    time.sleep(0.05)
    scope.io.nrst = 'high_z'
    time.sleep(0.05)

def cap_trace(scope, target):
    """
    Capture a power trace from the target device using the ChipWhisperer scope.

    Parameters
    ----------
    scope : chipwhisperer.scope.Scope
        The ChipWhisperer scope object.
    target : chipwhisperer.targets.Target
        The target device object.

    Returns
    -------
    array_like
        The captured power trace data.

    Notes
    -----
    This function arms the scope, resets the target, and captures a power trace.
    It handles any timeout during acquisition by printing a message.
    """
    scope.arm()
    target.flush()
    num_char = target.in_waiting()
    while num_char > 0:
        print(f"Received: {target.read(num_char, 10)}")
        time.sleep(0.01)
        num_char = target.in_waiting()
    reset(scope)
    # target.send_cmd('s', byte_value, bytearray([0x41]*16))
    ret = scope.capture()
    if ret:
        print('Timeout happened during acquisition')

    trace = scope.get_last_trace()
    # returned_data = target.read_cmd('r')
    # print(returned_data)
    return trace

def compile_and_flash(scope, path=".", hex_file="main-CWLITEARM.hex"):
    """
    Compile the firmware using Make and flash it onto the target device.

    Parameters
    ----------
    scope : chipwhisperer.scope.Scope
        The ChipWhisperer scope object.
    path : str, optional
        Path to the directory containing the Makefile (default is ".").
    hex_file : str, optional
        Name of the .hex file to be flashed (default is "main-CWLITEARM.hex").

    Returns
    -------
    None
    """
    subprocess.Popen(["make", "-C", path], stdout=subprocess.PIPE)
    cw.program_target(scope, prog, hex_file)

HW = [bin(n).count("1") for n in range(0, 256)]

def calc_min_traces_needed_for_zero_PGE(attack_results):
    """
    Calculate the minimum number of traces needed to recover the entire correct key
    :param attack_results: Attack results from the CPA attack
    :return: The number of traces needed to get the correct key
    """
    pges = attack_results.pge_total
    earliest_pge = {}

    for pge in pges:
        if pge['pge'] == 0:
            subkey = pge['subkey']
            if subkey not in earliest_pge or pge['trace'] < earliest_pge[subkey]['trace']:
                earliest_pge[subkey] = pge

    # print the number of traces needed to get the correct key
    max_trace = 0
    for pges in earliest_pge.values():
        if pges['trace'] > max_trace:
            max_trace = pges['trace']

    return max_trace