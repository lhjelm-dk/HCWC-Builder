"""Tab ④ — per-element chance against depth, derived rather than allocated.

The claim this tab makes, and then tests on itself: because the engine knows which element bound
the column in each realisation, each element gets a genuine chance-versus-depth curve. WellVolPOS
can only take one location factor and divide it up, and says so in its own docstring.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hcwc.core import decompose as dc
from hcwc.core.decompose import ELEMENTS, ReservoirEffectiveness
from hcwc.core.limits import Group
from hcwc.ui import results_tab, run, theme
from hcwc.ui.numbering import Numbering

TAB = 4
#: The same tab, run against the DHI-updated model. See :func:`render`.
TAB_DHI = 5


def render(tab: int = TAB, *, with_dhi: bool = False, n: Numbering | None = None) -> None:
    """The per-element decomposition, geological or DHI-updated.

    One function serving two tabs. ``tab`` drives the figure numbering and the section colours;
    ``with_dhi`` overlays the posterior. They are the same analysis on two inputs, and writing it
    twice would guarantee the two drifted.

    **Every widget is keyed by tab.** Streamlit renders both tabs on every run, so an unkeyed
    toggle would collide between the two instances and the second would silently mirror the first.
    """
    n = n or Numbering(tab)
    limit_set = st.session_state.get("limit_set")
    if limit_set is None:
        st.info("Define the limits on tab ③ first.")
        return
    result = run.current(limit_set)

    if with_dhi and not st.session_state.get("dhi_on", False):
        st.subheader("Risk against depth, per element | DHI")
        st.info(
            "**This prospect is not marked as a DHI prospect**, so there is nothing to update. "
            "Turn on *This is a DHI prospect* on tab ②. Tab ④ carries the geological "
            "decomposition and is unaffected either way."
        )
        return

    st.subheader("Risk against depth, per element"
                 + (" | DHI" if with_dhi else ""))
    theme.basis_banner(
        theme.GIVEN_DHI if with_dhi else theme.GEOLOGICAL,
        "The element chances are unchanged — a fluid indicator may move the total and may not "
        "re-attribute it between elements. Only the depth curves respond."
        if with_dhi else
        "The competing limits alone. The DHI-updated version of this tab is ⑤.")
    if with_dhi:
        st.markdown(
            "The same decomposition as tab ④, after the Bayesian update on tab ⑤. The "
            "geological curves are drawn underneath unchanged, because **the DHI may move the "
            "total and may not re-attribute it between elements** — E-POS's resolution "
            "ceiling: a fluid indicator senses whether a reservoir exists and what fluid fills it, "
            "not *which* of charge, closure or retention failed."
        )
    st.markdown(
        "WellVolPOS computes one location factor, `r = P(contact > z_entry | success)`, and spreads "
        "it across the elements by a weighting rule. Its own docstring is candid about what that "
        "buys: *\"Spreading a single number across four elements presents it differently; it does "
        "not add information about charge or closure.\"*\n\n"
        "The competing-limits model can do better, because it knows **which element bound the "
        "column in each realisation**. Take the shallowest active limit *within* each element — its "
        "group minimum — and each element gets its own curve. That is a "
        "**derivation**; the allocation is a presentation."
    )

    # ------------------------------------------------------------------ reservoir effectiveness
    theme.heading(tab, sub=n.sub, text="1 · Reservoir effectiveness — the effect that is not a limit")
    st.markdown(
        "Two things get called *reservoir versus depth* and only one moves the contact. "
        "**R2, the base or pinchout**, ends the reservoir so the column cannot continue — that is a "
        "geometric limit like spill and belongs on tab ③. **R1, effectiveness** — diagenesis, "
        "cementation, a net-to-gross trend — does not move the contact; it changes the chance of "
        "success *at* a depth. Conflating them breaks the consistency identity below, so R1 lives "
        "here and the identity is checked over the contact-controlling elements only."
    )
    use_r1 = st.toggle(
        "Apply a reservoir-effectiveness decline", value=False, key=f"r1_on_{tab}",
        help="For a reservoir that degrades with depth rather than stopping at a surface. Between "
             "the two depths it asks for, the chance of an effective reservoir falls off linearly, "
             "so a deeper contact is worth less than its height alone suggests.")
    reservoir = ReservoirEffectiveness()
    if use_r1:
        r1, r2 = st.columns(2)
        full_to = r1.number_input("Fully effective to (m TVDSS)", 0.0, 8000.0,
                                  float(np.percentile(result.contact_m, 25)), 25.0,
                                  key=f"r1_full_{tab}",
                                  help="Above this depth the reservoir is as good as it gets — "
                                       "the decline has not started.")
        none_below = r2.number_input("Not a reservoir below (m TVDSS)", 0.0, 8000.0,
                                     float(np.percentile(result.contact_m, 95)), 25.0,
                                     key=f"r1_none_{tab}",
                                     help="Below this there is effectively no reservoir left, so "
                                          "a contact down there adds nothing.")
        if none_below < full_to:
            st.error("The reservoir cannot stop being effective above the depth it is fully "
                     "effective to.")
            return
        reservoir = ReservoirEffectiveness(full_to, none_below)

    # With the DHI on, this tab is the posterior decomposition: every curve is the same statistic
    # reweighted by the amplitude evidence. The geological one is kept alongside so the shift is
    # visible per element rather than only in the total.
    overlay = st.session_state.get("dhi_overlay")
    weights = None
    if with_dhi and overlay is not None:
        w = np.asarray(overlay.get("weights", []), dtype=float)
        if w.size == result.n:
            weights = w
    d = dc.decompose(result, reservoir=reservoir, weights=weights)
    d_geo = dc.decompose(result, reservoir=reservoir) if weights is not None else d

    # ------------------------------------------------------------------ element curves
    theme.heading(tab, sub=n.sub, text="2 · Per-element chance against depth")

    # The four chances are set on tab 2 with the rest of the prospect's inputs. They used to be
    # typed here, after the results they feed, which put an input in the middle of an output.
    pos = st.session_state.get("element_pos")
    if not pos:
        st.info("Set the element risk on tab ② first.")
        return
    st.caption(
        "Element chances come from tab ② — "
        + " · ".join(f"**{g.value}** {v:.2f}" for g, v in pos.items())
        + ". Change them there and this whole tab follows."
    )

    sub_elements = st.toggle(
        "Break each element into its mechanisms", value=False, key=f"sub_el_{tab}",
        help="The sub-element view: which limit inside Retention is doing the work at this depth, "
             "rather than that Retention is. Each mechanism is drawn in a variation of its "
             "element's hue.")
    show_dhi = with_dhi

    curves = d.element_pos_at_depth(pos)
    geo_curves = d_geo.element_pos_at_depth(pos) if weights is not None else None
    fig = go.Figure()
    for element in ELEMENTS:
        if element not in curves:
            continue
        if geo_curves is not None:
            # Faint, underneath, unlabelled in the legend beyond one entry: the reference the
            # posterior moved from. Drawn first so the posterior sits on top of it.
            fig.add_scatter(x=geo_curves[element], y=d_geo.depths_m, mode="lines",
                            name=f"{element.value} — geological", legendgroup=element.value,
                            line=dict(color=theme.PILLAR_COLOURS[element.value], width=1.6,
                                      dash="dot"), opacity=0.75)
        fig.add_scatter(x=curves[element], y=d.depths_m, mode="lines",
                        name=element.value + (" — given the DHI" if weights is not None else ""),
                        legendgroup=element.value,
                        line=dict(color=theme.PILLAR_COLOURS[element.value], width=3))
    if Group.RESERVOIR not in curves and reservoir.active:
        fig.add_scatter(x=pos[Group.RESERVOIR] * d.reservoir_effectiveness, y=d.depths_m,
                        mode="lines", name="Reservoir (effectiveness only)",
                        line=dict(color=theme.PILLAR_COLOURS["Reservoir"], width=3, dash="dash"))
    if sub_elements:
        # One level down: the individual mechanisms inside each element, each in a variation of its
        # element's hue so the grouping stays readable at a glance. Scaled by the same element POS
        # as its parent, so a limit curve is never above the element curve it belongs to.
        shades = results_tab.limit_colours(limit_set)
        per_limit = dc.limit_curves_at_depth(result, d.depths_m, weights)
        for limit in limit_set.limits:
            fig.add_scatter(x=pos[limit.group] * per_limit[limit.name], y=d.depths_m,
                            mode="lines", name=f"  {limit.name}", legendgroup=limit.group.value,
                            line=dict(color=shades[limit.name], width=1.4, dash="dash"))

    fig.add_scatter(x=d.direct_pos(pos), y=d.depths_m, mode="lines", name="P at this depth (direct)",
                    line=dict(color="#333", width=3, dash="dot"))

    if show_dhi and overlay is not None:
        # Both curves are **prospect chance against depth**, on the same footing as the element
        # curves beside them: each reads its own POS at the assessment minimum and falls away with
        # depth. The posterior starts higher by exactly the Bayesian uplift.
        fig.add_scatter(x=np.interp(d.depths_m, overlay["depths_m"], overlay["prior_curve"]),
                        y=d.depths_m, mode="lines", name="prospect chance, before the DHI",
                        line=dict(color="#8A8A8A", width=2.5, dash="dash"))
        fig.add_scatter(x=np.interp(d.depths_m, overlay["depths_m"], overlay["pos_curve"]),
                        y=d.depths_m, mode="lines", name="prospect chance, after the DHI",
                        line=dict(color="#C44E52", width=3.5))

        # **Where the curve reads the headline, and where it does not.** Read at the assessment
        # minimum this curve IS the quoted prospect POS. Read at the picked contact it is roughly
        # half of it -- because the DHI puts the posterior MEDIAN at the pick, so about half the
        # remaining probability lies deeper. That is the DHI working, not the curve failing, and
        # it is a reading confusing enough that both are now labelled.
        _apex = float(np.median(result.apex_m))
        def _pos_at(depth_m: float) -> float:
            return float(np.interp(depth_m, overlay["depths_m"], overlay["pos_curve"]))

        _min_depth = _apex + float(overlay["h_min"])
        fig.add_scatter(x=[_pos_at(_min_depth)], y=[_min_depth], mode="markers+text",
                        marker=dict(color="#C44E52", size=11, symbol="diamond",
                                    line=dict(color="white", width=1.5)),
                        text=[f"  {_pos_at(_min_depth):.1%} — the quoted POS, at your minimum"],
                        textposition="middle right", textfont=dict(size=11, color="#8A2F33"),
                        showlegend=False, hoverinfo="skip")

        _pick = overlay.get("picked_contact_m")
        if _pick:
            _samples = np.asarray(overlay["contact_samples"], dtype=float)
            _median = float(np.median(_samples)) if _samples.size else None
            fig.add_scatter(x=[_pos_at(_pick)], y=[_pick], mode="markers+text",
                            marker=dict(color="#C44E52", size=11, symbol="circle",
                                        line=dict(color="white", width=1.5)),
                            text=[f"  {_pos_at(_pick):.1%} — chance of a column at least this deep"],
                            textposition="middle right", textfont=dict(size=11, color="#8A2F33"),
                            showlegend=False, hoverinfo="skip")
            if _median is not None:
                fig.add_hline(y=_median, line=dict(color="#C44E52", dash="dot", width=1.2),
                              annotation_text=f"posterior median contact {_median:,.0f} m",
                              annotation_position="bottom right",
                              annotation_font=dict(size=10, color="#8A2F33"))

    fig.update_layout(xaxis_title="Probability", xaxis_range=[0, 1],
                      yaxis_title="Depth (m TVDSS)", yaxis=dict(autorange="reversed"),
                      height=620, margin=dict(t=20), legend=dict(orientation="h", y=-0.15))
    n.plot(fig, "Each element's own chance curve, derived from the shallowest active limit within "
                "that element and scaled by the prospect's element POS. **This is what WellVolPOS "
                "should consume** in place of allocating one location factor — it is the "
                "evidence-based replacement for the hard-typed \"HCWC dissection\" column in the "
                "old `Results` sheet."
                + ("  Dashed lines are the individual mechanisms within each element, in "
                   "variations of its hue. A mechanism that flattens short of 1.0 is one that is "
                   "not always present — the flat value **is** its `P(active)`, read straight off "
                   "the axis." if sub_elements else "")
                + ("  The red curve is the whole-prospect chance after the DHI update from tab ⑤."
                   if show_dhi and overlay is not None else ""))

    if show_dhi and overlay is None:
        st.caption(
            "**The DHI update has not been computed yet.** Open tab ⑤ (*Results + DHI*) once so "
            "the evidence is entered; the curve appears here on the next interaction, because that "
            "tab computes it after this one has already drawn."
        )
    if show_dhi and overlay is not None:
        o1, o2 = st.columns(2)
        o1.metric("Prospect POS after the DHI", f"{overlay['posterior_pos']:.1%}",
                  f"before {overlay['prior_pos']:.1%}")
        o2.metric("At the assessment minimum", f"{limit_set.min_column_m:.0f} m column",
                  "both read at the same threshold", delta_color="off")
        st.caption(
            "**The DHI moves the whole curve, not a scalar beside it.** That is the same point tab "
            "⑤ makes with its POS-against-threshold figure, seen from the other side: because the "
            "updated POS and the updated contact distribution are one object, a DHI that raises "
            "the chance of success also moves *where* the contact is, and both readings have to "
            "come from this one curve.\n\n"
            "**The element curves below it are deliberately not updated.** E-POS's resolution "
            "ceiling says a fluid indicator senses whether a reservoir exists and what fills it, "
            "not *which* of charge, closure or retention failed — so the DHI may move the total "
            "and may not re-attribute it between elements."
        )

    # ------------------------------------------------------------------ consistency
    theme.heading(tab, sub=n.sub, text="3 · The consistency test")
    st.markdown(
        "Under independent limits, `∏ₑ Pₑ(z) = P(contact > z)` — the product of the element curves "
        "must reproduce the contact distribution. **Where it does not, the elements are not "
        "independent, and that gap is the double-count** the three-tool architecture exists to "
        "avoid, and it is worth running every time rather than assuming independence holds."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Max gap, column space", f"{d.max_abs_residual_column:.3f}",
              "exact under independent limits", delta_color="off")
    c2.metric("Max gap, depth space", f"{d.max_abs_residual_depth:.3f}",
              "includes the shared apex", delta_color="off")
    c3.metric("Attributable to the apex", f"{d.apex_contribution:+.3f}",
              "difference between the two", delta_color="off")

    fig2 = go.Figure()
    fig2.add_scatter(x=d.product_depth, y=d.depths_m, mode="lines",
                     name="∏ₑ Pₑ(z) — factorised", line=dict(color="#8CB7FC", width=3))
    fig2.add_scatter(x=d.direct_depth, y=d.depths_m, mode="lines",
                     name="P(contact > z) — direct", line=dict(color="#333", width=2, dash="dot"))
    fig2.add_scatter(x=d.residual_depth, y=d.depths_m, mode="lines", name="residual",
                     line=dict(color="#C44E52", width=2))
    fig2.update_layout(xaxis_title="Probability", yaxis_title="Depth (m TVDSS)",
                       yaxis=dict(autorange="reversed"), height=560, margin=dict(t=20),
                       legend=dict(orientation="h", y=-0.15))
    n.plot(fig2, "Factorised against direct. A residual near zero says the elements are behaving "
                 "independently and the decomposition can be handed downstream as-is. A large one "
                 "says the elements share something — correlated limits, or a wide apex — and the "
                 "per-element curves should not be multiplied by anything else that also depends "
                 "on depth.")

    st.info(
        "**Why the two spaces.** Every element's *contact* is `apex + h`, so the elements share "
        "the apex draw: even with perfectly independent limits, the depth-space curves are "
        "dependent and their product is not the contact distribution. The identity is exact only "
        "in **column-height** space. The difference between the two residuals is therefore the "
        "apex's contribution, and it is what tells you whether the depth-space test can be read at "
        "face value. On a tightly picked apex the two residuals are all but identical and the "
        "distinction can be ignored; a prospect with real depth-conversion uncertainty cannot "
        "ignore it."
    )

    # ------------------------------------------------------------------ allocation comparison
    theme.heading(tab, sub=n.sub, text="4 · Derived against allocated, at a well")
    z_entry = st.slider("Well reservoir entry depth (m TVDSS)",
                        float(d.depths_m[0]), float(d.depths_m[-1]),
                        float(np.percentile(result.contact_m, 40)), 5.0,
                        key=f"z_entry_{tab}")
    comp = dc.allocation_comparison(d, pos, z_entry)
    rows = []
    for element in ELEMENTS:
        derived = comp.get(f"derived::{element.value}")
        rows.append({
            "Element": element.value,
            "Prospect POS": f"{pos[element]:.2f}",
            "Derived at the well": "—" if derived is None else f"{derived:.3f}",
            "Allocated (equal cube-root)": f"{comp[f'allocated::{element.value}']:.3f}",
        })
    n.table(pd.DataFrame(rows),
            f"At {z_entry:,.0f} m, r = {comp['r_location']:.3f}. **The two columns are different "
            f"kinds of object.** The allocation divides one number by a rule and reproduces "
            f"P_well = {comp['allocated::P_well']:.3f} whatever rule is chosen. The derived column "
            f"carries information about which element actually binds at this depth, so it can — "
            f"and does — disagree.")
    st.caption(
        "Reservoir has no derived value here because no limit in this model is reservoir-"
        "controlled; add an R2 pinchout limit on tab ③ to give it one. Its effectiveness decline "
        "(§1) is separate and applies either way."
    )
