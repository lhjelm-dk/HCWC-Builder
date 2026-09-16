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

#: Where `p_valid` opens: an even chance that the picked event is a fluid contact.
#: Deliberately a round number and not `R/(R+1)` at the opening strength, because it is a
#: judgement about the *event* and the two must be answered separately. See the p_valid
#: block in `render` for what went wrong when it was derived.
#: `P(the picked event is the contact | there is hydrocarbon)` — the conditional factor the
#: geophysicist supplies. `p_valid` is this times the amplitude-updated `P(G)`, so the two
#: judgements stay separate and the product cannot exceed the chance of any hydrocarbon.
#: 0.36 since 15 Sep 2026 (Lars), from 0.70: a cautious opening value, the geometric mean of an
#: ambiguous fit to structure, diffuse terminations and an absent fluid-contact reflection. The
#: floor under the pick is then 0.64, so an untouched slider lets the pick say at most 0.56 : 1
#: against any contact depth; a well-conformed event is claimed by moving it.
DEFAULT_CONTACT_GIVEN_HC = 0.36

#: The three **contact** attributes, after Monigle et al. (2025), who separate them from the
#: *body* attributes that grade the amplitude. These answer whether the picked event is the
#: base of the column; the strength slider answers whether there is a column. The numbers are
#: elicited judgements, not a calibration -- which is why the result is offered rather than
#: applied. The shipped selections (:data:`DEFAULT_ATTRIBUTE_LEVELS`) give c = 0.36, the
#: slider's own default, so applying the suggestion on an untouched tab moves nothing.
#: The option each attribute opens on: the levels whose geometric mean is the shipped c.
DEFAULT_ATTRIBUTE_LEVELS: dict[str, str] = {
    "Fit to structure": "Ambiguous",
    "Amplitude terminations": "Diffuse or long",
    "Fluid contact reflection": "Absent, where one was expected",
}

CONTACT_ATTRIBUTES: dict[str, dict[str, float]] = {
    "Fit to structure": {
        "Flat, conformable, cuts dipping structure": 0.95,
        "Broadly conformable": 0.75,
        "Ambiguous": 0.45,
        "Follows stratigraphy, not structure": 0.15,
    },
    "Amplitude terminations": {
        "Sharp, at the picked depth": 0.90,
        "Moderate": 0.65,
        "Diffuse or long": 0.35,
        "No clear termination": 0.15,
    },
    "Fluid contact reflection": {
        "Clear FCR": 0.95,
        "Weak or possible": 0.70,
        "Absent, and not expected here": 0.60,
        "Absent, where one was expected": 0.30,
    },
}


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


def _pooled_note(gap: float | None, floor_part: float | None) -> str:
    """What the *pooled* curve is actually missing, split into its two halves.

    `POOLED` is the pick likelihood with nothing under it, so it drops **both** the detection
    function and Cromwell\u2019s floor. Measured 8 Sep 2026 on the shipped prospect the floor is
    most of it -- 0.223 of a 0.236 gap -- and the curve was labelled after the other one. The
    split is recomputed here rather than quoted, because it moves with `p_valid`: at
    `p_valid = 1` there is no floor and the two curves coincide almost exactly.
    """
    if gap is None:
        return ""
    if gap < 0.005:
        return ("\n\nThe pooled curve lies under the solid one: dropping the floor and the "
                "detection function moves it by less than half a percent. With `p_valid` near 1 "
                "there is almost no floor to drop, and the pick is far sharper than `D(h)`, so "
                "across the columns the pick favours the detection function is near constant and "
                "cancels.")
    detail = ""
    if floor_part is not None:
        detail = (f" Of that, {floor_part:.1%} is the floor and "
                  f"{max(gap - floor_part, 0.0):.1%} the detection function.")
    return (f"\n\nThe pooled curve is the pick likelihood with nothing under it, so it omits "
            f"both the floor `L \u2265 1 \u2212 p_valid` and the detection function. Together "
            f"they move this curve by up to {gap:.1%}.{detail} The floor is usually the larger "
            f"part: without it a confident pick drives the realisations it disfavours to near "
            f"zero weight, which is what the dashed line shows.")


