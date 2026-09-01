"""Bring your own benchmark: read a column-height dataset and make it comparable.

The tool ships with one open dataset. That is a weakness, and the honest fix is not to find a
second one and hard-code it — it is to let anyone point the same analysis at their own data.

**Raw rows, not a fitted shape.** A dataset enters as discoveries, one per row, and the censoring
correction runs *here*. That is the whole argument of this tool: a closure that filled to spill
tells you about the closure, not about the seal, so fitting filled traps as though they measured
seal capacity biases the result. A company importing 300 of their own fields should get that
finding on their own data, not a curve someone else fitted.

**Nothing is silently repaired.** Every inference the reader makes — a derived flag, a substituted
predictor, a row that cannot be true — is recorded in :attr:`Dataset.notes` and shown beside the
figures. A dataset that needed six repairs is still usable; a reader who is not told about them is
not.

**Privacy is the caller's, not ours.** Nothing here writes to disk, caches to a file, or reaches the
network. An imported dataset lives in the browser session and leaves when the tab closes.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
import pandas as pd

#: A column may be at most this much taller than its own closure and still be read as a filled
#: trap measured imperfectly. Beyond it the two numbers do not describe the same structure.
#:
#: 2 % is chosen from the shape of the failure rather than from taste: on the datasets seen so far
#: the excesses are not a smooth tail off 1.0 but a small cluster within a couple of per cent and
#: then a long scatter reaching five times and beyond. A 6 m closure carrying a 368 m column is not
#: a mis-measurement, and no tolerance should be wide enough to admit it.
COHERENCE_SLOP = 1.02

#: At or above this fraction of its closure, a trap is read as filled to spill. The same rule the
#: shipped NCS loader uses by default, so a correction means the same thing on every dataset.
FILLED_RULE = 0.99

#: Accepted spellings, lower-cased and stripped of spaces/underscores, for each field we need.
#: Generous on input because the alternative is a user editing headers to match an undocumented
#: convention, which is how a column gets renamed to the wrong thing.
ALIASES: dict[str, tuple[str, ...]] = {
    "trap_height_m": ("trapheightm", "trapheight", "closureheightm", "closureheight", "closure",
                      "trapheightmeters", "structuralrelief", "reliefm", "relief"),
    "hc_column_m": ("hccolumnm", "hccolumn", "columnheightm", "columnheight", "column",
                    "hcwcheight", "hcwcheightm", "oilcolumnm", "gascolumnm", "netcolumnm"),
    "burial_depth_m": ("burialdepthm", "burialdepth", "burial", "reservoirdepthm",
                       "reservoirdepth", "depthm"),
    "apex_depth_m": ("apexdepthm", "apexdepth", "apex", "crestdepthm", "crestdepth", "crest",
                     "topreservoirm", "topreservoir"),
    "filled_to_spill": ("filledtospill", "filledtospillrule", "fulltospill", "spillfilled",
                        "filled", "istofill", "filledtospillflag"),
    "trap_fill": ("trapfill", "fillfraction", "fillfrac", "fill", "fillratio"),
}


def _canonical(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


@dataclass(frozen=True)
class Dataset:
    """One imported dataset, with everything the reader had to infer recorded alongside it."""

    name: str
    rows: pd.DataFrame
    source: str
    #: Every inference, substitution and exclusion, in the order they were made.
    notes: tuple[str, ...] = ()
    #: Which predictors the censored fit can use. Always includes ``trap_height``; includes
    #: ``burial_depth`` only when the dataset carried one or something standing in for it.
    predictors: tuple[str, ...] = ("trap_height",)

    @property
    def n(self) -> int:
        return len(self.rows)

    @property
    def usable(self) -> pd.DataFrame:
        """Rows whose column and closure can describe the same structure."""
        return self.rows[~self.rows["column_exceeds_trap"].astype(bool)]

    @property
    def censored_fraction(self) -> float:
        u = self.usable
        return float(u["filled_to_spill"].mean()) if len(u) else float("nan")

    @property
    def full_model(self) -> bool:
        """Whether burial depth is available as a second predictor."""
        return "burial_depth" in self.predictors


class DatasetError(ValueError):
    """The file cannot be read as a column-height dataset. The message says what is missing."""


def read_csv(text: str | bytes, *, name: str, source: str = "") -> Dataset:
    """Read a CSV of discoveries into a :class:`Dataset`, recording every inference.

    Required: a closure height and a column height, under any of the spellings in :data:`ALIASES`.
    Everything else is derived or noted as absent.
    """
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig", errors="replace")
    try:
        raw = pd.read_csv(io.StringIO(text), comment="#")
    except Exception as exc:                                    # noqa: BLE001 - reported, not raised
        raise DatasetError(f"the file could not be parsed as CSV: {exc}") from exc
    if raw.empty:
        raise DatasetError("the file has no rows.")

    found: dict[str, str] = {}
    seen = {_canonical(c): c for c in raw.columns}
    for target, spellings in ALIASES.items():
        for spelling in (_canonical(target), *spellings):
            if spelling in seen:
                found[target] = seen[spelling]
                break

    missing = [f for f in ("trap_height_m", "hc_column_m") if f not in found]
    if missing:
        raise DatasetError(
            "a column-height dataset needs a closure height and a hydrocarbon column height, one "
            f"row per discovery. Missing: {', '.join(missing)}. The columns in this file are "
            f"{', '.join(map(str, raw.columns))} — rename the two that carry those quantities to "
            f"`trap_height_m` and `hc_column_m`, or use any of the spellings the reader accepts."
        )

    notes: list[str] = []
    trap = pd.to_numeric(raw[found["trap_height_m"]], errors="coerce").to_numpy(float)
    column = pd.to_numeric(raw[found["hc_column_m"]], errors="coerce").to_numpy(float)

    finite = np.isfinite(trap) & np.isfinite(column) & (trap > 0) & (column > 0)
    if finite.sum() < len(trap):
        notes.append(f"{len(trap) - int(finite.sum())} of {len(trap)} rows dropped: a closure or "
                     f"column height that was blank, non-numeric or not positive.")
    if finite.sum() < 20:
        raise DatasetError(
            f"only {int(finite.sum())} usable rows. A benchmark family fitted on fewer than about "
            f"twenty discoveries says more about the sample than about the geology."
        )
    trap, column = trap[finite], column[finite]
    kept = raw.loc[finite].reset_index(drop=True)

    fill = column / trap
    incoherent = fill > COHERENCE_SLOP
    if incoherent.any():
        worst = float(fill.max())
        notes.append(
            f"{int(incoherent.sum())} of {finite.sum()} rows have a column more than "
            f"{COHERENCE_SLOP:.0%} of their own closure — not possible for a simple structure, and "
            f"the worst is {worst:.1f}× its closure. **Kept and flagged, excluded from every fit.** "
            f"A discarded row is a decision nobody can audit; a flagged one can be argued with.")

    mild = (fill > 1.0) & ~incoherent
    if mild.any():
        notes.append(
            f"{int(mild.sum())} rows sit between 100 % and {COHERENCE_SLOP:.0%} of their closure. "
            f"Read as filled traps measured imperfectly, and **clipped to the closure for the "
            f"fit** — which is not a fudge: a filled trap is a right-censored observation, and the "
            f"value a censored observation carries is the censoring point.")

    # ---- filled to spill, taken if given and derived if not -------------------------------
    if "filled_to_spill" in found:
        flag = kept[found["filled_to_spill"]]
        filled = flag.map(lambda v: str(v).strip().lower() in
                          {"1", "true", "yes", "y", "t"} if not isinstance(v, (int, float, bool))
                          else bool(v)).to_numpy(bool)
        notes.append("Filled-to-spill taken from the file's own flag rather than derived.")
    else:
        filled = (fill >= FILLED_RULE) & ~incoherent
        notes.append(
            f"Filled-to-spill derived as column ≥ {FILLED_RULE:.0%} of closure — the same rule the "
            f"shipped NCS dataset uses, so the censoring correction means the same thing on both. "
            f"**This flag is what makes the correction possible**; supply your own column if you "
            f"record it directly.")

    # ---- burial depth, or a stand-in, or neither ------------------------------------------
    burial = None
    if "burial_depth_m" in found:
        burial = pd.to_numeric(kept[found["burial_depth_m"]], errors="coerce").to_numpy(float)
    elif "apex_depth_m" in found:
        burial = pd.to_numeric(kept[found["apex_depth_m"]], errors="coerce").to_numpy(float)
        notes.append(
            "**Apex depth used in place of burial depth.** They are not the same quantity — the "
            "apex is the crest of this closure, burial depth is where the reservoir sits — but "
            "they differ by less than the spread the fit is estimating, and using the apex keeps "
            "burial as a predictor rather than dropping it. Lars's ruling, 28 Aug 2026.")

    predictors: tuple[str, ...] = ("trap_height",)
    if burial is not None and np.isfinite(burial).sum() >= 20 and np.nanmin(burial) > 0:
        predictors = ("trap_height", "burial_depth")
    else:
        if burial is not None:
            notes.append("The burial-depth column was present but mostly unusable, so it is not "
                         "a predictor.")
        else:
            notes.append(
                "**No burial depth, and no apex depth to stand in for it.** The fit regresses "
                "column height on closure height alone. That is a different and weaker model than "
                "the two-predictor one used on the shipped dataset, and every figure drawn from it "
                "says so.")
        burial = np.full(trap.shape, np.nan)

    rows = pd.DataFrame({
        "trap_height_m": trap,
        "hc_column_m": column,
        "burial_depth_m": burial,
        "trap_fill": fill,
        "filled_to_spill": filled,
        "column_exceeds_trap": incoherent,
    })
    return Dataset(name=name.strip() or "imported dataset",
                   rows=rows,
                   source=source.strip() or "not stated",
                   notes=tuple(notes),
                   predictors=predictors)


def fit(dataset: Dataset):
    """The censoring-corrected log-linear fit for this dataset.

    Filled traps enter as **right-censored** observations of seal capacity rather than as
    measurements of it, which is the correction the whole tool is written around. Incoherent rows
    are excluded — they are flagged in the dataset and would otherwise drag the fit toward a
    relationship that is not in the geology.
    """
    from hcwc.core import censoring

    u = dataset.usable
    trap = u["trap_height_m"].to_numpy(float)
    # Clipped to the closure, which is not a fudge: a filled trap is a *right-censored* observation
    # of seal capacity, and the value a censored observation carries is the censoring point. A
    # column measured three metres over a 335 m closure is a filled trap plus measurement error,
    # and the trap height is the correct number for it. Rows that exceed by more than
    # COHERENCE_SLOP never reach here -- they are not filled traps, they are wrong.
    column = np.minimum(u["hc_column_m"].to_numpy(float), trap)
    predictors: dict[str, np.ndarray] = {"trap_height": trap}
    if dataset.full_model:
        predictors["burial_depth"] = u["burial_depth_m"].to_numpy(float)
    return censoring.censored_loglinear(predictors, column, trap)


def column_height(dataset: Dataset, rng: np.random.Generator, trap_height: float,
                  burial_m: float, n: int = 40_000, *, fitted=None) -> np.ndarray:
    """Column heights this dataset predicts for a closure of this size.

    ``min(S, H)`` applied to the fitted seal capacity, exactly as the shipped benchmark does: the
    sampled capacity is what the seal could hold, and the closure is what there is to fill.
    """
    f = fitted if fitted is not None else fit(dataset)
    mu = f.intercept + f.coefficients["trap_height"] * np.log(trap_height)
    if dataset.full_model and "burial_depth" in f.coefficients:
        mu = mu + f.coefficients["burial_depth"] * np.log(max(burial_m, 1.0))
    return np.minimum(np.exp(rng.normal(mu, f.sigma, n)), trap_height)
