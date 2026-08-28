"""Exports for WellVolPOS: the per-trial contacts, and the per-element curves.

Two different things, and keeping them apart is the point.

**1. The trial table.** WellVolPOS's importer consumes a ``TrialSet`` and nothing else
(``wellvolpos/io/adapters/base.py``), and its generic adapter recognises columns by name. The
canonical names and units are fixed — ``contact`` in m TVDSS, ``area`` in km², ``hc_grv`` in
10⁶ m³ — so the export writes headers its regex table already matches and nothing needs configuring
at the far end.

**It is deliberately a partial trial set.** WellVolPOS requires ``resource`` in MMboe, and this tool
cannot produce it: a resource needs net-to-gross, porosity, saturation, formation volume factor and
a recovery factor, none of which is a contact-depth question. Inventing a column to satisfy the
importer would be the worst possible outcome — every number downstream would then be computed from
fiction and nothing would look broken. So the file carries what this tool actually knows, and
:func:`missing_for_wellvolpos` names what has to be joined on and where it comes from (SCOPE-HC,
which does volumetrics). Better a refused import with a clear reason than an accepted one with a
fabricated column.

**2. The element curves.** These are not per-trial data and do not belong in the same file. They
are the thing tab ④ argues WellVolPOS should consume *instead of* allocating one location factor
across four elements — a chance-versus-depth curve per element, derived from which element bound
the column in each realisation. WellVolPOS cannot compute them, because it never sees the competing
limits; it can only take a single ``r`` and divide it up, and its own docstring says so.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from hcwc.core.decompose import ELEMENTS, Decomposition
from hcwc.core.engine import EngineResult
from hcwc.core.limits import Group

#: Canonical field -> unit, copied from WellVolPOS's ``CANONICAL_FIELDS`` for the fields this tool
#: can honestly fill. Kept here rather than imported so the two repos stay independent.
EXPORTED_FIELDS: dict[str, str] = {
    "trial": "",
    "contact": "m TVDSS",
    "crest": "m TVDSS",
    "spill": "m TVDSS",
    "area": "km2",
    "hc_grv": "1e6 m3",
}

#: Required by WellVolPOS and not derivable here. See the module docstring.
MISSING_FIELDS: dict[str, str] = {
    "resource": "MMboe — needs net-to-gross, porosity, saturation, Bo/Bg and a recovery factor",
}


def missing_for_wellvolpos() -> dict[str, str]:
    """What still has to be joined on before WellVolPOS will accept the file, and why."""
    return dict(MISSING_FIELDS)


def trial_table(result: EngineResult, area_depth=None, *,
                successes_only: bool = True) -> pd.DataFrame:
    """One row per realisation, in WellVolPOS's canonical column names and units.

    ``area_depth`` is an optional :class:`hcwc.core.charge.AreaDepthTable`; with it the export can
    also carry the area each contact encloses and the gross rock volume above it, both of which are
    pure geometry and so legitimately ours to state.

    ``successes_only`` defaults to True because the failure realisations have no contact in any
    useful sense — they are the cases where the column never reached the assessment minimum, and
    handing them to a volumetrics tool as if they were contacts would misstate the distribution it
    fits.
    """
    mask = result.above_minimum if successes_only else np.ones(result.n, dtype=bool)
    if not mask.any():
        raise ValueError(
            "no realisation reaches the assessment minimum, so there is nothing to export. "
            "Lower the minimum on tab ② or revisit the limits."
        )

    contact = result.contact_m[mask]
    frame = pd.DataFrame({
        "trial": np.arange(1, contact.size + 1),
        "contact": contact,
        "crest": result.apex_m[mask],
    })

    spill = _spill_depths(result)
    if spill is not None:
        frame["spill"] = spill[mask]

    if area_depth is not None:
        # Both are interpolations of the mapped table, clamped at its ends. Outside the table the
        # geometry is simply unknown, and NaN says that where a clamped value would quietly assert
        # the structure keeps going.
        inside = (contact >= area_depth.apex_m) & (contact <= area_depth.deepest_m)
        area = np.full(contact.shape, np.nan)
        grv = np.full(contact.shape, np.nan)
        area[inside] = np.interp(contact[inside], area_depth.depths_m, area_depth.top_area_km2)
        grv[inside] = np.interp(contact[inside], area_depth.depths_m, area_depth.grv_1e6m3)
        frame["area"] = area
        frame["hc_grv"] = grv
        frame = frame.drop(columns=[c for c in ("area", "hc_grv") if frame[c].isna().all()])

    return frame


def _spill_depths(result: EngineResult) -> np.ndarray | None:
    """The spill limit's own sampled depth, if the model has one.

    Exported because WellVolPOS uses crest and spill to bound its structure fit, and because a
    contact distribution without the closure that produced it is much harder to sanity-check at
    the far end.
    """
    for j, limit in enumerate(result.limit_set.limits):
        if limit.group is Group.CLOSURE and "spill" in limit.name.lower():
            return result.apex_m + result.sampled_m[:, j]
    return None


def element_curve_table(decomposition: Decomposition,
                        element_pos: dict[Group, float]) -> pd.DataFrame:
    """Chance against depth, one column per risk element, plus the direct contact curve.

    The replacement for WellVolPOS's allocation step. Each column is ``POS_e x P_e(z)``: the
    prospect's element chance taken down structure, derived from which element bound the column
    rather than apportioned by a weighting rule.

    ``direct`` is the whole-prospect curve read from the contact distribution itself. Under
    independent limits the four element columns multiply to it; where they do not, the elements
    share something and the columns must not be multiplied by anything else that also depends on
    depth. Tab ④ §3 quantifies that gap, and it travels with the file rather than being left
    behind.
    """
    curves = decomposition.element_pos_at_depth(element_pos)
    frame = pd.DataFrame({"depth_m": decomposition.depths_m})
    for element in ELEMENTS:
        if element in curves:
            frame[element.value.lower()] = curves[element]
    frame["direct"] = decomposition.direct_pos(element_pos)
    return frame


def provenance(result: EngineResult, seed: int, n_trials: int) -> str:
    """One line naming what produced the file, so a stray CSV can still be traced."""
    return (f"HCWC Distribution Builder | prospect {result.limit_set.name!r} | "
            f"{result.n:,} realisations, seed {seed} | assessment minimum "
            f"{result.limit_set.min_column_m:.0f} m column | "
            f"{len(result.limit_set.limits)} competing limits")
