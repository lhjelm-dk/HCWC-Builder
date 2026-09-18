"""The DHI branch: what a seismic amplitude does to the contact distribution, and to POS.

Worked out in ``archive/development_notes/DHI_alignment.md``. The short of it, because it decides the shape of this
module:

**POS is not a number, it is a reading.** Everything is one function, ``F(h) = P(column >= h)``. The
geological POS is ``F(h_min)``; the DHI-case probability is ``F(h_DHI)``; the well POS is
``F(z_entry - apex)``. ``F`` is monotone, so ``F(h_min) >= F(h_DHI)`` always and there is nothing to
reconcile — the two numbers were never competing. The error the tool exists to prevent is quoting a
POS read at one threshold beside a volume read at another.

**The DHI enters as a likelihood over column height**, because the seismic response depends on *how
much* hydrocarbon is there, not merely whether any is::

    posterior(h) ∝ prior(h) × L(seismic | h)

so the updated POS and the updated contact distribution are **the same object**, read at different
thresholds. That is the answer to the question the note was written for.

**The chain, and what is conditional on what.** Settled 14 Sep 2026 after an audit found the
strength evidence counted twice. The engine's realisations are draws from ``p(h | G)`` -- every one
of them already assumes the four elements worked -- so anything applied to them must be conditional
on ``G`` too. The chain is::

    A.  P(G | strength)          = simm_update(P(G), R_strength)          the character channel
    B.  p(h | G, geometry)       ∝ p(h | G) · L(geometry | h, G)          the pick, within G
        L(geometry | h, G)       = c · D(h) · Pick(z | apex + h) + (1 − c) · s
        c                        = P(the picked event is the contact | G, contact attributes)
    C.  POS(h_min)               = P(G | strength) · P(h ≥ h_min | G, geometry)

One posterior over ``h`` -- the weights from B -- supplies the histogram, the percentiles, ``F(h)``
and the conditional term in C. The curve ``P(G | strength) · F_post(h)`` passes through the
headline at ``h_min`` by construction rather than by rescaling.

What was wrong before: ``p_valid`` was built as ``P(G | strength) · c``. A term conditional on
``G`` had ``P(G)`` inside it, so the strength reached the geometry posterior through the mixture
weight *and* again through a separate likelihood ratio blended with ``r_dhi``. Holding ``c`` at 0.70
and moving the strength alone moved the posterior P50 by 17 m and the conditional term by six
points -- evidence about *whether there is hydrocarbon* reshaping *where the contact is, given there
is*. :func:`prospect_pos` is the corrected C; :class:`CombinedUpdate` is retained only for the
teaching comparison and must not supply a headline.

**There is one model, and two things it is worth being compared against.** The note offered the
scenario switch and the likelihood as rival formulations, and that framing survived longer than it
should have. What settled it was moving ``p_valid`` — the chance the picked event really is the
contact — *inside* the likelihood, where it makes the update robust rather than dogmatic. The
scenario switch's one genuine contribution was that parameter; with it accounted for, the other two
formulations are not alternative models but arithmetic with a term left out:

* **scenario switch** — ``IF(DHI valid, DHI contact, geological contact)``. A mixture, so it can
  move the contact and *widen* the answer but can never sharpen it, and cannot move POS at all.
  Hood's rule, and honest as far as it goes.
* **pooled** — the prior times the pick likelihood alone. Literally the Bayesian update with the
  detection function omitted, so it conditions on having seen an anomaly without accounting for the
  fact that seeing one was more likely when the column is tall.
* **Bayes** — ``prior x D(h) x pick``, mixed against a flat branch by ``p_valid``. The model.

The first two stay in the code and on the tab as a **teaching comparison**, never as a choice of
model, because seeing what a dropped term costs is the only way to make the argument concrete.

**What the DHI may not do.** E-POS's ``logic/dfi_pillar_update.py`` sets the ceiling: a fluid
indicator can sense whether a reservoir exists and -- more weakly, see the Kjonsberg note on the
strength section -- what fluid fills it, but *not which of charge,
closure or retention failed*. So a DHI may move POS and may assert a contact depth. It may **not**
tell you which element failed.

It *may* tell you which limit set the contact, because knowing roughly where the contact sits is
evidence about which mechanism put it there. Those are two different claims and the older wording
here forbade both: the controlling-limit diagnostic therefore has a geological reading and a
DHI-updated one, and they are two figures rather than one figure with two meanings.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from hcwc.core import dists, engine
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
    h50_m: float = 25.0
    steepness_m: float = 8.0
    ceiling: float = 0.9
    false_positive: float = 0.5

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
        return self.ceiling / (1.0 + np.exp(-(h - self.h50_m) / self.steepness_m))


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
    nothing else. It must not carry ``P(G)`` or any function of the amplitude strength: the
    engine's sample is ``p(h | G)``, so a mixture weight with ``P(G)`` inside it counts the
    chance of hydrocarbons once here and again wherever the strength channel is applied. Until
    14 Sep 2026 the app passed ``P(G | strength) · c`` and the strength reached the geometry
    posterior through this field.

    **``p_valid`` is taken independent of ``h``** (audit, 16 Sep 2026). One number weights the
    mixture for every realisation: the chance that the picked event is the contact is not made
    to depend on how tall the column is. A taller column could make a conformable event more
    likely to be its base; that dependence is not modelled, and ``D(h)`` is where the column
    height enters the valid branch instead. Stated in 8.1.5 and pinned by
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
    untouched. That is what gives the whole update its floor: since ``Pick(·) >= 0``,

        L / s  >=  1 - p_valid

    so the depth channel can never say more than ``p_valid / (1 - p_valid)`` against any hypothesis,
    whatever shape the pick has. Nothing is ever ruled out by one seismic interpretation — which is
    Cromwell's rule, and the reason a bounded pick shape is safe to offer at all.

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
        """Diagnostic ratio: how much the geometry likelihood favours tall columns over short ones.

        **Not part of the chance, since 14 Sep 2026.** Both sets it compares are inside ``G`` --
        realisations that clear the assessment minimum against those that fall short -- so it is
        a ratio between two column-height hypotheses, not between success and failure of the
        prospect. Applying it as a likelihood ratio on the prospect chance, as
        :class:`CombinedUpdate` did, treated ``P(h < h_min | G)`` as if it were ``P(not G)``. The
        geometry's effect on the chance is now read directly: ``P(h ≥ h_min | G, geometry)`` is
        :meth:`pos`, and :func:`prospect_pos` multiplies it by ``P(G | strength)``. This property
        stays as a readout of how much the pick discriminates, and for the trust panel.

        For a **seen** anomaly this is E-POS's ``r_dfi`` construction — ``L`` averaged over the
        success cases divided by ``L`` averaged over the failures — so the two tools report a
        comparable number. The comparison there is between one column height and another, which is
        the right question when the evidence is *where* an anomaly terminates.

        For an **absent** anomaly it is not. Absence is evidence against the accumulation existing
        at all, and comparing tall columns against short ones misses that entirely: it returns
        ``nan`` whenever the assessment minimum is low enough that every realisation clears it,
        which is exactly when the finding matters most. So the comparison is made against the
        barren world instead::

            R = E[1 - D(h) | success] / P(no anomaly | no accumulation)

        with the denominator taken as **1**: a trap with no hydrocarbon in it has nothing to show.
        That is an assumption and a slightly generous one — a barren trap can still throw a
        spurious bright event — but erring that way makes absence weaker evidence, not stronger,
        which is the safe direction for a number this consequential.

        **The denominator has to be a real sample.** The guard below used to catch only the case
        where *every* realisation clears the minimum. Seven out of ten thousand slipped through it,
        and seven is not a sample: on the shipped prospect at a 5 m minimum the ratio came out at
        1.66 from those seven, which lifted a **neutral** amplitude -- strength 0, ``r_strength``
        exactly 1 -- from 40.8 % to 53.3 %. An observation that says nothing must do nothing, and
        E-POS agrees. Below :func:`min_failures_for_r` the ratio is undefined rather than noisy,
        and :class:`CombinedUpdate` then falls back to the strength channel alone.

        There is a deeper reason to be strict here. These "failures" are not failed *prospects* --
        every realisation the engine draws is already conditional on the four elements working, and
        that chance lives in ``P(G)`` on tab 2.0. They are short columns. Comparing tall columns with
        short ones is the right question when the minimum is a real commercial threshold and a
        useful share of realisations miss it; it is meaningless when the minimum is a 5 m physical
        floor that only a rounding error fails to clear.
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
    """Monigle et al.'s (2025) rule for the contact weight from a DHI score in their sense.

    ``w = min(2 x score, 0.95)``: "high DHI scores (>0.50 rating) weight the HCWC at the rated
    DHI elevation to 95 % of the total trials; lower DHI scores weight the HCWC at the DHI
    elevation relative to the rating outcome (double the DHI score for weighting value)".
    Calibrated on 400+ drilled DHI prospects in their database, not on any one basin, and on
    their five-attribute machine-learning score rather than on this tool's strength reading.
    Offered on tab 5.1.3 as a third source of ``c`` beside the slider and the graded attributes
    (Lars, 17 Sep 2026; open question 3 of 15 Sep).
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
    hc: StrengthCase = StrengthCase(-50.0, 100.0)
    no_hc: StrengthCase = StrengthCase(-100.0, 50.0)

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
