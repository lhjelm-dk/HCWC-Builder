"""Every UI module must at least import, and every tab must be numbered exactly once.

This file exists because a syntax error in a Streamlit module is invisible to the rest of the
suite — nothing imports the UI, so a mangled string literal survives a green run and only shows up
as a red page in the browser. That happened twice while these tabs were being written. The check is
trivial; the gap it closes is not.

The numbering assertions are here for the same reason: the tab constants, the theme's colour map
and `app.py`'s tab strip have to agree, and a mismatch shows up as figures labelled for the wrong
tab rather than as an error.
"""
from __future__ import annotations

import ast
import importlib
import pathlib
import re

import pytest

UI = pathlib.Path(__file__).resolve().parent.parent / "hcwc" / "ui"
MODULES = sorted(p.stem for p in UI.glob("*.py") if p.stem != "__init__")
TAB_MODULES = ["prospect_tab", "limiters_tab", "results_tab", "depth_risk_tab", "dhi_tab",
               "empirical"]


@pytest.mark.parametrize("name", MODULES)
def test_the_module_imports(name):
    importlib.import_module(f"hcwc.ui.{name}")


def test_app_py_parses():
    """`app.py` is never imported by anything, so it is the most exposed file in the repo."""
    root = pathlib.Path(__file__).resolve().parent.parent
    ast.parse((root / "app.py").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", TAB_MODULES)
def test_the_tab_number_is_one_the_theme_knows_about(name):
    from hcwc.ui import theme
    module = importlib.import_module(f"hcwc.ui.{name}")
    assert module.TAB in theme.TAB_COLOURS


#: Modules that deliberately share a top-level tab, as sub-tabs of it. The contact distribution and
#: its per-element decomposition against depth are two readings of one run, and the DHI pair is the
#: same merge — so `results_tab` and `depth_risk_tab` are both tab ④, `dhi_tab` and
#: `depth_risk_tab.TAB_DHI` are both tab ⑤. Listed rather than inferred, so an *accidental*
#: collision between any other pair still fails.
SHARED_TABS = {frozenset({"results_tab", "depth_risk_tab"}),
               frozenset({"dhi_tab", "depth_risk_tab"})}


def test_no_two_tabs_claim_the_same_number_by_accident():
    numbers: dict[int, str] = {}
    for name in TAB_MODULES:
        module = importlib.import_module(f"hcwc.ui.{name}")
        clash = numbers.get(module.TAB)
        if clash is not None:
            assert frozenset({name, clash}) in SHARED_TABS, (
                f"{name} and {clash} both claim tab {module.TAB} and are not a declared sub-tab "
                f"pair — figures on that tab would be numbered twice and collide as element keys")
        numbers[module.TAB] = name


def test_no_two_sub_tabs_can_produce_the_same_figure_number():
    """Sub-tabs of one tab must not both start at `Figure 4.1`.

    Two `Figure 4.1`s on one tab means broken cross-references and a Streamlit duplicate element
    key — a red page rather than a wrong caption. **There are two valid ways to avoid it**, and the
    app now uses both:

    Both tabs with sub-tabs stamp each one with its own ``sub=``, so a label carries the page it is
    on: `Figure 5.2.1` is the first exhibit on *What you saw*, and `Figure 4.1.6` and `Figure 5.3.6`
    are the same figure on the two bases. A flat sequence gave the reader `Figure 5.9` with no way
    to know which of four pages to turn to, and matching tab ④ to it means someone comparing the two
    bases reads one numbering scheme rather than two.

    The assertion is the invariant — every sub-tab stamped, none able to collide — rather than any
    particular wiring, because sharing one sequence across sub-tabs would also be valid and was what
    both tabs used to do.
    """
    root = pathlib.Path(__file__).resolve().parent.parent
    source = (root / "app.py").read_text(encoding="utf-8")

    for tab, count in ((4, 2), (5, 4)):
        subs = re.findall(rf"Numbering\({tab},\s*sub=(\d)\)", source)
        assert sorted(subs) == [str(i) for i in range(1, count + 1)], (
            f"tab {tab} should hand each of its {count} sub-tabs its own Numbering, got sub={subs}")
    assert "Numbering(4)\n" not in source and "Numbering(5)\n" not in source, (
        "a bare Numbering on a tab with sub-tabs means two of them start at Figure n.1")


def test_app_py_opens_one_tab_per_theme_entry():
    """The tab strip is built from `theme.tab_labels()`, so a mismatch between the labels and the
    `st.tabs(...)` unpacking is a runtime ValueError on the Purpose tab and nowhere else.

    Identified by its *argument* rather than by being the only one: tabs ④ and ⑤ open sub-strips
    with `st.tabs([...])` of their own, and counting those as candidates would make this assert on
    whichever happened to come first.
    """
    from hcwc.ui import theme
    root = pathlib.Path(__file__).resolve().parent.parent
    tree = ast.parse((root / "app.py").read_text(encoding="utf-8"))
    unpacked = [node for node in ast.walk(tree)
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple)
                and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "attr", "") == "tabs"
                and any(getattr(getattr(a, "func", None), "attr", "") == "tab_labels"
                        for a in node.value.args)]
    assert len(unpacked) == 1, "expected exactly one st.tabs(theme.tab_labels()) in app.py"
    assert len(unpacked[0].targets[0].elts) == len(theme.tab_labels())


