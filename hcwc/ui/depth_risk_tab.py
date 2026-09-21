"""Tab 4.0 — per-element chance against depth, derived rather than allocated.

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
from hcwc.core import pos as pos_math
from hcwc.core.decompose import ELEMENTS, ReservoirEffectiveness
from hcwc.plotting.app.colours import limit_colours
from hcwc.ui import run, theme
from hcwc.ui.numbering import Numbering

TAB = 4

#: How far above the spill point the reservoir-effectiveness decline begins, by default.
#:
#: The decline is a statement about the deepest part of a closure degrading, so it is measured from
#: the spill point rather than from anywhere in the contact distribution. 50 m is Lars's number.
DECLINE_INTERVAL_M = 50.0

#: The same tab, run against the DHI-updated model. See :func:`render`.
TAB_DHI = 5


#: Where the entry-depth control opens, m TVDSS. A depth rather than a percentile of the
#: run: Lars's worked well enters here, and a percentile moves under you whenever the limits
#: change. Clamped into the decomposition's own depth range, which a shallow prospect can
#: sit entirely above.
DEFAULT_ENTRY_DEPTH_M = 2230.0


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
        st.info("Define the limits on tab 3.0 first.")
        return
    result = run.current(limit_set)

    # Gated on there being an update, not on the DHI toggle -- an offset penetration alone now
    # produces one, and this page is a reading of the posterior rather than of the amplitude.
    if with_dhi and st.session_state.get("dhi_posterior") is None:
        st.subheader("Risk against depth, per element | updated")
        st.info(
            "Nothing here has been updated yet. On tab 2.0, either This is a DHI prospect or "
            "This closure has been penetrated needs to be on. Tab 4.0 carries the geological "
            "decomposition and is unaffected either way."
        )
        return

    st.subheader("Risk against depth, per element"
                 + (f" | {theme.evidence_basis()}" if with_dhi else ""))
    theme.basis_banner(
        theme.GIVEN_DHI if with_dhi else theme.GEOLOGICAL,
        "The element chances are unchanged. Evidence about where the contact is may move the "
        "total and may not re-attribute it between elements; only the depth curves respond."
        if with_dhi else
        "The competing limits alone. The updated version of this tab is 5.3.")
    if with_dhi:
        st.markdown(
            "The same decomposition as tab 4.0, after the update on tab 5.1. The geological "
            "curves are drawn underneath unchanged: the evidence may move the total and may not "
            "re-attribute it between elements. Method: see 8.1.6."
        )
    st.markdown(
        "Each element's curve is derived from the shallowest active limit within that element, "
        "its group minimum. WellVolPOS allocates one location factor across the elements by a "
        "rule; the derived curves say which element binds at each depth. Method: see 8.1.3."
    )

    # ------------------------------------------------------------------ reservoir effectiveness
    theme.heading(tab, sub=n.sub, text="1 · Reservoir effectiveness")
    st.markdown(
        "A reservoir that ends at a surface (base or pinch-out) is a limit on tab 3.0 and moves "
        "the contact; a reservoir that degrades with depth is entered here and lowers the chance "
        "without moving it. Method: see 8.1.3."
    )
    use_r1 = st.toggle(
        "Apply a reservoir-effectiveness decline", value=False, key=f"r1_on_{tab}",
        help="For a reservoir that degrades with depth rather than stopping at a surface. "
             "Between the two depths the chance of an effective reservoir falls linearly, so a "
             "deeper contact is worth less than its height alone suggests.")
    reservoir = ReservoirEffectiveness()
    if use_r1:
        r1, r2 = st.columns(2)
        # Anchored on the **spill point**, not on percentiles of the contact distribution.
        #
        # These opened at the P25 and P95 contact, which put the start of the decline in the middle
        # of the answer: switching the toggle on immediately penalised three-quarters of the
        # realisations, so the control arrived already biting hard and the first thing anyone did
        # was drag it deeper. The spill point is also the honest datum — it is a property of the
        # closure the assessor stated on tab 2.0, not an output of the run being adjusted, so the
        # default does not move when the limits move.
        #
        # Lars's values, 2 Sep 2026: the decline occupies the deepest 50 m of the closure.
        _spill = st.session_state.get("spill_point")
        _none_default = (float(_spill) if _spill
                         else float(np.percentile(result.contact_m, 95)))
        _full_default = max(_none_default - DECLINE_INTERVAL_M, 0.0)
        full_to = r1.number_input("Fully effective to (m TVDSS)", 0.0, 8000.0,
                                  _full_default, 25.0,
                                  key=f"r1_full_{tab}",
                                  help="Above this depth the reservoir is fully effective; the "
                                       "decline has not started. Defaults to "
                                       f"{DECLINE_INTERVAL_M:.0f} m above the spill point, so "
                                       "the decline occupies the deepest part of the closure "
                                       "and nothing above it is affected.")
        none_below = r2.number_input("Not a reservoir below (m TVDSS)", 0.0, 8000.0,
                                     _none_default, 25.0,
                                     key=f"r1_none_{tab}",
                                     help="Below this there is effectively no reservoir, so a "
                                          "contact there adds nothing. Defaults to the spill "
                                          "point from tab 2.0, below which there is no closure "
                                          "to fill.")
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
    # Given the DHI the evidence index has updated P(G) to P(G | s) (8.1.4). The update is a
    # total; the per-element curves carry it spread by the allocation rule, so their product is
    # the posterior chance curve tab 5.1 draws and the well reads the same here as on 5.2.4.
    # Until 21 Sep 2026 this tab ran on the geological element chances with the posterior weights
    # and read 31.5 % at a well where 5.2.4 read 36.1 % (Lars, 21 Sep 2026).
    _p_g_updated = (float(overlay["p_g_given_amplitude"])
                    if weights is not None and "p_g_given_amplitude" in overlay else None)

    # ------------------------------------------------------------------ element curves
    theme.heading(tab, sub=n.sub, text="2 · Per-element chance against depth")

    # The four chances are set on tab 2 with the rest of the prospect's inputs. They used to be
    # typed here, after the results they feed, which put an input in the middle of an output.
    pos_stated = st.session_state.get("element_pos")
    if not pos_stated:
        st.info("Set the element risk on tab 2.0 first.")
        return
    pos = dc.element_pos_given_index(pos_stated, _p_g_updated)
    st.caption(
        "Element chances from tab 2.0: "
        + " · ".join(f"{g.value} {v:.2f}" for g, v in pos_stated.items())
        + ". This tab follows any change made there."
        + (f" Given the DHI the evidence index takes P(G) {pos_math.accumulation_chance(pos_stated):.3f} to "
           f"P(G | s) {pos_math.accumulation_chance(pos):.3f} (5.1.2); the update is spread over charge, "
           f"closure and retention by the allocation rule, an element held at 1 passing its "
           f"share on: "
           + " · ".join(f"{g.value} {v:.2f}" for g, v in pos.items()) + "."
           if _p_g_updated is not None else "")
    )

    sub_elements = st.toggle(
        "Break each element into its mechanisms", value=False, key=f"sub_el_{tab}",
        help="The sub-element view: which limit inside Retention is doing the work at this "
             "depth, rather than that Retention is. Each mechanism is drawn in a variation of "
             "its element's hue.")
    show_dhi = with_dhi

    curves = d.element_pos_at_depth(pos)
    geo_curves = d_geo.element_pos_at_depth(pos_stated) if weights is not None else None
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
                        name=element.value + (f" — {theme.evidence_basis()}"
                                              if weights is not None else ""),
                        legendgroup=element.value,
                        line=dict(color=theme.PILLAR_COLOURS[element.value], width=3))
    # Every element is in `curves` now, including one with no limit in the set: its curve is its
    # element chance, flat with depth, times the effectiveness decline where one is set. The
    # special case that used to draw "Reservoir (effectiveness only)" here is folded into that.
    if sub_elements:
        # One level down: the individual mechanisms inside each element, each in a variation of its
        # element's hue so the grouping stays readable at a glance. Scaled by the same element POS
        # as its parent, so a limit curve is never above the element curve it belongs to.
        shades = limit_colours(limit_set)
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

        # Two readings labelled: the median-apex equivalent of the assessment minimum, where the
        # depth-space curve sits close to the headline (equal when the apex is pinned), and the
        # indicated contact, where the posterior median lands and the curve reads about half.
        _apex = float(np.median(result.apex_m))
        def _pos_at(depth_m: float) -> float:
            return float(np.interp(depth_m, overlay["depths_m"], overlay["pos_curve"]))

        _min_depth = _apex + float(overlay["h_min"])
        fig.add_scatter(x=[_pos_at(_min_depth)], y=[_min_depth], mode="markers+text",
                        marker=dict(color="#C44E52", size=11, symbol="diamond",
                                    line=dict(color="white", width=1.5)),
                        text=[f"  {_pos_at(_min_depth):.1%}, the quoted POS at the minimum"],
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
                      height=620, margin=dict(t=20),
                      # To the right rather than beneath (Lars, 15 Sep 2026): given the DHI the
                      # legend carries two entries per element and the row wrapped to three lines.
                      legend=dict(orientation="v", x=1.02, y=1.0, xanchor="left"))
    n.plot(fig, "Each element's chance curve, derived from the shallowest active limit within "
                "that element and scaled by the prospect's element POS. This is the input "
                "WellVolPOS can consume in place of allocating one location factor."
                + ("  Dashed lines are the individual mechanisms within each element, in "
                   "variations of its hue. A mechanism that flattens short of 1.0 is not always "
                   "present; the flat value is its `P(active)`, read off the axis."
                   if sub_elements else "")
                + ("  The red curve is the whole-prospect chance after the update from tab 5.0."
                   if show_dhi and overlay is not None else ""))

    if show_dhi and overlay is None:
        st.caption(
            "The DHI update has not been computed yet. Opening tab 5.0 HCWC (DHI + well) once "
            "enters the evidence; the curve appears here on the next interaction, because that "
            "tab computes it after this one has drawn."
        )
    if show_dhi and overlay is not None:
        o1, o2 = st.columns(2)
        o1.metric("Prospect POS after the DHI", f"{overlay['posterior_pos']:.1%}",
                  f"before {overlay['prior_pos']:.1%}")
        o2.metric("At the assessment minimum", f"{limit_set.min_column_m:.0f} m column",
                  "both read at the same threshold", delta_color="off")
        st.caption(
            "The updated POS and the updated contact distribution are one object, read off this "
            "one curve. The element curves carry the same two updates: the evidence index in the "
            "element chances, spread by the allocation rule, and the geometry in the weights; "
            "their product is the red curve. Method: see 8.1.6."
        )

    # ------------------------------------------------------------------ consistency
    theme.heading(tab, sub=n.sub, text="3 · Consistency test")
    st.markdown(
        "Under independent limits, `∏ₑ Pₑ(z) = P(contact > z)`: the product of the element "
        "curves reproduces the contact distribution. The test runs on every rerun. Method: see "
        "8.1.8."
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
    n.plot(fig2, "Factorised against direct. A residual near zero says the elements behave "
                 "independently and the decomposition can be handed downstream as it is. A large "
                 "one says the elements share something (correlated limits, or a wide apex), and "
                 "the per-element curves should not be multiplied by anything else that also "
                 "depends on depth.")

    st.info(
        "The identity is exact in column-height space and approximate in depth space, where the "
        "elements share the apex draw; the difference between the two residuals is the apex's "
        "contribution. Method: see 8.1.2."
    )

    # ------------------------------------------------------------------ allocation comparison
    theme.heading(tab, sub=n.sub, text="4 · Derived against allocated, at a well")
    # A slider to explore with and a box to type into, because a well plan gives you a number
    # rather than a position on a track. They share a value through two callbacks rather than one
    # key: Streamlit refuses to bind two widgets to the same key, and letting them drift is worse
    # than the four lines it costs to keep them together.
    _lo, _hi = float(d.depths_m[0]), float(d.depths_m[-1])
    _sld, _num = f"z_entry_{tab}", f"z_entry_num_{tab}"
    _opening = min(max(DEFAULT_ENTRY_DEPTH_M, _lo), _hi)
    for _k in (_sld, _num):
        st.session_state.setdefault(_k, _opening)

    # The headline well reading on the sibling sub-tab (4.1 §4 / 5.3 §4) shares the depth, so a
    # change in either place lands in both.
    _head = f"z_entry_headline_{tab}"

    def _from_slider(sld=_sld, num=_num, head=_head):
        st.session_state[num] = st.session_state[sld]
        st.session_state[head] = st.session_state[sld]

    def _from_number(sld=_sld, num=_num, head=_head):
        st.session_state[sld] = st.session_state[num]
        st.session_state[head] = st.session_state[num]

    _c1, _c2 = st.columns([3, 1])
    z_entry = _c1.slider("Well reservoir entry depth (m TVDSS)", _lo, _hi, step=5.0,
                         key=_sld, on_change=_from_slider)
    _c2.number_input("or type it", _lo, _hi, step=5.0, key=_num, on_change=_from_number,
                     help="The same value as the slider, to the metre where the well plan gives "
                          "one; the slider rounds to 5 m.")
    # **Both bases, side by side, when there is a posterior to compare against.** Lars, 4 Sep 2026:
    # this table was the DHI-updated allocation on tab 5.0 and the geological one on tab 4.0, drawn
    # identically, with nothing on either to say which — and the two differ by more than the
    # rounding. They differ through two numbers: `r = P(contact > z_entry | G)`, read off the
    # contact distribution the geometry channel moves, and `P(G | s)`, the accumulation chance
    # the evidence index moves (8.1.4). Until 21 Sep 2026 only `r` was carried and the given-the-DHI
    # half ran on the geological `P(G)`, so this section read 31.5 % at a well where 5.2.4 read
    # 36.1 % (Lars, 21 Sep 2026). The index update is a total; it is spread by the allocation rule.
    _overlay = overlay or {}
    comp = dc.allocation_comparison(d, pos_stated, z_entry, p_g_updated=_p_g_updated)
    comp_geo = (dc.allocation_comparison(d_geo, pos_stated, z_entry)
                if weights is not None else None)
    rows = []
    for element in ELEMENTS:
        row = {"Element": element.value, "Prospect POS": f"{pos_stated[element]:.2f}"}
        if comp_geo is None:
            derived = comp.get(f"derived::{element.value}")
            row["Derived at the well"] = "—" if derived is None else f"{derived:.3f}"
            row["Allocated (equal cube-root)"] = f"{comp[f'allocated::{element.value}']:.3f}"
        else:
            for label, table in ((theme.GEOLOGICAL, comp_geo), (theme.evidence_basis(), comp)):
                derived = table.get(f"derived::{element.value}")
                row[f"Derived · {label}"] = "—" if derived is None else f"{derived:.3f}"
                row[f"Allocated · {label}"] = f"{table[f'allocated::{element.value}']:.3f}"
        rows.append(row)

    n.table(pd.DataFrame(rows),
            ((f"At {z_entry:,.0f} m the location factor is r = {comp_geo['r_location']:.3f} "
                f"geological and r = {comp['r_location']:.3f} {theme.evidence_basis()}; the "
                f"accumulation chance is P(G) = {comp_geo['p_g_applied']:.3f} geological and "
                f"P(G | s) = {comp['p_g_applied']:.3f} {theme.evidence_basis()}. The geometry "
                f"channel moves r, the evidence index moves P(G), and every difference in the "
                f"table follows from those two numbers. The index update is a total: the model "
                f"does not say which element the evidence speaks to, so it is spread over "
                f"charge, closure and retention by the same equal cube-root rule as r, an "
                f"element held at 1 passing its share to the others. "
                if comp_geo is not None else
                f"At {z_entry:,.0f} m, r = {comp['r_location']:.3f}. ")
             + f"Derived and allocated are different kinds of object. The allocation divides one "
               f"number by a rule and reproduces P_well = {comp['allocated::P_well']:.3f} "
               f"whatever rule is chosen. The derived columns carry information about which "
               f"element binds at this depth, so they can disagree with it."))
    # `P_well` is what this section computes, and it was a cell in the table above -- quieter
    # than the allocation rule beside it. Given the treatment tab 2.0 gives `P(G)`, and paired
    # with the two readings it is most often confused with: the prospect POS, which asks whether
    # there is a commercial column anywhere, and `r`, which is only the depth term.
    _pairs = [(theme.GEOLOGICAL, comp_geo or comp, _overlay.get("prior_pos"), "P(G)")]
    if comp_geo is not None:
        _pairs.append((theme.evidence_basis(), comp, _overlay.get("posterior_pos"), "P(G | s)"))

    _accent = theme.accent(tab)
    for _col, (_label, _table, _prospect, _pg_name) in zip(st.columns(len(_pairs)), _pairs):
        _p_well = _table["allocated::P_well"]
        _bits = [f"{_pg_name} {_table['p_g_applied']:.3f} × r {_table['r_location']:.3f}",
                 f"prospect POS {_prospect:.1%}" if _prospect is not None else None]
        _under = " &nbsp;·&nbsp; ".join(b for b in _bits if b)
        _col.markdown(
            f"<div style='margin:0.6rem 0 0.2rem;padding:0.55rem 0.9rem;"
            f"border-left:5px solid {_accent};background:{theme.rgba(_accent, 0.10)};"
            f"border-radius:0 5px 5px 0'>"
            f"<span style='font-size:0.82rem;letter-spacing:0.05em;text-transform:uppercase;"
            f"color:{theme.shade_hex(_accent, -0.45)};font-weight:700'>"
            f"P(well) &nbsp;{_label}</span>"
            f"<div style='font-size:2rem;font-weight:700;line-height:1.15;"
            f"color:{theme.shade_hex(_accent, -0.5)}'>{_p_well:.1%}</div>"
            f"<span style='font-size:0.85rem;opacity:0.8'>{_under}</span></div>",
            unsafe_allow_html=True)

    st.caption(
        f"Three readings, answering three questions. `P(well)` is the chance this well, entering "
        f"at {z_entry:,.0f} m, finds hydrocarbon: the accumulation chance times the chance the "
        f"contact lies below that depth. Given the DHI the accumulation chance is P(G | s), "
        f"updated by the evidence index, and r is read from the posterior contact distribution; "
        f"the reading agrees with the well on 5.2.4. The prospect POS asks whether there is a "
        f"commercial column anywhere, and is always the larger. `r` is the depth term only and "
        f"carries no element risk. An element with no limit in the model has its element "
        f"chance unchanged with depth. Method: see 8.1.3 and 8.1.6."
    )
