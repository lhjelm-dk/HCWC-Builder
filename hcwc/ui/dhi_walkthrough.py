"""Tab ⑤ sub-tab ① — the Bayesian update, walked through one term at a time.

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
            "Turn on *This is a DHI prospect* on tab ②, then describe the amplitude on sub-tab ②. "
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
        "The prior is everything on tabs ② and ③ and **nothing else**. It has two parts, and "
        "keeping them apart is most of the battle:\n\n"
        f"- **a number** — `P(G) = {element_product:.3f}`, the chance the prospect works at all. "
        "The product of the element chances on tab ②.\n"
        f"- **a distribution** — `p(h | G)`, how tall the column is *given* it works. The "
        "competing-limits model on tab ③.\n\n"
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
           "**The prior, drawn.** This is tab ④'s answer and it contains no seismic amplitude — "
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
    if observation.seen:
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
    r_strength = st.session_state.get("dhi_r_strength")
    st.markdown(
        "**This is the term geoscientists skip, and it is why bright amplitudes over-persuade.** "
        "An observation is only evidence to the extent that it is *more* likely under success "
        "than under failure. An anomaly you would have seen either way tells you nothing, however "
        "convincing it looks.\n\n"
        "Your tool answers it in two places, one for each thing the amplitude carries:"
    )
    rows = [{"Aspect of the observation": "**Character** — how hydrocarbon-like the amplitude looks",
             "Answered by": "the two-curve strength model, sub-tab ② §2",
             "Gives": f"R = {r_strength:.2f}" if r_strength else "R from strength"},
            {"Aspect of the observation": "**Geometry** — where the event terminates",
             "Answered by": "the pick likelihood against a flat rival, §4 below",
             "Gives": f"floor 1 − p_valid = {1 - observation.p_valid:.3f}"}]
    n.table(pd.DataFrame(rows),
            "**Two aspects of one observation, not two observations.** They are combined with a "
            "discount for exactly that reason — see sub-tab ② §5, where `dependence` lives.")

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
        f"With `p_valid = {observation.p_valid:.3f}`, derived from the DHI strength.\n\n"
        "**The second branch is flat in depth, so the geological prior passes through it "
        "untouched.** That is not a patch — it is what stops one seismic pick from ever declaring "
        "a contact depth impossible."
    )

    if observation.seen:
        depths = apex + grid
        d_at = detection.at(result.column_m)
        pick_at = observation.pick_pdf(result.contact_m)
        c = dhi_core.spurious_density(result.contact_m)
        branches = {
            "V alone — the pick is the contact": d_at * pick_at,
            "¬V alone — the pick is spurious": np.full(result.n, c),
            f"the mixture, p_valid = {observation.p_valid:.2f}": (
                observation.p_valid * d_at * pick_at + (1 - observation.p_valid) * c),
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
               "if the picked event is not the contact, tab ④'s answer stands exactly as it was.\n\n"
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
        f"**{dhi_core.R_CAP:.0f}** and floors it at **{dhi_core.R_FLOOR:g}** so that it cannot.")

    # ------------------------------------------------------------------ 6 · the arithmetic
    st.markdown("#### Step 6 · The arithmetic, on this prospect")
    prior_odds, posterior_odds = _odds(prior_pos), _odds(posterior_pos)
    r_combined = posterior_odds / prior_odds if prior_odds else float("nan")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prior odds", f"{prior_odds:.3f}", f"POS {prior_pos:.1%}", delta_color="off")
    c2.metric("× R combined", f"{r_combined:.3f}", "both channels, discounted", delta_color="off")
    c3.metric("= Posterior odds", f"{posterior_odds:.3f}", delta_color="off")
    c4.metric("Posterior POS", f"{posterior_pos:.1%}", f"{posterior_pos - prior_pos:+.1%}")
    st.latex(rf"{prior_odds:.3f} \times {r_combined:.3f} = {posterior_odds:.3f} "
             rf"\quad\Longrightarrow\quad \frac{{{posterior_odds:.3f}}}"
             rf"{{1 + {posterior_odds:.3f}}} = \mathbf{{{posterior_pos:.1%}}}")

    r_geometry = float(post.r_dhi)
    if np.isnan(r_geometry):
        st.warning(
            f"**All of that came from the strength slider.** At an assessment minimum of "
            f"{h_min:.0f} m every realisation counts as a success, so there is no failure set for "
            "the geometry channel to compare against and `R geometry` is undefined. The flat "
            "spot's *position* reshapes your contact distribution and moves your POS by nothing.\n\n"
            "Raise the assessment minimum on tab ② and geometry starts paying in — and once the "
            "minimum sits below the picked contact, it pays in **negatively**, which is the "
            "downgrade you would expect from being asked for more column than the amplitude "
            "supports."
        )
    else:
        st.caption(
            f"**R geometry = {r_geometry:.3f}** and **R strength = "
            f"{r_strength:.2f}**" if r_strength else f"**R geometry = {r_geometry:.3f}**")
