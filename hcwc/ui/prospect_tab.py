"""Tab ② — the prospect: its geometry, its element risk, and how the model is run.

Everything here is true of the whole prospect. Anything belonging to one mechanism lives on tab ③,
inside that mechanism's block.

Three things arrive here that used to be scattered. **Element risk** (play × conditional) was on
tab ④, a long way from the other inputs and after the results it feeds. **Burial depth** is new: it
is what the empirical benchmark on tab ⑥ conditions on, and it now also sets the seal calculator's
default temperature, so the two cannot be left saying different things about the same rock. And the
**DHI switch** is here rather than on the DHI tab, because whether a prospect has a fluid indicator
is a property of the prospect, not a display option.

What left: the area–depth table, which moved to tab ③ → Charge to sit beside the only calculation
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


def temperature_range(burial_m: float) -> tuple[float, float]:
    """Reservoir temperature implied by a burial depth, as a range.

    A *range* rather than a number because the gradient is the uncertain part, and the seal
    calculator wants a range anyway.

    This exists so burial depth and seal temperature cannot silently disagree. Interfacial tension
    falls with temperature, so a deeper prospect gets a weaker seal — and previously the two were
    typed independently, which meant a 4 000 m prospect could be assessed with a 70 °C seal without
    anything objecting.
    """
    lo, hi = GRADIENT_C_PER_KM
    km = max(burial_m, 0.0) / 1000.0
    return SURFACE_C + lo * km, SURFACE_C + hi * km


def render() -> None:
    n = Numbering(TAB)
    st.subheader("The prospect")

    st.session_state.setdefault("prospect_name", "Prospect")
    st.text_input("Prospect name", key="prospect_name")

    if st.session_state.pop("_loaded_name", None):
        st.success("Prospect loaded. Every input below, and every limit and calculator on tab ③, "
                   "is as it was saved.")

    with st.expander("Save or load this prospect"):
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
                "limits share control of the contact, so tab ④'s ranking has something to say."
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
        "The apex is the **datum**: every capacity limit on tab ③ is measured downward from it. "
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
    apex_hi = a2.number_input("Apex, P99 (m TVDSS)", 0.0, 10000.0, step=10.0, key="apex_p99")
    spill = a3.number_input(
        "Spill point, as mapped (m TVDSS)", 0.0, 10000.0, step=10.0, key="spill_input",
        help="The mapped synclinal spill. Its **uncertainty** is a limit on tab ③ → Closure, and "
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
    t_lo, t_hi = temperature_range(burial)
    b2.metric("Implied reservoir temperature", f"{t_lo:,.0f}–{t_hi:,.0f} °C",
              f"{GRADIENT_C_PER_KM[0]:.0f}–{GRADIENT_C_PER_KM[1]:.0f} °C/km from {SURFACE_C:.0f} °C",
              delta_color="off")
    st.caption(
        f"**Structural relief {spill - apex_mid:,.0f} m** at the mid apex. The temperature seeds "
        f"the seal calculator on tab ③ → Retention, so a deep prospect cannot be assessed with a "
        f"shallow prospect's seal — interfacial tension falls with temperature, so deeper is a "
        f"weaker seal."
    )

    # ------------------------------------------------------------------ element risk
    theme.heading(TAB, "2 · Element risk")
    st.markdown(
        "Play × conditional per element, as **E-POS** produces them. These do not move the contact "
        "— they scale the chance of success *at* each depth on tab ④, and they are what makes the "
        "derived per-element curves a risk statement rather than a geometry statement."
    )
    st.info(
        "**These must be the chance the element works *at the crest*, for the minimum volume — not "
        "the chance it holds the column you are hoping for.** Beha et al. (2012) is written about "
        "this exact error: a trapping element that fails *down-dip* from the crest does not reduce "
        "the chance of finding hydrocarbons at the location, it reduces the chance of a **deeper "
        "contact**. Folding it into the chance chain as well as into the limits on tab ③ counts it "
        "twice, which understates POS and — their finding — **overstates volume**.\n\n"
        "So: Retention here is *does the seal hold anything at all*. **How much** it holds is the "
        "top-seal capacity on tab ③. If your E-POS Retention number already means the full column, "
        "it belongs on tab ③ instead of here."
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
    st.caption(
        f"**Geological POS, `P(G)` = {product:.1%}** — the product of the four, and E-POS's "
        f"headline number: the chance the prospect works *at all*. **It is not the prospect POS, "
        f"and it is not a chance at any particular column height.**\n\n"
        f"`Prospect POS = P(G) × P(column ≥ h | G)`. The second term is the whole of tab ④ — the "
        f"competing limits, conditional on the elements having worked — and tab ④ shows the "
        f"product. Taken down structure rather than read at one threshold, the same quantity is "
        f"the depth-risk curve on tab ④, and it falls as you go deeper."
    )

    # ------------------------------------------------------------------ DHI
    theme.heading(TAB, "3 · Direct hydrocarbon indicator")
    dhi_on = st.toggle(
        "This is a DHI prospect", key="dhi_toggle", help="Off by default. A DHI is evidence, and a tool that assumes one is present will find "
             "one.")
    st.session_state["dhi_on"] = bool(dhi_on)
    st.caption(
        "With this on, two further tabs become live: **Results | DHI** and **Depth risk | DHI**, "
        "carrying the evidence inputs and the Bayesian update. Tab ④ stays **purely "
        "geological** either way — a DHI never edits the geological model, and E-POS's resolution "
        "ceiling is why: a fluid indicator senses whether a reservoir exists and what fills it, "
        "not *which* of charge, closure or retention failed."
        if dhi_on else
        "The geological model on tabs ③ to ④ stands on its own. Turn this on to add a seismic "
        "amplitude as evidence, on two further tabs."
    )

    # ------------------------------------------------------------------ run settings
    theme.heading(TAB, "4 · Assessment and run settings")
    r0, r1, r2 = st.columns(3)
    min_column = r0.number_input(
        "Assessment minimum (m column)", 0.0, 2000.0, 0.0, 5.0, key="min_column_input",
        help="The minimum-volume risking criterion, stated as a **column height** rather than a "
             "volume — Hood's reason being that only a column height links to seal capacity. POS "
             "is then F(h) read at this value, the same object as the contact distribution.")
    n_trials = r1.number_input(
        "Realisations", 1_000, 1_000_000, 10_000, 1_000, key="n_trials_input", help="At 10 000, P99.5 sits on 50 realisations, which is enough to be stable; at 1 000 it "
             "is five, which is not.")
    seed = r2.number_input(
        "Random seed", 0, 2**31 - 1, 20260825, 1, key="seed_input", help="Fixed by default so figures regenerate identically. An unfixed seed makes every "
             "number on every tab move between runs, which is indefensible in a document "
             "someone will quote from.")

    st.session_state["min_column"] = float(min_column)
    st.session_state["n_trials"] = int(n_trials)
    st.session_state["seed"] = int(seed)

    if min_column == 0:
        st.caption(
            "At zero, every realisation counts as a success — so POS reads 100 % and the DHI "
            "likelihood ratio is undefined, because there is no failure set to compare against. "
            "Set a real minimum to get either."
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
