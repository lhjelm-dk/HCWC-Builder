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


def render() -> None:
    n = Numbering(TAB)
    st.subheader("The prospect")

    st.session_state.setdefault("prospect_name", "Tiramisu-C4")
    st.text_input("Prospect name", key="prospect_name")

    if st.session_state.pop("_loaded_name", None):
        st.success("Prospect loaded. Every input below, and every limit and calculator on tab 3.0, "
                   "is as it was saved.")

    with st.expander("Save or load this prospect — or load the worked example"):
        st.markdown(
            "**Everything lives in the browser session until you save it** — close the tab and an "
            "hour of eliciting twelve limits is gone. A saved file carries every input you touched, "
            "including each calculator's own settings, so a reloaded prospect recomputes from the "
            "numbers it was computed from.\n\n"
            "**The file stores inputs, not answers.** Reopened after the tool changes it gives the "
            "*new* answer to the *old* question, which is what a record of an assessment should do. "
            "Storing the outputs would produce a file that quietly disagreed with the tool that "
            "opened it."
        )
        s1, s2 = st.columns(2)
        s1.download_button(
            "Download this prospect (.json)",
            prospect_io.to_json(st.session_state,
                                limit_set=st.session_state.get("limit_set")),
            file_name=f"{str(st.session_state.get('prospect_name', 'prospect')).replace(' ', '_')}"
                      f".hcwc.json",
            mime="application/json", use_container_width=True)
        loaded = s2.file_uploader("Load a saved prospect", type=["json"], key="prospect_upload")

        example = _EXAMPLE
        if example.exists():
            st.markdown("---")
            st.markdown(
                "**New here?** Load the worked example instead of reading twelve limit blocks "
                "cold. It is a 350 m closure at 2 050 m with a **120 m assessment minimum**, so "
                "the risk criterion actually bites, and its top seal is **computed** rather than "
                "typed — which is the fastest way to see what the seal calculator does. Three "
                "limits share control of the contact, so tab 4.0's ranking has something to say."
            )
            if st.button("Load the worked example", use_container_width=True,
                         key="load_example"):
                try:
                    st.session_state["_pending_load"] = prospect_io.read(
                        example.read_text(encoding="utf-8"))
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
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
    theme.heading(TAB, "1 · Geometry")
    st.markdown(
        "The apex is the **datum**: every capacity limit on tab 3.0 is measured downward from it. "
        "The spill point and the burial depth are stated here once and reused — the spill seeds "
        "the closure limit's range, the burial depth sets the benchmark comparison and the seal "
        "calculator's temperature."
    )
    # Seeded once, then owned by the widget. Passing a `value=` *and* a `key=` every run makes
    # Streamlit warn that the widget is driven from two places — and after a load it genuinely is,
    # with the literal default fighting the value that was just restored.
    for _key, _default in (("apex_p1", 2049.0), ("apex_p99", 2051.0), ("spill_input", 2400.0)):
        st.session_state.setdefault(_key, _default)

    a1, a2, a3 = st.columns(3)
    apex_lo = a1.number_input(
        "Apex, P1 (m TVDSS)", 0.0, 10000.0, step=10.0, key="apex_p1",
        help="The 1 % point of the apex depth — the shallow end. Narrow unless the depth "
             "conversion is genuinely poor.")
    apex_hi = a2.number_input(
        "Apex, P99 (m TVDSS)", 0.0, 10000.0, step=10.0, key="apex_p99",
        help="The 99 % point — the deep end. The gap between this and P1 is the depth-conversion uncertainty on the crest, and it is carried through every realisation rather than fixed.")
    spill = a3.number_input(
        "Spill point, as mapped (m TVDSS)", 0.0, 10000.0, step=10.0, key="spill_input",
        help="The mapped synclinal spill. Its **uncertainty** is a limit on tab 3.0 → Closure, and "
             "that limit's range opens around this value, so it is entered once.")

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
    b1, b2 = st.columns(2)
    # Seeded from the apex the first time only. After that the widget owns it, so a loaded
    # prospect is not overwritten by the apex on the next rerun.
    st.session_state.setdefault("burial_input", float(apex_mid))
    burial = b1.number_input(
        "Burial depth (m TVDSS)", 0.0, 10000.0, step=25.0, key="burial_input",
        help="Defaults to the apex. Edmundson's burial depth is a reservoir/crest depth — it "
             "averages 2 442 m against a mean trap height of 212 m in that dataset — so the apex "
             "is the right default, but set it to mid-reservoir if that is what you mean.")
    st.session_state["burial_depth"] = float(burial)
    st.session_state.setdefault("gradient_range", GRADIENT_C_PER_KM)
    g_lo, g_hi = b2.slider(
        "Geothermal gradient (°C/km)", 15.0, 60.0, step=0.5, key="gradient_range",
        help="The uncertain part of the temperature, so it is stated as a range rather than a "
             "number. 25–40 spans normal to hot; the NCS default sits high on purpose, because "
             "70–90 °C at about 2 050 m is ordinary there. Moving it moves the seal calculator's "
             "temperature on tab 3.0 with it.")
    t_lo, t_hi = temperature_range(burial)
    b2.markdown(
        f"<div style='margin-top:-0.4rem;font-size:0.9rem'>"
        f"<b>Implied reservoir temperature &nbsp;{t_lo:,.0f}–{t_hi:,.0f} °C</b>"
        f"<span style='opacity:0.7'> &nbsp;— {g_lo:.1f}–{g_hi:.1f} °C/km from "
        f"{SURFACE_C:.0f} °C surface</span></div>", unsafe_allow_html=True)
    st.caption(
        f"**Structural relief {spill - apex_mid:,.0f} m** at the mid apex. The temperature seeds "
        f"the seal calculator on tab 3.0 → Retention, so a deep prospect cannot be assessed with a "
        f"shallow prospect's seal — interfacial tension falls with temperature, so deeper is a "
        f"weaker seal. **Move the gradient and that default moves with it**; the seal tab can still "
        f"override the temperature outright if it is measured."
    )

    # ------------------------------------------------------------------ element risk
    theme.heading(TAB, "2 · Element risk")
    st.markdown(
        "**Play** is the chance the element works anywhere in this play; **conditional** is the "
        "chance it works *here*, given the play does. Their product is that element's chance, and "
        "the four products multiply to P(G). It is the split **E-POS** produces — if your number "
        "is already one chance per element, put it in Play and leave Conditional at 1.00.\n\n"
        "These do not move the contact "
        "— they scale the chance of success *at* each depth on tab 4.0, and they are what makes the "
        "derived per-element curves a risk statement rather than a geometry statement."
    )
    st.info(
        "**These must be the chance the element works *at the crest*, for the minimum volume — not "
        "the chance it holds the column you are hoping for.** Beha et al. (2012) is written about "
        "this exact error: a trapping element that fails *down-dip* from the crest does not reduce "
        "the chance of finding hydrocarbons at the location, it reduces the chance of a **deeper "
        "contact**. Folding it into the chance chain as well as into the limits on tab 3.0 counts it "
        "twice, which understates POS and — their finding — **overstates volume**.\n\n"
        "So: Retention here is *does the seal hold anything at all*. **How much** it holds is the "
        "top-seal capacity on tab 3.0. If your E-POS Retention number already means the full column, "
        "it belongs on tab 3.0 instead of here."
    )

    with st.expander("Take these from E-POS"):
        st.markdown(
            "Upload the prospect file E-POS saves, or the flat JSON form "
            "`{\"Charge\": 0.9, …}`.\n\n"
            "The file's `# Classic POS` row is the contract, and it carries **one number per "
            "pillar** rather than a play/conditional split — so an import lands in **Play** with "
            "**Conditional** left at 1.00, and the product is exactly the number E-POS booked. "
            "The ESL rollup is deliberately not recomputed here: it combines belief masses up a "
            "play × conditional tree with an uncertainty stance applied once at the top, and a "
            "second copy of that logic would drift from E-POS's without anyone noticing."
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
        f"<span style='font-size:0.85rem;opacity:0.8'>the <b>product</b> of the four above — "
        f"all four elements working <b>at the crest</b></span></div>",
        unsafe_allow_html=True)

    st.caption(
        f"**What this number is, and what it is not.** `P(G)` is the chance that every element "
        f"works **at the crest**: charge arrived, there is a closure, there is reservoir, there is "
        f"a seal. It carries no statement about how far *down* the column reaches.\n\n"
        f"**The geological POS of this prospect is not this number.** In this tool success is "
        f"defined as a column of at least `h_min`, so\n\n"
        f"`Geological POS = P(G) × P(column ≥ h_min | G)`\n\n"
        f"and tab 4.0 shows both terms and their product. The second comes from the competing "
        f"limits; taken down structure rather than read at one threshold, it is the depth-risk "
        f"curve on tab 4.0's second sub-tab.\n\n"
        f"**Why the split falls exactly there.** A trapping element that fails *below* the crest "
        f"does not reduce the chance of finding hydrocarbons — it reduces the chance of a *deeper "
        f"contact*. Elicit these four for the crest only; seal capacity, spill and fault leakage "
        f"belong on tab 3.0, where they move the contact. Folding them in here would count them "
        f"twice and, because volume is conditioned on the chance, **overstate volume**."
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
        help="On by default. Turn it off for a prospect with no amplitude support: tab 5.0 then "
             "says so and nothing else changes, because a DHI never edits the geological model.")
    st.session_state["dhi_on"] = bool(dhi_on)
    st.caption(
        "With this on, two further tabs become live: **Results + DHI** and **Depth risk + DHI**, "
        "carrying the evidence inputs and the Bayesian update. Tab 4.0 stays **purely "
        "geological** either way — a DHI never edits the geological model, and E-POS's resolution "
        "ceiling is why: a fluid indicator senses whether a reservoir exists and what fills it, "
        "not *which* of charge, closure or retention failed."
        if dhi_on else
        "The geological model on tabs 3.0 to 4.0 stands on its own. Turn this on to add a seismic "
        "amplitude as evidence, on two further tabs."
    )

    # ------------------------------------------------------------------ well control
    # Here rather than on tab 5.0 for the same reason the DHI switch is: whether a closure has been
    # penetrated is a fact about the prospect. It is the strongest evidence this tool takes and the
    # only one needing no argument -- a logged water leg is a measurement, where an amplitude is an
    # inference -- so it sits beside the geometry it constrains rather than behind the seismic.
    theme.heading(TAB, "4 · Offset well control")
    st.markdown(
        "**A penetration in this closure is the sharpest evidence there is about the contact.** A "
        "water leg says the contact is above it; hydrocarbons say it is below. Either enters as "
        "evidence on tab 5.0 — reweighting the realisations tab 3.0 produced, never as an extra "
        "limit, because a well *observes* the outcome of the mechanisms already modelled rather "
        "than adding one."
    )
    st.session_state.setdefault("well_toggle", False)
    well_on = st.toggle(
        "This closure has been penetrated", key="well_toggle",
        help="An appraisal, a nearby well through the same closure, or an earlier failure on the "
             "same structure. Leave it off for an untested prospect.")
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
            help="**Not the well's own depth error**, which is a metre or two. This is the error "
                 "in tying that depth to the mapped surface the apex is measured from — the same "
                 "depth conversion that makes the apex a range rather than a number.")
        c2.slider(
            "Chance the well samples this accumulation", 0.05, 1.0, 0.60, 0.05,
            key="well_in_connected",
            help="The fluid call is reliable; its *relevance* is what is uncertain. A different "
                 "fault block, a different compartment, a different sand. Below 1 on purpose: it "
                 "is the floor that stops one penetration ruling a contact out entirely.")

        if use_hc and use_water and not hc_depth < water_depth:
            st.error(
                f"**The hydrocarbons ({hc_depth:,.0f} m) must be above the water "
                f"({water_depth:,.0f} m).** Reversed, this describes two accumulations rather than "
                f"one contact."
            )
        elif use_hc:
            st.warning(
                "**Hydrocarbons proven in this closure means the prospect is a discovery**, which "
                "is a much larger statement than anything about depth. This tool uses the depth "
                "only — it does **not** touch the element chances above, because a proven "
                "accumulation makes those a statement about an appraisal rather than a prospect. "
                "That is a judgement to make deliberately, not a side effect of typing a depth."
            )
        if not use_hc and not use_water:
            st.info("Tick at least one. A penetration that established neither fluid is not "
                    "evidence about the contact.")

    # ------------------------------------------------------------------ run settings
    theme.heading(TAB, "5 · Assessment and run settings")
    r0, r1, r2 = st.columns(3)
    # **Five metres, not zero.** Lars, 28 Aug 2026: a minimum of zero says a contact exactly at
    # the apex counts as success, which is a column of nothing -- arithmetically fine and
    # operationally meaningless, because a testing tool cannot be placed on a drill string to that
    # precision and a column of a metre or two cannot be tested at all. Zero also made the app open
    # with a chance of 100 % by construction, which tab (4) then had to refuse to display. Five is
    # a floor with a physical reason, not a guess at anyone's commercial threshold -- which is why
    # it is the smallest defensible number rather than a realistic one.
    st.session_state.setdefault("min_column_input", 5.0)
    min_column = r0.number_input(
        "Assessment minimum (m column)", 0.0, 2000.0, step=5.0, key="min_column_input",
        help="The minimum-volume risking criterion, stated as a **column height** rather than a "
             "volume — Hood's reason being that only a column height links to seal capacity. The "
             "chance is then F(h) read at this value, the same object as the contact distribution. "
             "Defaults to 5 m as a physical floor, not as a commercial threshold: set it to the "
             "smallest column that would make YOUR well a discovery.")
    n_trials = r1.number_input(
        "Realisations", 1_000, 100_000, 10_000, 1_000, key="n_trials_input",
        help="At 10 000, P99.5 sits on 50 realisations, which is enough to be stable; at 1 000 it "
             "is five, which is not. **The ceiling is 100 000**, which puts 500 there — past the "
             "point where more trials tell you anything, and short of where one cached run costs "
             "180 MB on a shared server.")
    seed = r2.number_input(
        "Random seed", 0, 2**31 - 1, 20260825, 1, key="seed_input", help="Fixed by default so figures regenerate identically. An unfixed seed makes every "
             "number on every tab move between runs, which is indefensible in a document "
             "someone will quote from.")

    st.session_state["min_column"] = float(min_column)
    st.session_state["n_trials"] = int(n_trials)
    st.session_state["seed"] = int(seed)

    st.caption(
        "**This is a column height, not a depth, and it is measured from the apex.** The contact "
        "it names is `apex + h_min`; at `h_min = 0` that *is* the apex, which is a column of "
        "nothing. **Nothing in the limits produces this number** — the limits say how deep the "
        "column could reach, and this says how deep it must reach to be worth drilling. They meet "
        "at one point: the chance is the exceedance curve read here.\n\n"
        "**Why the default is 5 m rather than 0.** A column of a metre or two cannot be tested. A "
        "testing tool cannot be placed on a drill string to that precision, so a contact you "
        "cannot straddle is not a discovery whatever the model says. Five is a physical floor and "
        "**not a commercial threshold** — most operators will want tens of metres, and some will "
        "want a rate rather than a height. Set it to the smallest column that would make *your* "
        "well a discovery, and say which definition you used when the number travels."
    )
    if min_column == 0:
        st.warning(
            "**At zero every realisation counts as a success.** The column term reads 100 % by "
            "construction, so the prospect chance collapses to the element product alone, and the "
            "DHI likelihood ratio is undefined because there is no failure set to compare "
            "against. Tab 4.0 will refuse to print a chance until this is above zero."
        )
    tail = n_trials * 0.005
    (st.success if tail >= 20 else st.warning)(
        f"P99.5 would sit on {tail:,.0f} realisations."
        + ("" if tail >= 20 else "  Raise the trial count — that estimate will move between runs.")
    )

    n.table(
        pd.DataFrame([
            {"Property": "Apex", "Value": f"{apex_lo:,.0f}–{apex_hi:,.0f} m TVDSS"},
            {"Property": "Spill point, as mapped", "Value": f"{spill:,.0f} m TVDSS"},
            {"Property": "Structural relief", "Value": f"{spill - apex_mid:,.0f} m"},
            {"Property": "Burial depth", "Value": f"{burial:,.0f} m TVDSS"},
            {"Property": "Implied temperature", "Value": f"{t_lo:,.0f}–{t_hi:,.0f} °C"},
            {"Property": "Geological POS", "Value": f"{product:.1%}"},
            {"Property": "Assessment minimum", "Value": f"{min_column:,.0f} m column"},
            {"Property": "DHI", "Value": "yes" if dhi_on else "no"},
        ]),
        "The prospect as stated. Every number here is used somewhere downstream and none of it is "
        "entered twice.", height=320)
