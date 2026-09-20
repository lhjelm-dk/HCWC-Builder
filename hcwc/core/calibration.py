"""Am I optimistic or pessimistic against the empirical record?

Lars, 27 Aug 2026: *"is there a good way to illustrate and quantify how the built HCWC varies from
the statistical data … I would like an idea of whether I am over- or underestimating."*

The comparison already existed as two curves on one axis and a reader judging the gap by eye. This
turns it into a number and a shape.

**The number.** Take your median column and ask what share of the benchmark's comparable closures
reach it. If your P50 is 250 m and only a quarter of theirs get that deep, then

    your P50 is their P25 — you are optimistic

and the direction never needs interpreting: **below 50 optimistic, above 50 conservative.** It is
the probability-integral transform of one quantile, which is the least elaborate honest way to place
one distribution inside another.

**The shape.** The number cannot say *where* the disagreement is, and that matters more than its
size. Uniform optimism is a bias you can correct. Optimism confined to the upside — agreeing at P50
and departing at P10 — is worse, because that is the tail the volume comes from and the tail that
justifies the well. A Q–Q plot separates the two at a glance.

**What this is not.** Every benchmark is conditioned on **discovery**. Your prospect is not a
discovery yet and every one of theirs is, so "optimistic against the NCS record" is partly a
statement about which wells got written down. It is a sanity check, not a score.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from hcwc.core import engine

#: How far from P50 a prospect must sit before the verdict stops saying "in line". Below this the
#: difference is inside what a few thousand Monte Carlo realisations can produce on their own.
NEUTRAL_BAND = 10.0


def exceedance_percentile(value: float, samples: np.ndarray) -> float:
    """Where ``value`` sits in ``samples``, in the **exceedance** convention.

    Returns the share of ``samples`` that reach or exceed ``value``, as a percentage — so a large
    value scores *low*, matching P90-is-the-shallow-end everywhere else in this tool. Getting this
    inverted would flip every verdict on the tab and raise nothing, so it is asserted in the tests.
    """
    drawn = np.asarray(samples, dtype=float)
    if drawn.size == 0:
        return float("nan")
    return float(np.mean(drawn >= value) * 100.0)


@dataclass(frozen=True)
class Comparison:
    """One benchmark, judged against the built distribution at the prospect's own relief."""

    name: str
    built_p90: float
    built_p50: float
    built_p10: float
    bench_p90: float
    bench_p50: float
    bench_p10: float
    #: The exceedance percentile of the built P50 within the benchmark. 50 is agreement.
    p50_lands_at: float

    @property
    def ratio(self) -> float:
        """Built P50 over benchmark P50. Above 1 is a taller predicted column."""
        return self.built_p50 / self.bench_p50 if self.bench_p50 else float("nan")

    @property
    def verdict(self) -> str:
        if not np.isfinite(self.p50_lands_at):
            return "no comparison"
        if self.p50_lands_at < 50.0 - NEUTRAL_BAND:
            return "optimistic"
        if self.p50_lands_at > 50.0 + NEUTRAL_BAND:
            return "conservative"
        return "in line"

    @property
    def sentence(self) -> str:
        """The finding in one line, which is the form it will actually be quoted in."""
        if not np.isfinite(self.p50_lands_at):
            return f"{self.name}: nothing to compare against."
        return (f"Your P50 of {self.built_p50:,.0f} m is the **P{self.p50_lands_at:.0f}** of "
                f"{self.name} — {self.verdict}.")


