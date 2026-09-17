"""Saving and reloading a prospect.

The property that matters is not "the file parses" but **the reloaded prospect is the same
prospect**. Everything here is arranged around that: a round trip through JSON has to bring back
every input, in the same *type*, including the tuples that range sliders hold — Streamlit rejects a
list where it expects a tuple, so a lossy round trip shows up as a calculator that will not reopen
rather than as a wrong number.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from hcwc.io import prospect


def _state() -> dict:
    """A session state with one of everything the document is meant to carry."""
    return {
        "prospect_name": "Tofte North",
        "apex_p1": 2049.0, "apex_p99": 2051.0,
        "spill_input": 2400.0, "burial_input": 2050.0,
        "dhi_toggle": True, "min_column_input": 40.0,
        # The DHI observation itself, which used to live in unkeyed widgets and be lost on reload.
        "dhi_in_seen": "Seen", "dhi_in_shape": "normal", "dhi_in_contact": 2205.0,
        "dhi_in_sigma": 30.0, "dhi_in_strength": 25.0, "dhi_in_pvalid_manual": False,
        "n_trials_input": 20000, "seed_input": 7,
        "play_Charge": 1.0, "cond_Charge": 0.9,
        "lim_Charge_on": True, "lim_Charge_pa": 1.0, "lim_Charge_kind": "column",
        "lim_Charge_form": "pert", "lim_Charge_pert_minimum": 100.0,
        # The token the radio stores, not the label it shows. This fixture said
        # "From charge volume" -- a value the widget never writes, because its options are the
        # tokens and `format_func` supplies the labels. The enumeration check now refuses it,
        # which is the point: that is exactly the shape of file that crashed the app.
        "lim_Charge_src": "charge",
        # A range slider inside the seal calculator — a tuple, and it has to stay one.
        "lim_Top seal (capillary)_t": (56.0, 87.0),
        "lim_Top seal (capillary)_rs": (0.03, 0.20),
        # Noise that must not be saved.
        "limit_set": object(), "dhi_overlay": {"pos_curve": [1, 2, 3]},
        "_pending_load": {"x": 1}, "FormSubmitter:x": True,
    }


class TestRoundTrip:
    def test_every_input_comes_back(self):
        restored = prospect.read(prospect.to_json(_state()))
        for key in ("prospect_name", "apex_p1", "spill_input", "dhi_toggle",
                    "n_trials_input", "play_Charge", "lim_Charge_pa", "lim_Charge_src"):
            assert key in restored, key
        assert restored["prospect_name"] == "Tofte North"
        assert restored["n_trials_input"] == 20000

    def test_range_slider_tuples_survive_as_tuples(self):
        """The one that bites. JSON has no tuple, so a naive round trip returns a list — and
        Streamlit refuses a list where a range slider expects a tuple, so the seal calculator
        would raise on reopen rather than come back wrong."""
        restored = prospect.read(prospect.to_json(_state()))
        value = restored["lim_Top seal (capillary)_t"]
        assert isinstance(value, tuple)
        assert value == (56.0, 87.0)

    def test_derived_state_is_not_saved(self):
        """The file carries **inputs**. A saved `limit_set` or `dhi_overlay` would be a second
        place for the same fact to live, and the two would drift the moment the model changed."""
        doc = json.loads(prospect.to_json(_state()))
        for key in ("limit_set", "dhi_overlay", "_pending_load", "FormSubmitter:x"):
            assert key not in doc["inputs"], key

    def test_the_resolved_model_is_recorded_but_not_reloaded(self):
        """It goes in for provenance — so the file is readable without the app — and is ignored on
        load, because replaying the inputs is what makes a reopened file give the current tool's
        answer rather than a frozen one."""
        from hcwc.core.limits import reference_prospect
        doc = json.loads(prospect.to_json(_state(), limit_set=reference_prospect()))
        assert "resolved" in doc and doc["resolved"]["limits"]
        assert "resolved" not in prospect.read(json.dumps(doc))

    def test_a_second_round_trip_is_identical(self):
        once = prospect.to_json(_state())
        twice = prospect.to_json(prospect.read(once))
        assert json.loads(once)["inputs"] == json.loads(twice)["inputs"]


class TestRefusals:
    def test_a_newer_format_is_refused_rather_than_guessed_at(self):
        doc = json.loads(prospect.to_json(_state()))
        doc["format"] = prospect.FORMAT_VERSION + 1
        with pytest.raises(ValueError, match="newer version"):
            prospect.read(json.dumps(doc))

    def test_an_unrecognised_key_is_refused_and_named(self):
        """Half-applying a file is worse than refusing it: it looks like it worked."""
        doc = json.loads(prospect.to_json(_state()))
        doc["inputs"]["something_from_the_future"] = 1
        with pytest.raises(ValueError, match="something_from_the_future"):
            prospect.read(json.dumps(doc))

    def test_a_file_that_is_not_a_prospect_is_refused(self):
        with pytest.raises(ValueError, match="does not look like"):
            prospect.read('{"hello": "world"}')

    def test_broken_json_says_so(self):
        with pytest.raises(ValueError, match="not a valid JSON"):
            prospect.read("{not json")


def test_the_allow_list_covers_every_widget_key_the_app_creates():
    """The keys **are** the schema, so an input the app creates and the document does not know
    about is silently lost on save — the failure mode being a reloaded prospect that is subtly not
    the one you saved. This scans the UI for literal `key=` values and checks each is claimed.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "hcwc" / "ui"
    literal = set()
    for path in root.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        # Parsed, not grepped: `data-key="N"` inside a CSS docstring is not a widget, and a scan
        # that cannot tell the difference fails on prose.
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg == "key" and isinstance(kw.value, ast.Constant)                         and isinstance(kw.value.value, str):
                    literal.add(kw.value.value)

    # Keys that are deliberately *not* saved: transient UI state and display-only choices already
    # named in EXACT are fine, but these are per-run scratch.
    transient = {"prospect_upload", "epos_upload", "corr_editor", "limiter_corr_editor",
                 "stack_every", "stack_window_depth", "stack_window_column",
                 "concept_section", "area_depth_charge", "family_burial", "family_scale",
                 # Which axis the tornado measures its swing on. A reading choice, not an
                 # input to the model.
                 # Display choices, now suffixed by tab because the results renderer draws
                 # on both 4.0 and 5.0 and the two keep separate state.
                 "tornado_space", "dhi_tornado_space", "tornado_space_4", "tornado_space_5",
                 "restrict_successes_4", "restrict_successes_5",
                 "combo_all_4", "combo_all_5",
                 # Which contact distributions to draw behind the chance curves. A way of
                 # looking at the answer, not a part of it.
                 "hcwc_hist_5", "competition_window_4", "competition_window_5",
                 "map_quantity_5", "map_depth_5",
                 # Whether tab 6.0 draws the built distributions beside the empirical one. The same
                 # kind of choice: it changes what is on the figure, not what the model says.
                 "empirical_show_models",
                 # The benchmark fusion on tab 6.0 is drawn and never consumed: no limit, no
                 # engine run and no export reads it, so the weight is a way of looking at
                 # the answer rather than part of it. The seal shrinkage on tab 3.0 is the
                 # opposite — it moves a limit, so it is saved with that limit block.
                 "fuse_benchmark", "fuse_source",
                 # A one-shot action, not state: saving "the user pressed a button once" would
                 # reload the example every time the file was opened.
                 "load_example", "load_example_0", "load_example_1",
                 "tab1_example_0", "tab1_example_1",
                 # A display choice on the export, and one that must NOT persist: a saved
                 # geological prospect reopened with a stale "given the DHI" selection would
                 # export the wrong distribution, which is the defect B exists to prevent.
                 "export_basis",
                 # An imported benchmark dataset does NOT travel with a saved prospect, and this
                 # is a privacy decision rather than an oversight. The file may be a company's
                 # confidential field list; a prospect saved by one person and sent to another
                 # must not carry it, and a name or a source string is enough to identify the
                 # dataset without embedding it. Reload it beside the prospect instead.
                 "import_name", "import_source", "import_upload", "forget_import",
                 # The area-depth grid's own machinery. What is saved is the *table* -- three flat
                 # lists written by `_area_depth_inputs` -- not the editor's edit-diff, the reset
                 # button or the uploader, none of which describe the prospect.
                 "charge_ad_editor", "charge_ad_reset", "charge_ad_upload"}
    missed = {k for k in literal
              if k not in prospect.EXACT and not k.startswith(prospect.PREFIXES)
              and k not in transient and not k.startswith(("r1_", "sub_el_", "z_entry_"))}
    assert not missed, f"widget keys nothing saves and nothing excuses: {sorted(missed)}"


