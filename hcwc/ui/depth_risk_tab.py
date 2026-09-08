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
from hcwc.core.decompose import ELEMENTS, ReservoirEffectiveness
from hcwc.core.limits import Group
from hcwc.ui import results_tab, run, theme
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
            "**Nothing here has been updated yet.** On tab 2.0, turn on either *This is a DHI "
            "prospect* or *This closure has been penetrated*. Tab 4.0 carries the geological "
            "decomposition and is unaffected either way."
        )
        return

    st.subheader("Risk against depth, per element"
                 + (f" | {theme.evidence_basis()}" if with_dhi else ""))
    theme.basis_banner(
        theme.GIVEN_DHI if with_dhi else theme.GEOLOGICAL,
        "The element chances are unchanged — evidence about *where* the contact is may move the "
        "total and may not re-attribute it between elements. Only the depth curves respond."
        if with_dhi else
        "The competing limits alone. The updated version of this tab is 5.4.")
    if with_dhi:
        st.markdown(
            "The same decomposition as tab 4.0, after the Bayesian update on tab 5.0. The "
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
        "geometric limit like spill and belongs on tab 3.0. **R1, effectiveness** — diagenesis, "
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
                                  help="Above this depth the reservoir is as good as it gets — "
                                       "the decline has not started. Defaults to "
                                       f"{DECLINE_INTERVAL_M:.0f} m above the spill point, so the "
                                       "decline occupies the deepest part of the closure and "
                                       "nothing above it is touched until you say so.")
        none_below = r2.number_input("Not a reservoir below (m TVDSS)", 0.0, 8000.0,
                                     _none_default, 25.0,
                                     key=f"r1_none_{tab}",
                                     help="Below this there is effectively no reservoir left, so "
                                          "a contact down there adds nothing. Defaults to the "
                                          "spill point from tab 2.0, below which there is no closure "
                                          "to fill in any case.")
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
        st.info("Set the element risk on tab 2.0 first.")
        return
    st.caption(
        "Element chances come from tab 2.0 — "
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
                        name=element.value + (f" — {theme.evidence_basis()}"
                                              if weights is not None else ""),
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
                + ("  The red curve is the whole-prospect chance after the DHI update from tab 5.0."
                   if show_dhi and overlay is not None else ""))

    if show_dhi and overlay is None:
        st.caption(
            "**The DHI update has not been computed yet.** Open tab 5.0 (*Results + DHI*) once so "
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
            "5.0 makes with its POS-against-threshold figure, seen from the other side: because the "
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
    # A slider to explore with and a box to type into, because a well plan gives you a number
    # rather than a position on a track. They share a value through two callbacks rather than one
    # key: Streamlit refuses to bind two widgets to the same key, and letting them drift is worse
    # than the four lines it costs to keep them together.
    _lo, _hi = float(d.depths_m[0]), float(d.depths_m[-1])
    _sld, _num = f"z_entry_{tab}", f"z_entry_num_{tab}"
    _opening = min(max(DEFAULT_ENTRY_DEPTH_M, _lo), _hi)
    for _k in (_sld, _num):
        st.session_state.setdefault(_k, _opening)

    def _from_slider(sld=_sld, num=_num):
        st.session_state[num] = st.session_state[sld]

    def _from_number(sld=_sld, num=_num):
        st.session_state[sld] = st.session_state[num]

    _c1, _c2 = st.columns([3, 1])
    z_entry = _c1.slider("Well reservoir entry depth (m TVDSS)", _lo, _hi, step=5.0,
                         key=_sld, on_change=_from_slider)
    _c2.number_input("or type it", _lo, _hi, step=5.0, key=_num, on_change=_from_number,
                     help="The same value as the slider. Typed to the metre when the well plan "
                          "gives you one; the slider rounds to 5 m.")
    comp = dc.allocation_comparison(d, pos, z_entry)
    # **Both bases, side by side, when there is a posterior to compare against.** Lars, 4 Sep 2026:
    # this table was the DHI-updated allocation on tab 5.0 and the geological one on tab 4.0, drawn
    # identically, with nothing on either to say which — and the two differ by more than the
    # rounding. They differ through `r` alone: `r = P(contact > z_entry | success)` is read off the
    # contact distribution, which is the one thing the amplitude does move, while the element
    # chances above it are untouched by construction. So the whole gap between the two pairs of
    # columns below is the amplitude's opinion about depth, and nothing else.
    comp_geo = dc.allocation_comparison(d_geo, pos, z_entry) if weights is not None else None
    rows = []
    for element in ELEMENTS:
        row = {"Element": element.value, "Prospect POS": f"{pos[element]:.2f}"}
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
            ((f"At {z_entry:,.0f} m the location factor is **r = {comp_geo['r_location']:.3f} "
                f"geological** and **r = {comp['r_location']:.3f} {theme.evidence_basis()}**, "
                f"and every difference in the table follows from that one number — the element "
                f"chances from tab 2.0 are identical in both halves, because evidence about "
                f"*where* the contact is moves the total and may not re-attribute it between "
                f"elements. "
                if comp_geo is not None else
                f"At {z_entry:,.0f} m, r = {comp['r_location']:.3f}. ")
             + f"**Derived and allocated are different kinds of object.** The allocation divides "
               f"one number by a rule and reproduces P_well = {comp['allocated::P_well']:.3f} "
               f"whatever rule is chosen. The derived columns carry information about which element "
               f"actually binds at this depth, so they can — and do — disagree."))
    # `P_well` is what this section computes, and it was a cell in the table above -- quieter
    # than the allocation rule beside it. Given the treatment tab 2.0 gives `P(G)`, and paired
    # with the two readings it is most often confused with: the prospect POS, which asks whether
    # there is a commercial column anywhere, and `r`, which is only the depth term.
    _overlay = st.session_state.get("dhi_overlay") or {}
    _pairs = [(theme.GEOLOGICAL, comp_geo or comp, _overlay.get("prior_pos"))]
    if comp_geo is not None:
        _pairs.append((theme.evidence_basis(), comp, _overlay.get("posterior_pos")))

    _accent = theme.accent(tab)
    for _col, (_label, _table, _prospect) in zip(st.columns(len(_pairs)), _pairs):
        _p_well = _table["allocated::P_well"]
        _bits = [f"prospect POS {_prospect:.1%}" if _prospect is not None else None,
                 f"r = {_table['r_location']:.3f}"]
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
        f"**Three readings, and they answer three questions.** `P(well)` is the chance this "
        f"*well*, entering at {z_entry:,.0f} m, finds hydrocarbon — the prospect chance times the "
        f"chance the contact lies below that depth. The **prospect POS** above it asks whether "
        f"there is a commercial column *anywhere*, and is therefore always the larger. `r` is only "
        f"the depth term, and carries no element risk at all: quoting it as a chance of success "
        f"overstates the well by `1 / P(G)`.\n\n"
        "Reservoir has no derived value in the table because no limit in this model is reservoir-"
        "controlled; add an R2 pinchout limit on tab 3.0 to give it one. Its effectiveness decline "
        "(§1) is separate and applies either way."
    )
