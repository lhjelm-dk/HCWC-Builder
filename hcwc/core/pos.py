"""The chance, once: the accumulation chance, the chance curve and the depth axis.

    P(G)      = product of the element chances                (tab 2.0)
    F(h)      = P(H >= h | G)                                  engine.exceedance
    POS(h)    = P(G) x F(h)                                    read at h_min and at the well
    z_HCWC    = z_apex + H, per realisation                    EngineResult.contact_m

Until the clean-up of 18 Sep 2026 the product ``P(G) = prod(element chances)`` was written out in
eight places in the tabs and the product ``P(G) x F(h)`` in two more. One implementation here;
the tabs call it. Nothing numerical changed: every caller computed the same product.

``P(G)`` is the geological accumulation chance: the geological elements work at the crest and a
hydrocarbon column of some height exists. It carries no volume criterion; the assessment minimum
enters once, through ``F(h_min)`` (``docs/THEORY.md`` 8.1.1, 8.1.3).
"""
from __future__ import annotations

from typing import Mapping

import numpy as np

from hcwc.core.engine import EngineResult


def accumulation_chance(element_pos: Mapping[object, float] | None) -> float:
    """``P(G)``: the product of the element chances, each ``play x conditional``.

    ``1.0`` when no element chances are known, which is what every caller used before: a
    conditional reading with the element risk left out, labelled as such on the tab.
    """
    if not element_pos:
        return 1.0
    return float(np.prod([float(v) for v in element_pos.values()]))


def chance_curve(p_g: float, exceedance: np.ndarray | float) -> np.ndarray | float:
    """``POS(h) = P(G) x F(h)``: the prospect chance against threshold, or at one threshold."""
    if np.isscalar(exceedance):
        return float(p_g) * float(exceedance)
    return float(p_g) * np.asarray(exceedance, dtype=float)


def depth_axis(result: EngineResult, columns_m: np.ndarray | float) -> np.ndarray | float:
    """A depth axis under a column-space curve: the median apex plus the column.

    A drawing convention and not a second model (8.1.3): the curve is exact in column space and
    the well is read in depth space realisation by realisation; the axis places the curve at
    the median apex so it can be drawn beside the contact histogram.
    """
    return float(np.median(result.apex_m)) + columns_m
