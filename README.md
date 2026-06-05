# scatools

A small collection of utilities for **side-channel analysis (SCA)** with
[ChipWhisperer](https://chipwhisperer.readthedocs.io/) — capturing power traces,
computing SNR, fitting and comparing leakage models, talking to serial targets,
and quick interactive plotting.

> Author: Yusuf Hegazy ([@hegzploit](https://github.com/hegzploit))

## Installation

With [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv add git+https://github.com/hegzploit/scatools
```

With pip:

```bash
pip install git+https://github.com/hegzploit/scatools
```

Or, for local development:

```bash
git clone https://github.com/hegzploit/scatools
cd scatools
uv pip install -e .
```

> **Note:** `scatools` pulls in `chipwhisperer` and `scalib`. These are needed
> for hardware capture and SNR computation respectively. If you only need the
> leakage-model harness or plotting, you can still import those submodules, but
> the top-level package import requires the full dependency set.

## Quick start

```python
import scatools as sca

# --- Hardware: capture power traces with ChipWhisperer ---
scope, target = sca.init()
traces, plaintexts = sca.cap_trace(scope, target, N=5000)

# --- Compile + flash firmware to the target ---
sca.compile_and_flash("path/to/firmware-project", platform="CWLITEARM")

# --- Analysis: signal-to-noise ratio ---
snr = sca.getSNR(traces, labels)          # generic SNR
snr_hw = sca.getSNR_HW(traces, intermediates)  # Hamming-weight SNR

# --- Quick plots ---
sca.p(traces[0])               # line plot
sca.ph(traces[0])              # histogram
sca.plot_overlayed(traces[:50])
```

## Modules

| Module | What it gives you |
| --- | --- |
| `scatools` | Hardware setup (`init`, `reset`, `cap_trace`, `compile_and_flash`), SNR (`getSNR`, `getSNR_HW`), leakage constants (`HW`, `SBOX`, `HW_SBOX`), and plotting helpers (`p`, `ph`, `pi`, `plot_overlayed`, `plot_overlayed_alpha`, `export_plot_html_embed`). |
| `scatools.leakage_models` | Lightweight harness for building, fitting, and comparing linear leakage models: `LeakageModel`, `FitResult`, `Comparison`, `fit`, `compare`, `group_magnitudes`, `plot_coeffs`, `cross_run_table`, `plot_cross_run`. |
| `scatools.serial_target` | `Target` — a small pwntools-style serial wrapper (`send`, `recvn`, `recvuntil`, `clean`, `close`) for non-ChipWhisperer targets. |
| `scatools.plotting` | `LiveSNR` and `capture_live_snr` for refreshing an SNR plot point-by-point during a capture. |

### Leakage-model comparison

```python
import numpy as np
from scatools import leakage_models as lm

model = lm.LeakageModel(
    name="hw-model",
    groups=[("sbox_hw", hw_features)],   # (label, (N, k) ndarray)
)

cmp = lm.compare(model, traces)          # returns a named Comparison
lm.plot_coeffs(cmp)
lm.plot_cross_run([cmp_a, cmp_b])        # line up multiple runs
```

### Serial target

```python
from scatools import Target

t = Target("/dev/ttyUSB0", baudrate=115200)
t.send(b"\x01" + plaintext)
resp = t.recvn(16)
t.close()
```

## Development

```bash
git clone https://github.com/hegzploit/scatools
cd scatools
uv sync                 # create venv + install deps
uv pip install -e .     # editable install
```

See [`example.ipynb`](example.ipynb) for a worked end-to-end notebook.

## License

[MIT](LICENSE)
