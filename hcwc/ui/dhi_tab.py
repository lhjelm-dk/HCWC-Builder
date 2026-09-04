"""Tab 5.0 — the DHI update.

The headline is one figure: **prospect POS against threshold**, geological and given the DHI, with
markers at every threshold anyone quotes a chance at. It exists to make one error impossible to commit — quoting a
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
from hcwc.core import sensitivity
from hcwc.core import well as well_core
from hcwc.core.dhi import DetectionFunction, DhiObservation
from hcwc.ui import run, sources, theme
from hcwc.ui.numbering import Numbering

TAB = 5
PRIOR = "#8CB7FC"
POSTERIOR = "#C44E52"

#: The three things an interpreter can actually have. The middle one was missing, and an
#: observation that has no home gets entered as whichever neighbour is closer -- as a pick it does
#: not support, which overstates it, or as *absent*, which throws away that something is there.
CONFORMING = "Seen"
PARTIAL = "Seen over the crest only"
ABSENT = "Absent where one was expected"
OBSERVATIONS = (CONFORMING, PARTIAL, ABSENT)

#: Where the strength slider opens. Lars, 4 Sep 2026.
#:
#: **Deliberately not** :data:`hcwc.core.dhi.DEFAULT_STRENGTH`, which is 7.0 and is a faithful copy
#: of E-POS's ``DEFAULT_SLIDER``. That constant exists so the two tools agree about what E-POS's
#: default *is*, and a test pins it; overwriting it to change where a slider opens would make this
#: app quietly disagree with E-POS about a number it claims to be copying.
#:
#: Five rather than seven is a slightly more conservative opening position on the same axis — still
#: above the crossing point, so an assessor who moves nothing states a barely-supportive DHI rather
#: than a neutral one, which is the property the E-POS default was chosen for.
OPENING_STRENGTH = 5.0


def well_control() -> well_core.WellControl | None:
    """The penetration described on tab 2.0, or ``None``.

    Read through a function so the tab does not have to know how the switches are stored, and so an
    incomplete or contradictory entry becomes ``None`` here rather than an exception in the middle
    of a render. Tab 2.0 reports the contradiction where it is typed; this side simply declines to
    use it.
    """
    if not st.session_state.get("well_on", False):
        return None
    hc = (float(st.session_state.get("well_in_hc", 0.0))
          if st.session_state.get("well_in_hc_on") else None)
    water = (float(st.session_state.get("well_in_water", 0.0))
             if st.session_state.get("well_in_water_on") else None)
    if hc is None and water is None:
        return None
    try:
        return well_core.WellControl(
            hc_down_to_m=hc, water_at_m=water,
            depth_sigma_m=float(st.session_state.get("well_in_sigma", 10.0)),
            p_connected=float(st.session_state.get("well_in_connected", 0.9)))
    except ValueError:
        return None


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


def _resample(values: np.ndarray, weights: np.ndarray, n: int) -> np.ndarray:
    """Draw from ``values`` in proportion to ``weights`` -- the posterior as a sample.

    The DHI update is an importance weighting, so the posterior lives as *weights on the prior's
    realisations*. Anything that wants a distribution rather than a curve needs those weights
    collapsed into a sample, and resampling with replacement is the standard way.

    ``n`` is the trial count the user set, not a constant. It defaulted to 20 000 and was never
    passed, so the posterior was drawn at 20 000 whatever *Realisations* said -- better resolved
    than its own prior at 1 000, and silently ignoring the precision asked for at 100 000. The
    export on tab 7.0 takes this sample when the basis is "given the DHI", so the setting has to
    reach it.

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
        st.info("Define the limits on tab 3.0 first.")
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
            "on tab 2.0 to add a seismic amplitude as evidence. The geological model on tabs 3.0 to 4.0 "
            "stands on its own either way.\n\n"
            "**What a DHI may and may not do.** E-POS sets the ceiling: a fluid indicator can sense "
            "whether a reservoir exists and what fluid fills it, but *not which of charge, closure "
            "or retention failed*. So it may move POS and it may assert a contact depth. It may "
            "**not** tell you *which element failed*, which is why the element chances on tab 2.0 "
            "are never touched here. It *may* tell you which limit set the contact, because "
            "knowing roughly where the contact sits is genuine evidence about which mechanism put "
            "it there — so tab 4.0's controlling-limit diagnostic stays purely geological and its "
            "twin on this tab is the same diagnostic re-read through the amplitude."
        )
        # Otherwise a curve computed before the toggle was turned off would go on being drawn on
        # tab 4.0, which is the worst kind of stale: plausible, labelled, and wrong.
        st.session_state.pop("dhi_overlay", None)
        _well_only(result, n)
        return

    theme.basis_banner(
        theme.GIVEN_DHI,
        "Every contact distribution below carries the amplitude evidence. The purely geological "
        "model is on tab 4.0 and is unchanged by anything here.")

    # ------------------------------------------------------------------ observation
    theme.heading(TAB, sub=n.sub, text="1 · What was observed")
    # Keyed -- as is every widget in this section. Without keys these values exist only inside
    # Streamlit's own widget store, under generated ids: they survive a rerun, and they cannot be
    # read out by name, so `prospect.document` could not see them and a saved prospect carried
    # `dhi_toggle` and nothing else. It reopened claiming a DHI and quietly using the default one.
    anomaly = st.radio(
        "Amplitude anomaly", OBSERVATIONS, horizontal=True, key="dhi_in_seen",
        help="**Absent** is evidence too, and this tool uses it: no anomaly where the column "
             "would have been thick enough to show one argues against a long column. It is only "
             "usable if you would genuinely have seen it — say so with the detection function in "
             "§3.\n\n**Seen over the crest only** is the middle case: something is convincingly "
             "there and convincingly stops, but with no down-dip termination clean enough to pick "
             "a contact on. It carries a bound, not a depth.")
    seen = anomaly != ABSENT
    partial = anomaly == PARTIAL
    # **2 250 m, because that is the prospect's pick** -- Lars, 3 Sep 2026, asked for it back after
    # a spell on the model's own median.
    #
    # The median was a reaction to a real fault and the fix for that fault is kept below. The
    # original code took 2 250 m whenever it fell anywhere inside the contact *range*, a test
    # against the extremes rather than against the bulk, and on the prospect as it then shipped
    # 2 250 m was the **P94** of the geological contact: every new reader was greeted by an amplitude
    # arguing hard against the geology, an effective sample size of 2 801 of 10 000, and a POS the
    # DHI had dragged most of the way up on its own. The defaults have moved since -- the base seal
    # sits a reservoir thickness down, the charge mean is 110 -- and 2 250 m is now the P86, 65 m
    # below the median. Still a pick on the deep side, which is a statement about this prospect
    # rather than an accident of the code, and it is the reader's to change.
    #
    # What stays is the guard, tightened: the fallback fires when the pick sits outside the central
    # 98 % of the prior rather than outside its full range, so a prospect whose contact cannot
    # plausibly reach 2 250 m opens on its own median instead of on an update built from a handful
    # of realisations.
    DEFAULT_SIGMA_M = 10.0
    PROSPECT_PICK_M = 2_250.0
    lo_prior, hi_prior = np.percentile(result.contact_m, [1.0, 99.0])
    default_contact = (PROSPECT_PICK_M if lo_prior <= PROSPECT_PICK_M <= hi_prior
                       else float(np.percentile(result.contact_m, 50)))
    shape = st.radio(
        "How is the pick shaped?", dhi_core.PICK_SHAPES, horizontal=True,
        disabled=not seen or partial,
        key="dhi_in_shape",
        format_func=lambda k: {dhi_core.NORMAL: "Normal — an unbiased estimate",
                               dhi_core.PERT: "Three-point — shallowest / likeliest / deepest",
                               dhi_core.UNIFORM: "Bracket — no preferred depth inside"}[k],
        help="Two of these are bounded, and a bound is a strong claim. It is safe here only "
             "because §2 keeps a floor under everything — see the note there.")

    shallowest = deepest = None
    absent_below = None
    if partial:
        # No pick, by definition: the bound is the whole observation. `contact` is still assigned
        # because the area cross-check in §8 reads it, and for this case the cutoff is the only
        # depth the anomaly gives.
        o1, o2, o3 = st.columns(3)
        absent_below = o1.number_input(
            "Reliably absent below (m TVDSS)", 0.0, 10000.0, default_contact, 5.0,
            key="dhi_in_absent_below",
            help="The depth below which you are confident there is no anomaly — not where you "
                 "think the contact is. It is a bound: everything above it is equally consistent "
                 "with what you saw, and the likelihood falls away below it at a rate the "
                 "detection function in §3 sets.")
        o2.metric("Bound, as a column", f"{max(absent_below - apex, 0.0):,.0f} m")
        sigma, contact = DEFAULT_SIGMA_M, absent_below
    elif shape == dhi_core.NORMAL:
        o1, o2, o3 = st.columns(3)
        contact = o1.number_input(
            "Picked contact (m TVDSS)", 0.0, 10000.0, default_contact, 5.0, disabled=not seen,
            key="dhi_in_contact", help="The down-dip amplitude termination or flat spot.")
        sigma = o2.number_input(
            "Pick σ (m)", 1.0, 500.0, DEFAULT_SIGMA_M, 1.0, key="dhi_in_sigma",
            help="Flat-spot pick uncertainty **plus depth-conversion error**. The second is "
                 "usually the larger, and it is the same uncertainty that moves the well's entry "
                 "depth — the one place this tool and WellVolPOS genuinely couple.")
    else:
        sigma = 20.0
        o1, o2, o3, o4 = st.columns(4)
        shallowest = o1.number_input(
            "Shallowest possible (m TVDSS)", 0.0, 10000.0, default_contact - 20.0, 5.0,
            disabled=not seen, key="dhi_in_shallowest",
            help="Above this the contact cannot be — if the pick is right.")
        if shape == dhi_core.PERT:
            contact = o2.number_input(
                "Most likely (m TVDSS)", 0.0, 10000.0, default_contact, 5.0, disabled=not seen,
                key="dhi_in_mode",
                help="The mode. Put it **above centre** to say the termination under-calls the "
                     "contact, which tuning and resolution loss at the base of a column both "
                     "argue for. That is the control that moves the reading at the pick.")
            deepest = o3.number_input(
                "Deepest possible (m TVDSS)", 0.0, 10000.0, default_contact + 20.0, 5.0,
                disabled=not seen, key="dhi_in_deepest",
                help="Below this the contact cannot be, if the pick is right. This is the bound "
                     "that does the work: it is what stops the column short.")
        else:
            # The same key as the PERT branch above. Only one of the two is ever built in a
            # given run, and sharing the key carries the depth across a change of pick shape.
            deepest = o2.number_input(
                "Deepest possible (m TVDSS)", 0.0, 10000.0, default_contact + 20.0, 5.0,
                disabled=not seen, key="dhi_in_deepest",
                help="Below this the contact cannot be, if the pick is right. Inside the bracket "
                     "no depth is preferred over another.")
            contact = 0.5 * (shallowest + deepest)
            o3.metric("Bracket centre", f"{contact:,.0f} m")
    area = (o3 if partial else o4 if shape != dhi_core.NORMAL else o3).number_input(
        "Anomaly area (km²), optional", 0.0, 1000.0, 0.0, 0.5, key="dhi_in_area",
        help="Used for the cross-check in §8. Leave at zero to skip.")

    if partial and absent_below <= apex:
        st.error(
            f"**The anomaly cannot be absent below {absent_below:,.0f} m and seen over the crest** "
            f"— the apex is at {apex:,.0f} m, so that depth is at or above the top of the closure. "
            f"There would be no trap above it for the anomaly to have been seen in."
        )
        return
    if seen and not partial and shape != dhi_core.NORMAL and not shallowest < deepest:
        st.error("**The deepest possible contact must lie below the shallowest.**")
        return
    if seen and not partial and shape == dhi_core.PERT and not shallowest <= contact <= deepest:
        st.error("**The most likely contact must lie between the two bounds.**")
        return

    # ------------------------------------------------------------------ the pick, against the prior
    # An over-confident pick is almost impossible to recognise from its own parameters -- 20 m
    # sounds modest until you see it against a prior three hundred metres wide -- and it is the
    # input that most quietly decides the answer. So it is drawn where it is typed, on the same
    # axis as the distribution it is about to reweight.
    if partial:
        # The bound drawn where it is typed, for the same reason the pick is: what an interpreter
        # can check by eye is whether the cutoff sits anywhere near the distribution it is about to
        # act on. A cutoff below the whole prior says nothing and should look like it says nothing.
        figb = go.Figure()
        figb.add_histogram(x=result.contact_m, nbinsx=70, histnorm="probability density",
                           marker_color=PRIOR, opacity=0.75,
                           name="geological HCWC — the competing limits, tab 4.0")
        figb.add_vline(x=absent_below, line=dict(color=POSTERIOR, width=3),
                       annotation_text=f"absent below {absent_below:,.0f} m",
                       annotation_position="top right")
        figb.add_vrect(x0=absent_below, x1=float(result.contact_m.max()) + 10.0,
                       fillcolor="rgba(196,78,82,0.10)", line_width=0)
        figb.update_layout(xaxis_title="Contact depth (m TVDSS)", yaxis_title="Density",
                           height=300, margin=dict(t=30), legend=dict(orientation="h", y=-0.28))
        below = float((result.contact_m > absent_below).mean())
        n.plot(figb,
               "**Blue is the hydrocarbon–water contact your geology produced** — the "
               "competing-limits model from tab 3.0. The red line is the only depth this "
               "observation gives, and it is a **bound rather than a pick**: everything shallower "
               "than it is equally consistent with what you saw, and the shaded side is what the "
               "evidence argues against.\n\n"
               f"**{below:.0%} of the geological realisations fall in the shaded side**, and those "
               "are the ones the update acts on. If that share is near zero the observation is "
               "telling you nothing you did not already believe — which is a real answer, not a "
               "failure. The likelihood does not stop dead at the line: it falls away below it at "
               "the rate §3's detection function sets, because a slice of column just under the "
               "cutoff could plausibly have been missed and a hundred metres of it could not.")

        # The one way this observation misleads, and it does it quietly. Once the cutoff is above
        # essentially the whole prior, every realisation is penalised by the same saturated amount
        # -- `1 - D` has bottomed out at `1 - ceiling` for all of them -- so the likelihood is flat,
        # the posterior equals the prior, and the page reports that the DHI changed nothing. It did
        # not change nothing: it contradicted the model outright. A flat penalty and no evidence
        # produce the same picture, and only this check tells them apart.
        if below >= 0.95:
            st.warning(
                f"**Your seismic and your geology disagree outright, and the update cannot show "
                f"it.** The anomaly is said to stop above {absent_below:,.0f} m, and "
                f"{below:.0%} of the geological realisations put the contact deeper than that — "
                f"so every one of them is inconsistent with the observation by roughly the same "
                f"saturated amount.\n\n"
                f"A likelihood that is uniformly small carries no *relative* information, so the "
                f"posterior below will come out close to the prior and the DHI will appear to have "
                f"changed nothing. **Read that as the disagreement it is, not as a null result.** "
                f"Either the cutoff is picked shallower than the amplitude really supports, or the "
                f"limits on tab 3.0 are letting the column go deeper than this prospect can."
            )

    if seen and not partial:
        preview = DhiObservation(seen=True, contact_m=contact, pick_sigma_m=sigma,
                                 pick_shape=shape, shallowest_m=shallowest, deepest_m=deepest)
        lo = min(float(result.contact_m.min()), float(preview.pick_ppf(np.array([0.001]))[0]))
        hi = max(float(result.contact_m.max()), float(preview.pick_ppf(np.array([0.999]))[0]))
        axis = np.linspace(lo - 10.0, hi + 10.0, 500)
        figv = go.Figure()
        # Named for what it is, not for the role it plays in the arithmetic. "Prior" is the
        # Bayesian word for a distribution you already had, and using it as a *label* asks the
        # reader to translate before they can read the figure.
        figv.add_histogram(x=result.contact_m, nbinsx=70, histnorm="probability density",
                           marker_color=PRIOR, opacity=0.75,
                           name="geological HCWC — the competing limits, tab 4.0")
        figv.add_scatter(x=axis, y=preview.pick_pdf(axis), mode="lines", name="your pick",
                         line=dict(color=POSTERIOR, width=3), fill="tozeroy",
                         fillcolor="rgba(196,78,82,0.15)")
        figv.add_vline(x=contact, line=dict(color=POSTERIOR, dash="dot"),
                       annotation_text=f"{contact:,.0f} m", annotation_position="top right")
        figv.update_layout(xaxis_title="Contact depth (m TVDSS)", yaxis_title="Density",
                           height=300, margin=dict(t=30), legend=dict(orientation="h", y=-0.28))

        prior_span = float(np.percentile(result.contact_m, 90) - np.percentile(result.contact_m, 10))
        pick_span = float(preview.pick_ppf(np.array([0.9]))[0] - preview.pick_ppf(np.array([0.1]))[0])
        sharper = prior_span / max(pick_span, 1e-9)
        sits_at = float((result.contact_m <= contact).mean())
        n.plot(figv,
               "**Blue is the hydrocarbon–water contact your geology produced** — the "
               "competing-limits model from tab 3.0, which is what tab 4.0 draws. Red is what the "
               "amplitude says. Everything downstream is these two meeting. *(Where this tab says "
               "**prior**, it means the blue one.)*\n\n"
               f"**Your pick is {sharper:,.0f}× sharper than the geology**, centred where "
               f"{sits_at:.0%} of it lies shallower. Sharpness is a claim about the depth "
               "conversion, not about the seismic — the uncertainty that belongs here is the "
               "flat-spot pick *plus* the time-to-depth error, and the second is usually the "
               "larger. Far narrower than the geology and the pick dominates the answer; centred "
               "out in its tail and the posterior rests on very few realisations, which §4 "
               "reports as the effective sample size.")

    # ------------------------------------------------------------------ strength channel
    theme.heading(TAB, sub=n.sub, text="2 · DHI strength — the amplitude channel")
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
        "DHI strength", -100.0, 100.0, OPENING_STRENGTH, 1.0, key="dhi_in_strength",
        help=f"Opens at {OPENING_STRENGTH:.0f} — just above the crossing point, so an assessor who "
             f"moves nothing states a barely-supportive DHI rather than a neutral one. E-POS's own "
             f"default on the same axis is {dhi_core.DEFAULT_STRENGTH:.0f}; this is a shade more "
             f"conservative and the two are otherwise the same scale.")

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
            "and *the geological model on tab 4.0 stands untouched*. That branch is what keeps the "
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
        if st.checkbox("Set p_valid myself", value=False, key="dhi_in_pvalid_manual",
                       help="Overrides the value derived from DHI strength above. Use it when the "
                            "anomaly's *geometry* argues differently from its amplitude — a "
                            "conformable flat spot, or a bright blob that follows no structure."):
            p_valid = st.slider("p_valid", 0.05, 0.99, float(round(derived_p_valid, 2)), 0.01,
                                key="dhi_in_pvalid",
                                help="1.0 is deliberately unreachable: it would say the pick is "
                                     "certainly the contact, and certainty cannot be argued with.")
        else:
            p_valid = derived_p_valid

    # ------------------------------------------------------------------ combining
    theme.heading(TAB, sub=n.sub, text="3 · Detection function D(h)")
    st.markdown(
        "The chance a column of height *h* produces a **detectable** anomaly. Near zero below "
        "tuning thickness, rising through the resolution limit, then flat. It is what makes an "
        "absent anomaly usable evidence rather than a special case — the likelihood is simply "
        "`1 − D(h)`, which is largest at small *h*."
    )
    d1, d2, d3 = st.columns(3)
    h50 = d1.number_input("50 % detection column (m)", 1.0, 500.0, 25.0, 1.0,
                          help="Roughly the tuning thickness for this reservoir and frequency.")
    steep = d2.number_input(
        "Transition width (m)", 1.0, 200.0, 8.0, 1.0,
        help="How sharply detection turns on. Small means a clean threshold at the column above; "
             "large means a gradual rise, which is the safer assumption when the reservoir "
             "properties vary across the closure.")
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
    theme.heading(TAB, sub=n.sub, text="4 · Prospect POS against threshold")
    observation = DhiObservation(
        seen=seen, contact_m=None if partial or not seen else contact,
        pick_sigma_m=sigma, area_km2=area or None,
        pick_shape=shape, shallowest_m=None if partial else shallowest,
        deepest_m=None if partial else deepest,
        p_valid=p_valid, absent_below_m=absent_below)
    try:
        post = dhi_core.update(result, detection, observation)
    except ValueError as exc:
        st.error(str(exc))
        return

    # ---- the second evidence channel ---------------------------------------------------------
    # A penetration, if there is one, described on tab 2.0. It multiplies in here rather than being
    # folded into `DhiObservation`, because it is not a DHI: no strength, no detection function,
    # and it needs no argument to be admissible. The two are close to independent evidence -- a
    # reflection coefficient and a resistivity log -- which is what makes them worth having
    # together and what licenses the multiplication.
    control = well_control()
    if control is not None:
        try:
            post = dhi_core.DhiPosterior(
                result=result,
                weights=well_core.combine(post.weights, well_core.likelihood(result, control)),
                detection=detection, observation=observation)
        except ValueError as exc:
            st.error(str(exc))
            return
        theme.heading(TAB, sub=n.sub, text="3b · Well control")
        lo, hi = control.bracket()
        bits = []
        if control.hc_down_to_m is not None:
            bits.append(f"hydrocarbons proven to **{control.hc_down_to_m:,.0f} m**")
        if control.water_at_m is not None:
            bits.append(f"water at **{control.water_at_m:,.0f} m**")
        inside = float(((result.contact_m > lo) & (result.contact_m < hi)).mean())
        st.markdown(
            f"The penetration described on tab 2.0 is folded in above: {' and '.join(bits)}, tied to "
            f"the mapped surface with σ = **{control.depth_sigma_m:,.0f} m**, and a "
            f"**{control.p_connected:.0%}** chance it samples this accumulation.\n\n"
            f"**{inside:.0%} of the geological realisations already sit inside what the well "
            f"allows.** The update is the rest being pushed down toward the floor of "
            f"`1 − {control.p_connected:.2f} = {1 - control.p_connected:.2f}`, which is what stops "
            f"one penetration ruling a contact out altogether."
        )
        if inside < 0.05:
            st.warning(
                "**The well and the geological model disagree almost completely.** Nearly every "
                "realisation falls outside what the penetration allows, so all of them are "
                "penalised by roughly the same saturated amount, the likelihood goes flat, and the "
                "posterior below will come out close to the prior. **Read that as the "
                "disagreement it is, not as the well having said nothing** — either the depths are "
                "tied to a different datum than the apex, or the limits on tab 3.0 are letting the "
                "column go somewhere this well has already ruled out."
            )

    # Published for the trust panel on tab 4.0, which reports the effective sample size behind this
    # update. Same one-frame lag as `dhi_overlay` below and for the same reason: tab 4.0 renders
    # first, so it reads the posterior built on the previous run. Every interaction reruns both.
    st.session_state["dhi_posterior"] = post

    if np.isnan(post.r_dhi):
        st.info(
            "**R is undefined here.** It compares the likelihood over the success cases against "
            "the likelihood over the failures, and with the assessment minimum at "
            f"{h_min:.0f} m every realisation counts as a success — so there is no failure set to "
            "compare against. Set a minimum column height on tab 2.0 to get a likelihood ratio "
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

    # The two channels are combined here rather than in §5 because the figure below cannot be
    # drawn without the result: its posterior curve has to read the quoted POS at the assessment
    # minimum, and that number carries the strength channel. §5 keeps the argument for why the
    # combination is discounted, and the sweep showing what the discount costs.
    dependence = st.slider(
        "Dependence between the two channels", 0.0, 1.0, 0.5, 0.05, key="dhi_in_dependence",
        help="0 multiplies the two ratios outright, which assumes they are independent evidence. "
             "1 takes the stronger channel and ignores the other, which assumes they say the same "
             "thing. 0.5 is the default because neither end is defensible. §5 explains why.")

    # **Nothing was seen, so there is no amplitude to characterise.** The strength slider grades
    # the character of an observed anomaly; with no anomaly it has no subject, and leaving it
    # applied made an absent DHI as encouraging as a bright one -- the same POS, from evidence
    # pointing the opposite way. Neutral is the only defensible value.
    combined = dhi_core.CombinedUpdate(
        prior_pos=prior_pos,
        r_geometry=float(post.r_dhi),
        r_strength=r_strength if seen else 1.0,
        dependence=dependence)


    if not element_pos:
        st.warning(
            "**No element risk set**, so the update is anchored to the geometric chance alone. "
            "Set play × conditional on tab 2.0 — anchoring a DHI to a probability of 1.0 makes any "
            "evidence look like it changed nothing."
        )

    m1, m2, m3, m4 = st.columns(4)
    # `element_product * posterior_geometric` is the geometry update on its own and was reading
    # 40.8 % under a "Prospect POS" label while the tab's answer was 49.1 %. The combined update
    # is the number this metric is claiming to show.
    m1.metric(f"Prospect POS at h ≥ {h_min:.0f} m", f"{combined.posterior_pos:.1%}",
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

    # **Multiplied through by the element product.** Drawn as the bare exceedance this figure read
    # 100 % at a 5 m assessment minimum while the prospect POS there was 40.8 %, under a heading
    # that called it POS. `P(column >= h)` is the *conditional* column term; a POS is that times
    # the chance the prospect works at all, and the difference is the whole terminology error this
    # tool exists to prevent.
    st.markdown(
        "**The chance is a curve, not a number.** Every point on it is `P(G) × P(column ≥ h)` at "
        "one threshold, so a chance only means something once you say *at least how much column*. "
        "Read along a dashed line to see what the DHI did; read between the lines to see what the "
        "**threshold** did — and that second gap is the one that causes trouble, because it is "
        "there before any DHI and has nothing to do with one."
    )
    t1, t2 = st.columns([1, 1])
    with t1:
        show_all = st.toggle(
            "Show what dropping a term would give", value=False, key="combo_all_5",
            help="Two comparisons, not two alternatives: the pooled curve is this update with the "
                 "detection function left out, and the scenario switch is a mixture, which can "
                 "widen the answer but never sharpen it and cannot move the chance at all.")
    with t2:
        # The curves are cumulative, and a cumulative curve hides where the mass actually is: two
        # very different contact distributions can trace nearly the same exceedance. Drawn behind
        # them on their own axis, the histograms say what the curves only imply — and put the
        # reshaping the DHI performs next to the chance it produces.
        overlays = st.multiselect(
            "Overlay the contact distribution", [theme.GEOLOGICAL, theme.GIVEN_DHI],
            default=[theme.GEOLOGICAL, theme.GIVEN_DHI], key="hcwc_hist_5",
            help="Where the contacts themselves fall, binned by depth. The curves above are the "
                 "cumulative form of exactly these.")

    hs = np.linspace(0.0, float(result.column_m.max()), 300)
    depths = apex + hs

    def _anchored(curve, at_min, pos):
        """A curve that reads its own quoted POS at the assessment minimum.

        Scaling by the element product alone draws the *geometry* update and silently drops the
        strength channel's effect on the chance, which is how this figure came to read 40.8 % at
        the minimum beside a headline of 49.1 %.
        """
        return pos * np.asarray(curve) / max(float(at_min), 1e-12)

    prior_at_min = float(post.exceedance(np.array([h_min]), posterior=False)[0])
    post_at_min = float(post.exceedance(np.array([h_min]))[0])
    geological = _anchored(post.exceedance(hs, posterior=False), prior_at_min, combined.prior_pos)
    updated = _anchored(post.exceedance(hs), post_at_min, combined.posterior_pos)

    # Depth on y, inverted. This figure used to be the one exception to the tool's own convention,
    # which every other caption states out loud -- and being the exception made it read as a
    # different object from the identical curve two sub-tabs away.
    fig = go.Figure()

    # Added before the curves so the curves draw over them, and on a second x-axis so the POS axis
    # keeps meaning exactly one thing. Both bases share that axis, which is the point: a histogram
    # scaled to its own peak would make every distribution look equally concentrated.
    hist_edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 61)
    hist_centres = 0.5 * (hist_edges[:-1] + hist_edges[1:])
    shares = {}
    for basis, w in ((theme.GEOLOGICAL, None), (theme.GIVEN_DHI, post.weights)):
        if basis not in overlays:
            continue
        counts, _ = np.histogram(result.contact_m, bins=hist_edges, weights=w)
        total = float(counts.sum())
        shares[basis] = counts / total if total > 0 else counts
    for basis, values in shares.items():
        fig.add_bar(y=hist_centres, x=values, orientation="h", xaxis="x2",
                    # The token picks the colour; the words say what is in the weights, which on
                    # a prospect that also has a penetration is both channels.
                    name=(f"contacts — " + (theme.evidence_basis() if basis == theme.GIVEN_DHI
                                              else basis)), opacity=0.45,
                    marker_color=theme.BASIS_COLOUR[basis], marker_line_width=0,
                    hovertemplate="%{y:.0f} m TVDSS<br>%{x:.1%} of realisations<extra></extra>")

    fig.add_scatter(x=geological, y=depths, mode="lines", name="geological — before the update",
                    line=dict(color=PRIOR, width=3))
    fig.add_scatter(x=updated, y=depths, mode="lines", name=theme.evidence_basis(),
                    line=dict(color=POSTERIOR, width=3.4))

    if show_all and seen:
        for method, dash in ((dhi_core.POOLED, "dash"), (dhi_core.SCENARIO, "dot")):
            curve = _anchored(
                dhi_core.combination_exceedance(result, detection, observation, hs, method=method),
                float(dhi_core.combination_exceedance(
                    result, detection, observation, np.array([h_min]), method=method)[0]),
                combined.posterior_pos)
            fig.add_scatter(x=curve, y=depths, mode="lines", opacity=0.65,
                            name={dhi_core.POOLED: "…with the detection function dropped",
                                  dhi_core.SCENARIO: "…as a scenario switch (a mixture)"}[method],
                            line=dict(color=POSTERIOR, width=2.0, dash=dash))

    markers = [("assessment minimum", h_min, "#333")]
    if seen:
        markers.append(("DHI contact", contact - apex, POSTERIOR))
    spill = [i for i, nm in enumerate(limit_set.names) if "spill" in nm.lower()]
    if spill:
        markers.append(("median spill", float(np.median(result.sampled_m[:, spill[0]])), "#8172B2"))

    rows = []
    for label, h, colour in markers:
        if not 0 <= h <= hs[-1]:
            continue
        geo = float(_anchored(post.exceedance(h, posterior=False), prior_at_min,
                              combined.prior_pos)[0])
        upd = float(_anchored(post.exceedance(h), post_at_min, combined.posterior_pos)[0])
        rows.append({"Threshold": label, "Column (m)": f"{h:,.0f}",
                     "Contact (m TVDSS)": f"{apex + h:,.0f}",
                     "POS, geological": f"{geo:.1%}", "POS, given the DHI": f"{upd:.1%}",
                     "Move": f"{upd - geo:+.1%}"})
        fig.add_hline(y=apex + h, line=dict(color=colour, dash="dash", width=1.4),
                      annotation_text=label, annotation_position="top left")
        # Both readings printed where they are taken, so neither has to be inferred from the other.
        for value, tint, side in ((upd, POSTERIOR, "right"), (geo, PRIOR, "left")):
            fig.add_scatter(x=[value], y=[apex + h], mode="markers+text",
                            marker=dict(color=tint, size=10, symbol="diamond",
                                        line=dict(color="white", width=1.5)),
                            text=[f"  {value:.1%}" if side == "right" else f"{value:.1%}  "],
                            textposition=f"middle {side}", textfont=dict(size=11, color=tint),
                            showlegend=False, hoverinfo="skip")

    # The posterior median contact. The pick is an estimate, not a floor, so the median lands on
    # it -- which is the whole reason the reading at the picked contact is about half the one at
    # the assessment minimum, and the question this figure is asked most often.
    median_contact = float(np.interp(0.5, updated[::-1] / max(updated.max(), 1e-12),
                                     depths[::-1]))
    fig.add_scatter(x=[combined.posterior_pos * 0.5], y=[median_contact], mode="markers",
                    marker=dict(color=POSTERIOR, size=13, symbol="circle-open",
                                line=dict(width=3)),
                    name=f"posterior median contact, {median_contact:,.0f} m", hoverinfo="skip")

    fig.update_layout(xaxis_title="Prospect POS  =  P(G) × P(column ≥ h)",
                      xaxis_range=[0, min(1.0, max(combined.prior_pos, combined.posterior_pos,
                                                   0.05) * 1.15)],
                      yaxis_title="Contact depth (m TVDSS)", yaxis=dict(autorange="reversed"),
                      height=560, margin=dict(t=40 if not shares else 60),
                      legend=dict(orientation="h", y=-0.18))
    if shares:
        # Scaled so the tallest bar fills a third of the width: enough to read the shape against,
        # not enough to compete with the curves the figure is actually about.
        peak = max(float(np.max(v)) for v in shares.values()) or 1.0
        fig.update_layout(
            barmode="overlay", bargap=0.04,
            xaxis2=dict(overlaying="x", side="top", range=[0, peak * 3.0], showgrid=False,
                        tickformat=".0%", title="share of realisations per depth bin",
                        title_font_size=11, tickfont_size=10))
    n.plot(fig, "**The figure this tab exists for.** Every chance anyone quotes is a point on one "
                "of these curves, and each is a **prospect POS** — the element product times the "
                "chance of clearing that threshold, not the conditional column term on its own.\n\n"
                "**A DHI is not a lift; it is a reshaping.** It raises the chance at thresholds "
                "near and above the picked contact and *lowers* it below, and the curves cross "
                "where that changes. The open circle is the posterior median: it lands on the "
                "pick, because an amplitude termination is an estimate of the contact and not a "
                "floor under it — which is why the reading there is about half the one at your "
                "assessment minimum.")

    n.table(
        pd.DataFrame(rows),
        "**POS and its threshold, always as a pair.** These are readings of the curve above, not "
        "separate numbers — which is why a volume must be taken at the same row as the chance "
        "beside it. The answer to *which chance do I quote* is: whichever row your volume was "
        "computed at.")

    theme.heading(TAB, sub=n.sub, text="5 · Combining the two channels")
    st.markdown(
        """
Geometry and character are **two aspects of one observation, not two observations.** A bright
anomaly is more likely to have a mappable termination, so the two are positively dependent, and
multiplying their likelihood ratios assumes they are not. That over-states the evidence — the same
double-count this whole architecture is arranged to avoid, arriving one level in.

So the combination is discounted rather than taken raw.
"""
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("R, geometry", _fmt_r(post.r_dhi),
              "from §4" if not np.isnan(post.r_dhi) else "needs an assessment minimum",
              delta_color="off")
    c2.metric("R, strength", _fmt_r(combined.r_strength),
              "from §2" if seen else "neutral — nothing was seen", delta_color="off")
    # Moved here from §2 by the reorder: it needs the prior, and a chance is a result rather than
    # an input. It is the number to read the strength band against — see the caption in §2.
    c2.metric("POS on strength alone",
              f"{dhi_core.simm_update(prior_pos, combined.r_strength):.1%}",
              f"prior {prior_pos:.1%}", delta_color="off")
    c3.metric("R, combined", _fmt_r(combined.r_combined),
              dhi_core.strength_bands(combined.r_combined)[0], delta_color="off")
    c4.metric("Prospect POS", f"{combined.posterior_pos:.1%}",
              f"prior {combined.prior_pos:.1%}")

    # Published for tab 4.0, which draws the posterior beside the per-element decomposition. Tab 4.0
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
                                     post.weights[result.above_minimum],
                                     int(st.session_state.get("n_trials", 10_000))),
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
            "the strength channel alone. Set a minimum column height on tab 2.0 to use both."
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
            "Widen the pick σ in §1, raise the assessment minimum on tab 2.0, or lower the detection "
            "ceiling in §3, and watch it fall. If it will not fall, the model — not the DHI — is "
            "asserting the answer."
        )

    # A flat sweep is not the same finding as a robust one, and the figure cannot tell them apart
    # on its own: when the geometry channel is undefined the combination falls back to strength
    # alone for every value of `dependence`, so the curve is a horizontal line that reads as
    # "nothing rests on this assumption" when it means "one of the two channels is switched off".
    if np.isnan(combined.r_geometry):
        st.warning(
            "**The curve below is flat, and that is not reassurance.** With the geometry channel "
            "undefined there is only one channel left, so there is nothing for `dependence` to "
            "trade off and every setting returns the same answer. Give the assessment minimum a "
            "value that some realisations fail and this figure starts saying something."
        )

    span = np.linspace(0.0, 1.0, 41)
    figc = go.Figure()
    figc.add_scatter(
        x=span,
        y=[dhi_core.CombinedUpdate(combined.prior_pos, combined.r_geometry,
                                   combined.r_strength, float(d)).posterior_pos for d in span],
        mode="lines", name=f"POS {theme.evidence_basis()}", line=dict(color=POSTERIOR, width=2.5))
    figc.add_hline(y=combined.prior_pos, line=dict(color=PRIOR, dash="dash"),
                   annotation_text="geological POS", annotation_position="bottom right")
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
    with st.expander(
            "**Diagnostics** — what the answer rests on, and what the older formulation would "
            "have said", expanded=False):
        st.caption(
            "Everything above is the answer. Everything here is how much to trust it: what it "
            "rests on, which mechanism the amplitude promoted, whether the anomaly area agrees "
            "with the column, and what the scenario switch would have given instead. Good to "
            "read, and not what a first pass needs."
        )

        theme.heading(TAB, sub=n.sub, text="6 · What is this answer most sensitive to?")
        st.markdown(
            "**Two kinds of input, and the figure keeps them apart because they are argued about "
            "differently.** The geology varies realisation by realisation and is sliced the same way "
            "as on tab 4.0 \u2014 except the means are now *weighted*, because after the update a "
            "realisation is worth its likelihood. The DHI's own numbers do not vary at all: a picked "
            "contact and a pick \u03c3 are single typed values, so their influence is found by moving "
            "them and recomputing.\n\n"
            "**Moving them is cheap and that is the point of importance weighting.** Each variation is "
            "a new set of weights on the *same* realisations \u2014 no second Monte Carlo \u2014 so a "
            "one-at-a-time sensitivity over the DHI inputs costs nothing."
        )
        dhi_space = st.radio(
            "Swing measured on", ["Column below apex", "Contact depth"], horizontal=True,
            help="Which quantity the bars measure. The ranking can differ between the two: a "
                 "limit that moves the column a long way may move the *depth* less, because the "
                 "apex moves in the same realisation.",
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
                   f"**The geological ranking can differ from tab 4.0's.** Reweighting changes which "
                   f"limits the answer is sensitive to, which is a real consequence of the update and "
                   f"not visible anywhere else.")
        else:
            st.info("Not enough weight spread to slice a sensitivity from this posterior.")

        theme.heading(TAB, sub=n.sub,
                      text=f"7 · Which mechanism set the contact, {theme.evidence_basis()}")
        st.markdown(
            "**This is not the risk re-attributed — it is the *shallowest active limit* re-attributed, "
            "and the two are different questions.**\n\n"
            "*Given the prospect failed, which element failed?* A fluid indicator cannot say. The "
            "element chances on tab 2.0 are untouched by anything here, and the *Risk against depth* "
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

        theme.heading(TAB, sub=n.sub, text="8 · Cross-checks")
        if not (seen and area):
            st.caption("Enter an anomaly area in §1 to enable the area cross-check.")
        else:
            try:
                table = sources.current_area_depth()
                if table is None:
                    raise FileNotFoundError
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
        theme.heading(TAB, sub=n.sub, text="9 · What the scenario switch would have said")
        st.markdown(
            "`IF(DHI valid, DHI contact, geological contact)` — the older and simpler way to use a "
            "fluid indicator, and Hood's rule: merge late, never blend into the input distribution. "
            "It moves the contact but **not** the chance.\n\n"
            "**This is a comparison, not an alternative model.** Its one real contribution was the "
            f"parameter — *is the picked event actually the contact* — and that now lives inside the "
            f"likelihood in §2, at **p_valid = {p_valid:.3f}**, where it does more than switch between "
            "two stories: it puts a floor under the whole update, so no contact depth is ever ruled "
            "out. There is no second slider here because there is no second number; running the "
            "comparison on a different one would be comparing against something else."
        )
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


def _well_only(result, n: Numbering) -> None:
    """The update for a prospect with an offset penetration and no amplitude.

    **The gate used to be the DHI toggle, and that stranded the evidence.** Well control is entered
    on tab 2.0 but was only ever *used* inside this tab, which renders nothing unless the prospect
    is marked as a DHI prospect. So a closure with a penetration and no bright spot -- an offset
    well through the same reservoir, a dry hole on the same structure -- could not reach the one
    channel in the tool that needed no argument to be admissible. Lars, 4 Sep 2026, asking what well
    control was *for*: this is what it is for, and it was unreachable.

    The DHI path below is untouched. When both channels exist they still combine there, discounted
    for dependence; this is the branch where there is nothing to combine with.
    """
    control = well_control()
    if control is None:
        return
    posterior = dhi_core.DhiPosterior(result=result,
                                      weights=well_core.likelihood(result, control))
    st.session_state["dhi_posterior"] = posterior

    # **The whole overlay contract, not a convenient subset.** Four other modules read this dict by
    # key -- the depth decomposition wants `depths_m` and both curves, the walkthrough wants the two
    # chances, the export wants `contact_samples`. A partial overlay does not degrade gracefully; it
    # raises `KeyError` in the middle of somebody else's figure. So this branch writes the same keys
    # the amplitude branch writes, with `picked_contact_m` as `None` because there is no pick.
    apex = float(np.median(result.apex_m))
    h_min = float(result.limit_set.min_column_m)
    depth_grid = apex + np.linspace(0.0, float(result.column_m.max()), 300)
    element_pos = st.session_state.get("element_pos") or {}
    product = float(np.prod([float(v) for v in element_pos.values()])) if element_pos else 1.0
    prior_pos = product * posterior.pos(posterior=False)
    posterior_pos = product * posterior.pos()
    st.session_state["dhi_overlay"] = {
        "depths_m": depth_grid,
        # Anchored at the assessment minimum exactly as the amplitude branch is, so the two curves
        # are the same quantity and the sibling sub-tab can draw either without knowing which.
        "pos_curve": (posterior_pos * posterior.exceedance(depth_grid - apex)
                      / max(float(posterior.exceedance(np.array([h_min]))[0]), 1e-12)),
        "prior_curve": (prior_pos * posterior.exceedance(depth_grid - apex, posterior=False)
                        / max(float(posterior.exceedance(np.array([h_min]),
                                                         posterior=False)[0]), 1e-12)),
        "contact_samples": _resample(result.contact_m[result.above_minimum],
                                     posterior.weights[result.above_minimum],
                                     int(st.session_state.get("n_trials", 10_000))),
        "weights": posterior.weights,
        "picked_contact_m": None,
        "prior_pos": prior_pos,
        "posterior_pos": posterior_pos,
        "h_min": h_min,
    }

    theme.basis_banner(
        theme.GIVEN_DHI,
        "There is no amplitude on this prospect, so the update below is the **penetration alone**. "
        "The purely geological model is on tab 4.0 and is unchanged by it.")
    theme.heading(TAB, sub=n.sub, text="1 · The penetration, as evidence")
    lo, hi = control.bracket()
    bits = []
    if control.hc_down_to_m is not None:
        bits.append(f"hydrocarbons proven to **{control.hc_down_to_m:,.0f} m**")
    if control.water_at_m is not None:
        bits.append(f"water at **{control.water_at_m:,.0f} m**")
    inside = float(((result.contact_m > lo) & (result.contact_m < hi)).mean())
    st.markdown(
        f"The well described on tab 2.0: {' and '.join(bits)}, tied to the mapped surface with "
        f"σ = **{control.depth_sigma_m:,.0f} m**, and a **{control.p_connected:.0%}** chance it "
        f"samples this accumulation.\n\n"
        f"**{inside:.0%} of the geological realisations already sit inside what the well allows.** "
        f"The update is the rest being pushed down toward the floor of "
        f"`1 − {control.p_connected:.2f} = {1 - control.p_connected:.2f}`, which is what stops one "
        f"penetration ruling a contact out altogether.\n\n"
        f"**Prospect POS {prior_pos:.1%} → {posterior_pos:.1%}**, on an effective sample size of "
        f"**{posterior.effective_sample_size:,.0f}** of {result.n:,}. Everything on sub-tabs 5.3 "
        f"and 5.4 is drawn on this."
    )
    if inside < 0.05:
        st.warning(
            "**The well and the geological model disagree almost completely.** Nearly every "
            "realisation falls outside what the penetration allows, so all of them are penalised "
            "by roughly the same saturated amount, the likelihood goes flat, and the posterior "
            "comes out close to the prior. **Read that as the disagreement it is** — either the "
            "depths are tied to a different datum than the apex, or the limits on tab 3.0 are "
            "letting the column go somewhere this well has already ruled out."
        )
    st.info(
        "**No `R` and no tornado on this page.** Both are statements about an *amplitude* — E-POS's "
        "`r_dfi` compares the seismic likelihood over tall columns against short ones — and there "
        "is no amplitude here. The evidence is a depth bracket, and what it does is visible "
        "directly in the contact distribution on tab 5.3."
    )

