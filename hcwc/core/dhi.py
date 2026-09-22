"""The DHI: what a seismic observation does to P(G) and to the contact distribution (8.1.6 to 8.1.8).

The geological model gives ``P(G)``, the accumulation chance, and a sample of column heights
``h`` from ``p(h | G)`` (the engine's realisations, every one conditional on the elements having
worked). A seismic observation carries two kinds of evidence and each updates one factor::

    A.  evidence index s     ->  LR(s) = f(s | HC) / f(s | NoHC)                (StrengthModel.r_at)
                             ->  P(G | s) = LR P(G) / (LR P(G) + 1 - P(G))      (p_g_given_strength)
    B.  contact geometry     ->  L(D | h, G) = c D(h) Pick(z | apex + h) + (1 - c) s   (likelihood)
                             ->  weights w_j ∝ L(D | h_j, G) on the same realisations  (update)
    C.  POS(h) = P(G | s) x P(H >= h | G, geometry)                             (prospect_pos)

The index never reaches the weights and the geometry never reaches ``P(G)``; each enters once.
One weight array (``DhiPosterior.weights``) serves the histogram, the percentiles, ``F_post``,
the controlling shares and the chance; ``P(G | s) x F_post(h)`` passes through the headline at
``h_min`` by identity, with no rescaling.

Terms of B. ``c = P(the indicated event is the contact | G, contact attributes)`` is conditional on
``G`` and carries nothing of the index. ``D(h)`` is a simplified detectability model, logistic in
column height with a ceiling below one. ``Pick`` is the pick's density in depth, its width the pick
and depth-conversion error. ``s`` is the density of a spurious event over the declared contact
range, so the mixture is a density whatever ``c`` is, and ``L / s >= 1 - c`` keeps every depth in
play (Cromwell's rule). An absent anomaly is ``1 - D(h)`` within ``G`` and a separate ratio on
``P(G)`` (``absence_ratio``); partial conformance is a censored pick.

Diagnostics that are not part of the chance: the effective sample size, the geometry
discrimination ratio ``r_dhi`` (two definitions, seen and absent), and the outcome shares of a
seen DHI (``outcome_shares``). The comparison constructions, a scenario switch and a pooled
update, are in ``hcwc.core.dhi_comparison`` and never supply a headline.

What a DHI may not do: tell the model which geological element failed. The reweighting changes
the relative frequency of mechanisms within the contact-depth ensemble the evidence favours; the
element chances on tab 2.0 are untouched.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit
from scipy.stats import norm

from hcwc.core import defaults, dists, engine
from hcwc.core.engine import EngineResult


@dataclass(frozen=True)
class DetectionFunction:
    """``D(h)`` — the chance a column of height ``h`` produces a detectable anomaly.

    Near zero below tuning thickness, rising through the resolution limit, then flat. A logistic is
    the natural default and takes the two numbers an interpreter can state: the column at which
    seeing it is a coin toss, and how sharp the transition is.

    ``ceiling`` is below 1 on purpose. Even a thick column can fail to show — wrong AVO class, poor
    acquisition, an overburden problem — and a detection function that reaches certainty makes the
    absence of an anomaly infinitely strong evidence, which it is not.

    ⚠ **The shape is a modelling choice, not physics.** A Class III sand can become *less* visible
    when very thick, as the top and base responses separate; that is a humped function, not a
    monotone one. The logistic is exposed rather than hard-coded for that reason, and
    ``archive/development_notes/DHI_alignment.md`` §9 flags it as worth a geophysicist's opinion.

    ``false_positive`` is the detector's other property: how often a trap with **no** hydrocarbons
    shows an anomaly of the class being looked for, stated relative to how often a
    hydrocarbon-filled trap of the modelled geometry does. It is what lets an absent anomaly say
    anything about whether there are hydrocarbons at all; see :func:`absence_ratio`. It is
    elicited, and no calibration is known to the tool: the default is the maximum-ignorance
    value and is labelled as such where it is shown.
    """
    h50_m: float = defaults.DETECTION_H50_M
    steepness_m: float = defaults.DETECTION_WIDTH_M
    ceiling: float = defaults.DETECTION_CEILING
    false_positive: float = defaults.DETECTION_FALSE_POSITIVE

    def __post_init__(self) -> None:
        if self.h50_m <= 0:
            raise ValueError("the 50% detection column must be positive")
        if self.steepness_m <= 0:
            raise ValueError("steepness must be positive; it is the width of the transition")
        if not 0.0 < self.ceiling <= 1.0:
            raise ValueError("the detection ceiling must be in (0, 1]")
        if not 0.0 <= self.false_positive <= 1.0:
            raise ValueError("the relative false-positive rate must be in [0, 1]")

    def at(self, column_m: np.ndarray) -> np.ndarray:
        h = np.asarray(column_m, dtype=float)
        # expit rather than 1 / (1 + exp(-x)): the same function, without the overflow the
        # explicit form raises for a column far below h50.
        return self.ceiling * expit((h - self.h50_m) / self.steepness_m)


#: The smallest *share* of below-minimum realisations that can support ``r_dhi``'s denominator,
#: and the floor on their count.
#:
#: Audit finding P2-4, 14 Sep 2026. The gate was a count, ``100``, so whether the ratio was
#: defined depended on the trial count: one per cent of ten thousand trials, ten per cent of a
#: thousand. A prospect's status should not flip because the sidebar changed. The share is the
#: quantity that means something -- it is what "a threshold a real share of realisations miss"
#: says -- and the floor keeps the denominator from being a handful of draws at small trial
#: counts. Seven, which is what the shipped prospect produced at a 5 m minimum, gives a number
#: that is entirely noise and was moving the headline chance by twelve points.
MIN_FAILURE_SHARE = 0.01
MIN_FAILURES_FLOOR = 30


def min_failures_for_r(n: int) -> int:
    """How many below-minimum realisations ``r_dhi`` needs at ``n`` trials."""
    return max(int(np.ceil(MIN_FAILURE_SHARE * n)), MIN_FAILURES_FLOOR)


#: How the pick is shaped. All three are elicited in **m TVDSS** rather than as an error term,
#: because an interpreter can argue about a depth and cannot argue about a sigma.
NORMAL, PERT, UNIFORM = "normal", "pert", "uniform"
PICK_SHAPES = (NORMAL, PERT, UNIFORM)


@dataclass(frozen=True)
class DhiObservation:
    """What was actually observed on the seismic.

    ``seen = False`` is a real observation and not a missing one: an amplitude absent where one was
    expected is evidence, and with a detection function it needs no special handling — the
    likelihood becomes ``1 - D(h)``, which is largest at small ``h``.

    **The pick has a shape, not just a width.** Three controls do three separate things, and they
    were tangled together for as long as the only one was ``pick_sigma_m``:

    * *skew* decides the reading **at** the picked contact. A symmetric pick puts the posterior
      median on the pick, so the exceedance there is about half the POS. Skewing it deep — the
      claim that an amplitude termination under-calls, which tuning and resolution loss at the base
      of a column both argue for — moves that reading up.
    * *width* decides how fast the chance falls **below** the pick.
    * ``p_valid`` decides the floor under all of it, and is the subject of :func:`likelihood`.

    **``p_valid`` is ``P(the picked event is the contact | G, contact attributes)``.** Conditional
    on hydrocarbons being present, because every realisation it weights already is. It is the
    contact-attribute judgement -- conformance, flatness, whether the event cuts structure -- and
    nothing else: it carries neither ``P(G)`` nor any function of the evidence index, which would
    count the chance of hydrocarbons twice (once here, once where the index is applied).

    **``p_valid`` is taken independent of ``h``** (audit, 16 Sep 2026). One number weights the
    mixture for every realisation: the chance that the picked event is the contact is not made
    to depend on how tall the column is. A taller column could make a conformable event more
    likely to be its base; that dependence is not modelled, and ``D(h)`` is where the column
    height enters the valid branch instead. Stated in 8.1.7 and pinned by
    ``tests/test_dhi_audit.py``.

    It defaults to 1.0 so that constructing an observation the old way reproduces the old numbers
    exactly. The app never passes 1.0, for Cromwell's rule: at ``p_valid = 1`` a bounded pick shape
    assigns probability zero below its deepest bound, and no later evidence can ever revive a zero.
    """
    seen: bool
    contact_m: float | None = None
    pick_sigma_m: float = 15.0
    area_km2: float | None = None
    pick_shape: str = NORMAL
    shallowest_m: float | None = None
    deepest_m: float | None = None
    p_valid: float = 1.0
    absent_below_m: float | None = None

    @property
    def is_partial(self) -> bool:
        """Partial conformance: bright over the crest, reliably absent below a depth.

        The third observation, and the one the tab could not take. An interpreter often has an
        anomaly that is convincingly there and convincingly *stops*, without a down-dip termination
        clean enough to pick a contact on. Forced into the two cases that existed, it had to be
        entered either as a pick it does not support -- overstating what was seen -- or as *absent*,
        which throws away the fact that something is there. Neither is the observation.
        """
        return self.absent_below_m is not None

    def __post_init__(self) -> None:
        if self.is_partial:
            if not self.seen:
                raise ValueError(
                    "partial conformance is a *seen* anomaly -- bright over the crest and absent "
                    "below a depth. An anomaly that was never seen at all is the `seen=False` case"
                )
            if self.contact_m is not None:
                raise ValueError(
                    "partial conformance has no picked contact, and that is the point of it: the "
                    "anomaly stops without a down-dip termination clean enough to pick. Give "
                    "`absent_below_m` or `contact_m`, not both"
                )
        elif self.seen and self.contact_m is None:
            raise ValueError("an observed anomaly needs a picked contact depth")
        if self.pick_sigma_m <= 0:
            raise ValueError(
                "the pick sigma must be positive; it is the flat-spot pick uncertainty **plus** "
                "the depth-conversion error, which is the larger of the two on most prospects"
            )
        if self.pick_shape not in PICK_SHAPES:
            raise ValueError(f"pick_shape must be one of {PICK_SHAPES}, got {self.pick_shape!r}")
        if not 0.0 < self.p_valid <= 1.0:
            raise ValueError(
                "p_valid is the chance the picked event really is the contact, so it must lie in "
                "(0, 1]. Zero would say the observation is meaningless; it is never exactly zero "
                "or the DHI would not have been picked at all"
            )
        if self.seen and not self.is_partial and self.pick_shape != NORMAL:
            if self.shallowest_m is None or self.deepest_m is None:
                raise ValueError(f"a {self.pick_shape} pick needs both a shallowest and a "
                                 "deepest depth, in m TVDSS")
            if not self.shallowest_m < self.deepest_m:
                raise ValueError("the deepest possible contact must be below the shallowest")
            if self.pick_shape == PERT and not (
                    self.shallowest_m <= self.contact_m <= self.deepest_m):
                raise ValueError("the picked contact is the PERT's mode and must lie in range")

    def pick_pdf(self, contact_m: np.ndarray) -> np.ndarray:
        """Density over where the contact is, **given the picked event really is the contact**.

        This is only half of the likelihood. The other half — the world where the picked event is
        lithology, diagenesis, fizz gas or an artefact — is flat in depth and lives in
        :func:`likelihood`, which is what keeps a bounded shape here from becoming a claim of
        impossibility.
        """
        z = np.asarray(contact_m, dtype=float)
        if self.pick_shape == NORMAL:
            return norm.pdf((self.contact_m - z) / self.pick_sigma_m) / self.pick_sigma_m
        if self.pick_shape == UNIFORM:
            return dists.uniform_pdf(z, self.shallowest_m, self.deepest_m)
        return dists.pert_pdf(z, self.shallowest_m, self.contact_m, self.deepest_m)

    def pick_ppf(self, u: np.ndarray) -> np.ndarray:
        """Draws from the same pick, for the code that needs samples rather than a density.

        The scenario-switch comparison builds a *branch* of realisations rather than reweighting
        one, so it needs to sample the pick. Without this it sampled a Gaussian regardless of the
        shape chosen, which quietly made the comparison a comparison with something else.
        """
        u = np.asarray(u, dtype=float)
        if self.pick_shape == NORMAL:
            return norm.ppf(u, loc=self.contact_m, scale=self.pick_sigma_m)
        if self.pick_shape == UNIFORM:
            return dists.uniform_ppf(u, self.shallowest_m, self.deepest_m)
        return dists.pert_ppf(u, self.shallowest_m, self.contact_m, self.deepest_m)


def spurious_density(support_m: tuple[float, float]) -> float:
    """``s`` — the density of a flat event that is *not* the contact, at any one depth.

    Taken as uniform over the model's declared contact support -- the interval
    :meth:`hcwc.core.limits.LimitSet.contact_support_m` returns, apex to the deepest always-active
    limit: an event that has nothing to do with the hydrocarbon column is equally likely to turn
    up anywhere in the closure. It is the same value in the success and the failure world, and
    that equality is load-bearing — *is hydrocarbon present* is the strength channel's question
    and it answers it once. Letting ``s`` differ between the two worlds would answer it twice.

    **From the declared support, not the sample.** Until 14 Sep 2026 this was ``1 / (max − min)``
    of the realised contacts, which made the pick's likelihood depend on the trial count, the
    seed, and whichever extreme the sampler happened to reach: on the reference prospect the
    density moved by four per cent between a 2 000- and a 50 000-trial run of the same model. A
    likelihood is a property of the model, and this one now is.

    Only the ratio to the pick density matters, so the overall rate of spurious events cancels and
    never has to be elicited.
    """
    shallow, deep = float(support_m[0]), float(support_m[1])
    span = deep - shallow
    if not span > 0:
        raise ValueError(f"the contact support must have positive width, got {support_m}")
    return 1.0 / span


def likelihood(result: EngineResult, detection: DetectionFunction,
               observation: DhiObservation) -> np.ndarray:
    """``L(seismic | h)`` for every realisation.

    **Not seen:** ``1 - D(h)``. Its own floor is already built in — ``DetectionFunction.ceiling``
    is below 1 on purpose, so an absent anomaly is never infinitely strong evidence either.

    **Seen**, with ``V`` for *the event I picked really is the hydrocarbon–water contact*::

        L = p_valid · D(h) · Pick(z_DHI | apex + h)   +   (1 - p_valid) · s

    with ``s = 1 / span`` from :func:`spurious_density`, the declared contact support. Both
    branches are densities in depth: ``Pick`` integrates to one over depth and ``s`` integrates to
    one over the support, so the mixture is a density in depth whatever ``p_valid`` is.

    The detection function gates **only** the first branch. "Would a column this tall have produced
    a visible anomaly" is a question that means something only when the anomaly is the column's; in
    the second branch, seeing the event had nothing to do with the column.

    In the second branch the likelihood is flat in ``h``, so the geological prior passes through
    untouched. That is what gives the update its floor: since ``Pick(·) >= 0``,

        L / s  >=  1 - p_valid

    at every depth. No depth is excluded by one seismic interpretation (Cromwell's rule), which
    is what makes a bounded pick shape safe to offer. The floor is a bound from below on each
    depth, not a cap on discrimination: the ratio of likelihoods between two depths is at most
    ``1 + p_valid · D · Pick_max / ((1 - p_valid) · s)`` and grows as the pick narrows.

    **Partial conformance** -- bright over the crest, reliably absent below ``z_off``. Neither of
    the other two: something is there, so the strength channel applies in full, but there is no
    down-dip termination to pick. What the observation carries is a *bound*: the anomaly's edge
    lies above ``z_off``, to within the same pick-and-depth-conversion error a picked contact
    carries. That is a **censored observation** of the contact, and the arithmetic is the standard
    one for it::

        L = p_valid · D(h) · Φ((z_off − (apex + h)) / σ)   +   (1 − p_valid)

    with ``σ = pick_sigma_m`` and the apex drawn **per realisation**, because a depth means nothing
    until it is converted against the apex it belongs to. Read it against the pick: a picked
    contact is a normal *density* at ``z``; a bound is the normal *cumulative* at ``z_off``. Same
    error, same interpreter, same ``σ`` -- one statement of *where the edge is*, made with less
    precision.

    ``Φ`` is one half at the cutoff, near one for a contact well above it, near zero well below.
    The transition is soft, and its width is a number the interpreter can state: how well the
    depth below which the anomaly is reliably absent is known. It is not a hard bound, for two
    reasons that are visible in the formula rather than buried in it: ``σ`` spreads the edge, and
    the ``1 − p_valid`` branch keeps ``L`` above zero however far below the cutoff a column sits
    (Cromwell, as for a pick).

    ``D(h)`` is the same first factor as for a picked anomaly and does the same job: something was
    seen, so the column was tall enough to be visible at all. It is not applied a second time.

    **What this replaced, and why.** Until 14 Sep 2026 the bound was
    ``D(h) · [1 − D((h − h_off)+)]``: the detection function applied once to the column and once
    to the slice of it below the cutoff, as though "seen above" and "not seen below" were two
    independent detections of two separate thicknesses. They are not -- the down-dip edge of one
    anomaly is one observation -- and the form had no parameter of its own. Its softness came
    from ``h50`` and its steepness, elicited for whether a column shows at all, and its floor
    inside the valid branch was ``1 − ceiling``, so the strength of the bound was set by a number
    elicited for a different question. With the shipped defaults that put the fifty-per-cent
    point 25 m *below* the stated cutoff. The censored form has one parameter, already on the
    observation, meaning what it says.

    This is a soft, censored constraint on the depth of the anomaly's edge, not a forward model
    of the amplitude response: nothing in it says how bright the event should be at a depth,
    only how likely the recorded edge is above ``z_off`` given where the contact is.

    Here both branches are **probabilities** of the event *edge recorded above z_off*, not
    densities, so the spurious branch is the constant ``1`` rather than the ``s = 1 / span`` of
    the picked case -- and the value is right, not merely convenient. In the world
    where the bright event is lithology or fizz, its down-dip edge is wherever that thing happens
    to end, so *this observation is what you would have recorded whatever the column did*. The
    branch explains the data perfectly, which is what makes it a floor: ``L >= 1 - p_valid``, and
    partial conformance can never rule a column out. That the floor is high -- a much larger share
    of the likelihood than the pick's ``s`` -- is the honest reading. "Bright above, absent below"
    is weaker evidence than a contact you can pick, and the arithmetic should not pretend otherwise.

    There is no ``V`` branch in the failure world: with no accumulation there is no contact to
    indicate, so ``p_valid`` is properly ``P(V | G)`` and appears only here.

    **Everything in this function is conditional on ``G``.** ``result.column_m`` is a sample from
    ``p(h | G)``, and the value returned is ``L(geometry | h, G)``. Nothing about whether there is
    hydrocarbon at all belongs in it: that question is the strength channel's, answered once in
    :func:`prospect_pos` by updating ``P(G)``, and never inside a term that already assumes ``G``.
    """
    d = detection.at(result.column_m)
    if not observation.seen:
        return 1.0 - d
    if observation.is_partial:
        h_off = observation.absent_below_m - result.apex_m
        if not np.any(h_off > 0.0):
            raise ValueError(
                f"the anomaly is said to be absent below {observation.absent_below_m:,.0f} m, "
                f"which is at or above the apex in every realisation (the apex reaches "
                f"{float(result.apex_m.min()):,.0f} m). There is no closure above that depth for "
                f"the anomaly to have been seen in, so the observation describes no prospect. It "
                f"has to be a depth inside the closure."
            )
        # P(the observed edge lies above z_off | true contact at z), with the pick error on the
        # edge. `h_off - column` is `z_off - z` in column space, the apex cancelling.
        valid = d * norm.cdf((h_off - result.column_m) / observation.pick_sigma_m)
        if observation.p_valid >= 1.0:
            return valid
        return observation.p_valid * valid + (1.0 - observation.p_valid)
    valid = d * observation.pick_pdf(result.contact_m)
    if observation.p_valid >= 1.0:
        return valid
    return (observation.p_valid * valid
            + (1.0 - observation.p_valid)
            * spurious_density(result.limit_set.contact_support_m()))


def likelihood_branches(result: EngineResult, detection: DetectionFunction,
                        observation: DhiObservation) -> tuple[np.ndarray, np.ndarray]:
    """The two branches of the seen-pick likelihood, each already carrying its mixing weight.

    ``valid = c · D(h) · Pick(z)`` is the DHI as the contact; ``spurious = (1 − c) · s`` is the
    DHI as something else, flat in depth. Their sum is :func:`likelihood`, which keeps its own
    arithmetic so the weights stay bit-identical to the pinned baseline. Kept apart so that
    the posterior mass inside the indicated contact band can be split into the part the pick
    put there and the part the geology put there by itself (:func:`outcome_shares`; 8.1.8).
    Seen, picked observations only; the absent and partial forms have no indicated contact.
    """
    if not observation.seen or observation.is_partial:
        raise ValueError("the likelihood has two branches only for a seen, picked anomaly")
    d = detection.at(result.column_m)
    valid = observation.p_valid * d * observation.pick_pdf(result.contact_m)
    if observation.p_valid >= 1.0:
        return valid, np.zeros_like(valid)
    spurious = np.full_like(valid, (1.0 - observation.p_valid)
                            * spurious_density(result.limit_set.contact_support_m()))
    return valid, spurious


#: The outcomes of a seen DHI, in depth order, as 8.1.8 names them. The first is off the depth
#: axis; the four others share P(G | s) between them.
OUTCOME_NO_HC = "no hydrocarbons"
OUTCOME_ABOVE = "above the indicated contact"
OUTCOME_AT_BY_DHI = "at the indicated contact, because of it"
OUTCOME_AT_BY_CHANCE = "at the indicated contact, by coincidence"
OUTCOME_BELOW = "below the indicated contact"
OUTCOMES: tuple[str, ...] = (OUTCOME_NO_HC, OUTCOME_ABOVE, OUTCOME_AT_BY_DHI,
                             OUTCOME_AT_BY_CHANCE, OUTCOME_BELOW)


@dataclass(frozen=True)
class OutcomeShares:
    """What the DHI can turn out to have been, with the chance of each (8.1.8).

    ``band_m`` is the indicated contact band, the P99 to P1 of the pick. ``shares`` sum to one:
    ``no hydrocarbons`` is ``1 − P(G | s)``, and the four outcomes on the depth axis are the
    posterior mass of the contact above the band, within it and below it, times ``P(G | s)``;
    the mass within the band is split by the branch of the likelihood that put it there.
    ``attribution`` is the posterior chance the DHI is the contact, the valid branch's share of
    all the posterior mass, band or not.
    """
    band_m: tuple[float, float]
    shares: dict[str, float]
    attribution: float

    @property
    def p_g_given_s(self) -> float:
        return 1.0 - self.shares[OUTCOME_NO_HC]


def outcome_shares(posterior: DhiPosterior, p_g_given_s: float) -> OutcomeShares | None:
    """The outcomes of 8.1.8 on this posterior, or ``None`` when the observation is not a pick.

    Everything here is read off objects the update already holds: the weights, the two branches
    of the likelihood, and the pick's own percentiles. Nothing is re-simulated. The shares use
    every realisation, not the success cases only, because the outcomes are about where the
    contact is and not about a threshold.
    """
    obs = posterior.observation
    if not obs.seen or obs.is_partial:
        return None
    top, base = (float(v) for v in obs.pick_ppf(np.array([0.01, 0.99])))
    valid, spurious = likelihood_branches(posterior.result, posterior.detection, obs)
    total = float(valid.sum() + spurious.sum())
    if not np.isfinite(total) or total <= 0.0:
        return None
    z = posterior.result.contact_m
    above, within, below = z < top, (z >= top) & (z <= base), z > base
    p = float(np.clip(p_g_given_s, 0.0, 1.0))
    mass = lambda w, m: float(w[m].sum()) / total  # noqa: E731
    shares = {
        OUTCOME_NO_HC: 1.0 - p,
        OUTCOME_ABOVE: p * (mass(valid, above) + mass(spurious, above)),
        OUTCOME_AT_BY_DHI: p * mass(valid, within),
        OUTCOME_AT_BY_CHANCE: p * mass(spurious, within),
        OUTCOME_BELOW: p * (mass(valid, below) + mass(spurious, below)),
    }
    return OutcomeShares(band_m=(top, base), shares=shares,
                         attribution=float(valid.sum()) / total)


@dataclass(frozen=True)
class DhiPosterior:
    """The prior and posterior as one object, because they are one object."""
    result: EngineResult
    weights: np.ndarray
    #: The DHI channel, when there is one. **Both are optional** so that a prospect with an offset
    #: penetration and no amplitude can still produce an updated distribution: the weights are the
    #: object, and where they came from is metadata. Everything that reads these two -- the
    #: walkthrough, the tornado -- is reached only from the DHI path and can rely on them there.
    detection: "DetectionFunction | None" = None
    observation: "DhiObservation | None" = None

    @property
    def effective_sample_size(self) -> float:
        """Kish's ESS. Reweighting throws information away, and this says how much.

        Below a few hundred the posterior rests on too few realisations to be read, which happens
        when the picked contact sits far out in the tail of the geological prior — itself a finding
        worth surfacing rather than a number to quietly report.
        """
        w = self.weights
        return float(w.sum() ** 2 / np.sum(w**2)) if np.any(w > 0) else 0.0

    def exceedance(self, column_m: np.ndarray | float, *, posterior: bool = True) -> np.ndarray:
        """``F(h)``, prior or posterior."""
        return engine.exceedance(self.result.column_m, column_m,
                                 None if not posterior else self.weights)

    def pos(self, *, posterior: bool = True) -> float:
        """``F(h_min)`` — the min-volume POS, read off the same curve as everything else."""
        return float(self.exceedance(self.result.limit_set.min_column_m, posterior=posterior)[0])

    def percentiles(self, exceedance_pct: np.ndarray | float, *,
                    posterior: bool = True) -> np.ndarray:
        """Contact depth at exceedance percentiles. P100 shallowest, P0 deepest.

        :func:`hcwc.core.engine.weighted_percentiles`, the same estimator the engine uses, so
        the prior read here is the prior tab 4 prints.
        """
        keep = self.result.above_minimum
        return engine.weighted_percentiles(self.result.contact_m[keep],
                                           self.weights[keep] if posterior else None,
                                           exceedance_pct)

    @property
    def r_dhi(self) -> float:
        """The geometry discrimination ratio: a diagnostic of the geometry likelihood, not ``LR(s)``.

        Not part of the chance. Both sets it compares are inside ``G``, so it is a ratio between
        two column-height hypotheses and never between an accumulation and none; the geometry's
        effect on the chance is ``P(h ≥ h_min | G, geometry)`` (:meth:`pos`), and
        :func:`prospect_pos` multiplies that by ``P(G | s)``. This number says how much the
        geometry likelihood discriminates, for the trust panel and the comparison constructions.

        Two definitions, one per observation, and the caller must show the one that applies:

        * seen anomaly: ``E[L | h ≥ h_min] / E[L | h < h_min]``, the likelihood averaged over the
          realisations that meet the assessment minimum divided by its average over those that
          fall short (E-POS's ``r_dfi`` construction). Undefined (``nan``) when fewer than
          :func:`min_failures_for_r` realisations fall short: a ratio from a handful of draws is
          noise, and a neutral observation must not move anything.
        * absent anomaly: ``E[1 − D(h) | h ≥ h_min] / 1``, the average chance that a column meeting
          the minimum would have shown nothing, against a barren trap taken to show nothing with
          certainty. The denominator is an assumption on the generous side: a barren trap can
          throw a spurious event, and allowing for that would make absence weaker evidence still.

        ``nan`` when the posterior carries no DHI observation (well control alone).
        """
        # No DHI, no `r_dhi`. A prospect updated by well control alone has a perfectly good
        # posterior and no likelihood ratio *against an amplitude* to report, and returning some
        # number computed from the well's weights under E-POS's name for the DHI ratio would be
        # the wrong quantity wearing the right label.
        if self.observation is None:
            return float("nan")
        success = self.result.above_minimum
        if not self.observation.seen:
            # Still undefined when nothing succeeds: with no success set there is no
            # `E[1 - D(h) | success]` to take, and averaging over the failures instead would be a
            # different quantity wearing the same name.
            return float(self.weights[success].mean()) if success.any() else float("nan")
        if not success.any() or int((~success).sum()) < min_failures_for_r(self.result.n):
            return float("nan")
        return float(self.weights[success].mean() / self.weights[~success].mean())


def geometry_ratio_definition(posterior: DhiPosterior) -> str:
    """The definition of :attr:`DhiPosterior.r_dhi` that applies to this posterior, as text."""
    obs = posterior.observation
    if obs is None:
        return "no DHI observation; the geometry ratio is not defined"
    if not obs.seen:
        return "E[1 − D(h) | h ≥ h_min] against a barren trap showing nothing"
    return "E[L | h ≥ h_min] / E[L | h < h_min], the geometry likelihood's average over the columns that meet the minimum against those that fall short"


def posterior_indices(posterior: DhiPosterior, n: int | None = None,
                      seed: int = 20260904) -> np.ndarray:
    """The posterior as a sequence of realisation indices, drawn by weight with replacement.

    Figure 5.2.1a walks a window of fifty through the run; given the DHI it can walk the same
    window through the posterior instead, and what it then shows is the
    geological realisations resampled by their weights: each one is a run realisation, limits
    and controller intact, appearing as often as the evidence favours it. The order is one
    fixed draw so the slider is stable between reruns. All realisations, not the success
    cases only, because the figure draws the whole run. Returns ``np.arange(n)`` when the
    weights cannot be normalised.
    """
    n_out = posterior.result.n if n is None else int(n)
    weights = np.asarray(posterior.weights, dtype=float)
    total = float(weights.sum())
    if weights.size == 0 or not np.isfinite(total) or total <= 0:
        return np.arange(n_out)
    rng = np.random.default_rng(seed)
    return rng.choice(weights.size, n_out, replace=True, p=weights / total)


def posterior_columns(posterior: DhiPosterior, n: int = 10_000,
                      seed: int = 20260904) -> np.ndarray:
    """The updated column distribution as a **sample**, success cases only.

    The posterior lives as weights on the prior's realisations, and anything that needs a
    distribution rather than a curve -- the benchmark comparison on tab 6.0, the export -- needs
    those weights collapsed. Importance resampling with replacement, which is exact in the limit and
    honest about the effective sample size the tab already reports.

    **Columns, not contacts minus an apex.** The tempting shortcut is to take the resampled contacts
    the overlay already carries and subtract a median apex, and it is wrong by however much the apex
    varies between realisations -- which is a quantity this tool spends a whole section on. The
    engine holds ``column_m`` per realisation, so no apex arithmetic is needed at all.

    Success cases only, because every trap in every benchmark this feeds is a discovery.

    Returns an empty array when there is nothing to resample: no success cases, or weights that sum
    to zero because the evidence rules out everything the model drew.
    """
    keep = posterior.result.above_minimum
    columns = np.asarray(posterior.result.column_m, dtype=float)[keep]
    weights = np.asarray(posterior.weights, dtype=float)[keep]
    total = float(weights.sum())
    if columns.size == 0 or not np.isfinite(total) or total <= 0:
        return np.asarray([], dtype=float)
    rng = np.random.default_rng(seed)
    return columns[rng.choice(columns.size, int(n), p=weights / total)]


def update(result: EngineResult, detection: DetectionFunction,
           observation: DhiObservation) -> DhiPosterior:
    """Formulation B — reweight the geological realisations by the seismic likelihood.

    Importance weighting rather than re-running: the engine's realisations *are* a sample from the
    prior, so the posterior is the same sample with weights. Nothing is re-simulated, the
    controlling-limit bookkeeping survives intact, and prior and posterior are guaranteed to be
    talking about the same realisations — which is what makes ``F(h)`` comparable between them.
    """
    w = likelihood(result, detection, observation)
    if not np.isfinite(w).all():
        raise ValueError("the likelihood produced non-finite weights")
    if w.sum() <= 0:
        raise ValueError(
            "every realisation has zero likelihood, so there is no posterior. The picked contact "
            "lies outside everything the geological model considers possible — which is a finding "
            "about the model or the pick, not a number to report"
        )
    return DhiPosterior(result=result, weights=w, detection=detection, observation=observation)


def p_g_given_strength(p_g: float, r_strength: float) -> float:
    """Step A: the element chance updated by the amplitude character alone.

    :func:`simm_update` under the name of the job it does here, so that a reader of
    :func:`prospect_pos` sees which factor the strength touches. It is the only place the
    strength enters.
    """
    return simm_update(p_g, r_strength)


def absence_ratio(result: EngineResult, detection: DetectionFunction) -> float:
    """The likelihood ratio on ``G`` carried by an anomaly that is absent where one was looked for.

    Audit finding P1-0, 14 Sep 2026. The engine's realisations are conditional on ``G``, so the
    absent case's ``1 - D(h)`` weights can only reshape the column; they cannot lower the chance
    that there are hydrocarbons, and until this function the character channel was held neutral
    when nothing was seen. E-POS's principle -- an amplitude absent where one was expected lowers
    P(G) -- and Monigle et al. (2025) both put absence on the chance. This is that ratio::

        R_absent = P(absent | G) / P(absent | not G)
                 = (1 - d) / (1 - f · d),      d = E[D(h)] over the geological columns

    ``d`` is the chance a hydrocarbon-filled trap of the modelled geometry shows, averaged over
    ``p(h | G)``; ``f`` is :attr:`DetectionFunction.false_positive`, the barren trap's chance of
    showing stated relative to ``d``. Tying the false-positive rate to ``d`` is a modelling
    choice, made so that the ratio behaves at the ends: where nothing could have shown
    (``d -> 0``) absence is uninformative, ``R = 1``, whatever ``f`` says; where a barren trap
    shows as readily as a filled one (``f = 1``) likewise. Since ``f·d <= d`` the ratio is never
    above 1 -- absence never counts *for* hydrocarbons -- and with ``f = 0`` it is ``1 - d``, the
    strongest case. Bounded below at ``1 / R_SINGLE_CHANNEL`` like every other single channel.
    """
    d = float(np.mean(detection.at(result.column_m)))
    r = (1.0 - d) / (1.0 - detection.false_positive * d)
    return float(np.clip(r, 1.0 / R_SINGLE_CHANNEL, 1.0))


def applied_ratio(result: EngineResult, detection: DetectionFunction,
                  observation: DhiObservation, r_strength: float) -> float:
    """The ratio that updates ``P(G)`` for this observation.

    A seen anomaly is graded on the strength axis and ``r_strength`` is applied as it stands. An
    absent one has no character to grade, so the strength is ignored and :func:`absence_ratio`
    is applied instead. One function, so the tab, the leverage sweep and the paper's figures
    cannot disagree about which ratio the absent case carries.
    """
    return float(r_strength) if observation.seen else absence_ratio(result, detection)


def prospect_pos(p_g: float, r_strength: float, posterior: DhiPosterior) -> float:
    """Step C: the prospect chance at the assessment minimum, given the DHI.

    ``P(G | strength) × P(h ≥ h_min | G, geometry)``. The first factor is the element product from
    tab 2.0 updated by the character channel; the second is :meth:`DhiPosterior.pos`, read off the
    same weights that draw the posterior histogram and the percentiles. There is no third factor
    and no blending: the two channels answer different questions -- *is there hydrocarbon* and
    *given there is, how far down* -- and each answers its own once.

    This replaces ``CombinedUpdate.posterior_pos`` as the headline. That construction updated
    ``P(G) · F_prior(h_min)`` by a blend of the strength ratio and ``r_dhi``; ``r_dhi`` is a ratio
    between two column heights inside ``G`` and is not a likelihood ratio on the prospect, and the
    strength had already reached the weights through ``p_valid``. The result was a headline that
    was not the integral of the distribution drawn beside it, so the curve had to be rescaled to
    pass through it. This one passes through by construction: see :func:`prospect_pos_curve`.
    """
    return float(p_g_given_strength(p_g, r_strength) * posterior.pos())


def prospect_pos_curve(p_g: float, r_strength: float, posterior: DhiPosterior,
                       columns_m: np.ndarray) -> np.ndarray:
    """``P(G | strength) × F_post(h)`` on a grid of column heights: the chance against threshold.

    Read at ``posterior.result.limit_set.min_column_m`` it equals :func:`prospect_pos` exactly,
    because both are the same product of the same two numbers. That identity is what lets the
    figure on the DHI tab be drawn without the rescaling it needed under the blended headline.
    """
    return p_g_given_strength(p_g, r_strength) * np.asarray(posterior.exceedance(columns_m),
                                                             dtype=float)


@dataclass(frozen=True)
class Outcome:
    """The two numbers a reader takes off the DHI tab, together.

    Kept as one object because they answer different questions and an input can move one without
    the other: the amplitude character moves the chance and leaves the contact where the geology
    put it, while the pick does the reverse. Reporting only one of them is how a control comes to
    look dead when it is not.
    """
    #: :func:`prospect_pos` -- ``P(G | strength) × P(h ≥ h_min | G, geometry)``.
    pos: float
    #: The posterior median contact, m TVDSS, over the success cases. ``nan`` if there are none.
    contact_m: float


def outcome(result: EngineResult, detection: DetectionFunction, observation: DhiObservation, *,
            p_g: float, r_strength: float) -> Outcome:
    """Run one full state of the tab and report what a reader would see.

    The whole chain in one call -- reweight within ``G``, update ``P(G)`` by the strength,
    multiply -- so that :func:`leverage` can vary one input and be sure everything downstream of
    it moved with it. ``observation.p_valid`` is the contact-attribute judgement ``c`` and
    nothing else; see :class:`DhiObservation`.
    """
    post = update(result, detection, observation)
    r = applied_ratio(result, detection, observation, r_strength)
    return Outcome(pos=prospect_pos(p_g, r, post),
                   contact_m=float(post.percentiles(50.0)[0]))


@dataclass(frozen=True)
class Leverage:
    """How far one input moves the answer across the range that was swept.

    ``nan`` in :attr:`pos_points` means the sweep could not be run: fewer than two of the values
    produced a state the model would enter. That is a finding rather than a failure and is
    reported as "not measurable" rather than as a zero, because zero is the answer for a control
    that does nothing and this is not that. ``nan`` in :attr:`contact_m` alone is weaker -- the
    chance was measurable but there were not two success sets to compare contacts across.
    """
    #: Swing in the prospect chance, in **percentage points**.
    pos_points: float
    #: Swing in the posterior median contact, in metres.
    contact_m: float
    #: The values that produced the extremes, low then high, for a reader who wants to check.
    at: tuple[float, float] | tuple[None, None] = (None, None)
    #: The ends of the range that was actually swept.
    #:
    #: Reported because it is rarely the widget's own range and a caption that said "across
    #: its whole range" without it would be overclaiming: the pick sigma box accepts 1 to
    #: 500 m and is swept over 3 to 120, which is where an interpreter would ever put it,
    #: and the picked depth is swept over what the geological model considers possible
    #: rather than over the whole water column.
    span: tuple[float, float] | tuple[None, None] = (None, None)

    @property
    def measurable(self) -> bool:
        return bool(np.isfinite(self.pos_points))

    @property
    def inert(self) -> bool:
        """Below what a reader could act on: a tenth of a point and a tenth of a metre.

        Not a tolerance on the arithmetic -- these are exact -- but on the decision. An input that
        cannot move the chance by a tenth of a point is not an input, whatever else it is.
        """
        if not self.measurable:
            return False
        moved_depth = np.isfinite(self.contact_m) and abs(self.contact_m) >= 0.1
        return abs(self.pos_points) < 0.1 and not moved_depth


def leverage(build, values) -> Leverage:
    """Sweep one input over ``values`` and measure the swing, holding everything else fixed.

    ``build(v)`` returns the ``(result, detection, observation, p_g, r_strength)`` the tab would
    be in with that input at ``v`` -- everything, because an input such as the assessment minimum
    changes the realisation set and not merely the likelihood, and a sweep that varied only the
    likelihood would report a smaller number than the truth. ``p_g`` is the element product, not
    the prior prospect chance: the chain multiplies it by the conditional column term itself.

    One-at-a-time, which is the honest reading of a slider: *this* control, from where everything
    else currently stands. It is not a variance decomposition and does not claim to be -- the
    tornado in the sensitivity section is the tool for interactions.
    """
    tried: list[tuple[float, Outcome]] = []
    for v in values:
        try:
            args = build(v)
        except (ValueError, ZeroDivisionError):
            continue
        try:
            tried.append((v, outcome(args[0], args[1], args[2], p_g=args[3],
                                     r_strength=args[4])))
        except ValueError:
            # A state the model refuses -- every realisation ruled out, most often. Skipped rather
            # than counted as an extreme, because "the chance is zero there" and "the model will
            # not go there" are different statements and only the first is a leverage.
            continue
    usable = [(v, o) for v, o in tried if np.isfinite(o.pos)]
    if len(usable) < 2:
        return Leverage(float("nan"), float("nan"))
    lo = min(usable, key=lambda p: p[1].pos)
    hi = max(usable, key=lambda p: p[1].pos)
    contacts = [o.contact_m for _, o in usable if np.isfinite(o.contact_m)]
    spread = (max(contacts) - min(contacts)) if len(contacts) >= 2 else float("nan")
    return Leverage(pos_points=100.0 * (hi[1].pos - lo[1].pos), contact_m=spread,
                    at=(lo[0], hi[0]),
                    span=(min(v for v, _ in usable), max(v for v, _ in usable)))


def area_cross_check(depths_m: np.ndarray, areas_km2: np.ndarray, dhi_area_km2: float,
                     dhi_contact_m: float) -> dict[str, float]:
    """A DHI gives **two** readings of the contact. They should agree.

    The down-dip amplitude termination gives one. The areal extent, taken through the area–depth
    table, gives another. Disagreement is information, and nothing forces the two to agree:

    * ``area implies shallower`` — the anomaly is narrower than its down-dip limit implies, so it
      may not be filling the closure: a stratigraphic or diagenetic component, or a smaller
      effective trap.
    * ``area implies deeper`` — the anomaly extends beyond the mapped conformance, so suspect a
      non-fluid cause: lithology, or tuning.
    """
    depths = np.asarray(depths_m, dtype=float)
    areas = np.asarray(areas_km2, dtype=float)
    if depths.size != areas.size or depths.size < 2:
        raise ValueError("depths and areas must be the same length, and at least two long")
    if not np.all(np.diff(areas) >= -1e-9):
        raise ValueError("area must increase with depth for the inversion to be single-valued")
    from_area = float(np.interp(dhi_area_km2, areas, depths))
    return {"from_area_m": from_area, "from_termination_m": float(dhi_contact_m),
            "disagreement_m": from_area - float(dhi_contact_m)}


def containment_ok(depths_m: np.ndarray, areas_km2: np.ndarray, apex_m: float,
                   min_column_m: float, dhi_area_km2: float) -> tuple[bool, str]:
    """``A(h_min) <= A_DHI`` — a constraint that is easy to state and easy to leave unenforced.

    If the minimum-case area is *larger* than the DHI area, the DHI is evidence about a smaller
    success case than the one being risked, and the update is invalid as posed rather than merely
    weak.
    """
    depths = np.asarray(depths_m, dtype=float)
    areas = np.asarray(areas_km2, dtype=float)
    min_area = float(np.interp(apex_m + min_column_m, depths, areas))
    if min_area <= dhi_area_km2 + 1e-9:
        return True, ""
    return False, (
        f"the minimum-case area is {min_area:.2f} km² but the anomaly covers only "
        f"{dhi_area_km2:.2f} km². The DHI is then evidence about a smaller accumulation than the "
        f"one being risked, so the update does not apply to this success case — restate the "
        f"assessment minimum, or risk the DHI-sized case instead."
    )


# --------------------------------------------------------------------------- DHI strength
# Adapted from E-POS's `logic/dfi_custom.py` and `logic/dfi_simm.py`. Copied rather than imported,
# for the same reason the palette is: E-POS is a separate deployable app, not a library.

#: 2 x Phi^-1(0.99). A P1-to-P99 span is this many standard deviations.
_P1_P99_Z = 2.0 * 2.3263478740408408

#: Outer guard from E-POS on the **combined** ratio, so a degenerate ratio cannot blow up the
#: update. It is deliberately loose: Kjonsberg et al. (2010) measured a combined R of 29 on a
#: prospect that was subsequently drilled and found gas, so a combination in the tens is earned
#: rather than absurd, and clipping there would clip real evidence.
R_FLOOR, R_CAP = 1.0 / 50.0, 50.0

#: The calibrated ceiling on the contact weight: Hood's (2019) high-confidence case and Monigle
#: et al.'s (2025) empirical rule, from the same company's drilled DHI prospects, both stop here.
CONTACT_WEIGHT_CEILING = 0.95


def contact_weight_from_score(score: float) -> float:
    """Monigle et al.'s (2025) column-height weighting practice, from a DHI score in their sense.

    ``w = min(2 x score, 0.95)``: "high DHI scores (>0.50 rating) weight the HCWC at the rated
    DHI elevation to 95 % of the total trials; lower DHI scores weight the HCWC at the DHI
    elevation relative to the rating outcome (double the DHI score for weighting value)". An
    empirical relationship reported for their drilled-prospect database, on their five-attribute
    score and in a scenario (substitution) construction; it is not a calibration of ``c`` on
    this tool's evidence index or graded attributes, and its use as the mixture weight of the
    likelihood is this tool's mapping. Shown on tab 5.1.3 as a comparison beside the c in use;
    it is not a selectable source of ``c`` (comparison-only by decision, 22 Sep 2026).
    """
    return float(min(2.0 * float(np.clip(score, 0.0, 1.0)), CONTACT_WEIGHT_CEILING))

#: The most a **single channel** may claim, either way.
#:
#: A different job from :data:`R_CAP`, and it used to be done by the same number. Simm (Simm &
#: Bacon 2014, ch. 11; Simm 2020) is explicit that for one line of fluid-indicator evidence an
#: honest R rarely exceeds about 3, and that |R| above 10 should send you back to the inputs; :func:`strength_bands` has said so in
#: words since the strength model was written, while the arithmetic allowed 50. The gap was not
#: academic. On the shipped prospect the strength slider alone moved the prospect chance from
#: 1.4 % to 97.2 % -- a 96-point swing from one elicited number on an axis with no external
#: referent, which is more than every other input on the tab put together.
#:
#: Kjonsberg's 29 is not a counter-example: their number carries the amplitude *and* the geometry
#: through a full prestack inversion, so it is a combined ratio and belongs against ``R_CAP``.
#: This bound is on each channel going in.
R_SINGLE_CHANNEL = 10.0

#: E-POS's `DEFAULT_SLIDER`.
DEFAULT_STRENGTH = 7.0


@dataclass(frozen=True)
class StrengthCase:
    """One Gaussian over the DHI-strength axis, given by its 1st and 99th percentiles."""
    p1: float
    p99: float

    @property
    def mean(self) -> float:
        return (self.p1 + self.p99) / 2.0

    @property
    def sd(self) -> float:
        return max(abs(self.p99 - self.p1) / _P1_P99_Z, 1e-9)

    def pdf(self, x: float | np.ndarray) -> np.ndarray:
        return norm.pdf(np.asarray(x, dtype=float), self.mean, self.sd)


@dataclass(frozen=True)
class StrengthModel:
    """DHI strength to a likelihood ratio, by the two-curve construction E-POS uses.

    The user draws how a hydrocarbon-bearing prospect tends to look on the DHI and how a
    non-hydrocarbon one does, on a common arbitrary strength axis, then reads off where this
    prospect sits. ``R = pdf_HC(s) / pdf_NoHC(s)``.

    R is scale-invariant in the strength axis, so the −100…100 units carry no meaning of their own
    — only the relative heights of the two curves at the reading matter. E-POS's defaults are kept.
    """
    hc: StrengthCase = StrengthCase(*defaults.EVIDENCE_INDEX_HC_P1_P99)
    no_hc: StrengthCase = StrengthCase(*defaults.EVIDENCE_INDEX_NOHC_P1_P99)

    def r_at(self, strength: float) -> float:
        num = float(self.hc.pdf(strength))
        den = float(self.no_hc.pdf(strength))
        if den <= 0.0:
            return R_SINGLE_CHANNEL if num > 0.0 else 1.0
        return float(min(max(num / den, 1.0 / R_SINGLE_CHANNEL), R_SINGLE_CHANNEL))

    def strength_at(self, r: float) -> float:
        """The reading that produces likelihood ratio ``r``, or ``nan`` if the curves never do.

        The inverse of :meth:`r_at`, and it exists so the **slider can stop where the evidence
        stops** rather than run on into a range the cap has flattened. A dead half-slider is worse
        than a narrow live one: it invites a reading the arithmetic then quietly refuses.

        Analytic where the two cases share a standard deviation, which is the E-POS default and
        makes ``log R`` linear in the reading.

        Otherwise ``log R`` is a quadratic and reaches any target **twice**. The far root is where
        the narrower curve has collapsed to nothing: arithmetically the ratio is right, but it lies
        on the opposite side of the crossing from the population it is meant to favour, so using it
        as a slider bound would put the supportive end of the axis at a reading that argues
        against. The first crossing outward from neutral is the one wanted.
        """
        if r <= 0.0:
            return float("nan")
        m1, s1 = self.hc.mean, self.hc.sd
        m2, s2 = self.no_hc.mean, self.no_hc.sd
        target = np.log(r)
        if abs(s1 - s2) < 1e-9:
            slope = (m1 - m2) / (s1 * s1)
            if abs(slope) < 1e-12:
                return float("nan")
            return float((target + np.log(s2 / s1)
                          + (m1 * m1 - m2 * m2) / (2.0 * s1 * s1)) / slope)
        span = 20.0 * max(s1, s2) + max(abs(m1), abs(m2))
        grid = np.linspace(-span, span, 20_001)
        with np.errstate(divide="ignore", invalid="ignore"):
            curve = np.log(self.hc.pdf(grid)) - np.log(self.no_hc.pdf(grid))
        ok = np.isfinite(curve)
        if not ok.any():
            return float("nan")
        grid, curve = grid[ok], curve[ok]
        neutral = grid[int(np.argmin(np.abs(curve)))]
        side = grid >= neutral if target > 0.0 else grid <= neutral
        if not side.any():
            return float("nan")
        g, c = grid[side], curve[side]
        if target < 0.0:
            g, c = g[::-1], c[::-1]
        reached = np.flatnonzero(np.abs(c) >= abs(target))
        return float(g[reached[0]] if reached.size else g[-1])


def simm_update(prior: float, r: float) -> float:
    """Two-state Bayesian update: ``posterior = R·prior / (R·prior + (1 − prior))``."""
    if not 0.0 <= prior <= 1.0:
        raise ValueError(f"the prior must be a probability, got {prior}")
    if r <= 0:
        return 0.0
    return float(r * prior / (r * prior + (1.0 - prior)))


def volume_weight(r: float) -> float:
    """``R / (R + 1)`` — E-POS's ``dhi_score_from_r``.

    The probability form of the likelihood ratio, usually called the *DHI volume weight*. It is not
    a POS: it is the weight the evidence alone would carry against an even prior.
    """
    return 0.0 if r <= 0 else float(r / (r + 1.0))


def strength_bands(r: float) -> tuple[str, str]:
    """Simm's verbal reading of R (Simm & Bacon 2014; Simm 2020), so the number is not quoted bare.

    His caution matters and is repeated here: for a *single* DFI line of evidence an honest R rarely
    exceeds about 3 either way, and |R| above 10 should send you back to the inputs.
    """
    if r >= 10.0:
        return "Decisive ↑", "Very rarely justified for one DHI — re-check the curves."
    if r >= 3.0:
        return "Strong ↑", "About the practical ceiling Simm suggests for a single DHI."
    if r >= 1.5:
        return "Moderate ↑", "Credible supportive DHI evidence."
    if r > 1.0 / 1.5:
        return "Negligible", "R ≈ 1 — the DHI barely shifts the prior."
    if r > 1.0 / 3.0:
        return "Moderate ↓", "Credible evidence the DHI is anomalous against hydrocarbons."
    if r > 1.0 / 10.0:
        return "Strong ↓", "About the practical floor Simm suggests for a single DHI."
    return "Decisive ↓", "Very rarely justified for one DHI — re-check the curves."
