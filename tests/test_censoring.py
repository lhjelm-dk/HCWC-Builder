"""The censoring argument, as executable assertions.

These tests are the evidence behind the claim in `docs/HCWC_Builder_PLAN.md` §5.3 that
published column-height-vs-trap-height correlations are contaminated by filled-to-spill
observations. If the claim is wrong, these fail.

The simulation is deliberately generous to the published method: clean lognormals, no
measurement error, no depth-conversion uncertainty, n = 242 to match Edmundson. The bias
shown here is therefore a *floor*, not a worst case.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.core import censoring

N = 242                 # Edmundson's sample size
SIGMA_H = 0.7           # spread of log trap height
SIGMA_S = 0.8           # spread of log seal capacity


def synth(rng: np.random.Generator, corr: float, n: int = N):
    """Trap height H, seal capacity S with a *known* log-log relationship, and C=min(S,H).

    The true log-log slope of S on H is ``corr * SIGMA_S / SIGMA_H`` by construction.
    """
    h = np.exp(rng.normal(np.log(200.0), SIGMA_H, n))
    zh = (np.log(h) - np.log(200.0)) / SIGMA_H
    zs = corr * zh + np.sqrt(1.0 - corr**2) * rng.normal(0.0, 1.0, n)
    s = np.exp(np.log(250.0) + SIGMA_S * zs)
    return h, np.minimum(s, h)


def true_slope(corr: float) -> float:
    return corr * SIGMA_S / SIGMA_H


class TestTheArtefact:
    def test_zero_physics_still_yields_a_strong_apparent_correlation(self):
        """The headline. Seal capacity independent of trap height; OLS says otherwise."""
        rng = np.random.default_rng(7)
        slopes = []
        for _ in range(300):
            h, c = synth(rng, corr=0.0)
            slopes.append(censoring.naive_slope(h, c))
        mean_slope = float(np.mean(slopes))
        assert true_slope(0.0) == 0.0
        assert mean_slope > 0.45, (
            f"expected a large spurious slope from censoring alone, got {mean_slope:.3f}"
        )

    def test_filtering_out_filled_to_spill_does_not_fix_it(self):
        """Dropping the censored points trades censoring bias for truncation bias."""
        rng = np.random.default_rng(7)
        naive, filtered = [], []
        for _ in range(300):
            h, c = synth(rng, corr=0.0)
            naive.append(censoring.naive_slope(h, c))
            filtered.append(censoring.filtered_slope(h, c, h))
        assert float(np.mean(filtered)) > 0.40, (
            "filtering was expected to leave most of the bias in place"
        )


class TestTheFix:
    @pytest.mark.parametrize("corr", [0.0, 0.3, 0.7])
    def test_censored_mle_recovers_the_true_slope(self, corr):
        rng = np.random.default_rng(11)
        slopes = [
            censoring.censored_slope(*(lambda hc: (hc[0], hc[1], hc[0]))(synth(rng, corr))).slope
            for _ in range(120)
        ]
        assert float(np.mean(slopes)) == pytest.approx(true_slope(corr), abs=0.05)

    def test_it_beats_the_naive_estimator_on_the_hardest_case(self):
        rng = np.random.default_rng(3)
        h, c = synth(rng, corr=0.0)
        fit = censoring.censored_slope(h, c, h)
        assert abs(fit.slope) < abs(censoring.naive_slope(h, c))

    def test_reports_how_much_of_the_sample_was_censored(self):
        rng = np.random.default_rng(3)
        h, c = synth(rng, corr=0.0)
        fit = censoring.censored_slope(h, c, h)
        assert 0.3 < fit.censored_fraction < 0.9
        assert fit.n_censored + (fit.n_total - fit.n_censored) == N


class TestSpillCensoring:
    def test_flags_exact_fills(self):
        h = np.array([100.0, 200.0, 300.0])
        c = np.array([100.0, 150.0, 120.0])
        assert list(censoring.spill_censoring(c, h)) == [True, False, False]

    def test_tolerance_absorbs_mapping_noise(self):
        h = np.array([300.0])
        c = np.array([299.5])
        assert censoring.spill_censoring(c, h, tol_m=1.0)[0]
        assert not censoring.spill_censoring(c, h, tol_m=0.1)[0]

    def test_column_taller_than_closure_is_rejected(self):
        with pytest.raises(ValueError, match="cannot be taller"):
            censoring.spill_censoring(np.array([400.0]), np.array([300.0]))

    def test_all_censored_sample_is_refused_not_guessed(self):
        h = np.array([100.0, 200.0, 300.0, 400.0])
        with pytest.raises(ValueError, match="not identifiable"):
            censoring.censored_slope(h, h.copy(), h)


class TestOnThePublishedData:
    """The same argument, on Edmundson's own 242 rows rather than on a simulation.

    Their published matrix reproduces exactly from the shipped CSV, so any disagreement
    below is about the estimator, not about the observations.
    """

    def data(self):
        from hcwc.io import benchmarks
        d = benchmarks.load_edmundson().rows
        return (d.trap_height_m.to_numpy(float),
                d.hc_column_m.to_numpy(float),
                d.burial_depth_m.to_numpy(float))

    def test_the_shipped_data_is_the_published_data(self):
        from hcwc.io import benchmarks
        d = benchmarks.load_edmundson(use_authors_flag=True).rows
        assert len(d) == 242
        assert int(d.filled_to_spill.sum()) == 111        # the paper's own 111/242

    def test_published_matrix_reproduces_from_the_rows(self):
        from hcwc.io import benchmarks
        m = benchmarks.load_edmundson_matrix()
        assert m.n.sum() == 242
        assert np.allclose(m.p_fill_100, m.n_filled_authors / m.n)
        cols = ["p_fill_0_50", "p_fill_51_75", "p_fill_76_99", "p_fill_100"]
        assert np.allclose(m[cols].sum(axis=1), 1.0)

    def test_nearly_half_the_dataset_is_censored(self):
        H, C, _ = self.data()
        assert censoring.spill_censoring(C, H).mean() == pytest.approx(0.459, abs=0.01)

    def test_censoring_inflates_trap_height_and_halves_burial_depth(self):
        """The headline result on real data. Both directions matter."""
        H, C, D = self.data()
        fit = censoring.censored_loglinear({"trap_height": H, "burial_depth": D}, C, H)
        x = np.column_stack([np.ones(C.size), np.log(H), np.log(D)])
        naive, *_ = np.linalg.lstsq(x, np.log(C), rcond=None)

        assert naive[1] == pytest.approx(0.880, abs=0.01)
        assert naive[2] == pytest.approx(0.143, abs=0.01)
        assert fit.coefficients["trap_height"] == pytest.approx(0.70, abs=0.04)
        assert fit.coefficients["burial_depth"] == pytest.approx(0.28, abs=0.04)

        # The paper calls burial depth the weaker control. Corrected, it roughly doubles.
        assert fit.coefficients["burial_depth"] > 1.6 * naive[2]
        # And the trap-height term, which the paper calls strong, is overstated.
        assert fit.coefficients["trap_height"] < naive[1]

    def _p_spill(self, fit, h, z):
        from scipy.stats import norm
        mu = (fit.intercept + fit.coefficients["trap_height"] * np.log(h)
              + fit.coefficients["burial_depth"] * np.log(z))
        return norm.sf((np.log(h) - mu) / fit.sigma)

    def test_the_fitted_model_reproduces_the_observed_fill_rate(self):
        """Calibration, band by band. This is what validates the parametric form.

        An earlier version of this test asserted that the model's fill probability *at*
        h = 250 m (0.39) matched Graham's "40% of structures shorter than 250 m", and
        called that an independent cross-check. It was not one: Graham states a
        population average over traps below 250 m, not the value at 250 m. Compared
        properly, the model averages 0.545 over the 163 NCS traps under 250 m against an
        observed 0.540 -- much better agreement, but with the NCS, not with Graham.
        """
        H, C, D = self.data()
        fit = censoring.censored_loglinear({"trap_height": H, "burial_depth": D}, C, H)
        filled = censoring.spill_censoring(C, H)
        for lo, hi in ((0, 150), (150, 250), (250, 400), (400, 1e9)):
            m = (H >= lo) & (H < hi)
            predicted = float(np.mean([self._p_spill(fit, h, z) for h, z in zip(H[m], D[m])]))
            assert predicted == pytest.approx(float(filled[m].mean()), abs=0.06), (
                f"band {lo}-{hi} m is not calibrated"
            )

    def test_the_ncs_fills_to_spill_more_often_than_grahams_global_figure(self):
        """A real regional difference, not a discrepancy to explain away.

        Graham et al. report 40% of traps under 250 m filled to spill, globally. The NCS
        gives 54%. Edmundson et al. say plainly that NCS basins "have received plentiful
        hydrocarbon charge, so charge limitation is not a significant issue" -- so a
        charge-rich shelf filling more often than the world average is the expected
        direction, and it is exactly why Graham warns against global benchmarks without
        trap-specific geology.
        """
        H, C, _ = self.data()
        ncs = float(censoring.spill_censoring(C, H)[H < 250.0].mean())
        assert ncs == pytest.approx(0.54, abs=0.03)
        assert ncs > 0.40 + 0.05, "the NCS/global gap should be material, not noise"


class TestSharedApexMeasurementError:
    """A second bias, working the same direction, that censoring does NOT remove.

    Column height = contact - apex. Trap height = spill - apex. **The same apex pick enters
    both**, so a depth-conversion error on the apex moves them together and manufactures a
    positive relationship between them out of nothing.

    This is an errors-in-variables problem sitting on top of the censoring problem, and no
    censored estimator can see it -- the estimator is given the mismeasured numbers.
    """

    def synth_with_apex_error(self, rng, sigma_apex, n=242):
        apex = rng.normal(2500.0, 400.0, n)
        spill = apex + np.exp(rng.normal(np.log(200.0), 0.7, n))
        capacity = np.exp(rng.normal(np.log(250.0), 0.8, n))   # independent of trap height
        contact = apex + np.minimum(capacity, spill - apex)
        err = rng.normal(0.0, sigma_apex, n)                   # ONE shared error
        h = np.clip(spill - (apex + err), 5.0, None)
        c = np.clip(contact - (apex + err), 1.0, None)
        return h, np.minimum(c, h)

    def test_no_apex_error_means_the_censored_fit_is_clean(self):
        rng = np.random.default_rng(5)
        slopes = [censoring.censored_slope(*(lambda t: (t[0], t[1], t[0]))(
            self.synth_with_apex_error(rng, 0.0))).slope for _ in range(80)]
        assert float(np.mean(slopes)) == pytest.approx(0.0, abs=0.06)

    def test_a_realistic_apex_error_manufactures_most_of_the_observed_elasticity(self):
        """50 m at 2500 m is 2% -- ordinary depth conversion. Truth is 0.00."""
        rng = np.random.default_rng(5)
        slopes = [censoring.censored_slope(*(lambda t: (t[0], t[1], t[0]))(
            self.synth_with_apex_error(rng, 50.0))).slope for _ in range(80)]
        spurious = float(np.mean(slopes))
        assert spurious > 0.4, f"expected a large spurious elasticity, got {spurious:.3f}"

    def test_the_bias_grows_with_the_apex_error(self):
        rng = np.random.default_rng(5)
        got = []
        for sigma in (10.0, 50.0, 100.0):
            got.append(float(np.mean([censoring.censored_slope(*(lambda t: (t[0], t[1], t[0]))(
                self.synth_with_apex_error(rng, sigma))).slope for _ in range(50)])))
        assert got[0] < got[1] < got[2]

    def test_the_predictor_scale_is_why_burial_depth_survives_it(self):
        """The asymmetry that makes our burial-depth result the robust one.

        The same absolute apex error is ~25% of a 200 m trap height but ~2% of a 2500 m
        burial depth. The relative corruption differs by an order of magnitude, which is
        why the trap-height elasticity should be read as an upper bound while the
        burial-depth elasticity should not.
        """
        apex_error, typical_trap_height, typical_burial_depth = 50.0, 200.0, 2500.0
        assert (apex_error / typical_trap_height) / (apex_error / typical_burial_depth) > 10.0


class TestTheBenchmarkFamily:
    """The curves tab 7.0 §7 draws, and the specific numbers its text quotes.

    The family chart is where the censoring argument stops being about a coefficient and becomes
    about a deliverable — a prior for a closure of a given size. Every number asserted here appears
    in the UI copy, so if the fit moves, the test fails before the text becomes a false claim.
    """

    @staticmethod
    def _fits():
        from hcwc.io import benchmarks
        d = benchmarks.load_edmundson().rows
        h = d.trap_height_m.to_numpy(float)
        c = d.hc_column_m.to_numpy(float)
        z = d.burial_depth_m.to_numpy(float)
        fit = censoring.censored_loglinear({"trap_height": h, "burial_depth": z}, c, h)
        naive, *_ = np.linalg.lstsq(
            np.column_stack([np.ones(c.size), np.log(h), np.log(z)]), np.log(c), rcond=None)
        return fit, naive

    @staticmethod
    def _family(mu_of, sigma, closure, burial=2500.0, n=40_000):
        rng = np.random.default_rng(20260825)
        drawn = np.minimum(np.exp(rng.normal(mu_of(closure, burial), sigma, n)), closure)
        return float(np.percentile(drawn, 50)), float(np.mean(drawn >= closure - 1e-9))

    def test_the_fill_fraction_falls_as_the_closure_grows(self):
        """A bigger closure is harder to fill. If a benchmark's fill fraction were flat, it would
        be saying the closure never binds, and the whole family chart would be pointless."""
        fit, _ = self._fits()
        mu = lambda h, z: (fit.intercept + fit.coefficients["trap_height"] * np.log(h)
                           + fit.coefficients["burial_depth"] * np.log(z))
        fractions = [self._family(mu, fit.sigma, h)[0] / h for h in (100, 200, 400, 800)]
        assert fractions == sorted(fractions, reverse=True)
        assert fractions[0] > 0.95 and fractions[-1] < 0.7

    def test_the_naive_family_fans_out_further_than_the_corrected_one(self):
        """The claim the UI makes in words: the published estimator overstates the closure
        elasticity, so it under-fills small closures and over-fills the largest.

        This is the interesting direction, and it is not the one guessed first — the naive fit is
        *pessimistic* on small closures, where the censoring it omits does its damage.
        """
        fit, naive = self._fits()
        mu_c = lambda h, z: (fit.intercept + fit.coefficients["trap_height"] * np.log(h)
                             + fit.coefficients["burial_depth"] * np.log(z))
        mu_n = lambda h, z: naive[0] + naive[1] * np.log(h) + naive[2] * np.log(z)

        small_c, spill_c = self._family(mu_c, fit.sigma, 100.0)
        small_n, spill_n = self._family(mu_n, fit.sigma, 100.0)
        assert small_n < small_c and spill_n < spill_c   # under-fills the small closure
        assert small_c == pytest.approx(100, abs=3) and small_n == pytest.approx(82, abs=5)
        assert spill_c == pytest.approx(0.59, abs=0.04)
        assert spill_n == pytest.approx(0.37, abs=0.04)

        big_c, _ = self._family(mu_c, fit.sigma, 800.0)
        big_n, _ = self._family(mu_n, fit.sigma, 800.0)
        assert big_n > big_c                              # over-fills the large closure
        assert big_c == pytest.approx(490, abs=15) and big_n == pytest.approx(514, abs=15)

    def test_the_corrected_family_reproduces_the_observed_spill_rate(self):
        """46 % of the 242 discoveries filled to spill. Averaged over the closure heights actually
        present in the dataset, the corrected family must land near that — the calibration check
        that makes the family a benchmark rather than a shape."""
        from hcwc.io import benchmarks
        fit, _ = self._fits()
        d = benchmarks.load_edmundson().rows
        mu = lambda h, z: (fit.intercept + fit.coefficients["trap_height"] * np.log(h)
                           + fit.coefficients["burial_depth"] * np.log(z))
        rng = np.random.default_rng(11)
        h = d.trap_height_m.to_numpy(float)
        z = d.burial_depth_m.to_numpy(float)
        drawn = np.exp(rng.normal(mu(h, z), fit.sigma))
        assert float(np.mean(drawn >= h)) == pytest.approx(float(d.filled_to_spill.mean()),
                                                           abs=0.06)

    def test_grahams_family_stops_filling_to_spill_above_800_m(self):
        """The published endpoint, and the one place the linear reading of Graham's decay is
        pinned: the weight reaches zero at 800 m by construction."""
        from hcwc.io import benchmarks
        rng = np.random.default_rng(3)
        assert np.mean(benchmarks.graham_column_height(rng, 800.0, 20_000) >= 800.0) < 0.01
        assert np.mean(benchmarks.graham_column_height(rng, 200.0, 20_000) >= 200.0) \
            == pytest.approx(0.4, abs=0.02)

    def test_the_published_fit_cannot_reproduce_its_own_datasets_filling_behaviour(self):
        """The cleanest statement of the whole argument, and the one that needs no simulation.

        Ask each fit to reproduce the one statistic anybody can check by counting rows: how often a
        discovery fills to spill. Draw a column for every discovery at its own closure height and
        burial depth, and count. 45.9 % of the 242 do; the corrected fit says 47.4 %, the paper's
        says 32.3 %.

        It is a *self-consistency* failure, which is why it matters — no outside benchmark, no
        synthetic truth, no appeal to a preferred estimator. And it fails in exactly the direction
        the omitted censoring predicts: treating a closure's ceiling as evidence about the seal
        makes seals look more capable than they are, so fewer prospects fill.
        """
        from hcwc.io import benchmarks
        fit, naive = self._fits()
        d = benchmarks.load_edmundson().rows
        h = d.trap_height_m.to_numpy(float)
        z = d.burial_depth_m.to_numpy(float)
        observed = float(d.filled_to_spill.mean())

        rng = np.random.default_rng(11)
        mu_c = (fit.intercept + fit.coefficients["trap_height"] * np.log(h)
                + fit.coefficients["burial_depth"] * np.log(z))
        mu_n = naive[0] + naive[1] * np.log(h) + naive[2] * np.log(z)
        rate = lambda mu: float(np.mean([np.mean(np.exp(rng.normal(mu, fit.sigma)) >= h)
                                         for _ in range(200)]))
        corrected, published = rate(mu_c), rate(mu_n)

        assert observed == pytest.approx(0.459, abs=0.005)
        assert corrected == pytest.approx(observed, abs=0.03)
        assert published == pytest.approx(0.323, abs=0.02)
        assert observed - published > 0.10


class TestTheShrinkagePrior:
    """Pulling an elicited seal capacity toward the NCS record, and what it must not do.

    Edmundson's §5.2 asks for base rates to be integrated with the geological assessment and does
    not say how. This is the version that survives scrutiny: the censoring-corrected fit predicts
    the *same quantity* the seal calculator computes, so the two can be averaged without either
    standing in for the other.
    """

    def test_zero_weight_is_a_true_no_op(self):
        """The control's default must not move a number, or every saved prospect changes meaning."""
        from hcwc.io import benchmarks
        own = np.exp(np.random.default_rng(0).normal(np.log(350.0), 0.45, 5_000))
        assert np.array_equal(benchmarks.shrink_toward(own, own * 0.1, 0.0), np.sort(own))

    def test_full_weight_lands_on_the_record(self):
        from hcwc.io import benchmarks
        own = np.exp(np.random.default_rng(1).normal(np.log(350.0), 0.45, 5_000))
        ncs = benchmarks.ncs_seal_capacity(2050.0, 5_000, 7)
        got = benchmarks.shrink_toward(own, ncs, 1.0)
        for p in (10, 50, 90):
            assert np.percentile(got, p) == pytest.approx(np.percentile(ncs, p), rel=0.02)

    def test_it_interpolates_monotonically_between_the_two(self):
        """Quantile averaging, so every percentile moves steadily — no second hump appearing."""
        from hcwc.io import benchmarks
        own = np.exp(np.random.default_rng(2).normal(np.log(350.0), 0.45, 5_000))
        ncs = benchmarks.ncs_seal_capacity(2050.0, 5_000, 7)
        medians = [float(np.percentile(benchmarks.shrink_toward(own, ncs, w), 50))
                   for w in (0.0, 0.25, 0.5, 0.75, 1.0)]
        assert np.all(np.diff(medians) < 0), "the NCS median is lower, so shrinking must lower it"

    def test_the_capacity_prior_deepens_with_burial(self):
        """Compaction closes pore throats, `P_c` goes as 1/r, so deeper should hold more."""
        from hcwc.io import benchmarks
        shallow = benchmarks.ncs_seal_capacity(1200.0, 20_000, 3)
        deep = benchmarks.ncs_seal_capacity(4000.0, 20_000, 3)
        assert np.percentile(deep, 50) > np.percentile(shallow, 50)

    def test_the_prior_is_a_capacity_and_is_never_clipped_at_a_spill_point(self):
        """The engine takes `min(capacity, spill)` itself; clipping here would apply it twice."""
        from hcwc.io import benchmarks
        drawn = benchmarks.ncs_seal_capacity(2050.0, 20_000, 5)
        assert drawn.max() > 1_000.0, (
            "an unclipped lognormal capacity should reach far beyond any one closure")

    def test_it_is_fitted_against_burial_alone(self):
        """Including trap height would put geometry inside a capillary property."""
        from hcwc.io import benchmarks
        fit = benchmarks._capacity_fit()
        rows = benchmarks.load_edmundson().rows
        assert 0.3 < fit.slope < 0.7
        assert fit.slope > censoring.naive_slope(
            rows.burial_depth_m.to_numpy(float),
            rows.hc_column_m.to_numpy(float)), (
            "censoring hides the deep well-sealed traps, so the corrected term must be larger")