class TestTheValueCheckCoversEveryKindOfWidget:
    """The numeric half of this was written carefully; the enumerated half had no check at all.

    Streamlit does not complain about a stored value that is not among a selector's options — it
    silently falls back to the first one. So an unchecked enumeration is worse than a crash: the
    prospect loads, looks right, and is not the one that was saved.
    """

    @staticmethod
    def _read(key, value):
        return prospect.read(json.dumps({"format": 1, "inputs": {key: value}}))

    @pytest.mark.parametrize("value", ["garbage", "From the NCS data", "EMPIRICAL", ""])
    def test_a_source_that_is_not_one_of_the_options_is_refused(self, value):
        """`From the NCS data` is the *label*; the radio stores the token behind it. A file
        carrying labels reached a dict lookup and crashed with a bare `KeyError`."""
        with pytest.raises(ValueError, match="not one of"):
            self._read("lim_Charge_src", value)

    def test_the_tokens_the_radio_actually_stores_are_accepted(self):
        for token in ("Typed", "charge", "seal", "seal_as_top", "empirical"):
            assert self._read("lim_Charge_src", token)["lim_Charge_src"] == token

    @pytest.mark.parametrize("key,value", [("lim_Charge_form", "nonsense"),
                                           ("lim_Charge_kind", "sideways"),
                                           ("stack_mode_4", "Hologram"),
                                           ("stack_space_5", "sideways"),
                                           ("dhi_in_shape", "triangular")])
    def test_every_other_enumeration_is_checked_too(self, key, value):
        with pytest.raises(ValueError, match="not one of"):
            self._read(key, value)

    @pytest.mark.parametrize("key", ["lim_Charge_on", "lim_Top seal (capillary)_net",
                                     "dhi_toggle"])
    def test_a_switch_must_be_a_switch(self, key):
        """A toggle handed `"yes please"` is not an error Streamlit reports; it is simply truthy."""
        with pytest.raises(ValueError, match="must be true or false"):
            self._read(key, "yes please")

    def test_the_declared_bounds_are_the_bounds_the_widget_will_take(self):
        """`min_column_input` declared 0–10 000 while its widget accepts 0–2 000. A file at 5 000
        passed the check and then landed on **0.0** — not clamped, not the default — which makes
        the minimum-column test vacuous and changes the question being answered."""
        import re

        # Both files: the run settings live on tab 2.0, the area–depth thickness on tab 3.0, and a
        # declared bound has to match its widget wherever that widget happens to be written.
        root = pathlib.Path(__file__).resolve().parent.parent / "hcwc" / "ui"
        source = "\n".join((root / name).read_text(encoding="utf-8")
                           for name in ("prospect_tab.py", "sources.py"))
        for key, (low, high) in prospect.NUMERIC_BOUNDS.items():
            found = re.search(
                r'number_input\(\s*\n?\s*"[^"]*",\s*([0-9_.*\- ]+?),\s*([0-9_.*\- ]+?),'
                r'[^)]*key="%s"' % re.escape(key), source, re.S)
            assert found, (
                f"no widget found for {key}. The scan reads literals, so a widget whose key is a "
                f"named constant will not be seen -- write the string and pin the constant to it.")
            assert (eval(found.group(1)), eval(found.group(2))) == (low, high), \
                f"{key}: the file may carry {low}–{high} but the widget takes another range"


