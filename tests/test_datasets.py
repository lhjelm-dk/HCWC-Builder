"""Importing someone else's column-height dataset.

The reader's job is to accept a file it did not design and say what it had to assume. So the tests
are mostly about the *notes*: a repair that happens silently is the failure mode, not a repair that
happens.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hcwc.io import datasets


def make_csv(**overrides) -> str:
    """A small, coherent dataset: 60 closures, a log-normal capacity, filled where it spills."""
    rng = np.random.default_rng(7)
    trap = np.exp(rng.normal(np.log(250.0), 0.7, 60))
    capacity = np.exp(rng.normal(np.log(200.0), 0.8, 60))
    frame = pd.DataFrame({"trap_height_m": trap.round(2),
                          "hc_column_m": np.minimum(capacity, trap).round(2)})
    for key, value in overrides.items():
        frame[key] = value
    return frame.to_csv(index=False)


def trap_dependent_csv() -> str:
    """The realistic case: seal capacity rising with closure height.

    Edmundson et al. report r = 0.86 between column height and trap height on the NCS, so a
    fixture where the two are independent is a stress case rather than a representative one. Both
    are used, and the tests say which property belongs to which.
    """
    rng = np.random.default_rng(11)
    trap = np.exp(rng.normal(np.log(250.0), 0.8, 80))
    capacity = np.exp(rng.normal(np.log(1.4 * trap ** 0.75), 0.5))
    return pd.DataFrame({"trap_height_m": trap.round(2),
                         "hc_column_m": np.minimum(capacity, trap).round(2)}).to_csv(index=False)


class TestWhatItRequires:
    def test_a_closure_and_a_column_are_enough(self):
        d = datasets.read_csv(make_csv(), name="x")
        assert d.n == 60
        assert d.predictors == ("trap_height",)

    def test_missing_the_two_required_fields_says_which_and_lists_what_is_there(self):
        csv = "field,net_pay_m,fluid\n" + "".join(f"F{i},{10 + i},oil\n" for i in range(30))
        with pytest.raises(datasets.DatasetError) as err:
            datasets.read_csv(csv, name="x")
        message = str(err.value)
        assert "trap_height_m" in message and "hc_column_m" in message
        # and it lists what the file *does* have, so the user can see what to rename
        assert "net_pay_m" in message

    def test_a_tiny_dataset_is_refused_rather_than_fitted(self):
        """Fitting a benchmark family on ten discoveries describes the sample, not the geology."""
        frame = pd.DataFrame({"trap_height_m": [100.0] * 10, "hc_column_m": [50.0] * 10})
        with pytest.raises(datasets.DatasetError, match="twenty"):
            datasets.read_csv(frame.to_csv(index=False), name="x")

    @pytest.mark.parametrize("header", ["closure_height", "Closure Height (m)", "relief_m",
                                        "TRAPHEIGHT"])
    def test_the_closure_column_is_found_under_its_usual_spellings(self, header):
        frame = pd.read_csv(pd.io.common.StringIO(make_csv()))
        frame = frame.rename(columns={"trap_height_m": header})
        assert datasets.read_csv(frame.to_csv(index=False), name="x").n == 60


class TestWhatItInfers:
    def test_the_censoring_flag_is_derived_and_said_so(self):
        d = datasets.read_csv(make_csv(), name="x")
        assert any("derived" in note for note in d.notes)
        assert 0.0 < d.censored_fraction < 1.0

    def test_a_supplied_flag_is_used_instead_of_derived(self):
        d = datasets.read_csv(make_csv(filled_to_spill=0), name="x")
        assert any("taken from the file's own flag" in note for note in d.notes)
        assert d.censored_fraction == 0.0

    def test_apex_depth_stands_in_for_burial_and_says_so(self):
        """Lars's ruling, 28 Aug 2026: use apex depth where burial depth is absent."""
        d = datasets.read_csv(make_csv(apex_depth_m=2050.0), name="x")
        assert d.full_model
        assert any("Apex depth used in place of burial depth" in note for note in d.notes)

    def test_burial_depth_is_preferred_over_apex_when_both_are_present(self):
        d = datasets.read_csv(make_csv(burial_depth_m=3000.0, apex_depth_m=2050.0), name="x")
        assert d.full_model
        assert not any("Apex depth used" in note for note in d.notes)
        assert d.rows["burial_depth_m"].iloc[0] == 3000.0

    def test_no_depth_at_all_drops_to_the_weaker_model_loudly(self):
        d = datasets.read_csv(make_csv(), name="x")
        assert not d.full_model
        assert any("weaker model" in note for note in d.notes)


