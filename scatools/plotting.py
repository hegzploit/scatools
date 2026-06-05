"""Live-updating plots for incremental SCA capture loops.

Inspired by ``livelossplot``: collect data point-by-point, refresh the
figure in-place every ``refresh_every`` updates.  In a Jupyter
notebook the same output cell is updated via ``display_id`` so an
external ``tqdm`` progress bar keeps working alongside the plot.

Typical usage::

    from scatools.plotting import LiveSNR, capture_live_snr

    # Manual loop:
    live = LiveSNR()
    for op in tqdm(ops):
        trace, target = cap_trace(op)
        live.update(trace, target)
    traces, targets = live.finalize()

    # Or, the one-shot helper:
    traces, targets, _ = capture_live_snr(ops, cap_trace)
"""
from typing import Any, Callable, Iterable, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
from tqdm.auto import tqdm

from .scatools import getSNR, float_to_int16


# ---------- environment detection ----------

def _detect_mode() -> str:
    """Return ``"notebook"`` or ``"script"`` based on the IPython shell."""
    try:
        from IPython import get_ipython
        ip = get_ipython()
        if ip is None:
            return "script"
        cls = ip.__class__.__name__
        if cls in ("ZMQInteractiveShell", "Shell"):
            return "notebook"
        return "script"
    except ImportError:
        return "script"


# ---------- live SNR plotter ----------

class LiveSNR:
    """Accumulate traces+targets and live-update a per-sample SNR plot.

    Parameters
    ----------
    snr_fn : callable, default :func:`scatools.scatools.getSNR`
        scalib-backed grouped SNR.  Signature
        ``(traces, targets) -> 1D ndarray`` of length ``n_samples``.
        Swap in :func:`scatools.scatools.getSNR_HW` for the
        Hamming-weight-grouped variant.
    refresh_every : int, default 10
        Recompute and redraw every ``refresh_every`` calls to
        :meth:`update`.
    min_traces : int, default 4
        Skip the first redraws until this many traces are collected,
        otherwise SNR is unstable / undefined.
    figsize : (int, int), default (12, 4)
        Matplotlib figure size.
    title, xlabel, ylabel : str
        Plot annotations.  ``title`` is appended with ``(N=<count>)``.
    mode : {"notebook", "script", None}
        Force a display mode.  ``None`` auto-detects from IPython.
    convert_int16 : bool, default True
        If ``True`` and accumulated traces are floats, normalize and
        scale them to ``int16`` (via :func:`float_to_int16`) before
        passing to ``snr_fn``.  Required for scalib's ``SNR.fit_u``;
        harmless for the pure-numpy :func:`getSNR_HW`.
    """

    def __init__(
        self,
        snr_fn: Callable = getSNR,
        refresh_every: int = 10,
        min_traces: int = 4,
        figsize: Tuple[int, int] = (12, 4),
        title: str = "Live SNR",
        xlabel: str = "Sample index",
        ylabel: str = "SNR",
        mode: Optional[str] = None,
        convert_int16: bool = True,
    ):
        self.snr_fn = snr_fn
        self.refresh_every = max(1, int(refresh_every))
        self.min_traces = max(2, int(min_traces))
        self.figsize = figsize
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.mode = mode if mode is not None else _detect_mode()
        self.convert_int16 = convert_int16

        self._traces: list = []
        self._targets: list = []
        self._step: int = 0

        # Notebook display handle (for in-place updates via display_id).
        self._handle = None
        # Script-mode persistent figure/axes/line.
        self._fig = None
        self._ax = None
        self._line = None

    # ---- accumulator views ----

    @property
    def traces(self) -> np.ndarray:
        return np.asarray(self._traces)

    @property
    def targets(self) -> np.ndarray:
        return np.asarray(self._targets)

    @property
    def step(self) -> int:
        return self._step

    # ---- ingestion ----

    def update(self, trace, target) -> None:
        """Append one ``(trace, target)`` pair and refresh if due."""
        self._traces.append(np.asarray(trace))
        self._targets.append(target)
        self._step += 1
        if (self._step >= self.min_traces
                and self._step % self.refresh_every == 0):
            self.send()

    # ---- drawing ----

    def _compute_snr(self) -> np.ndarray:
        traces = np.asarray(self._traces)
        targets = np.asarray(self._targets)
        # scalib's SNR.fit_u requires int16 traces.  ChipWhisperer
        # captures are float, so naive .astype(int16) collapses small
        # values to zero -- use the package's normalize-then-quantize
        # helper instead.
        if self.convert_int16 and np.issubdtype(traces.dtype, np.floating):
            traces = float_to_int16(traces)
        return self.snr_fn(traces, targets)

    def send(self) -> None:
        """Force a recompute + redraw (no-op below ``min_traces``)."""
        if len(self._traces) < self.min_traces:
            return
        snr = self._compute_snr()
        if self.mode == "notebook":
            self._send_notebook(snr)
        else:
            self._send_script(snr)

    def _send_notebook(self, snr: np.ndarray) -> None:
        from IPython.display import display
        fig, ax = plt.subplots(figsize=self.figsize)
        ax.plot(snr, color="tab:blue", linewidth=0.9)
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)
        ax.set_title(f"{self.title}  (N={len(self._traces)})")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        # Close before display() so the figure isn't auto-rendered twice
        # (once as a side effect of the cell, once via display()).
        plt.close(fig)
        if self._handle is None:
            self._handle = display(fig, display_id=True)
        else:
            self._handle.update(fig)

    def _send_script(self, snr: np.ndarray) -> None:
        if self._fig is None:
            plt.ion()
            self._fig, self._ax = plt.subplots(figsize=self.figsize)
            self._line, = self._ax.plot(
                snr, color="tab:blue", linewidth=0.9,
            )
            self._ax.set_xlabel(self.xlabel)
            self._ax.set_ylabel(self.ylabel)
            self._ax.grid(True, alpha=0.3)
        else:
            self._line.set_data(np.arange(len(snr)), snr)
            self._ax.relim()
            self._ax.autoscale_view()
        self._ax.set_title(f"{self.title}  (N={len(self._traces)})")
        self._fig.canvas.draw_idle()
        plt.pause(0.01)

    # ---- finalization ----

    def finalize(self) -> Tuple[np.ndarray, np.ndarray]:
        """Final redraw and return ``(traces, targets)`` as ndarrays."""
        self.send()
        return self.traces, self.targets


