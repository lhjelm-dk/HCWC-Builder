"""How much should you trust this run?

Every check here already existed somewhere — a realisation count, a controlling share, a Higham
projection, an effective sample size. What did not exist was anything that **gathered them and said
so without being asked**. A tool that reports P0.5 to the metre and never mentions that the number
rests on five draws is not wrong, it is quiet in the wrong place.

So this module runs the checks that would embarrass the run if a reviewer found them first, and
returns them as data — one level, one number, one sentence about what to do. The UI renders it and
the one-page report prints it, from the same list, so the panel on screen and the panel in the
proposal can never disagree.

**Three levels, and they mean different things.**

``ok``
    Nothing to say. Shown anyway, because a checklist where the passes are hidden teaches the reader
    that anything visible is a problem, and then they stop reading the ones that are.

``watch``
    The number is usable but needs a sentence next to it. A prospect controlled 80 % by seal capacity
    is not broken — it is a seal prospect — but a reader who is not told will read the spread as
    though four mechanisms produced it.

``stop``
    The number should not leave the building as it stands. Not "the model is wrong": *this
    particular figure is not supported by what was run*, and the fix is usually more realisations or
    one more sentence of provenance.

**What this deliberately does not do.** It does not score the geology. Nothing here knows whether
120 m is a sensible minimum or whether the seal argument is any good. Every check is about whether
the arithmetic supports the number being quoted, which is the only thing a run can audit about
itself. The geological sanity check lives on tab 6.0, against the empirical record, and says so.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hcwc.core import correlate, engine
from hcwc.core.engine import EngineResult

#: Worst-first, so ``max(levels, key=ORDER.index)`` gives the headline.
ORDER = ("ok", "watch", "stop")

#: One glyph per level, shared by the panel and the report so they cannot label the same check
#: differently.
ICONS = {"ok": "✓", "watch": "⚠", "stop": "✕"}

#: How many realisations must sit beyond a percentile before it is worth quoting. Below 200 the
#: tenth percentile of a Monte Carlo moves by more than a metre between seeds on a typical column;
#: below 50 it moves by tens.
P10_SUPPORT_WATCH = 200
P10_SUPPORT_STOP = 50

#: Share of successful realisations one limit may control before the distribution is really that
#: limit's distribution wearing the others as decoration.
CONCENTRATION_WATCH = 0.75
CONCENTRATION_STOP = 0.95

#: How far the Higham projection may move an elicited correlation before the assessor should be told
#: the matrix they described is not the matrix that was sampled.
PROJECTION_WATCH = 0.05
PROJECTION_STOP = 0.15

#: Effective sample size, as a share of realisations, below which the DHI posterior is being carried
#: by a small number of heavily weighted draws.
ESS_WATCH = 0.30
ESS_STOP = 0.10

#: How far a reported percentile may move between two seeds, as a share of the column, before the
#: run is reporting Monte Carlo noise as a geological statement.
REPEAT_WATCH = 0.02
REPEAT_STOP = 0.05


@dataclass(frozen=True)
class Check:
    """One audit line: what was checked, how it went, and what to do about it."""

    name: str
    level: str
    finding: str
    meaning: str

    @property
    def icon(self) -> str:
        return ICONS[self.level]


def _level(value: float, watch: float, stop: float, *, higher_is_worse: bool = True) -> str:
    if higher_is_worse:
        return "stop" if value >= stop else "watch" if value >= watch else "ok"
    return "stop" if value <= stop else "watch" if value <= watch else "ok"


def _readable(value: float) -> str:
    """A likelihood ratio at a width a reader can take in.

    ``R`` is unbounded here — a sharply picked flat spot against a broad prior can produce six
    figures — and ``{:,.2f}`` on that prints ``3,887,068.71``, which reads as a data error rather
    than as very strong evidence. Two significant figures past a thousand says the same thing and
    is honest about the precision, which is none.
    """
    if not np.isfinite(value):
        return "undefined"
    if value >= 1_000:
        return f"{value:,.3g}"
    return f"{value:.2f}"


def tail_support(result: EngineResult) -> Check:
    """Does the deep tail rest on enough realisations to quote?

    The percentiles are taken over **successes only**, so a low chance of success thins the tail
    twice over: 10 000 trials at 40 % leaves 4 000, and P10 of that is 400 draws. The count that
    matters is not ``n_trials`` on the sidebar, which is what everyone looks at.
    """
    successes = int(result.above_minimum.sum())
    behind_p10 = int(round(successes * 0.10))
    behind_p1 = int(round(successes * 0.01))
    level = _level(behind_p10, P10_SUPPORT_WATCH, P10_SUPPORT_STOP, higher_is_worse=False)
    return Check(
        name="Support in the deep tail",
        level=level,
        finding=(f"{successes:,} of {result.n:,} realisations clear the assessment minimum. "
                 f"P10 rests on {behind_p10:,} of them, P1 on {behind_p1:,}."),
        meaning=("Enough to quote P10 to the metre." if level == "ok" else
                 "P10 needs a higher trial count before it is quoted. The percentiles are taken "
                 "over successes only, so a low chance of success thins the tail twice over."),
    )


def concentration(result: EngineResult) -> Check:
    """Is one limit doing all the work?

    Read on **successes only**, because the question is *what controls this contact given the
    prospect is worth drilling* — the number a reader of the exceedance curve is implicitly asking.
    """
    shares = result.controlling_shares(successes_only=True)
    if not shares:
        return Check("Spread of control", "ok", "No limits to report.", "")
    top, share = max(shares.items(), key=lambda kv: kv[1])
    idle = [name for name, s in shares.items() if s == 0.0]
    level = _level(share, CONCENTRATION_WATCH, CONCENTRATION_STOP)
    tail = (f" {len(idle)} limit{'s' if len(idle) != 1 else ''} never set the contact"
            f" ({', '.join(idle)})." if idle else "")
    return Check(
        name="Spread of control",
        level=level,
        finding=f"{top} sets the contact in {share:.0%} of successful realisations.{tail}",
        meaning=("Several mechanisms contribute, so the spread is a competition."
                 if level == "ok" else
                 f"This is close to {top}'s distribution alone. That may be right, since a seal "
                 f"prospect is a seal prospect, but it needs stating beside the curve; a reader "
                 f"will otherwise credit the spread to mechanisms that are not in it."),
    )


def assessment_minimum(result: EngineResult) -> Check:
    """Is the risk criterion actually engaged?

    The risk criterion in this tool is hard-linked to the assessment minimum: the column term is
    the chance of a column **at least this tall**. At a minimum of zero that term is 1.0 by
    construction, the depth-risk curves are decorative, and no DHI evidence can move a certainty.
    It is the single most common way to get a confidently wrong answer out of the tool, and it is
    invisible.

    Every probability quoted here is ``P(column >= h | G)`` — **conditional on the elements having
    worked**, because that is all the engine knows. It is said in full each time rather than
    shortened to "POS", which is a different number by a factor of ``1 / P(G)``.
    """
    minimum = float(result.limit_set.min_column_m)
    pos = result.pos
    if minimum <= 0:
        return Check(
            name="The assessment minimum",
            level="stop",
            finding="The assessment minimum is 0 m, so every realisation with any column "
                    "counts as a success and `P(column ≥ h | G)` is 100 % by construction; the "
                    "prospect chance collapses to the element product alone.",
            meaning="The minimum needs to be the smallest column worth drilling. The column term "
                    "means at least this tall; with no minimum it means nothing, and no DHI "
                    "evidence can move a certainty.",
        )
    if pos <= 0.02 or pos >= 0.98:
        return Check(
            name="The assessment minimum",
            level="watch",
            finding=f"A minimum of {minimum:,.0f} m gives `P(column ≥ h | G)` = {pos:.1%}, which "
                    f"is almost decided either way.",
            meaning="The minimum should be the volume that justifies the well. A term this close "
                    "to an endpoint usually means the minimum is far off the distribution rather "
                    "than that the prospect is settled.",
        )
    return Check(
        name="The assessment minimum",
        level="ok",
        finding=f"A minimum of {minimum:,.0f} m gives `P(column ≥ h | G)` = {pos:.1%}, the "
                f"conditional column term, multiplied by the element product for the prospect "
                f"chance.",
        meaning="The criterion sits inside the distribution, where a risk statement has to sit "
                "to mean anything.",
    )


def correlation_projection(result: EngineResult) -> Check:
    """Was the elicited correlation matrix the one that got sampled?

    An inconsistent set of pairwise correlations is not rejected — it is projected to the nearest
    consistent one, which is the right thing to do and the wrong thing to do silently. A 0.9
    quietly reduced to 0.6 because of what was said about a third limit is a change to the model
    that nobody asked for.
    """
    # The apex leads the correlated set, and a pair may name it -- the Apex|spill coupling is
    # the one the tab recommends. Built from the limit names alone this raised KeyError the
    # moment that pair was declared, which the audit of 14 Sep 2026 reproduced.
    names = result.limit_set.correlated_names
    declared = result.limit_set.correlations
    pairs = (correlate.describe(names, correlate.build_matrix(names, declared))
             if declared else [])
    if not pairs:
        return Check(
            name="Correlations as sampled",
            level="ok",
            finding="No correlations were elicited, so every limit is drawn independently.",
            meaning="Independence is a modelling choice too. Two limits that share a cause, the "
                    "same seal or the same fault, belong correlated on tab 3.0 rather than left "
                    "at zero.",
        )
    worst = max(pairs, key=lambda row: abs(row[2] - row[3]))
    moved = abs(worst[2] - worst[3])
    level = _level(moved, PROJECTION_WATCH, PROJECTION_STOP)
    return Check(
        name="Correlations as sampled",
        level=level,
        finding=(f"{len(pairs)} pair{'s' if len(pairs) != 1 else ''} elicited. Largest move under "
                 f"the projection: {worst[0]} ↔ {worst[1]}, asked for {worst[2]:+.2f}, "
                 f"sampled at {worst[3]:+.2f}."),
        meaning=("The matrix was already consistent, so what was asked for is what was sampled."
                 if level == "ok" else
                 "The elicited matrix was not internally consistent and was projected. The "
                 "correlation in the model is not the one stated for that pair on tab 3.0, and "
                 "the difference came from what was stated about a third limit."),
    )


def repeatability(result: EngineResult, other: EngineResult | None = None) -> Check:
    """Does the answer move if you press go again?

    The most honest single number about a Monte Carlo, and the one nobody computes: rerun at the
    next seed and report how far P10 shifted. Everything else here is a proxy for this.

    ``other`` is that second run. It defaults to computing one, so this stays a self-contained core
    function and every test of it reads as it did; the UI passes a cached one, because otherwise the
    whole Monte Carlo ran again on every interaction to answer a question whose answer had not
    changed.
    """
    if other is None:
        other = engine.run(result.limit_set, n=result.n, seed=result.seed + 1)
    mine = result.percentiles(np.array([90.0, 50.0, 10.0]))
    theirs = other.percentiles(np.array([90.0, 50.0, 10.0]))
    if not np.all(np.isfinite(mine)) or not np.all(np.isfinite(theirs)):
        return Check("Repeatability across seeds", "watch",
                     "Too few successes to compare two seeds.",
                     "Raise the trial count.")
    p50 = float(abs(mine[1]))
    shift = float(np.max(np.abs(mine - theirs)))
    relative = shift / p50 if p50 else float("inf")
    level = _level(relative, REPEAT_WATCH, REPEAT_STOP)
    return Check(
        name="Repeatability across seeds",
        level=level,
        finding=f"Rerun at seed {other.seed}, the P90/P50/P10 contacts move by at most "
                f"{shift:,.1f} m ({relative:.1%} of P50).",
        meaning=("Smaller than any depth that can be picked off a seismic section, so the digits "
                 "quoted are the model's and not the sampler's." if level == "ok" else
                 "Fewer digits, or more trials. A number that moves this much between two seeds "
                 "reports the random number generator, and will be read as geology."),
    )


def dhi_evidence(posterior, current: EngineResult | None = None) -> Check:
    """Is the DHI posterior carried by enough of the sample, and is it the *current* sample?

    Importance weighting does not add realisations; it re-reads the ones already drawn. Strong
    evidence concentrates the weight on a few draws, and past a point the posterior percentiles are
    a handful of realisations wearing a smooth curve.

    ``current`` is the run the rest of the panel is describing. The posterior reaches tab 4.0 through
    session state written by tab 5.0, which renders *after* it, so on the run where the trial count or
    seed changes the two are one interaction apart. Everywhere else in the app that lag is invisible;
    on a panel whose whole job is catching mismatched denominators, printing "6,920 of 10,000"
    beside "8,349 of 12,000" without a word would be the panel committing the error it exists to
    find. So it is checked and said.
    """
    # `effective_sample_size` and `r_dhi` are **properties** on `dhi.DhiPosterior`, not methods.
    # Read with `()` they raise `'float' object is not callable`, which is what tab 4.0 did the first
    # time a real posterior reached it — the test's stub had made them methods, so the test agreed
    # with the bug rather than catching it.
    ess = float(posterior.effective_sample_size)
    n = int(posterior.result.n)
    share = ess / n if n else 0.0

    stale = current is not None and (posterior.result.n != current.n
                                     or posterior.result.seed != current.seed)
    if stale:
        return Check(
            name="Weight behind the DHI update",
            level="watch",
            finding=f"The DHI update on hand was built on {n:,} realisations at seed "
                    f"{posterior.result.seed}, and this run is {current.n:,} at seed "
                    f"{current.seed}. It is one interaction behind.",
            meaning="Not an error, and not yet a number to quote: tab 5.0 rebuilds after this "
                    "panel renders, so the run that changed the trial count or seed sees the "
                    "previous posterior. It catches up on the next interaction.",
        )

    level = _level(share, ESS_WATCH, ESS_STOP, higher_is_worse=False)
    return Check(
        name="Weight behind the DHI update",
        level=level,
        finding=f"Effective sample size {ess:,.0f} of {n:,} realisations ({share:.0%}); the "
                f"evidence is worth R = {_readable(posterior.r_dhi)}.",
        meaning=("Enough of the sample survives the reweighting to read the posterior percentiles."
                 if level == "ok" else
                 "The posterior is carried by a small, heavily weighted part of the sample. It "
                 "needs a higher trial count or a softer detection function; a likelihood this "
                 "sharp claims that the amplitude alone nearly settles the column height."),
    )


def review(result: EngineResult, *, posterior=None, other: EngineResult | None = None) -> list[Check]:
    """Every check, in the order they should be read.

    ``posterior`` is optional because the DHI tabs are optional; when it is absent the DHI check is
    simply not run rather than reported as passing, which would be a lie about work not done.

    ``other`` is the next-seed run :func:`repeatability` compares against, passed in so the caller
    can cache it.
    """
    checks = [
        assessment_minimum(result),
        tail_support(result),
        repeatability(result, other),
        concentration(result),
        correlation_projection(result),
    ]
    if posterior is not None:
        checks.append(dhi_evidence(posterior, result))
    return checks


def headline(checks: list[Check]) -> tuple[str, str]:
    """The worst level present, and a sentence for it."""
    if not checks:
        return "ok", "Nothing to check."
    level = max((c.level for c in checks), key=ORDER.index)
    stops = sum(1 for c in checks if c.level == "stop")
    watches = sum(1 for c in checks if c.level == "watch")
    if level == "stop":
        return level, (f"{stops} check{'s' if stops != 1 else ''} "
                       f"{'do' if stops != 1 else 'does'} not support the numbers as they stand. "
                       f"{'They need' if stops != 1 else 'It needs'} resolving before the "
                       f"numbers are quoted.")
    if level == "watch":
        return level, (f"{watches} check{'s' if watches != 1 else ''} "
                       f"{'need' if watches != 1 else 'needs'} a sentence beside the number, not a "
                       f"change to the model.")
    return level, "Every check passes. The arithmetic supports the numbers being quoted."
