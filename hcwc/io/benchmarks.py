"""Loaders for the empirical column-height benchmarks.

Three families, deliberately kept distinguishable rather than merged into one
"empirical prior", because they are conditioned differently and disagree in ways that
are informative:

* **Edmundson** — 242 NCS discoveries, per-observation. Open, CC-BY 4.0, shipped in
  ``reference/``. The only one where we hold the raw rows and can therefore re-do the
  statistics ourselves.
* **Graham** — ExxonMobil global synthesis. Published as *parameters only* (40% of traps
  under 250 m fill to spill; uniform blended with filled-to-spill at weight 0–0.4 for
  250–800 m), so it is generated, not loaded.
* **C&C** — Lars's non-public reservoir statistics. Read from ``reference/private/`` if
  present and silently absent otherwise, so a clone still runs.

Every one of them is conditioned on **discovery**, and in every one the filled-to-spill
observations are right-censored. Nothing here corrects for that; that is
:mod:`hcwc.core.censoring`'s job, and keeping the two apart means the raw data stays
inspectable.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REFERENCE = Path(__file__).resolve().parents[2] / "reference"
PRIVATE = REFERENCE / "private"


@dataclass(frozen=True)
class Benchmark:
    """One empirical dataset, with its provenance attached rather than remembered."""
    name: str
    rows: pd.DataFrame
    source: str
    licence: str
    public: bool

    @property
    def n(self) -> int:
        return len(self.rows)

    @property
    def censored_fraction(self) -> float:
        return float(self.rows["filled_to_spill"].mean())


def load_edmundson(*, use_authors_flag: bool = False) -> Benchmark:
    """The 242 NCS discoveries.

    ``use_authors_flag`` selects the authors' own trap-fill binning instead of the
    ``trap_fill >= 0.99`` rule. It reproduces their published matrix exactly, and it is
    wrong on one row — a 86.5 m column in a 96.5 m trap, binned as 100% fill. Use it to
    reproduce them; use the default to analyse them.
    """
    path = REFERENCE / "edmundson_2021_ncs_columns.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. It is open data: https://osf.io/6ysbv/ (CC-BY 4.0)."
        )
    rows = pd.read_csv(path, comment="#")
    flag = "filled_to_spill_authors" if use_authors_flag else "filled_to_spill_rule"
    rows = rows.assign(filled_to_spill=rows[flag].astype(bool))
    return Benchmark(
        name="Edmundson et al. (2021) — 242 NCS discoveries",
        rows=rows,
        source="https://osf.io/6ysbv/ ; AAPG Bulletin 105(12) 2381–2403, doi:10.1306/03122119223",
        licence="CC-BY 4.0",
        public=True,
    )


def load_edmundson_matrix() -> pd.DataFrame:
    """The exact 3x3x4 forward-probability matrix, from the authors' own supplement."""
    return pd.read_csv(REFERENCE / "edmundson_2021_trapfill_matrix.csv", comment="#")


def load_cc_reservoir_stats() -> Benchmark | None:
    """Lars's non-public "C&C" reservoir statistics, or ``None`` if not on this machine.

    Returning ``None`` rather than raising is deliberate: this dataset must never be
    committed, so every clone except Lars's will not have it, and a missing private
    dataset is a normal state rather than an error.
    """
    path = PRIVATE / "cc_reservoir_stats.csv"
    if not path.exists():
        return None
    rows = pd.read_csv(path, comment="#")
    return Benchmark(
        name="C&C reservoir statistics (not public)",
        rows=rows,
        source="unpublished study; held locally, never committed",
        licence="all rights reserved — do not redistribute",
        public=False,
    )


def graham_column_height(rng: np.random.Generator, trap_height: float,
                         n: int) -> np.ndarray:
    """Graham et al. (2015) as a sampler, for a trap of relief ``trap_height``.

    Their published parameters: 40% of traps shorter than 250 m fill to synclinal spill;
    for 250–800 m, a uniform column-height distribution blended with filled-to-spill at
    a weight "between zero and 0.4".

    **The decay is an interpretation, not a quotation.** The abstract gives the range and
    the trap-height band but never says the weight falls linearly, nor in which
    direction. Linear 0.4 -> 0.0 across 250–800 m is the reading implemented here, because it is
    the one that makes the two published endpoints meet. Anyone using this should know it is a
    reading.
    """
    return _banded_family(rng, trap_height, n, shape=("uniform", ()))


def spill_weight(trap_height: float) -> float:
    """The filled-to-spill weight of the banded model, at this relief.

    Split out because **both** benchmark families share it exactly — the ExxonMobil branch and the
    C&C branch differ only in the shape they draw
    when the closure does *not* fill. Keeping the shared half in one place is what makes that
    visible instead of buried in two near-identical functions.
    """
    if trap_height <= 0:
        raise ValueError("trap height must be positive")
    if trap_height < 250.0:
        return 0.4
    if trap_height <= 800.0:
        return 0.4 * (800.0 - trap_height) / 550.0
    return 0.0


def _banded_family(rng: np.random.Generator, trap_height: float, n: int,
                   shape: tuple[str, tuple[float, ...]]) -> np.ndarray:
    """The banded fill-to-spill model, with the non-spill shape left open.

    The two families are the same model twice: Bernoulli on whether the closure fills to spill,
    and if it does not, a draw between a 20 m floor and the relief. Only the second half differs
    — ExxonMobil draws uniformly, C&C draws ``BetaGeneral(5, 1, 20, h)``.
    """
    w_spill = spill_weight(trap_height)
    kind, params = shape
    if kind == "uniform":
        out = rng.uniform(20.0, trap_height, n)
    elif kind == "beta_general":
        from hcwc.core import dists
        out = dists.beta_general(rng, params[0], params[1], 20.0, trap_height, n)
    else:
        raise ValueError(f"unknown non-spill shape {kind!r}")
    out[rng.random(n) < w_spill] = trap_height
    return out


def load_cc_shape() -> tuple[str, tuple[float, ...]] | None:
    """The C&C branch's non-spill shape, or ``None`` if it is not on this machine.

    **What this actually is, is not a dataset.** The C&C and ExxonMobil series are the same banded
    fill-to-spill model, sharing the same Bernoulli weight; the *only* difference between them is
    the distribution drawn when the closure does not fill to spill. So there is no table of
    reservoir statistics to extract — there is a shape.

    It is still gated. Those shape parameters may encode the conclusion of the unpublished study,
    and "keep for now, hidden" is the instruction; a shape that summarises non-public work is not
    obviously safer to publish than the rows behind it. So the parameters live in
    ``reference/private/cc_shape.json``, which is git-ignored, and every clone without it simply
    omits the series — the same contract as :func:`load_cc_reservoir_stats`.
    """
    path = PRIVATE / "cc_shape.json"
    if not path.exists():
        return None
    import json
    spec = json.loads(path.read_text(encoding="utf-8"))
    return str(spec["kind"]), tuple(float(x) for x in spec["params"])


def cc_column_height(rng: np.random.Generator, trap_height: float, n: int) -> np.ndarray | None:
    """The C&C branch of the banded model, or ``None`` when the shape is absent."""
    shape = load_cc_shape()
    if shape is None:
        return None
    return _banded_family(rng, trap_height, n, shape)
