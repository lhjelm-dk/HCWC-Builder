"""The chance, once: the accumulation chance, the chance curve, and the two exceedances.

    P(G)      = product of the element chances                (tab 2.0)
    F(h)      = P(H >= h | G)                                  engine.exceedance, column space
    POS(h)    = P(G) x F(h)                                    read at h_min
    z_HCWC    = z_apex + H, per realisation                    EngineResult.contact_m
    P(z_HCWC >= z | G)                                         depth_exceedance, depth space
    P(well)   = P(G) x P(z_HCWC >= z_well | G)                 read at the entry depth

Column space is where the threshold lives: ``h_min`` is a column height and ``F(h_min)`` is the
headline. Depth space is where a well and a figure with a depth axis live: the contact of each
realisation is its own apex plus its column, so a chance against absolute depth is read on the
realised contacts and not by shifting ``F(h)`` by one apex. The two agree when the apex is
pinned and differ by the apex spread when it is not (8.1.3).

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

from hcwc.core import engine
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


def depth_exceedance(result: EngineResult, depths_m: np.ndarray | float,
                     weights: np.ndarray | None = None) -> np.ndarray:
    """``P(z_HCWC >= z | G)``, or given the evidence with ``weights``: exact in depth space.

    Read on the realised contacts ``z_apex + H``, realisation by realisation, so a figure with a
    depth axis and the well reading at an entry depth are the same function. This is what every
    chance-against-depth figure draws; ``F(h)`` stays for column space and the threshold.
    """
    return np.asarray(engine.exceedance(result.contact_m, depths_m, weights), dtype=float)


def depth_grid(result: EngineResult, n: int = 400) -> np.ndarray:
    """A depth axis spanning the run: the shallowest apex to the deepest contact."""
    return np.linspace(float(result.apex_m.min()), float(result.contact_m.max()) * 1.0005, n)


def depth_axis(result: EngineResult, columns_m: np.ndarray | float) -> np.ndarray | float:
    """The median-apex equivalent of a column height: where ``h_min`` is drawn on a depth axis.

    A reference mark and not a curve (8.1.3): a threshold is a column height, and the depth it
    corresponds to differs realisation by realisation with the apex. Figures that need to show
    the assessment minimum on a depth axis draw it here and label it as the median-apex
    equivalent; curves against depth use :func:`depth_exceedance`.
    """
    return float(np.median(result.apex_m)) + columns_m
