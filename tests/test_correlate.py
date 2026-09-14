"""The Gaussian copula, and the two elicitation failures it is written against.

The claim to test is that the correlation asked for is the correlation delivered. That is
measurable, so it is measured — including the rank-versus-normal-score conversion, which is the
step it would be easiest to skip and hardest to notice missing.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.core import correlate, engine
from hcwc.core.limits import DepthDistribution, Group, Limit, LimitSet, reference_prospect

N = 60_000


def rng() -> np.random.Generator:
    return np.random.default_rng(4242)


class TestRankConversion:
    """Spearman in, normal-score parameter out. Skipping this delivers a weaker correlation."""

    def test_the_two_conversions_invert_each_other(self):
        for rho_s in (-0.9, -0.3, 0.0, 0.25, 0.7, 0.95):
            assert correlate.gaussian_to_spearman(
                correlate.spearman_to_gaussian(rho_s)) == pytest.approx(rho_s)

    def test_the_gaussian_parameter_is_larger_than_the_rank_correlation(self):
        """The reason the conversion matters — about 4 % at 0.7."""
        assert correlate.spearman_to_gaussian(0.7) > 0.7
        assert correlate.spearman_to_gaussian(0.7) == pytest.approx(0.7167, abs=1e-3)

    def test_the_endpoints_are_fixed(self):
        assert correlate.spearman_to_gaussian(0.0) == pytest.approx(0.0)
        assert correlate.spearman_to_gaussian(1.0) == pytest.approx(1.0)
        assert correlate.spearman_to_gaussian(-1.0) == pytest.approx(-1.0)


class TestDeliveredCorrelation:
    @pytest.mark.parametrize("target", [-0.7, -0.3, 0.0, 0.4, 0.8])
    def test_the_requested_rank_correlation_comes_back(self, target):
        m = np.array([[1.0, target], [target, 1.0]])
        u = correlate.correlated_uniforms(rng(), m, N)
        assert correlate.realised_spearman(u)[0, 1] == pytest.approx(target, abs=0.012)

    def test_skipping_the_conversion_would_undershoot(self):
        """What the naive implementation gives, so the difference is on record."""
        from scipy.stats import norm, spearmanr
        target = 0.8
        z = rng().standard_normal((N, 2)) @ np.linalg.cholesky(
            np.array([[1.0, target], [target, 1.0]])).T
        naive = spearmanr(norm.cdf(z))[0]
        assert naive < target - 0.01
        proper = correlate.realised_spearman(
            correlate.correlated_uniforms(rng(), np.array([[1.0, target], [target, 1.0]]), N))[0, 1]
        assert abs(proper - target) < abs(naive - target)

    def test_the_marginals_stay_uniform(self):
        u = correlate.correlated_uniforms(rng(), np.array([[1.0, 0.8], [0.8, 1.0]]), N)
        for j in (0, 1):
            assert u[:, j].mean() == pytest.approx(0.5, abs=0.005)
            assert u[:, j].min() > 0.0 and u[:, j].max() < 1.0

    def test_an_identity_matrix_gives_independent_columns(self):
        u = correlate.correlated_uniforms(rng(), np.eye(3), N)
        off = correlate.realised_spearman(u)[np.triu_indices(3, k=1)]
        assert np.all(np.abs(off) < 0.012)

    def test_three_way_structure_is_preserved(self):
        m = np.array([[1.0, 0.6, 0.0], [0.6, 1.0, 0.3], [0.0, 0.3, 1.0]])
        got = correlate.realised_spearman(correlate.correlated_uniforms(rng(), m, N))
        assert got[0, 1] == pytest.approx(0.6, abs=0.015)
        assert got[1, 2] == pytest.approx(0.3, abs=0.015)
        assert got[0, 2] == pytest.approx(0.0, abs=0.03)


class TestHigham:
    #: A and B correlated 0.9, B and C 0.9, A and C -0.9. Smallest eigenvalue -0.8.
    BAD = np.array([[1.0, 0.9, -0.9], [0.9, 1.0, 0.9], [-0.9, 0.9, 1.0]])

    def test_an_impossible_matrix_is_repaired_not_refused(self):
        assert np.min(np.linalg.eigvalsh(self.BAD)) < 0
        fixed = correlate.nearest_correlation_matrix(self.BAD)
        assert np.min(np.linalg.eigvalsh(fixed)) >= -1e-10

    def test_the_repaired_matrix_always_has_a_cholesky_factor(self):
        """The property that matters downstream, and the one SCOPE-HC's version does not have."""
        np.linalg.cholesky(correlate.nearest_correlation_matrix(self.BAD))

    def test_a_consistent_all_positive_matrix_is_already_valid(self):
        m = np.full((3, 3), 0.9)
        np.fill_diagonal(m, 1.0)
        assert np.min(np.linalg.eigvalsh(m)) > 0
        assert np.allclose(correlate.nearest_correlation_matrix(m), m, atol=1e-6)

    def test_force_psd_guarantees_a_unit_diagonal(self):
        out = correlate._force_psd(self.BAD)
        assert np.allclose(np.diag(out), 1.0)
        assert np.min(np.linalg.eigvalsh(out)) >= -1e-12

    def test_repair_keeps_the_diagonal_and_symmetry(self):
        bad = np.array([[1.0, 0.95, -0.95], [0.95, 1.0, 0.95], [-0.95, 0.95, 1.0]])
        fixed = correlate.nearest_correlation_matrix(bad)
        assert np.allclose(np.diag(fixed), 1.0)
        assert np.allclose(fixed, fixed.T)

    def test_a_valid_matrix_is_left_alone(self):
        m = np.array([[1.0, 0.5], [0.5, 1.0]])
        assert np.allclose(correlate.nearest_correlation_matrix(m), m, atol=1e-6)

    def test_describe_shows_both_the_asked_for_and_the_achievable(self):
        names = ("a", "b", "c")
        bad = np.array([[1.0, 0.9, -0.9], [0.9, 1.0, 0.9], [-0.9, 0.9, 1.0]])
        rows = correlate.describe(names, bad)
        assert len(rows) == 3
        assert any(abs(requested - achievable) > 0.05
                   for _, _, requested, achievable in rows), (
            "a correlation silently reduced by the projection must be visible")

    def test_an_impossible_request_still_samples(self):
        bad = np.array([[1.0, 0.9, -0.9], [0.9, 1.0, 0.9], [-0.9, 0.9, 1.0]])
        u = correlate.correlated_uniforms(rng(), bad, 20_000)
        assert u.shape == (20_000, 3)
        assert np.isfinite(u).all()


