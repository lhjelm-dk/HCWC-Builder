"""Tab ⑤ — the DHI update.

The headline is one figure: **POS against threshold**, prior and posterior, with markers at every
threshold anyone quotes a chance at. It exists to make one error impossible to commit — quoting a
POS read at the assessment minimum beside a volume read at the DHI case. On a scalar readout that
mistake is invisible; on this curve it is two different points.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hcwc.core import charge as ch
from hcwc.core import dhi as dhi_core
from hcwc.core import engine
from hcwc.core import sensitivity
from hcwc.core.dhi import DetectionFunction, DhiObservation
from hcwc.ui import run, theme
from hcwc.ui.numbering import Numbering

TAB = 5
PRIOR = "#8CB7FC"
POSTERIOR = "#C44E52"


def _fmt_r(r: float) -> str:
    """A likelihood ratio, formatted so an implausible one cannot masquerade as a precise one.

    The geometry channel is not clipped, and a sharp pick against a low assessment minimum can push
    it into the millions. Printing `15460945.21` gives a number that reads as a measurement; the
    scientific form reads as what it is, a ratio that has left the range anyone should quote.
    """
    if np.isnan(r):
        return "—"
    if r >= 1000.0:
        return f"{r:.1e}"
    if r <= 1.0 / 1000.0:
        return f"{r:.1e}"
    return f"{r:.2f}"


def _resample(values: np.ndarray, weights: np.ndarray, n: int = 20_000) -> np.ndarray:
    """Draw from ``values`` in proportion to ``weights`` -- the posterior as a sample.

    The DHI update is an importance weighting, so the posterior lives as *weights on the prior's
    realisations*. Anything that wants a distribution rather than a curve needs those weights
    collapsed into a sample, and resampling with replacement is the standard way.

    Its cost is honest and already reported: the effective sample size, in §5. A posterior
    resting on 300 distinct realisations resampled to 20 000 is still a posterior resting on
    300, and the number that says so is on the same tab.
    """
    total = float(np.sum(weights))
    if values.size == 0 or not np.isfinite(total) or total <= 0:
        return np.asarray(values, dtype=float)
    rng = np.random.default_rng(20260827)
    return np.asarray(values, dtype=float)[
        rng.choice(values.size, size=n, replace=True, p=np.asarray(weights, float) / total)]


def render(n: Numbering | None = None) -> None:
    # See the note in `results_tab.render`: one sequence per top-level tab, shared by its sub-tabs.
    n = n or Numbering(TAB)
    limit_set = st.session_state.get("limit_set")
    if limit_set is None:
        st.info("Define the limits on tab ③ first.")
        return
    result = run.current(limit_set)
    h_min = limit_set.min_column_m
    apex = float(np.median(result.apex_m))

    st.subheader("Direct hydrocarbon indicator")
    # The switch lives on tab 2 with the rest of the prospect's properties: whether a prospect has
    # a fluid indicator is a fact about the prospect, not a display option on the tab that uses it.
    if not st.session_state.get("dhi_on", False):
        st.markdown(
            "**This prospect is not marked as a DHI prospect.** Turn on *This is a DHI prospect* "
            "on tab ② to add a seismic amplitude as evidence. The geological model on tabs ③ to ④ "
            "stands on its own either way.\n\n"
            "**What a DHI may and may not do.** E-POS sets the ceiling: a fluid indicator can sense "
            "whether a reservoir exists and what fluid fills it, but *not which of charge, closure "
            "or retention failed*. So it may move POS and it may assert a contact depth. It may "
            "**not** tell you *which element failed*, which is why the element chances on tab ② "
            "are never touched here. It *may* tell you which limit set the contact, because "
            "knowing roughly where the contact sits is genuine evidence about which mechanism put "
            "it there — so tab ④'s controlling-limit diagnostic stays purely geological and its "
            "twin on this tab is the same diagnostic re-read through the amplitude."
        )
        # Otherwise a curve computed before the toggle was turned off would go on being drawn on
        # tab ④, which is the worst kind of stale: plausible, labelled, and wrong.
        st.session_state.pop("dhi_overlay", None)
        return

    theme.basis_banner(
        theme.GIVEN_DHI,
        "Every contact distribution below carries the amplitude evidence. The purely geological "
        "model is on tab ④ and is unchanged by anything here.")

    # ------------------------------------------------------------------ observation
    theme.heading(TAB, "1 · What was observed")
    seen = st.radio("Amplitude anomaly", ["Seen", "Absent where one was expected"],
                    horizontal=True) == "Seen"
    default_contact = float(np.percentile(result.contact_m, 50))
    shape = st.radio(
        "How is the pick shaped?", dhi_core.PICK_SHAPES, horizontal=True, disabled=not seen,
        format_func=lambda k: {dhi_core.NORMAL: "Normal — an unbiased estimate",
                               dhi_core.PERT: "Three-point — shallowest / likeliest / deepest",
                               dhi_core.UNIFORM: "Bracket — no preferred depth inside"}[k],
        help="Two of these are bounded, and a bound is a strong claim. It is safe here only "
             "because §2 keeps a floor under everything — see the note there.")

    shallowest = deepest = None
    if shape == dhi_core.NORMAL:
        o1, o2, o3 = st.columns(3)
        contact = o1.number_input(
            "Picked contact (m TVDSS)", 0.0, 10000.0, default_contact, 5.0, disabled=not seen,
            help="The down-dip amplitude termination or flat spot.")
        sigma = o2.number_input(
            "Pick σ (m)", 1.0, 500.0, 20.0, 1.0,
            help="Flat-spot pick uncertainty **plus depth-conversion error**. The second is "
                 "usually the larger, and it is the same uncertainty that moves the well's entry "
                 "depth — the one place this tool and WellVolPOS genuinely couple.")
    else:
        sigma = 20.0
        o1, o2, o3, o4 = st.columns(4)
        shallowest = o1.number_input(
            "Shallowest possible (m TVDSS)", 0.0, 10000.0, default_contact - 20.0, 5.0,
            disabled=not seen, help="Above this the contact cannot be — if the pick is right.")
        if shape == dhi_core.PERT:
            contact = o2.number_input(
                "Most likely (m TVDSS)", 0.0, 10000.0, default_contact, 5.0, disabled=not seen,
                help="The mode. Put it **above centre** to say the termination under-calls the "
                     "contact, which tuning and resolution loss at the base of a column both "
                     "argue for. That is the control that moves the reading at the pick.")
            deepest = o3.number_input(
                "Deepest possible (m TVDSS)", 0.0, 10000.0, default_contact + 20.0, 5.0,
                disabled=not seen)
        else:
            deepest = o2.number_input(
                "Deepest possible (m TVDSS)", 0.0, 10000.0, default_contact + 20.0, 5.0,
                disabled=not seen)
            contact = 0.5 * (shallowest + deepest)
            o3.metric("Bracket centre", f"{contact:,.0f} m")
    area = (o4 if shape != dhi_core.NORMAL else o3).number_input(
        "Anomaly area (km²), optional", 0.0, 1000.0, 0.0, 0.5,
        help="Used for the cross-check in §8. Leave at zero to skip.")

    if seen and shape != dhi_core.NORMAL and not shallowest < deepest:
        st.error("**The deepest possible contact must lie below the shallowest.**")
        return
    if seen and shape == dhi_core.PERT and not shallowest <= contact <= deepest:
        st.error("**The most likely contact must lie between the two bounds.**")
        return

    # ------------------------------------------------------------------ strength channel
    theme.heading(TAB, "2 · DHI strength — the amplitude channel")
    st.markdown(
        """