# ---------- one-shot capture helper ----------

def capture_live_snr(
    ops: Iterable,
    capture_fn: Callable[[Any], Any],
    target_fn: Optional[Callable[[Any], Any]] = None,
    *,
    snr_fn: Callable = getSNR,
    refresh_every: int = 10,
    min_traces: int = 4,
    progress: bool = True,
    n_mean_traces_count: int = 1,
    **plot_kwargs,
) -> Tuple[np.ndarray, np.ndarray, LiveSNR]:
    """Drive a capture loop with a live-updating SNR plot.

    ``capture_fn(op)`` may return either:

    * a single trace -- in which case ``target_fn(op)`` must be
      provided to derive the SNR grouping label, or
    * a ``(trace, target)`` tuple -- which is used as-is.

    Mirrors the user's manual pattern::

        traces = []
        for op in tqdm(ops):
            t = cap_trace(op)[0]
            traces.append(t)

    Parameters
    ----------
    ops : iterable
        Inputs driving each capture.
    capture_fn : callable
        ``op -> trace`` or ``op -> (trace, target)``.
    target_fn : callable, optional
        ``op -> target``; required when ``capture_fn`` returns just a
        trace.
    snr_fn, refresh_every, min_traces, **plot_kwargs
        Forwarded to :class:`LiveSNR`.
    progress : bool, default True
        Wrap the loop in ``tqdm``.
    n_mean_traces_count : int, default 1
        Number of times to repeat ``capture_fn(op)`` for each ``op``
        before advancing to the next input.  The captured traces are
        averaged (mean) and the mean is fed to the live SNR.  Useful
        for noise reduction on a fixed input.  The target from the
        first repeat is used (it should be deterministic in ``op``).

    Returns
    -------
    traces : ndarray, shape (N, n_samples)
    targets : ndarray, shape (N, ...)
    plotter : LiveSNR
        The plotter (held for further inspection / saving).
    """
    if n_mean_traces_count < 1:
        raise ValueError("n_mean_traces_count must be >= 1")

    def _one(op):
        out = capture_fn(op)
        if isinstance(out, tuple):
            trace, target = out
        else:
            if target_fn is None:
                raise ValueError(
                    "capture_fn returned a single value; either have it "
                    "return (trace, target), or pass target_fn(op)."
                )
            trace, target = out, target_fn(op)
        return np.asarray(trace), target

    live = LiveSNR(
        snr_fn=snr_fn,
        refresh_every=refresh_every,
        min_traces=min_traces,
        **plot_kwargs,
    )
    iterator = tqdm(ops) if progress else ops
    for op in iterator:
        if n_mean_traces_count == 1:
            trace, target = _one(op)
        else:
            reps = [_one(op) for _ in range(n_mean_traces_count)]
            trace = np.mean([t for t, _ in reps], axis=0)
            target = reps[0][1]
        live.update(trace, target)
    traces, targets = live.finalize()
    return traces, targets, live