class TestTheAreaDepthTableTravelsWithTheProspect:
    def test_the_thickness_constant_matches_the_literal_the_widget_uses(self):
        """The widget writes the key as a literal so the bounds scan can find it; this is what
        stops the constant the rest of the module reads from drifting away from it."""
        from hcwc.ui import sources

        assert sources.AREA_DEPTH_THICKNESS == "charge_ad_thickness"

    def test_the_methods_agree_between_the_ui_and_the_reader(self):
        from hcwc.ui import sources

        assert set(prospect.AREA_DEPTH_METHODS) == {sources.SURFACES, sources.THICKNESS}


class TestTheDhiObservationIsPartOfTheDocument:
    def test_the_dhi_inputs_round_trip(self):
        """Every DHI widget was unkeyed, so `document` could not see any of them and a saved
        prospect carried `dhi_toggle` alone."""
        restored = prospect.read(prospect.to_json(_state()))
        for key in ("dhi_in_seen", "dhi_in_shape", "dhi_in_contact", "dhi_in_strength"):
            assert key in restored, key
        assert restored["dhi_in_strength"] == 25.0

    def test_the_derived_dhi_state_is_not_saved(self):
        """`dhi_in_` rather than a bare `dhi_` prefix, so the tab's *outputs* stay out. Saving one
        would let a stale posterior be restored over a fresh computation."""
        saved = prospect.document({"dhi_in_strength": 7.0, "dhi_r_strength": 1.4,
                                   "dhi_on": True, "dhi_posterior": 0.5})["inputs"]
        assert "dhi_in_strength" in saved
        assert not [k for k in saved if k.startswith("dhi_") and not k.startswith("dhi_in_")]


