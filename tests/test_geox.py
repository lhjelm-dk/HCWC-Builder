"""The export has to be right in a way nothing downstream will catch.

If the exceedance convention is inverted, GeoX imports a contact distribution that is upside down
and every volume is wrong, with no error anywhere. So the convention gets its own tests.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.io import geox


@pytest.fixture
def contacts() -> np.ndarray:
    """Contact depths, m TVDSS: apex 2050, a spread of columns below it."""
    rng = np.random.default_rng(42)
    return 2050.0 + rng.lognormal(np.log(200.0), 0.5, 50_000)


class TestConvention:
    def test_p100_is_shallowest_and_p0_is_deepest(self, contacts):
        t = geox.percentile_table(contacts).table.set_index("Percentile")["Value"]
        assert t[100] < t[50] < t[0], "exceedance: P100 = shallowest, P0 = deepest"

    def test_values_decrease_monotonically_with_percentile(self, contacts):
        t = geox.percentile_table(contacts).table
        assert (t.Percentile.to_numpy() == np.arange(100, -1, -1)).all()
        assert np.all(np.diff(t.Value.to_numpy()) >= 0), "depth must increase as P falls"

    def test_p90_is_the_low_side_case(self, contacts):
        """P90 = 90% chance of being at least this deep = a shallow contact = small volume."""
        t = geox.percentile_table(contacts).table.set_index("Percentile")["Value"]
        assert t[90] == pytest.approx(np.percentile(contacts, 10.0), rel=1e-9)
        assert t[10] == pytest.approx(np.percentile(contacts, 90.0), rel=1e-9)


class TestShape:
    def test_101_rows(self, contacts):
        assert len(geox.percentile_table(contacts).table) == 101

    def test_seven_fractile_form(self, contacts):
        t = geox.percentile_table(contacts, points=geox.SEVEN_FRACTILES).table
        assert list(t.Percentile) == [100, 95, 90, 50, 10, 5, 0]

    def test_csv_is_two_named_columns(self, contacts):
        csv = geox.percentile_table(contacts).to_csv()
        assert csv.splitlines()[0] == "Percentile,Value"
        assert len(csv.strip().splitlines()) == 102          # header + 101

    def test_rejects_a_points_count_it_does_not_support(self, contacts):
        with pytest.raises(ValueError, match="101-fractile"):
            geox.percentile_table(contacts, points=51)


class TestTails:
    def test_truncation_pulls_the_endpoints_in(self, contacts):
        raw = geox.percentile_table(contacts, tail_mode="raw").table.set_index("Percentile")["Value"]
        cut = geox.percentile_table(contacts).table.set_index("Percentile")["Value"]
        assert cut[100] > raw[100], "the shallow endpoint should move deeper"
        assert cut[0] < raw[0], "the deep endpoint should move shallower"

    def test_raw_endpoints_are_the_sample_extremes(self, contacts):
        t = geox.percentile_table(contacts, tail_mode="raw").table.set_index("Percentile")["Value"]
        assert t[100] == pytest.approx(contacts.min())
        assert t[0] == pytest.approx(contacts.max())

    def test_truncated_endpoints_are_the_half_percent_points(self, contacts):
        t = geox.percentile_table(contacts).table.set_index("Percentile")["Value"]
        assert t[100] == pytest.approx(np.percentile(contacts, 0.5))
        assert t[0] == pytest.approx(np.percentile(contacts, 99.5))

    def test_the_interior_is_untouched_by_truncation(self, contacts):
        raw = geox.percentile_table(contacts, tail_mode="raw").table.Value.to_numpy()
        cut = geox.percentile_table(contacts).table.Value.to_numpy()
        assert np.allclose(raw[1:-1], cut[1:-1])

    def test_extrapolate_refuses_rather_than_improvising(self, contacts):
        with pytest.raises(NotImplementedError, match="not implemented"):
            geox.percentile_table(contacts, tail_mode="extrapolate")

    def test_unknown_mode_rejected(self, contacts):
        with pytest.raises(ValueError, match="unknown tail_mode"):
            geox.percentile_table(contacts, tail_mode="clip")


class TestProvenance:
    def test_names_the_convention_and_the_tails(self, contacts):
        e = geox.percentile_table(contacts)
        assert "P100 = shallowest" in e.provenance
        assert "P0.5/P99.5" in e.provenance
        assert "50,000" in e.provenance

    def test_raw_mode_says_so(self, contacts):
        assert "raw" in geox.percentile_table(contacts, tail_mode="raw").provenance


class TestGuards:
    def test_too_few_realisations(self):
        with pytest.raises(ValueError, match="at least two"):
            geox.percentile_table(np.array([2100.0]))

    def test_non_finite_values_are_dropped_not_propagated(self):
        x = np.array([2100.0, 2200.0, np.nan, 2300.0, np.inf])
        assert geox.percentile_table(x, tail_mode="raw").n_trials == 3


class TestTheExportSaysWhichDistributionItIs:
    """The defect this was written for: the 101-percentile export was **always** the geological
    distribution, even with a DHI switched on, and nothing on the page or in the file said so.

    A bare table of contact depths looks identical either way. Handed to GeoX for a DHI prospect it
    is the wrong distribution, and nothing downstream can catch it — which makes this the worst
    failure the tool had available to it.
    """

    def test_the_basis_leads_the_provenance_line(self):
        samples = np.random.default_rng(0).normal(2300.0, 60.0, 5_000)
        for basis in ("geological", "given the DHI"):
            line = geox.percentile_table(samples, basis=basis).provenance
            assert line.upper().startswith(basis.upper()), line

    def test_the_basis_travels_with_the_numbers(self):
        """It has to be recoverable from the object, not just printed once beside it."""
        samples = np.random.default_rng(1).normal(2300.0, 60.0, 2_000)
        assert geox.percentile_table(samples, basis="given the DHI").basis == "given the DHI"

    def test_it_still_defaults_to_geological_for_every_existing_caller(self):
        samples = np.random.default_rng(2).normal(2300.0, 60.0, 2_000)
        assert geox.percentile_table(samples).basis == "geological"

    def test_the_two_bases_give_genuinely_different_tables(self):
        """If they could not differ there would be nothing to label. A DHI that moves the contact
        moves the percentiles, which is exactly why the file needs to say which it holds."""
        rng = np.random.default_rng(3)
        geological = rng.normal(2300.0, 60.0, 20_000)
        updated = rng.normal(2240.0, 35.0, 20_000)          # a pick has tightened and shallowed it
        a = geox.percentile_table(geological, basis="geological")
        b = geox.percentile_table(updated, basis="given the DHI")
        assert not np.allclose(a.table["Value"], b.table["Value"])
        assert a.provenance != b.provenance


def test_the_app_never_exports_without_a_stated_basis():
    """Scanned rather than trusted: every `percentile_table` call in the app either passes an
    explicit basis or takes the geological default, and the download filename carries it."""
    import pathlib
    import re

    app = (pathlib.Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
    calls = re.findall(r"geox\.percentile_table\((.*?)\)", app, re.S)
    assert calls, "the export moved — this test needs pointing at it"
    for call in calls:
        assert "basis=" in call, f"percentile_table called without a basis: {call[:90]}"
    assert "hcwc_percentiles_{basis" in app.replace("f\"", "\""), \
        "the download filename must carry the basis"