class TestLikelihoodRatioFormatting:
    """`dhi_tab._fmt_r`, and the reason it exists.

    Wiring the strength slider up surfaced a real problem: the geometry channel is **not** clipped,
    and on a sharp pick against a low assessment minimum it returns values in the millions. Printed
    as `15460945.21` that reads as a measurement. It is not one — it is a ratio that has left the
    range anyone should quote, and the scientific form says so at a glance.
    """

    def test_ordinary_ratios_read_as_ordinary_numbers(self):
        from hcwc.ui.dhi_tab import _fmt_r
        assert _fmt_r(1.40) == "1.40"
        assert _fmt_r(0.5) == "0.50"
        assert _fmt_r(50.0) == "50.00"

    def test_an_implausible_ratio_is_shown_in_scientific_form(self):
        from hcwc.ui.dhi_tab import _fmt_r
        assert _fmt_r(15_460_945.21) == "1.5e+07"
        assert _fmt_r(1e-6) == "1.0e-06"

    def test_an_undefined_ratio_is_a_dash_not_nan(self):
        from hcwc.ui.dhi_tab import _fmt_r
        assert _fmt_r(float("nan")) == "—"


class TestTheDefaultStrengthIsDefensible:
    """E-POS's slider default is 7, and the tool ships with it. This says what that *means*.

    A default that quietly asserted strong evidence would be indefensible in a tool whose whole
    argument is about not over-stating what seismic tells you. Seven sits just above the crossing
    point of the two default curves, so an assessor who moves nothing has stated a *barely*
    supportive DHI — which is the right thing for a default to say.
    """

    def test_the_default_gives_a_modest_ratio(self):
        from hcwc.core import dhi
        r = dhi.StrengthModel().r_at(dhi.DEFAULT_STRENGTH)
        assert 1.0 < r < 1.5
        assert dhi.strength_bands(r)[0] == "Negligible"

    def test_a_negligible_band_still_moves_a_mid_prior_several_points(self):
        """Both things are true at once, and the gap between them is what trips people up.

        R = 1.40 is genuinely weak *evidence* — Simm's band for it is "Negligible". But weak
        evidence still moves a mid prior a visible amount, because the prior is mid: 30 % becomes
        **37.5 %**, a 7.5-point move, from a slider nobody touched.

        So the band label alone is not a safe thing to read. That is exactly why the tab shows
        "POS on strength alone" against the prior beside the band, rather than the band by itself.
        """
        from hcwc.core import dhi
        r = dhi.StrengthModel().r_at(dhi.DEFAULT_STRENGTH)
        assert dhi.strength_bands(r)[0] == "Negligible"
        assert dhi.simm_update(0.30, r) == pytest.approx(0.375, abs=0.005)

    def test_the_cap_is_what_a_huge_geometry_channel_hits(self):
        """The condition the UI warns on: when one channel is astronomical the combination is the
        guard, not the evidence, and the reader has to be told which they are looking at."""
        from hcwc.core import dhi
        combined = dhi.CombinedUpdate(prior_pos=0.3, r_geometry=1.5e7, r_strength=1.40)
        assert combined.r_combined == dhi.R_CAP