def _leverage_caption(lv: dhi_core.Leverage) -> str:
    """One line under a control saying what it is worth, in the units of the decision.

    The audit this came from found the tab explaining hardest where it mattered least: the
    detection function carried a warning triangle and moved the chance by 0.00 points, while
    the picked contact depth -- the second most powerful control here -- had a bare number
    box. A measured swing puts that right without writing more theory, and it teaches the
    structure better than theory would: a reader who does not think in likelihood ratios can
    still see which control is load-bearing, and which is switched off and why.

    Three readings, because "no effect" has three causes and only one is a property of the
    control:

    * a number, when the control moves something;
    * *inert*, when its whole range is worth less than a tenth of a point and a tenth of a
      metre -- true of the detection function on any prospect whose columns clear tuning,
      where ``D(h)`` sits at its ceiling for every realisation and a constant cancels out of
      a ratio;
    * *not measurable*, when the sweep met states the model refuses, which is a finding about
      the prospect rather than about the control.
    """
    if not lv.measurable:
        return ("Leverage not measurable from here: part of this range puts the model in a "
                "state it refuses, usually a pick the geology rules out entirely.")
    chance = (f"{abs(lv.pos_points):.1f} points of prospect chance"
              if abs(lv.pos_points) >= 0.05 else "nothing of the prospect chance")
    moves_depth = np.isfinite(lv.contact_m) and abs(lv.contact_m) >= 0.5
    depth = (f"{abs(lv.contact_m):.0f} m of contact depth" if moves_depth
             else "nothing of the contact depth")
    lo, hi = lv.span
    # Depths run to four figures and probabilities to two decimals, and `.3g` renders the
    # first as scientific notation. Pick the format from the magnitude rather than making
    # every caller pass one.
    if lo is None:
        swept = "its range"
    elif max(abs(lo), abs(hi)) >= 100.0:
        swept = f"{lo:,.0f} to {hi:,.0f}"
    else:
        swept = f"{lo:g} to {hi:g}"
    if lv.inert:
        return (f"No leverage on this prospect: over {swept} this control changes neither the "
                f"chance nor the contact. A property of this prospect, not of the control.")
    return (f"Leverage on this prospect: swept from {swept}, this control is worth "
            f"{chance} and {depth}.")


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
            "This prospect is not marked as a DHI prospect. The switch is on tab 2.0; with it on, "
            "a seismic amplitude enters as evidence here, and the geological model on tabs 3.0 "
            "to 4.0 stands on its own either way. Method: see 8.1.5."
        )
        # Otherwise a curve computed before the toggle was turned off would go on being drawn on
        # tab 4.0, which is the worst kind of stale: plausible, labelled, and wrong.
        st.session_state.pop("dhi_overlay", None)
        _well_only(result, n)
        return

    # Placeholders reserved beside each control and filled at the foot of the input
    # sections, once every value the sweep needs has been read.
    _lev: dict[str, object] = {}

    theme.basis_banner(
        theme.GIVEN_DHI,
        "Every contact distribution below carries the amplitude evidence. The purely geological "
        "model is on tab 4.0 and is unchanged by anything here.")

    # The geometry enters the chance as P(h ≥ h_min | G, geometry). At an assessment minimum
    # that every realisation clears, that factor is 1 before and after the update, so the pick
    # can reshape the contact distribution and cannot move the chance. Said here, above the
    # inputs it concerns, because a reader who moves the pick and sees the chance stand still
    # needs the reason beside the control. Until 14 Sep 2026 this was framed as a guard on a
    # likelihood ratio (`r_dhi` needing a failure set); under the corrected chain the ratio is
    # not part of the chance and the reason is the plain one.
    _short = int((~result.above_minimum).sum())
    if _short < dhi_core.min_failures_for_r(result.n):
        _need = float(np.quantile(result.column_m,
                                  dhi_core.min_failures_for_r(result.n) / max(result.n, 1)))
        st.warning(
            f"At an assessment minimum of {h_min:,.0f} m, {result.n - _short:,} of "
            f"{result.n:,} realisations clear it, so P(column ≥ h_min | G) is 1 before the "
            f"update and stays 1 after it. The pick, its width and c reshape the contact "
            f"distribution below; they cannot move the prospect chance, which at this minimum "
            f"responds to the amplitude character alone.\n\n"
            f"The pick reaches the chance once the minimum is a threshold a real share of "
            f"realisations miss. On this prospect about {_need:,.0f} m is the lowest such value."
        )

    # ------------------------------------------------------------------ observation
    theme.heading(TAB, sub=n.sub, text="1 · What was observed")
    # Keyed -- as is every widget in this section. Without keys these values exist only inside
    # Streamlit's own widget store, under generated ids: they survive a rerun, and they cannot be
    # read out by name, so `prospect.document` could not see them and a saved prospect carried
    # `dhi_toggle` and nothing else. It reopened claiming a DHI and quietly using the default one.
    anomaly = st.radio(
        "Amplitude anomaly", OBSERVATIONS, horizontal=True, key="dhi_in_seen",
        help="Absent is evidence too: no anomaly where the column would have been thick enough "
             "to show one argues for a short column. It is usable only where the anomaly would "
             "have been seen, which the detection function in §3b states.\n\n"
             "Seen over the crest only is the middle case: something is there and stops, with no "
             "down-dip termination clean enough to pick a contact on. It carries a bound, not a "
             "depth.")
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
        help="Two of these are bounded, and a bound is a strong claim. It is safe here because "
             "§3 keeps a floor under every depth.")

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
            help="The depth below which the anomaly is reliably absent, not where the contact "
                 "is thought to be. A bound: contacts well above it are equally consistent with "
                 "the observation, and the likelihood falls away below it at the rate the pick "
                 "error sets, as a censored pick.")
        o2.metric("Bound, as a column", f"{max(absent_below - apex, 0.0):,.0f} m")
        sigma, contact = DEFAULT_SIGMA_M, absent_below
    elif shape == dhi_core.NORMAL:
        o1, o2, o3 = st.columns(3)
        contact = o1.number_input(
            "Picked contact (m TVDSS)", 0.0, 10000.0, default_contact, 5.0, disabled=not seen,
            key="dhi_in_contact",
            help="The down-dip amplitude termination or flat spot. The tool takes it as the "
                 "hydrocarbon–water contact and does not ask whether it is a gas–oil contact. "
                 "On a two-phase prospect the amplitude is poor at resolving that, and a GOC "
                 "picked as an HCWC understates the column.")
        if seen:
            _lev["contact"] = o1.empty()
        sigma = o2.number_input(
            "Pick σ (m)", 1.0, 500.0, DEFAULT_SIGMA_M, 1.0, key="dhi_in_sigma",
            help="Flat-spot pick uncertainty plus depth-conversion error. The second is usually "
                 "the larger, and it is the same uncertainty that moves the well's entry depth.")
        if seen:
            _lev["sigma"] = o2.empty()
    else:
        sigma = 20.0
        o1, o2, o3, o4 = st.columns(4)
        shallowest = o1.number_input(
            "Shallowest possible (m TVDSS)", 0.0, 10000.0, default_contact - 20.0, 5.0,
            disabled=not seen, key="dhi_in_shallowest",
            help="Above this the contact cannot be, if the pick is right.")
        if shape == dhi_core.PERT:
            contact = o2.number_input(
                "Most likely (m TVDSS)", 0.0, 10000.0, default_contact, 5.0, disabled=not seen,
                key="dhi_in_mode",
                help="The mode. Above centre it says the termination under-calls the contact, "
                     "which tuning and resolution loss at the base of a column both argue for. "
                     "This is the control that moves the reading at the pick.")
            deepest = o3.number_input(
                "Deepest possible (m TVDSS)", 0.0, 10000.0, default_contact + 20.0, 5.0,
                disabled=not seen, key="dhi_in_deepest",
                help="Below this the contact cannot be, if the pick is right. This is the bound "
                     "that stops the column short.")
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
            f"The anomaly cannot be absent below {absent_below:,.0f} m and seen over the crest: "
            f"the apex is at {apex:,.0f} m, so that depth is at or above the top of the closure "
            f"and there is no trap above it for the anomaly to have been seen in."
        )
        return
    if seen and not partial and shape != dhi_core.NORMAL and not shallowest < deepest:
        st.error("The deepest possible contact must lie below the shallowest.")
        return
    if seen and not partial and shape == dhi_core.PERT and not shallowest <= contact <= deepest:
        st.error("The most likely contact must lie between the two bounds.")
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
               "Blue is the geological contact distribution, the competing limits from tab 3.0. "
               "The red line is the one depth this observation gives, and it is a bound rather "
               "than a pick: contacts well above it are equally consistent with the observation, "
               "and the shaded side is what the evidence argues against.\n\n"
               f"{below:.0%} of the geological realisations fall in the shaded side, and those "
               "are the ones the update acts on. A share near zero means the observation adds "
               "nothing the model did not already hold. The likelihood falls away below the "
               "line at the rate the pick error sets. Method: see 8.1.6.")

        # Once the cutoff is above essentially the whole prior, every realisation is penalised
        # by the same saturated amount, the likelihood is flat apart from the floor, the
        # posterior equals the prior, and the page reports that the DHI changed nothing. It
        # contradicted the model outright. A flat penalty and no evidence produce the same
        # picture, and only this check tells them apart.
        if below >= 0.95:
            st.warning(
                f"The seismic and the geology disagree outright, and the update cannot show it. "
                f"The anomaly is said to stop above {absent_below:,.0f} m, and {below:.0%} of "
                f"the geological realisations put the contact deeper than that, so every one of "
                f"them is inconsistent with the observation by roughly the same amount.\n\n"
                f"A likelihood that is uniformly small carries no relative information, so the "
                f"posterior below comes out close to the prior and the DHI appears to have "
                f"changed nothing. That is a disagreement, not a null result: either the cutoff "
                f"is shallower than the amplitude supports, or the limits on tab 3.0 let the "
                f"column go deeper than this prospect can."
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
        figv.add_scatter(x=axis, y=preview.pick_pdf(axis), mode="lines", name="the pick",
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
               "Blue is the geological contact distribution, the competing limits from tab 3.0 "
               "and what tab 4.0 draws. Red is the pick. Everything downstream is these two "
               "meeting; where this tab says prior, it means the blue one.\n\n"
               f"The pick is {sharper:,.0f} times sharper than the geology, centred where "
               f"{sits_at:.0%} of it lies shallower. Far narrower than the geology, the pick "
               "dominates the answer; centred in its tail, the posterior rests on few "
               "realisations, which §4 reports as the effective sample size. Method: see 8.1.6.")

    # ------------------------------------------------------------------ strength channel
    theme.heading(TAB, sub=n.sub, text="2 · Amplitude character")
    st.markdown(
        "The amplitude carries two kinds of evidence. §1 recorded where the anomaly terminates; "
        "this section grades its character: how bright, how consistent with the expected fluid "
        "response. The character updates the chance of hydrocarbons and does not enter the "
        "contact distribution; §5 multiplies the two."
    )
    st.caption(
        "R is the ratio of the heights of two elicited curves, hydrocarbon-bearing and not, at "
        "the prospect's reading on an axis without units (E-POS). Method: see 8.1.5."
    )

    with st.expander("The two populations (E-POS defaults)"):
        st.caption(
            "Each case is a Gaussian given by its 1st and 99th percentiles; cases further apart "
            "say the DHI separates the two populations better. Overlapping curves are the usual "
            "state.")
        h1, h2, h3, h4 = st.columns(4)
        hc = dhi_core.StrengthCase(
            h1.number_input("HC, P1", -200.0, 200.0, -50.0, 5.0),
            h2.number_input("HC, P99", -200.0, 200.0, 100.0, 5.0))
        no_hc = dhi_core.StrengthCase(
            h3.number_input("No HC, P1", -200.0, 200.0, -100.0, 5.0),
            h4.number_input("No HC, P99", -200.0, 200.0, 50.0, 5.0))
    model = dhi_core.StrengthModel(hc=hc, no_hc=no_hc)

    # The slider stops where the evidence stops. `strength_at` inverts the two curves for the
    # reading that buys the single-channel ceiling, and that becomes the end of the axis, so the
    # cap is visible as the shape of the control rather than as a range that does nothing.
    # Curves that never reach the ceiling (identical populations, or a narrow case nested inside a
    # broad one, which inverts the two ends) fall back to the old canvas.
    _ends = sorted(v for v in (model.strength_at(dhi_core.R_SINGLE_CHANNEL),
                               model.strength_at(1.0 / dhi_core.R_SINGLE_CHANNEL))
                   if np.isfinite(v))
    if len(_ends) == 2 and _ends[0] < _ends[1] - 1.0:
        _s_lo, _s_hi = float(np.floor(_ends[0])), float(np.ceil(_ends[1]))
        _bounded = True
    else:
        _s_lo, _s_hi, _bounded = -100.0, 100.0, False
    # A widened pair of curves can move the bound inside the reading already stored, and Streamlit
    # raises rather than clamping when a keyed value falls outside its own slider.
    _was = st.session_state.get("dhi_in_strength")
    if _was is not None:
        st.session_state["dhi_in_strength"] = float(np.clip(_was, _s_lo, _s_hi))
    _clamped = _was is not None and float(_was) != st.session_state["dhi_in_strength"]

    strength = st.slider(
        "DHI strength", _s_lo, _s_hi, float(np.clip(OPENING_STRENGTH, _s_lo, _s_hi)), 1.0,
        key="dhi_in_strength",
        help=f"Opens at {OPENING_STRENGTH:.0f}, just above the crossing point, so an untouched "
             f"slider states a barely supportive DHI rather than a neutral one. E-POS's default "
             f"on the same axis is {dhi_core.DEFAULT_STRENGTH:.0f}; the two scales are otherwise "
             f"the same.")
    if _clamped:
        # Moving a saved reading without saying so is how a prospect quietly stops being the
        # prospect that was saved. Two paths reach here: reopening work stored before the
        # ceiling existed, and widening the two curves so the same R arrives at a lower reading.
        st.info(
            f"The saved reading of {float(_was):+.0f} was outside the axis and has been moved "
            f"to {strength:+.0f}. The curves above put R = {dhi_core.R_SINGLE_CHANNEL:.0f} at "
            f"{_s_hi:+.0f}, which is as much as one channel may claim, so the old reading "
            f"asserted evidence the update does not carry. A stronger claim is made in the two "
            f"populations: drawn further apart, the same reading buys more."
        )

    if _bounded:
        st.caption(
            f"The axis ends at R = {dhi_core.R_SINGLE_CHANNEL:.0f} : 1 either way, {_s_lo:+.0f} to "
            f"{_s_hi:+.0f} on the curves above. That is Simm's ceiling for a single line of "
            "fluid-indicator evidence. A stronger claim comes from a second channel, or from two "
            "populations drawn further apart.")
    _lev["strength"] = st.empty()

    with st.expander("What a measured amplitude buys: the one published likelihood ratio"):
        st.markdown(
            "The only published numbers that put a measured value on this quantity are "
            "Kjønsberg, Hauge, Kolbjørnsen and Buland (2010), *Bayesian Monte Carlo method for "
            "seismic predrill prospect assessment*, Geophysics 75(5), O9–O19: the strongest "
            "anomaly bought a factor of 29 and absence at the outskirts 0.70, carrying the "
            "amplitude and the geometry together. Method: see 8.1.5."
        )

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
    n.plot(figs, f"The two-curve strength model, read at {strength:,.0f}. R is the ratio of the "
                 f"two marked heights, which is why the units on the axis do not matter.")

    # "POS on strength alone" is deliberately absent: it needs the prior, which is not computed
    # until the channels are combined, and a chance is a result rather than an input.
    #
    # The two likelihoods are here because Lars asked where P(DHI | G) was and the answer was
    # nowhere -- R arrived as a number with no visible parts, which is most of why it is hard to
    # argue with. They are the heights of the two dots in the figure above, divided by the curves'
    # common peak: both cases carry the same sd, so one peak serves both, the numbers land in
    # [0, 1] and their ratio is still exactly R.
    _peak = float(hc.pdf(hc.mean))
    _l_hc = float(hc.pdf(strength)) / _peak
    _l_no = float(no_hc.pdf(strength)) / _peak
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("L(DHI | G)", f"{_l_hc:.3f}", "if hydrocarbons", delta_color="off")
    s2.metric("L(DHI | not G)", f"{_l_no:.3f}", "if not", delta_color="off")
    s3.metric("R from strength", f"{r_strength:.2f}", band, delta_color="off")
    s4.metric("DHI volume weight", f"{dhi_core.volume_weight(r_strength):.3f}",
              "R / (R + 1)", delta_color="off")
    st.caption(
        f"The first two are the two dots in the figure above, scaled by the curves' shared peak "
        f"so they can be compared: how typical a reading of {strength:,.0f} is for a prospect "
        f"that works, and for one that does not. Their ratio is R exactly "
        f"({_l_hc:.3f} / {_l_no:.3f} = {r_strength:.2f}). Likelihoods, not probabilities; "
        f"only the ratio survives the arbitrary axis. Method: see 8.1.5."
    )
    # Worked from OPENING_STRENGTH rather than typed. The caption below used to quote a
    # default of 7 and the 37.5 % that follows from it; the slider moved to 5 on 6 Sep and
    # the prose did not. Same defect as the pooled curve's label, found by the same sweep.
    _opening_r = dhi_core.StrengthModel().r_at(OPENING_STRENGTH)
    _opening_shift = dhi_core.simm_update(0.30, _opening_r)
    st.caption(
        f"{band}: {band_note} At the opening reading of {OPENING_STRENGTH:.0f} the band is "
        f"{dhi_core.strength_bands(_opening_r)[0]}, and a 30 % prior becomes "
        f"{_opening_shift:.1%}. The volume weight `R / (R + 1)` is not a POS. Method: see 8.1.5."
    )

    # ------------------------------------------------------------------ p_valid
    # `p_valid` is `c`: P(the picked event is the contact | G, contact attributes). Nothing
    # else. Until 14 Sep 2026 it was `P(G | strength) x c`, which put the chance of hydrocarbons
    # inside a term that weights realisations already conditional on G, so the strength reached
    # the geometry posterior here and again in the combination. The ceiling, the R-c plane and
    # the override that came with that construction went with it. See `dhi.prospect_pos`.
    #
    # Published for the walkthrough sub-tab, which explains this number rather than producing
    # it. Same one-frame lag as everything else that crosses a sub-tab boundary.
    st.session_state["dhi_r_strength"] = float(r_strength)
    _elements = st.session_state.get("element_pos") or {}
    _p_g = float(np.prod([float(v) for v in _elements.values()])) if _elements else 1.0

    theme.heading(TAB, sub=n.sub, text="3 · Is the picked event the contact?")
    st.markdown(
        "A flat event can be lithology, a diagenetic front, fizz gas read as pay, or a "
        "processing artefact. This section states the chance that it is none of those, given a "
        "column here; §2 answers whether there is hydrocarbon at all, and the two enter the "
        "chance as separate factors. Method: see 8.1.6."
    )
    picked_levels = {}
    with st.expander("Grade the three contact attributes, for a suggested value of c"):
        st.markdown(
            "Contact attributes bear on whether the picked event is the base of the column; "
            "body attributes, graded in §2, on whether there is hydrocarbon (Monigle et al. "
            "2025). Method: see 8.1.6."
        )
        cols = st.columns(len(CONTACT_ATTRIBUTES))
        for col, (attribute, levels) in zip(cols, CONTACT_ATTRIBUTES.items()):
            picked_levels[attribute] = col.selectbox(
                attribute, list(levels),
                index=list(levels).index(DEFAULT_ATTRIBUTE_LEVELS[attribute]),
                key=f"dhi_in_attr_{attribute.replace(' ', '_').lower()}")
        scores = [CONTACT_ATTRIBUTES[a][lv] for a, lv in picked_levels.items()]
        suggested_c = float(np.prod(scores) ** (1.0 / len(scores)))
        st.caption(
            f"Suggested c = {suggested_c:.2f}, the geometric mean of "
            f"{', '.join(f'{s:.2f}' for s in scores)}, so that one poor attribute pulls the "
            f"value down. A heuristic, not a calibration. Method: see 8.1.6."
        )

    use_attributes = st.checkbox(
        f"Use the attributes' suggestion (c = {suggested_c:.2f})", value=False,
        key="dhi_in_c_from_attributes",
        help="Takes c from the three gradings above instead of the slider. Off by default: "
             "the combination rule is a heuristic, and a stated value is easier to defend than "
             "one a rule chose.")
    stated_c = st.slider(
        "Given there is hydrocarbon here, is the picked event its base?",
        0.05, 1.0, DEFAULT_CONTACT_GIVEN_HC, 0.01, key="dhi_in_contact_given_hc",
        disabled=use_attributes,
        help="P(the picked event is the contact | hydrocarbon present). A question about the "
             "event, not the amplitude and not the charge: granted a column here, is this flat "
             "thing its base rather than lithology, a diagenetic front, fizz, or an artefact. "
             "Conformance, flatness and whether it cuts structure answer it.")
    _lev["c"] = st.empty()
    contact_given_hc = suggested_c if use_attributes else stated_c
    p_valid = float(np.clip(contact_given_hc, 0.01, 0.99))

    pv1, pv2 = st.columns([1, 2])
    pv1.metric("p_valid", f"{p_valid:.2f}", f"floor {1 - p_valid:.2f}", delta_color="off")
    pv2.caption(
        f"The remaining {1 - p_valid:.2f} goes to a branch in which the pick says nothing about "
        f"depth, so the depth channel can say at most {p_valid / (1 - p_valid):.1f} : 1 against "
        f"any contact depth. It does not carry the chance of hydrocarbons, which enters once, "
        f"in §5. Method: see 8.1.6."
    )

    st.caption(
        "Anchors for the slider. These are judgements, not measurements, and the spacing "
        "matters more than the exact value.\n\n"
        "- 0.9 and up: a flat, conformable event that cuts dipping structure, with a clear "
        "fluid contact reflection.\n"
        "- 0.6 to 0.8: conformable and plausibly a contact, with something missing: no FCR, or "
        "terminations that are not sharp.\n"
        "- 0.3 to 0.5: the event is there and flat, and so is a plausible lithological "
        "explanation. The shipped default of 0.36 sits here; a well-conformed event is "
        "claimed by moving the slider rather than by leaving it.\n"
        "- Below 0.2: the event would not have been picked on a less interesting prospect. "
        "Whether there is a DHI at all is the question at this level."
    )

    # ------------------------------------------------------------------ combining
    theme.heading(TAB, sub=n.sub, text="3b · Detection function D(h)")
    st.markdown(
        "The chance a column of height h produces a detectable anomaly. It is what makes an "
        "absent anomaly usable evidence; the fourth input sets how much absence says about the "
        "chance. Method: see 8.1.6."
    )
    d1, d2, d3, d4 = st.columns(4)
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
    false_positive = d4.number_input(
        "Barren trap shows, relative", 0.0, 1.0, 0.5, 0.05, key="dhi_in_false_positive",
        help="How often a trap with no hydrocarbons shows an anomaly of this class, as a fraction "
             "of how often a hydrocarbon-filled trap of this geometry does. 0 says a barren trap "
             "never shows; 1 says it shows as readily as a filled one, and absence then says "
             "nothing about the chance. Elicited; no calibration is known to the tool, and 0.5 "
             "is the maximum-ignorance default rather than a measurement. It acts only when "
             "nothing was seen.")
    _lev["h50"], _lev["steep"], _lev["det_ceiling"] = d1.empty(), d2.empty(), d3.empty()
    _lev["false_positive"] = d4.empty()
    detection = DetectionFunction(h50_m=h50, steepness_m=steep, ceiling=ceiling,
                                  false_positive=false_positive)

    grid = np.linspace(0.0, max(float(result.column_m.max()), h50 * 3), 300)
    figd = go.Figure()
    figd.add_scatter(x=detection.at(grid), y=apex + grid, mode="lines", name="D(h)",
                     line=dict(color=POSTERIOR, width=3))
    figd.add_hline(y=apex + h50, line=dict(color="#888", dash="dot"),
                   annotation_text=f"50 % at {h50:.0f} m column")
    figd.update_layout(xaxis_title="P(detectable)", xaxis_range=[0, 1],
                       yaxis_title="Contact depth (m TVDSS)", yaxis=dict(autorange="reversed"),
                       height=380, margin=dict(t=20), showlegend=False)
    n.plot(figd, "The detection function, logistic in column height. Its shape is a modelling "
                 "choice, exposed rather than hard-coded. Method: see 8.1.6.")

    # ------------------------------------------------------------------ the update
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
        theme.heading(TAB, sub=n.sub, text="3c · Well control")
        lo, hi = control.bracket()
        bits = []
        if control.hc_down_to_m is not None:
            bits.append(f"hydrocarbons proven to {control.hc_down_to_m:,.0f} m")
        if control.water_at_m is not None:
            bits.append(f"water at {control.water_at_m:,.0f} m")
        inside = float(((result.contact_m > lo) & (result.contact_m < hi)).mean())
        st.markdown(
            f"The penetration described on tab 2.0 is multiplied into the weights: "
            f"{' and '.join(bits)}, tied to the mapped surface with σ = "
            f"{control.depth_sigma_m:,.0f} m, and a {control.p_connected:.0%} chance it samples "
            f"this accumulation.\n\n"
            f"{inside:.0%} of the geological realisations already sit inside what the well "
            f"allows. The update pushes the rest toward the floor of "
            f"`1 − {control.p_connected:.2f} = {1 - control.p_connected:.2f}`, which stops one "
            f"penetration ruling a contact out altogether."
        )
        if inside < 0.05:
            st.warning(
                "The well and the geological model disagree almost completely. Nearly every "
                "realisation falls outside what the penetration allows, so all are penalised by "
                "roughly the same amount, the likelihood is flat, and the posterior comes out "
                "close to the prior. That is a disagreement, not a well that said nothing: "
                "either the depths are tied to a different datum than the apex, or the limits on "
                "tab 3.0 let the column go where this well has ruled it out."
            )

    # Published for the trust panel on tab 4.0, which reports the effective sample size behind this
    # update. Same one-frame lag as `dhi_overlay` below and for the same reason: tab 4.0 renders
    # first, so it reads the posterior built on the previous run. Every interaction reruns both.
    st.session_state["dhi_posterior"] = post

    if post.effective_sample_size < 300:
        st.warning(
            f"Effective sample size {post.effective_sample_size:,.0f}. The picked contact sits "
            f"far out in the tail of the geological prior, so the posterior rests on very few "
            f"realisations. That is a finding about the model or the pick, not a number to "
            f"read off."
        )

    # --------------------------------------------------------------- the chain
    # POS(h_min) = P(G | strength) x P(h >= h_min | G, geometry). The first factor is the
    # element product from tab 2.0 updated by the amplitude character; the second is read off
    # the same weights that draw the histogram and the percentiles below. Nothing is blended and
    # nothing is rescaled: the curve `P(G | strength) x F_post(h)` passes through the headline
    # at h_min by identity. Until 14 Sep 2026 the headline was `simm_update(P(G) x F_prior,
    # blend(r_dhi, R_strength))`, which counted the strength twice (it had already entered
    # the weights through p_valid) and applied a ratio between two column heights inside G
    # as if it were a likelihood ratio on the prospect. See `dhi.prospect_pos`.
    #
    # Nothing seen, nothing to characterise: the strength axis grades an observed anomaly. With
    # no anomaly the chance is updated by `absence_ratio` instead -- P(absent | G) over
    # P(absent | not G), audit finding P1-0 -- so that an absent DHI reads against the prospect
    # rather than as neutral, and never as encouraging.
    element_pos = st.session_state.get("element_pos") or {}
    element_product = float(np.prod([float(v) for v in element_pos.values()])) if element_pos else 1.0
    r_applied = dhi_core.applied_ratio(result, detection, observation, r_strength)
    st.session_state["dhi_r_applied"] = float(r_applied)
    p_g_updated = dhi_core.p_g_given_strength(element_product, r_applied)
    geometric_prior = post.pos(posterior=False)
    posterior_geometric = post.pos()
    prior_pos = element_product * geometric_prior
    posterior_pos = dhi_core.prospect_pos(element_product, r_applied, post)

    # ---- what each control is worth, into the placeholders reserved beside them -----------
    # Everything the tab reads is known by this line and not one line earlier, which is why
    # the captions are placeholders: the detection function is read below the pick. A caption
    # written where its control is drawn would be quoting the previous rerun.
    #
    # `_state` rebuilds the whole tab at one changed value rather than patching the
    # likelihood, so the swing reported is the swing a user would get by dragging the control.
    def _state(**over):
        _s = over.get("strength", strength)
        _r = model.r_at(_s)
        _pv = float(np.clip(over.get("c", contact_given_hc), 0.01, 0.99))
        _det = DetectionFunction(h50_m=over.get("h50", h50),
                                 steepness_m=over.get("steep", steep),
                                 ceiling=over.get("det_ceiling", ceiling),
                                 false_positive=over.get("false_positive", false_positive))
        _obs = DhiObservation(
            seen=seen,
            contact_m=None if partial or not seen else over.get("contact", contact),
            pick_sigma_m=over.get("sigma", sigma), area_km2=area or None,
            pick_shape=shape, shallowest_m=None if partial else shallowest,
            deepest_m=None if partial else deepest,
            p_valid=_pv, absent_below_m=absent_below)
        return (result, _det, _obs, element_product, _r)

    _span = (float(result.contact_m.min()), float(result.contact_m.max()))
    _sweeps = {
        "strength": (lambda v: _state(strength=v), np.linspace(_s_lo, _s_hi, 9)),
        "c": (lambda v: _state(c=v), np.linspace(0.05, 1.0, 9)),
        "sigma": (lambda v: _state(sigma=v), [3.0, 8.0, 15.0, 30.0, 60.0, 120.0]),
        "contact": (lambda v: _state(contact=v), np.linspace(_span[0], _span[1], 9)),
        "h50": (lambda v: _state(h50=v), [5.0, 15.0, 25.0, 50.0, 100.0]),
        "steep": (lambda v: _state(steep=v), [2.0, 5.0, 8.0, 20.0, 50.0]),
        "det_ceiling": (lambda v: _state(det_ceiling=v), [0.5, 0.7, 0.9, 0.99]),
        "false_positive": (lambda v: _state(false_positive=v), [0.0, 0.25, 0.5, 0.75, 1.0]),
    }
    for _name, _slot in _lev.items():
        _build, _values = _sweeps[_name]
        _slot.caption(_leverage_caption(dhi_core.leverage(_build, _values)))

    if not element_pos:
        st.warning(
            "No element risk is set, so the update is anchored to the geometric chance alone. "
            "Play x conditional on tab 2.0 supplies P(G); anchoring a DHI to a probability of "
            "1.0 makes any evidence look like it changed nothing."
        )

    # ------------------------------------------------------------------ 4 · the contact
    theme.heading(TAB, sub=n.sub, text="4 · Posterior contact distribution")
    st.markdown(
        "The contact distribution given the elements worked, reweighted by the pick. "
        "Percentiles are over the realisations that reach the assessment minimum, in the "
        "exceedance convention: P90 is the shallow end."
    )
    c1, c2, c3, c4 = st.columns(4)
    for _col, _p in ((c1, 90), (c2, 50), (c3, 10)):
        _col.metric(f"Contact P{_p}", f"{post.percentiles(float(_p))[0]:,.0f} m",
                    f"geological {post.percentiles(float(_p), posterior=False)[0]:,.0f} m",
                    delta_color="off")
    c4.metric("Effective sample size", f"{post.effective_sample_size:,.0f}",
              f"of {result.n:,}", delta_color="off")
    _edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 61)
    _centres = 0.5 * (_edges[:-1] + _edges[1:])
    figh = go.Figure()
    for _label, _w, _colour in ((theme.GEOLOGICAL, None, theme.BASIS_COLOUR[theme.GEOLOGICAL]),
                                (theme.evidence_basis(), post.weights,
                                 theme.BASIS_COLOUR[theme.GIVEN_DHI])):
        _counts, _ = np.histogram(result.contact_m, bins=_edges, weights=_w)
        _total = float(_counts.sum())
        figh.add_bar(y=_centres, x=_counts / _total if _total else _counts, orientation="h",
                     name=_label, opacity=0.55, marker_color=_colour, marker_line_width=0,
                     hovertemplate="%{y:.0f} m TVDSS<br>%{x:.1%} of realisations<extra></extra>")
    for _p, _dash in ((90, "dot"), (50, "solid"), (10, "dot")):
        figh.add_hline(y=float(post.percentiles(float(_p))[0]), line=dict(color=POSTERIOR, dash=_dash, width=1.2),
                       annotation_text=f"P{_p}", annotation_position="top left")
    if h_min > 0:
        figh.add_hline(y=apex + h_min, line=dict(color="#333", dash="dash", width=1.2),
                       annotation_text="assessment minimum", annotation_position="bottom right")
    figh.update_layout(barmode="overlay", bargap=0.04, xaxis_title="Share of realisations per depth bin",
                       xaxis_tickformat=".0%", yaxis_title="Contact depth (m TVDSS)",
                       yaxis=dict(autorange="reversed"), height=420, margin=dict(t=20),
                       legend=dict(orientation="h", y=-0.18))
    n.plot(figh, "Where the contact is, before and after the pick. Both histograms are over "
                 "every realisation and conditional on the elements having worked; the lines are "
                 "the posterior percentiles over the realisations above the assessment minimum. "
                 "The amplitude character does not enter this figure: it updates the chance of "
                 "hydrocarbons, not where the contact is given that there are.")

    # ------------------------------------------------------------------ 5 · the chance
    theme.heading(TAB, sub=n.sub, text="5 · Prospect chance against threshold")
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Prospect POS at h ≥ {h_min:.0f} m", f"{posterior_pos:.1%}",
              f"prior {prior_pos:.1%}")
    m2.metric("P(G | amplitude)", f"{p_g_updated:.1%}",
              f"P(G) {element_product:.1%} from tab 2.0", delta_color="off")
    m3.metric(f"P(column ≥ {h_min:.0f} m | G, pick)", f"{posterior_geometric:.1%}",
              f"geological {geometric_prior:.1%}", delta_color="off")

    st.caption(
        f"`P(G | amplitude)` = {element_product:.3f} updated by R = {r_applied:.2f} gives "
        f"{p_g_updated:.3f} (§2). `P(column ≥ h_min | G, pick)` = {posterior_geometric:.3f}, "
        f"against {geometric_prior:.3f} from the geology alone (§1, §3). `Prospect POS` = "
        f"{p_g_updated:.3f} × {posterior_geometric:.3f} = {posterior_pos:.3f}. The chance and "
        f"the contact distribution below are read off the same weighted realisations. Method: "
        f"see 8.1.5."
    )

    # **Multiplied through by the element product.** Drawn as the bare exceedance this figure read
    # 100 % at a 5 m assessment minimum while the prospect POS there was 40.8 %, under a heading
    # that called it POS. `P(column >= h)` is the *conditional* column term; a POS is that times
    # the chance the prospect works at all, and the difference is the whole terminology error this
    # tool exists to prevent.
    st.markdown(
        "Along a dashed line the gap is what the DHI did; between the lines it is what the "
        "threshold did."
    )
    t1, t2 = st.columns([1, 1])
    with t1:
        show_all = st.toggle(
            "Show what dropping a term would give", value=False, key="combo_all_5",
            help="Two comparisons, not two alternatives: the pooled curve is this update with "
                 "the detection function left out, and the scenario switch is a mixture, which "
                 "can widen the answer but never sharpen it and cannot move the chance at all. "
                 "The pooled curve drops two things -- Cromwell\u2019s floor and the detection "
                 "function -- and the caption below says how much each is worth here.")
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

    # No rescaling. Each curve is one constant times one exceedance function -- P(G) times the
    # geological F(h), P(G | amplitude) times the updated F(h) -- and reads its headline at h_min
    # by identity. The `_anchored` helper this replaces existed because the blended headline was
    # not the integral of the distribution drawn beside it.
    geological = element_product * np.asarray(post.exceedance(hs, posterior=False), dtype=float)
    updated = dhi_core.prospect_pos_curve(element_product, r_applied, post, hs)

    def _comparison_curve(exceedance_fn):
        """A rival construction of the conditional term, on the same first factor.

        The pooled and scenario curves are alternative geometry updates, so they take the same
        `P(G | amplitude)` the Bayesian one does and differ only in the second factor.
        """
        return p_g_updated * np.asarray(exceedance_fn, dtype=float)

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

    # Kept so the caption can report it. See `_pooled_note`.
    pooled_gap = None
    floor_part = None
    if show_all and seen:
        for method, dash in ((dhi_core.POOLED, "dash"), (dhi_core.SCENARIO, "dot")):
            curve = _comparison_curve(
                dhi_core.combination_exceedance(result, detection, observation, hs, method=method))
            if method == dhi_core.POOLED:
                pooled_gap = float(np.abs(np.asarray(curve) - np.asarray(updated)).max())
                # The same comparison with the detection function held flat, so the caption can
                # say how much of the gap is the floor rather than asserting a split that moves
                # with p_valid.
                _flat = dhi_core.DetectionFunction(h50_m=1e-6, steepness_m=1e-6, ceiling=1.0)
                _flat_curve = _comparison_curve(
                    dhi_core.combination_exceedance(result, _flat, observation, hs,
                                                    method=dhi_core.BAYES))
                floor_part = float(np.abs(np.asarray(curve) - np.asarray(_flat_curve)).max())
            fig.add_scatter(x=curve, y=depths, mode="lines", opacity=0.65,
                            name={dhi_core.POOLED: "…with the floor and D(h) dropped",
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
        geo = float(element_product * post.exceedance(h, posterior=False)[0])
        upd = float(dhi_core.prospect_pos_curve(element_product, r_applied, post,
                                                np.array([h]))[0])
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
    fig.add_scatter(x=[p_g_updated * 0.5], y=[median_contact], mode="markers",
                    marker=dict(color=POSTERIOR, size=13, symbol="circle-open",
                                line=dict(width=3)),
                    name=f"posterior median contact, {median_contact:,.0f} m", hoverinfo="skip")

    fig.update_layout(xaxis_title="Prospect POS  =  P(G | amplitude) × P(column ≥ h | G, pick)",
                      xaxis_range=[0, min(1.0, max(element_product, p_g_updated,
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
    n.plot(fig, "The chance against threshold: P(G) × F(h) geological, P(G | amplitude) × "
                "F(h | G, pick) updated. The amplitude scales the whole curve; the pick reshapes "
                "it, raising the chance near and above the picked contact and lowering it below. "
                "The open circle is the posterior median, which lands on the pick. Method: see "
                "8.1.5."
                + _pooled_note(pooled_gap, floor_part))

    n.table(
        pd.DataFrame(rows),
        "POS and its threshold, as a pair. These are readings of the curve above rather than "
        "separate numbers, which is why a volume is taken at the same row as the chance beside "
        "it. The chance to quote is the one at the row the volume was computed at.")

    theme.heading(TAB, sub=n.sub, text="5b · The two factors")
    # The two channels multiply as separate factors and no dependence parameter is applied
    # (the blended `CombinedUpdate.dependence` is retained only for the teaching comparison and
    # never reaches a number on this tab). The relation between the two is at elicitation --
    # body and contact attributes both improve with impedance contrast -- and that is a
    # heuristic judgement made by the assessor, not a fitted joint distribution. Audit item 7,
    # 16 Sep 2026.
    st.markdown(
        "Two questions, two factors: the character updates the element chance; given "
        "hydrocarbons, the pick updates the column distribution. Each enters once, and no "
        "dependence parameter is applied between them; the two judgements are related at "
        "elicitation, which is a heuristic and not a fitted joint distribution. Method: see "
        "8.1.5."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("R, amplitude character" if seen else "R, absent anomaly", _fmt_r(r_applied),
              dhi_core.strength_bands(r_applied)[0] if seen
              else f"(1 − d) / (1 − f·d), d = {float(np.mean(detection.at(result.column_m))):.2f}",
              delta_color="off")
    c2.metric("P(G | amplitude)" if seen else "P(G | absence)", f"{p_g_updated:.1%}",
              f"P(G) {element_product:.1%}", delta_color="off")
    c3.metric(f"P(column ≥ {h_min:.0f} m | G, {'pick' if seen else 'absence'})",
              f"{posterior_geometric:.1%}",
              f"geological {geometric_prior:.1%}", delta_color="off")
    c4.metric("Prospect POS", f"{posterior_pos:.1%}", f"prior {prior_pos:.1%}")

    # Published for tab 4.0, which draws the posterior beside the per-element decomposition.
    # Tab 4.0 renders before this one, so it reads the value written on the previous run, a
    # one-frame lag that is invisible in practice because every interaction reruns both.
    # Storing the curve rather than the object keeps the dependency one-way.
    depth_grid = apex + np.linspace(0.0, float(result.column_m.max()), 300)
    st.session_state["dhi_overlay"] = {
        "depths_m": depth_grid,
        # Scaled to the prospect chance, not left conditional: the Risk against depth sub-tab
        # draws this against per-element curves that already carry the element chances. Each
        # curve is one constant times one exceedance function and reads its headline at h_min
        # by identity.
        "pos_curve": dhi_core.prospect_pos_curve(element_product, r_applied, post,
                                                 depth_grid - apex),
        "prior_curve": element_product * np.asarray(
            post.exceedance(depth_grid - apex, posterior=False), dtype=float),
        # A resampled set of contacts, so downstream code that needs samples rather than a
        # curve (the export, the benchmark comparison) gets the posterior distribution itself.
        # Importance resampling with replacement, exact in the limit and honest about the
        # effective sample size above.
        "contact_samples": _resample(result.contact_m[result.above_minimum],
                                     post.weights[result.above_minimum],
                                     int(st.session_state.get("n_trials", 10_000))),
        # The raw per-realisation weights, so the sibling sub-tab can rebuild the decomposition
        # as its posterior twin rather than being handed one pre-computed curve.
        "weights": post.weights,
        "picked_contact_m": float(contact) if seen else None,
        "prior_pos": float(prior_pos),
        "posterior_pos": float(posterior_pos),
        "p_g_given_amplitude": float(p_g_updated),
        "h_min": float(h_min),
    }

    # ------------------------------------------------------------------ 6 · assumptions
    # In the open, not behind a fold. Each is labelled for what it is: an elicited judgement,
    # a heuristic, or a modelling choice. None is solved by wording.
    theme.heading(TAB, sub=n.sub, text="6 · Assumptions and limitations")
    _d_at = detection.at(result.column_m)
    _d_flat = float(_d_at.max() - _d_at.min()) < 1e-3
    st.markdown(
        "Elicited judgements and heuristics.\n\n"
        "- R: the ratio of two elicited curves at an elicited reading, capped at "
        + f"{dhi_core.R_SINGLE_CHANNEL:.0f}" + " : 1 either way. Elicited judgement.\n"
        "- c: typed, or the geometric mean of three graded attributes. Heuristic, not a "
        "calibration."
    )
    st.markdown(
        "Modelling choices.\n\n"
        "- The detection function is logistic in column height."
        + (" At these inputs it is at its ceiling for every realisation, so only the ceiling "
           "acts." if _d_flat else "") + "\n"
        "- One fluid: a flat spot is taken as the hydrocarbon–water contact; a gas–oil contact "
        "picked as one understates the column.\n"
        "- Absence: P(absent | G) / P(absent | no hydrocarbons), with the barren trap's chance "
        "of showing tied to the filled trap's by the rate in §3b. Elicited, uncalibrated.\n"
        "- A flat event that is not the contact is equally likely at any depth in the model's "
        "contact range.\n"
        "- The pick and a penetration are multiplied as independent evidence.\n"
        "- Floors of 1 − c and 1 − p_connected keep every contact depth in play (Cromwell's "
        "rule).\n"
        "- Where every realisation clears the assessment minimum, the pick cannot move the "
        "chance.\n\n"
        "Method: see 8.1.6 and 8.1.9."
    )

    # ------------------------------------------------------------------ cross-checks
    # ------------------------------------------------------------- success attribution
    with st.expander(
            "Diagnostics: what the answer rests on, and what the older formulation would "
            "have said", expanded=False):
        st.caption(
            "The sections above are the answer. The sections here say how far to trust it: what "
            "it rests on, which mechanism the amplitude promoted, whether the anomaly area agrees "
            "with the column, and what the scenario switch would have given instead. A first pass "
            "does not need them."
        )

        theme.heading(TAB, sub=n.sub, text="7 · What is this answer most sensitive to?")
        st.markdown(
            "Geological inputs are sliced by decile as on tab 4.0, with likelihood-weighted "
            "means; the DHI's typed numbers are moved one at a time and the realisations "
            "reweighted. Method: see 8.1.8."
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
                   f"What the DHI-updated mean rests on. Blue bars are geological inputs, sliced by "
                   f"decile and weighted by the likelihood; red bars are the DHI's own typed numbers, "
                   f"each moved one at a time: the pick \u03c3 halved and doubled, the picked contact "
                   f"by half a \u03c3, the detection parameters across the span an assessor cannot "
                   f"pin down.\n\n"
                   f"Where a typed DHI number moves the answer further than the geology does, the "
                   f"posterior is a statement about the seismic assumptions rather than about the "
                   f"prospect. Method: see 8.1.8.")
        else:
            st.info("Not enough weight spread to slice a sensitivity from this posterior.")

        theme.heading(TAB, sub=n.sub,
                      text=f"7 · Which mechanism set the contact, {theme.evidence_basis()}")
        st.markdown(
            "This table re-attributes the shallowest active limit, not the risk: the element "
            "chances on tab 2.0 are untouched. Given the contact is where the amplitude says, "
            "which mechanism stopped it there is what the evidence can answer. Method: see "
            "8.1.5."
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
                f"{theme.basis_tag(theme.GIVEN_DHI)} &nbsp; Share of successful realisations in "
                f"which each mechanism was the shallowest active limit, before and after the update. "
                f"A mechanism that cannot produce a contact where the amplitude was picked loses "
                f"share; one that naturally produces that contact gains it. The column reads as what "
                f"stopped the column, not as where the risk is.")

        theme.heading(TAB, sub=n.sub, text="8 · Cross-checks")
        if not (seen and area):
            st.caption("The area cross-check needs an anomaly area in §1.")
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
                    st.success("The two readings agree and count as one observation with a tighter σ.")
                elif cross["disagreement_m"] < 0:
                    st.warning(
                        "The anomaly is narrower than its down-dip limit implies. It may not fill "
                        "the closure: a stratigraphic or diagenetic component, or a smaller "
                        "effective trap than the one mapped.")
                else:
                    st.warning(
                        "The anomaly extends beyond the mapped conformance. A non-fluid cause, "
                        "lithology or tuning, is the usual explanation.")
                if not ok:
                    st.error(f"Containment fails. {msg}")
            st.caption(
                "A DHI gives two readings of the contact: the down-dip termination and the areal "
                "extent through the area–depth table. They should agree, and nothing forces them "
                "to, which is why the check is here."
            )

        # ------------------------------------------------------------------ formulation A
        theme.heading(TAB, sub=n.sub, text="9 · What the scenario switch would have said")
        st.markdown(
            "`IF(DHI valid, DHI contact, geological contact)` is the older method; it moves the "
            "contact and not the chance. A comparison, not an alternative model: its one "
            f"parameter lives inside the likelihood in §3 at p_valid = {p_valid:.2f}. Method: "
            "see 8.1.5."
        )
        if seen:
            switched = dhi_core.scenario_switch(result, p_valid, contact, sigma)
            s1, s2, s3 = st.columns(3)
            for col, p in ((s1, 90), (s2, 50), (s3, 10)):
                col.metric(f"Contact P{p}, scenario switch",
                           f"{np.percentile(switched, 100 - p):,.0f} m",
                           f"likelihood form {post.percentiles(p)[0]:,.0f} m", delta_color="off")
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

    The DHI path is untouched. There the amplitude updates P(G) and the pick updates the column
    distribution; here there is no amplitude, so the chance is P(G) times the well-updated
    column term, which is the same chain with the character factor at one.
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
        # The same quantity the amplitude branch writes, so the sibling sub-tab can draw either
        # without knowing which: P(G) times the exceedance, with no amplitude to update P(G).
        "pos_curve": dhi_core.prospect_pos_curve(product, 1.0, posterior, depth_grid - apex),
        "prior_curve": product * np.asarray(
            posterior.exceedance(depth_grid - apex, posterior=False), dtype=float),
        "contact_samples": _resample(result.contact_m[result.above_minimum],
                                     posterior.weights[result.above_minimum],
                                     int(st.session_state.get("n_trials", 10_000))),
        "weights": posterior.weights,
        "picked_contact_m": None,
        "prior_pos": prior_pos,
        "posterior_pos": posterior_pos,
        "p_g_given_amplitude": product,
        "h_min": h_min,
    }

    theme.basis_banner(
        theme.GIVEN_DHI,
        "There is no amplitude on this prospect, so the update below is the penetration alone. "
        "The geological model on tab 4.0 is unchanged by it.")
    theme.heading(TAB, sub=n.sub, text="1 · The penetration, as evidence")
    lo, hi = control.bracket()
    bits = []
    if control.hc_down_to_m is not None:
        bits.append(f"hydrocarbons proven to {control.hc_down_to_m:,.0f} m")
    if control.water_at_m is not None:
        bits.append(f"water at {control.water_at_m:,.0f} m")
    inside = float(((result.contact_m > lo) & (result.contact_m < hi)).mean())
    st.markdown(
        f"The well described on tab 2.0: {' and '.join(bits)}, tied to the mapped surface with "
        f"σ = {control.depth_sigma_m:,.0f} m, and a {control.p_connected:.0%} chance that it "
        f"samples this accumulation.\n\n"
        f"{inside:.0%} of the geological realisations already sit inside what the well allows. "
        f"The update pushes the rest down toward the floor of "
        f"`1 − {control.p_connected:.2f} = {1 - control.p_connected:.2f}`, which is what stops one "
        f"penetration ruling a contact out altogether.\n\n"
        f"Prospect POS {prior_pos:.1%} → {posterior_pos:.1%}, on an effective sample size of "
        f"{posterior.effective_sample_size:,.0f} of {result.n:,}. Sub-tabs 5.2 and 5.3 are drawn "
        f"on this."
    )
    if inside < 0.05:
        st.warning(
            "The well and the geological model disagree almost completely. Nearly every "
            "realisation falls outside what the penetration allows, so all of them are penalised "
            "by roughly the same saturated amount, the likelihood goes flat, and the posterior "
            "comes out close to the prior. That is a disagreement, not a weak update: either the "
            "depths are tied to a different datum than the apex, or the limits on tab 3.0 let "
            "the column go where this well has already ruled it out."
        )
    st.info(
        "There is no R and no tornado on this page. Both are statements about an amplitude, "
        "since E-POS's `r_dfi` compares the seismic likelihood over tall columns against short "
        "ones, and there is no amplitude here. The evidence is a depth bracket, and its effect is "
        "visible directly in the contact distribution on tab 5.2."
    )

