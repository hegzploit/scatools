"""
Basic Module providing utility functions for data analysis and hardware interaction using ChipWhisperer.

This module includes functions for plotting data, initializing hardware connections,
capturing power traces, compiling and flashing firmware, and computing statistical metrics.
AUTHOR: Yusuf Hegazy (@hegzploit)
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
from scalib.metrics import SNR

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

def export_plot_html_embed(fig, file_name):
    fig.write_html(file_name, include_plotlyjs='cdn', full_html=False)

def init(target_type=cw.targets.SimpleSerial2):
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
    global prog, scope
    try:
        if not scope.connectStatus: # type: ignore
            scope.con()
    except NameError:
        scope = cw.scope()

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
    try:
        # Use subprocess.run to wait for completion and check for errors.
        # capture_output=True will capture stdout and stderr.
        result = subprocess.run(["make", "-C", path], check=True, capture_output=True, text=True)
        # You can optionally print result.stdout or result.stderr if needed
        # print(f"Make stdout: {result.stdout}")
        # print(f"Make stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return  # Optionally, re-raise or handle more gracefully

    cw.program_target(scope, prog, hex_file)

def HW(n, bitwidth: int = 32):
    """Hamming weight (popcount) of `n` at the given bit width.

    Vectorized over array-like `n`.
    """
    f = np.vectorize(lambda x: np.binary_repr(x, bitwidth).count("1"))
    return f(n)

SBOX = np.array([
    # 0    1    2    3    4    5    6    7    8    9    a    b    c    d    e    f
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76, # 0
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0, # 1
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15, # 2
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75, # 3
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84, # 4
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf, # 5
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8, # 6
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2, # 7
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73, # 8
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb, # 9
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79, # a
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08, # b
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a, # c
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e, # d
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf, # e
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16  # f
], dtype=np.uint8)

HW_SBOX = HW(SBOX, 8)

def plot_overlayed(data_list, line_names=None, title='Overlayed Line Plots', x_title='Index', y_title='Value'):
    """
    Overlays multiple line plots on the same figure using data from a list of arrays/lists.
    Uses default x-values based on the length of the first y-data.

    Args:
        data_list: A list of arrays/lists, where each element contains the y-values for a line plot.
                   Can be numpy arrays, lists, or any array-like object.
                   All elements should have the same length for default x-values.
        line_names: An optional list of strings specifying the names for each line in the legend.
                    If None, default names ('Line 1', 'Line 2', etc.) will be used.
        title: The title of the plot.
        x_title: The label for the x-axis (defaults to 'Index').
        y_title: The label for the y-axis (defaults to 'Value').
    
    Returns:
        fig: A plotly Figure object that can be shown with .show() or further modified.
    """
    fig = go.Figure()

    if not data_list or len(data_list) == 0:
        print("Warning: Empty data_list provided. No lines will be plotted.")
        fig.show()
        return fig

    # Convert to numpy array for consistent handling
    data_array = np.asarray(data_list[0])
    expected_length = len(data_array)
    default_x = np.arange(expected_length)

    # Generate default line names if not provided
    if line_names is None:
        line_names = [f'Line {i+1}' for i in range(len(data_list))]
    elif len(line_names) != len(data_list):
        raise ValueError("The length of 'line_names' must match the number of lines in 'data_list'.")

    # Add traces for each line
    for i, y_data in enumerate(data_list):
        y_array = np.asarray(y_data)
        
        if len(y_array) != expected_length:
            raise ValueError(
                f"The length of y-data for '{line_names[i]}' ({len(y_array)}) "
                f"does not match the expected length ({expected_length})."
            )
        
        fig.add_trace(go.Scatter(
            x=default_x, 
            y=y_array, 
            mode='lines', 
            name=line_names[i]
        ))

    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title
    )

    return fig

def getSNR_HW(traces, snr_target):
    """
    Calculates the Signal-to-Noise Ratio (SNR) based on Hamming Weight (HW) groups.

    Args:
        traces (np.array): A 2D numpy array where rows are individual traces
                           and columns are samples (time points).
        snr_target (np.array): A 1D array containing the Hamming Weight
                               for each corresponding trace in `traces`.

    Returns:
        np.array: A 1D array containing the SNR for each sample.
                  Returns an array of NaNs if all groups are empty or noise is zero.
    """
    n_traces, n_samples = traces.shape

    # Ensure target_var_hw_values is a NumPy array for efficient indexing
    if not isinstance(snr_target, np.ndarray):
        snr_target = np.array(snr_target)

    # Define the possible HW values (0 to 8 for a byte)
    hw_groups = np.arange(9)

    # Initialize arrays to store group means and variances
    # Using np.nan as a placeholder for groups that might be empty
    # or to handle division by zero later more gracefully.
    group_means = np.full((hw_groups.size, n_samples), np.nan)
    group_vars = np.full((hw_groups.size, n_samples), np.nan)

    # Calculate means and variances for each HW group
    for i, hw_val in enumerate(hw_groups):
        # Create a boolean mask for traces belonging to the current HW group
        mask = (snr_target == hw_val)

        # Check if the current group has any traces
        if np.any(mask):
            traces_in_group = traces[mask]
            group_means[i] = np.mean(traces_in_group, axis=0)
            group_vars[i] = np.var(traces_in_group, axis=0)

    # Calculate signal: variance of the group means
    # np.nanvar will ignore NaNs, which is useful if some groups were empty.
    signal = np.nanvar(group_means, axis=0)

    # Calculate noise: mean of the group variances
    # np.nanmean will ignore NaNs.
    noise = np.nanmean(group_vars, axis=0)

    # Calculate SNR
    # Handle potential division by zero or NaN noise
    # If noise is zero (or NaN), SNR is undefined (or should be handled as NaN/inf).
    # We'll set SNR to 0 where noise is 0 and signal is also 0, and NaN otherwise.
    snr = np.full_like(noise, np.nan)

    # Valid noise (non-zero and not NaN)
    valid_noise_mask = (noise != 0) & (~np.isnan(noise))
    snr[valid_noise_mask] = signal[valid_noise_mask] / noise[valid_noise_mask]

    # Where signal is 0 and noise is 0, SNR can be considered 0 (no signal, no noise variation)
    # Or, depending on the context, it might still be NaN or Inf. Here, let's set to 0.
    # This case is often debatable. For side-channel, if signal is 0, SNR is 0.
    zero_signal_zero_noise_mask = (signal == 0) & (noise == 0) & (~np.isnan(noise)) # ensure noise was not originally NaN
    snr[zero_signal_zero_noise_mask] = 0

    return snr

def getSNR(traces, snr_target):
    # Ensure target is at least 2D for libraries that expect (N, M)
    if snr_target.ndim == 1:
        snr_target = snr_target.reshape(-1, 1)
        
    # Dynamically determine nc based on targets
    # Note: If nc is very large, consider a different leakage model
    num_classes = int(snr_target.max()) + 1
    snr = SNR(nc=num_classes, use_64bit=True)
    
    # Use float32 for traces to preserve precision unless 
    # the specific SNR implementation requires integers.
    # Use .astype() only if you are certain of the data range.
    snr.fit_u(traces, snr_target.astype(np.uint16))
    return snr.get_snr()[0]

def float_to_int16(traces):
    # 1. Find the global max/min to keep scaling consistent across all traces
    t_min, t_max = traces.min(), traces.max()
    
    # 2. Map the range to [-1, 1] then scale to int16 range
    # We use 32767 to avoid overflow
    traces_normalized = 2 * (traces - t_min) / (t_max - t_min) - 1
    traces_int16 = (traces_normalized * 32767).astype(np.int16)
    
    return traces_int16

def plot_overlayed_alpha(
    traces,
    *,
    alpha: float = 0.05,
    linewidth: float = 0.9,
    color: str = "black",
    figsize: tuple = (12, 6),
    dpi: int = 150,
    xlabel: str = "Sample index",
    ylabel: str = "Amplitude",
    title: str | None = None,
):
    """
    Overlay several 1-D traces on a single plot.

    Parameters
    ----------
    traces : (N, M)‐array-like
        Collection of N traces, each of length M.
    alpha : float, default 0.05
        Opacity per trace (lower → darker regions where many traces overlap).
    linewidth : float, default 1.0
        Width of each trace’s line.
    color : str, default 'black'
        Color for all traces.
    figsize : tuple, default (12, 6)
        Figure size in inches.
    dpi : int, default 150
        Figure resolution.
    xlabel, ylabel : str
        Axis labels.
    title : str, optional
        Custom title.  If None, a title is auto-generated.

    Returns
    -------
    matplotlib.figure.Figure
        The created figure (so you can tweak it further if needed).
    """
    traces = np.asarray(traces)

    fig = plt.figure(figsize=figsize, dpi=dpi)
    for tr in traces:
        plt.plot(tr, alpha=alpha, color=color, linewidth=linewidth)

    if title is None:
        title = f"Overlay of {traces.shape[0]} traces (α = {alpha})"
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()

    return fig