class TestTheAllowListMatchesTheApp:
    def test_no_exact_entry_is_dead(self):
        """`stack_space` and `stack_mode` sat here without the tab number the real keys carry, so
        they matched nothing: the settings were never saved and the entries were decoration."""
        from hcwc.ui import limit_stack
        assert set(prospect.STACK_MODES) == set(limit_stack.MODES)

    def test_the_version_field_refuses_with_the_right_reason(self):
        """A string version used to be reported as "format 1, this reads 1" — a refusal whose
        reason reads as a contradiction, sending the reader to update a current app."""
        with pytest.raises(ValueError, match="not a version number"):
            prospect.read('{"format": "1", "inputs": {}}')
        with pytest.raises(ValueError, match="newer version"):
            prospect.read('{"format": 99, "inputs": {}}')


class TestTheBasisEnumerationMatchesTheThemes:
    """`hcwc.io` must not import Streamlit, so the four basis strings are duplicated. This is the
    test that stops the copies drifting -- a saved file whose basis is not in the enumeration is
    silently reset to the first option, and the reader is told nothing."""

    def test_every_basis_the_ui_can_produce_is_accepted(self):
        from hcwc.io import prospect
        from hcwc.ui import theme

        assert theme.GEOLOGICAL in prospect.BASIS_VALUES
        assert theme.GIVEN_DHI in prospect.BASIS_VALUES
        # The two combined forms `evidence_basis` builds, spelled out rather than derived, because
        # deriving them here would test the copy against itself.
        assert "given the well" in prospect.BASIS_VALUES
        assert "given the DHI + well" in prospect.BASIS_VALUES

    def test_the_calibration_basis_survives_a_reload(self):
        import json

        from hcwc.io import prospect

        saved = prospect.document({"calibration_basis": "given the DHI"})
        assert prospect.read(json.dumps(saved))["calibration_basis"] == "given the DHI"


class TestTheShippedExamplesLoad:
    """Two files under `reference/` that the buttons on tabs 1 and 2 read.

    The first one could not be opened at all between the stack views becoming per-tab and 15 Sep
    2026: it carried the two dead keys and the reader refused it. Nothing tested the file, so the
    button on tab 2 raised for anyone who pressed it. Both files are read here, and the reader
    drops the dead keys rather than refusing a file that carries them.
    """
    import pathlib

    ROOT = pathlib.Path(__file__).resolve().parent.parent
    FILES = ("example_prospect.hcwc.json", "example_prospect_spill.hcwc.json")

    @pytest.mark.parametrize("name", FILES)
    def test_it_reads(self, name):
        text = (self.ROOT / "reference" / name).read_text(encoding="utf-8")
        inputs = prospect.read(text)
        assert inputs["prospect_name"]
        assert "stack_mode" not in inputs and "stack_space" not in inputs

    def test_the_dead_keys_are_dropped_not_refused(self):
        import json
        text = (self.ROOT / "reference" / self.FILES[0]).read_text(encoding="utf-8")
        doc = json.loads(text)
        doc["inputs"]["stack_mode"] = "Exceedance curves"
        doc["inputs"]["stack_space"] = "depth"
        inputs = prospect.read(json.dumps(doc))
        assert "stack_mode" not in inputs

    @pytest.mark.render
    def test_the_two_examples_are_controlled_by_different_mechanisms(self):
        """The reason there are two: seal-dominated against spill-dominated."""
        from streamlit.testing.v1 import AppTest
        from hcwc.core import engine

        winners = {}
        for name in self.FILES:
            at = AppTest.from_file(str(self.ROOT / "app.py"), default_timeout=900)
            at.session_state["_pending_load"] = prospect.read(
                (self.ROOT / "reference" / name).read_text(encoding="utf-8"))
            at.run()
            assert not at.exception, name
            ls = at.session_state["limit_set"]
            r = engine.run(ls, n=4_000, seed=1)
            shares = {n: float((r.controller == j).mean()) for j, n in enumerate(ls.names)}
            winners[name] = max(shares, key=shares.get)
            if "spill" in name:
                assert shares["Closure / spill point"] > 0.5, shares
        assert "spill" in winners[self.FILES[1]].lower()
        assert "seal" in winners[self.FILES[0]].lower()
