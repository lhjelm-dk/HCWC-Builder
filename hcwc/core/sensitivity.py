"""Which elicited number actually moves the answer?

Tab 4.0 §2b ranks limits by how often they **control** the contact. That is a different question from
how much they **move** it, and the difference matters: a limit can control 60 % of realisations and
still be worth no elicitation effort, because it always bites at nearly the same depth. What an
assessor wants before spending an afternoon is the number whose *uncertainty* the answer is
sensitive to.

**Conditional expectations, from the run you already have.** Every realisation records the uniform
that produced each limit's draw, so the sample can be sliced by where each input landed in its own
distribution without re-running anything:

    swing_j = E[column | u_j in its top decile] - E[column | u_j in its bottom decile]

That is the mean outcome when input *j* came out high, minus the mean when it came out low, over
the *actual joint sample*. It therefore respects the copula for free: correlate the apex with the
spill and the spill's bar changes, because the slices are taken from correlated draws rather than
from a one-at-a-time perturbation that would have to assume independence.

**Mean, not P50** (Lars, 28 Aug 2026). The mean is what a volume is built from, it moves when the
tail moves, and a median can sit still while a limit reshapes the distribution underneath it.

**Presence is a separate bar.** A limit with ``p_active < 1`` has two kinds of influence: where it
bites, and whether it is there at all. They are different elicitations — a distribution and a
probability — and averaging them into one bar would hide which of the two to go and argue about.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hcwc.core.engine import EngineResult
from hcwc.core.limits import APEX

#: Slice width. A decile each end is a compromise: narrower is a purer conditional expectation and
#: noisier, wider dilutes the contrast. At 10 000 realisations each slice holds ~1 000 draws, which
#: is enough for a mean to be stable to well under a metre.
TAIL = 0.10

#: Kinds of influence, kept apart because they are answered by different elicitations.
DEPTH_EFFECT = "where it bites"
PRESENCE_EFFECT = "whether it is there"


@dataclass(frozen=True)
class Effect:
    """One input's influence on the mean outcome."""

    name: str
    kind: str
    low: float
    high: float
    #: Realisations behind the smaller of the two slices — the honest limit on this bar.
    support: int

    @property
    def swing(self) -> float:
        return self.high - self.low

    @property
    def magnitude(self) -> float:
        return abs(self.swing)


def _mean_or_nan(values: np.ndarray) -> float:
    return float(values.mean()) if values.size else float("nan")


def tornado(result: EngineResult, *, space: str = "column",
            successes_only: bool = False) -> list[Effect]:
    """Every input's swing on the mean, largest first.

    ``space`` is ``"column"`` (metres below the apex) or ``"depth"`` (m TVDSS). They rank
    differently and both are legitimate: the apex barely moves the column and moves the contact
    depth one-for-one, so a tool that offered only one would hide half the sensitivity.

    ``successes_only`` restricts to realisations above the assessment minimum. Off by default,
    because a limit that usually kills the prospect is under-represented among the survivors
    **because** it is the most severe — the same selection error this tool criticises in the
    published record.
    """
    if space not in ("column", "depth"):
        raise ValueError("space must be 'column' or 'depth'")
    outcome = result.column_m if space == "column" else result.contact_m
    mask = result.above_minimum if successes_only else np.ones(result.n, dtype=bool)
    outcome = outcome[mask]
    if outcome.size < 100:
        return []

    effects: list[Effect] = []

    # ---- the apex, which is column 0 of the copula and not a limit --------------------------
    apex = result.apex_m[mask]
    order = np.argsort(apex)
    cut = max(1, int(round(order.size * TAIL)))
    effects.append(Effect(
        name=APEX, kind=DEPTH_EFFECT,
        low=_mean_or_nan(outcome[order[:cut]]),
        high=_mean_or_nan(outcome[order[-cut:]]),
        support=cut))

    # ---- each limit ------------------------------------------------------------------------
    for j, limit in enumerate(result.limit_set.limits):
        u = result.uniforms[mask, j]
        low_slice = outcome[u <= TAIL]
        high_slice = outcome[u >= 1.0 - TAIL]
        if low_slice.size and high_slice.size:
            effects.append(Effect(
                name=limit.name, kind=DEPTH_EFFECT,
                low=_mean_or_nan(low_slice), high=_mean_or_nan(high_slice),
                support=int(min(low_slice.size, high_slice.size))))

        # Presence, where there is any to have. A limit that is always active has no presence
        # uncertainty and gets no bar -- an empty bar would read as "no influence", which is the
        # opposite of what p_active = 1 means.
        if not limit.always_active and limit.p_active > 0.0:
            on = result.active[mask, j]
            if on.any() and (~on).any():
                effects.append(Effect(
                    name=limit.name, kind=PRESENCE_EFFECT,
                    low=_mean_or_nan(outcome[on]),      # present -> shallower, so this is the low
                    high=_mean_or_nan(outcome[~on]),
                    support=int(min(on.sum(), (~on).sum()))))

    return sorted((e for e in effects if np.isfinite(e.swing)),
                  key=lambda e: -e.magnitude)


def baseline(result: EngineResult, *, space: str = "column",
             successes_only: bool = False) -> float:
    """The mean the swings are measured against — the centre line of the tornado."""
    outcome = result.column_m if space == "column" else result.contact_m
    mask = result.above_minimum if successes_only else np.ones(result.n, dtype=bool)
    return _mean_or_nan(outcome[mask])


