"""HCWC Distribution Builder — Streamlit shell.

Eight numbered, colour-coded tabs, no sidebar. Figures and tables are numbered by tab in one
shared sequence, so `Figure 4.2` locates itself; the trial count and seed are exposed rather than
buried.

**Organised by risk element, not by pipeline.** Tab ② is the prospect, tab ③ is every mechanism
that could limit the column grouped as Charge / Closure / Retention, and the rest are outputs. The
calculators — charge filling, seal capacity — are not tabs: each lives inside the limit it fills in,
behind a *Typed / Computed* radio, next to the inputs it consumes.

**Tab ④ is geological only.** The DHI update gets its own tab, ⑤, always present and saying so
when the prospect has no DHI. Each carries the same two readings as sub-tabs — the contact and its
per-element decomposition against depth. Keeping the geological and DHI pairs apart is not
tidiness: a fluid indicator senses whether a reservoir exists and what fluid fills it, not *which*
of charge, closure or retention failed, so it may move the total and may not edit the geological
model underneath.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import streamlit as st

from hcwc.core import charge as ch
from hcwc.core import trust
from hcwc.core import decompose as dc
from hcwc.io import geox, report
from hcwc.io import wellvolpos as wvp
from hcwc.ui import (depth_risk_tab, dhi_tab, empirical, limiters_tab, prospect_tab,
                     results_tab, theme)
from hcwc.ui.numbering import Numbering

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"

st.set_page_config(page_title="HCWC Distribution Builder", page_icon="📉", layout="wide")
theme.apply()

# --------------------------------------------------------------------------- restore, first
# A saved prospect is applied **before any widget is created**. Streamlit refuses a write to a
# widget's key once that widget has rendered this run, so the uploader stashes the parsed inputs
# and reruns; this block, at the top, is the only place they can safely land.
_pending = st.session_state.pop("_pending_load", None)
if _pending is not None:
    for _key, _value in _pending.items():
        st.session_state[_key] = _value
    st.session_state["_loaded_name"] = _pending.get("prospect_name", "prospect")

st.title("HCWC Distribution Builder")
st.caption(
    "Where is the hydrocarbon–water contact, why is it there, and what does that mean for the risk?"
)

(tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8) = st.tabs(theme.tab_labels())

# --------------------------------------------------------------------------- ① Purpose
with tab1:
    st.markdown(
        """
The depth of the hydrocarbon–water contact is the largest single driver of prospect volume, and it
is the only input that converts a prospect chance into a chance at a specific well location. Yet it
is usually entered as one distribution, chosen by habit, with no record of what controls it.

This tool builds the contact distribution the way the geology works: as a **competition between
limits**. Charge, closure and spill, fault juxtaposition, capillary and continuity failure of top and
base seal, tilt-related spillage, reservoir pinchout — each is sampled independently, each with its
own probability of being active, and the **shallowest active limit wins** in every realisation.
Nothing is blended, because blending a leak into the background column height suppresses outcomes
*above* the leak, which is not geology.

Because the model records **which limit won**, it answers questions a distribution alone cannot:
which mechanism actually controls this contact, how that changes with depth, and therefore which
element your risk really sits in — derived, not allocated.

It compares what you build against the published empirical record, and it corrects that record for a
bias nobody has corrected before: **a closure that filled to spill tells you about the closure, not
about the seal.** Nearly half the discoveries in the reference dataset are of that kind.

**It will not tell you whether to drill.** It produces one input to that decision, honestly, with its
provenance attached.
"""
    )

    theme.heading(1, "1 · What can set a hydrocarbon–water contact")
    concept_png = ROOT / "reference" / "concept.png"
    if concept_png.exists():
        st.image(str(concept_png), use_container_width=True)
        st.caption(
            "**Every mechanism that can stop the column, on one section, with its distribution "
            "where it acts.** Charge migrates in from below, follows the top reservoir up-dip under "
            "buoyancy to the structural apex, and filling then works **downward** from there — "
            "which is why every capacity in this tool is measured from the apex. Figure by Lars "
            "Hjelm; `reference/concept_full.png` is the uncropped version with the depth-axis "
            "panel, which tab ④ builds from live data."
        )

    theme.heading(1, "2 · The rule the whole tool rests on")
    st.markdown(
        """
**A probability of success is not a probability of anything until you say what counts as success.**

So say it. Name the smallest accumulation that would make the well a discovery — a cup of oil, a
sustained test rate, a commercial threshold; the tool does not care which, only that it is stated.
That single decision is the risk criterion, and everything else is downstream of it.