def compare(built: np.ndarray, benchmark: np.ndarray, name: str) -> Comparison:
    """Place the built column distribution inside one benchmark's."""
    built = np.asarray(built, dtype=float)
    benchmark = np.asarray(benchmark, dtype=float)
    if built.size == 0:
        # `np.percentile` of an empty array is an IndexError from deep inside numpy, which is what
        # a reader saw when the assessment minimum was set above any achievable column. That is a
        # legitimate question -- "is this prospect commercial at 350 m?" -- with a legitimate
        # answer, and the answer is not a traceback.
        raise ValueError(
            "there is nothing to compare: no realisation reached the assessment minimum, so the "
            "built column distribution is empty. Lower the minimum on tab 2.0 to see where this "
            "prospect does sit against the benchmarks."
        )
    if benchmark.size == 0:
        raise ValueError("the benchmark drew no samples at this relief.")
    b90, b50, b10 = (float(v) for v in engine.weighted_percentiles(built, None, [90.0, 50.0, 10.0]))
    k90, k50, k10 = (float(v) for v in engine.weighted_percentiles(benchmark, None, [90.0, 50.0, 10.0]))
    return Comparison(name=name, built_p90=b90, built_p50=b50, built_p10=b10,
                      bench_p90=k90, bench_p50=k50, bench_p10=k10,
                      p50_lands_at=exceedance_percentile(b50, benchmark))


def quantile_pairs(built: np.ndarray, benchmark: np.ndarray,
                   n: int = 99) -> tuple[np.ndarray, np.ndarray]:
    """Matched quantiles of the two distributions, for a Q–Q plot.

    Evenly spaced in probability rather than in value, so the middle of the plot carries the middle
    of both distributions. The extreme percentiles are trimmed: P0 and P100 of a Monte Carlo are its
    sample minimum and maximum, the two least stable statistics in the run, and a Q–Q plot that
    ended on them would swing on one realisation at each corner.

    **The returned arrays run shallow to deep**, i.e. from the smallest column to the largest. In
    this tool's exceedance convention that is **P99 first and P1 last**, which is the opposite of
    the ascending percentile the ``numpy`` call uses internally. Use :func:`exceedance_grid` to
    label them; getting it backwards puts "P1 shallow" on an axis where P1 is the deepest contact
    on every other figure in the app, which is how it read until Lars caught it on 27 Aug 2026.
    """
    probabilities = np.linspace(1.0, 99.0, n)
    return (engine.weighted_percentiles(np.asarray(built, dtype=float), None, 100.0 - probabilities),
            engine.weighted_percentiles(np.asarray(benchmark, dtype=float), None, 100.0 - probabilities))


def exceedance_grid(n: int = 99) -> np.ndarray:
    """The exceedance percentile of each element :func:`quantile_pairs` returns.

    P99 down to P1: the share of the distribution reaching at least that column. Deliberately a
    function beside the pairs rather than a constant somewhere, so the two cannot be changed
    independently — the whole bug was that the labelling and the ordering lived in different files.
    """
    return np.linspace(99.0, 1.0, n)


#: How far a quantile may sit from the benchmark before it stops counting as agreement. 15 % is
#: chosen because the four benchmarks disagree with *each other* by more than that at most reliefs
#: — a tighter corridor would report you as miscalibrated against a spread the literature does not
#: resolve.
CORRIDOR = 0.15


def corridor_share(built: np.ndarray, benchmark: np.ndarray,
                   tolerance: float = CORRIDOR) -> float:
    """The share of matched quantiles within ``tolerance`` of the benchmark, as a fraction.

    The number the single percentile cannot give: *how much* of the distribution agrees, rather
    than where its median lands. A prospect can sit at P50 on its median and still disagree
    everywhere else, and that shows up here and nowhere else on the tab.
    """
    mine, theirs = quantile_pairs(built, benchmark)
    safe = theirs != 0
    if not np.any(safe):
        return float("nan")
    return float(np.mean(np.abs(mine[safe] / theirs[safe] - 1.0) <= tolerance))


def quantile_ratios(built: np.ndarray, benchmark: np.ndarray) -> np.ndarray:
    """Built over benchmark at each matched quantile. Above 1 is a taller predicted column.

    Returned as a curve rather than a summary because *where* the ratio departs from 1 is the
    thing worth seeing: a flat 1.2 is a correctable bias, a ratio rising towards the upside is
    optimism concentrated in the tail the volume comes from.
    """
    mine, theirs = quantile_pairs(built, benchmark)
    return np.divide(mine, theirs, out=np.full_like(mine, np.nan), where=theirs != 0)
