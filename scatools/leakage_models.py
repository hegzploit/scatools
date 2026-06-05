"""Lightweight harness for comparing linear leakage models.

Each model is a named sequence of feature groups (label, (N, k) array).
Each `compare()` call produces a named `Comparison` you can hold onto,
plot, and line up against other runs with `plot_cross_run`.
"""
from dataclasses import dataclass, field
from typing import Sequence
import numpy as np
import matplotlib.pyplot as plt


# ---------- model + single-fit ----------

@dataclass
class LeakageModel:
    name: str
    groups: Sequence[tuple[str, np.ndarray]]  # [(label, (N, k) ndarray), ...]

    def design_matrix(self) -> np.ndarray:
        mats = [m for _, m in self.groups]
        n = mats[0].shape[0]
        return np.hstack([*mats, np.ones((n, 1))])

    @property
    def widths(self) -> list[int]:
        return [m.shape[1] for _, m in self.groups]

    @property
    def labels(self) -> list[str]:
        return [lbl for lbl, _ in self.groups]


@dataclass
class FitResult:
    model: LeakageModel
    coeffs: np.ndarray   # includes intercept as last element
    r2: float
    y_pred: np.ndarray


def fit(model: LeakageModel, y: np.ndarray) -> FitResult:
    A = model.design_matrix()
    coeffs, *_ = np.linalg.lstsq(A, y, rcond=None)
    y_pred = A @ coeffs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return FitResult(model, coeffs, float(1.0 - ss_res / ss_tot), y_pred)


def group_magnitudes(result: FitResult) -> dict[str, float]:
    coeffs = np.abs(result.coeffs[:-1])
    out, i = {}, 0
    for lbl, w in zip(result.model.labels, result.model.widths):
        out[lbl] = float(coeffs[i:i + w].sum())
        i += w
    return out


# ---------- comparison bundle ----------

@dataclass
class Comparison:
    """One named experimental condition (a POI, dataset slice, etc.)."""
    name: str
    results: list[FitResult]
    meta: dict = field(default_factory=dict)   # e.g. {"poi": 123, "N": 1_000_000}

    def __repr__(self) -> str:
        return (f"Comparison(name={self.name!r}, "
                f"n_models={len(self.results)}, meta={self.meta})")

    @property
    def meta_str(self) -> str:
        return "  ".join(f"{k}={v}" for k, v in self.meta.items())

    @property
    def header(self) -> str:
        return f"=== {self.name} ===" + (f"   [{self.meta_str}]" if self.meta else "")

    def best(self) -> FitResult:
        return max(self.results, key=lambda r: r.r2)

    def r2_by_model(self) -> dict[str, float]:
        return {r.model.name: r.r2 for r in self.results}


# ---------- plotting ----------

_COLORS = ["red", "gold", "magenta", "cyan", "limegreen", "orange"]


def plot_coeffs(result: FitResult, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(15, 4))
    coeffs = result.coeffs[:-1]
    ax.bar(range(len(coeffs)), np.abs(coeffs))

    boundaries = np.cumsum(result.model.widths)[:-1]
    labels = result.model.labels
    for i, b in enumerate(boundaries):
        ax.axvline(b - 0.5, color=_COLORS[i % len(_COLORS)], linestyle="--",
                   label=f"{labels[i]}/{labels[i+1]}")
    ax.set_xlabel("Feature index")
    ax.set_ylabel("|coefficient|")
    ax.set_title(f"{result.model.name}   R² = {result.r2:.4f}")
    ax.legend(loc="upper right", fontsize=8)
    return ax


def _print_summary(comp: Comparison) -> None:
    w = max(len(r.model.name) for r in comp.results)
    print(comp.header)
    print(f"{'model':<{w}}  {'R²':>8}  {'n_feat':>7}   per-group |coeff| sum")
    print("-" * (w + 50))
    for r in sorted(comp.results, key=lambda x: -x.r2):
        mags = group_magnitudes(r)
        mag_str = "  ".join(f"{k}={v:.2f}" for k, v in mags.items())
        print(f"{r.model.name:<{w}}  {r.r2:>8.4f}  {len(r.coeffs)-1:>7}   {mag_str}")


def compare(models_or_results, y=None, *, name="comparison", **meta) -> Comparison:
    """Fit and compare. Accepts either a list of already-fit FitResults,
    or `(models, y)` to fit them now. Any kwargs become `meta`.

    Examples
    --------
    >>> compare([de, ex], y, name="poi_1", poi=poi_1, N=N)
    >>> compare(pre_fit_results, name="baseline")
    """
    if y is None:
        results = list(models_or_results)
    else:
        results = [fit(m, y) for m in models_or_results]

    comp = Comparison(name=name, results=results, meta=meta)
    _print_summary(comp)

    n = len(results)
    fig, axes = plt.subplots(n, 1, figsize=(15, 3.5 * n))
    if n == 1:
        axes = [axes]
    for ax, r in zip(axes, results):
        plot_coeffs(r, ax)
    suptitle = comp.name + (f"   ({comp.meta_str})" if comp.meta else "")
    fig.suptitle(suptitle, fontsize=14, y=1.0)
    fig.tight_layout()
    return comp


# ---------- cross-run ----------

def cross_run_table(comparisons: Sequence[Comparison]):
    """Matrix of R² with rows = models, cols = runs.

    Returns (model_names, run_names, M) where M[i, j] is R² of model i in run j,
    or NaN if that model wasn't in that run.
    """
    model_names = sorted({r.model.name for c in comparisons for r in c.results})
    run_names = [c.name for c in comparisons]
    M = np.full((len(model_names), len(run_names)), np.nan)
    for j, c in enumerate(comparisons):
        d = c.r2_by_model()
        for i, m in enumerate(model_names):
            if m in d:
                M[i, j] = d[m]
    return model_names, run_names, M


def plot_cross_run(comparisons: Sequence[Comparison], ax=None):
    model_names, run_names, M = cross_run_table(comparisons)
    if ax is None:
        _, ax = plt.subplots(
            figsize=(1.2 + 1.3 * len(run_names), 0.5 * len(model_names) + 1.5)
        )
    im = ax.imshow(M, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(run_names)), run_names, rotation=30, ha="right")
    ax.set_yticks(range(len(model_names)), model_names)

    finite = M[np.isfinite(M)]
    mid = finite.mean() if finite.size else 0.0
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.3f}", ha="center", va="center",
                        color="white" if v < mid else "black", fontsize=9)
    ax.set_xlabel("run")
    ax.set_ylabel("model")
    plt.colorbar(im, ax=ax, label="R²")
    ax.set_title("R² across runs")
    return ax