**In this tool, naming that volume names a depth.** The smallest volume that counts is the volume
above some contact, so choosing it fixes how far down the hydrocarbons must reach — a column height
below the apex, or equivalently a depth in metres TVDSS. That number is the **assessment minimum**
on tab ②, and it is not a detail of the run settings. It is the definition of success.

**Risk and volume are then one statement, not two.** POS is `F(h_min)` — the exceedance curve read
at that depth — so the chance and the volume it refers to come off the same object and cannot drift
apart. Move the minimum and both move together. Quote a chance from one threshold beside a volume
from another and you have said something incoherent, which is easy to do when POS arrives as a
scalar from one tool and volume as a distribution from another.

**What this rules out, and it is the common error.** A trapping element that fails *below* the crest
does not reduce the chance of finding hydrocarbons at the well — it reduces the chance of a *deeper
contact*. Folding fault seal, top seal capacity or spill into the chance chain therefore understates
POS and, because the volume is conditioned on that chance, **overstates volume**. Beha et al. (2012)
is written about exactly this. Here those mechanisms are limits on tab ③, where they move the
contact; only whether an element works *at the crest* belongs in the chance on tab ②.
"""
    )

    theme.heading(1, "3 · Where to start")
    st.markdown(
        """
Eight tabs is a lot to meet cold. There are only four steps, and the third is the one people skip
— so it now sits on the same screen as the second, where skipping it takes effort.

**1 · Describe the prospect — tab ②.** Apex, spill point, burial depth, the four element chances
from E-POS, and whether it has a DHI. **Set the assessment minimum**: it is the definition of
success, not a run setting, and nothing downstream means anything without it. Tab ④ will refuse to
show you a chance until you have.

**2 · Say what could stop the column — tab ③.** Twelve mechanisms grouped by risk element. Do not
elicit them carefully yet. Leave the defaults, switch off the ones this prospect does not have, and
move on.

**3 · Elicit only what matters — tab ③ §1, without leaving the tab.** The ranking at the top of tab
③ says which of the twelve is actually setting the contact, and it updates as you edit. **That
ranking is the point of the whole tool.** Most limits turn out not to move the answer, and the ones
that do are usually not the ones you would have spent the afternoon on — so spend it on the top two
or three and leave the rest rough. Tab ④ §3 has the fuller version: the same ranking restricted to
realisations worth drilling, and why the two differ.

**4 · Read the answer, and check it — tabs ④ and ⑥.** The exceedance curve is the output; the
chance is a *reading* of it at your minimum. Tab ⑥ §8 then says whether your distribution is
optimistic or pessimistic against 242 NCS discoveries at your own structural relief.

*If this is a DHI prospect, tab ⑤ carries the update, in the same two sub-tabs. Tab ④ stays purely
geological.*

