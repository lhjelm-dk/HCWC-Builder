"""Percentile export, in the form GeoX reads.

SLB does not publish the GeoX import specification and it is not findable online. The format
below is taken from an export that GeoX has actually read: two columns headed ``Percentile`` and
``Depth(m)``, 101 rows running 100 down to 0.

**The convention is exceedance, and it is the opposite of what a statistician means by a
percentile.** "P100" is the *shallowest* contact — 100% chance the true contact is at least this
deep — and "P0" the deepest. That is the industry low-side/high-side reading, and getting it
backwards would invert every contact GeoX imports without raising an error anywhere, so it is
spelled out here and asserted in the tests.

On truncation. P0 and P100 from a Monte Carlo are the sample minimum and maximum: the least stable
statistics in the run. They move on every reseed and drift outward as trials are added. Exporting
them as if they were distribution endpoints hands GeoX a spurious range, so the default truncates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

TailMode = Literal["truncate", "raw", "extrapolate"]

#: The seven-point form, "GeoX 7fractile".
SEVEN_FRACTILES: tuple[int, ...] = (100, 95, 90, 50, 10, 5, 0)


@dataclass(frozen=True)
class PercentileExport:
    """A percentile table plus what was done to its tails, so the note travels with the numbers."""
    table: pd.DataFrame
    tail_mode: TailMode
    n_trials: int
    truncated_at: tuple[float, float] | None
    #: Which contact distribution these percentiles are of. Defaulted so every existing caller
    #: keeps working, and it leads the provenance line because it is the one thing a reader of a
    #: bare CSV cannot recover from the numbers.
    basis: str = "geological"

    def to_csv(self, path=None) -> str:
        """Two columns, ``Percentile`` and ``Value``, no index. Returns the CSV text."""
        text = self.table.to_csv(index=False, lineterminator="\n")
        if path is not None:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        return text

    @property
    def provenance(self) -> str:
        """One line naming **which distribution**, the convention and the tail treatment.

        ``basis`` leads, because it is the thing a reader of a bare CSV cannot recover and the
        thing that most changes what the numbers mean. A geological and a DHI-updated export are
        both plausible tables of contact depths; nothing in the numbers says which you have.
        """
        base = (f"{self.basis.upper()} contact distribution. "
                f"Exceedance percentiles (P100 = shallowest) from {self.n_trials:,} trials"
                f"; tails: {self.tail_mode}")
        if self.truncated_at is not None:
            lo, hi = self.truncated_at
            base += f" at P{100 - hi:g}/P{100 - lo:g}"
        return base + "."


def percentile_table(samples: np.ndarray, *, points: int | tuple[int, ...] = 101,
                     tail_mode: TailMode = "truncate",
                     truncate_at: float = 0.5,
                     basis: str = "geological") -> PercentileExport:
    """Build the export table from a set of realisations.

    ``samples`` are contact depths (or column heights — the function does not care, but the
    exceedance convention only reads naturally for depth).

    ``points`` is 101 for the full fractile export, or a tuple of exceedance percentiles such as
    :data:`SEVEN_FRACTILES`.

    ``tail_mode``:

    * ``"truncate"`` (default) — P100 and P0 are replaced by the P(100-truncate_at) and
      P(truncate_at) values, so the exported endpoints are estimated from ~50 realisations at
      10 000 trials rather than from one.
    * ``"raw"`` — the sample minimum and maximum, unmodified.
    * ``"extrapolate"`` — not implemented; raises, rather than silently doing something else.
    """
    samples = np.asarray(samples, dtype=float)
    samples = samples[np.isfinite(samples)]
    if samples.size < 2:
        raise ValueError("need at least two finite realisations to build a percentile table")

    if isinstance(points, int):
        if points != 101:
            raise ValueError("integer `points` supports only the 101-fractile form; "
                             "pass a tuple for anything else")
        exceedance = tuple(range(100, -1, -1))
    else:
        exceedance = tuple(points)
        if not all(0 <= p <= 100 for p in exceedance):
            raise ValueError("exceedance percentiles must lie in [0, 100]")

    if tail_mode == "extrapolate":
        raise NotImplementedError(
            "fitted-tail extrapolation is not implemented; use 'truncate' (default) or 'raw'"
        )
    if tail_mode not in ("truncate", "raw"):
        raise ValueError(f"unknown tail_mode {tail_mode!r}")

    # Exceedance P -> cumulative quantile (100 - P). P100 is the shallowest, i.e. the 0th quantile.
    cumulative = np.array([100.0 - p for p in exceedance], dtype=float)
    truncated: tuple[float, float] | None = None
    if tail_mode == "truncate":
        if not 0.0 < truncate_at < 50.0:
            raise ValueError("truncate_at must be a small positive percentage, e.g. 0.5")
        lo, hi = truncate_at, 100.0 - truncate_at
        cumulative = np.clip(cumulative, lo, hi)
        truncated = (lo, hi)

    values = np.percentile(samples, cumulative)
    return PercentileExport(
        table=pd.DataFrame({"Percentile": list(exceedance), "Value": values}),
        tail_mode=tail_mode,
        n_trials=int(samples.size),
        truncated_at=truncated,
        basis=basis,
    )