class TestBurialDepthDrivesSealTemperature:
    """Tab ② → tab ③: one number, so the two cannot disagree about the same rock.

    Before this, burial depth and seal temperature were typed independently, which meant a 4 000 m
    prospect could be assessed with a 70 °C seal and nothing would object. Interfacial tension falls
    with temperature, so deeper is a weaker seal — the coupling is physical, not cosmetic.
    """

    def test_it_returns_a_range_because_the_gradient_is_the_uncertain_part(self):
        from hcwc.ui.prospect_tab import GRADIENT_C_PER_KM, temperature_range
        lo, hi = temperature_range(2000.0)
        assert lo < hi
        assert hi - lo == pytest.approx((GRADIENT_C_PER_KM[1] - GRADIENT_C_PER_KM[0]) * 2.0)

    def test_deeper_is_hotter(self):
        from hcwc.ui.prospect_tab import temperature_range
        shallow, deep = temperature_range(1500.0), temperature_range(3500.0)
        assert deep[0] > shallow[0] and deep[1] > shallow[1]

    def test_the_default_can_reach_the_reference_temperature(self):
        """The reference prospect sits at ~2 050 m, where 70-90 °C is ordinary on the NCS — which
        implies roughly 32-41 °C/km, a hot basin rather than a textbook 30.

        The derived range has to be able to *contain* that, or the default would quietly contradict
        the data the tool is calibrated against. It reaches 87 °C, so it covers the 70 and most of
        the 90; a basin hotter still is a case for overriding the slider, which is why the slider
        is there.
        """
        from hcwc.ui.prospect_tab import temperature_range
        lo, hi = temperature_range(2050.0)
        assert lo < 70.0 < hi
        assert hi > 85.0

    def test_the_surface_intercept_is_not_zero(self):
        """A gradient through the origin would give 5 °C at 0 m, which is a seabed, not a surface."""
        from hcwc.ui.prospect_tab import SURFACE_C, temperature_range
        assert temperature_range(0.0) == (SURFACE_C, SURFACE_C)

    def test_a_deep_oil_prospect_reaches_where_the_correlation_breaks_down(self):
        """Not a bug to fix — a physical limit the default now surfaces.

        Aplin & Yang's oil interfacial-tension fit goes non-positive near 132 °C. At 3 500 m the
        derived range already reaches 128 °C, so a deep oil prospect will hit the refusal in
        `sample_max_column_m` rather than silently returning a negative column. That is the right
        outcome, and it is only reachable *because* the temperature now follows the burial depth.
        """
        from hcwc.core import seals
        from hcwc.ui.prospect_tab import temperature_range
        deep = temperature_range(4000.0)
        assert deep[1] > 132.0
        with pytest.raises(ValueError, match="132"):
            seals.sample_max_column_m(
                seals.SealInputs(temperature_c=deep, fluid="Oil"), 500)


class TestSliderDefaultsAreValid:
    """`sources._slider_default`, and the two ways a derived slider default breaks Streamlit.

    Both of these shipped and both reached Lars as a red traceback on the seal calculator. They are
    the kind of failure a type checker would not catch and a smoke test would only catch if it
    happened to open that expander, so they are pinned directly.
    """

    def test_the_result_is_always_floats(self):
        """`round()` with no ndigits returns an int, and Streamlit refuses a slider whose value type
        does not match its float bounds. This is the bug that broke Top seal (capillary)."""
        from hcwc.ui.sources import _slider_default
        low, high = _slider_default((56.25, 76.75), 10.0, 160.0)
        assert isinstance(low, float) and isinstance(high, float)

    def test_a_range_below_the_track_does_not_invert(self):
        """Clamping the ends independently gave (10.0, 5.0) for a near-surface burial depth -- a
        low above its high, which Streamlit also refuses."""
        from hcwc.ui.sources import _slider_default
        low, high = _slider_default((2.0, 5.0), 10.0, 160.0)
        assert low <= high

    def test_a_range_above_the_track_is_pulled_back_in(self):
        from hcwc.ui.sources import _slider_default
        low, high = _slider_default((180.0, 240.0), 10.0, 160.0)
        assert 10.0 <= low <= high <= 160.0

    @pytest.mark.parametrize("burial", [0.0, 200.0, 2050.0, 4500.0, 6000.0, 9000.0])
    def test_every_burial_depth_gives_a_slider_streamlit_will_accept(self, burial):
        """The real guarantee: whatever depth is typed on tab ②, the seal calculator opens."""
        from hcwc.ui.prospect_tab import temperature_range
        from hcwc.ui.sources import _slider_default
        low, high = _slider_default(temperature_range(burial), 10.0, 160.0)
        assert isinstance(low, float) and isinstance(high, float)
        assert 10.0 <= low <= high <= 160.0


