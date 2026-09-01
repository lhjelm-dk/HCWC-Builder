"""The DHI branch: what a seismic amplitude does to the contact distribution, and to POS.

Worked out in ``docs/DHI_alignment.md``. The short of it, because it decides the shape of this
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
indicator can sense whether a reservoir exists and what fluid fills it, but *not which of charge,
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
    ``docs/DHI_alignment.md`` §9 flags it as worth a geophysicist's opinion.
    """
    h50_m: float = 25.0
    steepness_m: float = 8.0
    ceiling: float = 0.9

    def __post_init__(self) -> None:
        if self.h50_m <= 0:
            raise ValueError("the 50% detection column must be positive")
        if self.steepness_m <= 0:
            raise ValueError("steepness must be positive; it is the width of the transition")
        if not 0.0 < self.ceiling <= 1.0:
            raise ValueError("the detection ceiling must be in (0, 1]")

    def at(self, column_m: np.ndarray) -> np.ndarray:
        h = np.asarray(column_m, dtype=float)
        return self.ceiling / (1.0 + np.exp(-(h - self.h50_m) / self.steepness_m))


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

    ``p_valid`` defaults to 1.0 so that constructing an observation the old way reproduces the old
    numbers exactly. **The app never passes 1.0** — it derives the value from the DHI strength — and
    the reason is Cromwell's rule: at ``p_valid = 1`` a bounded pick shape assigns probability zero
    below its deepest bound, and no later evidence can ever revive a zero.
    """
    seen: bool
    contact_m: float | None = None
    pick_sigma_m: float = 15.0
    area_km2: float | None = None
    pick_shape: str = NORMAL
    shallowest_m: float | None = None
    deepest_m: float | None = None
    p_valid: float = 1.0

    def __post_init__(self) -> None:
        if self.seen and self.contact_m is None:
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
        if self.seen and self.pick_shape != NORMAL:
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


def spurious_density(contact_m: np.ndarray) -> float:
    """``c`` — the density of a flat event that is *not* the contact, at any one depth.

    Taken as uniform over the trap's own depth range: an event that has nothing to do with the
    hydrocarbon column is equally likely to turn up anywhere in the closure. It is the same value
    in the success and the failure world, and that equality is load-bearing — *is hydrocarbon
    present* is the strength channel's question and it answers it once. Letting ``c`` differ
    between the two worlds would answer it twice.

    Only the ratio to the pick density matters, so the overall rate of spurious events cancels and
    never has to be elicited.
    """
    z = np.asarray(contact_m, dtype=float)
    span = float(z.max() - z.min())
    return 1.0 / span if span > 0 else 1.0


def likelihood(result: EngineResult, detection: DetectionFunction,
               observation: DhiObservation) -> np.ndarray:
    """``L(seismic | h)`` for every realisation.

    **Not seen:** ``1 - D(h)``. Its own floor is already built in — ``DetectionFunction.ceiling``
    is below 1 on purpose, so an absent anomaly is never infinitely strong evidence either.

    **Seen**, with ``V`` for *the event I picked really is the hydrocarbon–water contact*::

        L = p_valid · D(h) · Pick(z_DHI | apex + h)   +   (1 - p_valid) · c

    The detection function gates **only** the first branch. "Would a column this tall have produced
    a visible anomaly" is a question that means something only when the anomaly is the column's; in
    the second branch, seeing the event had nothing to do with the column.

    In the second branch the likelihood is flat in ``h``, so the geological prior passes through
    untouched. That is what gives the whole update its floor: since ``Pick(·) >= 0``,

        L / c  >=  1 - p_valid

    so the depth channel can never say more than ``p_valid / (1 - p_valid)`` against any hypothesis,
    whatever shape the pick has. Nothing is ever ruled out by one seismic interpretation — which is
    Cromwell's rule, and the reason a bounded pick shape is safe to offer at all.

    There is no ``V`` branch in the failure world: with no accumulation there is no contact to
    indicate, so ``p_valid`` is properly ``P(V | G)`` and appears only here.
    """
    d = detection.at(result.column_m)
    if not observation.seen:
        return 1.0 - d
    valid = d * observation.pick_pdf(result.contact_m)
    if observation.p_valid >= 1.0:
        return valid
    return (observation.p_valid * valid
            + (1.0 - observation.p_valid) * spurious_density(result.contact_m))


@dataclass(frozen=True)
class DhiPosterior:
    """The prior and posterior as one object, because they are one object."""
    result: EngineResult
    weights: np.ndarray
    detection: DetectionFunction
    observation: DhiObservation

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
        """Contact depth at exceedance percentiles. P100 shallowest, P0 deepest."""
        p = np.atleast_1d(np.asarray(exceedance_pct, dtype=float))
        keep = self.result.above_minimum
        contacts = self.result.contact_m[keep]
        if contacts.size == 0:
            return np.full(p.shape, np.nan)
        w = self.weights[keep] if posterior else np.ones(contacts.size)
        if w.sum() <= 0:
            return np.full(p.shape, np.nan)
        order = np.argsort(contacts)
        c, w = contacts[order], w[order]
        cumulative = (np.cumsum(w) - 0.5 * w) / w.sum()
        return np.interp((100.0 - p) / 100.0, cumulative, c)

    @property
    def r_dhi(self) -> float:
        """Likelihood ratio: how much the observation favours success over failure.

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
        """
        success = self.result.above_minimum
        if not self.observation.seen:
            # Still undefined when nothing succeeds: with no success set there is no
            # `E[1 - D(h) | success]` to take, and averaging over the failures instead would be a
            # different quantity wearing the same name.
            return float(self.weights[success].mean()) if success.any() else float("nan")
        if not success.any() or success.all():
            return float("nan")
        return float(self.weights[success].mean() / self.weights[~success].mean())


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

#: Guards from E-POS, so a degenerate ratio cannot blow up the update.
R_FLOOR, R_CAP = 1.0 / 50.0, 50.0

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
            return R_CAP if num > 0.0 else 1.0
        return float(min(max(num / den, R_FLOOR), R_CAP))


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
    """Simm's (2016) verbal reading of R, so the number is not quoted bare.

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

    @property
    def r_combined(self) -> float:
        """Geometric interpolation between the product and the stronger single channel."""
        if not np.isfinite(self.r_geometry) or self.r_geometry <= 0:
            return self.r_strength
        log_product = np.log(self.r_geometry) + np.log(self.r_strength)
        log_stronger = max(abs(np.log(self.r_geometry)), abs(np.log(self.r_strength)))
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
    Bayesian update with the detection function left out**. That omission is the whole difference:
    it conditions on having seen an anomaly without accounting for the fact that seeing one was
    more likely when the column is tall, so it inherits a selection effect it cannot see.

    ``BAYES`` — prior x D(h) x pick likelihood. The detection function is what turns "I saw it"
    into evidence about the column rather than about your own attention, and it is what lets an
    *absent* anomaly be evidence at all.
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
