"""HCWC Distribution Builder — Streamlit shell.

Eight numbered, colour-coded tabs, no sidebar. Figures and tables are numbered by tab, so
`Figure 4.2` locates itself — and by sub-tab where a tab has enough of them for that to matter,
so `Figure 5.2.1` names the page as well as the position on it. The trial count and seed are
exposed rather than buried.

**Organised by risk element, not by pipeline.** Tab 2.0 is the prospect, tab 3.0 is every mechanism
that could limit the column grouped as Charge / Closure / Retention, and the rest are outputs. The
calculators — charge filling, seal capacity — are not tabs: each lives inside the limit it fills in,
behind a *Typed / Computed* radio, next to the inputs it consumes.

**Tab 4.0 is geological only.** The DHI update gets its own tab, 5.0, always present and saying so
when the prospect has no DHI. Each carries the same two readings as sub-tabs — the contact and its
per-element decomposition against depth. Keeping the geological and DHI pairs apart is not
tidiness: a fluid indicator senses whether a reservoir exists and what fluid fills it, not *which*
of charge, closure or retention failed, so it may move the total and may not edit the geological
model underneath.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from hcwc.core import charge as ch
from hcwc.core import trust
from hcwc.core import decompose as dc
from hcwc.io import benchmarks, geox, report
from hcwc.io import wellvolpos as wvp
from hcwc.ui import (depth_risk_tab, dhi_tab, dhi_walkthrough, empirical, limiters_tab,
                     prospect_tab, results_tab, theme)
from hcwc.ui import numbering
from hcwc.ui import sources
from hcwc.ui import run as engine_run
from hcwc.ui.numbering import Numbering

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"


def _render_with_figures(text: str, base: Path) -> None:
    """Render Markdown that carries relative image links.

    ``st.markdown`` resolves nothing relative to the file the text came from, so
    ``![](figures/x.png)`` renders as a *broken image* rather than as an error -- the
    failure mode where the article silently loses its five figures and nobody notices.
    The document is therefore split on its own image lines and those handed to
    ``st.image``, which does take a path. Everything else passes through untouched,
    including the blockquote caption after each figure: Lars's rule of 28 Aug 2026 is that
    a caption is never folded or separated from what it captions.

    Split on whole lines rather than by regular expression: an image line in this document is
    always alone on its line, and a pattern with four escaped brackets in it is the kind of thing
    that survives review and then quietly matches nothing.

    **It also breaks at every top-level heading, which is damage control rather than layout.**
    A ``$...$`` or ``$$...$$`` that opens on one line and closes on the next is an unterminated
    expression to a Markdown renderer, and it swallows everything after it until the next ``$``.
    Lars found exactly that on 7 Sep 2026: one wrapped equation in section 2 turned the rest of
    that section and all of section 3 into red LaTeX source. The wrapping is fixed and
    `TestThePaperAgreesWithTheAppItDescribes` now refuses a document that reintroduces it, but
    rendering section by section means the next one costs a section rather than the paper.
    """
    buffer: list[str] = []

    def flush() -> None:
        chunk = "\n".join(buffer).strip()
        buffer.clear()
        if chunk:
            st.markdown(chunk)

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("![") and stripped.endswith(")") and "](" in stripped:
            flush()
            src = stripped[stripped.index("](") + 2:-1].strip()
            target = base / src
            if target.exists():
                st.image(str(target), width="stretch")
            else:
                st.caption(f"`{src}` not found — run `scripts/paper_figures.py`.")
            continue
        if stripped.startswith("## "):
            flush()
        buffer.append(line)
    flush()


st.set_page_config(page_title="HCWC Distribution Builder", page_icon="📉", layout="wide")
theme.apply()

# --------------------------------------------------------------------------- restore, first
# A saved prospect is applied **before any widget is created**. Streamlit refuses a write to a
# widget's key once that widget has rendered this run, so the uploader stashes the parsed inputs
# and reruns; this block, at the top, is the only place they can safely land.
_pending = st.session_state.pop("_pending_load", None)
if _pending is not None:
    # `prospect.read` has already refused anything whose values would crash a widget. This guard is
    # for the case it cannot see: a file that is valid against *its* build meeting widgets that
    # have since moved. Failing here is a dead page — module scope, before any tab renders — so the
    # applied keys are rolled back and the reason is shown instead.
    _applied: list[str] = []
    try:
        for _key, _value in _pending.items():
            st.session_state[_key] = _value
            _applied.append(_key)
    except Exception as _load_exc:                      # noqa: BLE001 — reported, not raised
        for _key in _applied:
            st.session_state.pop(_key, None)
        st.error(
            f"**That prospect could not be applied, so nothing was changed.** {_load_exc}\n\n"
            "The file is readable but does not fit this version of the app. Rebuild it from the "
            "current tool rather than editing it."
        )
    else:
        st.session_state["_loaded_name"] = _pending.get("prospect_name", "prospect")

st.title("HCWC Distribution Builder")
st.caption(
    "Where is the hydrocarbon–water contact, why is it there, and what does that mean for the risk?"
)

(tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8) = st.tabs(theme.tab_labels())

# --------------------------------------------------------------------------- 1.0 Concept
with tab1:
    st.markdown(
        """
