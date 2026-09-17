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
#: it were as well supported as the rest. An effective count rather than a share, unlike
#: :func:`hcwc.core.dhi.min_failures_for_r`, because a tornado bar's support is the ESS of a
#: slice and not a fraction of the trial count: a mean of a hundred effective realisations is
#: coarse but reportable, and twenty-seven is not.
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
    st.subheader(f"HCWC | {theme.evidence_basis()}" if given_dhi else "HCWC | geological")
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
            "these percentiles are the whole distribution rather than its success cases, and "
            "there is no threshold to read a chance at. Method: see 8.1.4."
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
        # The main controls beside the headline (master brief §27): a P50 with the three
        # mechanisms that set it is a result a reader can question; a P50 alone is not.
        _top = sorted(result.controlling_shares(successes_only=True, weights=weights).items(),
                      key=lambda kv: -kv[1])[:3]
        st.caption(
            "Main controls, success cases: "
            + ", ".join(f"{name} {share:.0%}" for name, share in _top)
            + ". Every chance here carries its threshold and the conditioning it was computed "
            "under; the contact percentiles are conditional on the assessment minimum. Method: "
            "see 8.1.4."
        )

    # ------------------------------------------------------------------ 1 · exceedance
    theme.heading(tab, sub=n.sub, text="1 · Where the contact is")
    # ------------------------------------------------------------------ 1 · the competition
    # Lars, 17 Sep 2026: the paper's figure 1, live. Fifty realisations at a time, every active
    # limit's sampled depth as a dot and the shallowest ringed in the controller's colour; a
    # window slider walks the fifty through the whole run in run order. The right panel is the
    # whole distribution, with the fifty shown marked on it, so a reader sees where this window
    # sits in the ten thousand. Draws are the geology's whatever the basis; under the evidence
    # the right panel's bars and curve carry the weights, as every other exhibit on tab 5 does.
    _window = 50
    _start = st.slider(
        "Realisations from", 0, max(result.n - _window, 0), 0, step=_window,
        key=f"competition_window_{tab}",
        help=f"Which {_window} of the {result.n:,} realisations the left panel shows, in the "
             "order the engine drew them. The right panel is always all of them.")
    _idx = np.arange(_start, min(_start + _window, result.n))
    _colours = limit_colours(limit_set)
    _live_names = [name for name, share in engine.limit_ranking(result, weights=weights)
                   if share > 0.0005]
    _apex = result.apex_m[_idx]
    _x = np.arange(_idx.size)

    figc = go.Figure()
    for _name in _live_names:
        _j = limit_set.names.index(_name)
        _on = result.active[_idx, _j]
        if not _on.any():
            continue
        figc.add_scatter(x=_x[_on], y=(_apex + result.sampled_m[_idx, _j])[_on], mode="markers",
                         name=_name, marker=dict(color=_colours.get(_name, "#999"), size=6,
                                                 opacity=0.75),
                         hovertemplate=f"{_name}<br>%{{y:,.0f}} m TVDSS<extra></extra>",
                         xaxis="x", yaxis="y")
    _won = result.contact_m[_idx]
    _ctrl = [limit_set.names[k] for k in result.controller[_idx]]
    figc.add_scatter(x=_x, y=_won, mode="lines", name="the contact, realisation to realisation",
                     line=dict(color="#555", width=1), opacity=0.5, hoverinfo="skip",
                     xaxis="x", yaxis="y")
    figc.add_scatter(x=_x, y=_won, mode="markers", name="shallowest active limit = the contact",
                     # An open symbol takes its stroke from `marker.color`, not `marker.line`.
                     marker=dict(symbol="circle-open", size=13, line=dict(width=2.2),
                                 color=[_colours.get(c, "#111") for c in _ctrl]),
                     customdata=_ctrl,
                     hovertemplate="realisation %{x}<br>contact %{y:,.0f} m<br>"
                                   "controlled by %{customdata}<extra></extra>",
                     xaxis="x", yaxis="y")

    # The whole distribution beside it: bars, the exceedance curve on a top axis, the window's
    # fifty as a rug in their controllers' colours.
    _edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 61)
    _counts, _ = np.histogram(result.contact_m, bins=_edges, weights=weights)
    _total = float(_counts.sum())
    # Grey, not the basis colour: every element hue is taken by a limit, and a blue bar reads as
    # closure. The caption's chip says which basis the bars carry.
    figc.add_bar(y=0.5 * (_edges[:-1] + _edges[1:]), x=_counts / _total if _total else _counts,
                 orientation="h", name="share of realisations per depth bin", opacity=0.55,
                 marker_color="#B8BEC7", marker_line_width=0, xaxis="x2", yaxis="y",
                 hovertemplate="%{y:.0f} m TVDSS<br>%{x:.1%} of realisations<extra></extra>")
    _grid = np.linspace(0.0, float(result.column_m.max()) * 1.02, 400)
    figc.add_scatter(x=exceed(_grid), y=float(np.median(result.apex_m)) + _grid, mode="lines",
                     name="P(contact deeper than this)", line=dict(color="#4C72B0", width=3),
                     xaxis="x3", yaxis="y")
    # The fifty shown, as ticks across the bars in their controllers' colours: where this
    # window sits in the whole, and what set each of its contacts.
    figc.add_scatter(x=np.full(_idx.size, 0.02), y=_won, mode="markers",
                     name=f"the {_idx.size} shown, coloured by controlling limit",
                     # A line symbol is drawn with `marker.line`, so the colour goes there.
                     marker=dict(symbol="line-ew", size=16,
                                 line=dict(width=2.4,
                                           color=[_colours.get(c, "#111") for c in _ctrl])),
                     customdata=_ctrl,
                     hovertemplate="%{y:,.0f} m, %{customdata}<extra></extra>",
                     xaxis="x3", yaxis="y")
    for _p, _dash in ((90, "dot"), (50, "solid"), (10, "dot")):
        figc.add_shape(type="line", xref="x3", yref="y", x0=0, x1=1, y0=pct(_p), y1=pct(_p),
                       line=dict(color="#888", dash=_dash, width=1))
        figc.add_annotation(xref="x3", yref="y", x=1.0, y=pct(_p), text=f"P{_p}",
                            showarrow=False, xanchor="right", yanchor="bottom", font_size=10)
    if h_min > 0:
        _z_min = float(np.median(result.apex_m)) + h_min
        figc.add_shape(type="line", xref="x3", yref="y", x0=0, x1=1, y0=_z_min, y1=_z_min,
                       line=dict(color="#C44E52", dash="dash"))
        figc.add_annotation(xref="x3", yref="y", x=0.0, y=_z_min, text="assessment minimum",
                            showarrow=False, xanchor="left", yanchor="bottom", font_size=10,
                            font_color="#C44E52")
    _peak = float(np.max(_counts / _total)) if _total else 1.0
    # A capacity sampled from the tail can sit hundreds of metres below anything else in the
    # window and would squeeze the competition into a band; the range follows what the shown
    # realisations occupy, and the right panel's curve continues beyond it.
    _shown = np.concatenate([
        (_apex + result.sampled_m[_idx, limit_set.names.index(nm)])[result.active[_idx, limit_set.names.index(nm)]]
        for nm in _live_names] + [_won])
    _y_lo = min(float(np.percentile(_shown, 0.5)), float(result.contact_m.min())) - 10.0
    _y_hi = float(np.percentile(_shown, 97.0)) + 15.0
    figc.update_layout(
        xaxis=dict(domain=[0.0, 0.6], title=f"realisation ({_start:,} to {_idx[-1]:,})"),
        xaxis2=dict(domain=[0.66, 1.0], title="share of realisations per depth bin",
                    tickformat=".0%", range=[0, max(_peak, 1e-6) * 3.0], showgrid=False),
        xaxis3=dict(domain=[0.66, 1.0], overlaying="x2", side="top", range=[0, 1],
                    title="probability the contact is deeper"),
        yaxis=dict(title="Depth (m TVDSS)", range=[_y_hi, _y_lo]),
        height=620, margin=dict(t=48, b=40), barmode="overlay", bargap=0.04,
        legend=dict(orientation="v", x=1.02, y=1.0, xanchor="left"))
    n.plot(figc, f"The competition, realisation by realisation. Left: every active limit's "
                 f"sampled depth in {_idx.size} realisations, the shallowest ringed in the "
                 f"colour of the limit that set it; the slider walks the window through all "
                 f"{result.n:,}. Right: the whole distribution, its exceedance curve on the top "
                 f"axis, and the {_idx.size} shown marked at their depths. Method: see 8.1.3.")

    # `grid` and `apex_med` feed the chance curve in section 3; the exceedance figure that used
    # to sit here was replaced by the competition figure above (Lars, 17 Sep 2026), which carries
    # the same curve on its right-hand panel.
    grid = np.linspace(0.0, float(result.column_m.max()) * 1.02, 400)
    apex_med = float(np.median(result.apex_m))

    # ------------------------------------------------------------------ 2 · which limit controls
    theme.heading(tab, sub=n.sub, text="2 · What controls the contact")
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
    view = GEOLOGICAL
    if given_dhi:
        view = st.radio("Show", (GIVEN, GEOLOGICAL, DIFFERENCE), horizontal=True,
                        key=f"controlling_view_{tab}",
                        help="A DHI cannot say which element failed. It can say which limit set "
                             "the contact, because roughly where the contact sits is evidence "
                             "about which mechanism put it there.")
    # On both tabs, since 15 Sep 2026 (Lars: why was it only on 5.3.2?). Scaled, the bars are
    # shares of all realisations and bin height carries the contact distribution; unscaled, each
    # bin is normalised against itself, the classic diagnostic. Given the DHI the scaling is
    # also what makes the two bases differ visibly: normalising within a bin conditions on
    # contact depth, and the detection function is saturated at its ceiling for every column in
    # every occupied bin, so once the depth is fixed the amplitude has nothing left to
    # discriminate on. What it moves is how many realisations reach each depth.
    scaled = st.checkbox(
        "Scale bars by how many realisations reach each depth", value=True,
        key=f"controlling_scaled_{tab}", disabled=view == DIFFERENCE,
        help="On: bars are shares of all realisations, so bin height carries the contact "
             "distribution and the figure reads as a histogram coloured by controlling limit. "
             "Off: each bin is normalised against itself, so every occupied depth reads as "
             "100 % and the figure shows the mechanism mix at that depth."
             + (" Given the DHI the two bases differ visibly only when scaled."
                if given_dhi else ""))
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
                           legend=dict(orientation="v", x=1.02, y=1.0, xanchor="left"))
    if view == DIFFERENCE:
        moves = {name: float(shares[name].sum()) for name in ranked}
        gained = max(moves, key=moves.get)
        lost = min(moves, key=moves.get)
        n.plot(fig2, "What the evidence changed in the controlling mechanism. Right of the line "
                     "is a limit the evidence promoted; left is one it demoted. Bars are shares "
                     "of all realisations, so each limit's bars sum across depth to its change in "
                     f"overall controlling share: here {gained} {moves[gained]:+.1%} and {lost} "
                     f"{moves[lost]:+.1%}. The evidence moves the depth distribution, and only "
                     "through it the mechanism mix; the element chances on tab 2.0 are unchanged. "
                     "Method: see 8.1.6.")
    else:
        n.plot(fig2, "The controlling mechanism at each depth, which changes down structure. Hue "
                     "is the risk element in E-POS's colours (salmon charge, blue closure, yellow "
                     "reservoir, green retention); lightness separates the limits within an "
                     "element. Method: see 8.1.3."
                     + ("\n\nBars are shares of all realisations, so bin height carries the "
                        "contact distribution and each limit's bars sum across depth to its "
                        "overall share." if scaled else
                        "\n\nEach bin is normalised against itself, so bar length is the "
                        "mechanism mix at that depth and says nothing about how many "
                        "realisations reach it.")
                     + (("\n\nBin height carries the contact distribution here, which is why "
                         f"{GIVEN} and Geological differ visibly: the evidence moves which depths "
                         "are reached far more than it moves the mechanism mix at any one depth."
                         if scaled else
                         f"\n\n{GIVEN} and Geological are near-identical here, by "
                         f"{_within_bin_move(result, edges, weights):.1%} at most, and that is a "
                         "property of the evidence rather than of the control. Normalising each "
                         "bin against itself conditions on contact depth. The box above shows "
                         "the half the evidence does move.")
                        if given_dhi else ""))

    # ------------------------------------------------------------------ 3 · ranking
    theme.heading(tab, sub=n.sub, text="2b · Limit ranking and sensitivity")
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
                "of them, and the effective sample size on tab 5.1 §6 shows the same for the whole "
                "posterior."
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
               f"from how often it controls the contact (the figure above). Each bar is the "
               f"mean outcome with that input in its top tenth against its bottom tenth, from "
               f"the run on screen. Two kinds of bar: where a limit applies is its distribution; "
               f"whether it is there is `P(active)`. Method: see 8.1.9.")
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
                caption="A limit that usually fails the prospect outright is under-represented "
                "among the survivors. Both columns are needed; neither alone is the answer. "
                "Method: see 8.1.3.")

    # ------------------------------------------------------------------ 2c, 2d · folded
    # Two further readings of the controls. Moved behind a fold on 16 Sep 2026 so the default
    # view answers the four questions in order; the figures and their numbers are unchanged
    # and the export report carries them as before.
    # The label names the exhibits inside, so the jump in numbering a reader sees from the last
    # open figure to the next section is accounted for on the fold itself.
    with st.expander(f"Further readings of the controls: by risk element (Table "
                     f"{n.stem}.{n._count + 1}) and all limits on one axis (Figure "
                     f"{n.stem}.{n._count + 2})", expanded=True):
        # ------------------------------------------------------------------ group minima
        theme.heading(tab, sub=n.sub, text="2c · By risk element")
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
        theme.heading(tab, sub=n.sub, text="2d · All limits on one axis")
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

    # ------------------------------------------------------------------ 2e · strength and c
    # Lars, 17 Sep 2026: what other readings of the two DHI judgements would give. The two act
    # differently and the exhibits keep that visible: strength scales the chance and never
    # reshapes the contact, c reshapes the contact and does not touch the chance's first
    # factor; the headline is their product, so it is the one quantity that gets a map. Every
    # scenario is a reweight of the same realisations or a scalar, nothing is re-simulated.
    if (given_dhi and posterior.observation is not None and posterior.observation.seen
            and posterior.detection is not None):
        import dataclasses

        from hcwc.core import dhi as dhi_core
        from hcwc.core import well as well_core
        from hcwc.ui.dhi_tab import well_control

        theme.heading(tab, sub=n.sub, text="2e · What other strength and c readings would give")
        st.markdown(
            "The evidence strength scales the chance and never reshapes the contact; the contact "
            "attribution c reshapes the contact and does not enter the chance's first factor. "
            "The headline chance is their product. Each scenario below is the same realisations "
            "reweighted, or the same curve rescaled. Method: see 8.1.6."
        )
        _obs = posterior.observation
        _det = posterior.detection
        _c_now = float(_obs.p_valid)
        _r_now = float(st.session_state.get("dhi_r_applied", 1.0))
        _p_g_now = dhi_core.p_g_given_strength(p_geological, _r_now)
        _well = well_control()
        _well_w = well_core.likelihood(result, _well) if _well is not None else None

        def _weights_at(c: float) -> np.ndarray:
            w = dhi_core.likelihood(result, _det, dataclasses.replace(
                _obs, p_valid=float(np.clip(c, 0.01, 0.99))))
            return well_core.combine(w, _well_w) if _well_w is not None else w

        def _f_at(w: np.ndarray, columns: np.ndarray) -> np.ndarray:
            return np.asarray(engine.exceedance(result.column_m, columns, w), dtype=float)

        _c_ladder = sorted({0.05, 0.2, 0.36, 0.5, 0.7, 0.9, round(_c_now, 2)})
        _r_ladder = sorted({0.1, 1.0 / 3.0, 1.0, 3.0, 10.0, _r_now})
        _depth = apex_med + grid

        # (a) the contact at other c ------------------------------------------------------------
        fig_c = go.Figure()
        fig_c.add_scatter(x=np.asarray(result.exceedance(grid), dtype=float), y=_depth,
                          mode="lines", name="geological, no evidence",
                          line=dict(color="#9aa3ad", width=2))
        for _c in _c_ladder:
            _w = _weights_at(_c)
            _fc = _f_at(_w, grid)
            _is_now = abs(_c - _c_now) < 0.005
            fig_c.add_scatter(x=_fc, y=_depth, mode="lines",
                              name=f"c = {_c:.2f}" + (" (current)" if _is_now else ""),
                              line=dict(color=theme.BASIS_COLOUR[theme.GIVEN_DHI] if _is_now
                                        else "#C44E52",
                                        width=3.2 if _is_now else 1.4,
                                        dash="solid" if _is_now else "dash"),
                              opacity=1.0 if _is_now else 0.7)
            # Labelled on the shallow flank, where the curves are apart; at 0.5 they meet at
            # the pick and the labels would sit on one another.
            _z85 = float(np.interp(0.85, _fc[::-1], _depth[::-1]))
            fig_c.add_annotation(x=0.85, y=_z85, text=f"c {_c:.2f}", showarrow=False,
                                 xanchor="left", xshift=6, font=dict(size=10, color="#C44E52"),
                                 bgcolor="rgba(255,255,255,0.7)")
        if h_min > 0:
            fig_c.add_hline(y=apex_med + h_min, line=dict(color="#333", dash="dash", width=1),
                            annotation_text="assessment minimum", annotation_position="bottom right")
        fig_c.update_layout(xaxis=dict(title="F(h) = P(column ≥ h | G, evidence)", range=[0, 1.02]),
                            yaxis=dict(title="Contact at least this deep (m TVDSS)",
                                       autorange="reversed"),
                            height=520, margin=dict(t=20),
                            legend=dict(orientation="v", x=1.02, y=1.0, xanchor="left"))
        n.plot(fig_c, f"The contact at other contact attributions. Solid is the current c = "
                      f"{_c_now:.2f}; dashed curves are the same realisations reweighted at other "
                      f"values, each labelled where it crosses 0.85; grey is the geology. As c "
                      f"rises the pick takes over; as it falls the geology returns. Strength does "
                      f"not appear here because it does not move these curves. Method: see 8.1.6.")

        # (b) the chance at other strengths ------------------------------------------------------
        _f_now = _f_at(posterior.weights, grid)
        fig_s = go.Figure()
        for _r in _r_ladder:
            _pg = dhi_core.p_g_given_strength(p_geological, _r)
            _is_now = abs(_r - _r_now) < 1e-9
            _band = dhi_core.strength_bands(_r)[0]
            fig_s.add_scatter(x=_pg * _f_now, y=_depth, mode="lines",
                              name=f"R = {_r:.2g}, P(G | s) = {_pg:.2f}, {_band}"
                                   + (" (current)" if _is_now else ""),
                              line=dict(color="#C44E52" if _is_now else "#7d8794",
                                        width=3.2 if _is_now else 1.4,
                                        dash="solid" if _is_now else "dash"))
            fig_s.add_annotation(x=_pg, y=float(_depth[0]), text=f"R {_r:.2g}", showarrow=False,
                                 yanchor="bottom", yshift=4, font=dict(size=10, color="#7d8794"))
        if h_min > 0:
            fig_s.add_hline(y=apex_med + h_min, line=dict(color="#333", dash="dash", width=1),
                            annotation_text="assessment minimum", annotation_position="bottom right")
        fig_s.update_layout(xaxis=dict(title="prospect chance = P(G | s) × F(h), at the current c",
                                       range=[0, 1.02]),
                            yaxis=dict(title="Contact at least this deep (m TVDSS)",
                                       autorange="reversed"),
                            height=520, margin=dict(t=30),
                            legend=dict(orientation="v", x=1.02, y=1.0, xanchor="left"))
        n.plot(fig_s, f"The chance against depth at other evidence strengths, at the current c. "
                      f"Solid is the current R = {_r_now:.2f}; each dashed curve is the same "
                      f"shape scaled by P(G | s), labelled at the apex with its R. Strength moves "
                      f"the whole curve and never its shape; the single-channel ceiling is 10 : 1 "
                      f"either way. Method: see 8.1.6.")

        # (c) the quantities that vary with both, on a map ---------------------------------------
        # Only a product of P(G | s) with a reading of the contact varies with both inputs; the
        # contact's own percentiles, spread and effective sample size depend on c alone and are
        # drawn against c in (d). The map offers the products, with the well's chance first
        # because it varies with both even at a minimum every realisation clears.
        from hcwc.ui.depth_risk_tab import DEFAULT_ENTRY_DEPTH_M

        _cs = np.linspace(0.05, 0.95, 19)
        _rs = np.logspace(-1, 1, 25)
        _w_by_c = [_weights_at(c) for c in _cs]
        _pgs = np.array([dhi_core.p_g_given_strength(p_geological, r) for r in _rs])
        _z_well_now = float(st.session_state.get(f"z_entry_{tab}", DEFAULT_ENTRY_DEPTH_M))
        _MAP_WELL = "P(well) at the entry depth"
        _MAP_HMIN = "prospect chance at the assessment minimum"
        _MAP_DEPTH = "chance of a contact at least as deep as a chosen depth"
        m1, m2 = st.columns([3, 1])
        _map_what = m1.radio("Map shows", (_MAP_WELL, _MAP_HMIN, _MAP_DEPTH), horizontal=True,
                             key=f"map_quantity_{tab}",
                             help="Each is P(G | strength) times a reading of the updated "
                                  "contact distribution, so each varies with both inputs. The "
                                  "contact's own percentiles depend on c alone and are drawn "
                                  "against c below.")
        _z_chosen = m2.number_input("Chosen depth (m TVDSS)", float(result.contact_m.min()),
                                    float(result.contact_m.max()),
                                    float(round(pct(50), 0)), 5.0, key=f"map_depth_{tab}",
                                    disabled=_map_what != _MAP_DEPTH)
        if _map_what == _MAP_HMIN:
            _z_read, _read_now = None, float(posterior.pos())
            _col_at = np.array([h_min])
        elif _map_what == _MAP_WELL:
            _z_read = _z_well_now
            _col_at = None
        else:
            _z_read = float(_z_chosen)
            _col_at = None
        if _col_at is not None:
            _f_read = np.array([float(_f_at(w, _col_at)[0]) for w in _w_by_c])
        else:
            # A depth is a fixed surface: read the share of realisations whose contact lies at or
            # below it, apex drawn per realisation, as section 4 does for the well.
            _f_read = np.array([float(np.sum(w[result.contact_m >= _z_read]) / np.sum(w))
                                for w in _w_by_c])
            _read_now = float(np.sum(posterior.weights[result.contact_m >= _z_read])
                              / np.sum(posterior.weights))
        _zmap = np.outer(_f_read, _pgs)   # rows c, columns R
        _now_value = _p_g_now * _read_now
        _map_title = {_MAP_HMIN: "prospect chance at h_min",
                      _MAP_WELL: f"P(well) at {_z_well_now:,.0f} m",
                      _MAP_DEPTH: f"chance of a contact ≥ {_z_read or 0:,.0f} m"}[_map_what]
        fig_m = go.Figure()
        fig_m.add_contour(x=np.log10(_rs), y=_cs, z=_zmap, colorscale="Blues",
                          contours=dict(showlabels=True, labelfont=dict(size=10),
                                        labelformat=".0%"),
                          colorbar=dict(title=_map_title, tickformat=".0%", x=1.02),
                          hovertemplate="R = 10^%{x:.2f}<br>c = %{y:.2f}<br>%{z:.1%}"
                                        "<extra></extra>")
        fig_m.add_scatter(x=[np.log10(max(_r_now, 1e-6))], y=[_c_now], mode="markers",
                          name="current setting",
                          marker=dict(color="#C44E52", size=12, symbol="x",
                                      line=dict(width=2)), showlegend=False)
        fig_m.add_annotation(x=np.log10(max(_r_now, 1e-6)), y=_c_now,
                             text=f"current: {_now_value:.1%}",
                             showarrow=False, xanchor="left", xshift=10, yanchor="bottom",
                             bgcolor="rgba(255,255,255,0.85)", font=dict(size=11, color="#333"))
        _ticks = [0.1, 1.0 / 3.0, 1.0, 3.0, 10.0]
        fig_m.update_layout(
            xaxis=dict(title="evidence strength, as the likelihood ratio R (log scale)",
                       tickmode="array", tickvals=[np.log10(t) for t in _ticks],
                       ticktext=["1/10", "1/3", "1", "3", "10"]),
            yaxis=dict(title="contact attribution c"), height=480, margin=dict(t=20))
        n.plot(fig_m, f"{_map_title[0].upper() + _map_title[1:]} over both judgements: "
                      f"P(G | s) across, from R = 1/10 to 10, and c down, from 0.05 to 0.95; "
                      f"the cross is the current setting. Each map is P(G | s) times a reading "
                      f"of the updated contact distribution, so contours run diagonally where "
                      f"both inputs bite and vertically where the reading is 1 whatever c is, "
                      f"which the headline is at a minimum every realisation clears. Method: "
                      f"see 8.1.6.")

        # (d) what c alone does to the contact ---------------------------------------------------
        # Six readings against c, each with the geological value dashed where there is one and
        # the current c marked with its value. Strength does not enter any of them.
        from plotly.subplots import make_subplots

        _keep = result.above_minimum
        if not _keep.any():
            # Every reading below is over the success cases, and there are none at this
            # minimum; the headline said so at the top of the tab.
            st.info("No realisation reaches the assessment minimum, so there are no success "
                    "cases to read the contact's percentiles, spread or displacement from. A "
                    "lower minimum on tab 2.0 restores them.")
            _keep = None
        _z_keep = result.contact_m[_keep] if _keep is not None else np.array([])
        _col_keep = result.column_m[_keep] if _keep is not None else np.array([])
        _q = np.array([90.0, 50.0, 10.0])
        if _keep is not None:
            _g_pcts = engine.weighted_percentiles(_z_keep, None, _q)
            _g_cols = engine.weighted_percentiles(_col_keep, None, _q)
            _g_mean = float(np.mean(_z_keep))
            _g_spread = float(_g_pcts[2] - _g_pcts[0])
            _qgrid = np.linspace(1.0, 99.0, 99)
            _g_quantiles = engine.weighted_percentiles(_z_keep, None, _qgrid)
            rows = {"P50": [], "mean": [], "spread": [], "spread_ratio": [], "col_ratio": [],
                    "displacement": [], "ess": []}
            for _w in _w_by_c:
                _wk = _w[_keep]
                _pcts = engine.weighted_percentiles(_z_keep, _wk, _q)
                _cols = engine.weighted_percentiles(_col_keep, _wk, _q)
                rows["P50"].append(float(_pcts[1]))
                rows["mean"].append(float(np.average(_z_keep, weights=_wk)))
                rows["spread"].append(float(_pcts[2] - _pcts[0]))
                rows["spread_ratio"].append(float((_pcts[2] - _pcts[0]) / max(_g_spread, 1e-9)))
                rows["col_ratio"].append(float(_cols[2] / max(_cols[0], 1e-9)))
                rows["displacement"].append(float(np.mean(np.abs(
                    engine.weighted_percentiles(_z_keep, _wk, _qgrid) - _g_quantiles))))
                rows["ess"].append(float(_w.sum() ** 2 / np.sum(_w ** 2)))
            _panels = [
                ("contact P50 and mean (m TVDSS)", [("P50", rows["P50"], float(_g_pcts[1])),
                                                     ("mean", rows["mean"], _g_mean)], True),
                ("P90–P10 spread (m)", [("spread", rows["spread"], _g_spread)], False),
                ("spread ratio, DHI / geological", [("ratio", rows["spread_ratio"], 1.0)], False),
                ("P10 / P90 column ratio", [("ratio", rows["col_ratio"],
                                             float(_g_cols[2] / max(_g_cols[0], 1e-9)))], False),
                ("displacement from the geology (m)", [("mean |Δquantile|", rows["displacement"],
                                                        None)], False),
                ("effective sample size", [("ESS", rows["ess"], float(result.n))], False),
            ]
            fig_d = make_subplots(rows=2, cols=3, subplot_titles=[t for t, _, _ in _panels],
                                  vertical_spacing=0.16, horizontal_spacing=0.08)
            for _k, (_title, _series, _reversed) in enumerate(_panels):
                _r, _cc = divmod(_k, 3)
                _r += 1; _cc += 1
                for _j, (_label, _ys, _geo) in enumerate(_series):
                    _colour = "#C44E52" if _j == 0 else "#E07B7B"
                    fig_d.add_scatter(x=_cs, y=_ys, mode="lines", name=_label,
                                      line=dict(color=_colour, width=2.5,
                                                dash="solid" if _j == 0 else "dot"),
                                      showlegend=False, row=_r, col=_cc)
                    if _geo is not None:
                        fig_d.add_hline(y=_geo, line=dict(color="#9aa3ad", dash="dash", width=1),
                                        row=_r, col=_cc)
                    # The current c as a point on the line, labelled with its value.
                    _yv = float(np.interp(_c_now, _cs, _ys))
                    _fmt = (f"{_yv:,.0f}" if abs(_yv) >= 100 else f"{_yv:.2f}")
                    fig_d.add_scatter(x=[_c_now], y=[_yv], mode="markers+text",
                                      text=[f"{_label} {_fmt}"], textposition="top right",
                                      textfont=dict(size=10, color=_colour),
                                      marker=dict(color=_colour, size=9,
                                                  line=dict(color="white", width=1.5)),
                                      showlegend=False, hoverinfo="skip", row=_r, col=_cc)
                fig_d.add_vline(x=_c_now, line=dict(color="#333", dash="dash", width=1),
                                row=_r, col=_cc)
                if _reversed:
                    fig_d.update_yaxes(autorange="reversed", row=_r, col=_cc)
            fig_d.update_xaxes(title_text="c", row=2)
            fig_d.update_layout(height=620, margin=dict(t=40, b=40), showlegend=False)
            n.plot(fig_d, f"What c alone does to the contact, against c with the current "
                          f"{_c_now:.2f} marked on every line: the P50 and mean (success cases); "
                          f"the P90–P10 spread and its ratio to the geological spread; the P10 / P90 "
                          f"ratio of the column height; the displacement from the geology, the mean "
                          f"absolute shift of the contact quantiles in metres; and the effective "
                          f"sample size. Dashed grey is the geological value where there is one. "
                          f"None of the six depends on the evidence strength. Method: see 8.1.6.")


        # (e) the contact over depth and c, as one surface ---------------------------------------
        # The family of (a) drawn as a map: c across, depth down, colour and contours are
        # F(h | G, evidence). Where the pick takes hold reads as the contours bending toward
        # the picked depth as c rises.
        _surface_c = np.array([_f_at(w, grid) for w in _w_by_c]).T   # rows depth, columns c
        fig_e = go.Figure()
        fig_e.add_contour(x=_cs, y=_depth, z=_surface_c, colorscale="Blues",
                          contours=dict(showlabels=True, labelfont=dict(size=10),
                                        labelformat=".1f", start=0.1, end=0.9, size=0.1),
                          colorbar=dict(title="F(h | G, evidence)", x=1.02),
                          hovertemplate="c = %{x:.2f}<br>%{y:,.0f} m<br>F = %{z:.2f}"
                                        "<extra></extra>")
        fig_e.add_vline(x=_c_now, line=dict(color="#C44E52", width=2),
                        annotation_text=f"current c {_c_now:.2f}", annotation_position="top")
        for _p, _dash in ((90, "dot"), (50, "solid"), (10, "dot")):
            _zg = float(result.percentiles(float(_p))[0])
            if np.isfinite(_zg):
                fig_e.add_hline(y=_zg, line=dict(color="#9aa3ad", dash=_dash, width=1),
                                annotation_text=f"geological P{_p}",
                                annotation_position="right")
        if posterior.observation.contact_m is not None:
            fig_e.add_hline(y=float(posterior.observation.contact_m),
                            line=dict(color="#B45309", dash="dash", width=1.2),
                            annotation_text="picked contact", annotation_position="left")
        fig_e.update_layout(xaxis=dict(title="contact attribution c"),
                            yaxis=dict(title="Contact at least this deep (m TVDSS)",
                                       autorange="reversed"),
                            height=520, margin=dict(t=30))
        n.plot(fig_e, f"The updated contact over depth and c, as one surface: the family of "
                      f"the figure above with c across and depth down, coloured and contoured by "
                      f"F(h | G, evidence). At small c the contours are the geology's; as c "
                      f"rises they bend toward the picked contact. The red line is the current "
                      f"c, grey the geological P90 / P50 / P10, orange the pick. Strength does not "
                      f"enter. Method: see 8.1.6.")

        # (f) the chance over depth and R, at the current c --------------------------------------
        _surface_r = np.outer(_f_now, _pgs)   # rows depth, columns R
        fig_f = go.Figure()
        fig_f.add_contour(x=np.log10(_rs), y=_depth, z=_surface_r, colorscale="Reds",
                          contours=dict(showlabels=True, labelfont=dict(size=10),
                                        labelformat=".0%", start=0.1, end=0.9, size=0.1),
                          colorbar=dict(title="prospect chance", tickformat=".0%", x=1.02),
                          hovertemplate="R = 10^%{x:.2f}<br>%{y:,.0f} m<br>%{z:.1%}"
                                        "<extra></extra>")
        fig_f.add_vline(x=np.log10(max(_r_now, 1e-6)), line=dict(color="#C44E52", width=2),
                        annotation_text=f"current R {_r_now:.2f}", annotation_position="top")
        if h_min > 0:
            fig_f.add_hline(y=apex_med + h_min, line=dict(color="#333", dash="dash", width=1),
                            annotation_text="assessment minimum", annotation_position="right")
        fig_f.add_hline(y=_z_well_now, line=dict(color="#0369A1", dash="dot", width=1.2),
                        annotation_text="well entry", annotation_position="left")
        fig_f.update_layout(
            xaxis=dict(title="evidence strength, as R (log scale)", tickmode="array",
                       tickvals=[np.log10(t) for t in _ticks],
                       ticktext=["1/10", "1/3", "1", "3", "10"]),
            yaxis=dict(title="Contact at least this deep (m TVDSS)", autorange="reversed"),
            height=520, margin=dict(t=30))
        n.plot(fig_f, f"The prospect chance over depth and evidence strength, at the current "
                      f"c = {_c_now:.2f}: the fan of the strength figure as a surface. Every "
                      f"column is the same curve scaled by P(G | s), so the contours are the "
                      f"depth curve's shape stretched sideways; the assessment minimum and the "
                      f"well entry are the two depths the chance is quoted at. Method: see "
                      f"8.1.6.")

        # (g) the update's net effect and leverage -----------------------------------------------
        # The geological reference for the quantity on the map: P(G) times the geological
        # reading, one number over the whole plane. The difference says where the evidence
        # helps and hurts; the ratio says by what factor.
        if _col_at is not None:
            _geo_read = float(result.exceedance(_col_at)[0])
        else:
            _geo_read = float(np.mean(result.contact_m >= _z_read))
        _geo_value = p_geological * _geo_read
        _diff = _zmap - _geo_value
        with np.errstate(divide="ignore", invalid="ignore"):
            _ratio = np.where(_geo_value > 0, _zmap / max(_geo_value, 1e-12), np.nan)
        _lim = float(np.nanmax(np.abs(_diff))) or 0.01
        fig_h = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.12,
                              subplot_titles=(f"net effect: {_map_title} minus geological "
                                              f"({_geo_value:.1%})",
                                              f"leverage: {_map_title} divided by geological"))
        fig_h.add_contour(x=np.log10(_rs), y=_cs, z=_diff, colorscale="RdBu", zmid=0.0,
                          zmin=-_lim, zmax=_lim,
                          contours=dict(showlabels=True, labelfont=dict(size=9),
                                        labelformat="+.0%"),
                          colorbar=dict(title="points", tickformat="+.0%", x=0.44),
                          hovertemplate="R = 10^%{x:.2f}<br>c = %{y:.2f}<br>%{z:+.1%}"
                                        "<extra></extra>", row=1, col=1)
        fig_h.add_contour(x=np.log10(_rs), y=_cs, z=np.log10(_ratio), colorscale="RdBu",
                          zmid=0.0,
                          contours=dict(showlabels=False),
                          colorbar=dict(title="factor", x=1.02, tickmode="array",
                                        tickvals=[np.log10(v) for v in (0.25, 0.5, 1, 2, 4)],
                                        ticktext=["×0.25", "×0.5", "×1", "×2", "×4"]),
                          hovertemplate="R = 10^%{x:.2f}<br>c = %{y:.2f}<br>×%{customdata:.2f}"
                                        "<extra></extra>", customdata=_ratio, row=1, col=2)
        for _k in (1, 2):
            fig_h.add_scatter(x=[np.log10(max(_r_now, 1e-6))], y=[_c_now], mode="markers",
                              marker=dict(color="#111", size=10, symbol="x", line=dict(width=2)),
                              showlegend=False, hoverinfo="skip", row=1, col=_k)
            fig_h.update_xaxes(tickmode="array", tickvals=[np.log10(t) for t in _ticks],
                               ticktext=["1/10", "1/3", "1", "3", "10"],
                               title_text="R (log scale)", row=1, col=_k)
        fig_h.update_yaxes(title_text="contact attribution c", row=1, col=1)
        fig_h.update_layout(height=440, margin=dict(t=50, b=40))
        n.plot(fig_h, f"What the evidence is worth, for the quantity on the map above. Left: the "
                      f"updated value minus the geological one, {_geo_value:.1%}, in points; the "
                      f"white contour is where the evidence neither helps nor hurts. Right: the "
                      f"same as a factor, ×1 where it is neutral. Both are the map above shifted "
                      f"and scaled, so the shapes agree; the labels are what change. The cross is "
                      f"the current setting. Method: see 8.1.6.")

    # ------------------------------------------------------------------ 3 · the chance
    # The third question. Every point on this curve is a prospect chance: the element chance
    # times the chance of a column at least this tall given the elements worked. On the
    # geological tab the first factor is P(G) from tab 2.0; given the DHI it is P(G) updated by
    # the amplitude, which tab 5.0 has already written into the overlay by the time its results
    # sub-tab draws this.
    theme.heading(tab, sub=n.sub, text="3 · How the chance changes with depth")
    _overlay = st.session_state.get("dhi_overlay") if given_dhi else None
    _p_g_applied = (float(_overlay.get("p_g_given_amplitude", p_geological))
                    if _overlay else p_geological)
    _f = np.asarray(exceed(grid), dtype=float)
    _chance = _p_g_applied * _f
    _chance_prior = p_geological * np.asarray(result.exceedance(grid), dtype=float)

    # Lars, 17 Sep 2026: the chance curve alone is F(h) scaled by one number, so the figure now
    # carries the three things that make the reading: the controlling mechanism per depth bin
    # (shares of all realisations, as 4.1.2 scaled), F(h) in blue with the contact's P90, P50,
    # P10 and mean marked on it, and the prospect chance in red on the same 0-1 axis, so the
    # vertical gap between the two curves is P(G) made visible.
    figp = go.Figure()
    _edges7 = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 41)
    _centres7 = 0.5 * (_edges7[:-1] + _edges7[1:])
    _shares7 = engine.controlling_share_by_depth(result, _edges7, weights=weights,
                                                 within_bin=False)
    _peak7 = 0.0
    _stack = np.zeros(len(_centres7))
    for _name in ranked:
        if _name not in _shares7 or float(np.sum(_shares7[_name])) <= 0.0005:
            continue
        figp.add_bar(y=_centres7, x=_shares7[_name], orientation="h", name=_name,
                     marker_color=colour_of[_name], marker_line_width=0, opacity=0.85,
                     xaxis="x2", yaxis="y", legendgroup="limits", legendgrouptitle_text="controlling limit",
                     hovertemplate=f"{_name}<br>%{{y:.0f}} m: %{{x:.1%}} of realisations"
                                   "<extra></extra>")
        _stack = _stack + np.asarray(_shares7[_name], dtype=float)
    _peak7 = float(_stack.max()) if _stack.size else 1.0

    if given_dhi:
        figp.add_scatter(x=_chance_prior, y=apex_med + grid, mode="lines",
                         name="prospect chance, geological",
                         line=dict(color="#7d8794", width=2, dash="dash"))
    figp.add_scatter(x=_f, y=apex_med + grid, mode="lines",
                     name="F(h) = P(column ≥ h | G), conditional",
                     line=dict(color="#4C72B0", width=3))
    figp.add_scatter(x=_chance, y=apex_med + grid, mode="lines",
                     name=f"prospect chance = P(G) × F(h), P(G) = {_p_g_applied:.2f}"
                          + (f", {theme.evidence_basis()}" if given_dhi else ""),
                     line=dict(color="#C44E52", width=3))

    # The contact's percentiles and mean, read on the conditional curve: success cases, the
    # same numbers as the headline metrics.
    _keep = result.above_minimum
    _w_keep = None if weights is None else np.asarray(weights, dtype=float)[_keep]
    _mean_z = (float(np.average(result.contact_m[_keep], weights=_w_keep))
               if _keep.any() else float("nan"))
    _marks = [(f"P{_p}", pct(_p)) for _p in (90, 50, 10)] + [("mean", _mean_z)]
    _mx, _my, _mt = [], [], []
    for _label, _z in _marks:
        if not np.isfinite(_z):
            continue
        _fx = float(np.interp(_z - apex_med, grid, _f))
        _mx.append(_fx); _my.append(_z); _mt.append(f"{_label} {_z:,.0f} m")
    # P50 and the mean sit a few metres apart on most prospects, so their labels take
    # opposite sides of the point.
    _pos = {"P90": "middle right", "P50": "top right", "P10": "middle right",
            "mean": "bottom right"}
    figp.add_scatter(x=_mx, y=_my, mode="markers+text", text=_mt,
                     textposition=[_pos[t.split()[0]] for t in _mt],
                     name="contact P90 / P50 / P10 and mean, success cases",
                     marker=dict(color="#4C72B0", size=9,
                                 symbol=["diamond" if t.startswith("mean") else "circle"
                                         for t in _mt],
                                 line=dict(color="white", width=1.5)),
                     textfont=dict(size=11, color="#4C72B0"),
                     hovertemplate="%{text}<br>F = %{x:.2f}<extra></extra>")

    if h_min > 0:
        figp.add_hline(y=apex_med + h_min, line=dict(color="#C44E52", dash="dash"),
                       annotation_text=f"assessment minimum: chance {prospect_pos if not given_dhi else _p_g_applied * column_pos:.1%}",
                       annotation_position="bottom right")
    figp.update_layout(
        barmode="stack", bargap=0.05,
        xaxis=dict(title="probability, on one axis: conditional F(h) and the prospect chance",
                   range=[0, 1.02]),
        xaxis2=dict(overlaying="x", side="top", range=[0, max(_peak7, 1e-6) * 3.0],
                    showgrid=False, tickformat=".0%",
                    title="share of all realisations per depth bin, by controlling limit",
                    title_font_size=11, tickfont_size=10),
        yaxis=dict(title="Contact at least this deep (m TVDSS)", autorange="reversed"),
        height=620, margin=dict(t=58),
        legend=dict(orientation="v", x=1.02, y=1.0, xanchor="left"))
    n.plot(figp, f"The chance against depth, and what makes it. Blue is F(h), the chance of a "
                 f"column at least this tall given the elements worked, with the contact's "
                 f"P90, P50, P10 and mean marked on it (success cases). Red is the prospect "
                 f"chance, P(G) = {_p_g_applied:.3f} times the blue curve; the gap between the "
                 f"two is the element risk. The bars are the controlling limit per depth bin as "
                 f"shares of all realisations, the scaled view of 4.1.2. Read at the assessment "
                 f"minimum the red curve is the headline above; read at any other depth it is "
                 f"the chance of a column reaching that depth. Method: see 8.1.4.")

    # ------------------------------------------------------------------ 4 · the well
    # The last question: a well entering the reservoir at a depth finds hydrocarbon if the
    # elements worked and the contact lies below that depth. The entry depth is shared with the
    # per-element reading on the sibling sub-tab through session state, so the two agree.
    theme.heading(tab, sub=n.sub, text="4 · The assessment minimum and the well")
    if h_min > 0:
        st.markdown(
            f"`Prospect POS = P(G) × P(column ≥ h | G)` = "
            f"{p_geological:.3f} × {column_pos:.3f} = {prospect_pos:.3f}. `P(G)` is the element "
            f"chance from tab 2.0; `P(column ≥ h | G)` is read off the exceedance curve in "
            f"section 1 at the assessment minimum, from the competing limits, conditional on "
            f"the elements having worked."
        )
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
        f"assessment minimum; it is at most the prospect chance. The column at the well is the "
        f"contact depth minus the entry depth. The per-element reading is on the Risk against "
        f"depth sub-tab. Method: see 8.1.4."
    )

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
