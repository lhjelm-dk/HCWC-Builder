"""HCWC Distribution Builder — Streamlit shell.

Eight numbered, colour-coded tabs, no sidebar. Figures and tables are numbered by tab, so
`Figure 4.2` locates itself — and by sub-tab where a tab has enough of them for that to matter,
so `Figure 5.2.1` names the page as well as the position on it. The trial count and seed are
exposed rather than buried.

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
from hcwc.ui import (depth_risk_tab, dhi_tab, dhi_walkthrough, empirical, limiters_tab,
                     prospect_tab, results_tab, theme)
from hcwc.ui import numbering
from hcwc.ui import run as engine_run
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
    horizontal contact. **Remigration and hydraulic reconfiguration** are absent for the same reason:
    both genuinely stop columns, and neither is here.

    **Compartmentalisation is out of scope, not merely unmodelled.** It turns one contact into
    several, and this tool builds one — a compartmentalised trap needs a contact per compartment,
    which is a different object rather than a harder version of this one.

    **Whether a mechanism is present is drawn independently for each.** The copula correlates the
    *depths* at which limits bite, so you can say two faults leak at similar depths — but not that
    they are the same fault and therefore stand or fall together. Beha et al. (2012) make the same
    independence assumption explicitly, which makes this a shared limitation of the approach rather
    than a defect of this implementation, and it is still a limitation.

    **The empirical benchmarks are conditioned on discovery**, censored above and truncated below.
    Tab ⑥ sets out exactly what that does and what it means for using them as a pre-drill prior.

    **The engine is validated against one published case, not against a population.** Beha et al.
    (2012) enumerate a two-fault closure by hand and get 0.60 / 0.12 / 0.28 at three leak points, and
    the engine reproduces all three to Monte Carlo error. That is a genuine external check and it is
    the only one there is — no published dataset of competing-limit models exists to test against, so
    the engine's *behaviour* is verified by its own test suite and its *result* by one worked example.

    **The competing-limits model is not new, and it is worth knowing whose it is.** Beha, Christensen
    & Young (2012) set it out: enumerate the combinations of trapping elements sealing or failing,
    assign each scenario a probability, and derive the leak point that follows. Their observation
    that *a deeper leak point can be more likely than a shallower one* — because it needs more
    elements to seal at once — is the principle in a sentence. Grant (2020) publishes the
    controlling-limit diagnostic as "column height control statistics"; Lowry et al. (2005) had
    chance against column height two decades ago. What is new here is the continuous, correlated
    form of it, and the censoring correction on tab ⑥ — see tab ⑧ → *Beha et al. (2012)* and
    *The article*.
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
    # Numbered by sub-tab, as tab ⑤ is. Two sub-tabs is fewer than four, but the reason is the same
    # and so is the reader's problem: `Figure 4.6` said nothing about which of the two pages it was
    # on, and the tab-⑤ twin of the very same figure now says `5.3.6`. Matching them means a reader
    # comparing the two bases is reading one numbering scheme, not two.
    _contact, _depth = st.tabs(["4.1 · Contact and chance", "4.2 · Risk against depth"])
    with _contact:
        results_tab.render(Numbering(4, sub=1))
    with _depth:
        depth_risk_tab.render(n=Numbering(4, sub=2))

# --------------------------------------------------------------------------- ⑤ Results | DHI
#
# **Three sub-tabs, because the first one was doing two jobs.** It elicited the DHI evidence AND
# presented the result, so the result half never grew the structure tab ④ has -- six of tab ④'s
# objects had no counterpart here, and the controlling mechanism against depth existed only as a
# table. Splitting the evidence off makes room for the results to mirror tab ④ exactly.
#
# Sub-tab ② is `results_tab.render` with a posterior: the same figures in the same order as tab ④,
# on the reweighted sample. The basis is a parameter rather than a control, so no widget can
# misroute it.
with tab5:
    # The lesson comes first for the reader: someone who does not yet believe the method has
    # nowhere to look on the other three sub-tabs, all of which assume it.
    #
    # It is rendered *second*, and the two facts are not in conflict. `st.tabs` returns containers,
    # so where content is written is independent of when. The walkthrough runs on the observation
    # `dhi_tab` has just built rather than on the previous frame's — which matters here more than
    # anywhere else in the app, because a first-time visitor lands on this page before touching a
    # widget, and a one-frame lag would greet them by asking for something they had already done.
    # Numbering by sub-tab is what makes that free: each owns its own sequence, so rendering out
    # of order no longer costs the reader anything.
    #
    # **One sequence per sub-tab, not per tab.** Four sub-tabs sharing a flat sequence gave a
    # reader `Figure 5.9` with no way to know which of the four pages to turn to — and the
    # sequence counts in render order, which here is not reading order. Numbered by sub-tab,
    # `Figure 5.2.1` is the first exhibit on *What you saw*, and it stays that whatever else moves.
    _how, _evidence, _contact_dhi, _depth_dhi = st.tabs(
        ["5.1 · How a DHI moves a chance", "5.2 · What you saw",
         "5.3 · Contact and chance | DHI", "5.4 · Risk against depth | DHI"])
    with _evidence:
        dhi_tab.render(Numbering(5, sub=2))
    with _how:
        dhi_walkthrough.render(Numbering(5, sub=1))
    with _contact_dhi:
        _post = st.session_state.get("dhi_posterior") if st.session_state.get("dhi_on") else None
        if _post is None:
            st.info(
                "**Nothing to show until the evidence is described.** Turn on *This is a DHI "
                "prospect* on tab ② and fill in sub-tab 5.2 — the figures here are tab ④'s, drawn "
                "on the updated distribution, so they need an update to draw."
            )
        else:
            results_tab.render(Numbering(5, sub=3), posterior=_post)
    with _depth_dhi:
        depth_risk_tab.render(depth_risk_tab.TAB_DHI, with_dhi=True,
                              n=Numbering(5, sub=4))

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
        result = engine_run.current(limit_set)
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

        # ------------------------------------------------------------- figures
        theme.heading(7, "3 · Every figure, as images")
        _figs = st.session_state.get(numbering.FIGURES_KEY) or {}
        st.markdown(
            f"**{len(_figs)} figures were drawn on this run**, and each is exported under its own "
            f"number — `Figure_4-3.png`, not `newplot.png`. Rendered at 1600 px and 2× device "
            f"scale, which is enough for a slide or a printed page.\n\n"
            f"**The camera button on any figure does one at a time**, in the browser, at the same "
            f"resolution and with the same filename. Use that when you want a single chart; use "
            f"this when you want the set."
        )
        if not _figs:
            st.info("No figures yet — visit the tabs you want, then come back. Only figures that "
                    "actually rendered this run can be exported, because a stale one would be "
                    "worse than a missing one.")
        elif st.button("Render every figure to PNG", key="render_figures"):
            import io as _io
            import zipfile as _zipfile
            _buffer = _io.BytesIO()
            _failed: list[str] = []
            _progress = st.progress(0.0, text="Rendering…")
            with _zipfile.ZipFile(_buffer, "w", _zipfile.ZIP_DEFLATED) as _zf:
                for _i, (_label, (_fig, _)) in enumerate(
                        sorted(_figs.items(), key=lambda kv: numbering.figure_order(kv[0])),
                        start=1):
                    try:
                        _png = _fig.to_image(format="png", width=1600, height=900, scale=2)
                    except Exception as _exc:                       # noqa: BLE001 — reported below
                        _failed.append(f"{_label}: {type(_exc).__name__}")
                        continue
                    _zf.writestr(f"{_label.replace(' ', '_').replace('.', '-')}.png", _png)
                    _progress.progress(_i / len(_figs), text=f"Rendering… {_label}")
            _progress.empty()
            if _failed:
                # Named rather than swallowed: a zip that is quietly short of what was asked for is
                # the kind of thing nobody notices until the figure is missing from the report.
                st.warning("**These would not render**, and are not in the archive:\n\n"
                           + "\n".join(f"- {x}" for x in _failed))
            st.download_button(
                f"Download {len(_figs) - len(_failed)} figures (.zip)", _buffer.getvalue(),
                f"{str(st.session_state.get('prospect_name', 'prospect')).replace(' ', '_')}"
                f"_figures.zip", "application/zip", key="download_figures")
        st.caption(
            "**Server-side rendering, via kaleido.** It is the one thing the browser cannot do — a "
            "page cannot zip twelve charts — and it is why kaleido is in `requirements.txt`. If "
            "this fails on a deployment, the camera button on each figure still works, because it "
            "never leaves the browser."
        )

        # ------------------------------------------------------------- one page
        theme.heading(7, "4 · One page, for the well proposal")
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
        d1, d2 = st.columns(2)
        d1.download_button("Download the one-page summary (HTML)", _html,
                           f"{_name.replace(' ', '_')}_HCWC_summary.html", "text/html",
                           use_container_width=True)
        # The working record: the same summary, then every figure drawn this run with the caption
        # shown beside it in the app. Built on demand rather than every rerun -- it renders each
        # figure through kaleido, which is about a second apiece.
        if d2.button("Build the full report (with every figure)", key="build_full_report",
                     use_container_width=True):
            _full, _missing = report.build_full(
                result,
                report.Provenance(prospect=_name, basis=basis,
                                  trials=int(st.session_state.get("n_trials", 10_000)),
                                  seed=int(st.session_state.get("seed", 20260825)),
                                  source_file=st.session_state.get("_loaded_name", "")),
                st.session_state.get(numbering.FIGURES_KEY) or {},
                checks=_checks, p_geological=_p_g,
                colours=results_tab.limit_colours(limit_set),
                note=st.session_state.get("report_note", ""))
            if _missing:
                st.warning("**These figures would not render** and are absent from the report "
                           "rather than substituted:\n\n"
                           + "\n".join(f"- {x}" for x in _missing))
            st.download_button("Download the full report (HTML)", _full,
                               f"{_name.replace(' ', '_')}_HCWC_report.html", "text/html",
                               key="download_full_report")
        st.caption(
            "**Two documents, two moments.** The **one-pager** is what you hand across a table: one "
            "sheet, two charts drawn at report size, every number on it one somebody will quote. "
            "The **full report** is the working record — the same summary followed by every figure "
            "the app actually drew, each with the caption that says what it means and what it "
            "cannot tell you. Nobody reads that end to end; it exists so a number quoted six "
            "months from now can be traced to the figure it came from, and so a reviewer can "
            "disagree with a specific chart rather than with the tool.\n\n"
            "Figures embed as **vector SVG** — a few kilobytes each, sharp at any zoom, which "
            "matters because the arguments about a column-height distribution happen in the tails."
        )
        st.caption(
            "**HTML rather than PDF, on purpose.** A PDF would need a rendering engine this app "
            "cannot rely on having; the browser already has one, and its print dialogue makes a "
            "better PDF than any library would. The file is self-contained — no stylesheet, no "
            "font, no script — so it survives being emailed, and the figures are vector, so they "
            "print at the printer's resolution rather than the screenshot's.")

# --------------------------------------------------------------------------- ⑥ Theory & Guide
with tab8:
    theme.heading(8, "Documents")
    # `NEXT_PLAN.md` is deliberately NOT listed. It is a development document -- what is built,
    # what is not, what was decided and why -- and a user reading it learns which parts the
    # author is unsure about, which is not the same as learning what the tool does. It stays in
    # the repo for whoever works on this next.
    doc = st.radio("Document", ["The article", "Benchmark sources", "Beha et al. (2012)",
                                "Seal capacity", "Lowry et al. (2005)", "DHI alignment",
                                "References"],
                   horizontal=True, label_visibility="collapsed")
    path = {"The article": "ARTICLE.md",
            "Benchmark sources": "BENCHMARK_SOURCES.md",
            "Beha et al. (2012)": "BEHA_2012_REVIEW.md",
            "Seal capacity": "SEAL_CAPACITY_REVIEW.md",
            "Lowry et al. (2005)": "LOWRY_2005_REVIEW.md",
            "DHI alignment": "DHI_alignment.md", "References": "REFERENCES.md"}[doc]
    target = DOCS / path
    if target.exists():
        _text = target.read_text(encoding="utf-8")
        if doc == "The article":
            st.info(
                "**Every number below is computed from the shipped dataset, not typed in.** The "
                "coefficients, the fill rates and the censored count are the ones this app "
                "produces — §3 of tab ⑥ draws them. If you change the tolerance or the dataset "
                "they will move, and the article says so where it matters."
            )
            with st.expander("**Copy the source** — Markdown, for LinkedIn or a document"):
                st.caption(
                    "LinkedIn strips Markdown, so the headings and bold will not survive a paste "
                    "into the post box — paste it somewhere that keeps them, or into LinkedIn's "
                    "article editor, which does. The em dashes and the ± are deliberate; the "
                    "tables will need rebuilding by hand in the post box."
                )
                st.code(_text, language="markdown")
        st.markdown(_text)
    else:
        st.info(f"`docs/{path}` not found in this checkout.")