**A DHI carries two independent kinds of evidence, and this is the second one.** §1 recorded
*where* the anomaly terminates; §§3–4 turn that geometry into a likelihood. This section is about
its **character** instead: how bright, how consistent with the expected fluid response, how
convincing as an amplitude. §5 combines the two.

The construction is E-POS's, adapted from the custom R tool. Draw how a hydrocarbon-bearing
prospect tends to look on a common strength axis, draw how a non-hydrocarbon one looks, then read
off where *this* prospect sits. The likelihood ratio is the ratio of the two curve heights at that
reading, `R = pdf_HC(s) / pdf_NoHC(s)`.

**The axis has no units and does not need any.** R depends only on the *relative* heights of the
two curves where you read them, so −100 to 100 is a canvas, not a measurement. What carries meaning
is where your prospect sits relative to the two populations you drew.
"""
    )

    strength = st.slider(
        "DHI strength", -100.0, 100.0, dhi_core.DEFAULT_STRENGTH, 1.0,
        help="E-POS's default is 7 — just above the crossing point, so an assessor who moves "
             "nothing states a barely-supportive DHI rather than a neutral one.")

    with st.expander("The two populations (E-POS defaults)"):
        st.caption(
            "Each case is a Gaussian given by its 1st and 99th percentiles. Widen a case to say "
            "that class of prospect is more variable on this axis; move them apart to say the DHI "
            "separates the two populations well. **Overlapping curves are the honest default** — a "
            "DHI that cleanly separated hydrocarbon from brine would not need a probability.")
        h1, h2, h3, h4 = st.columns(4)
        hc = dhi_core.StrengthCase(
            h1.number_input("HC, P1", -200.0, 200.0, -50.0, 5.0),
            h2.number_input("HC, P99", -200.0, 200.0, 100.0, 5.0))
        no_hc = dhi_core.StrengthCase(
            h3.number_input("No HC, P1", -200.0, 200.0, -100.0, 5.0),
            h4.number_input("No HC, P99", -200.0, 200.0, 50.0, 5.0))
    model = dhi_core.StrengthModel(hc=hc, no_hc=no_hc)
    r_strength = model.r_at(strength)
    band, band_note = dhi_core.strength_bands(r_strength)

    axis = np.linspace(-160.0, 160.0, 400)
    figs = go.Figure()
    figs.add_scatter(x=axis, y=hc.pdf(axis), mode="lines", name="hydrocarbon-bearing",
                     line=dict(color=POSTERIOR, width=2.5))
    figs.add_scatter(x=axis, y=no_hc.pdf(axis), mode="lines", name="not hydrocarbon-bearing",
                     line=dict(color=PRIOR, width=2.5))
    figs.add_scatter(x=[strength, strength], y=[0.0, max(float(hc.pdf(strength)),
                                                         float(no_hc.pdf(strength)))],
                     mode="lines", name="this prospect", line=dict(color=theme.INK, dash="dot"))
    for case, colour in ((hc, POSTERIOR), (no_hc, PRIOR)):
        figs.add_scatter(x=[strength], y=[float(case.pdf(strength))], mode="markers",
                         showlegend=False, marker=dict(color=colour, size=9))
    figs.update_layout(xaxis_title="DHI strength (arbitrary axis)", yaxis_title="Density",
                       height=340, margin=dict(t=20), legend=dict(orientation="h", y=-0.22))
    n.plot(figs, f"The two-curve strength model, read at **{strength:,.0f}**. R is the ratio of the "
                 f"two marked heights — which is why the units on the axis never matter.")

    # Two metrics, not three. "POS on strength alone" needs the prior, which is not computed until
    # the channels are combined -- and a chance is a result rather than an input, so it belongs
    # there and not here. It moved with the reorder rather than being dropped.
    s1, s2 = st.columns(2)
    s1.metric("R from strength", f"{r_strength:.2f}", band, delta_color="off")
    s2.metric("DHI volume weight", f"{dhi_core.volume_weight(r_strength):.3f}",
              "R / (R + 1)", delta_color="off")
    st.caption(
        f"**{band} — {band_note}** Simm's caution is worth repeating: for a *single* line of "
        f"fluid-indicator evidence an honest R rarely exceeds about 3 either way, and anything past "
        f"10 should send you back to the two curves rather than into the volumetrics.\n\n"
        f"**Never read the band alone \u2014 read it against what it does to the prior, in \u00a75.** They "
        f"can disagree in a way that misleads: at the default reading of 7 the band is "
        f"*Negligible*, and yet a 30 % prior becomes **37.5 %**, a 7.5-point move from a slider "
        f"nobody touched. The band grades the strength of the *evidence*; the shift also depends "
        f"on where the prior already sat, and it is largest for the mid priors most prospects "
        f"have.\n\n"
        f"**The volume weight is not a POS.** It is `R / (R + 1)` — the weight the amplitude "
        f"evidence alone would carry against an even prior. Quoting it as a chance of success is "
        f"the error the name invites, and it is a common one."
    )

    # ------------------------------------------------------------------ p_valid
    # The volume weight has a second job. Read as a probability it is exactly the question the
    # depth channel needs answered -- is the thing I picked really the contact -- and using it
    # there makes the floor `1/(R+1)`, which the capped R can never drive to zero.
    # Published for the walkthrough sub-tab, which explains this number rather than
    # producing it. Same one-frame lag as everything else that crosses a sub-tab boundary.
    st.session_state["dhi_r_strength"] = float(r_strength)
    derived_p_valid = dhi_core.volume_weight(r_strength)
    with st.expander(f"**Is the picked event really the contact?** "
                     f"p_valid = {derived_p_valid:.3f}, from the strength above"):
        st.markdown(
            "A flat event can be lithology, a diagenetic front, fizz gas read as pay, or a "
            "processing artefact. **`p_valid` is the chance it is none of those**, and it decides "
            "how much of the contact depth the pick is allowed to settle.\n\n"
            "The rest of the probability goes to a branch where the pick says nothing about depth "
            "and *the geological model on tab ④ stands untouched*. That branch is what keeps the "
            "chance from ever reaching zero, however sharply the pick is drawn:\n\n"
            f"- the depth channel can say at most **{derived_p_valid / (1 - derived_p_valid):.1f} : 1** "
            f"against any contact depth\n"
            f"- and never more than **{dhi_core.R_CAP:.0f} : 1**, because R is capped — so a "
            "bounded pick shape is safe to use\n\n"
            "**Where this mapping can be wrong.** The strength axis measures how *hydrocarbon-like "
            "the amplitude looks*, not how reliably the event locates a contact. A dim but "
            "geometrically perfect flat spot is an excellent contact indicator and gets an "
            "unfairly low `p_valid` here; a bright non-conformable blob gets an unfairly high one. "
            "Override it when that is the case — and if you are overriding often, the mapping "
            "is wrong and worth telling me about."
        )
        if st.checkbox("Set p_valid myself", value=False):
            p_valid = st.slider("p_valid", 0.05, 0.99, float(round(derived_p_valid, 2)), 0.01,
                                help="1.0 is deliberately unreachable: it would say the pick is "
                                     "certainly the contact, and certainty cannot be argued with.")
        else:
            p_valid = derived_p_valid

    # ------------------------------------------------------------------ combining
    theme.heading(TAB, "3 · Detection function D(h)")
    st.markdown(
        "The chance a column of height *h* produces a **detectable** anomaly. Near zero below "
        "tuning thickness, rising through the resolution limit, then flat. It is what makes an "
        "absent anomaly usable evidence rather than a special case — the likelihood is simply "
        "`1 − D(h)`, which is largest at small *h*."
    )
    d1, d2, d3 = st.columns(3)
    h50 = d1.number_input("50 % detection column (m)", 1.0, 500.0, 25.0, 1.0,
                          help="Roughly the tuning thickness for this reservoir and frequency.")
    steep = d2.number_input("Transition width (m)", 1.0, 200.0, 8.0, 1.0)
    ceiling = d3.number_input("Ceiling", 0.05, 1.0, 0.90, 0.01,
                              help="Below 1 on purpose. A thick column can still fail to show, and "
                                   "a function reaching certainty would make an absent anomaly "
                                   "infinitely strong evidence.")
    detection = DetectionFunction(h50_m=h50, steepness_m=steep, ceiling=ceiling)

    grid = np.linspace(0.0, max(float(result.column_m.max()), h50 * 3), 300)
    figd = go.Figure()
    figd.add_scatter(x=detection.at(grid), y=apex + grid, mode="lines", name="D(h)",
                     line=dict(color=POSTERIOR, width=3))
    figd.add_hline(y=apex + h50, line=dict(color="#888", dash="dot"),
                   annotation_text=f"50 % at {h50:.0f} m column")
    figd.update_layout(xaxis_title="P(detectable)", xaxis_range=[0, 1],
                       yaxis_title="Contact depth (m TVDSS)", yaxis=dict(autorange="reversed"),
                       height=380, margin=dict(t=20), showlegend=False)
    n.plot(figd, "The detection function. **Its shape is a modelling choice, not physics** — a "
                 "Class III sand can become *less* visible when very thick, as the top and base "
                 "responses separate. Logistic is a defensible default and is exposed rather than "
                 "hard-coded for that reason.")

    # ------------------------------------------------------------------ the update
    theme.heading(TAB, "4 · POS against threshold")
    observation = DhiObservation(seen=seen, contact_m=contact if seen else None,
                                 pick_sigma_m=sigma, area_km2=area or None,
                                 pick_shape=shape, shallowest_m=shallowest, deepest_m=deepest,
                                 p_valid=p_valid)
    try:
        post = dhi_core.update(result, detection, observation)
    except ValueError as exc:
        st.error(str(exc))
        return

    # Published for the trust panel on tab ④, which reports the effective sample size behind this
    # update. Same one-frame lag as `dhi_overlay` below and for the same reason: tab ④ renders
    # first, so it reads the posterior built on the previous run. Every interaction reruns both.
    st.session_state["dhi_posterior"] = post

    if np.isnan(post.r_dhi):
        st.info(
            "**R is undefined here.** It compares the likelihood over the success cases against "
            "the likelihood over the failures, and with the assessment minimum at "
            f"{h_min:.0f} m every realisation counts as a success — so there is no failure set to "
            "compare against. Set a minimum column height on tab ② to get a likelihood ratio "
            "comparable with E-POS's `r_dfi`."
        )

    if post.effective_sample_size < 300:
        st.warning(
            f"**Effective sample size {post.effective_sample_size:,.0f}.** The picked contact sits "
            f"far out in the tail of the geological prior, so the posterior rests on very few "
            f"realisations. That is a finding about the model or the pick, not a number to read off."
        )

    # --------------------------------------------------------------- the anchor
    # E-POS anchors its DFI update to the *geological* POS -- the product of the element chances,
    # or the ESL mass-rollup -- and never to a geometric exceedance probability
    # (`logic/dfi_bayes.py::compute_dfi_posterior`, `prior_pg_override`). This tool anchored to
    # F(h_min) alone, which is P(column reaches the threshold | the prospect works). At a zero
    # assessment minimum that is 1.0, and no evidence can move certainty -- which is why a
    # "Negligible" DHI appeared to leave POS at 100 %.
    #
    # The prospect POS is the product of the two, and both halves already exist: the element
    # chances come from tab 2 and the exceedance from the engine. R itself is unaffected -- a
    # likelihood ratio is invariant to re-anchoring, which E-POS says in as many words.
    element_pos = st.session_state.get("element_pos") or {}
    element_product = float(np.prod([float(v) for v in element_pos.values()])) if element_pos else 1.0
    geometric_prior = post.pos(posterior=False)
    prior_pos = element_product * geometric_prior
    posterior_geometric = post.pos()

    if not element_pos:
        st.warning(
            "**No element risk set**, so the update is anchored to the geometric chance alone. "
            "Set play × conditional on tab ② — anchoring a DHI to a probability of 1.0 makes any "
            "evidence look like it changed nothing."
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Prospect POS at h ≥ {h_min:.0f} m", f"{element_product * posterior_geometric:.1%}",
              f"prior {prior_pos:.1%}")
    # R compares the likelihood over successes against the likelihood over failures, so it needs
    # both sets to exist. With the assessment minimum at zero every realisation is a success and R
    # is genuinely undefined -- which is worth saying rather than printing "nan".
    r = post.r_dhi
    m2.metric("Likelihood ratio R", _fmt_r(r),
              "needs an assessment minimum" if np.isnan(r) else "above 1 favours success",
              delta_color="off")
    m3.metric("Posterior P50 contact", f"{post.percentiles(50.0)[0]:,.0f} m",
              f"prior {post.percentiles(50.0, posterior=False)[0]:,.0f} m")
    m4.metric("Effective sample size", f"{post.effective_sample_size:,.0f}",
              f"of {result.n:,}", delta_color="off")

    st.caption(
        f"**The anchor is the geological POS, not the exceedance curve.** Prospect POS is "
        f"`∏ element chances × P(column ≥ h)` = **{element_product:.3f} × "
        f"{geometric_prior:.3f} = {prior_pos:.3f}** before the DHI. Anchoring to the exceedance "
        f"alone is what E-POS's `prior_pg_override` exists to prevent: at a zero assessment "
        f"minimum that term is 1.0, and no evidence can move certainty.\n\n"
        f"**R is unaffected by the anchor.** A likelihood ratio compares how surprising the "
        f"observation is under success against under failure; re-anchoring moves only where that "
        f"ratio is applied, which is E-POS's point too."
    )

    hs = np.linspace(0.0, float(result.column_m.max()), 300)
    fig = go.Figure()
    fig.add_scatter(x=hs, y=post.exceedance(hs, posterior=False), mode="lines",
                    name="prior — geological", line=dict(color=PRIOR, width=3))
    fig.add_scatter(x=hs, y=post.exceedance(hs), mode="lines", name="posterior — with the DHI",
                    line=dict(color=POSTERIOR, width=3))
    markers = [("assessment minimum", h_min, "#333")]
    if seen:
        markers.append(("DHI contact", contact - apex, POSTERIOR))
    spill = [i for i, nm in enumerate(limit_set.names) if "spill" in nm.lower()]
    if spill:
        markers.append(("median spill", float(np.median(result.sampled_m[:, spill[0]])), "#8172B2"))
    for label, h, colour in markers:
        if 0 <= h <= hs[-1]:
            fig.add_vline(x=h, line=dict(color=colour, dash="dash"),
                          annotation_text=label, annotation_position="top")
    fig.update_layout(xaxis_title="Threshold column height h (m below apex)",
                      yaxis_title="P(column ≥ h)", yaxis_range=[0, 1], height=520,
                      margin=dict(t=40), legend=dict(orientation="h", y=-0.18))
    n.plot(fig, "**The figure this tab exists for.** Every chance anyone quotes is a point on one of "
                "these curves. A strong DHI raises POS at the assessment minimum *and* raises the "
                "chance of the large case — both, from one update, because the updated POS and the "
                "updated contact distribution are the same object. Quoting a POS read at one marker "
                "beside a volume read at another is the error this makes visible.")

    n.table(
        pd.DataFrame([
            {"Threshold": label,
             "Column (m)": f"{h:,.0f}",
             "Contact (m TVDSS)": f"{apex + h:,.0f}",
             "Prior POS": f"{post.exceedance(h, posterior=False)[0]:.1%}",
             "Posterior POS": f"{post.exceedance(h)[0]:.1%}"}
            for label, h, _ in markers if 0 <= h <= hs[-1]
        ]),
        "**POS and its threshold, always as a pair.** These are readings of the curve above, not "
        "separate numbers — which is why a volume must be taken at the same row as the chance "
        "beside it.")

    theme.heading(TAB, "5 · Combining the two channels")
    st.markdown(
        """