Predrill uncertainty in the depth of the hydrocarbon–water contact is often the largest single
driver of prospect resource potential, and it sets the probability of encountering hydrocarbons at
a specific well location.

A generic distribution for the contact — uniform from apex to spill point, say — carries
little connection to the mechanisms that may limit the column. A DHI, where present, may indicate
the contact directly; the question is with what certainty that indication should enter the
distribution.

This tool models the contact as a competition between geological limiting mechanisms: charge,
closure and spill, fault seal, top- and base-seal capacity and continuity, tilt-related spillage,
reservoir pinch-out.

Each limiter is assigned a probability of being active and an uncertainty in depth or capacity. In
each Monte Carlo realisation the shallowest active limit controls the column.

The simulation records which mechanism controls each realisation, so the result shows what sets
the contact and how that changes with depth. The distribution is derived from the geological
assumptions rather than imposed.

Where available, the result can be compared with empirical data and updated with DHI evidence.
        """
    )

    st.markdown(
        """
---

New here? Start with the tabs in this order.

- **2.0 Prospect** — apex, spill point, element risk and the assessment minimum: the smallest
  column that qualifies as a discovery at the well.
- **3.0 HCWC Limiters** — the mechanisms that may limit the column, each with its probability
  and its depth or capacity uncertainty.
- **4.0 Results** — the contact distribution, the controlling mechanism, and the probability of
  hydrocarbons with depth.
- **5.0 DHI** — the geological model updated with a DHI indication and its uncertainty.
- **6.0 Benchmarks** and **8.0 Theory** — empirical reference data and methodological
  background.
- **7.0 Export** — contact percentiles for predrill volumetric tools, with the distribution
  basis stated.

The worked example on **2.0 Prospect** fills every input for a real prospect.
        """
    )

    theme.heading(1, "1 · What can set a hydrocarbon–water contact")
    concept_png = ROOT / "reference" / "concept.png"
    if concept_png.exists():
        st.image(str(concept_png), width="stretch")
        st.caption(
            "Every mechanism that can stop the column, on one section, with the distribution of "
            "the depth at which it acts. Charge migrates in from below and follows the top "
            "reservoir up-dip to the apex; filling then works downward from there, which is why "
            "every capacity in this tool is measured from the apex. Figure by Lars Hjelm. "
            "`reference/concept_full.png` is the uncropped version with the depth-axis panel that "
            "tab 4.0 builds from live data."
        )

    theme.heading(1, "2 · The assessment minimum")
    st.markdown(
        "A probability of success refers to a stated definition of success: the smallest "
        "accumulation that would make the well a discovery. In this tool that volume corresponds "
        "to a contact depth, and that depth is the assessment minimum on tab 2.0."
    )
    with st.expander("Why the minimum defines the chance, and what that rules out"):
        st.markdown(
            """
