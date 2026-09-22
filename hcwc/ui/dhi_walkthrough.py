"""Tab 5.0 sub-tab 1.0 — the Bayesian update, walked through one term at a time.

The rest of this tab applies Bayes' rule nine times and never once writes it down. A geoscientist
who wants to check the reasoning has nowhere to look, and the two questions that actually stop
people — *where did the denominator go* and *what if the thing I picked is not the contact* — are
never asked out loud.

So this sub-tab is a lesson rather than a control panel. It changes nothing. Every number on it is
the live one from the prospect next door, because a worked example on the reader's own numbers
is the only kind anyone finishes reading.

The order is the formula's order, not the software's:

    P(HC | DHI) = P(DHI | HC) . P(HC) / P(DHI)

prior, then likelihood, then the rival likelihood nobody remembers to write down, then the branch
where the pick is wrong, then the ratio that makes the denominator vanish, then the arithmetic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hcwc.core import dhi as dhi_core
from hcwc.core import pos
from hcwc.ui import theme
from hcwc.ui.numbering import Numbering

TAB = 5
PRIOR = "#8CB7FC"
POSTERIOR = "#C44E52"
FLAT = "#8A8A8A"


def _odds(p: float) -> float:
    return p / (1.0 - p) if 0.0 < p < 1.0 else float("nan")


def render(n: Numbering | None = None) -> None:
    n = n or Numbering(TAB)
    post = st.session_state.get("dhi_posterior") if st.session_state.get("dhi_on") else None
    overlay = st.session_state.get("dhi_overlay")
    if post is None or overlay is None:
        st.info(
            "This page runs on the current prospect's numbers, so it needs an observation first: "
            "**This is a DHI prospect** on tab 2.0, then the amplitude on tab 5.1. "
            "Everything here is explanation; nothing on this page changes a result."
        )
        return

    result, observation, detection = post.result, post.observation, post.detection
    apex = float(np.median(result.apex_m))
    h_min = float(overlay["h_min"])
    prior_pos, posterior_pos = float(overlay["prior_pos"]), float(overlay["posterior_pos"])
    element_pos = st.session_state.get("element_pos") or {}
    element_product = pos.accumulation_chance(element_pos)

    st.markdown(
        "Nothing on this page changes a result. It is the update tab 5.1 performs, "
        "taken apart one term at a time, on the current prospect's numbers.\n\n"
        "The rule as usually taught appears to need something that cannot be estimated:"
    )
    st.latex(r"P(\mathrm{HC} \mid \mathrm{DHI}) = "
             r"\frac{P(\mathrm{DHI} \mid \mathrm{HC}) \; P(\mathrm{HC})}{P(\mathrm{DHI})}")
    st.markdown(
        "`P(DHI)` is the chance of seeing this amplitude across all possible worlds. Step 5 "
        "shows why it is never needed.")

    # ------------------------------------------------------------------ 1 · the prior
    st.markdown("##### Step 1 · P(HC): the state of belief before the seismic")
    st.markdown(
        "The prior is everything on tabs 2.0 and 3.0 and nothing else. It has two parts, and "
        "they are kept apart throughout:\n\n"
        f"- a number, `P(G) = {element_product:.3f}`, the chance the prospect works at all: the "
        "product of the element chances on tab 2.0;\n"
        f"- a distribution, `p(h | G)`, the column height given that it works: the "
        "competing-limits model on tab 3.0.\n\n"
        "The prospect POS is neither. It is a reading of the two together, and it cannot be "
        "quoted without the column height at which it was read:"
    )
    st.latex(r"P(\mathrm{HC}) = P(G) \times P(h \geq h_{\min} \mid G) = "
             rf"{element_product:.3f} \times {prior_pos / max(element_product, 1e-12):.3f} = "
             rf"\mathbf{{{prior_pos:.3f}}}")

    prior_contacts = result.contact_m
    figp = go.Figure()
    figp.add_histogram(x=prior_contacts, nbinsx=70, marker_color=PRIOR, opacity=0.85,
                       name="geological contact, before the DHI")
    figp.add_vline(x=apex + h_min, line=dict(color=theme.INK, dash="dash"),
                   annotation_text=f"assessment minimum, {apex + h_min:,.0f} m",
                   annotation_position="top right")
    figp.update_layout(xaxis_title="Contact depth (m TVDSS)", yaxis_title="Realisations",
                       height=320, margin=dict(t=20), showlegend=False)
    n.plot(figp,
           "The prior, drawn. This is tab 4.0's answer, and the model assumes it contains no "
           "seismic amplitude; the assumption cannot be checked here.\n\n"
           "It is also the assumption most often false in practice. Where the closure was mapped "
           "with the anomaly on screen, the apex above all, since it enters the likelihood "
           "directly as `apex + h`, the prior already carries the DHI, and multiplying by the DHI "
           "likelihood counts the same evidence twice. Correct arithmetic downstream does not "
           "repair a prior that has already seen the answer.")

    # ------------------------------------------------------------------ 2 · the likelihood
    st.markdown("##### Step 2 · P(DHI | HC): the chance of this observation if the prospect works")
    st.markdown(
        "The term is usually found hard because it runs backwards from the question of interest. "
        "The question is about the prospect given the seismic; Bayes' rule asks about the seismic "
        "given the prospect.\n\n"
        "Two factors multiply, and they answer different questions:"
    )
    grid = np.linspace(0.0, float(np.percentile(result.column_m, 99.5)), 400)
    d_curve = detection.at(grid)
    figl = go.Figure()
    figl.add_scatter(x=grid, y=d_curve, mode="lines", name="D(h): would the column show at all?",
                     line=dict(color=PRIOR, width=2.6))
    if observation.is_partial:
        # The bound is a censored pick: the edge lies above the cutoff, to within the same error
        # a picked contact carries, so the curve is the normal cumulative where a pick's is the
        # density. Plotted on the same axes so the shapes can be compared directly.
        from scipy.stats import norm as _norm
        h_off = observation.absent_below_m - apex
        bound_curve = _norm.cdf((h_off - grid) / observation.pick_sigma_m)
        figl.add_scatter(x=grid, y=bound_curve, mode="lines",
                         name="Φ((z_off − z) / σ): does the edge lie above the cutoff?",
                         line=dict(color=POSTERIOR, width=2.6))
        product = d_curve * bound_curve
        figl.add_scatter(x=grid, y=product / (float(product.max()) or 1.0), mode="lines",
                         name="their product", line=dict(color=theme.INK, width=3.2, dash="dot"))
    elif observation.seen:
        pick_curve = observation.pick_pdf(apex + grid)
        scale = float(pick_curve.max()) or 1.0
        figl.add_scatter(x=grid, y=pick_curve / scale, mode="lines",
                         name="Pick(z | apex + h): would it have terminated there?",
                         line=dict(color=POSTERIOR, width=2.6))
        product = d_curve * pick_curve
        figl.add_scatter(x=grid, y=product / (float(product.max()) or 1.0), mode="lines",
                         name="their product", line=dict(color=theme.INK, width=3.2, dash="dot"))
    figl.update_layout(xaxis_title="Column height h (m)", yaxis_title="Relative likelihood",
                       height=360, margin=dict(t=20), legend=dict(orientation="h", y=-0.24))
    n.plot(figl,
           "Two questions, one product. `D(h)` asks whether a column of that height would have "
           "shown at all; it is near zero below tuning thickness and flat above resolution. The "
           "pick likelihood asks whether, having shown, it would have terminated where the "
           "observed one did.\n\n"
           "Their product peaks at the column heights that explain the observation best. Curves "
           "are scaled to a common height; only their shapes carry meaning.")

    # ------------------------------------------------------------------ 3 · the rival
    st.markdown("##### Step 3 · P(DHI | no HC): the chance of the same observation if it does not")
    # Guarded on `dhi_on` like every other reader of a `dhi_` output. Switching the DHI off clears
    # `dhi_overlay` but leaves this and `dhi_posterior` behind, so an unguarded read is a stale
    # strength waiting for the day this function is called from somewhere that does not return
    # early when there is no DHI.
    r_strength = (st.session_state.get("dhi_r_strength")
                  if st.session_state.get("dhi_on") else None)
    # The ratio the tab applied: the strength when something was seen, the absence ratio when
    # nothing was. Falls back to recomputing from the posterior's own detection function so a
    # stale key cannot put a strength on an absent anomaly.
    r_applied = (float(st.session_state.get("dhi_r_applied"))
                 if st.session_state.get("dhi_r_applied") is not None
                 else dhi_core.applied_ratio(result, detection, observation, r_strength or 1.0))
    st.markdown(
        "This is the term most often skipped, and the reason bright amplitudes over-persuade. "
        "An observation is evidence only to the extent that it is more likely under G, an "
        "accumulation, than under not G. An anomaly that would have appeared either way carries "
        "no information, "
        "however convincing it looks.\n\n"
        "The tool answers it in two places, one for each thing the amplitude carries:"
    )
    rows = [{"Aspect of the observation": ("Character: how hydrocarbon-like the amplitude looks"
                                           if observation.seen else
                                           "Absence: nothing shows where a column would have"),
             "Answered by": ("the DHI evidence-strength model, tab 5.1 §2" if observation.seen
                             else "P(absent | G) / P(absent | no hydrocarbons), tab 5.1 §3b"),
             "Updates": "P(G), the chance the elements worked",
             "Gives": f"R = {r_applied:.2f}"},
            {"Aspect of the observation": "Geometry: where the event terminates",
             "Answered by": "the pick likelihood against a flat rival, step 4 below",
             "Updates": "p(h | G), the column given that they worked",
             "Gives": f"floor 1 − p_valid = {1 - observation.p_valid:.2f}"}]
    n.table(pd.DataFrame(rows),
            "Two aspects of one observation, answering two questions. Each updates its own "
            "factor of the chance and neither is applied to the other's, so nothing is counted "
            "twice and nothing has to be discounted.")

    # ------------------------------------------------------------------ 4 · the two branches
    st.markdown("##### Step 4 · The case where the picked event is not the contact")
    st.markdown(
        "A flat event can be lithology, a diagenetic front, fizz gas read as pay, or a processing "
        "artefact. Writing `V` for *the indicated event is in fact the contact*, the likelihood is two "
        "stories, weighted:"
    )
    st.latex(r"L(E \mid G, h) = \underbrace{p_{\mathrm{valid}} \cdot D(h) \cdot "
             r"\mathrm{Pick}(z \mid \mathrm{apex} + h)}_{V:\ \text{the pick locates the contact}}"
             r" \;+\; \underbrace{(1 - p_{\mathrm{valid}}) \cdot c}"
             r"_{\neg V:\ \text{it says nothing about depth}}")
    st.markdown(
        f"With `p_valid = {observation.p_valid:.2f}`: the chance the picked event is the "
        "contact, given that there is hydrocarbon for it to be the contact of. It is the "
        "contact-attribute judgement from tab 5.1 §3 and carries nothing about whether "
        "there is hydrocarbon, since every realisation it weights already assumes there is.\n\n"
        "The second branch is flat in depth, so the geological prior passes through it "
        "untouched. That is what stops one seismic pick from ever declaring a contact depth "
        "impossible."
    )

    if observation.seen:
        depths = apex + grid
        d_at = detection.at(result.column_m)
        if observation.is_partial:
            # The same three branches, for the bound. The spurious one is a bare 1 rather than a
            # density: with the bright event unrelated to the column, its down-dip edge is wherever
            # that thing ends, so this observation is what you would have recorded either way.
            from scipy.stats import norm as _norm
            valid_at = d_at * _norm.cdf(
                (observation.absent_below_m - result.contact_m) / observation.pick_sigma_m)
            c = 1.0
            labels = ("V alone — the edge does lie above the cutoff",
                      "¬V alone — the bright event is not the column")
        else:
            valid_at = d_at * observation.pick_pdf(result.contact_m)
            c = dhi_core.spurious_density(result.limit_set.contact_support_m())
            labels = ("V alone — the pick is the contact",
                      "¬V alone — the pick is spurious")
        branches = {
            labels[0]: valid_at,
            labels[1]: np.full(result.n, c),
            f"the mixture, p_valid = {observation.p_valid:.2f}": (
                observation.p_valid * valid_at + (1 - observation.p_valid) * c),
        }
        figb = go.Figure()
        for (label, w), colour, dash in zip(branches.items(), (POSTERIOR, FLAT, theme.INK),
                                            ("dot", "dash", "solid")):
            total = float(w.sum())
            curve = [float((w * (result.contact_m >= z)).sum() / total) for z in depths]
            figb.add_scatter(x=curve, y=depths, mode="lines", name=label,
                             line=dict(color=colour, width=3.0 if dash == "solid" else 2.2,
                                       dash=dash))
        figb.update_layout(xaxis_title="P(contact at least this deep)",
                           yaxis_title="Contact depth (m TVDSS)",
                           yaxis=dict(autorange="reversed"), height=440, margin=dict(t=20),
                           legend=dict(orientation="h", y=-0.2))
        n.plot(figb,
               "The grey dashed line is the geological model, unchanged. That is branch ¬V: if "
               "the picked event is not the contact, tab 4.0's answer stands as it was.\n\n"
               "The mixture never leaves the corridor between the two branches, so it cannot reach "
               "zero while the grey line is above zero. That is the guarantee: no contact depth "
               f"is excluded, because every depth keeps at least {1 - observation.p_valid:.2f} of "
               "the flat alternative. How strongly the pick favours one depth over another is "
               "set by its width, not by c.")

    # ------------------------------------------------------------------ 5 · the ratio
    st.markdown("##### Step 5 · R, and where the intractable term went")
    st.markdown(
        "Bayes' rule written twice, once for G and once for not G, and divided one by the "
        "other. `P(DHI)` is the same in both, so it cancels:")
    st.latex(r"\underbrace{\frac{P(\mathrm{HC} \mid \mathrm{DHI})}"
             r"{P(\mathrm{no\ HC} \mid \mathrm{DHI})}}_{\text{posterior odds}} = "
             r"\underbrace{\frac{P(\mathrm{DHI} \mid \mathrm{HC})}"
             r"{P(\mathrm{DHI} \mid \mathrm{no\ HC})}}_{R} \times "
             r"\underbrace{\frac{P(\mathrm{HC})}{P(\mathrm{no\ HC})}}_{\text{prior odds}}")
    st.markdown(
        "That is the whole method. The one question a DHI has to answer is how much more "
        "likely the observation was if the prospect works than if it does not; the absolute "
        "probability of the observation is never computed.\n\n"
        "It also makes the two extremes legible:\n\n"
        "- R = 0 says the observation was impossible under G. Posterior odds zero, and no "
        "prior survives it, which is why step 4 exists.\n"
        "- R = ∞ says it was impossible under not G.\n\n"
        "Neither should come out of one seismic interpretation. The tool caps R at "
        f"{dhi_core.R_SINGLE_CHANNEL:.0f} and floors it at "
        f"{1.0 / dhi_core.R_SINGLE_CHANNEL:g} so that it cannot.")

    # ------------------------------------------------------------------ 6 · the arithmetic
    st.markdown("##### Step 6 · The arithmetic, on this prospect")
    st.markdown(
        "The odds form above is applied to one factor, the chance the elements worked. The pick "
        "then updates the other factor, the column given that they did, and the two multiply."
    )
    p_g_updated = dhi_core.p_g_given_strength(element_product, r_applied)
    prior_odds, posterior_odds = _odds(element_product), _odds(p_g_updated)
    f_prior, f_post = float(post.pos(posterior=False)), float(post.pos())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prior odds on G", f"{prior_odds:.3f}", f"P(G) {element_product:.1%}",
              delta_color="off")
    c2.metric("× R, amplitude" if observation.seen else "× R, absence", f"{r_applied:.3f}",
              "character channel" if observation.seen else "absence channel", delta_color="off")
    _ev = "amplitude" if observation.seen else "absence"
    _geo = "pick" if observation.seen else "absence"
    c3.metric(f"= P(G | {_ev})", f"{p_g_updated:.1%}", f"odds {posterior_odds:.3f}",
              delta_color="off")
    c4.metric(f"× P(column ≥ {h_min:.0f} m | G, {_geo})", f"{f_post:.1%}",
              f"geological {f_prior:.1%}", delta_color="off")
    st.latex(rf"{prior_odds:.3f} \times {r_applied:.3f} = {posterior_odds:.3f} "
             rf"\;\Longrightarrow\; P(G \mid \mathrm{{{_ev}}}) = {p_g_updated:.3f}"
             # `%` opens a comment in LaTeX, so a percentage has to be escaped or KaTeX renders
             # the whole line as red source.
             rf"\qquad {p_g_updated:.3f} \times {f_post:.3f} = "
             rf"\mathbf{{{posterior_pos * 100:.1f}\%}}")
    st.caption(
        f"The prior prospect chance was P(G) × F(h_min) = {element_product:.3f} × "
        f"{f_prior:.3f} = {prior_pos:.1%}. The second factor is read off the same weighted "
        f"realisations that draw the contact distribution on tab 5.1, so the histogram, the "
        f"percentiles and the chance are one object."
    )

    if f_prior >= 0.999:
        st.info(
            f"At an assessment minimum of {h_min:.0f} m the column term is 1 before and after "
            f"the update: every realisation clears it. The {_geo} reshapes the contact "
            f"distribution and cannot move the chance here; the whole move comes from the "
            f"{_ev}. A minimum a real share of realisations miss lets the {_geo} reach the "
            f"chance, and once it sits below the indicated contact the pick lowers the chance, which "
            f"is the reading of being asked for more column than the amplitude supports."
        )
