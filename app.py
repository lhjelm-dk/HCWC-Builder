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

import streamlit as st

from hcwc.ui import (concept, depth_risk_tab, dhi_tab, empirical, export, limiters_tab,
                     prospect_tab, results_tab, theme, theory)
from hcwc.ui.numbering import Numbering

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
    concept.render()

# --------------------------------------------------------------------------- 2.0 Prospect
with tab2:
    prospect_tab.render()

# --------------------------------------------------------------------------- 3.0 Limits
with tab3:
    limiters_tab.render()

# --------------------------------------------------------------------------- 4.0 HCWC (geological)
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

# --------------------------------------------------------------------------- 5.0 HCWC (DHI + well)
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
    # Three sub-tabs since 16 Sep 2026: the walkthrough that opened this tab is the derivation
    # and renders under 8.1.8, on the same live numbers.
    _evidence, _contact_dhi, _depth_dhi = st.tabs(
        ["5.1 · The observation",
         "5.2 · Contact and chance (DHI + well)", "5.3 · Risk against depth (DHI + well)"])
    for _panel in (_evidence, _contact_dhi, _depth_dhi):
        with _panel:
            st.markdown(theme.subtab_marker(5), unsafe_allow_html=True)
    with _evidence:
        dhi_tab.render(Numbering(5, sub=1))
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
                "sub-tab 5.1 — the figures here are tab 4.0's, drawn on the updated distribution, "
                "so they need an update to draw."
            )
        else:
            results_tab.render(Numbering(5, sub=2, basis=theme.GIVEN_DHI), posterior=_post)
    with _depth_dhi:
        depth_risk_tab.render(depth_risk_tab.TAB_DHI, with_dhi=True,
                              n=Numbering(5, sub=3, basis=theme.GIVEN_DHI))

# Tab 4.0's trust panel, now that tab 5.0 has published the posterior one of its checks reports on.
# It is written into a container tab 4.0 reserved, so it still appears at the foot of tab 4.0.
results_tab.render_trust_panel()

# --------------------------------------------------------------------------- 6.0 Benchmarks
with tab6:
    empirical.render()

# --------------------------------------------------------------------------- 7.0 Export
with tab7:
    export.render()

# --------------------------------------------------------------------------- 8.0 Theory & Guide
with tab8:
    theory.render()