The smallest volume that counts is the volume above some contact, so choosing it fixes how far
down the hydrocarbons must reach: a column height below the apex, or a depth in metres TVDSS.
That is the assessment minimum. It is the definition of success rather than a run setting.

The chance is then a reading of the contact distribution: POS is the exceedance at that depth,
`F(h_min)`. Chance and volume come off the same curve, so they cannot refer to different
thresholds. Moving the minimum moves both.

A trapping element that fails below the crest does not reduce the chance of finding hydrocarbons
at the well; it reduces the chance of a deeper contact. Folding fault seal, seal capacity or spill
into the chance chain understates POS and, because volume is conditioned on that chance,
overstates volume. Beha et al. (2012) describe this error. Here those mechanisms are limits on
tab 3.0, where they move the contact; only whether an element works at the crest belongs in the
chance on tab 2.0.
            """
        )

    theme.heading(1, "3 · Where the effort goes")
    st.markdown(
        "The ranking at the top of tab 3.0 shows which limit is setting the contact, and it "
        "updates as inputs change. In most cases a few limits control the answer and the rest do "
        "not move it, so the elicitation effort belongs on the top two or three. Tab 4.0 · 4.1.5 "
        "gives the same ranking restricted to realisations above the assessment minimum."
    )
    st.markdown(
        "Tab 6.0 · 8 compares the resulting distribution with 242 NCS discoveries at the same "
        "structural relief, and states whether it is optimistic or pessimistic against that record."
    )

    with st.expander(theme.section_label(1, "4 · Related tools"), expanded=False):
        st.markdown(
            "Four open-source tools, each doing one job. Each runs in the browser; *app* opens it "
            "and *code* shows what it does."
        )
        left, mid, right = st.columns(3)
        left.markdown(
            "**Upstream — E-POS**\n"
            "[app](https://e-pos.streamlit.app) · "
            "[code](https://github.com/lhjelm-dk/E-POS)\n"
            "Element risk: play and conditional chances for Charge, Closure, Reservoir and "
            "Retention, evidence support, and the Bayesian DHI update. Supplies the element chances "
            "on tab 2.0; the DHI strength model on tab 5.0 is adapted from its custom-R tool."
        )
        mid.markdown(
            "**Volumetrics — SCOPE-HC**\n"
            "[app](https://scope-hc.streamlit.app) · "
            "[code](https://github.com/lhjelm-dk/SCOPE-HC)\n"
            "Probabilistic volumes from GRV, reservoir and fluid inputs. It supplies the resource "
            "column the WellVolPOS export on tab 7.0 leaves out. Planned: it will read the "
            "101-percentile contact distribution exported there."
        )
        right.markdown(
            "**Downstream — WellVolPOS**\n"
            "[app](https://wellvolpos.streamlit.app) · "
            "[code](https://github.com/lhjelm-dk/WellVolPOS)\n"
            "Turns a contact distribution into well-location chance and at-the-well volume. "
            "Consumes the trial table and the per-element curves from tab 7.0."
        )

    with st.expander(theme.section_label(1, "5 · Known limitations"), expanded=False):
        st.markdown(
            """
None of these is a bug. Each is something the model does not do.

Seal capacity is treated as phase-independent. `h_max = P_c / (Δρ · g)` depends on the
density contrast between hydrocarbon and water, so a gas column and an oil column below the same
seal differ in height (Sales 1997; Graham et al. 2015). The seal calculator takes a fluid, but a
mixed-phase prospect needs the gas cap and the oil leg limited by different capacities with a
gas–oil contact between them, and this tool does not do that. Phases should be run as separate
cases; a single mixed-phase run is indicative.

Hydrodynamics and tilted contacts are not modelled. A hydrodynamic gradient tilts the contact and
changes the effective seal capacity; Grant (2020) includes it. The model assumes a hydrostatic,
horizontal contact. Remigration and hydraulic reconfiguration are absent for the same reason.

