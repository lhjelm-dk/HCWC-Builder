"""The trust checks have to fire on the cases they were written for, and stay quiet otherwise.

A checklist that never says anything is worse than no checklist: it certifies. So every check gets
a case that trips it and a case that does not, and the levels are asserted rather than the wording.
"""
from __future__ import annotations

import dataclasses

import pytest

from hcwc.core import engine, trust
from hcwc.core.limits import reference_prospect


@pytest.fixture(scope="module")
def zero_minimum():
    return engine.run(reference_prospect(), n=4_000, seed=20260825)


@pytest.fixture(scope="module")
def real_minimum():
    ls = dataclasses.replace(reference_prospect(), min_column_m=120.0)
    return engine.run(ls, n=4_000, seed=20260825)


def _named(checks, name):
    return next(c for c in checks if c.name == name)


def test_zero_minimum_is_a_stop(zero_minimum):
    """The single most common way to get a confidently wrong answer, and it is invisible."""
    check = trust.assessment_minimum(zero_minimum)
    assert check.level == "stop"
    assert "0 m" in check.finding


def test_a_real_minimum_passes(real_minimum):
    check = trust.assessment_minimum(real_minimum)
    assert check.level == "ok"
    assert 0.02 < real_minimum.pos < 0.98


def test_tail_support_falls_when_successes_do():
    """The count that matters is successes, not the trial count on the sidebar."""
    plenty = engine.run(reference_prospect(), n=10_000, seed=1)
    assert trust.tail_support(plenty).level == "ok"

    thin = engine.run(dataclasses.replace(reference_prospect(), min_column_m=120.0),
                      n=200, seed=1)
    assert trust.tail_support(thin).level in ("watch", "stop")


def test_repeatability_uses_a_different_seed(real_minimum):
    check = trust.repeatability(real_minimum)
    assert check.level in trust.ORDER
    assert str(real_minimum.seed + 1) in check.finding


def test_concentration_reads_successes_only(real_minimum):
    check = trust.concentration(real_minimum)
    shares = real_minimum.controlling_shares(successes_only=True)
    top = max(shares.values())
    assert f"{top:.0%}" in check.finding
    assert check.level == trust._level(top, trust.CONCENTRATION_WATCH, trust.CONCENTRATION_STOP)


def test_correlation_check_reports_the_projection():
    """An elicited matrix that is not positive semi-definite gets moved, and must say so."""
    ls = reference_prospect()
    a, b, c = ls.names[:3]
    inconsistent = dataclasses.replace(
        ls, min_column_m=120.0,
        correlations={f"{a}|{b}": 0.9, f"{b}|{c}": 0.9, f"{a}|{c}": -0.9})
    check = trust.correlation_projection(engine.run(inconsistent, n=2_000, seed=1))
    assert check.level in ("watch", "stop"), check.finding
    assert "asked for" in check.finding


def test_no_correlations_is_reported_as_a_choice(real_minimum):
    check = trust.correlation_projection(real_minimum)
    assert check.level == "ok"
    assert "independent" in check.finding


def test_headline_takes_the_worst_level(zero_minimum, real_minimum):
    assert trust.headline(trust.review(zero_minimum))[0] == "stop"
    level, sentence = trust.headline(trust.review(real_minimum))
    assert level in ("ok", "watch")
    assert sentence


def test_dhi_check_is_absent_rather_than_passing(real_minimum):
    """A check that did not run must not appear as one that passed."""
    names = [c.name for c in trust.review(real_minimum)]
    assert "Weight behind the DHI update" not in names


def test_dhi_check_fires_on_a_collapsed_sample(real_minimum):
    """The fake must match `dhi.Posterior`'s real interface, and here is why.

    Both of these are **properties**, and the first version of this fake made them methods. The
    test passed against a fake that could not exist, `trust.dhi_evidence` called them with `()`,
    and the tab crashed with `'float' object is not callable` the moment a real posterior arrived.
    `test_the_dhi_fake_matches_the_real_posterior` below is the guard: it asserts the shape rather
    than trusting the fake.
    """
    class _Posterior:
        result = real_minimum

        @property
        def effective_sample_size(self):
            return real_minimum.n * 0.05

        @property
        def r_dhi(self):
            return 3.0

    check = trust.dhi_evidence(_Posterior())
    assert check.level == "stop"
    assert "5%" in check.finding


def test_the_dhi_fake_matches_the_real_posterior():
    """A stub that does not match the thing it stands in for tests nothing.

    Asserted against the class rather than an instance, so it costs no Monte Carlo run and still
    fails the moment either attribute changes from a property to a method or back.
    """
    from hcwc.core import dhi

    for attribute in ("effective_sample_size", "r_dhi"):
        assert isinstance(getattr(dhi.DhiPosterior, attribute), property), (
            f"dhi.DhiPosterior.{attribute} is no longer a property — trust.dhi_evidence reads it "
            f"without parentheses, and the DHI trust check will break on tab 4.0"
        )


def test_every_check_carries_a_level_and_two_sentences(real_minimum):
    for check in trust.review(real_minimum):
        assert check.level in trust.ORDER
        assert check.finding.strip()
        assert check.meaning.strip()
        assert check.icon in trust.ICONS.values()


def test_exceedance_grid_matches_the_pair_ordering():
    """The label and the ordering used to live in different files, and disagreed.

    `quantile_pairs` returns shallow-to-deep. In the exceedance convention the shallow end is P99,
    so the grid must start at 99 and end at 1 — and the first pair must be the *smaller* column.
    """
    import numpy as np

    from hcwc.core import calibration

    built = np.linspace(10.0, 500.0, 5_000)
    mine, theirs = calibration.quantile_pairs(built, built)
    grid = calibration.exceedance_grid()

    assert grid.size == mine.size
    assert grid[0] == 99.0 and grid[-1] == 1.0
    assert mine[0] < mine[-1], "pairs must run shallow to deep"
    # And the value at exceedance P99 must be what `exceedance_percentile` agrees it is: 99 % of
    # the distribution reaches at least the shallow end.
    assert calibration.exceedance_percentile(mine[0], built) == pytest.approx(99.0, abs=1.0)
    assert calibration.exceedance_percentile(mine[-1], built) == pytest.approx(1.0, abs=1.0)


def test_a_stale_dhi_posterior_is_flagged_rather_than_averaged_in(real_minimum):
    """Tab 6.0 renders after tab 4.0, so a changed trial count leaves the posterior one run behind.

    The panel's own denominator would then disagree with the DHI check's, silently. That is the
    exact class of error this panel exists to catch, so it catches its own.
    """
    other = engine.run(real_minimum.limit_set, n=1_000, seed=real_minimum.seed)

    class _Posterior:
        result = other

        @property
        def effective_sample_size(self):
            return 900.0

        @property
        def r_dhi(self):
            return 2.0

    stale = trust.dhi_evidence(_Posterior(), real_minimum)
    assert stale.level == "watch"
    assert "one interaction behind" in stale.finding

    # Same posterior, judged against the run it was actually built on: no complaint.
    assert trust.dhi_evidence(_Posterior(), other).level == "ok"