class TestMatrixBuilding:
    NAMES = ("Top seal (capillary)", "Base seal (capillary)", "Closure / spill")

    def test_pairs_become_a_symmetric_matrix(self):
        m = correlate.build_matrix(self.NAMES, {"Top seal (capillary)|Base seal (capillary)": 0.7})
        assert m[0, 1] == m[1, 0] == 0.7
        assert m[0, 2] == 0.0
        assert np.allclose(np.diag(m), 1.0)

    def test_an_unknown_limit_name_is_named_in_the_error(self):
        with pytest.raises(KeyError, match="Fault 9"):
            correlate.build_matrix(self.NAMES, {"Top seal (capillary)|Fault 9": 0.5})

    def test_a_malformed_key_is_refused(self):
        with pytest.raises(ValueError, match="must be 'name\\|name'"):
            correlate.build_matrix(self.NAMES, {"Top seal (capillary)": 0.5})

    def test_a_self_pair_is_refused(self):
        with pytest.raises(ValueError, match="with itself"):
            correlate.build_matrix(self.NAMES,
                                   {"Closure / spill|Closure / spill": 0.5})

    def test_an_out_of_range_correlation_is_refused(self):
        with pytest.raises(ValueError, match=r"outside \[-1, 1\]"):
            correlate.build_matrix(self.NAMES,
                                   {"Top seal (capillary)|Base seal (capillary)": 1.4})