Compartmentalisation is out of scope. It turns one contact into several, and this tool builds one.
A compartmentalised trap needs a contact per compartment.

Whether a mechanism is present is drawn independently for each. The copula correlates the depths
at which limits act, so two faults may leak at similar depths, but it cannot state that they are
the same fault and stand or fall together. Beha et al. (2012) make the same independence
assumption.

The empirical benchmarks are conditioned on discovery, censored above and truncated below. Tab 6.0
sets out what that does to their use as a predrill prior.

The engine is validated against one published case. Beha et al. (2012) enumerate a two-fault
closure by hand and obtain 0.60 / 0.12 / 0.28 at three leak points; the engine reproduces all
three to Monte Carlo error. No published dataset of competing-limit models exists to test
against, so the engine's behaviour is verified by its test suite and its result by that one
example.

The competing-limits model is not new. Beha, Christensen and Young (2012) set it out: enumerate
the combinations of trapping elements sealing or failing, assign each scenario a probability, and
derive the leak point that follows. Grant (2020) publishes the controlling-limit diagnostic as
column height control statistics; Lowry et al. (2005) had chance against column height two
decades earlier. What is new here is the continuous, correlated form, and the censoring
correction on tab 6.0. The paper on tab 8.0 sets this out.
            """
        )

    st.divider()
    _left, _mid, _right = st.columns([1, 2, 1])
    with _mid:
        st.caption(
            "The tool is free and open source. Contributions towards its development are "
            "welcome and optional."
        )
        # `st.iframe` rather than `components.html`, which is deprecated with a removal
        # date of 2026-06-01 that has already passed. It takes the URL directly, so the
        # widget is no longer a frame inside a frame.
        st.iframe("https://ko-fi.com/lhjelm/?hidefeed=true&widget=true&embed=true&preview=true",
                  height=712)
        # The embed is the most-blocked kind of third-party frame there is: uBlock Origin and
        # Firefox's strict tracking protection both drop ko-fi widgets, and the viewer then sees
        # an empty box with no way to tell whether it is broken or still loading. The link is the
        # part that always works, so it sits beside the embed rather than instead of it.
        st.caption(
            "Not showing? Some ad blockers and Firefox's strict mode drop embedded widgets \u2014 "
            "[ko-fi.com/lhjelm](https://ko-fi.com/lhjelm) works either way."
        )

# --------------------------------------------------------------------------- 2.0 Prospect
with tab2:
    prospect_tab.render()

# --------------------------------------------------------------------------- 3.0 Limits
with tab3:
    limiters_tab.render()

# --------------------------------------------------------------------------- 4.0 Results
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
    # Numbered by sub-tab, as tab 5.0 is. Two sub-tabs is fewer than four, but the reason is the same
    # and so is the reader's problem: `Figure 4.6` said nothing about which of the two pages it was
    # on, and the tab-5.0 twin of the very same figure now says `5.3.6`. Matching them means a reader
    # comparing the two bases is reading one numbering scheme, not two.
    _contact, _depth = st.tabs(["4.1 · Contact and chance", "4.2 · Risk against depth"])
    for _panel in (_contact, _depth):
        with _panel:
            st.markdown(theme.subtab_marker(4), unsafe_allow_html=True)
    with _contact:
        results_tab.render(Numbering(4, sub=1, basis=theme.GEOLOGICAL))
    with _depth:
        depth_risk_tab.render(n=Numbering(4, sub=2, basis=theme.GEOLOGICAL))

# --------------------------------------------------------------------------- 5.0 Results + DHI
#
# **Three sub-tabs, because the first one was doing two jobs.** It elicited the DHI evidence AND
# presented the result, so the result half never grew the structure tab 4.0 has -- six of tab 4.0's
# objects had no counterpart here, and the controlling mechanism against depth existed only as a
# table. Splitting the evidence off makes room for the results to mirror tab 4.0 exactly.
#
# Sub-tab 2.0 is `results_tab.render` with a posterior: the same figures in the same order as tab 4.0,
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
    # `Figure 5.2.1` is the first exhibit on *The observation*, and it stays that whatever else moves.
    _how, _evidence, _contact_dhi, _depth_dhi = st.tabs(
        ["5.1 · How a DHI moves a chance", "5.2 · The observation",
         "5.3 · Contact and chance + DHI", "5.4 · Risk against depth + DHI"])
    for _panel in (_how, _evidence, _contact_dhi, _depth_dhi):
        with _panel:
            st.markdown(theme.subtab_marker(5), unsafe_allow_html=True)
    with _evidence:
        dhi_tab.render(Numbering(5, sub=2))
    with _how:
        dhi_walkthrough.render(Numbering(5, sub=1))
    with _contact_dhi:
        # **The posterior, whatever built it.** This asked for `dhi_on` and so hid the page from a
        # prospect updated by an offset penetration alone -- which is exactly the case sub-tab 5.2
        # now handles. The question this page answers is "is there an update", and the posterior
        # being there is that question.
        _post = st.session_state.get("dhi_posterior")
        if _post is None:
            st.info(
                "**Nothing to show until the evidence is described.** On tab 2.0, turn on either "
                "*This is a DHI prospect* or *This closure has been penetrated*, then fill in "
                "sub-tab 5.2 — the figures here are tab 4.0's, drawn on the updated distribution, "
                "so they need an update to draw."
            )
        else:
            results_tab.render(Numbering(5, sub=3, basis=theme.GIVEN_DHI), posterior=_post)
    with _depth_dhi:
        depth_risk_tab.render(depth_risk_tab.TAB_DHI, with_dhi=True,
                              n=Numbering(5, sub=4, basis=theme.GIVEN_DHI))

# Tab 4.0's trust panel, now that tab 5.0 has published the posterior one of its checks reports on.
# It is written into a container tab 4.0 reserved, so it still appears at the foot of tab 4.0.
results_tab.render_trust_panel()

# --------------------------------------------------------------------------- 6.0 Benchmarks
with tab6:
    empirical.render()

# --------------------------------------------------------------------------- 7.0 Export
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
        st.info("Define the limits on tab 3.0 first.")
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
            "at all — they are the chance-versus-depth curve per risk element from tab 4.0, the "
            "thing WellVolPOS cannot compute for itself because it never sees the competing limits."
        )

        try:
            # The grid on tab (3), not the shipped CSV -- an export describing a
            # structure the assessor had replaced would be a quiet lie.
            area_table = sources.current_area_depth()
            if area_table is None:
                raise FileNotFoundError
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
            st.info("Set the element risk on tab 2.0 to enable the element-curve export.")
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
            st.warning("**No element risk is set on tab 2.0, so `P(G)` is 1.0 and the page will say "
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
                           width="stretch")
        # The working record: the same summary, then every figure drawn this run with the caption
        # shown beside it in the app. Built on demand rather than every rerun -- it renders each
        # figure through kaleido, which is about a second apiece.
        if d2.button("Build the full report (with every figure and table)",
                     key="build_full_report",
                     width="stretch"):
            _full, _missing = report.build_full(
                result,
                report.Provenance(prospect=_name, basis=basis,
                                  trials=int(st.session_state.get("n_trials", 10_000)),
                                  seed=int(st.session_state.get("seed", 20260825)),
                                  source_file=st.session_state.get("_loaded_name", "")),
                st.session_state.get(numbering.FIGURES_KEY) or {},
                tables=st.session_state.get(numbering.TABLES_KEY) or {},
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
            "*and every table* the app drew, interleaved in number order, each with the caption "
            "that says what it means and what it cannot tell you. Nobody reads that end to end; it "
            "exists so a number quoted six months from now can be traced to the exhibit it came "
            "from, and so a reviewer can disagree with a specific chart rather than with the "
            "tool.\n\n"
            "**The tables were missing from it until 4 Sep 2026.** Figures were registered as they "
            "were drawn and tables were not, so the limits as entered, the group minima, the "
            "allocation comparison and the whole benchmark section were absent from a document "
            "called *the full report*.\n\n"
            "Figures embed as **vector SVG** — a few kilobytes each, sharp at any zoom, which "
            "matters because the arguments about a column-height distribution happen in the tails."
        )
        st.caption(
            "**HTML rather than PDF, on purpose.** A PDF would need a rendering engine this app "
            "cannot rely on having; the browser already has one, and its print dialogue makes a "
            "better PDF than any library would. The file is self-contained — no stylesheet, no "
            "font, no script — so it survives being emailed, and the figures are vector, so they "
            "print at the printer's resolution rather than the screenshot's.")

# --------------------------------------------------------------------------- 8.0 Theory & Guide
with tab8:
    st.markdown(
        "**The reasoning this tool rests on, the paper that sets it out, and the sources.** "
        "Everything here is meant to be argued with: the theory notes are the working behind three "
        "places where this tool refuses to multiply something in, and each is referenced from the "
        "tab that refuses."
    )

    theme.heading(8, "1 · Theory")
    # Five notes, one picker. Until 7 Sep 2026 this section also carried five *paper reviews* --
    # whether Beha, Hood, Monigle, Lowry and the seal-capacity literature say what this app claims
    # they say. Lars's call was that a user does not want to browse those. They are kept in
    # `docs/` and indexed in `docs/NEXT_PLAN.md`, which is the internal document by design; the
    # bibliography in section 3 names them where they bear on a citation.
    st.markdown(
        "*Competing limits* is the construction the tool rests on: why the contact is derived "
        "from the mechanisms rather than entered, and why the reference data are censored. "
        "*Prior or likelihood?*, *Weight, not Bayes* and *Base rates* are three notes on what "
        "may be treated as evidence, each written against a specific mistake. *DHI alignment* "
        "is a working note on how POS and the DHI update fit together. *Benchmark sources* is "
        "a negative result: what was searched for and not found."
    )

    _theory = st.radio(
        "Theory note",
        ["Competing limits", "Prior or likelihood?", "Weight, not Bayes", "Base rates",
         "DHI alignment", "Benchmark sources"],
        captions=["the construction, and why limits are not blended",
                  "why a base rate is not evidence",
                  "why tab 6.0 §8 weights rather than multiplies",
                  "the symmetric rule, and why it cannot be Bayes",
                  "working note · POS and the DHI update",
                  "is there a second public dataset? — no"],
        horizontal=True, label_visibility="collapsed", key="theory_doc")
    _theory_path = {"Competing limits": "COMPETING_LIMITS.md",
                    "Prior or likelihood?": "LIKELIHOOD_OR_PRIOR.md",
                    "Weight, not Bayes": "WEIGHT_NOT_BAYES.md",
                    "Base rates": "BASE_RATE_NEGLECT.md",
                    "DHI alignment": "DHI_alignment.md",
                    "Benchmark sources": "BENCHMARK_SOURCES.md"}[_theory]
    _theory_target = DOCS / _theory_path
    if _theory_target.exists():
        _render_with_figures(_theory_target.read_text(encoding="utf-8"), DOCS)
    else:
        st.info(f"`docs/{_theory_path}` not found in this checkout.")

    # The worked example that used to be section 1 in full, on arrival, above everything else.
    # It is one illustration of one of the five notes above and it now sits where an illustration
    # belongs -- behind its own summary, after the note it illustrates.
    with st.expander("**Worked: what multiplying a base rate in would do to this prospect** "
                     "— it makes you *more* certain after consulting a vaguer source"):
        st.markdown(
            "**A base rate is a *prior* over column height, and this tool already has one** — "
            "multiplying it in would count the same belief twice. A DHI can be a likelihood "
            "because it is an observation *of this prospect*.\n\n"
            "**Because a prior and a likelihood are the same kind of object** — both are "
            "functions of the unknown. A likelihood is a *use*, not a kind of distribution, and "
            "to act as one the data must be something **you observed on this prospect**.\n\n"
            "**So the test is not ‘is this a probability?’ but ‘does this data carry something my "
            "model has not already used?’** The argument is in → *Prior or likelihood?* above; "
            "the table below shows what getting it wrong does to a real prospect."
        )
        _t8_limits = st.session_state.get("limit_set")
        _t8_spill = ([i for i, nm in enumerate(_t8_limits.names) if "spill" in nm.lower()]
                     if _t8_limits is not None else [])
        # `_t8_mine` is the success cases, and an assessment minimum above every achievable column
        # leaves it empty -- the same emptiness tab 6.0 guards, reached by a different route. Checked
        # here rather than at each `np.percentile` below, because none of the four rows means anything
        # without it.
        _t8_have_successes = True
        if _t8_limits is not None and _t8_spill:
            _t8_probe = engine_run.current(_t8_limits)
            _t8_have_successes = bool(_t8_probe.above_minimum.any())
            if not _t8_have_successes:
                st.info(
                    "**No realisation reaches the assessment minimum**, so there is no column "
                    "distribution to fuse with the benchmark. Lower the minimum on tab 2.0."
                )
        if _t8_limits is not None and _t8_spill and _t8_have_successes:
            _t8_result = engine_run.current(_t8_limits)
            _t8_relief = float(np.median(_t8_result.sampled_m[:, _t8_spill[0]]))
            # `or` would take the fallback for a burial of zero, because zero is falsy -- a typed 0
            # silently became 2500 m. Only a genuinely absent value should fall back.
            _t8_stored = st.session_state.get("burial_depth")
            _t8_burial = float(_t8_stored if _t8_stored is not None else 2500.0)
            _t8_mine = _t8_result.column_m[_t8_result.above_minimum]

            _t8_fit = benchmarks._capacity_fit()
            _t8_bench = np.minimum(
                np.exp(np.random.default_rng(11).normal(
                    _t8_fit.intercept + _t8_fit.slope * np.log(_t8_burial), _t8_fit.sigma, 60_000)),
                _t8_relief)
            _t8_fused = benchmarks.shrink_toward(_t8_mine, _t8_bench, 0.5)

            # Histogram densities rather than a KDE: the point is the *width* of the product, which a
            # coarse density carries perfectly well, and it costs nothing on every rerun of this tab.
            _t8_edges = np.linspace(0.0, _t8_relief * 1.02, 220)
            _t8_mid = 0.5 * (_t8_edges[:-1] + _t8_edges[1:])

            def _t8_density(sample):
                # Normalised by hand rather than with `density=True`, which divides by the total and
                # hands back NaNs when that total is zero. A non-empty sample can still put nothing in
                # these bins: the axis runs to the structural relief, and at a high assessment minimum
                # every surviving column sits at or beyond it. NaNs there would read as a distribution
                # rather than as an empty one, and `_t8_pct` below already knows what to do with zeros.
                counts, _ = np.histogram(sample, bins=_t8_edges)
                total = float(counts.sum())
                if total <= 0:
                    return np.zeros(counts.size, dtype=float)
                return counts / np.diff(_t8_edges) / total

            def _t8_pct(density, p):
                cumulative = np.cumsum(density)
                if cumulative[-1] <= 0:
                    return float("nan")
                return float(np.interp(p / 100.0, cumulative / cumulative[-1], _t8_mid))

            _t8_dm, _t8_db = _t8_density(_t8_mine), _t8_density(_t8_bench)
            _t8_product = _t8_dm * _t8_db
            _t8_rows = [
                ("your model", _t8_pct(_t8_dm, 10), _t8_pct(_t8_dm, 50), _t8_pct(_t8_dm, 90)),
                ("the benchmark at your relief", _t8_pct(_t8_db, 10), _t8_pct(_t8_db, 50),
                 _t8_pct(_t8_db, 90)),
                ("the two fused, weight 0.5 — what tab 6.0 draws",
                 float(np.percentile(_t8_fused, 10)), float(np.percentile(_t8_fused, 50)),
                 float(np.percentile(_t8_fused, 90))),
                ("multiplied as if the benchmark were a likelihood",
                 _t8_pct(_t8_product, 10), _t8_pct(_t8_product, 50), _t8_pct(_t8_product, 90)),
            ]
            st.dataframe(
                pd.DataFrame([
                    {"": name, "P10": f"{p10:,.0f} m", "P50": f"{p50:,.0f} m",
                     "P90": f"{p90:,.0f} m", "P10–P90 spread": f"{p90 - p10:,.0f} m"}
                    for name, p10, p50, p90 in _t8_rows]),
                hide_index=True, width="stretch", key="t8_likelihood_table")
            st.caption(
                f"**Computed from the prospect in front of you** — relief {_t8_relief:,.0f} m, burial "
                f"{_t8_burial:,.0f} m — so it can be checked rather than believed.\n\n"
                f"**Read the last row against the first two.** Multiplying two densities always "
                f"sharpens, and that is *correct* when two independent instruments measure the same "
                f"thing. Here it produces a spread of "
                f"**{_t8_rows[3][3] - _t8_rows[3][1]:,.0f} m** — tighter than your own model's "
                f"{_t8_rows[0][3] - _t8_rows[0][1]:,.0f} m, after consulting a source whose own spread "
                f"is {_t8_rows[1][3] - _t8_rows[1][1]:,.0f} m. **Adding a vaguer opinion made you more "
                f"certain.** The arithmetic is telling you the two are not independent evidence."
            )

        st.markdown(
            "**One thing in that dataset *is* a genuine likelihood** — not the distribution, the"
            " **outcomes**. They cannot inform your column, but they can inform what you and those 242"
            " share: the parameters of the seal-capacity relationship. That is empirical Bayes, and it"
            " is the seal limit\u2019s *Pull this toward the NCS record* on tab 3.0."
        )


        st.markdown(
            "**One thing in that dataset *is* a genuine likelihood** — not the distribution, the "
            "**outcomes**. They cannot inform your column, but they can inform what you and those "
            "242 share: the parameters of the seal-capacity relationship. That is empirical "
            "Bayes, and it is the seal limit\u2019s *Pull this toward the NCS record* on tab 3.0."
        )

    theme.heading(8, "2 · The paper")
    st.markdown(
        "The method written up for a journal rather than for this screen: competing limits, the "
        "survival function every POS is read from, and the likelihood formulation of DHI "
        "evidence. It is the document to hand someone who does not use the tool."
    )
    _paper = DOCS / "ARTICLE.md"
    if _paper.exists():
        _paper_text = _paper.read_text(encoding="utf-8")
        st.info(
            "**Every number below is computed, not typed in.** The worked prospect is this "
            "app's own default read at a 120 m assessment minimum, the calibration figures "
            "come from the shipped NCS table, and the five figures are regenerated from the "
            "engine by `scripts/paper_figures.py`. Change an input and they move."
        )
        with st.expander("**Copy the source** — Markdown, for a manuscript or a document"):
            st.caption(
                "Written for a journal rather than a post: numbered sections, an abstract, "
                "figure captions and LaTeX maths. A submission would want the equations "
                "rebuilt in the publisher's template and the figures taken from "
                "`docs/figures/` at 200 dpi."
            )
            st.code(_paper_text, language="markdown")
        _render_with_figures(_paper_text, DOCS)
    else:
        st.info("`docs/ARTICLE.md` not found in this checkout.")

    theme.heading(8, "3 · References")
    st.markdown(
        "Every source this tool leans on, with each DOI checked and each entry saying what was "
        "taken from it. Open access is marked, because a claim you cannot go and read is a claim "
        "you have to take on trust."
    )
    _refs = DOCS / "REFERENCES.md"
    if _refs.exists():
        _render_with_figures(_refs.read_text(encoding="utf-8"), DOCS)
    else:
        st.info("`docs/REFERENCES.md` not found in this checkout.")