class TestRowsThatCannotBeTrue:
    """A column taller than its own closure. The tool's own reference file has 88 of them."""

    def csv_with_impossible_rows(self) -> str:
        frame = pd.read_csv(pd.io.common.StringIO(make_csv()))
        frame.loc[0, "hc_column_m"] = frame.loc[0, "trap_height_m"] * 30.0   # wildly impossible
        frame.loc[1, "hc_column_m"] = frame.loc[1, "trap_height_m"] * 1.008  # a filled trap
        return frame.to_csv(index=False)

    def test_the_impossible_row_is_flagged_kept_and_excluded(self):
        d = datasets.read_csv(self.csv_with_impossible_rows(), name="x")
        assert d.n == 60, "flagged, not dropped -- a discarded row is a decision nobody can audit"
        assert len(d.usable) == 59
        assert any("not possible for a simple structure" in note for note in d.notes)

    def test_a_column_a_shade_over_its_closure_is_a_filled_trap_not_an_error(self):
        d = datasets.read_csv(self.csv_with_impossible_rows(), name="x")
        assert bool(d.rows["filled_to_spill"].iloc[1])
        assert not bool(d.rows["column_exceeds_trap"].iloc[1])
        assert any("clipped to the closure" in note for note in d.notes)

    def test_the_fit_runs_despite_them(self):
        """`censored_loglinear` refuses a column over its trap, so the clip is load-bearing."""
        d = datasets.read_csv(self.csv_with_impossible_rows(), name="x")
        assert np.isfinite(datasets.fit(d).sigma)


class TestTheFamilyItProduces:
    def test_no_sample_exceeds_the_closure_it_was_drawn_for(self):
        d = datasets.read_csv(make_csv(), name="x")
        drawn = datasets.column_height(d, np.random.default_rng(0), 300.0, 2000.0, 5_000)
        assert drawn.max() <= 300.0 + 1e-9

    def test_the_filled_share_falls_as_the_closure_grows(self):
        """The pattern every published compilation reports, and a real check on the fit.

        Graham et al. (2015): 40 % of structures shorter than 250 m fill to spill, declining
        towards zero by 800 m. A fitted family that did not reproduce the *direction* of that would
        be wrong in a way no goodness-of-fit statistic would show.
        """
        d = datasets.read_csv(make_csv(), name="x")
        fitted = datasets.fit(d)
        rng = np.random.default_rng(3)
        shares = [
            (datasets.column_height(d, rng, h, 2000.0, 20_000, fitted=fitted) >= h * 0.999).mean()
            for h in (100.0, 400.0, 1200.0)
        ]
        assert shares[0] > shares[1] > shares[2], shares

    def test_a_bigger_closure_gives_a_taller_median_only_while_it_binds(self):
        """Saturation is the right answer, and it took a failing test to see it.

        In `make_csv` the seal capacity is drawn independently of the closure, so past the point
        where the closure stops binding a bigger closure buys nothing -- the column is whatever
        the seal holds. The first version of this test asserted a median rising without limit and
        failed at 192 m against 190 m, which is the model being right rather than wrong.

        Real data is not like that: Edmundson report r = 0.86 between column and trap height, so
        `trap_dependent_csv` below is the realistic case and gets the monotone assertion.
        """
        d = datasets.read_csv(make_csv(), name="x")
        fitted = datasets.fit(d)
        rng = np.random.default_rng(4)
        medians = [float(np.median(datasets.column_height(d, rng, h, 2000.0, 20_000,
                                                          fitted=fitted)))
                   for h in (100.0, 400.0, 1200.0)]
        assert medians[0] < medians[1], medians
        assert medians[2] == pytest.approx(medians[1], rel=0.10), (
            "with capacity independent of closure, the median must saturate rather than keep "
            f"climbing: {medians}")

    def test_when_capacity_scales_with_closure_the_median_keeps_climbing(self):
        d = datasets.read_csv(trap_dependent_csv(), name="x")
        fitted = datasets.fit(d)
        rng = np.random.default_rng(5)
        medians = [float(np.median(datasets.column_height(d, rng, h, 2000.0, 20_000,
                                                          fitted=fitted)))
                   for h in (100.0, 400.0, 1200.0)]
        assert medians[0] < medians[1] < medians[2], medians