class TestInTheEngine:
    """Both failure modes, and what correlation actually does to the answer."""

    def correlated_prospect(self, rho: float) -> LimitSet:
        base = reference_prospect()
        return LimitSet(apex=base.apex, limits=base.limits, name=base.name,
                        correlations={"Top seal (capillary)|Base seal (capillary)": rho,
                                      "Top seal (continuity)|Base seal (continuity)": rho})

    def test_no_correlations_declared_leaves_the_engine_unchanged(self):
        r = engine.run(reference_prospect(), 20_000)
        assert not reference_prospect().correlations
        assert r.uniforms.shape == (20_000, len(reference_prospect()))

    def test_the_declared_correlation_is_delivered(self):
        r = engine.run(self.correlated_prospect(0.7), N)
        # The realised matrix is over `correlated_names`, apex first, since 15 Sep 2026.
        names = list(self.correlated_prospect(0.7).correlated_names)
        i, j = names.index("Top seal (capillary)"), names.index("Base seal (capillary)")
        assert r.realised_correlation()[i, j] == pytest.approx(0.7, abs=0.02)
        assert r.realised_pairs()["Top seal (capillary)|Base seal (capillary)"] == \
            pytest.approx(0.7, abs=0.02)

    def test_an_apex_correlation_is_realised_and_reported(self):
        """The apex is a member of the correlated set. Its draw used to be discarded after
        sampling, so the Apex|spill pair the tab recommends could be requested and sampled but
        never read back as realised."""
        from hcwc.core.limits import APEX
        base = reference_prospect()
        spill = next(n for n in base.names if "spill" in n.lower())
        ls = LimitSet(apex=base.apex, limits=base.limits, name=base.name,
                      correlations={f"{APEX}|{spill}": 0.8})
        r = engine.run(ls, N)
        names = list(ls.correlated_names)
        assert names[0] == APEX
        assert r.realised_correlation().shape == (len(base.limits) + 1,) * 2
        assert r.realised_correlation()[0, names.index(spill)] == pytest.approx(0.8, abs=0.02)
        assert r.realised_pairs()[f"{APEX}|{spill}"] == pytest.approx(0.8, abs=0.02)

    def test_perfect_dependence_claims_two_limits_are_the_same_rock(self):
        """`TopandbaseSeal` has an off-diagonal of 1.0, not merely a positive number."""
        r = engine.run(self.correlated_prospect(1.0), 30_000)
        names = list(self.correlated_prospect(1.0).correlated_names)
        i, j = names.index("Top seal (capillary)"), names.index("Base seal (capillary)")
        got = r.realised_correlation()[i, j]
        assert got > 0.99, "perfect dependence must still be achievable, not merely near"

    def test_correlating_the_seals_changes_the_contact_distribution(self):
        """The reason B-1 matters: a correlation that is declared but empty changes the answer."""
        independent = engine.run(reference_prospect(), N)
        correlated = engine.run(self.correlated_prospect(0.9), N)
        assert abs(np.median(correlated.column_m) - np.median(independent.column_m)) > 0.5

    def two_seals(self, rho: float) -> LimitSet:
        """Two limits and nothing else, so the effect of correlating them is unambiguous."""
        dist = DepthDistribution("uniform", {"minimum": 0.0, "maximum": 400.0})
        return LimitSet(
            apex=DepthDistribution("fixed", {"value": 2000.0}),
            limits=(Limit("top seal", Group.RETENTION, 1.0, dist),
                    Limit("base seal", Group.RETENTION, 1.0, dist)),
            correlations={"top seal|base seal": rho} if rho else {})

    def test_correlating_two_limits_raises_the_minimum(self):
        """Counter-intuitive, and the reason it is tested in isolation.

        The contact is a **minimum**. Two *independent* limits give two independent opportunities
        for one to bite shallow; correlating them means that when one is shallow the other is too,
        so there are effectively fewer independent chances and the minimum is stochastically
        *larger*. Correlation moves the low side **up**, which is the opposite of the intuition that
        correlating risks makes things worse — that holds for sums, not for minima.

        For two uniforms on [0, 400] the independent minimum has mean 400/3 = 133.3; perfectly
        correlated they are the same draw, so the minimum has mean 200.
        """
        independent = engine.run(self.two_seals(0.0), N).column_m
        correlated = engine.run(self.two_seals(0.9), N).column_m
        assert independent.mean() == pytest.approx(400.0 / 3.0, abs=2.0)
        assert correlated.mean() > independent.mean() + 10.0
        for q in (1, 5, 10, 25, 50):
            assert np.percentile(correlated, q) > np.percentile(independent, q), f"P{q}"

    def test_perfect_correlation_makes_the_minimum_the_marginal(self):
        """At rho = 1 the two limits are one draw, so min(A, B) has A's own distribution."""
        column = engine.run(self.two_seals(0.999), N).column_m
        assert column.mean() == pytest.approx(200.0, abs=4.0)

    def test_on_the_full_prospect_the_effect_is_real_but_localised(self):
        """With nine limits competing, correlating two of them moves the answer without
        dominating it — the other limits still bind where they bound before."""
        independent = engine.run(reference_prospect(), N)
        correlated = engine.run(self.correlated_prospect(0.9), N)
        assert abs(np.median(correlated.column_m) - np.median(independent.column_m)) > 0.5
        assert abs(correlated.column_m.mean() - independent.column_m.mean()) < 20.0

    def test_correlations_survive_a_round_trip(self, tmp_path):
        original = self.correlated_prospect(0.65)
        loaded = LimitSet.load(original.save(tmp_path / "p.json"))
        assert loaded.correlations == original.correlations
        assert np.array_equal(engine.run(original, 5000, seed=1).column_m,
                              engine.run(loaded, 5000, seed=1).column_m)

    def test_a_correlation_naming_a_missing_limit_fails_loudly(self):
        base = reference_prospect()
        broken = LimitSet(apex=base.apex, limits=base.limits,
                          correlations={"Top seal (capillary)|Nonexistent": 0.5})
        with pytest.raises(KeyError, match="Nonexistent"):
            engine.run(broken, 1000)
