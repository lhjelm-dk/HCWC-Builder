"""`hcwc.core.defaults`: the scientific defaults in one place, and the modules read them.

Phase 4 of the clean-up (18 Sep 2026). The values are the ones the tabs and the core carried
before; these tests pin them and the wiring, so a default cannot drift in one place only.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.core import defaults, dhi, pos
from hcwc.core.limits import Group


def test_the_shipped_element_chances_give_the_shipped_p_g():
    element_pos = {Group(name): play * cond for name, (play, cond) in defaults.ELEMENT_CHANCES.items()}
    assert pos.accumulation_chance(element_pos) == pytest.approx(0.4082, abs=5e-5)


def test_the_strength_model_reads_the_reference_distributions():
    model = dhi.StrengthModel()
    assert (model.hc.p1, model.hc.p99) == defaults.EVIDENCE_INDEX_HC_P1_P99 == (-50.0, 100.0)
    assert (model.no_hc.p1, model.no_hc.p99) == defaults.EVIDENCE_INDEX_NOHC_P1_P99 == (-100.0, 50.0)
    assert model.r_at(0.0) == pytest.approx(1.0), "the two reference distributions cross at 0"


def test_the_detection_function_reads_its_defaults():
    d = dhi.DetectionFunction()
    assert (d.h50_m, d.steepness_m, d.ceiling, d.false_positive) == (
        defaults.DETECTION_H50_M, defaults.DETECTION_WIDTH_M, defaults.DETECTION_CEILING,
        defaults.DETECTION_FALSE_POSITIVE) == (25.0, 8.0, 0.9, 0.5)


def test_the_three_routes_to_c_agree_on_an_untouched_tab():
    scores = [defaults.CONTACT_ATTRIBUTES[a][lv] for a, lv in defaults.DEFAULT_ATTRIBUTE_LEVELS.items()]
    geometric = float(np.prod(scores) ** (1.0 / len(scores)))
    assert geometric == pytest.approx(defaults.DEFAULT_CONTACT_GIVEN_HC, abs=0.005)
    assert dhi.contact_weight_from_score(defaults.DEFAULT_DHI_SCORE) == pytest.approx(
        defaults.DEFAULT_CONTACT_GIVEN_HC)


def test_the_tab_constants_are_the_defaults():
    from hcwc.ui import dhi_tab, prospect_tab
    assert dhi_tab.OPENING_STRENGTH == defaults.OPENING_EVIDENCE_INDEX == 5.0
    assert dhi_tab.DEFAULT_CONTACT_GIVEN_HC == defaults.DEFAULT_CONTACT_GIVEN_HC
    assert dhi_tab.CONTACT_ATTRIBUTES is defaults.CONTACT_ATTRIBUTES
    assert prospect_tab.DEFAULT_RISK[Group.CHARGE] == defaults.ELEMENT_CHANCES["Charge"]


def test_every_register_entry_names_its_unit_meaning_and_range():
    for entry in defaults.REGISTER:
        assert entry.unit and entry.meaning and entry.provenance and entry.allowed, entry.name
