"""The two outward contracts: element risk in from E-POS, trials and curves out to WellVolPOS.

The most valuable test here is `test_wellvolpos_maps_every_column_we_export`, which runs
WellVolPOS's *own* adapter over our file. A contract asserted only against my reading of the other
repo is a contract asserted against my reading; this one asks the consumer.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import numpy as np
import pytest

from hcwc.core import charge, decompose, engine
from hcwc.core.limits import Group, reference_prospect
from hcwc.io import epos
from hcwc.io import wellvolpos as wvp

WELLVOLPOS = Path("D:/Dokumenter/Lars/Pythonscripts/WellVolPOS")


@pytest.fixture(scope="module")
def result():
    return engine.run(dataclasses.replace(reference_prospect(), min_column_m=40.0), 4_000)


@pytest.fixture(scope="module")
def table():
    return charge.AreaDepthTable.reference()


# --------------------------------------------------------------------------- E-POS in
EPOS_CSV = (
    "# GeoRisk Prospect,Tofte North,LH,Halten Terrace,2026-08-25,1.2\n"
    "# ESL play,{}\n"
    "# Classic POS,0.85,0.95,0.6,0.72\n"
    "model,pillar,sub_element,success_criteria,p_success\n"
)

EPOS_CSV_WITH_ESL = (
    "# GeoRisk Prospect,Tofte North,LH,Halten Terrace,2026-08-25,1.2\n"
    '# ESL play,"{""Charge"": {""support_for"": 0.8}}"\n'
    "# Classic POS,0.85,0.95,0.6,0.72\n"
)


class TestEposImport:
    def test_it_reads_the_classic_pos_row_in_e_pos_s_own_order(self):
        """Positional, not keyed: E-POS writes charge, closure, reservoir, retention. Reading them
        in any other order would silently swap two elements and still validate."""
        got = epos.read(EPOS_CSV)
        assert got.values == {"Charge": 0.85, "Closure": 0.95,
                              "Reservoir": 0.6, "Retention": 0.72}
        assert got.title == "Tofte North"

    def test_an_esl_prospect_is_flagged_rather_than_reconstructed(self):
        """E-POS's headline ESL number is a mass rollup with a stance applied at the top. We do not
        recompute it -- that logic would drift from the original -- so we say so instead."""
        got = epos.read(EPOS_CSV_WITH_ESL)
        assert got.warnings and "ESL" in got.warnings[0]

    def test_an_empty_esl_block_is_not_flagged(self):
        """Every E-POS save writes the row, empty or not. Warning on an empty one would train the
        user to ignore the warning."""
        assert epos.read(EPOS_CSV).warnings == ()

    def test_a_file_without_the_row_is_refused_not_defaulted(self):
        """A silent default would be indistinguishable from a real elicitation downstream."""
        with pytest.raises(ValueError, match="Classic POS"):
            epos.read("some,other,csv\n1,2,3\n")

    def test_the_json_form_round_trips(self):
        values = {"Charge": 0.9, "Closure": 1.0, "Reservoir": 0.6, "Retention": 0.8}
        assert epos.read(epos.to_json(values, "X")).values == pytest.approx(values)

    def test_the_form_is_chosen_by_content_not_by_extension(self):
        """A JSON body saved as .csv, or the reverse, is the case that actually happens."""
        assert epos.read('  {"Charge":0.9,"Closure":1,"Reservoir":0.6,"Retention":0.8}').values
        assert epos.read(EPOS_CSV).values

    def test_json_keys_are_case_insensitive_but_never_abbreviated(self):
        assert epos.read('{"charge":0.9,"CLOSURE":1,"Reservoir":0.6,"retention":0.8}').values
        with pytest.raises(ValueError, match="Retention"):
            epos.read('{"charge":0.9,"closure":1,"reservoir":0.6,"ret":0.8}')

    def test_a_chance_outside_zero_to_one_is_refused(self):
        with pytest.raises(ValueError, match="probability"):
            epos.read('{"Charge":1.4,"Closure":1,"Reservoir":0.6,"Retention":0.8}')


# --------------------------------------------------------------------------- WellVolPOS out
class TestTrialTable:
    def test_it_carries_one_row_per_successful_realisation(self, result, table):
        frame = wvp.trial_table(result, table)
        assert len(frame) == int(result.above_minimum.sum())
        assert len(frame) < result.n            # the fixture has a real minimum, so some fail

    def test_failures_are_excluded_by_default(self, result, table):
        """A failed realisation has no contact in any useful sense. Handing them to a volumetrics
        tool as contacts would misstate the distribution it fits."""
        frame = wvp.trial_table(result, table)
        assert frame["contact"].min() >= result.contact_m[result.above_minimum].min() - 1e-9
        assert len(wvp.trial_table(result, table, successes_only=False)) == result.n

    def test_the_contact_is_always_below_the_crest(self, result, table):
        frame = wvp.trial_table(result, table)
        assert (frame["contact"] >= frame["crest"]).all()

    def test_the_contact_never_passes_the_spill_point(self, result, table):
        """The closure/spill limit is always active, so no contact may sit below it."""
        frame = wvp.trial_table(result, table)
        assert "spill" in frame
        assert (frame["contact"] <= frame["spill"] + 1e-9).all()

    def test_geometry_outside_the_mapped_table_is_nan_not_clamped(self, result, table):
        """A clamped area would quietly assert the structure keeps going below what was mapped."""
        frame = wvp.trial_table(result, table)
        deep = frame["contact"] > table.deepest_m
        if deep.any():
            assert frame.loc[deep, "area"].isna().all()

    def test_resource_is_absent_and_named_as_the_gap(self, result, table):
        """The whole design decision. Inventing this column to satisfy the importer would make
        every downstream number a computation on fiction, with nothing looking broken."""
        assert "resource" not in wvp.trial_table(result, table).columns
        assert "resource" in wvp.missing_for_wellvolpos()

    def test_an_impossible_minimum_refuses_with_a_reason(self):
        empty = engine.run(dataclasses.replace(reference_prospect(), min_column_m=10_000.0), 500)
        with pytest.raises(ValueError, match="nothing to export"):
            wvp.trial_table(empty)


class TestElementCurveTable:
    def test_it_has_a_column_per_element_present_plus_the_direct_curve(self, result):
        pos = {Group.CHARGE: 0.9, Group.CLOSURE: 1.0,
               Group.RESERVOIR: 0.6, Group.RETENTION: 0.8}
        frame = wvp.element_curve_table(decompose.decompose(result), pos)
        assert "depth_m" in frame and "direct" in frame
        assert {"charge", "closure", "retention"} <= set(frame.columns)

    def test_every_curve_falls_with_depth(self, result):
        pos = {g: 0.8 for g in Group}
        frame = wvp.element_curve_table(decompose.decompose(result), pos)
        for name in frame.columns.drop("depth_m"):
            assert (np.diff(frame[name].to_numpy()) <= 1e-9).all(), name

    def test_no_element_curve_exceeds_its_own_pos(self, result):
        pos = {Group.CHARGE: 0.9, Group.CLOSURE: 1.0,
               Group.RESERVOIR: 0.6, Group.RETENTION: 0.8}
        frame = wvp.element_curve_table(decompose.decompose(result), pos)
        for group, value in pos.items():
            if group.value.lower() in frame:
                assert frame[group.value.lower()].max() <= value + 1e-9


# --------------------------------------------------------------------------- the real consumer
@pytest.mark.skipif(not WELLVOLPOS.exists(),
                    reason="the WellVolPOS checkout is not on this machine")
def test_wellvolpos_maps_every_column_we_export(result, table):
    """Ask the consumer, rather than trusting my reading of it.

    WellVolPOS's generic adapter recognises columns by regex against the header and refuses a file
    whose required fields it cannot identify. This asserts two things at once: every column we
    write is understood with **no configuration at the far end**, and the only thing it complains
    about is the one field we deliberately do not fabricate.
    """
    sys.path.insert(0, str(WELLVOLPOS))
    from wellvolpos.io.adapters import generic
    from wellvolpos.io.adapters.source import Source

    csv_text = wvp.trial_table(result, table).to_csv(index=False)
    proposal = generic.propose(Source(name="hcwc_trials.csv", data=csv_text.encode("utf-8")))

    assert set(proposal.mapping) == {"trial", "contact", "crest", "spill", "area", "hc_grv"}
    assert all(canon == col for canon, col in proposal.mapping.items())
    assert proposal.missing_required == ["resource"]
