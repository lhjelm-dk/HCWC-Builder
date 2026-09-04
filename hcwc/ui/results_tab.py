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

    st.subheader("Results | given the DHI" if given_dhi else "Results")
    if given_dhi:
        theme.basis_banner(
            theme.GIVEN_DHI,
            "Every figure below carries the amplitude evidence. The purely geological versions of "
            "the same figures are on tab 4.0, in the same order — they are a different "
            "distribution, not a different view of this one.")
    else:
        theme.basis_banner(
            theme.GEOLOGICAL,
            "The competing limits alone. If this prospect has a DHI, its updated results are on "
            "tab 5.0 and are a different distribution — not a different view of this one.")

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
            "**The contact distribution is still real; only the chance is not.** With no minimum "
            "every realisation counts as a success, so these percentiles are the whole "
            "distribution rather than its success cases, and there is no threshold for a chance to "
            "be read at. Everything below this point is unaffected — it is the *chance* that needs "
            "the minimum, not the contact."
        )
    else:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(f"Prospect POS at h ≥ {h_min:.0f} m", f"{prospect_pos:.1%}",
                  "the reportable number", delta_color="off")
        m2.metric(f"P(column ≥ {h_min:.0f} m | G)", f"{column_pos:.1%}",
                  "conditional — this tab only", delta_color="off")
        for col, p in ((m3, 90), (m4, 50), (m5, 10)):
            col.metric(f"Contact P{p}", f"{pct(p):,.0f} m",
                       "success cases only", delta_color="off")
        st.markdown(
            f"**The prospect chance is a product of two things, and this tab computes only one of "
            f"them.**\n\n"
            f"`Prospect POS = P(G) × P(column ≥ h | G)` = "
            f"**{p_geological:.3f} × {column_pos:.3f} = {prospect_pos:.3f}**\n\n"
            f"`P(G)` is the **geological POS** from tab 2.0 — the product of the four element "
            f"chances, the chance the prospect works *at all*. It is E-POS's headline number and "
            f"it says nothing about how tall the column is. `P(column ≥ h | G)` is everything on "
            f"this tab: the competing limits, **conditional on the elements having worked**. A "
            f"reservoir that is not there has no contact to distribute."
        )
        st.caption(
            "**Every chance here carries its threshold, and the conditioning it was computed "
            "under.** The contact percentiles are *success cases only* — conditional, in the sense "
            "WellVolPOS settled: the distribution is the primary object and the chance multiplies "
            "it, never the other way round. Quoting a chance from one threshold beside a volume "
            "from another is the error tab 6.0 is written to prevent, and quoting the conditional "
            "term as though it were the prospect chance is the same error one level up."
        )

    # ------------------------------------------------------------------ 1 · exceedance
    theme.heading(tab, sub=n.sub, text="1 · Where is the contact?")
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
        basis = theme.GIVEN_DHI if given_dhi else theme.GEOLOGICAL
        edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 61)
        counts, _ = np.histogram(result.contact_m, bins=edges, weights=weights)
        total = float(counts.sum())
        fig.add_bar(y=0.5 * (edges[:-1] + edges[1:]), x=counts / total if total else counts,
                    orientation="h", xaxis="x2", name=f"contacts — {basis}", opacity=0.45,
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
    n.plot(fig, "The exceedance curve `F(h) = P(column ≥ h)`, on the depth axis. Depth on y, "
                "inverted, m TVDSS — the convention throughout this tool and WellVolPOS. **This "
                "curve is the risk output**; POS at any threshold is a reading of it.")

    # ------------------------------------------------------------------ 2 · which limit controls
    theme.heading(tab, sub=n.sub, text="2 · Which limit controls the contact?")
    edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 26)
    centres = 0.5 * (edges[:-1] + edges[1:])

    # **The DHI is in this figure and was invisible in it.** Drawn on its own the updated shares
    # look like any other stacked bar; the only way to see what the amplitude did was to hold the
    # geological twin on tab 4.0 in your head and flip between tabs. Three views of one figure fixes
    # that, and the third is the one worth having — the difference is where the finding is.
    GIVEN, GEOLOGICAL, DIFFERENCE = "Given the DHI", "Geological", "What the DHI changed"
    view, scaled = GEOLOGICAL, False
    if given_dhi:
        view = st.radio("Show", (GIVEN, GEOLOGICAL, DIFFERENCE), horizontal=True,
                        key=f"controlling_view_{tab}",
                        help="A DHI cannot tell you which element failed. It can tell you which "
                             "limit set the contact, because knowing roughly where the contact "
                             "sits is evidence about which mechanism put it there.")
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
                 "against itself — the classic diagnostic, and a view a DHI cannot move.")
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
        n.plot(fig2, "**What the amplitude did to the controlling mechanism.** Right of the line "
                     "is a limit the DHI promoted; left is one it demoted. Bars are shares of "
                     "*all* realisations, so each limit's bars sum across depth to its change in "
                     "overall controlling share — here "
                     f"**{gained} {moves[gained]:+.1%}** and **{lost} {moves[lost]:+.1%}**.\n\n"
                     "**Why this is not the difference of the two views above.** Those normalise "
                     "within each depth bin, which conditions on where the contact is — and that "
                     "is almost the whole of what a DHI knows. Subtract them and you get nothing: "
                     "0.9 points at most, against 3.9 here. A DHI moves the *depth distribution*, "
                     "and only through it the mechanism mix.\n\n"
                     "This is a claim about **geometry**, not about elements. The amplitude says "
                     "roughly where the contact is and some mechanisms explain that depth better "
                     "than others; it is not evidence about which element failed, and the element "
                     "chances on tab 2.0 are untouched by it.")
    else:
        n.plot(fig2, "The diagnostic the argmin bookkeeping buys, and the reason for keeping it: "
                     "**the controlling mechanism changes as you step down structure.** Hue is the "
                     "risk element, in E-POS's colours — salmon charge, blue closure, yellow "
                     "reservoir, green retention — and lightness separates the limits within an "
                     "element. Grant (2020) publishes an equivalent as \"column height control "
                     "statistics\"; the per-element curves built from it are, as far as I can "
                     "find, unpublished."
                     + (("\n\n**Bin height carries the contact distribution here**, which is why "
                         "*Given the DHI* and *Geological* differ visibly: the amplitude moves "
                         "which depths are reached, by up to ten points, far more than it moves "
                         "the mechanism mix at any one depth."
                         if scaled else
                         "\n\n**In this view *Given the DHI* and *Geological* are "
                         f"indistinguishable — they differ by {_within_bin_move(result, edges, weights):.1%} "
                         "at most — and that is a property of the evidence, not a broken control.** "
                         "Normalising each bin against itself conditions on contact depth, and the "
                         "detection function sits at its ceiling for every column in every "
                         "occupied bin, so with the depth fixed the amplitude has nothing left to "
                         "discriminate on. It moves *which depths are reached*, not *what stops "
                         "the column once you are at one*. **Tick the box above** to see the "
                         "half it does move.")
                        if given_dhi else ""))

    # ------------------------------------------------------------------ 3 · ranking
    theme.heading(tab, sub=n.sub, text="3 · Which limit — and which elicited number — actually matters?")
    successes_only = st.toggle(
        "Restrict to realisations above the assessment minimum", value=False,
        key=f"restrict_successes_{tab}",
        help="The two answer different questions. Unrestricted: what controls this closure? "
             "Restricted: what controls it, given it is worth drilling? Reporting only the "
             "restricted one repeats, one level up, the selection error this tool criticises in "
             "the published column-height statistics.")
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
    n.plot(fig3, "Limits ordered by how often they set the contact. **Use this as a workflow "
                 "step, not a summary:** run once, then spend elicitation effort only on the top "
                 "two or three. A limit near zero can be left rough — it is not moving the answer.")

    # ---- the other half of this section's question --------------------------------------
    swing_space = st.radio(
        "Swing measured on", ["Column below apex", "Contact depth"], horizontal=True,
        key=f"tornado_space_{tab}",
        help="They rank differently and both are honest. The apex barely moves the COLUMN and "
             "moves the CONTACT one-for-one, so a tool offering only one would hide half the "
             "sensitivity.")
    space = "column" if swing_space.startswith("Column") else "depth"
    effects = (sensitivity.dhi_tornado(posterior, space=space) if given_dhi
               else sensitivity.tornado(result, space=space))
    centre = (sensitivity.dhi_baseline(posterior, space=space) if given_dhi
              else sensitivity.baseline(result, space=space))

    # A bar's width says how much the answer moves; nothing on it says how much evidence that
    # rests on. Unweighted the two are the same, because every tail is a fixed tenth of the run.
    # Weighted they are not: after a sharp DHI update a tail of a thousand realisations can carry
    # an effective sample of twenty-odd, and the bar is drawn exactly as wide either way.
    if given_dhi and effects:
        _thin = [e for e in effects[:12] if e.support < MIN_TORNADO_SUPPORT]
        if _thin:
            st.warning(
                f"**{len(_thin)} of these bars rest on very little.** After reweighting, the "
                f"thinnest carries an effective sample of **{min(e.support for e in _thin):,}** "
                f"realisations — the tail still holds about a tenth of the run, but almost all of "
                f"that weight is now near zero. Read those bars as directions rather than "
                f"distances: "
                + ", ".join(f"*{e.name}* ({e.support:,})" for e in _thin[:4])
                + ("…" if len(_thin) > 4 else "")
                + ".\n\nMore realisations do not fix this — it is the update concentrating on "
                "fewer of them, and §5's effective sample size is the same story for the whole "
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
               f"**How much each elicited number moves the mean**, which is a different question "
               f"from how often it controls the contact — the figure above. A limit can set the "
               f"contact in most realisations and still be worth no effort, because it always "
               f"bites at nearly the same depth.\n\n"
               f"Each bar is a **conditional mean**: the average outcome when that input came out "
               f"in its top tenth, against its bottom tenth, taken from the run already on screen. "
               f"Because the slices come from the actual joint sample, the bars respect the "
               f"correlations — couple the apex to the spill and the spill's bar changes.\n\n"
               f"**Two kinds of bar.** *Where it bites* is the distribution; *whether it is there* "
               f"is `P(active)`. They are different elicitations, and which one is longer tells "
               f"you whether to go and argue about a depth or about a probability. **The mean, not "
               f"the median** — it is what a volume is built from, and a median can sit still "
               f"while the tail moves underneath it.")
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
                caption="The same selection effect this tool identifies in the empirical literature, "
                "committed one level up if it is ignored: **a limit that usually kills the prospect "
                "outright is under-represented among the survivors precisely because it is the most "
                "severe.** Both columns are wanted; neither alone is the answer.")

    # ------------------------------------------------------------------ group minima
    theme.heading(tab, sub=n.sub, text="4 · By risk element")
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
            "Group minima — the shallowest active limit within each element. These are what the "
            "per-element "
            "chance-versus-depth curves on the *Risk against depth* sub-tab are derived from.")

    # ------------------------------------------------------------------ 5 · one axis
    theme.heading(tab, sub=n.sub, text="5 · Every limit, and the answer, on one axis")
    st.markdown(
        "The competition, drawn. **A limit that is only sometimes present flattens at its "
        "`P(active)`** — read that number off the right-hand end of its curve — and **the result is "
        "the lower envelope**, because the contact is the shallowest active limit. A curve far to "
        "the right of the bold line is a mechanism that never mattered."
        + ("\n\n**Both answers are on the axis.** The bold red line is the contact *given the DHI* "
           "— the answer on this tab — and the dashed blue one is the purely geological contact "
           "from tab 4.0, kept beside it because the gap between them is what the amplitude "
           "bought. Every thin limit curve is drawn under the DHI weights as well, which is what "
           "keeps the lower-envelope reading true." if given_dhi else ""))
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
        help="Exceedance curves read as probabilities; the violins and the histogram show where each limit actually lands; points show the individual realisations behind them.")
    every = c3.number_input(
        "Every n-th point", 1, 500, 10, 1, key=f"stack_every_{tab}",
        disabled=mode != "Points",
        help="Thinning, so the cloud stays readable: 10 draws every tenth realisation. Only applies to **Points**, which is why it is greyed out otherwise.")

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
           "One axis, five ways of looking at it. **Exceedance curves** is the analytic view — "
           "flattening levels are `P(active)`, and the bold line is the lower envelope. "
           "**Violin** and **half violin** show where each limit's mass sits, which is better for "
           "spotting overlap and worse for reading a probability. **Histogram** is the same "
           "unsmoothed, for when a kernel would invent a shape the samples do not have. "
           "**Points** shows the sample itself."
           + ("\n\n**Three groups, left to right, and they are three different kinds of thing.** "
              "*Competing limits* are the mechanisms. *The amplitude alone* is not one of them — it "
              "is the evidence they are being judged against, drawn hollow — a dotted edge, open "
              "bars, open markers — because it is a **likelihood, not a count of realisations**: "
              "read its shape, which is the factor the geology is multiplied by at each depth, and "
              "not its area. In **Points** its markers are drawn *from* that shape rather than "
              "observed, since a likelihood has no realisations behind it. *Result* carries both "
              "answers, "
              + theme.basis_tag(theme.GEOLOGICAL) + " and " + theme.basis_tag(theme.GIVEN_DHI)
              + ", so the middle group is visibly what turns the first into the second.\n\n"
                "In **Points** the updated lane is an importance *resample* of the same "
                "realisations, so a realisation the amplitude favours appears more than once — "
                "that repetition is the update." if given_dhi else ""))

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
