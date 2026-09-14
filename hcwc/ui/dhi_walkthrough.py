"""Tab 5.0 sub-tab 1.0 — the Bayesian update, walked through one term at a time.

The rest of this tab applies Bayes' rule nine times and never once writes it down. A geoscientist
who wants to check the reasoning has nowhere to look, and the two questions that actually stop
people — *where did the denominator go* and *what if the thing I picked is not the contact* — are
never asked out loud.

So this sub-tab is a lesson rather than a control panel. It changes nothing. Every number on it is
the live one from the prospect next door, because a worked example with your own prospect's numbers
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
            "**This page runs on your own prospect's numbers, so it needs an observation first.** "
            "Turn on *This is a DHI prospect* on tab 2.0, then describe the amplitude on sub-tab 2.0. "
            "Everything here is explanation — nothing on this page changes a result."
        )
        return

    result, observation, detection = post.result, post.observation, post.detection
    apex = float(np.median(result.apex_m))
    h_min = float(overlay["h_min"])
    prior_pos, posterior_pos = float(overlay["prior_pos"]), float(overlay["posterior_pos"])
    element_pos = st.session_state.get("element_pos") or {}
    element_product = (float(np.prod([float(v) for v in element_pos.values()]))
                       if element_pos else 1.0)

    st.markdown(
        "**Nothing on this page changes anything.** It is the same update the next sub-tab "
        "performs, taken apart one term at a time, on your numbers.\n\n"
        "The rule everybody is taught looks like it needs something impossible:"
    )
    st.latex(r"P(\mathrm{HC} \mid \mathrm{DHI}) = "
             r"\frac{P(\mathrm{DHI} \mid \mathrm{HC}) \; P(\mathrm{HC})}{P(\mathrm{DHI})}")
    st.markdown(
        "`P(DHI)` is the chance of seeing this amplitude across *all* possible worlds, and nobody "
        "can estimate that. **§5 shows why you never have to.**")

    # ------------------------------------------------------------------ 1 · the prior
    st.markdown("#### Step 1 · P(HC) — what you believed before the seismic")
    st.markdown(
        "The prior is everything on tabs 2.0 and 3.0 and **nothing else**. It has two parts, and "
        "keeping them apart is most of the battle:\n\n"
        f"- **a number** — `P(G) = {element_product:.3f}`, the chance the prospect works at all. "
        "The product of the element chances on tab 2.0.\n"
        f"- **a distribution** — `p(h | G)`, how tall the column is *given* it works. The "
        "competing-limits model on tab 3.0.\n\n"
        "What people call *the prospect POS* is neither. It is a **reading** of the two together, "
        "and it cannot be quoted without saying at what column height it was read:"
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
           "**The prior, drawn.** This is tab 4.0's answer and it contains no seismic amplitude — "
           "that is an assumption the model makes and cannot check.\n\n"
           "⚠ **It is also the assumption most likely to be false in practice.** If the closure was "
           "mapped with the anomaly on screen — and the apex especially, since it enters the "
           "likelihood directly as `apex + h` — then the prior already knows about the DHI, and "
           "multiplying by the DHI likelihood counts the same evidence twice. No amount of correct "
           "arithmetic downstream survives a prior that has already seen the answer.")

    # ------------------------------------------------------------------ 2 · the likelihood
    st.markdown("#### Step 2 · P(DHI | HC) — if it really works, how likely was I to see this?")
    st.markdown(
        "The term everyone finds hard, because it runs **backwards** from the question you care "
        "about. You want to know about the prospect given the seismic; Bayes makes you answer "
        "about the seismic given the prospect.\n\n"
        "Two things multiply, and they answer different questions:"
    )
    grid = np.linspace(0.0, float(np.percentile(result.column_m, 99.5)), 400)
    d_curve = detection.at(grid)
    figl = go.Figure()
    figl.add_scatter(x=grid, y=d_curve, mode="lines", name="D(h) — would I have seen it at all?",
                     line=dict(color=PRIOR, width=2.6))
    if observation.is_partial:
        # The bound is a censored pick: the edge lies above the cutoff, to within the same error
        # a picked contact carries, so the curve is the normal cumulative where a pick's is the
        # density. Plotted on the same axes so the shapes can be compared directly.
        from scipy.stats import norm as _norm
        h_off = observation.absent_below_m - apex
        bound_curve = _norm.cdf((h_off - grid) / observation.pick_sigma_m)
        figl.add_scatter(x=grid, y=bound_curve, mode="lines",
                         name="Φ((z_off − z) / σ) — does the edge lie above the cutoff?",
                         line=dict(color=POSTERIOR, width=2.6))
        product = d_curve * bound_curve
        figl.add_scatter(x=grid, y=product / (float(product.max()) or 1.0), mode="lines",
                         name="their product", line=dict(color=theme.INK, width=3.2, dash="dot"))
    elif observation.seen:
        pick_curve = observation.pick_pdf(apex + grid)
        scale = float(pick_curve.max()) or 1.0
        figl.add_scatter(x=grid, y=pick_curve / scale, mode="lines",
                         name="Pick(z | apex + h) — would it have stopped there?",
                         line=dict(color=POSTERIOR, width=2.6))
        product = d_curve * pick_curve
        figl.add_scatter(x=grid, y=product / (float(product.max()) or 1.0), mode="lines",
                         name="their product", line=dict(color=theme.INK, width=3.2, dash="dot"))
    figl.update_layout(xaxis_title="Column height h (m)", yaxis_title="Relative likelihood",
                       height=360, margin=dict(t=20), legend=dict(orientation="h", y=-0.24))
    n.plot(figl,
           "**Two questions, one product.** `D(h)` asks whether a column of that height would have "
           "shown up at all — it is near zero below tuning thickness and flat above resolution. "
           "The pick likelihood asks whether, having shown up, it would have terminated where "
           "yours did.\n\n"
           "Their product peaks at the column heights that explain the observation best. Curves "
           "are scaled to a common height; only their shapes carry meaning.")

    # ------------------------------------------------------------------ 3 · the rival
    st.markdown("#### Step 3 · P(DHI | no HC) — and if it doesn't work, how likely was I anyway?")
    # Guarded on `dhi_on` like every other reader of a `dhi_` output. Switching the DHI off clears
    # `dhi_overlay` but leaves this and `dhi_posterior` behind, so an unguarded read is a stale
    # strength waiting for the day this function is called from somewhere that does not return
    # early when there is no DHI.
    r_strength = (st.session_state.get("dhi_r_strength")
                  if st.session_state.get("dhi_on") else None)
    st.markdown(
        "**This is the term geoscientists skip, and it is why bright amplitudes over-persuade.** "
        "An observation is only evidence to the extent that it is *more* likely under success "
        "than under failure. An anomaly you would have seen either way tells you nothing, however "
        "convincing it looks.\n\n"
        "Your tool answers it in two places, one for each thing the amplitude carries:"
    )
    rows = [{"Aspect of the observation": "Character: how hydrocarbon-like the amplitude looks",
             "Answered by": "the two-curve strength model, sub-tab 2.0 §2",
             "Updates": "P(G), the chance the elements worked",
             "Gives": f"R = {r_strength:.2f}" if r_strength else "R from strength"},
            {"Aspect of the observation": "Geometry: where the event terminates",
             "Answered by": "the pick likelihood against a flat rival, §4 below",
             "Updates": "p(h | G), the column given that they worked",
             "Gives": f"floor 1 − p_valid = {1 - observation.p_valid:.2f}"}]
    n.table(pd.DataFrame(rows),
            "Two aspects of one observation, answering two questions. Each updates its own "
            "factor of the chance and neither is applied to the other's, so nothing is counted "
            "twice and nothing has to be discounted.")

    # ------------------------------------------------------------------ 4 · the two branches
    st.markdown("#### Step 4 · What if the thing I picked isn't the contact at all?")
    st.markdown(
        "A flat event can be lithology, a diagenetic front, fizz gas read as pay, or a processing "
        "artefact. Writing `V` for *the picked event really is the contact*, the likelihood is two "
        "stories, weighted:"
    )
    st.latex(r"L(E \mid G, h) = \underbrace{p_{\mathrm{valid}} \cdot D(h) \cdot "
             r"\mathrm{Pick}(z \mid \mathrm{apex} + h)}_{V:\ \text{the pick locates the contact}}"
             r" \;+\; \underbrace{(1 - p_{\mathrm{valid}}) \cdot c}"
             r"_{\neg V:\ \text{it says nothing about depth}}")
    st.markdown(
        f"With `p_valid = {observation.p_valid:.2f}`: the chance the picked event is the "
        "contact, given that there is hydrocarbon for it to be the contact of. It is the "
        "contact-attribute judgement from sub-tab 2.0 §3 and carries nothing about whether "
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
            labels = ("V alone — the edge really lies above the cutoff",
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
               "**The grey dashed line is the geological model, unchanged.** That is branch ¬V — "
               "if the picked event is not the contact, tab 4.0's answer stands exactly as it was.\n\n"
               "The mixture never leaves the corridor between the two branches, so it can never "
               "reach zero while the grey line is above zero. Read that as the guarantee it is: "
               f"**the depth channel can say at most "
               f"{observation.p_valid / max(1 - observation.p_valid, 1e-9):.1f} : 1 against any "
               "contact depth**, however sharply you draw the pick.")

    # ------------------------------------------------------------------ 5 · the ratio
    st.markdown("#### Step 5 · R — and where the impossible term went")
    st.markdown(
        "Write Bayes' rule twice, once for success and once for failure, and divide one by the "
        "other. `P(DHI)` is the same in both, so it **cancels**:")
    st.latex(r"\underbrace{\frac{P(\mathrm{HC} \mid \mathrm{DHI})}"
             r"{P(\mathrm{no\ HC} \mid \mathrm{DHI})}}_{\text{posterior odds}} = "
             r"\underbrace{\frac{P(\mathrm{DHI} \mid \mathrm{HC})}"
             r"{P(\mathrm{DHI} \mid \mathrm{no\ HC})}}_{R} \times "
             r"\underbrace{\frac{P(\mathrm{HC})}{P(\mathrm{no\ HC})}}_{\text{prior odds}}")
    st.markdown(
        "**That is the whole method.** The only question a DHI ever has to answer is *how much "
        "more likely was this observation if the prospect works than if it doesn't* — and the "
        "term nobody could estimate never has to be computed.\n\n"
        "It also makes the two extremes legible:\n\n"
        "- **R = 0** says the observation was flatly impossible under success. Posterior odds "
        "zero, and no prior survives it — which is why §4 exists.\n"
        "- **R = ∞** says it was impossible under failure.\n\n"
        "Neither should ever come out of one seismic interpretation. Your tool caps R at "
        f"**{dhi_core.R_SINGLE_CHANNEL:.0f}** and floors it at "
        f"**{1.0 / dhi_core.R_SINGLE_CHANNEL:g}** so that it cannot.")

    # ------------------------------------------------------------------ 6 · the arithmetic
    st.markdown("#### Step 6 · The arithmetic, on this prospect")
    st.markdown(
        "The odds form above is applied to one factor, the chance the elements worked. The pick "
        "then updates the other factor, the column given that they did, and the two multiply."
    )
    r_applied = float(r_strength) if (r_strength and observation.seen) else 1.0
    p_g_updated = dhi_core.p_g_given_strength(element_product, r_applied)
    prior_odds, posterior_odds = _odds(element_product), _odds(p_g_updated)
    f_prior, f_post = float(post.pos(posterior=False)), float(post.pos())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prior odds on G", f"{prior_odds:.3f}", f"P(G) {element_product:.1%}",
              delta_color="off")
    c2.metric("× R, amplitude", f"{r_applied:.3f}", "character channel", delta_color="off")
    c3.metric("= P(G | amplitude)", f"{p_g_updated:.1%}", f"odds {posterior_odds:.3f}",
              delta_color="off")
    c4.metric(f"× P(column ≥ {h_min:.0f} m | G, pick)", f"{f_post:.1%}",
              f"geological {f_prior:.1%}", delta_color="off")
    st.latex(rf"{prior_odds:.3f} \times {r_applied:.3f} = {posterior_odds:.3f} "
             rf"\;\Longrightarrow\; P(G \mid \mathrm{{amplitude}}) = {p_g_updated:.3f}"
             rf"\qquad {p_g_updated:.3f} \times {f_post:.3f} = \mathbf{{{posterior_pos:.1%}}}")
    st.caption(
        f"The prior prospect chance was P(G) × F(h_min) = {element_product:.3f} × "
        f"{f_prior:.3f} = {prior_pos:.1%}. The second factor is read off the same weighted "
        f"realisations that draw the contact distribution on sub-tab 2.0, so the histogram, the "
        f"percentiles and the chance are one object."
    )

    if f_prior >= 0.999:
        st.info(
            f"At an assessment minimum of {h_min:.0f} m the column term is 1 before and after "
            f"the update: every realisation clears it. The pick reshapes the contact "
            f"distribution and cannot move the chance here; the whole move comes from the "
            f"amplitude. A minimum a real share of realisations miss lets the pick reach the "
            f"chance, and once it sits below the picked contact the pick lowers the chance, which "
            f"is the reading of being asked for more column than the amplitude supports."
        )
