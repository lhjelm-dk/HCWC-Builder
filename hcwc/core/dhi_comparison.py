"""The other ways of combining a DHI with the geology, kept for the comparison and not for a headline.

Moved out of ``hcwc.core.dhi`` on 18 Sep 2026 (Phase 3 of the clean-up) so the canonical chain
stays in one module: index -> likelihood ratio -> ``P(G | s)``; pick, ``c``, ``D(h)`` ->
weights -> ``HCWC | G, evidence``; ``POS(h) = P(G | s) x F_post(h)``. Everything here is what
tab 5.1's diagnostics draw *beside* that chain:

* :func:`scenario_switch` -- Hood's rule, ``IF(DHI valid, DHI contact, geological contact)``,
  a mixture that moves the contact and not the chance;
* :class:`CombinedUpdate` -- the blended construction superseded as the headline on 14 Sep 2026,
  retained so the tab can show what it gave;
* :func:`combination_exceedance` -- the three combinations (scenario, pooled, Bayesian) on one
  grid, the argument for offering the update rather than the switch.

Nothing here feeds a number the app reports as a result. The code is unchanged from where it
sat; the tests that pin it moved with it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from scipy.stats import norm

from hcwc.core.dhi import (DetectionFunction, DhiObservation, R_CAP, R_FLOOR, R_SINGLE_CHANNEL,
                           likelihood, simm_update, volume_weight)
from hcwc.core.engine import EngineResult


def scenario_switch(result: EngineResult, p_valid: float, dhi_contact_m: float,
                    pick_sigma_m: float, seed: int | None = None) -> np.ndarray:
    """Formulation A — ``IF(DHI valid, DHI contact, geological contact)``.

    Hood's rule: merge late, as a scenario, never as a blended input distribution. It replaces the
    contact where the DHI is taken to be valid and leaves it alone otherwise, so it moves the
    contact distribution but **not** POS.

    ``p_valid`` has to be typed as a single number, which is the formulation's weakness. Under
    formulation B that number is revealed as a collapsed detection function — a scalar standing in
    for ``D(h)`` evaluated somewhere unspecified — which is why it never equals E-POS's
    ``dhi_volume_weight``.
    """
    if not 0.0 <= p_valid <= 1.0:
        raise ValueError("P(DHI is a valid contact indicator) must be in [0, 1]")
    if pick_sigma_m <= 0:
        raise ValueError("the pick sigma must be positive")
    rng = np.random.default_rng(result.seed + 7717 if seed is None else seed)
    valid = rng.random(result.n) < p_valid
    picked = rng.normal(dhi_contact_m, pick_sigma_m, result.n)
    return np.where(valid, picked, result.contact_m)


@dataclass(frozen=True)
class CombinedUpdate:
    """The two channels of one seismic observation, and the warning that goes with combining them.

    **Superseded as the headline on 14 Sep 2026, and not to be used for one.** It blended
    ``r_dhi`` -- a ratio between two column heights *inside* ``G`` -- with the strength ratio and
    applied the blend to ``P(G) · F_prior(h_min)`` as if it were a likelihood ratio on the
    prospect. It is not: ``P(h < h_min | G)`` is not ``P(not G)``. And the strength had already
    entered the weights through the old ``p_valid``, so it was counted twice. The chance is now
    :func:`prospect_pos`, and ``dependence`` has no role in it. This class stays so that the
    tab can show what the blended construction gave beside the correct one, in the same way the
    scenario switch and the pooled curve are shown: as arithmetic with something wrong in it.

    ``r_geometry`` is implied by the contact update on this tab — the detection function and the
    pick together say how much more likely the observation is if there really is a column.
    ``r_strength`` comes from the amplitude *character*, through the two-curve strength model.

    **They are different aspects of the same observation, not two observations.** A bright anomaly
    is more likely to have a mappable termination, so the two are positively dependent, and
    multiplying them assumes they are not. That over-states the evidence — the same double-count
    this whole architecture is arranged to avoid, one level in. ``dependence`` discounts the
    combination: 0 multiplies them outright, 1 takes the stronger of the two and ignores the other.
    """
    prior_pos: float
    r_geometry: float
    r_strength: float
    dependence: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.dependence <= 1.0:
            raise ValueError("dependence must be in [0, 1]")

    @staticmethod
    def _one_channel(r: float) -> float:
        """Bound one channel before it is combined.

        The geometry ratio is a *measurement* off the realisations, so :attr:`DhiPosterior.r_dhi`
        reports it raw -- a reader who is shown 4 000 needs to see 4 000 and be told it is an
        artefact of a sharp pick against a distant failure set. What must not happen is that the
        raw value then walks into the combination and is trimmed only by the outer guard, which is
        five times what one channel is allowed to say. It is bounded here, at the point of use.
        """
        return float(min(max(r, 1.0 / R_SINGLE_CHANNEL), R_SINGLE_CHANNEL))

    @property
    def r_combined(self) -> float:
        """Geometric interpolation between the product and the stronger single channel."""
        if not np.isfinite(self.r_geometry) or self.r_geometry <= 0:
            return self._one_channel(self.r_strength)
        log_product = (np.log(self._one_channel(self.r_geometry))
                       + np.log(self._one_channel(self.r_strength)))
        log_stronger = max(abs(np.log(self._one_channel(self.r_geometry))),
                           abs(np.log(self._one_channel(self.r_strength))))
        log_stronger = np.copysign(log_stronger, log_product) if log_product else 0.0
        blended = (1.0 - self.dependence) * log_product + self.dependence * log_stronger
        return float(min(max(np.exp(blended), R_FLOOR), R_CAP))

    @property
    def posterior_pos(self) -> float:
        return simm_update(self.prior_pos, self.r_combined)

    @property
    def volume_weight(self) -> float:
        return volume_weight(self.r_combined)


# --------------------------------------------------------------------------- three combinations
#
# There are three things people mean by "combining the DHI with the geological model", and they
# give different answers. Offering all three is not indecision -- it is the only way to show that
# the choice matters, and which one is defensible.
#
# The framing to be suspicious of is "the DHI's HCWC distribution". **A DHI is not a distribution
# over the contact; it is an observation of one.** Turning it into a distribution and combining it
# with the geological one treats evidence as a competing opinion, and that is where two of these
# three go wrong.

SCENARIO, POOLED, BAYES = "scenario switch", "pooled distributions", "Bayesian update"

#: In the order a reader should meet them: the common one, the plausible-looking wrong one, the
#: defensible one.
COMBINATIONS = (SCENARIO, POOLED, BAYES)


def combination_exceedance(result: EngineResult, detection: DetectionFunction,
                           observation: DhiObservation, columns_m: np.ndarray, *,
                           method: str = BAYES, p_valid: float | None = None) -> np.ndarray:
    """``P(column >= h)`` under one of the three ways of combining a DHI with the geology.

    ``SCENARIO`` — a Bernoulli on whether the DHI is a valid contact indicator. Where it is, the
    contact is the picked one; where it is not, the geological model stands. A **mixture**, so it
    moves the contact and *widens* the answer, and it cannot move the chance at all: mixing two
    distributions can never be sharper than both. Hood's rule, and honest as far as it goes.

    ``POOLED`` — the prior multiplied by the pick likelihood alone. This is what "combine the two
    distributions" produces if you do it by multiplying, and it is **the same arithmetic as the
    Bayesian update with the detection function left out**. It conditions on having seen an
    anomaly without accounting for the fact that seeing one was more likely when the column is
    tall, so it inherits a selection effect it cannot see.

    **It drops two terms, not one, and the smaller one used to have the label.** ``POOLED`` is
    ``norm.pdf(residual)`` with nothing under it, so it omits the detection function *and*
    Cromwell's floor ``L >= 1 - p_valid``. Decomposed on the reference prospect at
    ``p_valid = 0.56``, in maximum exceedance difference (re-measured 14 Sep 2026 under the
    declared-support density; the earlier figures of 0.223 / 0.013 / 0.236 were taken with the
    sample-based one):

    ==========================================  ======
    the floor alone (holding ``D(h)`` flat)      0.286
    the detection function alone                 0.017
    both together, which is what ``POOLED`` is   0.303
    ==========================================  ======

    So the floor is most of it. That is Cromwell's rule doing visible work: without it a confident
    pick is allowed to drive realisations it dislikes to nearly zero weight, and the pooled curve
    is what that looks like.

    The detection function's own contribution depends on how much room the floor leaves it. At
    ``p_valid = 1`` -- no floor -- the two agree to five decimal places even though ``D(h)`` varies
    from 0.34 to 0.90 across the columns in play, because a 15 m pick concentrates the posterior
    into a band across which it is near enough constant to cancel. ``D(h)`` becomes decisive on
    **absence**, where there is no pick to carry the update and ``1 - D(h)`` is the entire
    likelihood, and when the **detection midpoint falls inside the columns the pick favours** --
    move ``h50_m`` to 250 m and the two part by 0.45. See
    ``tests/test_dhi.py::TestPooledIsBayesWithTheDetectionFunctionRemoved``.

    ``BAYES`` — prior x D(h) x pick likelihood. The detection function is what turns "I saw it"
    into evidence about the column rather than about your own attention, and it is what lets an
    *absent* anomaly be evidence at all. Note the direction, which is easy to invert: if only a
    tall column could have been detected, then having seen one is evidence the column is tall, so
    accounting for detectability *raises* the curve rather than discounting it.
    """
    h = np.atleast_1d(np.asarray(columns_m, dtype=float))
    above = result.column_m[None, :] >= h[:, None]

    if method == SCENARIO:
        # `p_valid` lives on the observation now, where the Bayesian likelihood also reads it, so
        # the comparison uses the same number as the model it is being compared against. It used to
        # default to a constant 0.655 while the update ran on a value derived from the DHI
        # strength -- two different answers to one question, a section apart.
        p_valid = observation.p_valid if p_valid is None else p_valid
        if not 0.0 <= p_valid <= 1.0:
            raise ValueError("P(DHI is a valid contact indicator) must be in [0, 1]")
        geological = above.mean(axis=1)
        if not observation.seen or observation.contact_m is None:
            return geological
        # The DHI branch on its own: the contact is drawn from the pick, and the apex it is
        # measured against still varies realisation by realisation. Sampled through `pick_ppf` so
        # a bounded or skewed pick is compared as itself rather than as a Gaussian.
        rng = np.random.default_rng(20260828)
        picked = observation.pick_ppf(rng.random(result.n))
        dhi_column = picked - result.apex_m
        dhi_only = (dhi_column[None, :] >= h[:, None]).mean(axis=1)
        return (1.0 - p_valid) * geological + p_valid * dhi_only

    if method == POOLED:
        if not observation.seen or observation.contact_m is None:
            return above.mean(axis=1)
        residual = (observation.contact_m - result.contact_m) / observation.pick_sigma_m
        w = norm.pdf(residual)
    elif method == BAYES:
        w = likelihood(result, detection, observation)
    else:
        raise ValueError(f"method must be one of {COMBINATIONS}, got {method!r}")

    total = float(w.sum())
    if total <= 0:
        return np.full(h.shape, np.nan)
    return (above * w[None, :]).sum(axis=1) / total
