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

from hcwc.core import engine, trust
from hcwc.core import limits as limits_mod
from hcwc.core.limits import Group
from hcwc.ui import limit_stack, theme, trust_panel
from hcwc.ui.numbering import Numbering

TAB = 4

@st.cache_data(show_spinner="Running the competing-limits model…")
def _run(payload: dict, n: int, seed: int):
    from hcwc.core.limits import LimitSet
    return engine.run(LimitSet.from_dict(payload), n, seed)


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


def render(n: Numbering | None = None) -> None:
    # The Numbering is passed in when this shares a tab with the depth-risk decomposition, so the
    # two sub-tabs draw from one sequence and `Figure 4.6` means one figure rather than two.
    n = n or Numbering(TAB)
    limit_set = st.session_state.get("limit_set")
    if limit_set is None:
        st.info("Define the limits on tab ③ first.")
        return

    result = _run(limit_set.to_dict(), st.session_state.get("n_trials", 10_000),
                  st.session_state.get("seed", 20260825))
    h_min = limit_set.min_column_m

    st.subheader("Results")
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
    element_pos = st.session_state.get("element_pos") or {}
    p_geological = float(np.prod([float(v) for v in element_pos.values()])) if element_pos else 1.0
    prospect_pos = p_geological * result.pos

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
            col.metric(f"Contact P{p}", f"{result.percentiles(p)[0]:,.0f} m",
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
        m2.metric(f"P(column ≥ {h_min:.0f} m | G)", f"{result.pos:.1%}",
                  "conditional — this tab only", delta_color="off")
        for col, p in ((m3, 90), (m4, 50), (m5, 10)):
            col.metric(f"Contact P{p}", f"{result.percentiles(p)[0]:,.0f} m",
                       "success cases only", delta_color="off")
        st.markdown(
            f"**The prospect chance is a product of two things, and this tab computes only one of "
            f"them.**\n\n"
            f"`Prospect POS = P(G) × P(column ≥ h | G)` = "
            f"**{p_geological:.3f} × {result.pos:.3f} = {prospect_pos:.3f}**\n\n"
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
    theme.heading(TAB, "1 · Where is the contact?")
    grid = np.linspace(0.0, float(result.column_m.max()) * 1.02, 400)
    f = result.exceedance(grid)
    apex_med = float(np.median(result.apex_m))
    fig = go.Figure()
    fig.add_scatter(x=f, y=apex_med + grid, mode="lines", name="P(contact deeper than this)",
                    line=dict(color="#4C72B0", width=3))
    if h_min > 0:
        fig.add_hline(y=apex_med + h_min, line=dict(color="#C44E52", dash="dash"),
                      annotation_text=f"assessment minimum — P(column ≥ h | G) = {result.pos:.1%}",
                      annotation_position="bottom right")
    for p, dash in ((90, "dot"), (50, "solid"), (10, "dot")):
        fig.add_hline(y=float(result.percentiles(p)[0]), line=dict(color="#888", dash=dash,
                                                                  width=1),
                      annotation_text=f"P{p}", annotation_position="top left")
    fig.update_layout(xaxis_title="Probability the contact is deeper", xaxis_range=[0, 1],
                      yaxis_title="Depth (m TVDSS)", yaxis=dict(autorange="reversed"),
                      height=560, margin=dict(t=20), legend=dict(orientation="h", y=-0.15))
    n.plot(fig, "The exceedance curve `F(h) = P(column ≥ h)`, on the depth axis. Depth on y, "
                "inverted, m TVDSS — the convention throughout this tool and WellVolPOS. **This "
                "curve is the risk output**; POS at any threshold is a reading of it.")

    # ------------------------------------------------------------------ 2 · which limit controls
    theme.heading(TAB, "2 · Which limit controls the contact?")
    edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 26)
    centres = 0.5 * (edges[:-1] + edges[1:])
    shares = engine.controlling_share_by_depth(result, edges)
    ranked = [name for name, _ in engine.limit_ranking(result)]
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
    theme.heading(TAB, "3 · Which limit — and which elicited number — actually matters?")
    successes_only = st.toggle(
        "Restrict to realisations above the assessment minimum", value=False,
        help="The two answer different questions. Unrestricted: what controls this closure? "
             "Restricted: what controls it, given it is worth drilling? Reporting only the "
             "restricted one repeats, one level up, the selection error this tool criticises in "
             "the published column-height statistics.")
    ranking = engine.limit_ranking(result, successes_only=successes_only)
    other = engine.limit_ranking(result, successes_only=not successes_only)
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
    theme.heading(TAB, "4 · By risk element")
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
    theme.heading(TAB, "5 · Every limit, and the answer, on one axis")
    st.markdown(
        "The competition, drawn. **A limit that is only sometimes present flattens at its "
        "`P(active)`** — read that number off the right-hand end of its curve — and **the result is "
        "the lower envelope**, because the contact is the shallowest active limit. A curve far to "
        "the right of the bold line is a mechanism that never mattered."
    )
    c1, c2, c3 = st.columns([2, 2, 1])
    space = c1.radio(
        "Show depths as", [limits_mod.DEPTH, limits_mod.COLUMN], horizontal=True,
        key="stack_space",
        format_func=lambda s_: "m TVDSS" if s_ == limits_mod.DEPTH else "m column below apex",
        help="Display only. The model always competes in column height, because that is the space "
             "where comparing a seal capacity with a spill point means anything.")
    mode = c2.selectbox("Draw as", limit_stack.MODES, key="stack_mode")
    every = c3.number_input("Every n-th point", 1, 500, 10, 1, key="stack_every",
                            disabled=mode != "Points")

    apex_med = float(np.median(result.apex_m))
    lo_def, hi_def = limit_stack.default_window(result, space, apex_med,
                                                limit_stack._spill(result, apex_med))
    lo_def, hi_def = float(min(lo_def, hi_def)), float(max(lo_def, hi_def))
    pad = 0.35 * (hi_def - lo_def)
    window = st.slider(
        f"Depth range ({limits_mod.Limit.label_for(space)})",
        float(lo_def - pad), float(hi_def + pad), (lo_def, hi_def), key=f"stack_window_{space}",
        help="Defaults to 1 % above the apex and 1 % below the spill point. Several limits carry "
             "tails reaching far below anything the structure contains, and letting those set the "
             "range squeezes the part that matters into the top of the plot.")

    n.plot(limit_stack.figure(result, space=space, mode=mode, window=window, every=int(every)),
           "One axis, five ways of looking at it. **Exceedance curves** is the analytic view — "
           "flattening levels are `P(active)`, and the bold line is the lower envelope. "
           "**Violin** and **half violin** show where each limit's mass sits, which is better for "
           "spotting overlap and worse for reading a probability. **Histogram** is the same "
           "unsmoothed, for when a kernel would invent a shape the samples do not have. "
           "**Points** shows the sample itself.")

    # ------------------------------------------------------------------ 6 · trust
    trust_panel.render(n, result, tab=TAB,
                       posterior=(st.session_state.get("dhi_posterior")
                                  if st.session_state.get("dhi_on") else None))
