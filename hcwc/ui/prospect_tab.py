"""Tab 2.0 — the prospect: its geometry, its element risk, and how the model is run.

Everything here is true of the whole prospect. Anything belonging to one mechanism lives on tab 3.0,
inside that mechanism's block.

Three things arrive here that used to be scattered. **Element risk** (play × conditional) was on
tab 4.0, a long way from the other inputs and after the results it feeds. **Burial depth** is new: it
is what the empirical benchmark on tab 6.0 conditions on, and it now also sets the seal calculator's
default temperature, so the two cannot be left saying different things about the same rock. And the
**DHI switch** is here rather than on the DHI tab, because whether a prospect has a fluid indicator
is a property of the prospect, not a display option.

What left: the area–depth table, which moved to tab 3.0 → Charge to sit beside the only calculation
that reads it.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from hcwc.core.decompose import ELEMENTS
from hcwc.core.limits import Group
from hcwc.io import epos
from hcwc.io import prospect as prospect_io
from hcwc.ui import theme
from hcwc.ui.numbering import Numbering

TAB = 2

#: A complete prospect to load rather than read twelve limit blocks cold.
_EXAMPLE = Path(__file__).resolve().parents[2] / "reference" / "example_prospect.hcwc.json"
#: A second one, spill-limited, so the controlling-limit diagnostic is seen going the other
#: way: the first example is seal-dominated, this one fills to spill in about seven
#: realisations in ten. Two examples teach the judgement where one teaches the mechanics.
_EXAMPLE_SPILL = (Path(__file__).resolve().parents[2] / "reference"
                  / "example_prospect_spill.hcwc.json")

#: (label, file, one sentence) for every shipped example, in the order they are offered.
EXAMPLES = (
    ("Load the worked example (seal-limited)", _EXAMPLE,
     "A 350 m closure at 2 050 m with a 120 m assessment minimum. Its top seal is computed "
     "rather than typed, and three limits share control of the contact, so the ranking on tab "
     "3.0 is informative."),
    ("Load the second example (spill-limited)", _EXAMPLE_SPILL,
     "A 150 m closure at 2 050 m with a tight, computed top seal and a 100 m assessment minimum. "
     "The spill point sets the contact in about seven realisations in ten, so the contact "
     "distribution is narrow and the geometry, not the seal, is what an elicitation would "
     "refine."),
)


def example_buttons(key: str) -> None:
    """One button per shipped example, on any tab. Loading stashes the file's inputs for the
    top of the next run, since the widgets of this run already exist."""
    shipped = [(i, label, path) for i, (label, path, _) in enumerate(EXAMPLES) if path.exists()]
    if not shipped:
        return
    for col, (i, label, path) in zip(st.columns(len(shipped)), shipped):
        if col.button(label, width="stretch", key=f"{key}_{i}"):
            try:
                st.session_state["_pending_load"] = prospect_io.read(
                    path.read_text(encoding="utf-8"))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.rerun()

#: Element -> (play, conditional) starting values. The product is the element chance.
#: Lars's values, 26 Aug 2026. Geological POS = 0.408.
DEFAULT_RISK: dict[Group, tuple[float, float]] = {
    Group.CHARGE: (1.00, 0.90),
    Group.CLOSURE: (1.00, 1.00),
    Group.RESERVOIR: (0.90, 0.70),
    Group.RETENTION: (0.90, 0.80),
}

#: Geothermal gradient range, °C/km, and surface temperature, used to default the seal
#: calculator's temperature from the burial depth — see :func:`temperature_range`.
#:
#: 25–40 spans normal to hot. The upper end is deliberately not the textbook 30: this tool's
#: reference data is Norwegian Continental Shelf, where gradients run high and 70–90 °C at about
#: 2 050 m is ordinary — which implies roughly 32–41 °C/km. A default that could not reach the
#: temperatures the reference data was collected at would be the wrong default.
GRADIENT_C_PER_KM = (25.0, 40.0)
SURFACE_C = 5.0


def gradient_range() -> tuple[float, float]:
    """The geothermal gradient in force: the slider in §1 · Geometry, or the default.

    Read through a function rather than off the constant so every consumer sees the same value:
    the temperature read-out here and the seal calculator's default on tab 3.0 are the same
    quantity, and a gradient the user moved that reached only one of them would let a prospect be
    assessed at two temperatures at once.
    """
    value = st.session_state.get("gradient_range")
    if value and len(value) == 2:
        return float(value[0]), float(value[1])
    return GRADIENT_C_PER_KM


def temperature_range(burial_m: float) -> tuple[float, float]:
    """Reservoir temperature implied by a burial depth, as a range.

    A *range* rather than a number because the gradient is the uncertain part, and the seal
    calculator wants a range anyway.

    This exists so burial depth and seal temperature cannot silently disagree. Interfacial tension
    falls with temperature, so a deeper prospect gets a weaker seal — and previously the two were
    typed independently, which meant a 4 000 m prospect could be assessed with a 70 °C seal without
    anything objecting.
    """
    lo, hi = gradient_range()
    km = max(burial_m, 0.0) / 1000.0
    return SURFACE_C + lo * km, SURFACE_C + hi * km


def _floor_note(hc_m: float | None, water_m: float | None, sigma_m: float,
                p_connected: float) -> None:
    """The contact's P90–P10 under this penetration at the chosen connection chance and at
    0.95, so the floor's cost is visible beside the slider that sets it."""
    from hcwc.core import engine
    from hcwc.core import well as well_core
    from hcwc.ui import run as engine_run
    limit_set = st.session_state.get("limit_set")
    if limit_set is None:
        return
    result = engine_run.current(limit_set)
    keep = result.above_minimum
    if not keep.any():
        return

    def spread(p: float) -> float:
        w = well_core.likelihood(result, well_core.WellControl(
            hc_down_to_m=hc_m, water_at_m=water_m, depth_sigma_m=sigma_m, p_connected=p))
        q = engine.weighted_percentiles(result.contact_m[keep], w[keep], [90.0, 10.0])
        return float(q[1] - q[0])

    prior = float(np.diff(engine.weighted_percentiles(result.contact_m[keep], None,
                                                      [90.0, 10.0]))[0])
    st.caption(
        f"What the connection chance costs on this prospect: the contact's P90–P10 is "
        f"{prior:,.0f} m before the well, {spread(p_connected):,.0f} m at {p_connected:.2f} and "
        f"{spread(0.95):,.0f} m at 0.95. The floor under the likelihood is 1 − {p_connected:.2f} "
        f"= {1 - p_connected:.2f}, and it is what keeps the penetration from ruling a depth out."
    )