def test_nothing_here_touches_the_disk_or_the_network():
    """An imported dataset may be confidential. It lives in the session and nowhere else.

    Asserted against the source rather than by sandboxing, because the property worth protecting is
    that nobody *adds* a cache later without noticing what it would mean.
    """
    import pathlib
    source = pathlib.Path(datasets.__file__).read_text(encoding="utf-8")
    for forbidden in ("open(", "to_csv(", "write_text(", "requests", "urlopen", "st.cache"):
        assert forbidden not in source, f"{forbidden!r} in datasets.py — imported data must not leave the session"


class TestTheReaderRefusesForTheRightReason:
    """The content checks were already strong. These are the two cases where the *diagnosis* was
    wrong, and the one where there was no check at all."""

    @staticmethod
    def _rows(n):
        return "hc_column_m,trap_height_m\n" + "100,200\n" * n

    def test_a_dataset_of_any_size_is_no_longer_accepted(self):
        """The one path that takes a file of any size from whoever is using the app. On a shared
        server a long-lived process holds every dataset anyone imports."""
        assert datasets.read_csv(self._rows(50), name="ok").rows.shape[0] == 50
        with pytest.raises(datasets.DatasetError, match="rows, over the"):
            datasets.read_csv(self._rows(datasets.MAX_ROWS + 1), name="huge")

    def test_a_file_of_any_length_is_refused_before_it_is_parsed(self):
        with pytest.raises(datasets.DatasetError, match="MB, over the"):
            datasets.read_csv("x" * (datasets.MAX_CHARS + 1), name="huge")

    def test_a_semicolon_file_is_told_about_its_separator(self):
        """Excel on a European locale writes semicolons. The file then parses as one column whose
        *name* is the whole header line — so the reader reported the two required columns missing
        while looking straight at both of them."""
        with pytest.raises(datasets.DatasetError, match="semicolon- or tab-separated"):
            datasets.read_csv("hc_column_m;trap_height_m\n100;200\n150;300\n", name="eu")

    def test_comma_decimals_are_named_rather_than_counted(self):
        """Same trap one step further in: the columns are found, every value is a string like
        `"100,5"`, and the reader said "0 usable rows" — which sends the reader to look at their
        data rather than at the decimal mark."""
        with pytest.raises(datasets.DatasetError, match="decimal mark"):
            datasets.read_csv(
                'hc_column_m,trap_height_m\n"100,5","200,5"\n"150,5","300,5"\n', name="eu")

    def test_genuinely_unusable_values_still_report_as_unusable(self):
        """The two messages above must not swallow the ordinary case."""
        with pytest.raises(datasets.DatasetError, match="usable rows"):
            datasets.read_csv("hc_column_m,trap_height_m\nabc,def\nghi,jkl\n", name="e")
