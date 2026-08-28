"""Which elicited number actually moves the answer?

Tab ④ §3 ranks limits by how often they **control** the contact. That is a different question from
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
