"""Tab 4.0 — the three outputs the engine exists to produce.

1. The exceedance curve, `F(h) = P(column >= h)`, which is the primary risk output. **Never a bare
   POS**: every chance quoted here carries the threshold it was read at, because a POS read at one
   threshold and a volume read at another is the specific error `docs/DHI_alignment.md` exists to
   prevent.
2. Which limit controlled the contact, against depth — the question a distribution alone cannot
   answer, and the reason the engine keeps the argmin.
3. The limit ranking, which is the answer to *which of the numbers I elicited actually mattered*.
   It is meant as a workflow step: run once, look at the ranking, then elicit properly only the two
   or three limits that bind.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hcwc.core import engine, sensitivity, trust
from hcwc.core import limits as limits_mod
from hcwc.core.limits import Group
from hcwc.ui import limit_stack, run, theme, trust_panel
from hcwc.ui.numbering import Numbering

TAB = 4

#: Where tab 4.0 parks the container its trust panel is drawn into. See :func:`render`.
TRUST_SLOT_KEY = "_trust_slot"

#: Below this effective sample size a tornado bar is reported as thin rather than drawn as though
#: it were as well supported as the rest. Same threshold and same reasoning as
#: :data:`hcwc.core.dhi.MIN_FAILURES_FOR_R`: a mean of a hundred effective realisations is coarse
#: but reportable, and twenty-seven is not.
MIN_TORNADO_SUPPORT = 100


def limit_colours(limit_set) -> dict[str, str]:
    """One colour per limit: a **variation of its risk element's hue**.

    Lars's rule, 25 Aug 2026: fault leakage and the seals are retention mechanisms, so they are
    greens — but not *the* retention green, which stays reserved for the element itself. Hue says
    which element a limit belongs to at a glance; lightness separates the limits inside it. That
    matters because colouring purely by element left five retention limits in one indistinguishable
    red, which defeats the point of a diagnostic whose whole job is to name mechanisms.
    """
    out: dict[str, str] = {}
    for group in Group:
        members = [name for name, g in zip(limit_set.names, limit_set.groups) if g is group]
        for name, colour in zip(members, theme.element_shades(group.value, len(members))):
            out[name] = colour
    return out



def _within_bin_move(result, edges, weights) -> float:
    """How much the DHI moves the *within-bin* mechanism mix, weighted by bin occupancy.

    Reported rather than asserted, because the honest answer is prospect-specific and small: a
    within-bin share conditions on contact depth, and contact depth is nearly all a DHI knows.
    Occupancy weighting is what keeps the number meaningful — a near-empty tail bin can swing
    twenty points on three realisations while contributing a bar too short to see.
    """
    geological = engine.controlling_share_by_depth(result, edges, within_bin=True)
    updated = engine.controlling_share_by_depth(result, edges, weights=weights, within_bin=True)
    occupancy = np.sum(list(engine.controlling_share_by_depth(
        result, edges, within_bin=False).values()), axis=0)
    return max(float(np.sum(occupancy * np.abs(updated[k] - geological[k]))) for k in geological)


def render(n: Numbering | None = None, *, posterior=None) -> None:
    """The contact distribution and what produced it, geological or DHI-updated.

    ``posterior`` is a :class:`hcwc.core.dhi.DhiPosterior` or ``None``. With one, every figure is
    drawn on the reweighted sample and the tab number, colour and basis banner follow. **The same
    figures in the same order either way** -- which is what makes flipping between tab 4.0 and tab 5.0
    a comparison rather than a hunt, and why the basis is a parameter here rather than a control
    the user could set inconsistently.
    """
    # The Numbering is passed in when this shares a tab with the depth-risk decomposition, so the
    # two sub-tabs draw from one sequence and `Figure 4.6` means one figure rather than two.
    given_dhi = posterior is not None
    tab = 5 if given_dhi else TAB
    weights = posterior.weights if given_dhi else None
    n = n or Numbering(tab)
    limit_set = st.session_state.get("limit_set")
    if limit_set is None:
        st.info("Define the limits on tab 3.0 first.")
        return

    result = posterior.result if given_dhi else run.current(limit_set)
    h_min = limit_set.min_column_m

    # Named for the evidence actually in the posterior. A prospect updated by an offset
    # penetration alone reaches this page too, and a heading reading "given the DHI" on it would be
    # simply false -- the one thing a basis label must never be.
    st.subheader(f"Results | {theme.evidence_basis()}" if given_dhi else "Results")
    if given_dhi:
        theme.basis_banner(
            theme.GIVEN_DHI,
            "Every figure below carries the evidence named above. The purely geological versions "
            "of the same figures are on tab 4.0, in the same order. They are a different "
            "distribution, not a different view of this one.")
    else:
        theme.basis_banner(
            theme.GEOLOGICAL,
            "The competing limits alone. Where the prospect has a DHI or a penetration, the "
            "updated results are on tab 5.0 and are a different distribution, not a different "
            "view of this one.")

    # ------------------------------------------------------------------ headline
    #
    # **Two chances, and they are not the same number.** `result.pos` is the *conditional*
    # column-height term: given the four elements work, does the column reach the assessment
    # minimum. The reportable prospect chance is that times the element product from tab 2.0. The
    # app showed only the conditional one here and called it "POS", which is the exact confusion
    # the rest of the tool is arranged to prevent -- Lars caught it on the report sheet, where a
    # 79.8 % read as a prospect chance when the prospect chance was 32.6 %.
    # Every probability below reads through these, so the basis is decided once rather than at
    # each of fifteen call sites -- one place to be wrong instead of fifteen.
    def pos_at(h: float) -> float:
        return (float(posterior.exceedance(h)[0]) if given_dhi
                else float(result.exceedance(h)[0]))

    def pct(p: float) -> float:
        return (float(posterior.percentiles(p)[0]) if given_dhi
                else float(result.percentiles(p)[0]))

    def exceed(grid_m):
        return posterior.exceedance(grid_m) if given_dhi else result.exceedance(grid_m)

    column_pos = pos_at(h_min)

    element_pos = st.session_state.get("element_pos") or {}
    p_geological = float(np.prod([float(v) for v in element_pos.values()])) if element_pos else 1.0
    prospect_pos = p_geological * column_pos

    if h_min <= 0:
        # **No number, rather than a number and a correction.** At a minimum of zero the column
        # term is 1.0 by construction, so "Prospect POS" collapses to the element product and reads
        # as a real answer to a reader who has not been told. It was printed here as 40.8 % on a
        # cold start, with the ✕ that says so five sections down the page, which nobody reaches
        # before forming an opinion. A tool that shows a wrong number and explains it later has
        # already lost; the fix is to show the explanation *instead of* the number.
        trust_panel.stop_card(trust.assessment_minimum(result))
        c1, c2, c3 = st.columns(3)
        for col, p in ((c1, 90), (c2, 50), (c3, 10)):
            col.metric(f"Contact P{p}", f"{pct(p):,.0f} m",
                       "all realisations — no minimum set", delta_color="off")
        st.caption(
            "The contact distribution stands; only the chance is undefined. With no minimum "
            "every realisation counts as a success, so these percentiles are the whole "
            "distribution rather than its success cases, and there is no threshold to read a "
            "chance at. Everything below this point is unaffected: the chance needs the minimum, "
            "the contact does not."
        )
    else:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(f"Prospect POS at h ≥ {h_min:.0f} m", f"{prospect_pos:.1%}",
                  "the reportable number", delta_color="off")
        m2.metric(f"P(column ≥ {h_min:.0f} m | G)", f"{column_pos:.1%}",
                  "conditional; this tab only", delta_color="off")
        for col, p in ((m3, 90), (m4, 50), (m5, 10)):
            col.metric(f"Contact P{p}", f"{pct(p):,.0f} m",
                       "success cases only", delta_color="off")
        st.markdown(
            f"The prospect chance is a product of two terms, and this tab computes one of "
            f"them.\n\n"
            f"`Prospect POS = P(G) × P(column ≥ h | G)` = "
            f"{p_geological:.3f} × {column_pos:.3f} = {prospect_pos:.3f}\n\n"
            f"`P(G)` is the element chance from tab 2.0: the product of the four element chances, "
            f"the chance the prospect works at all, and E-POS's headline number. It says nothing "
            f"about how tall the column is. `P(column ≥ h | G)` is what this tab computes: the "
            f"competing limits, conditional on the elements having worked."
        )
        st.caption(
            "Every chance here carries its threshold and the conditioning it was computed under. "
            "The contact percentiles are success cases only. The distribution is the primary "
            "object and the chance multiplies it. A chance from one threshold beside a volume "
            "from another is the error tab 6.0 is written to prevent; the conditional term quoted "
            "as the prospect chance is the same error one level up."
        )

    # ------------------------------------------------------------------ 1 · exceedance
    theme.heading(tab, sub=n.sub, text="1 · Contact depth")
    # A cumulative curve hides where the mass is: two quite different contact distributions can
    # trace nearly the same exceedance. The histogram is the same object read the other way, so it
    # is on by default and switchable off rather than the reverse.
    show_hist = st.checkbox("Show the contacts themselves", value=True,
                            key=f"contact_hist_{tab}",
                            help="The distribution the curve beside it is the cumulative form of, "
                                 "binned by depth on its own axis.")
    grid = np.linspace(0.0, float(result.column_m.max()) * 1.02, 400)
    f = exceed(grid)
    apex_med = float(np.median(result.apex_m))
    fig = go.Figure()

    if show_hist:
        # The token picks the colour; the words come from what is actually in the weights.
        basis = theme.GIVEN_DHI if given_dhi else theme.GEOLOGICAL
        basis_words = theme.evidence_basis() if given_dhi else theme.GEOLOGICAL
        edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 61)
        counts, _ = np.histogram(result.contact_m, bins=edges, weights=weights)
        total = float(counts.sum())
        fig.add_bar(y=0.5 * (edges[:-1] + edges[1:]), x=counts / total if total else counts,
                    orientation="h", xaxis="x2", name=f"contacts — {basis_words}", opacity=0.45,
                    marker_color=theme.BASIS_COLOUR[basis], marker_line_width=0,
                    hovertemplate="%{y:.0f} m TVDSS<br>%{x:.1%} of realisations<extra></extra>")

    fig.add_scatter(x=f, y=apex_med + grid, mode="lines", name="P(contact deeper than this)",
                    line=dict(color="#4C72B0", width=3))
    if h_min > 0:
        fig.add_hline(y=apex_med + h_min, line=dict(color="#C44E52", dash="dash"),
                      annotation_text=f"assessment minimum — P(column ≥ h | G) = {column_pos:.1%}",
                      annotation_position="bottom right")
    for p, dash in ((90, "dot"), (50, "solid"), (10, "dot")):
        fig.add_hline(y=pct(p), line=dict(color="#888", dash=dash, width=1),
                      annotation_text=f"P{p}", annotation_position="top left")
    fig.update_layout(xaxis_title="Probability the contact is deeper", xaxis_range=[0, 1],
                      yaxis_title="Depth (m TVDSS)", yaxis=dict(autorange="reversed"),
                      height=560, margin=dict(t=20 if not show_hist else 58),
                      legend=dict(orientation="h", y=-0.15))
    if show_hist:
        # Its own axis, so "probability the contact is deeper" keeps meaning exactly one thing, and
        # scaled to a third of the width so the bars read as the ground the curve stands on.
        peak = float(np.max(counts / total)) if total else 1.0
        fig.update_layout(bargap=0.04, xaxis2=dict(
            overlaying="x", side="top", range=[0, max(peak, 1e-6) * 3.0], showgrid=False,
            tickformat=".0%", title="share of realisations per depth bin",
            title_font_size=11, tickfont_size=10))
    n.plot(fig, "The exceedance curve `F(h) = P(column ≥ h)` on the depth axis. Depth on y, "
                "inverted, m TVDSS, the convention throughout this tool and WellVolPOS. This "
                "curve is the risk output; POS at any threshold is a reading of it.")

    # ------------------------------------------------------------------ 2 · which limit controls
    theme.heading(tab, sub=n.sub, text="2 · Controlling limit by depth")
    edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 26)
    centres = 0.5 * (edges[:-1] + edges[1:])

    # **The DHI is in this figure and was invisible in it.** Drawn on its own the updated shares
    # look like any other stacked bar; the only way to see what the amplitude did was to hold the
    # geological twin on tab 4.0 in your head and flip between tabs. Three views of one figure fixes
    # that, and the third is the one worth having — the difference is where the finding is.
    # The option labels name the two distributions being compared, so they follow the evidence
    # like every other basis label. `DIFFERENCE` names the *operation*, and "what the evidence
    # changed" is the honest reading of it whichever channel supplied the weights.
    GIVEN = theme.evidence_title()
    GEOLOGICAL, DIFFERENCE = "Geological", "What the evidence changed"
    view, scaled = GEOLOGICAL, False
    if given_dhi:
        view = st.radio("Show", (GIVEN, GEOLOGICAL, DIFFERENCE), horizontal=True,
                        key=f"controlling_view_{tab}",
                        help="A DHI cannot say which element failed. It can say which limit set "
                             "the contact, because roughly where the contact sits is evidence "
                             "about which mechanism put it there.")
        # **Without this the first two views are indistinguishable, and correctly so.** Normalising
        # each bin against itself conditions on contact depth, and the detection function is
        # saturated at its ceiling for every column in every occupied bin — so once the depth is
        # fixed the amplitude has nothing left to discriminate on. What it does move is *how many
        # realisations reach each depth*, by up to ten points, and that only shows when the bars
        # are left as shares of the whole sample.
        scaled = st.checkbox(
            "Scale bars by how many realisations reach each depth", value=True,
            key=f"controlling_scaled_{tab}", disabled=view == DIFFERENCE,
            help="On: bars are shares of all realisations, so bin height carries the contact "
                 "distribution and the two bases differ visibly. Off: each bin is normalised "
                 "against itself, the classic diagnostic, which a DHI cannot move.")
    basis_weights = weights if view != GEOLOGICAL else None
    if view == DIFFERENCE:
        # **Not the difference of the two views above, and it cannot be.** Those normalise within
        # each depth bin, which conditions on contact depth — and a DHI's evidence is almost
        # entirely about contact depth, so the within-bin mix is nearly untouched by it: 0.95
        # points at most on the worked prospect, against 3.9 in the overall shares. Drawing that
        # difference would draw a row of empty bins and call it a finding.
        #
        # Shares of *all* realisations instead, so each limit's bars sum across bins to its overall
        # controlling share, and the difference sums to the change in that share.
        shares = engine.controlling_share_by_depth(result, edges, weights=weights,
                                                   within_bin=False)
        geological = engine.controlling_share_by_depth(result, edges, weights=None,
                                                       within_bin=False)
        shares = {name: shares[name] - geological[name] for name in shares}
    else:
        shares = engine.controlling_share_by_depth(result, edges, weights=basis_weights,
                                                   within_bin=not scaled)
    ranked = [name for name, _ in engine.limit_ranking(result, weights=basis_weights)]
    group_of = dict(zip(limit_set.names, limit_set.groups))
    colour_of = limit_colours(limit_set)
    # Stacked horizontal bars rather than a stacked area. Plotly's `stackgroup` accumulates along
    # the *value* axis, which on an inverted depth axis stacks the depths themselves -- the first
    # attempt at this figure ran the y-axis to 20 km. Bars stack along x by construction, so the
    # orientation cannot be got wrong.
    bar_height = float(np.diff(edges).mean())
    fig2 = go.Figure()
    for name in ranked:
        if np.abs(shares[name]).sum() == 0:
            continue
        fig2.add_bar(x=shares[name], y=centres, orientation="h", name=name,
                     width=bar_height, marker_color=colour_of[name],
                     marker_line_width=0,
                     hovertemplate=f"{name}<br>%{{y:.0f}} m TVDSS<br>%{{x:+.0%}}<extra></extra>"
                     if view == DIFFERENCE else
                     f"{name}<br>%{{y:.0f}} m TVDSS<br>%{{x:.0%}}<extra></extra>")
    if view == DIFFERENCE:
        # `relative` puts gains to the right of zero and losses to the left, so a bar that has
        # crossed the line is a mechanism the amplitude promoted or demoted at that depth. The
        # bars sum to zero in every bin, which is the point: a share taken from one limit went
        # to another, and the figure says which.
        span = max(float(np.abs(np.sum([np.clip(v, 0, None) for v in shares.values()], axis=0)).max()),
                   float(np.abs(np.sum([np.clip(v, None, 0) for v in shares.values()], axis=0)).max()),
                   0.02)
        fig2.add_vline(x=0.0, line=dict(color=theme.INK, width=1.4))
        fig2.update_layout(barmode="relative", bargap=0.06,
                           xaxis_title="Change in share of all realisations, given the DHI",
                           xaxis_range=[-span * 1.1, span * 1.1], xaxis_tickformat="+.0%",
                           yaxis_title="Contact depth (m TVDSS)",
                           yaxis=dict(autorange="reversed"), height=560, margin=dict(t=20),
                           legend=dict(orientation="h", y=-0.18))
    else:
        # **One axis for both bases, or the toggle lies.** Auto-scaling each view to its own peak
        # made the geological spread and the DHI's sharp concentration look like the same picture
        # at different labels — 12 % and 22 % both drawn to the right-hand edge. The whole point of
        # switching between them is the height difference, so both are drawn to the taller one.
        def _peak(w):
            return float(np.sum(list(engine.controlling_share_by_depth(
                result, edges, weights=w, within_bin=False).values()), axis=0).max())

        reach = max(_peak(None), _peak(weights)) if (scaled and given_dhi) else (
            float(np.sum(list(shares.values()), axis=0).max()) if shares else 1.0)
        fig2.update_layout(barmode="stack", bargap=0.06,
                           xaxis_title="Share of all realisations, by controlling limit" if scaled
                           else "Share of realisations at this depth, by controlling limit",
                           xaxis_range=[0, reach * 1.05 if scaled else 1.0],
                           xaxis_tickformat=".0%" if not scaled else ".1%",
                           yaxis_title="Contact depth (m TVDSS)",
                           yaxis=dict(autorange="reversed"), height=560, margin=dict(t=20),
                           legend=dict(orientation="h", y=-0.18))
    if view == DIFFERENCE:
        moves = {name: float(shares[name].sum()) for name in ranked}
        gained = max(moves, key=moves.get)
        lost = min(moves, key=moves.get)
        n.plot(fig2, "What the evidence changed in the controlling mechanism. Right of the line "
                     "is a limit the evidence promoted; left is one it demoted. Bars are shares "
                     "of all realisations, so each limit's bars sum across depth to its change in "
                     f"overall controlling share: here {gained} {moves[gained]:+.1%} and {lost} "
                     f"{moves[lost]:+.1%}.\n\n"
                     "This is not the difference of the two views above. Those normalise within "
                     "each depth bin, which conditions on where the contact is, and that is "
                     "almost all a DHI knows; their difference is 0.9 points at most, against 3.9 "
                     "here. A DHI moves the depth distribution, and only through it the mechanism "
                     "mix.\n\n"
                     "This is a claim about geometry, not about elements. The amplitude says "
                     "roughly where the contact is, and some mechanisms explain that depth better "
                     "than others. It is not evidence about which element failed, and the element "
                     "chances on tab 2.0 are unchanged by it.")
    else:
        n.plot(fig2, "The controlling mechanism at each depth, which changes down structure. Hue "
                     "is the risk element in E-POS's colours (salmon charge, blue closure, yellow "
                     "reservoir, green retention); lightness separates the limits within an "
                     "element. Grant (2020) publishes an equivalent as column height control "
                     "statistics; per-element curves built from it appear to be unpublished."
                     + (("\n\nBin height carries the contact distribution here, which is why "
                         f"{GIVEN} and Geological differ visibly: the evidence moves which depths "
                         "are reached far more than it moves the mechanism mix at any one depth."
                         if scaled else
                         f"\n\n{GIVEN} and Geological are near-identical here, by "
                         f"{_within_bin_move(result, edges, weights):.1%} at most, and that is a "
                         "property of the evidence rather than of the control. Normalising each "
                         "bin against itself conditions on contact depth, and the evidence moves "
                         "which depths are reached, not what stops the column at a given depth. "
                         "The box above shows the half it does move.")
                        if given_dhi else ""))

    # ------------------------------------------------------------------ 3 · the chance
    # The third question. Every point on this curve is a prospect chance: the element chance
    # times the chance of a column at least this tall given the elements worked. On the
    # geological tab the first factor is P(G) from tab 2.0; given the DHI it is P(G) updated by
    # the amplitude, which tab 5.0 has already written into the overlay by the time its results
    # sub-tab draws this.
    theme.heading(tab, sub=n.sub, text="3 · Prospect chance against threshold")
    _overlay = st.session_state.get("dhi_overlay") if given_dhi else None
    _p_g_applied = (float(_overlay.get("p_g_given_amplitude", p_geological))
                    if _overlay else p_geological)
    _chance = _p_g_applied * np.asarray(exceed(grid), dtype=float)
    _chance_prior = p_geological * np.asarray(result.exceedance(grid), dtype=float)
    figp = go.Figure()
    if given_dhi:
        figp.add_scatter(x=_chance_prior, y=apex_med + grid, mode="lines",
                         name="geological", line=dict(color="#7d8794", width=2, dash="dash"))
    figp.add_scatter(x=_chance, y=apex_med + grid, mode="lines",
                     name=(theme.evidence_basis() if given_dhi else "geological"),
                     line=dict(color=theme.BASIS_COLOUR[theme.GIVEN_DHI if given_dhi
                                                        else theme.GEOLOGICAL], width=3))
    if h_min > 0:
        figp.add_hline(y=apex_med + h_min, line=dict(color="#C44E52", dash="dash"),
                       annotation_text=f"assessment minimum: {prospect_pos if not given_dhi else _p_g_applied * column_pos:.1%}",
                       annotation_position="bottom right")
    figp.update_layout(xaxis_title="Prospect chance  =  P(G) × P(column ≥ h | G)",
                       xaxis_range=[0, min(1.0, max(_p_g_applied, p_geological, 0.05) * 1.15)],
                       yaxis_title="Contact at least this deep (m TVDSS)",
                       yaxis=dict(autorange="reversed"), height=420, margin=dict(t=20),
                       legend=dict(orientation="h", y=-0.18))
    n.plot(figp, f"The prospect chance at every threshold. Includes the element risk: each "
                 f"point is P(G) = {_p_g_applied:.3f} times the chance of a column at least that "
                 f"tall given the elements worked, so it starts at P(G) at the apex and falls with "
                 f"depth. Read at the assessment minimum it is the headline above; read at any "
                 f"other depth it is the chance of a column reaching that depth. A chance quoted "
                 f"without its threshold is not a number.")

    # ------------------------------------------------------------------ 4 · the well
    # The last question: a well entering the reservoir at a depth finds hydrocarbon if the
    # elements worked and the contact lies below that depth. The entry depth is shared with the
    # per-element reading on the sibling sub-tab through session state, so the two agree.
    theme.heading(tab, sub=n.sub, text="4 · The well")
    from hcwc.ui.depth_risk_tab import DEFAULT_ENTRY_DEPTH_M
    _lo_z, _hi_z = float(result.contact_m.min()), float(result.contact_m.max())
    _open_z = min(max(DEFAULT_ENTRY_DEPTH_M, _lo_z), _hi_z)
    _zkey, _zhead = f"z_entry_{tab}", f"z_entry_headline_{tab}"
    st.session_state.setdefault(_zkey, _open_z)
    st.session_state.setdefault(_zhead, float(st.session_state[_zkey]))

    def _push_entry(zkey=_zkey, zhead=_zhead):
        st.session_state[zkey] = st.session_state[zhead]
        st.session_state[f"z_entry_num_{tab}"] = st.session_state[zhead]

    w1, w2, w3 = st.columns([1, 1, 1])
    z_entry = w1.number_input("Reservoir entry depth (m TVDSS)", _lo_z, _hi_z, step=5.0,
                              key=_zhead, on_change=_push_entry,
                              help="Where the well enters the reservoir. The same depth is used "
                                   "by the per-element reading on the Risk against depth "
                                   "sub-tab.")
    _r_well = float(engine.exceedance(result.contact_m, np.array([z_entry]), weights)[0])
    _p_well = _p_g_applied * _r_well
    w2.metric("P(well finds hydrocarbon)", f"{_p_well:.1%}",
              f"P(G) {_p_g_applied:.3f} × P(contact ≥ {z_entry:,.0f} m | G) {_r_well:.3f}",
              delta_color="off")
    w3.metric("Column at the well, P50", f"{max(pct(50) - z_entry, 0.0):,.0f} m",
              f"P50 contact {pct(50):,.0f} m", delta_color="off")
    st.caption(
        f"P(well) includes the element risk and is read at the entry depth, not at the "
        f"assessment minimum. It is the prospect chance times the chance the contact lies "
        f"below {z_entry:,.0f} m given the elements worked, and is at most the prospect chance. "
        f"The column at the well is the contact depth minus the entry depth; the per-element "
        f"reading and the comparison with an allocated location factor are on the Risk against "
        f"depth sub-tab."
    )

    # ------------------------------------------------------------------ 3 · ranking
    theme.heading(tab, sub=n.sub, text="5 · Limit ranking and sensitivity")
    successes_only = st.toggle(
        "Restrict to realisations above the assessment minimum", value=False,
        key=f"restrict_successes_{tab}",
        help="The two answer different questions. Unrestricted: what controls this closure. "
             "Restricted: what controls it, given that it is worth drilling. Reporting only the "
             "restricted one repeats, one level up, the selection error in the published "
             "column-height statistics.")
    ranking = engine.limit_ranking(result, successes_only=successes_only, weights=weights)
    other = engine.limit_ranking(result, successes_only=not successes_only, weights=weights)
    other_map = dict(other)
    live = [(name, share) for name, share in ranking if share > 0.0005]
    fig3 = go.Figure()
    fig3.add_bar(x=[s for _, s in live][::-1], y=[nm for nm, _ in live][::-1], orientation="h",
                 marker_color=[colour_of[nm] for nm, _ in live][::-1],
                 name="as shown")
    fig3.update_layout(xaxis_title="Share of realisations in which this limit set the contact",
                       height=max(300, 46 * len(live)), margin=dict(t=20), showlegend=False,
                       xaxis_tickformat=".0%")
    n.plot(fig3, "Limits ordered by how often they set the contact. The elicitation effort "
                 "belongs on the top two or three; a limit near zero does not move the answer "
                 "and can stay at a rough value.")

    # ---- the other half of this section's question --------------------------------------
    swing_space = st.radio(
        "Swing measured on", ["Column below apex", "Contact depth"], horizontal=True,
        key=f"tornado_space_{tab}",
        help="The two rank differently and both are valid. The apex barely moves the column and "
             "moves the contact one-for-one, so either alone would hide half the sensitivity.")
    space = "column" if swing_space.startswith("Column") else "depth"
    # **The DHI tornado needs a DHI.** It perturbs the amplitude's own inputs -- pick sigma, the
    # strength, the detection function -- so a posterior built from an offset penetration alone has
    # nothing for it to move, and it raised on `observation.pick_sigma_m` being `None`. The
    # geological tornado is the honest fallback there: what varies on such a prospect is the limits.
    amplitude = given_dhi and posterior.observation is not None
    effects = (sensitivity.dhi_tornado(posterior, space=space) if amplitude
               else sensitivity.tornado(result, space=space))
    centre = (sensitivity.dhi_baseline(posterior, space=space) if amplitude
              else sensitivity.baseline(result, space=space))
    if given_dhi and not amplitude:
        st.caption(
            "This tornado is geological. The updated one perturbs the amplitude's own inputs "
            "(the pick, its σ, the detection function), and this prospect is updated by a "
            "penetration rather than an amplitude, so there is nothing there to perturb. What "
            "moves the answer here is the limits, which is what is ranked below."
        )

    # A bar's width says how much the answer moves; nothing on it says how much evidence that
    # rests on. Unweighted the two are the same, because every tail is a fixed tenth of the run.
    # Weighted they are not: after a sharp DHI update a tail of a thousand realisations can carry
    # an effective sample of twenty-odd, and the bar is drawn exactly as wide either way.
    if amplitude and effects:
        _thin = [e for e in effects[:12] if e.support < MIN_TORNADO_SUPPORT]
        if _thin:
            st.warning(
                f"{len(_thin)} of these bars rest on very little. After reweighting, the "
                f"thinnest carries an effective sample of {min(e.support for e in _thin):,} "
                f"realisations; the tail still holds about a tenth of the run, but most of that "
                f"weight is near zero. Those bars are directions rather than distances: "
                + ", ".join(f"{e.name} ({e.support:,})" for e in _thin[:4])
                + ("…" if len(_thin) > 4 else "")
                + ".\n\nMore realisations do not change this. The update concentrates on fewer "
                "of them, and §5's effective sample size shows the same for the whole posterior."
            )

    if effects:
        shown = effects[:12]
        fig4 = go.Figure()
        for kind, colour, opacity in ((sensitivity.DEPTH_EFFECT, None, 1.0),
                                      (sensitivity.PRESENCE_EFFECT, "#7d8794", 0.75)):
            rows = [e for e in shown if e.kind == kind]
            if not rows:
                continue
            fig4.add_bar(
                y=[f"{e.name} — {e.kind}" for e in rows][::-1],
                x=[e.high - e.low for e in rows][::-1],
                base=[min(e.low, e.high) - centre if False else e.low - centre
                      for e in rows][::-1],
                orientation="h", name=kind,
                marker_color=([colour_of.get(e.name, "#7d8794") for e in rows][::-1]
                              if colour is None else colour),
                marker_opacity=opacity,
                hovertemplate="%{y}<br>low %{base:,.0f} → high %{x:,.0f} m from the mean"
                              "<extra></extra>")
        fig4.add_vline(x=0.0, line=dict(color="#555", width=1.5))
        fig4.update_layout(
            xaxis_title=f"Metres from the mean of {centre:,.0f} m",
            height=max(280, 34 * len(shown)), margin=dict(t=20),
            barmode="overlay", legend=dict(orientation="h", y=-0.22))
        n.plot(fig4,
               f"How much each elicited number moves the mean, which is a different question "
               f"from how often it controls the contact (the figure above). A limit can set the "
               f"contact in most realisations and still be worth no effort, because it always "
               f"applies at nearly the same depth.\n\n"
               f"Each bar is a conditional mean: the average outcome when that input came out in "
               f"its top tenth, against its bottom tenth, taken from the run on screen. The "
               f"slices come from the joint sample, so the bars respect the correlations; "
               f"coupling the apex to the spill changes the spill's bar.\n\n"
               f"Two kinds of bar. Where it applies is the distribution; whether it is there is "
               f"`P(active)`. They are different elicitations, and the longer one says whether "
               f"the question is a depth or a probability. The mean rather than the median, "
               f"because a volume is built from the mean and a median can sit still while the "
               f"tail moves.")
    else:
        st.info("Too few realisations to slice into deciles for a sensitivity.")

    if h_min > 0:
        table = pd.DataFrame([
            {"Limit": name, "Group": group_of[name].value,
             "All realisations": f"{(share if not successes_only else other_map[name]):.1%}",
             "Above the minimum": f"{(other_map[name] if not successes_only else share):.1%}",
             "Shift": f"{((other_map[name] - share) if successes_only else (share - other_map[name])) * -1 if successes_only else (other_map[name] - share):+.1%}"}
            for name, share in ranking if share > 0.0005 or other_map[name] > 0.0005
        ])
        # Optional: it exists only when an assessment minimum is set, so numbering it in the main
        # sequence would renumber everything below whenever that minimum went to zero.
        n.table(table, optional=True,
                caption="The same selection effect the tool identifies in the empirical "
                "literature, one level up: a limit that usually fails the prospect outright is "
                "under-represented among the survivors because it is the most severe. Both "
                "columns are needed; neither alone is the answer.")

    # ------------------------------------------------------------------ group minima
    theme.heading(tab, sub=n.sub, text="6 · By risk element")
    rows = []
    for group in Group:
        gm = result.group_minimum(group)
        finite = gm[np.isfinite(gm)]
        if finite.size == 0:
            continue
        rows.append({"Element": group.value,
                     # Counted with `is`, not through numpy: `np.array` on a str-Enum stringifies each
# member to "Group.CHARGE" and truncates to the array width, so the comparison
# silently returns nonsense rather than failing.
                     "Limits": sum(1 for x in limit_set.groups if x is group),
                     "Binds in": f"{np.isfinite(gm).mean():.0%} of realisations",
                     "Median column when it binds": f"{np.median(finite):,.0f} m",
                     "Controls the contact": f"{sum(s for nm, s in ranking if group_of[nm] is group):.1%}"})
    n.table(pd.DataFrame(rows),
            "Group minima: the shallowest active limit within each element. The per-element "
            "chance-versus-depth curves on the Risk against depth sub-tab are derived from "
            "these.")

    # ------------------------------------------------------------------ 5 · one axis
    theme.heading(tab, sub=n.sub, text="7 · All limits on one axis")
    st.markdown(
        "The competition drawn. A limit that is only sometimes present flattens at its "
        "`P(active)`, which can be read off the right-hand end of its curve. The result is the "
        "lower envelope, because the contact is the shallowest active limit. A curve far to the "
        "right of the bold line is a mechanism that never controlled."
        + (f"\n\nBoth answers are on the axis. The bold red line is the contact "
           f"{theme.evidence_basis()}, the answer on this tab; the dashed blue one is the purely "
           f"geological contact from tab 4.0, kept beside it because the gap between them is "
           f"what the evidence changed. Every thin limit curve is drawn under the same weights, "
           f"which keeps the lower-envelope reading true."
           if given_dhi else ""))
    c1, c2, c3 = st.columns([2, 2, 1])
    space = c1.radio(
        "Show depths as", [limits_mod.DEPTH, limits_mod.COLUMN], horizontal=True,
        key=f"stack_space_{tab}",
        format_func=lambda s_: "m TVDSS" if s_ == limits_mod.DEPTH else "m column below apex",
        help="Display only. The model always competes in column height, because that is the space "
             "where comparing a seal capacity with a spill point means anything.")
    mode = c2.selectbox(
        # **Violin, not the exceedance curves.** Lars's call, 3 Sep 2026, and it is the right one
        # for an opening view: the curves are the analytic reading and reward knowing what a
        # flattening level means, while the violins show where each limit's mass actually sits,
        # which is the question a reader arrives with. Both tabs open the same way — a default that
        # differed between 4.0 and 5.0 would make flipping between them a hunt rather than a
        # comparison.
        "Draw as", limit_stack.MODES, index=limit_stack.MODES.index("Violin"),
        key=f"stack_mode_{tab}",
        help="Exceedance curves read as probabilities; the violins and the histogram show where "
             "each limit lands; points show the individual realisations behind them.")
    every = c3.number_input(
        "Every n-th point", 1, 500, 10, 1, key=f"stack_every_{tab}",
        disabled=mode != "Points",
        help="Thinning, so the cloud stays readable: 10 draws every tenth realisation. Applies "
             "to Points only.")

    apex_med = float(np.median(result.apex_m))
    lo_def, hi_def = limit_stack.default_window(result, space, apex_med,
                                                limit_stack._spill(result, apex_med))
    lo_def, hi_def = float(min(lo_def, hi_def)), float(max(lo_def, hi_def))
    pad = 0.35 * (hi_def - lo_def)
    window = st.slider(  # keyed below, by tab and space
        f"Depth range ({limits_mod.Limit.label_for(space)})",
        float(lo_def - pad), float(hi_def + pad), (lo_def, hi_def), key=f"stack_window_{tab}_{space}",
        help="Defaults to 1 % above the apex and 1 % below the spill point. Several limits carry "
             "tails reaching far below anything the structure contains, and letting those set the "
             "range squeezes the part that matters into the top of the plot.")

    n.plot(limit_stack.figure(result, space=space, mode=mode, window=window,
                              every=int(every), posterior=weights),
           "One axis, five views. Exceedance curves is the analytic view: flattening levels are "
           "`P(active)`, and the bold line is the lower envelope. Violin and half violin show "
           "where each limit's mass sits, better for overlap and worse for reading a "
           "probability. Histogram is the same unsmoothed, for where a kernel would invent a "
           "shape the samples do not have. Points shows the sample itself."
           + ("\n\nThree groups of three kinds. Competing limits are the mechanisms. The "
              "evidence alone is not one of them and is drawn hollow because it is a likelihood, "
              "not a count of realisations; its shape carries the information, not its area. "
              "Result carries both answers, "
              + theme.basis_tag(theme.GEOLOGICAL) + " and " + theme.basis_tag(theme.GIVEN_DHI)
              + ", so the middle group is what turns the first into the second.\n\n"
                "Points is the exception: the evidence lane's markers are drawn from its shape "
                "rather than observed, and the updated result lane is an importance resample, so "
                "a favoured realisation appears more than once."
              if given_dhi else ""))

    # ------------------------------------------------------------------ 6 · trust
    # Geological only. The panel audits the run -- realisation counts, seed
    # repeatability, the correlation projection -- and those are properties of the sample, not of
    # the reweighting. Its DHI check already reports the effective sample size behind the update.
    if not given_dhi:
        # **Reserved now, filled after tab 5.0 has run.** One of these checks reports the effective
        # sample size behind the DHI update, and that posterior is built on tab 5.0 -- which renders
        # *after* this one. Rendering here read the previous frame's posterior, so changing the DHI
        # strength left this panel one interaction behind: it showed 28 % where the answer was
        # 10 %, then 10 % where it was 24 %, silently and with nothing on the page to say so.
        #
        # `st.tabs` returns containers, so where content is written is independent of when. This is
        # the last section of the tab, so deferring it changes nothing about the order a reader
        # sees, and `n` carries the figure numbering regardless of when it is called.
        st.session_state[TRUST_SLOT_KEY] = (st.container(), n, result, tab)


def render_trust_panel() -> None:
    """Fill the slot tab 4.0 reserved, once tab 5.0 has published its posterior.

    Called from ``app.py`` after tab 5.0, and a no-op when tab 4.0 did not run or is showing the
    DHI-updated view, which has its own reporting.
    """
    slot = st.session_state.pop(TRUST_SLOT_KEY, None)
    if slot is None:
        return
    container, n, result, tab = slot
    with container:
        trust_panel.render(n, result, tab=tab,
                           posterior=(st.session_state.get("dhi_posterior")
                                      if st.session_state.get("dhi_on") else None))