**Not sure where to begin?** Tab ② → *Save or load this prospect* → **Load the worked example**.
"""
    )

    with st.expander("**4 · How it is arranged**", expanded=False):
        st.markdown(
            "**Tab ② is the prospect** — apex, spill point, burial depth, the element risk from E-POS, "
            "and whether this is a DHI prospect. **Tab ③ is every mechanism that could limit the "
            "column**, grouped by risk element: Charge, Closure, Retention. Everything after that is "
            "output.\n\n"
            "**Calculators are not tabs.** The charge filling and the seal-capacity calculation each "
            "live inside the limit they fill in, behind a *Typed / Computed* radio, beside the inputs "
            "they consume — the area–depth table sits next to the charge integration that reads it, "
            "and nowhere else.\n\n"
            "**Tab ④ is geological only.** The DHI update has its own tab, ⑤. That is "
            "not tidiness: a fluid indicator may move the total chance and may **not** re-attribute it "
            "between elements, so the geological model has to stay readable on its own."
        )

    with st.expander("**5 · Where this sits**", expanded=False):
        st.markdown(
            "Four free tools, each doing one job. Every one is open source and runs in the browser — "
            "**app** to use it, **code** to check what it does."
        )
        left, mid, right = st.columns(3)
        left.markdown(
            "**Upstream — E-POS**\n"
            "[app](https://e-pos.streamlit.app) · "
            "[code](https://github.com/lhjelm-dk/E-POS)\n"
            "Element risk: play and conditional for Charge, Closure, Reservoir and Retention, "
            "Italian-flag evidence support, and the Bayesian DHI/DFI update. Supplies the element "
            "chances on tab ②, and the DHI strength model on tab ⑤ is adapted from its custom-R tool."
        )
        mid.markdown(
            "**Volumetrics — SCOPE-HC**\n"
            "[app](https://scope-hc.streamlit.app) · "
            "[code](https://github.com/lhjelm-dk/SCOPE-HC)\n"
            "Probabilistic volumes from GRV, reservoir and fluid inputs. It is what supplies the "
            "`resource` column the WellVolPOS export on tab ⑦ deliberately leaves out. **Planned:** it "
            "will read the 101-percentile contact distribution exported there."
        )
        right.markdown(
            "**Downstream — WellVolPOS**\n"
            "[app](https://wellvolpos.streamlit.app) · "
            "[code](https://github.com/lhjelm-dk/WellVolPOS)\n"
            "Turns a contact distribution into well-location chance and at-the-well volume. Consumes "
            "the trial table and the per-element curves from tab ⑦."
        )

    with st.expander("**6 · Known limitations**", expanded=False):
        st.markdown(
            """
    Stated here rather than discovered later. None of these is a bug; each is a thing the model does
    not do, and knowing which is which is part of using it honestly.

    **Seal capacity is treated as phase-independent, and it is not.**
    `h_max = P_c / (Δρ · g)`, so it depends on the density contrast between hydrocarbon and water. **A
    gas column and an oil column below the same seal are very different heights** — Sales (1997), cited
    by Graham et al. (2015) as the interplay among closure height, seal capacity and fluid type. The
    seal calculator takes a fluid, but a **mixed-phase** prospect needs the gas cap and the oil leg
    limited by different capacities with a gas–oil contact between them, and this tool does not do that.
    Run the phases as separate cases; treat a single mixed-phase run as indicative. A deliberate scope
    decision, not an oversight.

    **Hydrodynamics and tilted contacts are not modelled.** A hydrodynamic gradient tilts the contact
    and changes the effective seal capacity. Grant (2020) includes it; this assumes a hydrostatic,
    horizontal contact.

    **The empirical benchmarks are conditioned on discovery**, censored above and truncated below.
    Tab ⑥ sets out exactly what that does and what it means for using them as a pre-drill prior.

    **The engine is validated against one published case, not against a population.** Beha et al.
    (2012) enumerate a two-fault closure by hand and get 0.60 / 0.12 / 0.28 at three leak points, and
    the engine reproduces all three to Monte Carlo error. That is a genuine external check and it is
    the only one there is — no published dataset of competing-limit models exists to test against, so
    the engine's *behaviour* is verified by its own test suite and its *result* by one worked example.

    **The competing-limits model is not new.** Beha et al. (2012) describe it, and Grant (2020)
    publishes the controlling-limit diagnostic. What is new here is the continuous, correlated form of
    it, and the censoring correction on tab ⑥ — see tab ⑧ → *Beha et al. (2012)*.
    """
        )

# --------------------------------------------------------------------------- ② Prospect
with tab2:
    prospect_tab.render()

# --------------------------------------------------------------------------- ③ Limits
with tab3:
    limiters_tab.render()

# --------------------------------------------------------------------------- ④ Results
#
# **The contact and its depth decomposition are two readings of one run, so they are two sub-tabs
# of one tab.** They were separate tabs until the strip outgrew its own rule — `theme.tab_labels`
# has always said eight is where it starts to scroll, and at ten the Theory tab was measurably
# off-screen on a normal laptop. Merging the pair here and the DHI pair below brings it back to
# eight without hiding anything.
#
# One `Numbering` per top-level tab, shared by its sub-tabs, so the figures run 4.1 … 4.n across
# both rather than restarting — two `Figure 4.1`s on one tab would break every cross-reference and
# would collide as Streamlit element keys.
with tab4:
    _n4 = Numbering(4)
    _contact, _depth = st.tabs(["① Contact and chance", "② Risk against depth"])
    with _contact:
        results_tab.render(_n4)
    with _depth:
        depth_risk_tab.render(n=_n4)

# --------------------------------------------------------------------------- ④ Results | DHI
with tab5:
    _n5 = Numbering(5)
    _contact_dhi, _depth_dhi = st.tabs(["① Contact and chance | DHI", "② Risk against depth | DHI"])
    with _contact_dhi:
        dhi_tab.render(_n5)
    with _depth_dhi:
        depth_risk_tab.render(depth_risk_tab.TAB_DHI, with_dhi=True, n=_n5)

# --------------------------------------------------------------------------- ⑤ Empirical basis
with tab6:
    empirical.render()

# --------------------------------------------------------------------------- ⑤ Export
with tab7:
    n8 = Numbering(7)
    theme.heading(7, "1 · 101-percentile export")
    st.markdown(
        "The **GeoX 101-fractile** format: two columns, `Percentile` and `Value`, running "
        "**P100 → P0** in the **exceedance** "
        "convention — P100 is the *shallowest* contact. Getting that backwards would invert every "
        "contact GeoX imports without raising an error anywhere, so it is asserted in the test "
        "suite.\n\n"
        "**Also the planned hand-off to [SCOPE-HC](https://scope-hc.streamlit.app)** — the same "
        "table is what it should read to take its contact distribution from here rather than from "
        "a typed three-point estimate."
    )
    e1, e2 = st.columns([2, 1])
    _overlay = st.session_state.get("dhi_overlay")
    _has_dhi = bool(st.session_state.get("dhi_on")) and _overlay is not None
    if _has_dhi:
        # No default. Until this existed the export was silently geological even with a DHI on,
        # so a file handed to GeoX for a DHI prospect was the wrong distribution and nothing said
        # so. A pre-selected answer would reintroduce exactly that, one click further away.
        basis = e1.radio("Which distribution?", ["— choose —", theme.GEOLOGICAL, theme.GIVEN_DHI],
                         horizontal=True, key="export_basis",
                         help="They are different distributions and the numbers alone cannot tell "
                              "you which you have. The choice goes in the filename and in the "
                              "provenance line inside the file.")
    else:
        basis = theme.GEOLOGICAL
        e1.markdown(f"**Basis** &nbsp; {theme.basis_tag(theme.GEOLOGICAL)} &nbsp; "
                    f"<span style='opacity:.7'>no DHI on this prospect</span>",
                    unsafe_allow_html=True)
    mode = e2.radio("Tail treatment", ["truncate", "raw"], horizontal=True,
                    help="P0 and P100 from a Monte Carlo are the sample minimum and maximum — the "
                         "least stable statistics in the run. Truncating at P0.5/P99.5 estimates "
                         "the endpoints from ~50 realisations instead of one.")

    limit_set = st.session_state.get("limit_set")
    if limit_set is None:
        st.info("Define the limits on tab ③ first.")
    elif basis == "— choose —":
        st.warning(
            "**This prospect has a DHI, so there are two contact distributions and they are not "
            "interchangeable.** Choose which one to export. Nothing is offered by default on "
            "purpose: a bare table of contact depths looks identical either way, and the wrong one "
            "in a volumetrics package is an error nothing downstream can catch."
        )
    else:
        result = results_tab._run(limit_set.to_dict(),
                                  int(st.session_state.get("n_trials", 10_000)),
                                  int(st.session_state.get("seed", 20260825)))
        if basis == theme.GIVEN_DHI:
            samples = np.asarray(_overlay["contact_samples"], dtype=float)
        else:
            samples = result.contact_m[result.above_minimum]
        exp = geox.percentile_table(samples, tail_mode=mode, basis=basis)
        n8.table(exp.table,
                 f"{theme.basis_tag(basis)} &nbsp; The built contact distribution, success cases "
                 f"only. {exp.provenance}", height=280)
        st.download_button(
            "Download CSV", exp.to_csv(),
            f"hcwc_percentiles_{basis.replace(' ', '_')}.csv", "text/csv")

        # ------------------------------------------------------------- WellVolPOS
        theme.heading(7, "2 · To WellVolPOS")
        st.markdown(
            "Two files, because they are two different things. The **trial table** is one row per "
            "realisation in WellVolPOS's canonical column names and units, so its importer maps "
            "every column with nothing to configure. The **element curves** are not per-trial data "
            "at all — they are the chance-versus-depth curve per risk element from tab ④, the "
            "thing WellVolPOS cannot compute for itself because it never sees the competing limits."
        )

        try:
            area_table = ch.AreaDepthTable.reference()
        except FileNotFoundError:
            area_table = None

        trials = wvp.trial_table(result, area_table)
        w1, w2 = st.columns(2)
        w1.metric("Trials exported", f"{len(trials):,}",
                  f"of {result.n:,} — successes only", delta_color="off")
        w2.metric("Columns WellVolPOS reads", f"{len(trials.columns)}",
                  "mapped with no configuration", delta_color="off")
        n8.table(trials.head(12), "The first twelve rows. Column names and units are "
                                  "WellVolPOS's canonical set, verified against its own adapter in "
                                  "the test suite.", height=260)
        st.download_button("Download trial table (CSV)", trials.to_csv(index=False),
                           "hcwc_trials.csv", "text/csv")

        st.warning(
            "**This is deliberately a partial trial set, and WellVolPOS will say so.** It requires "
            "`resource` in MMboe, and this tool cannot produce one: a resource needs net-to-gross, "
            "porosity, saturation, a formation volume factor and a recovery factor, none of which "
            "is a contact-depth question.\n\n"
            "Writing a made-up column to get past the importer would be the worst available "
            "outcome — every number downstream would then be computed from fiction and nothing "
            "would look broken. **Join the resource on from "
            "[SCOPE-HC](https://scope-hc.streamlit.app), which does the volumetrics**, and keep "
            "the trial order: row *n* here is row *n* there only if both were run on the same "
            "seed and trial count."
        )

        element_pos = st.session_state.get("element_pos")
        if element_pos is None:
            st.info("Set the element risk on tab ② to enable the element-curve export.")
        else:
            curves = wvp.element_curve_table(dc.decompose(result), element_pos)
            n8.table(curves.iloc[::20], "Chance against depth, one column per element, plus the "
                                        "whole-prospect curve read directly from the contact "
                                        "distribution. Every twentieth row shown.", height=240)
            st.download_button("Download element curves (CSV)", curves.to_csv(index=False),
                               "hcwc_element_curves.csv", "text/csv")
        st.caption(wvp.provenance(result, int(st.session_state.get("seed", 20260825)),
                                  int(st.session_state.get("n_trials", 10_000))))

        # ------------------------------------------------------------- one page
        theme.heading(7, "3 · One page, for the well proposal")
        _elements = st.session_state.get("element_pos") or {}
        _p_g = float(np.prod([float(v) for v in _elements.values()])) if _elements else 1.0
        st.markdown(
            f"Everything above is a CSV, and a CSV does not travel. This is the inputs, the "
            f"answer, the controlling-limit diagnostic, the trust checks and the provenance on "
            f"**one sheet** — open it and print to PDF.\n\n"
            f"It carries `Prospect POS = P(G) × P(column ≥ h | G)` = "
            f"**{_p_g:.3f} × {result.pos:.3f} = {_p_g * result.pos:.3f}** and both terms "
            f"separately, because the conditional term alone is {1 / _p_g if _p_g else 0:.1f}× the "
            f"prospect chance and reads exactly like it."
        )
        if not _elements:
            st.warning("**No element risk is set on tab ②, so `P(G)` is 1.0 and the page will say "
                       "so in red.** Set the four element chances before this goes to anyone: "
                       "without them the prospect POS on the sheet is the column term alone.")
        _checks = trust.review(result, posterior=(st.session_state.get("dhi_posterior")
                                                  if st.session_state.get("dhi_on") else None))
        _name = st.session_state.get("prospect_name") or limit_set.name or "prospect"
        _html = report.build(
            result,
            report.Provenance(prospect=_name, basis=basis,
                              trials=int(st.session_state.get("n_trials", 10_000)),
                              seed=int(st.session_state.get("seed", 20260825)),
                              source_file=st.session_state.get("_loaded_name", "")),
            checks=_checks, p_geological=_p_g,
            colours=results_tab.limit_colours(limit_set),
            note=st.session_state.get("report_note", ""))
        st.text_area("A note for the sheet (optional)", key="report_note", height=68,
                     placeholder="One or two sentences — the seal argument, the analogue, "
                                 "whatever a reader will ask about first.")
        st.download_button("Download the one-page summary (HTML)", _html,
                           f"{_name.replace(' ', '_')}_HCWC_summary.html", "text/html")
        st.caption(
            "**HTML rather than PDF, on purpose.** A PDF would need a rendering engine this app "
            "cannot rely on having; the browser already has one, and its print dialogue makes a "
            "better PDF than any library would. The file is self-contained — no stylesheet, no "
            "font, no script — so it survives being emailed, and the figures are vector, so they "
            "print at the printer's resolution rather than the screenshot's.")

# --------------------------------------------------------------------------- ⑥ Theory & Guide
with tab8:
    theme.heading(8, "Documents")
    doc = st.radio("Document", ["What to build next", "Beha et al. (2012)", "Seal capacity",
                                "Lowry et al. (2005)", "DHI alignment", "References"],
                   horizontal=True, label_visibility="collapsed")
    path = {"What to build next": "NEXT_PLAN.md",
            "Beha et al. (2012)": "BEHA_2012_REVIEW.md",
            "Seal capacity": "SEAL_CAPACITY_REVIEW.md",
            "Lowry et al. (2005)": "LOWRY_2005_REVIEW.md",
            "DHI alignment": "DHI_alignment.md", "References": "REFERENCES.md"}[doc]
    target = DOCS / path
    if target.exists():
        st.markdown(target.read_text(encoding="utf-8"))
    else:
        st.info(f"`docs/{path}` not found in this checkout.")
