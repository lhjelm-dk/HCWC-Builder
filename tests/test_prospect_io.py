"""Saving and reloading a prospect.

The property that matters is not "the file parses" but **the reloaded prospect is the same
prospect**. Everything here is arranged around that: a round trip through JSON has to bring back
every input, in the same *type*, including the tuples that range sliders hold — Streamlit rejects a
list where it expects a tuple, so a lossy round trip shows up as a calculator that will not reopen
rather than as a wrong number.
"""
from __future__ import annotations

import json

import pytest

from hcwc.io import prospect


def _state() -> dict:
    """A session state with one of everything the document is meant to carry."""
    return {
        "prospect_name": "Tofte North",
        "apex_p1": 2049.0, "apex_p99": 2051.0,
        "spill_input": 2400.0, "burial_input": 2050.0,
        "dhi_toggle": True, "min_column_input": 40.0,
        "n_trials_input": 20000, "seed_input": 7,
        "play_Charge": 1.0, "cond_Charge": 0.9,
        "lim_Charge_on": True, "lim_Charge_pa": 1.0, "lim_Charge_kind": "column",
        "lim_Charge_form": "pert", "lim_Charge_pert_minimum": 100.0,
        "lim_Charge_src": "From charge volume",
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
                 # on both ④ and ⑤ and the two keep separate state.
                 "tornado_space", "dhi_tornado_space", "tornado_space_4", "tornado_space_5",
                 "restrict_successes_4", "restrict_successes_5",
                 "combo_all_4", "combo_all_5",
                 # Which contact distributions to draw behind the chance curves. A way of
                 # looking at the answer, not a part of it.
                 "hcwc_hist_5", "contact_hist_4", "contact_hist_5",
                 # A one-shot action, not state: saving "the user pressed a button once" would
                 # reload the example every time the file was opened.
                 "load_example",
                 # A display choice on the export, and one that must NOT persist: a saved
                 # geological prospect reopened with a stale "given the DHI" selection would
                 # export the wrong distribution, which is the defect B exists to prevent.
                 "export_basis",
                 # An imported benchmark dataset does NOT travel with a saved prospect, and this
                 # is a privacy decision rather than an oversight. The file may be a company's
                 # confidential field list; a prospect saved by one person and sent to another
                 # must not carry it, and a name or a source string is enough to identify the
                 # dataset without embedding it. Reload it beside the prospect instead.
                 "import_name", "import_source", "import_upload", "forget_import"}
    missed = {k for k in literal
              if k not in prospect.EXACT and not k.startswith(prospect.PREFIXES)
              and k not in transient and not k.startswith(("r1_", "sub_el_", "z_entry_"))}
    assert not missed, f"widget keys nothing saves and nothing excuses: {sorted(missed)}"