# --------------------------------------------------------------------------- the DHI tornado
#
# A DHI posterior is sensitive to two very different kinds of input, and separating them is the
# whole value of the figure.
#
# **The geology** still varies realisation by realisation, so it slices exactly as above -- except
# the means are weighted, because after the update a realisation is worth its likelihood. That
# already says something: a DHI can change which limit the answer is sensitive to, and the
# geological tornado on tab 4.0 cannot show it.
#
# **The DHI's own numbers do not vary at all.** A picked contact, a pick sigma, a detection ceiling
# are single typed values -- so their influence has to be found by moving them, one at a time, and
# recomputing. That is cheap here: each perturbation is a new set of weights on the *same*
# realisations, not a new Monte Carlo, which is the one real advantage of importance weighting.
#
# It is also where the uncomfortable answers live. The pick sigma and the detection ceiling are
# usually the least defensible numbers on the tab and frequently the most influential, and a
# posterior that moves more when you change your mind about the ceiling than when you change the
# geology is one to say out loud rather than quote.

#: How far each typed DHI input is moved to measure its influence. Chosen to be defensible rather
#: than dramatic: a factor of two on an uncertainty, half a sigma on a pick, and the full plausible
#: span on the two shape parameters an assessor genuinely cannot pin down.
DHI_INPUT = "DHI input, moved"


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    total = float(weights.sum())
    return float((values * weights).sum() / total) if total > 0 else float("nan")


def effective_n(weights: np.ndarray) -> float:
    """Kish's effective sample size — how many realisations a weighted mean really rests on.

    **A count is the wrong number once weights are involved**, and this is where that bites. A
    ten-per-cent tail holds about a thousand realisations whatever the DHI says, so a bar drawn from
    it looks equally well supported before and after a sharp update. It is not: on the reference
    prospect a pick with σ = 4 m and ``p_valid = 0.98`` leaves tails of 992 realisations carrying an
    effective sample of **27**. Same bar, same width, a fortieth of the evidence.

    This is the same failure that let ``dhi.r_dhi`` be estimated from seven realisations — a
    count-based guard missing a weight-based collapse — so it is measured here rather than assumed.
    """
    w = np.asarray(weights, dtype=float)
    total = float(w.sum())
    if not np.isfinite(total) or total <= 0:
        return 0.0
    return float(total ** 2 / float(np.sum(w ** 2)))


def dhi_tornado(posterior, *, space: str = "column") -> list[Effect]:
    """What the DHI-updated mean is sensitive to — the geology, and the DHI's own numbers.

    ``posterior`` is a :class:`hcwc.core.dhi.DhiPosterior`.
    """
    from hcwc.core import dhi as dhi_core

    result = posterior.result
    outcome = result.column_m if space == "column" else result.contact_m
    base_weights = posterior.weights
    effects: list[Effect] = []

    # ---- the geology, reweighted --------------------------------------------------------
    for j, limit in enumerate(result.limit_set.limits):
        u = result.uniforms[:, j]
        low, high = u <= TAIL, u >= 1.0 - TAIL
        if low.any() and high.any():
            # Support is the *effective* sample here, not the count. The count is a fixed ten per
            # cent of the run and says nothing about how much of the posterior actually sits in the
            # tail; after a sharp update most of these weights are near zero.
            effects.append(Effect(
                name=limit.name, kind=DEPTH_EFFECT,
                low=_weighted_mean(outcome[low], base_weights[low]),
                high=_weighted_mean(outcome[high], base_weights[high]),
                support=int(round(min(effective_n(base_weights[low]),
                                      effective_n(base_weights[high]))))))

    # ---- the DHI's own typed numbers ----------------------------------------------------
    observation, detection = posterior.observation, posterior.detection

    def mean_for(det, obs) -> float:
        try:
            w = dhi_core.likelihood(result, det, obs)
        except (ValueError, ZeroDivisionError):
            return float("nan")
        return _weighted_mean(outcome, w)

    import dataclasses as _dc

    variations: list[tuple[str, object, object]] = [
        ("Pick σ", _dc.replace(observation, pick_sigma_m=observation.pick_sigma_m * 0.5),
         _dc.replace(observation, pick_sigma_m=observation.pick_sigma_m * 2.0)),
    ]
    if observation.seen and observation.contact_m is not None:
        half = 0.5 * observation.pick_sigma_m
        variations.append(
            ("Picked contact", _dc.replace(observation, contact_m=observation.contact_m - half),
             _dc.replace(observation, contact_m=observation.contact_m + half)))

    for name, low_obs, high_obs in variations:
        effects.append(Effect(name=name, kind=DHI_INPUT, support=result.n,
                              low=mean_for(detection, low_obs),
                              high=mean_for(detection, high_obs)))

    for name, low_det, high_det in (
        ("Detection ceiling", _dc.replace(detection, ceiling=max(0.05, detection.ceiling - 0.25)),
         _dc.replace(detection, ceiling=min(1.0, detection.ceiling + 0.09))),
        ("50 % detection column", _dc.replace(detection, h50_m=detection.h50_m * 0.5),
         _dc.replace(detection, h50_m=detection.h50_m * 2.0)),
        ("Transition width", _dc.replace(detection, steepness_m=detection.steepness_m * 0.5),
         _dc.replace(detection, steepness_m=detection.steepness_m * 2.0)),
    ):
        effects.append(Effect(name=name, kind=DHI_INPUT, support=result.n,
                              low=mean_for(low_det, observation),
                              high=mean_for(high_det, observation)))

    return sorted((e for e in effects if np.isfinite(e.swing)), key=lambda e: -e.magnitude)


def dhi_baseline(posterior, *, space: str = "column") -> float:
    """The posterior mean the DHI swings are measured against."""
    result = posterior.result
    outcome = result.column_m if space == "column" else result.contact_m
    return _weighted_mean(outcome, posterior.weights)