def render() -> None:
    n = Numbering(TAB)
    st.subheader("The prospect")

    st.session_state.setdefault("prospect_name", "Tiramisu-C4")
    st.text_input("Prospect name", key="prospect_name")

    if st.session_state.pop("_loaded_name", None):
        st.success("Prospect loaded. Every input below, and every limit and calculator on tab "
                   "3.0, is as saved.")

    with st.expander("Save or load this prospect — or load the worked example"):
        st.markdown(
            "Inputs are held in the browser session until saved; closing the tab discards them. A "
            "saved file carries every input, including each calculator's settings, so a "
            "reloaded prospect recomputes from the numbers it was computed from.\n\n"
            "The file stores inputs, not results. Reopened after the tool has changed, it gives the "
            "current answer to the recorded question."
        )
        s1, s2 = st.columns(2)
        s1.download_button(
            "Download this prospect (.json)",
            prospect_io.to_json(st.session_state,
                                limit_set=st.session_state.get("limit_set")),
            file_name=f"{str(st.session_state.get('prospect_name', 'prospect')).replace(' ', '_')}"
                      f".hcwc.json",
            mime="application/json", width="stretch")
        loaded = s2.file_uploader("Load a saved prospect", type=["json"], key="prospect_upload")

        if any(path.exists() for _, path, _ in EXAMPLES):
            st.markdown("---")
            st.markdown("Two shipped examples, one seal-limited and one spill-limited. What "
                        "changes between them is the judgement the tool exists to support.")
            for _, _, sentence in EXAMPLES:
                st.caption(sentence)
            example_buttons("load_example")
        if loaded is not None:
            try:
                inputs = prospect_io.read(loaded.getvalue().decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError) as exc:
                st.error(str(exc))
            else:
                # Stashed rather than applied: the widgets below have already been created this
                # run, and Streamlit refuses a write to a live widget's key. The rerun lands it at
                # the top of app.py before anything renders.
                st.session_state["_pending_load"] = inputs
                st.rerun()

    # ------------------------------------------------------------------ geometry
    theme.heading(TAB, "1 · Geometry and the assessment minimum")
    st.markdown(
        "The apex is the datum: every capacity limit on tab 3.0 is measured downward from it. "
        "The spill point is stated once here and seeds the closure limit's range. The "
        "assessment minimum is the threshold a discovery has to meet, and every chance downstream "
        "is read at it."
    )
    # Seeded once, then owned by the widget. Passing a `value=` *and* a `key=` every run makes
    # Streamlit warn that the widget is driven from two places — and after a load it genuinely is,
    # with the literal default fighting the value that was just restored.
    for _key, _default in (("apex_p1", 2049.0), ("apex_p99", 2051.0), ("spill_input", 2400.0)):
        st.session_state.setdefault(_key, _default)

    a1, a2, a3 = st.columns(3)
    apex_lo = a1.number_input(
        "Apex, P1 (m TVDSS)", 0.0, 10000.0, step=10.0, key="apex_p1",
        help="The 1 % point of the apex depth, the shallow end. Narrow unless the depth "
             "conversion is poor.")
    apex_hi = a2.number_input(
        "Apex, P99 (m TVDSS)", 0.0, 10000.0, step=10.0, key="apex_p99",
        help="The 99 % point, the deep end. The gap to P1 is the depth-conversion uncertainty on "
             "the crest, and it is carried through every realisation rather than fixed.")
    spill = a3.number_input(
        "Spill point, as mapped (m TVDSS)", 0.0, 10000.0, step=10.0, key="spill_input",
        help="The mapped synclinal spill. Its uncertainty is a limit on tab 3.0 → Closure, "
             "and that limit's range opens around this value.")

    if apex_hi <= apex_lo:
        st.error("The apex P99 must be deeper than its P1.")
        return
    if spill <= apex_hi:
        st.error(
            f"The spill point ({spill:,.0f} m) is not below the apex P99 ({apex_hi:,.0f} m), so "
            f"the closure has no relief. Depth-stated limits are converted against the apex drawn "
            f"in each realisation, and this would give a negative column."
        )
        return

    st.session_state["apex"] = (apex_lo, apex_hi)
    st.session_state["spill_point"] = float(spill)

    apex_mid = 0.5 * (apex_lo + apex_hi)
    st.session_state["apex"] = (apex_lo, apex_hi)
    st.session_state["spill_point"] = float(spill)

    # The assessment minimum sits with the geometry because it is the definition of success,
    # not a run setting: every chance downstream is the exceedance curve read at this height.
    # Five metres rather than zero (Lars, 28 Aug 2026): a column of a metre or two cannot be
    # tested, and zero made the app open at a chance of 100 % by construction.
    st.session_state.setdefault("min_column_input", 5.0)
    m1, m2 = st.columns([1, 2])
    min_column = m1.number_input(
        "Assessment minimum (m column)", 0.0, 2000.0, step=5.0, key="min_column_input",
        help="The smallest column that would make the well a discovery, as a height below the "
             "apex. Stated as a column rather than a volume because only a column links to seal "
             "capacity (Hood 2019). Defaults to 5 m as a physical floor, not a commercial "
             "threshold.")
    st.session_state["min_column"] = float(min_column)
    m2.markdown(
        f"A discovery is a column of at least {min_column:,.0f} m, a contact at or below "
        f"{apex_mid + min_column:,.0f} m TVDSS at the mid apex. The limits on tab 3.0 say how "
        f"deep the column could reach; this says how deep it must reach to count. Method: see "
        f"8.1.3."
    )
    if min_column == 0:
        st.warning(
            "At zero every realisation meets the threshold and the prospect chance equals the "
            "element product. Tab 4.0 does not print a chance until this is above zero."
        )
    st.caption(
        f"Structural relief {spill - apex_mid:,.0f} m at the mid apex."
    )

    # ------------------------------------------------------------------ element risk
    theme.heading(TAB, "2 · Element chances")
    st.markdown(
        "Play is the chance the element works anywhere in the play; conditional is the chance it "
        "works here, given that it does. Their product is the element chance, and the four "
        "products multiply to P(G). This is the split E-POS produces; a single chance per element "
        "goes in Play with Conditional at 1.00.\n\n"
        "These do not move the contact. They scale the chance at each depth on tab 4.0."
    )
    st.info(
        "The chances here are for the element working at the crest. A trapping element that "
        "fails down-dip from the crest is a limit on tab 3.0, not a reduction of the chance "
        "here. Method: see 8.1.1.\n\n"
        "Retention here is whether the seal holds anything. How much it holds is the top-seal "
        "capacity on tab 3.0. An E-POS Retention number that already means the full column belongs "
        "on tab 3.0."
    )

    with st.expander("Take these from E-POS"):
        st.markdown(
            "Upload the prospect file E-POS saves, or the flat JSON form "
            "`{\"Charge\": 0.9, …}`.\n\n"
            "The file's `# Classic POS` row carries one number per element rather than a "
            "play/conditional split, so an import lands in Play with Conditional at 1.00 and the "
            "product equals the number E-POS booked. The ESL rollup is not recomputed here: it "
            "combines belief masses up a play × conditional tree with an uncertainty stance "
            "applied once at the top, and a second copy of that logic would drift from E-POS's."
        )
        upload = st.file_uploader("E-POS prospect (.csv) or element-POS (.json)",
                                  type=["csv", "json"], key="epos_upload")
        if upload is not None:
            try:
                imported = epos.read(upload.getvalue().decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError) as exc:
                st.error(str(exc))
            else:
                st.session_state["epos_import"] = imported.values
                st.success(f"Read from **{imported.source}**"
                           + (f" — prospect *{imported.title}*" if imported.title else ""))
                for warning in imported.warnings:
                    st.warning(warning)

    imported_pos = st.session_state.get("epos_import", {})
    header = st.columns([2, 1, 1, 1])
    for col, label in zip(header, ("Element", "Play", "Conditional", "Element chance")):
        col.markdown(f"**{label}**")

    element_pos: dict[Group, float] = {}
    for element in ELEMENTS:
        play_default, cond_default = DEFAULT_RISK[element]
        if element.value in imported_pos:
            play_default, cond_default = float(imported_pos[element.value]), 1.0
        c0, c1, c2, c3 = st.columns([2, 1, 1, 1])
        c0.markdown(
            f"<div style='padding-top:0.55rem'>"
            f"<span style='display:inline-block;width:0.8rem;height:0.8rem;border-radius:2px;"
            f"background:{theme.PILLAR_COLOURS[element.value]};margin-right:0.4rem'></span>"
            f"{element.value}</div>", unsafe_allow_html=True)
        play = c1.number_input("Play", 0.0, 1.0, play_default, 0.01,
                               key=f"play_{element.value}", label_visibility="collapsed")
        conditional = c2.number_input("Conditional", 0.0, 1.0, cond_default, 0.01,
                                      key=f"cond_{element.value}", label_visibility="collapsed")
        element_pos[element] = float(play * conditional)
        c3.markdown(f"<div style='padding-top:0.55rem'><b>{play * conditional:.3f}</b></div>",
                    unsafe_allow_html=True)

    st.session_state["element_pos"] = element_pos
    product = float(np.prod(list(element_pos.values())))

    # Its own line, at size, because it is the number this section exists to produce and it was
    # previously the smallest thing on the page -- a figure inside a grey caption, under a table
    # whose individual cells were louder than their product.
    accent = theme.accent(TAB)
    st.markdown(
        f"<div style='margin:0.6rem 0 0.2rem;padding:0.55rem 0.9rem;border-left:5px solid {accent};"
        f"background:{theme.rgba(accent, 0.10)};border-radius:0 5px 5px 0'>"
        f"<span style='font-size:0.82rem;letter-spacing:0.05em;text-transform:uppercase;"
        f"color:{theme.shade_hex(accent, -0.45)};font-weight:700'>Combined element chance &nbsp;P(G)</span>"
        f"<div style='font-size:2rem;font-weight:700;line-height:1.15;"
        f"color:{theme.shade_hex(accent, -0.5)}'>{product:.1%}</div>"
        f"<span style='font-size:0.85rem;opacity:0.8'>the product of the four above: "
        f"all four elements working at the crest</span></div>",
        unsafe_allow_html=True)

    st.caption(
        "P(G) is the chance that every element works at the crest; it carries no statement about "
        "how far down the column reaches. The geological POS is "
        "`P(G) × P(column ≥ h_min | G)`; tab 4.0 shows both terms and their product. Method: see "
        "8.1.4."
    )

    # ------------------------------------------------------------------ DHI
    theme.heading(TAB, "3 · Direct hydrocarbon indicator")
    # On by default, at Lars's request (27 Aug 2026). The reasoning that had it off was that a
    # tool assuming a DHI will find one -- but the tab is inert until an amplitude is actually
    # described, and leaving it off hid the whole DHI half of the app behind a switch most users
    # never found. A prospect without one turns it off in a click and the geological tabs are
    # unchanged either way.
    st.session_state.setdefault("dhi_toggle", True)
    dhi_on = st.toggle(
        "This is a DHI prospect", key="dhi_toggle",
        help="On by default. Off for a prospect with no amplitude support: tab 5.0 then says so "
             "and nothing else changes, because a DHI never edits the geological model.")
    st.session_state["dhi_on"] = bool(dhi_on)
    st.caption(
        "With this on, tab 5.0 HCWC (DHI + well) carries the evidence inputs and the update. "
        "Tab 4.0 stays geological either way."
        if dhi_on else
        "The geological model on tabs 3.0 to 4.0 stands on its own. With this on, a seismic "
        "amplitude enters as evidence on tab 5.0."
    )

    # ------------------------------------------------------------------ well control
    # Here rather than on tab 5.0 for the same reason the DHI switch is: whether a closure has been
    # penetrated is a fact about the prospect. It is the strongest evidence this tool takes and the
    # only one needing no argument -- a logged water leg is a measurement, where an amplitude is an
    # inference -- so it sits beside the geometry it constrains rather than behind the seismic.
    theme.heading(TAB, "4 · Offset well control")
    st.markdown(
        "A penetration in this closure is the sharpest evidence available about the contact. A "
        "water leg places the contact above it; hydrocarbons place it below. Either enters on tab "
        "5.0 as evidence that reweights the realisations from tab 3.0, not as an additional "
        "limit: a well observes the outcome of the mechanisms already modelled."
    )
    st.session_state.setdefault("well_toggle", False)
    well_on = st.toggle(
        "This closure has been penetrated", key="well_toggle",
        help="An appraisal, a nearby well through the same closure, or an earlier failure on the "
             "same structure. Off for an untested prospect.")
    st.session_state["well_on"] = bool(well_on)
    if well_on:
        w1, w2 = st.columns(2)
        use_hc = w1.checkbox(
            "Hydrocarbons proven down to", key="well_in_hc_on",
            help="The deepest depth at which hydrocarbons were established. The contact is below "
                 "it.")
        hc_depth = w1.number_input(
            "m TVDSS (hydrocarbons)", 0.0, 10000.0, float(apex_hi) + 100.0, 5.0,
            key="well_in_hc", disabled=not use_hc, label_visibility="collapsed")
        use_water = w2.checkbox(
            "Water seen at", key="well_in_water_on", value=True,
            help="The shallowest depth at which water was established in this reservoir. The "
                 "contact is above it.")
        water_depth = w2.number_input(
            "m TVDSS (water)", 0.0, 10000.0, float(apex_hi) + 200.0, 5.0,
            key="well_in_water", disabled=not use_water, label_visibility="collapsed")

        c1, c2 = st.columns(2)
        c1.slider(
            "Depth-tie uncertainty σ (m)", 1.0, 100.0, 30.0, 1.0, key="well_in_sigma",
            help="Not the well's own depth error, which is a metre or two, but the error in "
                 "tying that depth to the mapped surface the apex is measured from: the same depth "
                 "conversion that makes the apex a range.")
        c2.slider(
            "Chance the well samples this accumulation", 0.05, 1.0, 0.60, 0.05,
            key="well_in_connected",
            help="The fluid call is reliable; its relevance is uncertain: a different fault block, "
                 "compartment or sand. Below 1 so that one penetration cannot rule a contact out "
                 "entirely.")

        if use_hc and use_water and not hc_depth < water_depth:
            st.error(
                f"The hydrocarbons ({hc_depth:,.0f} m) must be above the water ({water_depth:,.0f} m). "
                f"Reversed, this describes two accumulations rather than one contact."
            )
        elif use_hc or use_water:
            # What the floor costs, on this prospect, where the slider is (open question 1,
            # 15 Sep 2026). The likelihood floor is 1 - p_connected, and at the shipped 0.60 a
            # tight bracket narrows the contact by almost nothing; the number here is read off
            # the last run's limit set, so it is one interaction behind on the first render.
            _floor_note(hc_depth if use_hc else None, water_depth if use_water else None,
                        float(st.session_state.get("well_in_sigma", 30.0)),
                        float(st.session_state.get("well_in_connected", 0.60)))
        elif use_hc:
            st.warning(
                "Hydrocarbons proven in this closure make the prospect a discovery. This tool uses "
                "the depth only and does not change the element chances above. See 8.1.8."
            )
        if not use_hc and not use_water:
            st.info("At least one is required. A penetration that established neither fluid is not "
                    "evidence about the contact.")

    # ------------------------------------------------------------------ further inputs
    theme.heading(TAB, "5 · Further inputs")
    st.markdown(
        "Inputs a first model can leave at their defaults. Burial depth and the geothermal "
        "gradient set the seal calculator's temperature on tab 3.0 and the benchmark comparison "
        "on tab 6.0. The trial count and the seed set the Monte Carlo."
    )
    b1, b2 = st.columns(2)
    # Seeded from the apex the first time only. After that the widget owns it, so a loaded
    # prospect is not overwritten by the apex on the next rerun.
    st.session_state.setdefault("burial_input", float(apex_mid))
    burial = b1.number_input(
        "Burial depth (m TVDSS)", 0.0, 10000.0, step=25.0, key="burial_input",
        help="Defaults to the apex. Edmundson's burial depth is a crest depth (mean 2 442 m "
             "against a mean trap height of 212 m in that dataset), so the apex is the appropriate "
             "default. Mid-reservoir is the alternative where that is the intended reference.")
    st.session_state["burial_depth"] = float(burial)
    st.session_state.setdefault("gradient_range", GRADIENT_C_PER_KM)
    g_lo, g_hi = b2.slider(
        "Geothermal gradient (°C/km)", 15.0, 60.0, step=0.5, key="gradient_range",
        help="Stated as a range because it is the uncertain part of the temperature. 25–40 spans "
             "normal to hot; the NCS default is high because 70–90 °C at about 2 050 m is "
             "ordinary there. It sets the seal calculator's temperature on tab 3.0.")
    t_lo, t_hi = temperature_range(burial)
    b2.markdown(
        f"<div style='margin-top:-0.4rem;font-size:0.9rem'>"
        f"Implied reservoir temperature &nbsp;{t_lo:,.0f}–{t_hi:,.0f} °C"
        f"<span style='opacity:0.7'> &nbsp;— {g_lo:.1f}–{g_hi:.1f} °C/km from "
        f"{SURFACE_C:.0f} °C surface</span></div>", unsafe_allow_html=True)
    st.caption(
        "The temperature seeds the seal calculator on tab 3.0 → Retention. Gas–water tension "
        "falls with temperature, so a deeper gas prospect has a weaker seal; oil–water tension "
        "is elicited there and does not follow the temperature. The seal block may override the "
        "temperature where it is measured."
    )

    r1, r2 = st.columns(2)
    n_trials = r1.number_input(
        "Realisations", 1_000, 100_000, 10_000, 1_000, key="n_trials_input",
        help="At 10 000, P99.5 rests on 50 realisations, which is stable; at 1 000 it rests on "
             "five, which is not. The ceiling of 100 000 puts 500 there, beyond which more trials "
             "add little, and one cached run costs 180 MB on a shared server.")
    seed = r2.number_input(
        "Random seed", 0, 2**31 - 1, 20260825, 1, key="seed_input",
        help="Fixed by default so figures regenerate identically. An unfixed seed moves every "
             "number between runs, which a quoted document cannot carry.")
    st.session_state["n_trials"] = int(n_trials)
    st.session_state["seed"] = int(seed)
    tail = n_trials * 0.005
    (st.success if tail >= 20 else st.warning)(
        f"P99.5 rests on {tail:,.0f} realisations."
        + ("" if tail >= 20 else " Raise the trial count; that estimate will move between runs.")
    )

    # ------------------------------------------------------------------ result
    # The tab's result: the prospect as stated, every number of it used downstream. Its own
    # section rather than the tail of the further inputs, so a reader finds it by number.
    theme.heading(TAB, "6 · The prospect as stated")
    n.table(
        pd.DataFrame([
            {"Property": "Apex", "Value": f"{apex_lo:,.0f}–{apex_hi:,.0f} m TVDSS"},
            {"Property": "Spill point, as mapped", "Value": f"{spill:,.0f} m TVDSS"},
            {"Property": "Structural relief", "Value": f"{spill - apex_mid:,.0f} m"},
            {"Property": "Burial depth", "Value": f"{burial:,.0f} m TVDSS"},
            {"Property": "Implied temperature", "Value": f"{t_lo:,.0f}–{t_hi:,.0f} °C"},
            {"Property": "Element chance P(G)", "Value": f"{product:.1%}"},
            {"Property": "Assessment minimum", "Value": f"{min_column:,.0f} m column"},
            {"Property": "DHI", "Value": "yes" if dhi_on else "no"},
        ]),
        "The prospect as stated. Every number here is used downstream and none is entered twice.",
        height=320)
