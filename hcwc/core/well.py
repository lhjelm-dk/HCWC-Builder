"""Well control: a penetration that saw where the hydrocarbons stop, or where they had not started.

**This is the one piece of evidence about a contact that needs no argument.** A DHI is an
inference, and tab 5.0 spends four sub-tabs earning the right to use it. A well that logged a water
leg at 2 260 m is not an inference — the reservoir was there, the fluid was measured, and the
contact is above it. Where the DHI needs a detection function and a validity term to become a
likelihood, this arrives as one.

**It enters as evidence, not as a limit, and the difference matters.** A limit is a *mechanism* that
could stop the column; adding one changes the model. A penetration is an *observation of the outcome*
of the mechanisms already in the model. If the contact is at 2 210 m because the top seal gave way,
a well seeing water at 2 260 m is a measurement of that, not a second cause of it. So it reweights
the realisations the engine already drew, exactly as the DHI does, and the controlling-limit
bookkeeping survives — which it would not if the well were entered as another limit.

**Two things can be seen, and they are not symmetric.**

*Water at a depth* says the contact is shallower. It is the clean case: water down-dip is entirely
consistent with a column up-dip, so the observation constrains **where** the contact is and says
nothing at all about whether the prospect works.

*Hydrocarbons proven down to a depth* says the contact is deeper — and it also says the prospect
**is a discovery**, which is a far larger statement than anything about depth. This module deals
only with the depth. It deliberately does not touch the element chances on tab 2.0, because a proven
accumulation means those are no longer prior beliefs about an untested prospect, and quietly setting
P(G) to 1 inside a contact calculation would hide that. See :meth:`WellControl.proves_hydrocarbons`,
which exists so the interface can say so out loud.

**Why there is still a validity term.** The measurement is reliable; its *relevance* is not. The
penetration may sit in a different fault block, a different compartment, or a stratigraphic unit
that is not the one being drilled. Low-resistivity pay and residual saturation can also make a log
call wrong. ``p_connected`` carries all of that, and it plays the same role — with the same
Cromwell floor — as ``p_valid`` does for a seismic pick.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from hcwc.core.engine import EngineResult


@dataclass(frozen=True)
class WellControl:
    """What a penetration saw, in m TVDSS.

    At least one of the two depths is required; both together bracket the contact, which is the
    strongest evidence this tool can take. ``hc_down_to_m`` must be above ``water_at_m`` — a well
    reporting hydrocarbons *below* its own water leg is describing two accumulations, or an error.
    """

    hc_down_to_m: float | None = None
    water_at_m: float | None = None
    depth_sigma_m: float = 5.0
    p_connected: float = 0.9
    name: str = "well control"

    def __post_init__(self) -> None:
        if self.hc_down_to_m is None and self.water_at_m is None:
            raise ValueError(
                "well control needs at least one depth: hydrocarbons proven down to a depth, "
                "water seen at a depth, or both"
            )
        if (self.hc_down_to_m is not None and self.water_at_m is not None
                and not self.hc_down_to_m < self.water_at_m):
            raise ValueError(
                f"the hydrocarbons ({self.hc_down_to_m:,.0f} m) must be above the water "
                f"({self.water_at_m:,.0f} m). Reversed, this describes two accumulations rather "
                f"than one contact"
            )
        if self.depth_sigma_m <= 0:
            raise ValueError(
                "the depth uncertainty must be positive. It is not the well's own depth error, "
                "which is small, but the error in tying the well to the mapped surface this model "
                "measures its apex from"
            )
        if not 0.0 < self.p_connected <= 1.0:
            raise ValueError(
                "p_connected is the chance the penetration samples the same accumulation, so it "
                "must lie in (0, 1]. Zero would say the well is irrelevant, in which case it is "
                "not evidence and should not be entered"
            )

    @property
    def proves_hydrocarbons(self) -> bool:
        """Whether the observation establishes that the prospect works.

        Read by the interface so it can say what the depth arithmetic below deliberately will not:
        a proven column makes the element chances on tab 2.0 a statement about an appraisal, not a
        prospect, and that is a decision for the assessor rather than a side effect of entering
        a depth.
        """
        return self.hc_down_to_m is not None

    def bracket(self) -> tuple[float, float]:
        """The depths the contact is constrained to lie between, ignoring the soft edges."""
        return (self.hc_down_to_m if self.hc_down_to_m is not None else -np.inf,
                self.water_at_m if self.water_at_m is not None else np.inf)


def likelihood(result: EngineResult, well: WellControl) -> np.ndarray:
    """``L(what the well saw | contact)`` for every realisation.

    Two soft steps and a floor::

        L = p_connected · Φ((z − z_hc)/σ) · Φ((z_w − z)/σ)  +  (1 − p_connected)

    with ``z`` the realisation's contact depth. The first factor is near 1 where the contact is
    below the proven hydrocarbons and falls away above them; the second is near 1 where the contact
    is above the water and falls away below it. Either may be absent.

    **The steps are soft, and σ is not the well's depth error.** A wireline depth is good to a metre
    or two. What is uncertain is the tie between that depth and the *mapped surface* this model
    measures its apex from — the same depth-conversion error that makes the apex a distribution
    rather than a number in the first place. That is tens of metres on most prospects, and it is
    what belongs here.

    **The floor is the point of the mixture.** Since both Φ terms are at most 1,

        L  ≥  1 − p_connected

    so a penetration can never rule a contact out entirely, whatever depth it reports. That is
    Cromwell's rule, and it is what makes it safe to enter a hard observation at all: the well is
    certain about the fluid it logged and uncertain about whether that fluid belongs to the
    accumulation being assessed, and the arithmetic keeps those two apart.
    """
    z = np.asarray(result.contact_m, dtype=float)
    valid = np.ones_like(z)
    if well.hc_down_to_m is not None:
        valid = valid * norm.cdf((z - well.hc_down_to_m) / well.depth_sigma_m)
    if well.water_at_m is not None:
        valid = valid * norm.cdf((well.water_at_m - z) / well.depth_sigma_m)
    if well.p_connected >= 1.0:
        return valid
    return well.p_connected * valid + (1.0 - well.p_connected)


def combine(*weights: np.ndarray) -> np.ndarray:
    """Multiply independent likelihood channels into one weight vector.

    Independence is the assumption and it is worth stating. A seismic amplitude and a well
    penetration are close to independent evidence — one is a reflection coefficient, the other a
    resistivity log — which is exactly what makes them worth having together. Two amplitudes on the
    same volume would not be, and should not be entered as two observations.
    """
    if not weights:
        raise ValueError("nothing to combine")
    out = np.ones_like(np.asarray(weights[0], dtype=float))
    for w in weights:
        out = out * np.asarray(w, dtype=float)
    return out