Geometry and character are **two aspects of one observation, not two observations.** A bright
anomaly is more likely to have a mappable termination, so the two are positively dependent, and
multiplying their likelihood ratios assumes they are not. That over-states the evidence — the same
double-count this whole architecture is arranged to avoid, arriving one level in.

So the combination is discounted rather than taken raw.
"""
    )
    dependence = st.slider(
        "Dependence between the two channels", 0.0, 1.0, 0.5, 0.05,
        help="0 multiplies the two ratios outright, which assumes they are independent evidence. "
             "1 takes the stronger channel and ignores the other, which assumes they say the same "
             "thing. 0.5 is the default because neither end is defensible.")

    combined = dhi_core.CombinedUpdate(
        prior_pos=prior_pos,
        r_geometry=float(post.r_dhi),
        r_strength=r_strength,
        dependence=dependence)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("R, geometry", _fmt_r(post.r_dhi),
              "from §4" if not np.isnan(post.r_dhi) else "needs an assessment minimum",
              delta_color="off")
    c2.metric("R, strength", _fmt_r(r_strength), "from §2", delta_color="off")
    # Moved here from §2 by the reorder: it needs the prior, and a chance is a result rather than
    # an input. It is the number to read the strength band against — see the caption in §2.
    c2.metric("POS on strength alone", f"{dhi_core.simm_update(prior_pos, r_strength):.1%}",
              f"prior {prior_pos:.1%}", delta_color="off")
    c3.metric("R, combined", _fmt_r(combined.r_combined),
              dhi_core.strength_bands(combined.r_combined)[0], delta_color="off")
    c4.metric("Prospect POS", f"{combined.posterior_pos:.1%}",
              f"prior {combined.prior_pos:.1%}")

    # Published for tab ④, which draws the posterior beside the per-element decomposition. Tab ④
    # renders before this one, so it reads the value written on the previous run -- a one-frame lag
    # that is invisible in practice, because every interaction reruns both and the user has to
    # switch tabs to look. Storing the curve rather than the object keeps the dependency one-way.
    depth_grid = apex + np.linspace(0.0, float(result.column_m.max()), 300)
    st.session_state["dhi_overlay"] = {
        "depths_m": depth_grid,
        # **Scaled to the prospect chance, not left conditional.** `post.exceedance` is
        # P(column >= h | the prospect works AND the DHI), so it starts at 1.0 at the apex. The
        # *Risk against depth* sub-tab beside this one draws it against per-element curves that already carry the element chances, and an
        # unscaled curve therefore sat at 100 % where the geological curves sat at 41 % -- two
        # different quantities on one axis, which is the error this whole tool is arranged to
        # prevent, committed by the tool itself.
        #
        # The anchor is the assessment minimum, because that is where the Bayesian update was
        # applied: at h_min the curve must read the posterior prospect POS exactly, and the shape
        # above and below comes from the updated contact distribution.
        "pos_curve": (combined.posterior_pos
                      * post.exceedance(depth_grid - apex)
                      / max(float(post.exceedance(np.array([h_min]))[0]), 1e-12)),
        "prior_curve": (combined.prior_pos
                        * post.exceedance(depth_grid - apex, posterior=False)
                        / max(float(post.exceedance(np.array([h_min]),
                                                    posterior=False)[0]), 1e-12)),
        # A resampled set of contacts, so downstream code that needs *samples* rather than a
        # curve -- the export, the benchmark comparison -- gets the posterior distribution itself
        # rather than reconstructing it from percentiles. Importance resampling with replacement,
        # which is exact in the limit and honest about the effective sample size above.
        "contact_samples": _resample(result.contact_m[result.above_minimum],
                                     post.weights[result.above_minimum]),
        # The raw per-realisation weights, so the sibling sub-tab can rebuild the decomposition as its
        # posterior twin rather than being handed one pre-computed curve.
        "weights": post.weights,
        # The picked contact, so the sibling figures can mark it and say what the curve
        # reads there -- the reading Lars made and had to ask about.
        "picked_contact_m": float(contact) if seen else None,
        "prior_pos": float(combined.prior_pos),
        "posterior_pos": float(combined.posterior_pos),
        "h_min": float(h_min),
    }

    if np.isnan(post.r_dhi):
        st.info(
            "**The geometry channel is undefined**, because the assessment minimum is zero and "
            "there is no failure set for R to compare against. The combination has fallen back to "
            "the strength channel alone. Set a minimum column height on tab ② to use both."
        )
    elif post.r_dhi > dhi_core.R_CAP:
        # Found by wiring this section up: the geometry channel is not clipped, and on a sharp pick
        # against a low assessment minimum it returns astronomical values. The clip in
        # CombinedUpdate then does all the work, and a reader who is not told that will read the
        # cap as a finding. Say it plainly instead.
        st.warning(
            f"**The geometry channel returned R = {post.r_dhi:,.0f}, and the guard is what you are "
            f"seeing in `R, combined`, not the evidence.** E-POS clips any single likelihood ratio "
            f"to {dhi_core.R_CAP:.0f}, and that clip is binding here.\n\n"
            "A ratio that size says the pick is near-impossible unless the prospect succeeds, which "
            "is an artefact of comparing a sharp pick against a failure set that the pick sits far "
            "away from — not a statement about the seismic. **Simm's caution applies: for a single "
            "line of fluid-indicator evidence an honest R rarely exceeds about 3 either way.** "
            "Widen the pick σ in §1, raise the assessment minimum on tab ②, or lower the detection "
            "ceiling in §3, and watch it fall. If it will not fall, the model — not the DHI — is "
            "asserting the answer."
        )

    span = np.linspace(0.0, 1.0, 41)
    figc = go.Figure()
    figc.add_scatter(
        x=span,
        y=[dhi_core.CombinedUpdate(combined.prior_pos, combined.r_geometry,
                                   combined.r_strength, float(d)).posterior_pos for d in span],
        mode="lines", name="posterior POS", line=dict(color=POSTERIOR, width=2.5))
    figc.add_hline(y=combined.prior_pos, line=dict(color=PRIOR, dash="dash"),
                   annotation_text="prior POS", annotation_position="bottom right")
    figc.add_scatter(x=[dependence], y=[combined.posterior_pos], mode="markers",
                     showlegend=False, marker=dict(color=theme.INK, size=10))
    figc.update_layout(xaxis_title="Assumed dependence between the channels",
                       yaxis_title="Prospect POS", yaxis_range=[0, 1], height=320,
                       margin=dict(t=20), showlegend=False)
    n.plot(figc, "**How much the answer rests on an assumption nobody can measure.** The left-hand "
                 "end treats the two channels as independent evidence and the right-hand end treats "
                 "them as one; the gap between the ends is the size of the double-count you would "
                 "commit by multiplying without thinking. If that gap is large, the honest report "
                 "is the range, not the midpoint.")

    # ------------------------------------------------------------------ cross-checks
    # ------------------------------------------------------------- success attribution
    st.divider()
    st.markdown(
        "### Diagnostics\n\n"
        "Everything above is the answer. Everything below is how much to trust it — what "
        "the answer rests on, which mechanism the amplitude promoted, whether the anomaly "
        "area agrees with the column, and what the older scenario-switch formulation would "
        "have said instead. Good to read, and not what a first pass needs."
    )

    theme.heading(TAB, "6 · What is this answer most sensitive to?")
    st.markdown(
        "**Two kinds of input, and the figure keeps them apart because they are argued about "
        "differently.** The geology varies realisation by realisation and is sliced the same way "
        "as on tab \u2463 \u2014 except the means are now *weighted*, because after the update a "
        "realisation is worth its likelihood. The DHI's own numbers do not vary at all: a picked "
        "contact and a pick \u03c3 are single typed values, so their influence is found by moving "
        "them and recomputing.\n\n"
        "**Moving them is cheap and that is the point of importance weighting.** Each variation is "
        "a new set of weights on the *same* realisations \u2014 no second Monte Carlo \u2014 so a "
        "one-at-a-time sensitivity over the DHI inputs costs nothing."
    )
    dhi_space = st.radio(
        "Swing measured on", ["Column below apex", "Contact depth"], horizontal=True,
        key="dhi_tornado_space")
    _space = "column" if dhi_space.startswith("Column") else "depth"
    _effects = sensitivity.dhi_tornado(post, space=_space)
    _centre = sensitivity.dhi_baseline(post, space=_space)

    if _effects:
        _shown = _effects[:12]
        figt = go.Figure()
        for _kind, _colour in ((sensitivity.DEPTH_EFFECT, PRIOR),
                               (sensitivity.DHI_INPUT, POSTERIOR)):
            _rows = [e for e in _shown if e.kind == _kind]
            if not _rows:
                continue
            figt.add_bar(y=[f"{e.name} \u2014 {e.kind}" for e in _rows][::-1],
                         x=[e.high - e.low for e in _rows][::-1],
                         base=[e.low - _centre for e in _rows][::-1],
                         orientation="h", name=_kind, marker_color=_colour,
                         hovertemplate="%{y}<br>%{x:,.0f} m of swing<extra></extra>")
        figt.add_vline(x=0.0, line=dict(color="#555", width=1.5))
        figt.update_layout(xaxis_title=f"Metres from the posterior mean of {_centre:,.0f} m",
                           height=max(300, 34 * len(_shown)), margin=dict(t=20),
                           barmode="overlay", legend=dict(orientation="h", y=-0.22))
        n.plot(figt,
               f"**What the DHI-updated mean actually rests on.** Blue bars are geological inputs, "
               f"sliced by decile and weighted by the likelihood; red bars are the DHI's own typed "
               f"numbers, each moved one at a time \u2014 the pick \u03c3 halved and doubled, the picked "
               f"contact by half a \u03c3, the detection parameters across the span an assessor "
               f"genuinely cannot pin down.\n\n"
               f"**Read the red bars against the blue ones.** If a typed DHI number moves the "
               f"answer further than the geology does, the posterior is a statement about your "
               f"seismic assumptions rather than about the prospect \u2014 and the pick \u03c3 and the "
               f"detection ceiling are usually the least defensible numbers on this tab. That is "
               f"worth saying out loud rather than quoting.\n\n"
               f"**The geological ranking can differ from tab \u2463's.** Reweighting changes which "
               f"limits the answer is sensitive to, which is a real consequence of the update and "
               f"not visible anywhere else.")
    else:
        st.info("Not enough weight spread to slice a sensitivity from this posterior.")

    theme.heading(TAB, "7 · Which mechanism set the contact, given the DHI")
    st.markdown(
        "**This is not the risk re-attributed — it is the *shallowest active limit* re-attributed, "
        "and the two are different questions.**\n\n"
        "*Given the prospect failed, which element failed?* A fluid indicator cannot say. The "
        "element chances on tab ② are untouched by anything here, and the *Risk against depth* "
        "sub-tab draws them "
        "unchanged.\n\n"
        "*Given it worked, and the contact is where the amplitude says, which mechanism stopped it "
        "there?* **That the DHI can answer**, because the contact depth is observed and the "
        "controlling limit is coupled to it. Ordinary inference on a latent variable, and the "
        "reason the argmin was worth keeping."
    )
    weights = post.weights
    total_w = float(weights.sum())
    rows = []
    for j, limit in enumerate(limit_set.limits):
        won = result.controller == j
        geo = float(won.mean())
        upd = float((won * weights).sum() / total_w) if total_w > 0 else geo
        if max(geo, upd) < 0.005:
            continue
        rows.append({"Limit": limit.name, "Element": limit.group.value,
                     "Geological": f"{geo:.1%}", "Given the DHI": f"{upd:.1%}",
                     "Shift": f"{upd - geo:+.1%}", "_sort": -upd})
    table = pd.DataFrame(sorted(rows, key=lambda r: r["_sort"])).drop(columns="_sort")
    n.table(table,
            f"{theme.basis_tag(theme.GIVEN_DHI)} &nbsp; Share of **successful** realisations in "
            f"which each mechanism was the shallowest active limit, before and after the update. "
            f"A mechanism that cannot produce a contact where the amplitude was picked loses share; "
            f"one that naturally produces exactly that contact gains it. **Read it as *what "
            f"stopped the column*, never as *where the risk is*.**")

    theme.heading(TAB, "8 · Cross-checks")
    if not (seen and area):
        st.caption("Enter an anomaly area in §1 to enable the area cross-check.")
    else:
        try:
            table = ch.AreaDepthTable.reference()
            cross = dhi_core.area_cross_check(table.depths_m, table.top_area_km2, area, contact)
            ok, msg = dhi_core.containment_ok(table.depths_m, table.top_area_km2,
                                              table.apex_m, h_min, area)
        except (FileNotFoundError, ValueError) as exc:
            st.info(f"Area cross-check unavailable: {exc}")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Contact from the anomaly's area", f"{cross['from_area_m']:,.0f} m")
            c2.metric("Disagreement", f"{cross['disagreement_m']:+,.0f} m",
                      "area minus termination", delta_color="off")
            if abs(cross["disagreement_m"]) < 25:
                st.success("The two readings agree. Treat them as one observation with a tighter σ.")
            elif cross["disagreement_m"] < 0:
                st.warning(
                    "**The anomaly is narrower than its down-dip limit implies.** It may not be "
                    "filling the closure — a stratigraphic or diagenetic component, or a smaller "
                    "effective trap than the one mapped.")
            else:
                st.warning(
                    "**The anomaly extends beyond the mapped conformance.** Suspect a non-fluid "
                    "cause: lithology, or tuning.")
            if not ok:
                st.error(f"**Containment fails.** {msg}")
        st.caption(
            "A DHI gives **two** readings of the contact — the down-dip termination and the areal "
            "extent through the area–depth table. They should agree, and nothing forces them to — "
            "which is why the check is here."
        )

    # ------------------------------------------------------------------ formulation A
    theme.heading(TAB, "9 · The scenario-switch formulation, for comparison")
    st.markdown(
        "`IF(DHI valid, DHI contact, geological contact)` — the older and simpler way to use a "
        "fluid indicator, and Hood's rule: merge late, never blend into the input distribution. "
        "It moves the contact but **not** the chance, which is the difference between the two "
        "formulations."
    )
    p_valid = st.slider("P(DHI is a valid contact indicator)", 0.0, 1.0, 0.655, 0.005,
                        help="A single typed number, as this formulation requires. Under the "
                             "likelihood formulation above it is revealed as a collapsed detection "
                             "function — a scalar standing in for D(h) evaluated somewhere "
                             "unspecified — which is why it never equals E-POS's "
                             "`dhi_volume_weight`.")
    if seen:
        switched = dhi_core.scenario_switch(result, p_valid, contact, sigma)
        s1, s2, s3 = st.columns(3)
        for col, p in ((s1, 90), (s2, 50), (s3, 10)):
            col.metric(f"Contact P{p}, scenario switch",
                       f"{np.percentile(switched, 100 - p):,.0f} m",
                       f"likelihood form {post.percentiles(p)[0]:,.0f} m", delta_color="off")
        st.caption(
            "**B-10 is downgraded, not fixed.** `E26 = 0.655` is not a bug — it is an unlabelled "
            "parameter of a model that was never written down. The likelihood formulation writes "
            "it down, and needs two numbers a geophysicist can state instead of one nobody can."
        )
    else:
        st.caption("The scenario switch has nothing to switch to when no anomaly was seen.")