class TestTabCrossReferences:
    """The prose says "tab ⑤" in fifty-odd places. Renumbering makes all of them suspect.

    R5 moved Empirical 7→8, Export 8→9 and Theory 9→10, and every sentence pointing at one of them
    silently became wrong. Nothing failed; the app just started telling the reader to look in the
    wrong place. These checks are cheap and catch the class.
    """

    CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"

    @staticmethod
    def _sources():
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        return [root / "app.py"] + sorted((root / "hcwc" / "ui").glob("*.py"))

    def _references(self):
        import re
        for path in self._sources():
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"tab ([" + self.CIRCLED + r"])", text):
                yield path.name, self.CIRCLED.index(match.group(1)) + 1, match.start(), text

    def test_every_reference_names_a_tab_that_exists(self):
        from hcwc.ui import theme
        for name, number, _, _ in self._references():
            assert number in theme.TAB_COLOURS, f"{name} points at tab {number}, which is gone"

    def test_the_prose_anchors_still_point_where_they_claim(self):
        """Distinctive phrases pinned to the tab they must name. If a tab moves, these fail rather
        than quietly misdirecting the reader."""
        from hcwc.ui import theme
        anchors = {
            "Define the limits on tab": "HCWC limiters",
            "Set the element risk on tab": "Prospect",
            "Full references in tab": "Theory",
        }
        joined = {name: text for name, _, _, text in self._references()}
        found = 0
        for phrase, expected_tab_name in anchors.items():
            expected = next(k for k, (_, label) in theme.TAB_COLOURS.items()
                            if label == expected_tab_name)
            for text in joined.values():
                index = text.find(phrase)
                while index != -1:
                    numeral = text[index + len(phrase) + 1]
                    assert numeral in self.CIRCLED, f"{phrase!r} is not followed by a tab numeral"
                    got = self.CIRCLED.index(numeral) + 1
                    assert got == expected, (
                        f"{phrase!r} points at tab {got} but {expected_tab_name} is tab {expected}")
                    found += 1
                    index = text.find(phrase, index + 1)
        assert found >= len(anchors), "the anchor phrases have been reworded; update this test"

    def test_no_module_points_the_reader_at_its_own_tab(self):
        """A module telling you to go to the tab you are already on is always a leftover from a move.

        `depth_risk_tab` and `results_tab` are the exceptions: each renders on both tab ④ and
        tab ⑤ — the same analysis on the geological sample and on the DHI posterior — so neither
        can avoid naming one of them. Every other module must point at a **sub-tab by name** when it
        means the other half of its own tab — "the *Risk against depth* sub-tab", not "tab ④".
        That is clearer to the reader, and it is what keeps this guard sharp now that the merge
        from ten tabs to eight has made same-tab references possible for three modules that
        previously could not make one.
        """
        import importlib
        # Both of these render on tab ④ AND tab ⑤ -- the same analysis on the geological
        # sample and on the DHI posterior -- so each has to name one of the two.
        allowed = {"depth_risk_tab.py", "results_tab.py"}
        for name, number, _, _ in self._references():
            module = name.replace(".py", "")
            if name in allowed or name == "app.py":
                continue
            try:
                tab = getattr(importlib.import_module(f"hcwc.ui.{module}"), "TAB", None)
            except ModuleNotFoundError:
                continue
            if tab is not None:
                assert number != tab, f"{name} refers the reader to tab {number}, its own tab"


def test_every_widget_in_the_shared_depth_risk_function_is_keyed():
    """`depth_risk_tab.render` is called twice per run — tabs ④ and ⑤ — so any widget it creates
    without an explicit key collides with its own twin.

    Streamlit derives an element's identity from its type and parameters, so the second instance
    raises `StreamlitDuplicateElementId`. Two of these shipped (a slider and, via `Numbering`, the
    figures), and the failure only appears once the DHI is switched on, which is exactly the state
    a smoke test with default inputs does not reach. Scanning the source is cheaper and complete.
    """
    import pathlib
    import re

    widgets = ("slider", "toggle", "checkbox", "radio", "selectbox", "number_input", "text_input",
               "multiselect", "file_uploader", "button", "data_editor", "plotly_chart",
               "dataframe", "download_button", "text_area")
    src = (pathlib.Path(__file__).resolve().parent.parent
           / "hcwc" / "ui" / "depth_risk_tab.py").read_text(encoding="utf-8")

    unkeyed = []
    for match in re.finditer(r"(?:st|[a-z0-9_]+)\.(" + "|".join(widgets) + r")\(", src):
        depth, i = 0, match.end() - 1
        while i < len(src):
            if src[i] == "(":
                depth += 1
            elif src[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        call = src[match.start():i + 1]
        if "key=" not in call:
            unkeyed.append(f"line {src[:match.start()].count(chr(10)) + 1}: {match.group(1)}")

    assert not unkeyed, "unkeyed widgets in a function rendered on two tabs: " + "; ".join(unkeyed)
