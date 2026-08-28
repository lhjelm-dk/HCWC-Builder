"""Tab ④ — the three outputs the engine exists to produce.

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


def render(n: Numbering | None = None, *, posterior=None) -> None:
    """The contact distribution and what produced it, geological or DHI-updated.

    ``posterior`` is a :class:`hcwc.core.dhi.DhiPosterior` or ``None``. With one, every figure is
    drawn on the reweighted sample and the tab number, colour and basis banner follow. **The same
    figures in the same order either way** -- which is what makes flipping between tab ④ and tab ⑤
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
        st.info("Define the limits on tab ③ first.")
        return

    result = posterior.result if given_dhi else run.current(limit_set)
    h_min = limit_set.min_column_m

    st.subheader("Results | given the DHI" if given_dhi else "Results")
    if given_dhi:
        theme.basis_banner(
            theme.GIVEN_DHI,
            "Every figure below carries the amplitude evidence. The purely geological versions of "
            "the same figures are on tab ④, in the same order — they are a different "
            "distribution, not a different view of this one.")
    else:
        theme.basis_banner(
            theme.GEOLOGICAL,
            "The competing limits alone. If this prospect has a DHI, its updated results are on "
            "tab ⑤ and are a different distribution — not a different view of this one.")

    # ------------------------------------------------------------------ headline
    #
    # **Two chances, and they are not the same number.** `result.pos` is the *conditional*
    # column-height term: given the four elements work, does the column reach the assessment
    # minimum. The reportable prospect chance is that times the element product from tab ②. The
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
            f"`P(G)` is the **geological POS** from tab ② — the product of the four element "
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
            "from another is the error tab ⑥ is written to prevent, and quoting the conditional "
            "term as though it were the prospect chance is the same error one level up."
        )

    # ------------------------------------------------------------------ 1 · exceedance
    theme.heading(tab, "1 · Where is the contact?")
    grid = np.linspace(0.0, float(result.column_m.max()) * 1.02, 400)
    f = exceed(grid)
    apex_med = float(np.median(result.apex_m))
    fig = go.Figure()
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
                      height=560, margin=dict(t=20), legend=dict(orientation="h", y=-0.15))
    n.plot(fig, "The exceedance curve `F(h) = P(column ≥ h)`, on the depth axis. Depth on y, "
                "inverted, m TVDSS — the convention throughout this tool and WellVolPOS. **This "
                "curve is the risk output**; POS at any threshold is a reading of it.")

    # ------------------------------------------------------------------ 2 · which limit controls
    theme.heading(tab, "2 · Which limit controls the contact?")
    edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 26)
    centres = 0.5 * (edges[:-1] + edges[1:])
    shares = engine.controlling_share_by_depth(result, edges, weights=weights)
    ranked = [name for name, _ in engine.limit_ranking(result, weights=weights)]
    group_of = dict(zip(limit_set.names, limit_set.groups))
    colour_of = limit_colours(limit_set)
    # Stacked horizontal bars rather than a stacked area. Plotly's `stackgroup` accumulates along
    # the *value* axis, which on an inverted depth axis stacks the depths themselves -- the first
    # attempt at this figure ran the y-axis to 20 km. Bars stack along x by construction, so the
    # orientation cannot be got wrong.
    bar_height = float(np.diff(edges).mean())
    fig2 = go.Figure()
    for name in ranked:
        if shares[name].sum() == 0:
            continue
        fig2.add_bar(x=shares[name], y=centres, orientation="h", name=name,
                     width=bar_height, marker_color=colour_of[name],
                     marker_line_width=0,
                     hovertemplate=f"{name}<br>%{{y:.0f}} m TVDSS<br>%{{x:.0%}}<extra></extra>")
    fig2.update_layout(barmode="stack", bargap=0.06,
                       xaxis_title="Share of realisations controlled by this limit",
                       xaxis_range=[0, 1], xaxis_tickformat=".0%",
                       yaxis_title="Contact depth (m TVDSS)",
                       yaxis=dict(autorange="reversed"), height=560, margin=dict(t=20),
                       legend=dict(orientation="h", y=-0.18))
    n.plot(fig2, "The diagnostic the argmin bookkeeping buys, and the reason for keeping it: **the "
                 "controlling mechanism changes as you step down structure.** Hue is the risk "
                 "element, in E-POS's colours — salmon charge, blue closure, yellow reservoir, "
                 "green retention — and lightness separates the limits within an element. Grant "
                 "(2020) publishes an equivalent as \"column height control statistics\"; the "
                 "per-element curves built from it are, as far as I can find, unpublished.")

    # ------------------------------------------------------------------ 3 · ranking
    theme.heading(tab, "3 · Which limit — and which elicited number — actually matters?")
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
    theme.heading(tab, "4 · By risk element")
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
    theme.heading(tab, "5 · Every limit, and the answer, on one axis")
    st.markdown(
        "The competition, drawn. **A limit that is only sometimes present flattens at its "
        "`P(active)`** — read that number off the right-hand end of its curve — and **the result is "
        "the lower envelope**, because the contact is the shallowest active limit. A curve far to "
        "the right of the bold line is a mechanism that never mattered."
    )
    c1, c2, c3 = st.columns([2, 2, 1])
    space = c1.radio(
        "Show depths as", [limits_mod.DEPTH, limits_mod.COLUMN], horizontal=True,
        key=f"stack_space_{tab}",
        format_func=lambda s_: "m TVDSS" if s_ == limits_mod.DEPTH else "m column below apex",
        help="Display only. The model always competes in column height, because that is the space "
             "where comparing a seal capacity with a spill point means anything.")
    mode = c2.selectbox("Draw as", limit_stack.MODES, key=f"stack_mode_{tab}")
    every = c3.number_input("Every n-th point", 1, 500, 10, 1, key=f"stack_every_{tab}",
                            disabled=mode != "Points")

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
           "**Points** shows the sample itself.")

    # ------------------------------------------------------------------ 6 · trust
    # Geological only. The panel audits the run -- realisation counts, seed
    # repeatability, the correlation projection -- and those are properties of the sample, not of
    # the reweighting. Its DHI check already reports the effective sample size behind the update.
    if not given_dhi:
        trust_panel.render(n, result, tab=tab,
                           posterior=(st.session_state.get("dhi_posterior")
                                      if st.session_state.get("dhi_on") else None))
