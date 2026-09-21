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
from plotly.subplots import make_subplots

from hcwc.core import defaults
from hcwc.core import dhi as dhi_core
from hcwc.core import engine
from hcwc.core import dhi_comparison as comparison
from hcwc.core import sensitivity
from hcwc.core import well as well_core
from hcwc.core.dhi import DetectionFunction, DhiObservation
from hcwc.core import pos
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
OPENING_STRENGTH = defaults.OPENING_EVIDENCE_INDEX

#: Where `p_valid` opens: an even chance that the picked event is a fluid contact.
#: Deliberately a round number and not `R/(R+1)` at the opening strength, because it is a
#: judgement about the *event* and the two must be answered separately. See the p_valid
#: block in `render` for what went wrong when it was derived.
#: `P(the picked event is the contact | there is hydrocarbon)` — the conditional factor the
#: geophysicist supplies. `p_valid` is this times the amplitude-updated `P(G)`, so the two
#: judgements stay separate and the product cannot exceed the chance of any hydrocarbon.
#: 0.36 since 15 Sep 2026 (Lars), from 0.70: a cautious opening value. The floor under the
#: pick is then 0.64, so an untouched slider lets the pick say at most 0.56 : 1 against any
#: contact depth; a well-conformed event is claimed by moving it. The graded attributes open at
#: a geometric mean of 0.25 since 20 Sep 2026, so the stated value and the suggestion differ.
DEFAULT_CONTACT_GIVEN_HC = defaults.DEFAULT_CONTACT_GIVEN_HC

#: The three routes to c on tab 5.1.3, as the radio names them.
C_STATED, C_FROM_ATTRIBUTES, C_FROM_SCORE = ("Stated", "Graded attributes",
                                             "DHI score, Monigle et al. (2025)")
#: The DHI score whose calibrated rule gives the shipped c, so the untouched route agrees with
#: the untouched slider: 2 x 0.18 = 0.36.
DEFAULT_DHI_SCORE = defaults.DEFAULT_DHI_SCORE

#: The three **contact** attributes, after Monigle et al. (2025), who separate them from the
#: *body* attributes that grade the amplitude. These answer whether the picked event is the
#: base of the column; the strength slider answers whether there is a column. The numbers are
#: elicited judgements, not a calibration -- which is why the result is offered rather than
#: applied. The shipped selections (:data:`DEFAULT_ATTRIBUTE_LEVELS`) give c = 0.25, one level
#: below the slider's 0.36 on fit to structure, so an untouched tab shows the stated value and
#: the graded suggestion side by side and different (Lars, 20 Sep 2026).
DEFAULT_ATTRIBUTE_LEVELS: dict[str, str] = defaults.DEFAULT_ATTRIBUTE_LEVELS

CONTACT_ATTRIBUTES: dict[str, dict[str, float]] = defaults.CONTACT_ATTRIBUTES


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

    Its cost is honest and already reported: the effective sample size, in §6. A posterior
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
            "to 4.0 stands on its own either way. Method: see 8.1.6."
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
    st.markdown(
        "One observation, two DHI information channels. The evidence index (§2) updates "
        "P(G), the chance of hydrocarbons; the contact geometry (§1, §3) updates the HCWC "
        "distribution given G. Each enters the chance once. Method: see 8.1.6."
    )
    # The update at a glance (master brief §27): what moved, before and after, filled once the
    # chain below has run. The four numbers a reader wants first, above the inputs that set them.
    _glance = st.container()

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
    theme.heading(TAB, sub=n.sub, text="1 · DHI evidence present")
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
    DEFAULT_SIGMA_M = defaults.DEFAULT_PICK_SIGMA_M
    PROSPECT_PICK_M = defaults.DEFAULT_PICK_M
    lo_prior, hi_prior = np.percentile(result.contact_m, [1.0, 99.0])
    default_contact = (PROSPECT_PICK_M if lo_prior <= PROSPECT_PICK_M <= hi_prior
                       else float(np.percentile(result.contact_m, 50)))
    shape = st.radio(
        "Pick uncertainty: shape", dhi_core.PICK_SHAPES, horizontal=True,
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
        # because the area cross-check in §9 reads it, and for this case the cutoff is the only
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
            "Indicated contact (m TVDSS)", 0.0, 10000.0, default_contact, 5.0, disabled=not seen,
            key="dhi_in_contact",
            help="The depth the DHI indicates: the down-dip amplitude termination or flat spot. An "
                 "indication, not a detection; the contact attribution in section 3 says how "
                 "far it is taken as the contact. The tool reads it as the hydrocarbon–water "
                 "contact and does not ask whether it is a gas–oil contact. "
                 "On a two-phase prospect the amplitude is poor at resolving that, and a GOC "
                 "picked as an HCWC understates the column.")
        if seen:
            _lev["contact"] = o1.empty()
        sigma = o2.number_input(
            "Pick uncertainty σ (m)", 1.0, 500.0, DEFAULT_SIGMA_M, 1.0, key="dhi_in_sigma",
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
        help="Used for the cross-check in §9. Leave at zero to skip.")
    if seen and area:
        # Containment, A(h_min) ≤ A_DHI, beside the input rather than only in the diagnostics
        # fold (master brief §16): if it fails, the DHI and the success case being risked are
        # not the same object, and the reader should see that before reading any update.
        try:
            _table = sources.current_area_depth()
            if _table is not None:
                _ok, _msg = dhi_core.containment_ok(_table.depths_m, _table.top_area_km2,
                                                    _table.apex_m, h_min, area)
                if not _ok:
                    st.error(f"Containment fails: {_msg}")
        except (FileNotFoundError, ValueError):
            pass

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
               "line at the rate the pick error sets. Method: see 8.1.5.")

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

        prior_span = float(np.diff(engine.weighted_percentiles(result.contact_m, None, [90.0, 10.0]))[0])
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
               "realisations, which §6 reports as the effective sample size. Method: see 8.1.5.")

    # A penetration described on tab 2.0 is evidence present too, and its note belongs in §1;
    # it is computed after the update below, so the slot is reserved here and filled there.
    _well_slot = st.container()

    # ------------------------------------------------------------------ strength channel
    theme.heading(TAB, sub=n.sub, text="2 · DHI evidence index: updates P(G)")
    st.markdown(
        "The first channel. §1 recorded where the anomaly terminates; this section places its "
        "character on the DHI evidence index, a relative scale for the strength and polarity of "
        "the seismic evidence: 0 is neutral, positive values increasingly positive evidence, "
        "negative values increasingly negative evidence or a missing expected response. The "
        "values have no physical units. The index updates the chance of hydrocarbons and does "
        "not enter the contact distribution; §5 multiplies the two. Strong evidence raises P(G) "
        "and does not narrow the contact: the spread stays with the pick (§1), the attribution "
        "(§3) and the detection model (3b)."
    )
    st.caption(
        "The evidence model is two conditional densities on the index, f(s | HC) for "
        "hydrocarbon-bearing outcomes and f(s | NoHC) for non-hydrocarbon ones; their ratio at "
        "the observed index is the likelihood ratio LR(s), the evidence weight. P(G) from tab "
        "2.0 is the prior it updates: P(G | s) = LR(s) P(G) / (LR(s) P(G) + 1 − P(G)). "
        "Method: see 8.1.4."
    )

    with st.expander("The two reference distributions"):
        st.caption(
            "Each is a Gaussian on the index given by its 1st and 99th percentiles: the "
            "hydrocarbon-bearing reference distribution and the non-hydrocarbon one. Further "
            "apart, the index separates the two outcomes better; overlapping is the usual state. "
            "The defaults are the reference relationship the tool ships with, not a calibration "
            "for this basin.")
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
        "DHI evidence index", _s_lo, _s_hi, float(np.clip(OPENING_STRENGTH, _s_lo, _s_hi)), 1.0,
        key="dhi_in_strength",
        help="Relative evidence scale. Positive values indicate increasingly positive DHI "
             "evidence; negative values indicate increasingly negative evidence. The scale is "
             f"conceptual and has no physical units. Neutral evidence is where the two reference "
             f"distributions cross; opens at {OPENING_STRENGTH:.0f}, just above it, so an "
             f"untouched slider states barely supportive evidence rather than none.")
    _neutral = model.strength_at(1.0)
    st.caption(
        "Neutral evidence = "
        + (f"{_neutral:.0f}" if np.isfinite(_neutral) else "where the two curves cross")
        + f"; this prospect reads {strength:+.0f}."
    )
    if _clamped:
        # Moving a saved reading without saying so is how a prospect quietly stops being the
        # prospect that was saved. Two paths reach here: reopening work stored before the
        # ceiling existed, and widening the two curves so the same R arrives at a lower reading.
        st.info(
            f"The saved reading of {float(_was):+.0f} was outside the axis and has been moved "
            f"to {strength:+.0f}. The curves above put LR = {dhi_core.R_SINGLE_CHANNEL:.0f} at "
            f"{_s_hi:+.0f}, which is as much as one channel may claim, so the old reading "
            f"asserted evidence the update does not carry. A stronger claim is made in the two "
            f"populations: drawn further apart, the same reading buys more."
        )

    if _bounded:
        st.caption(
            f"The axis ends at LR = {dhi_core.R_SINGLE_CHANNEL:.0f} : 1 either way, {_s_lo:+.0f} to "
            f"{_s_hi:+.0f} on the curves above. That is Simm's ceiling for a single line of "
            "fluid-indicator evidence. A stronger claim comes from a second channel, or from two "
            "reference distributions drawn further apart.")
    _lev["strength"] = st.empty()

    with st.expander("What a measured amplitude buys: the one published likelihood ratio"):
        st.markdown(
            "The only published numbers that put a measured value on this quantity are "
            "Kjønsberg, Hauge, Kolbjørnsen and Buland (2010), *Bayesian Monte Carlo method for "
            "seismic predrill prospect assessment*, Geophysics 75(5), O9–O19: the strongest "
            "anomaly bought a factor of 29 and absence at the outskirts 0.70, carrying the "
            "amplitude and the geometry together. Method: see 8.1.6."
        )

    r_strength = model.r_at(strength)
    band, band_note = dhi_core.strength_bands(r_strength)
    _elements_now = st.session_state.get("element_pos") or {}
    _p_g_prior = pos.accumulation_chance(_elements_now)

    axis = np.linspace(-160.0, 160.0, 400)
    figs = go.Figure()
    figs.add_scatter(x=axis, y=hc.pdf(axis), mode="lines", name="f(s | HC), hydrocarbon-bearing",
                     line=dict(color=POSTERIOR, width=2.5))
    figs.add_scatter(x=axis, y=no_hc.pdf(axis), mode="lines",
                     name="f(s | NoHC), non-hydrocarbon", line=dict(color=PRIOR, width=2.5))
    figs.add_scatter(x=[strength, strength], y=[0.0, max(float(hc.pdf(strength)),
                                                         float(no_hc.pdf(strength)))],
                     mode="lines", name="this prospect", line=dict(color=theme.INK, dash="dot"))
    for case, colour in ((hc, POSTERIOR), (no_hc, PRIOR)):
        figs.add_scatter(x=[strength], y=[float(case.pdf(strength))], mode="markers",
                         showlegend=False, marker=dict(color=colour, size=9))
    figs.update_layout(xaxis_title="DHI evidence index", yaxis_title="density",
                       height=340, margin=dict(t=20), legend=dict(orientation="h", y=-0.22))
    n.plot(figs, f"The DHI evidence-strength model: the two reference distributions on the "
                 f"index, read at {strength:,.0f}. The likelihood ratio is the ratio of the two "
                 f"marked heights, which is why the units on the axis do not matter.")

    # The likelihood ratio and the posterior against the index, so the reader sees the update
    # as a function rather than one number (Lars, 18 Sep 2026). Same curves, same prior.
    _lr_axis = np.array([model.r_at(float(v)) for v in axis])
    _post_axis = np.array([dhi_core.simm_update(_p_g_prior, float(v)) for v in _lr_axis])
    figr = make_subplots(rows=1, cols=3, horizontal_spacing=0.08)
    figr.add_scatter(x=axis, y=_lr_axis, mode="lines", name="LR(s) = f(s | HC) / f(s | NoHC)",
                     line=dict(color=theme.INK, width=2.2), row=1, col=1)
    figr.add_scatter(x=[strength], y=[model.r_at(strength)], mode="markers", showlegend=False,
                     marker=dict(color=POSTERIOR, size=10), row=1, col=1)
    figr.add_scatter(x=axis, y=_post_axis, mode="lines", name="P(G | s)",
                     line=dict(color=POSTERIOR, width=2.2), row=1, col=2)
    figr.add_scatter(x=[strength], y=[dhi_core.simm_update(_p_g_prior, model.r_at(strength))],
                     mode="markers", showlegend=False, marker=dict(color=POSTERIOR, size=10),
                     row=1, col=2)
    figr.add_hline(y=_p_g_prior, line=dict(color=PRIOR, width=1.5, dash="dash"), row=1, col=2)
    figr.add_annotation(x=axis[0], y=_p_g_prior, text=f"prior P(G) = {_p_g_prior:.2f}",
                        xanchor="left", yshift=9, showarrow=False,
                        font=dict(size=10, color="#4C72B0"), row=1, col=2)
    # Third panel: the update as a function of the prior, P(G | s) against P(G) from 1 % to
    # 99 %, at this prospect's index in red and at reference indices -50 to 50 in grey, labelled at the
    # curve's end (Lars, 20 Sep 2026). The 0 curve is the diagonal: neutral evidence returns
    # the prior. Same LR, same two-state update, no new quantity.
    _priors = np.linspace(0.01, 0.99, 99)
    for _ref in (-50.0, -40.0, -30.0, -20.0, -10.0, -5.0, 0.0, 5.0, 10.0, 20.0, 30.0, 40.0,
                 50.0):
        _lr_ref = model.r_at(_ref)
        _post_ref = np.array([dhi_core.simm_update(float(p), _lr_ref) for p in _priors])
        figr.add_scatter(x=_priors, y=_post_ref, mode="lines", showlegend=False,
                         line=dict(color="#b8bec7" if _ref != 0.0 else "#7d8794", width=1.2,
                                   dash="solid" if _ref != 0.0 else "dot"),
                         hovertemplate=f"index {_ref:+.0f}, LR {_lr_ref:.2f}<br>"
                                       "P(G) %{x:.2f} → %{y:.2f}<extra></extra>",
                         row=1, col=3)
        # labelled at a prior of 0.5, where the curves are furthest apart; at 1 they all meet
        figr.add_annotation(x=0.5, y=float(np.interp(0.5, _priors, _post_ref)),
                            text=f"{_ref:+.0f}", xanchor="left", xshift=4, showarrow=False,
                            font=dict(size=9, color="#7d8794"), row=1, col=3)
    _lr_now = model.r_at(strength)
    figr.add_scatter(x=_priors, y=[dhi_core.simm_update(float(p), _lr_now) for p in _priors],
                     mode="lines", name=f"P(G | s) at this index, {strength:+.0f}",
                     line=dict(color=POSTERIOR, width=2.2), row=1, col=3)
    figr.add_scatter(x=[_p_g_prior], y=[dhi_core.simm_update(_p_g_prior, _lr_now)],
                     mode="markers", showlegend=False, marker=dict(color=POSTERIOR, size=10),
                     row=1, col=3)
    figr.update_xaxes(title_text="DHI evidence index", range=[-60, 60], row=1, col=1)
    figr.update_xaxes(title_text="DHI evidence index", range=[-60, 60], row=1, col=2)
    figr.update_xaxes(title_text="prior P(G)", range=[0, 1], dtick=0.1, row=1, col=3)
    figr.update_yaxes(title_text="likelihood ratio", type="log", row=1, col=1)
    figr.update_yaxes(title_text="P(G | DHI)", range=[0, 1], row=1, col=2)
    figr.update_yaxes(title_text="P(G | DHI)", range=[0, 1], dtick=0.1, row=1, col=3)
    figr.update_layout(height=340, margin=dict(t=20, b=40),
                       legend=dict(orientation="h", y=-0.28))
    n.plot(figr, f"Left: the likelihood ratio against the index, capped at "
                 f"{dhi_core.R_SINGLE_CHANNEL:.0f} : 1 either way. Middle: the posterior "
                 f"P(G | s) it gives against the prior P(G) = {_p_g_prior:.2f} from tab 2.0. "
                 f"Right: the same update as a function of the prior, from 1 % to 99 %, at this "
                 f"prospect's index in red and at indices −50 to 50 in grey (every 10, and ±5); "
                 f"the 0 line is the diagonal, neutral evidence returning the prior. The dots are "
                 f"this prospect. The model weights evidence about hydrocarbon presence; it says "
                 f"nothing about the depth of the contact, which §3 carries. Method: see 8.1.4.")

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
    s1.metric("f(s | HC)", f"{_l_hc:.3f}", "if hydrocarbons", delta_color="off")
    s2.metric("f(s | NoHC)", f"{_l_no:.3f}", "if not", delta_color="off")
    s3.metric("Likelihood ratio LR(s)", f"{r_strength:.2f}", band, delta_color="off")
    s4.metric("DHI volume weight", f"{dhi_core.volume_weight(r_strength):.3f}",
              "LR / (LR + 1)", delta_color="off")
    st.caption(
        f"The first two are the two dots in Figure {n.stem}.2a, scaled by the curves' shared "
        f"peak so they can be compared: how typical an index of {strength:,.0f} is for a "
        f"hydrocarbon-bearing outcome, and for a non-hydrocarbon one. Their ratio is the "
        f"likelihood ratio exactly ({_l_hc:.3f} / {_l_no:.3f} = {r_strength:.2f}). Densities, "
        f"not probabilities; only the ratio survives the relative axis. Method: see 8.1.4."
    )
    # Worked from OPENING_STRENGTH rather than typed. The caption below used to quote a
    # default of 7 and the 37.5 % that follows from it; the slider moved to 5 on 6 Sep and
    # the prose did not. Same defect as the pooled curve's label, found by the same sweep.
    _opening_r = dhi_core.StrengthModel().r_at(OPENING_STRENGTH)
    _opening_shift = dhi_core.simm_update(0.30, _opening_r)
    st.caption(
        f"{band}: {band_note} At the opening reading of {OPENING_STRENGTH:.0f} the band is "
        f"{dhi_core.strength_bands(_opening_r)[0]}, and a 30 % prior becomes "
        f"{_opening_shift:.1%}. The volume weight `R / (R + 1)` is not a POS. Method: see 8.1.4."
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

    theme.heading(TAB, sub=n.sub, text="3 · Contact attribution: updates HCWC | G")
    st.markdown(
        "The second channel. A flat event can be lithology, a diagenetic front, fizz gas read "
        "as pay, or a processing artefact; this section states the chance that it is none of "
        "those, given a column here. With the pick (§1) and the detection model (3b) it "
        "reweights the HCWC distribution within G. Method: see 8.1.5."
    )
    picked_levels = {}
    with st.expander("Grade the three contact attributes, for a suggested value of c"):
        st.markdown(
            "Contact attributes bear on whether the picked event is the base of the column; "
            "body attributes, graded in §2, on whether there is hydrocarbon (Monigle et al. "
            "2025). Method: see 8.1.5."
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
            f"value down. A heuristic, not a calibration. Method: see 8.1.5."
        )

    # Three routes to c (Lars, 17 Sep 2026): stated on the slider; the graded attributes'
    # geometric mean, a heuristic; or a DHI score in Monigle et al.'s (2025) sense through their
    # calibrated rule w = min(2 x score, 0.95), the one external referent this quantity has. The
    # radio replaced a checkbox keyed `dhi_in_c_from_attributes`; a prospect saved with that
    # checkbox on opens on the attributes route, so the file keeps its meaning.
    if "dhi_in_c_source" not in st.session_state and \
            st.session_state.get("dhi_in_c_from_attributes") is True:
        st.session_state["dhi_in_c_source"] = C_FROM_ATTRIBUTES
    c_source = st.radio(
        "Source of c", [C_STATED, C_FROM_ATTRIBUTES, C_FROM_SCORE], horizontal=True,
        key="dhi_in_c_source",
        help="Stated: the slider, a value the assessor defends. Graded attributes: the geometric "
             "mean of the three gradings above, a heuristic. DHI score: Monigle et al.'s (2025) "
             "rule w = min(2 × score, 0.95), calibrated on their drilled database and not on "
             "this basin; their score is a five-attribute rating, not the evidence index of "
             "§2.")
    stated_c = st.slider(
        "Contact attribution: given hydrocarbons, is the picked event the HCWC?",
        0.05, 1.0, DEFAULT_CONTACT_GIVEN_HC, 0.01, key="dhi_in_contact_given_hc",
        disabled=c_source != C_STATED,
        help="P(the picked event is the contact | hydrocarbon present). A question about the "
             "event, not the amplitude and not the charge: granted a column here, is this flat "
             "thing its base rather than lithology, a diagenetic front, fizz, or an artefact. "
             "Conformance, flatness and whether it cuts structure answer it.")
    sc1, sc2 = st.columns([1, 2])
    dhi_score = sc1.number_input(
        "DHI score (Monigle et al. 2025), 0 to 1", 0.0, 1.0, DEFAULT_DHI_SCORE, 0.01,
        key="dhi_in_dhi_score", disabled=c_source != C_FROM_SCORE,
        help="A chance of success from the seismic alone, as their five-attribute score rates "
             "it. Opens at 0.18, the score whose rule gives the shipped c of 0.36.")
    score_c = dhi_core.contact_weight_from_score(dhi_score)
    sc2.caption(
        f"Monigle et al.'s rule gives c = {score_c:.2f} from a score of {dhi_score:.2f}: "
        f"w = min(2 × score, {dhi_core.CONTACT_WEIGHT_CEILING:.2f}), calibrated on 400+ drilled "
        f"DHI prospects in their database. The rule is theirs and the basin is not; a score "
        f"above 0.475 reaches the ceiling. Method: see 8.1.5."
    )
    _lev["c"] = st.empty()
    contact_given_hc = {C_STATED: stated_c, C_FROM_ATTRIBUTES: suggested_c,
                        C_FROM_SCORE: score_c}[c_source]
    p_valid = float(np.clip(contact_given_hc, 0.01, 0.99))

    pv1, pv2 = st.columns([1, 2])
    pv1.metric("p_valid", f"{p_valid:.2f}", f"floor {1 - p_valid:.2f}", delta_color="off")
    pv2.caption(
        f"The remaining {1 - p_valid:.2f} goes to a branch in which the pick says nothing about "
        f"depth, so the depth channel can say at most {p_valid / (1 - p_valid):.1f} : 1 against "
        f"any contact depth. It does not carry the chance of hydrocarbons, which enters once, "
        f"in §5. Method: see 8.1.5."
    )

    st.caption(
        "Anchors for the slider. These are judgements, not measurements, and the spacing "
        "matters more than the exact value.\n\n"
        "- 0.9 and up: a flat, conformable event that cuts dipping structure, with a clear "
        "fluid contact reflection. 0.95 is the calibrated ceiling on the contact weight (Hood "
        "2019; Monigle et al. 2025).\n"
        "- 0.6 to 0.8: conformable and plausibly a contact, with something missing: no FCR, or "
        "terminations that are not sharp.\n"
        "- 0.3 to 0.5: the event is there and flat, and so is a plausible lithological "
        "explanation. The shipped default of 0.36 sits here; a well-conformed event is "
        "claimed by moving the slider rather than by leaving it.\n"
        "- Below 0.2: the event would not have been picked on a less interesting prospect. "
        "Whether there is a DHI at all is the question at this level."
    )

    # ------------------------------------------------------------------ the two judgements, together
    # The R-c plane returns without the surface it lost on 14 Sep 2026 (Lars, 17 Sep 2026).
    # Nothing in the arithmetic joins R and c, so nothing here is shaded by a product of them;
    # what is drawn is where the two judgements sit against each other. Simm's bands on R, the
    # slider's anchors on c, a diagonal band for the pairing body and contact attributes usually
    # make, since both improve with impedance contrast (Monigle et al. 2025), and the two
    # off-diagonal corners, which are real prospects worth a sentence. The band and the corners
    # are judgement, not calibration; the corner thresholds are the ones the tab flagged on
    # 9 Sep. Beside the plane, the three contact attributes as ladders with the graded level
    # filled, so the reader sees what c rests on. R is the other axis and never proposes c.
    _MUTED_INK = "#7d8794"
    _lr = float(np.log10(max(r_strength, 1.0 / dhi_core.R_SINGLE_CHANNEL)))
    _lr_lo, _lr_hi = -1.0, 1.0
    figc = make_subplots(rows=1, cols=2, column_widths=[0.3, 0.7], shared_yaxes=True,
                         horizontal_spacing=0.03)

    # -- left: the ladders. One column per attribute, levels at their scores. ----------------
    for k, (attribute, levels) in enumerate(CONTACT_ATTRIBUTES.items()):
        chosen = picked_levels[attribute]
        figc.add_scatter(
            x=[k] * len(levels), y=list(levels.values()), mode="markers",
            marker=dict(color="white", size=9, line=dict(color=theme.INK, width=1.2)),
            text=list(levels), hovertemplate=f"{attribute}<br>%{{text}}<br>%{{y:.2f}}"
                                              "<extra></extra>",
            showlegend=False, row=1, col=1)
        figc.add_scatter(
            x=[k], y=[levels[chosen]], mode="markers", marker=dict(color=POSTERIOR, size=12),
            hovertemplate=f"{attribute}<br>{chosen}<br>{levels[chosen]:.2f}<extra></extra>",
            showlegend=False, row=1, col=1)
        figc.add_scatter(x=[k, k], y=[0.05, 1.0], mode="lines",
                         line=dict(color="#d7dbe0", width=1), showlegend=False,
                         hoverinfo="skip", row=1, col=1)
    figc.add_scatter(x=[-0.5, 2.5], y=[suggested_c, suggested_c], mode="lines",
                     name=f"suggested c = {suggested_c:.2f}, geometric mean",
                     line=dict(color=POSTERIOR, width=1.5, dash="dash"), row=1, col=1)
    figc.update_xaxes(tickvals=[0, 1, 2], ticktext=["fit to<br>structure", "termin-<br>ations",
                                                     "fluid contact<br>reflection"],
                      range=[-0.5, 2.9], showgrid=False, row=1, col=1)

    # -- both panels: the slider's anchors as continuous bands on c, green to red -------------
    # Edges halfway between the anchor ranges (0.9 and up; 0.6 to 0.8; 0.3 to 0.5; below 0.2),
    # dusty so the markers and the band read on top of them (Lars, 17 Sep 2026).
    for y0, y1, fill, label in ((0.85, 1.0, "#DCE9D5", "flat, conformable, cuts structure, FCR"),
                                (0.55, 0.85, "#EDEFD0", "conformable, something missing"),
                                (0.25, 0.55, "#F5E2CB", "flat, and lithology plausible"),
                                (0.05, 0.25, "#F2D5D0", "would not be picked elsewhere")):
        for col, x0, x1 in ((1, -0.5, 2.9), (2, _lr_lo, _lr_hi)):
            figc.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, row=1, col=col,
                           fillcolor=fill, line=dict(width=0), layer="below")
        figc.add_annotation(x=_lr_hi, y=y1 - 0.03, text=label, xanchor="right",
                            showarrow=False, font=dict(size=9.5, color=_MUTED_INK),
                            row=1, col=2)

    # the calibrated ceiling on the contact weight: Hood's high-COV case (2019) and Monigle et
    # al.'s (2025) empirical rule both stop at 0.95, on the same company's drilled database
    for col, x0, x1 in ((1, -0.5, 2.9), (2, _lr_lo, _lr_hi)):
        figc.add_shape(type="line", x0=x0, x1=x1, y0=0.95, y1=0.95, row=1, col=col,
                       line=dict(color="#2F6B3F", width=1.2, dash="dashdot"))
    figc.add_annotation(x=_lr_lo + 0.02, y=0.95, yshift=-9, xanchor="left",
                        text="0.95: calibrated ceiling (Hood 2019; Monigle et al. 2025)",
                        showarrow=False, font=dict(size=9.5, color="#2F6B3F"), row=1, col=2)

    # -- right: the plane. Simm's bands on R. --------------------------------------------------
    for edge in (1 / 3, 1 / 1.5, 1.5, 3):
        figc.add_shape(type="line", x0=np.log10(edge), x1=np.log10(edge), y0=0.05, y1=1.0,
                       line=dict(color="#c9ced6", width=1, dash="dot"), row=1, col=2)
    for x0, x1, name in ((1 / 10, 1 / 3, "strong ↓"), (1 / 3, 1 / 1.5, "moderate ↓"),
                         (1 / 1.5, 1.5, "negligible"), (1.5, 3, "moderate ↑"),
                         (3, 10, "strong ↑")):
        figc.add_annotation(x=(np.log10(x0) + np.log10(x1)) / 2, y=1.0, yshift=10, text=name,
                            showarrow=False, font=dict(size=9.5, color=_MUTED_INK),
                            row=1, col=2)

    # the usual pairing: a band along the diagonal, +/- 0.15 in c around a line through
    # (R = 0.1, c = 0.10), (1, 0.40), (10, 0.70), so the shipped case (R 1.27, c 0.36) sits
    # mid-band and c above 0.85 is usual only near the cap. A heuristic, drawn so it can be
    # argued with; the first draft ran through (1, 0.55) and read as kind to high c.
    def _band(x, edge=0.0):
        return np.clip(0.40 + 0.30 * np.asarray(x, dtype=float) + edge, 0.05, 1.0)

    _xs = np.linspace(_lr_lo, _lr_hi, 40)
    figc.add_scatter(x=np.concatenate([_xs, _xs[::-1]]),
                     y=np.concatenate([_band(_xs, 0.15), _band(_xs, -0.15)[::-1]]),
                     fill="toself", fillcolor="rgba(76, 114, 176, 0.16)",
                     line=dict(width=0), name="the usual pairing (heuristic)",
                     hoverinfo="skip", row=1, col=2)
    # the two corners the tab flags are the band's complement beyond R = 1.5 either way:
    # bright body with an unconvincing event below it, dim body with a convincing one above.
    # Both real, both worth a sentence in the report.
    _xb = np.linspace(np.log10(1.5), _lr_hi, 20)
    _xd = np.linspace(_lr_lo, np.log10(1 / 1.5), 20)
    for xs, ys, label, lx, ly in (
            (np.concatenate([_xb, _xb[::-1]]),
             np.concatenate([np.full_like(_xb, 0.05), _band(_xb, -0.15)[::-1]]),
             "bright body,<br>unconvincing event", 0.62, 0.12),
            (np.concatenate([_xd, _xd[::-1]]),
             np.concatenate([_band(_xd, 0.15), np.full_like(_xd, 1.0)]),
             "dim body,<br>convincing event", -0.62, 0.62)):
        figc.add_scatter(x=xs, y=ys, mode="lines", line=dict(color=_MUTED_INK, width=1,
                                                             dash="dot"),
                         showlegend=False, hoverinfo="skip", row=1, col=2)
        figc.add_annotation(x=lx, y=ly, text=label, showarrow=False,
                            font=dict(size=10, color=theme.INK), row=1, col=2)

    for other_c, symbol, name in ((suggested_c, "diamond-open", "the attributes' suggestion"),
                                  (score_c, "square-open", "Monigle et al.'s rule")):
        if abs(other_c - contact_given_hc) > 0.005:
            figc.add_scatter(x=[_lr], y=[other_c], mode="markers",
                             marker=dict(color=POSTERIOR, size=11, symbol=symbol,
                                         line=dict(width=1.5)),
                             name=f"{name}, c = {other_c:.2f}",
                             hovertemplate=f"R {r_strength:.2f}<br>c {other_c:.2f}<extra></extra>",
                             row=1, col=2)
    figc.add_scatter(x=[_lr], y=[contact_given_hc], mode="markers+text",
                     marker=dict(color=POSTERIOR, size=15, symbol="diamond",
                                 line=dict(color="white", width=2)),
                     text=["  this prospect"], textposition="middle right",
                     textfont=dict(size=11, color=POSTERIOR), name="this prospect",
                     hovertemplate=f"R {r_strength:.2f}<br>c {contact_given_hc:.2f}<extra></extra>",
                     row=1, col=2)
    _ticks = [0.1, 0.2, 0.5, 1, 2, 5, 10]
    figc.update_xaxes(title_text="LR from the evidence index (§2), log scale",
                      tickvals=[np.log10(v) for v in _ticks], ticktext=[str(v) for v in _ticks],
                      range=[_lr_lo - 0.04, _lr_hi + 0.04], showgrid=False, row=1, col=2)
    figc.update_yaxes(title_text="c, contact attribution", range=[0.05, 1.0], row=1, col=1)
    figc.update_yaxes(range=[0.05, 1.0], row=1, col=2)
    figc.update_layout(height=470, margin=dict(t=36, b=10, l=10, r=10),
                       legend=dict(orientation="h", y=-0.16, x=0))
    n.plot(figc,
           f"The two judgements against each other. Left: the three contact attributes, each "
           f"level at its score, the graded one filled ("
           + ", ".join(lv.lower() for lv in picked_levels.values())
           + f"); the dashed line is their geometric mean, c = {suggested_c:.2f}. Right: R from §2 on Simm's bands against c on the "
           f"slider's anchors, this prospect at R = {r_strength:.2f}, c = {contact_given_hc:.2f}. "
           f"The shaded diagonal is the pairing the two judgements usually make: conformance "
           f"to structure and a fluid-contact reflection are also the characteristics most "
           f"predictive of finding hydrocarbons (Roden et al. 2012; Nixon et al. 2018), so an "
           f"event that earns a high c usually earns a higher evidence index in §2 too. The "
           f"dotted corners, outside the band beyond R = 1.5 either way, are the pairings worth "
           f"a sentence. The colour bands are the slider's anchors, in both panels; the "
           f"dash-dot line is the calibrated ceiling on the contact weight. The split of "
           f"Monigle et al.'s (2025) five attributes into body and contact is this tool's "
           f"reading. Nothing in the arithmetic joins the two axes: R does not propose c, and "
           f"the band is a judgement, not a calibration. Method: see 8.1.5 and 8.1.6.")
    if r_strength >= 1.5 and contact_given_hc < float(_band(_lr, -0.15)):
        st.caption(
            f"Bright body, unconvincing event: the evidence index argues for hydrocarbons "
            f"(R = {r_strength:.2f}) while the event is graded at c = {contact_given_hc:.2f}. "
            f"A real and common pairing, an anomaly believed in and bounded by something that "
            f"is not. The chance moves; the contact stays near where the geology put it. Simm "
            f"(2020) grades an anomaly without characteristics consistent with the trap and "
            f"indicative of a fluid contact as a low-grade DHI that generally warrants no "
            f"uplift, so an LR above 1.5 here rests on the evidence index alone and is worth "
            f"stating as such."
        )
    elif r_strength <= 1 / 1.5 and contact_given_hc > float(_band(_lr, 0.15)):
        st.caption(
            f"Dim body, convincing event: the evidence index argues against hydrocarbons "
            f"(R = {r_strength:.2f}) while the event is graded at c = {contact_given_hc:.2f}. "
            f"Also real: a conformable flat spot on a low-contrast reservoir is a good contact "
            f"indicator with an unremarkable amplitude. The contact sharpens; the chance falls."
        )

    # ------------------------------------------------------------------ combining
    theme.subsection(TAB, "Detection model D(h)")
    st.markdown(
        "The chance a column of height h produces a detectable anomaly. It is what makes an "
        "absent anomaly usable evidence; the false-positive assumption sets how much absence "
        "says about the chance. Method: see 8.1.5."
    )
    d1, d2, d3, d4 = st.columns(4)
    h50 = d1.number_input("50 % detection column (m)", 1.0, 500.0, defaults.DETECTION_H50_M, 1.0,
                          help="Roughly the tuning thickness for this reservoir and frequency.")
    steep = d2.number_input(
        "Transition width (m)", 1.0, 200.0, defaults.DETECTION_WIDTH_M, 1.0,
        help="How sharply detection turns on. Small means a clean threshold at the column above; "
             "large means a gradual rise, which is the safer assumption when the reservoir "
             "properties vary across the closure.")
    ceiling = d3.number_input("Ceiling", 0.05, 1.0, defaults.DETECTION_CEILING, 0.01,
                              help="Below 1 on purpose. A thick column can still fail to show, and "
                                   "a function reaching certainty would make an absent anomaly "
                                   "infinitely strong evidence.")
    false_positive = d4.number_input(
        "False-positive assumption (barren trap shows, relative)", 0.0, 1.0,
        defaults.DETECTION_FALSE_POSITIVE, 0.05,
        key="dhi_in_false_positive",
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
                 "choice, exposed rather than hard-coded. Method: see 8.1.5.")

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
        with _well_slot:
            theme.subsection(TAB, "Well control")
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
    element_product = pos.accumulation_chance(element_pos)
    r_applied = dhi_core.applied_ratio(result, detection, observation, r_strength)
    st.session_state["dhi_r_applied"] = float(r_applied)
    p_g_updated = dhi_core.p_g_given_strength(element_product, r_applied)
    geometric_prior = post.pos(posterior=False)
    posterior_geometric = post.pos()
    prior_pos = element_product * geometric_prior
    posterior_pos = dhi_core.prospect_pos(element_product, r_applied, post)

    with _glance:
        _p50_before = float(post.percentiles(50.0, posterior=False)[0])
        _p50_after = float(post.percentiles(50.0)[0])
        _sp_before = float(np.diff(post.percentiles(np.array([90.0, 10.0]), posterior=False))[0])
        _sp_after = float(np.diff(post.percentiles(np.array([90.0, 10.0])))[0])
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("P(G)", f"{p_g_updated:.0%}", f"from {element_product:.0%}", delta_color="off")
        g2.metric("HCWC P50", f"{_p50_after:,.0f} m", f"from {_p50_before:,.0f} m",
                  delta_color="off")
        g3.metric("P90–P10", f"{_sp_after:,.0f} m", f"from {_sp_before:,.0f} m",
                  delta_color="off")
        g4.metric("Effective sample size", f"{post.effective_sample_size:,.0f}",
                  f"from {result.n:,}", delta_color="off")
        st.caption(
            "The update at a glance: the evidence index moved P(G); the geometry channel moved "
            "the contact and its spread; the effective sample size says how many realisations "
            "carry the answer. Contact percentiles are conditional on the assessment minimum."
        )

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
    theme.heading(TAB, sub=n.sub, text="4 · The HCWC distribution, updated")
    st.markdown(
        "The posterior is the same weighted geological sample. The histogram shows every "
        "realisation given G; the reported contact percentiles are conditional on the "
        "assessment minimum. Exceedance convention: P90 is the shallow end."
    )
    c1, c2, c3 = st.columns(3)
    for _col, _p in ((c1, 90), (c2, 50), (c3, 10)):
        _col.metric(f"Contact P{_p}", f"{post.percentiles(float(_p))[0]:,.0f} m",
                    f"geological {post.percentiles(float(_p), posterior=False)[0]:,.0f} m",
                    delta_color="off")
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
    # The outcomes of 8.1.6: where the contact turns out to lie relative to the indicated
    # contact band (the P99 to P1 of the pick) names what the DHI was. Read off the posterior
    # and the two branches of the likelihood; nothing new is computed (Lars, 21 Sep 2026).
    _outcomes = dhi_core.outcome_shares(post, p_g_updated)
    if _outcomes is not None:
        _top, _base = _outcomes.band_m
        _z_lo, _z_hi = float(result.contact_m.min()), float(result.contact_m.max())
        _sh = _outcomes.shares
        # The labels sit at the band edges, where the bars are short, not at the band's
        # centre, where the widest bar is. Placed as annotations anchored to the edge depth
        # because the axis is reversed and a rectangle's own label lands on the wrong side.
        _fills = ((_z_lo, _top, dhi_core.OUTCOME_ABOVE, _sh[dhi_core.OUTCOME_ABOVE],
                   "rgba(140,183,252,0.10)", _top, "bottom"),
                  (_top, _base, "at the indicated contact",
                   _sh[dhi_core.OUTCOME_AT_BY_DHI] + _sh[dhi_core.OUTCOME_AT_BY_CHANCE],
                   "rgba(196,78,82,0.10)", _top, "top"),
                  (_base, _z_hi, dhi_core.OUTCOME_BELOW, _sh[dhi_core.OUTCOME_BELOW],
                   "rgba(140,183,252,0.10)", _base, "top"))
        for _y0, _y1, _name, _share, _fill, _y_label, _anchor in _fills:
            if _y1 <= _y0:
                continue
            figh.add_hrect(y0=_y0, y1=_y1, fillcolor=_fill, line_width=0, layer="below")
            figh.add_annotation(xref="paper", x=0.99, xanchor="right", y=_y_label,
                                yanchor=_anchor, showarrow=False, font_size=10,
                                font_color="#1c2128", bgcolor="rgba(255,255,255,0.85)",
                                text=f"{_name} · {_share:.0%}")
    figh.update_layout(barmode="overlay", bargap=0.04, xaxis_title="Share of realisations per depth bin",
                       xaxis_tickformat=".0%", yaxis_title="Contact depth (m TVDSS)",
                       yaxis=dict(autorange="reversed"), height=420, margin=dict(t=20),
                       legend=dict(orientation="h", y=-0.18))
    n.plot(figh, "Where the contact is, before and after the pick. Both histograms are over "
                 "every realisation and conditional on the elements having worked; the lines are "
                 "the posterior percentiles over the realisations above the assessment minimum. "
                 "The amplitude character does not enter this figure: it updates the chance of "
                 "hydrocarbons, not where the contact is given that there are."
                 + (f" The shaded intervals are the outcomes of 8.1.6 relative to the indicated "
                    f"contact band, {_top:,.0f} to {_base:,.0f} m (the P99 to P1 of the pick); "
                    f"each carries its chance as a share of all outcomes, hydrocarbons or not."
                    if _outcomes is not None else ""))

    if _outcomes is not None:
        theme.subsection(TAB, "What the DHI can turn out to have been")
        _order = list(dhi_core.OUTCOMES)
        _bar_colours = {dhi_core.OUTCOME_NO_HC: "#B8BEC7",
                        dhi_core.OUTCOME_ABOVE: "#8CB7FC",
                        dhi_core.OUTCOME_AT_BY_DHI: POSTERIOR,
                        dhi_core.OUTCOME_AT_BY_CHANCE: "#E4A3A5",
                        dhi_core.OUTCOME_BELOW: "#4C72B0"}
        figo = go.Figure()
        for _name in _order:
            figo.add_bar(x=[_sh[_name]], y=["outcomes"], orientation="h", name=_name,
                         marker_color=_bar_colours[_name], marker_line_width=0,
                         text=f"{_sh[_name]:.0%}", textposition="inside",
                         insidetextanchor="middle", textfont=dict(size=11),
                         hovertemplate=f"{_name}<br>%{{x:.1%}}<extra></extra>")
        figo.add_vline(x=_sh[dhi_core.OUTCOME_NO_HC], line=dict(color="#333", width=1.2))
        figo.add_annotation(x=_sh[dhi_core.OUTCOME_NO_HC], y=1.0, yref="paper", yanchor="bottom",
                            xanchor="left", showarrow=False, font_size=10,
                            text=f"  hydrocarbons in the trap, P(G | s) = {p_g_updated:.0%}")
        figo.update_layout(barmode="stack", height=170, margin=dict(t=36, b=30, l=10, r=10),
                           xaxis=dict(range=[0, 1], tickformat=".0%", title=None),
                           yaxis=dict(showticklabels=False),
                           legend=dict(orientation="h", y=-0.5, x=0, font_size=10,
                                       traceorder="normal"))
        n.plot(figo, f"The outcomes of a seen DHI, in depth order, as shares of all outcomes. "
                     f"The first is off the depth axis: no hydrocarbons, the DHI a false "
                     f"hydrocarbon indicator, {_sh[dhi_core.OUTCOME_NO_HC]:.0%}. The four others "
                     f"share P(G | s) = {p_g_updated:.0%}: the contact above the indicated "
                     f"contact band, within it because the DHI is the contact, within it by "
                     f"coincidence, and below it. A well at the crest finds hydrocarbons in "
                     f"the four; a well at the top of the band in the last three; a well below "
                     f"the band in the last alone. Method: see 8.1.6.")

        _rows = {
            dhi_core.OUTCOME_NO_HC: ("—", "a false hydrocarbon indicator",
                                     "water at every depth"),
            dhi_core.OUTCOME_ABOVE: (f"shallower than {_top:,.0f} m",
                                     "not the contact; the response lies in the water leg",
                                     "hydrocarbons whenever they are present"),
            dhi_core.OUTCOME_AT_BY_DHI: (f"{_top:,.0f} to {_base:,.0f} m, the DHI being its base",
                                         "the contact",
                                         "hydrocarbons where the contact is at or below the well"),
            dhi_core.OUTCOME_AT_BY_CHANCE: (f"{_top:,.0f} to {_base:,.0f} m, the geology having "
                                            f"put it there", "not the contact",
                                            "the same for the well; not for the look-back"),
            dhi_core.OUTCOME_BELOW: (f"deeper than {_base:,.0f} m",
                                     "not the contact; the response lies inside the column, "
                                     "possibly a gas–oil contact",
                                     "hydrocarbons where the contact is below the well"),
        }
        n.table(pd.DataFrame([{"Outcome": _name, "Chance": f"{_sh[_name]:.1%}",
                               "The contact is": _rows[_name][0],
                               "The DHI was": _rows[_name][1],
                               "A well entering there finds": _rows[_name][2]}
                              for _name in _order]),
                f"The outcomes with their chances, summing to one. The two rows within the band "
                f"are separated by the branch of the likelihood that put the contact there: "
                f"the posterior attribution, the chance the DHI is the contact given the "
                f"geology as well, is {_outcomes.attribution:.2f} against the stated "
                f"c = {p_valid:.2f}. A well finding the contact within the band confirms the "
                f"DHI in that proportion. Method: see 8.1.6.")

    # ------------------------------------------------------------------ 5 · the chance
    theme.heading(TAB, sub=n.sub, text="5 · Prospect POS, updated")
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Prospect POS at h ≥ {h_min:.0f} m", f"{posterior_pos:.1%}",
              f"prior {prior_pos:.1%}")
    m2.metric("P(G | s)", f"{p_g_updated:.1%}",
              f"P(G) {element_product:.1%} from tab 2.0", delta_color="off")
    m3.metric(f"P(column ≥ {h_min:.0f} m | G, pick)", f"{posterior_geometric:.1%}",
              f"geological {geometric_prior:.1%}", delta_color="off")

    st.caption(
        f"`P(G | s)` = {element_product:.3f} updated by the evidence index, LR = {r_applied:.2f}, gives "
        f"{p_g_updated:.3f} (§2). `P(column ≥ h_min | G, pick)` = {posterior_geometric:.3f}, "
        f"against {geometric_prior:.3f} from the geology alone (§1, §3). `Prospect POS` = "
        f"{p_g_updated:.3f} × {posterior_geometric:.3f} = {posterior_pos:.3f}. The chance and "
        f"the contact distribution below are read off the same weighted realisations. Method: "
        f"see 8.1.6."
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
        for method, dash in ((comparison.POOLED, "dash"), (comparison.SCENARIO, "dot")):
            curve = _comparison_curve(
                comparison.combination_exceedance(result, detection, observation, hs, method=method))
            if method == comparison.POOLED:
                pooled_gap = float(np.abs(np.asarray(curve) - np.asarray(updated)).max())
                # The same comparison with the detection function held flat, so the caption can
                # say how much of the gap is the floor rather than asserting a split that moves
                # with p_valid.
                _flat = dhi_core.DetectionFunction(h50_m=1e-6, steepness_m=1e-6, ceiling=1.0)
                _flat_curve = _comparison_curve(
                    comparison.combination_exceedance(result, _flat, observation, hs,
                                                    method=comparison.BAYES))
                floor_part = float(np.abs(np.asarray(curve) - np.asarray(_flat_curve)).max())
            fig.add_scatter(x=curve, y=depths, mode="lines", opacity=0.65,
                            name={comparison.POOLED: "…with the floor and D(h) dropped",
                                  comparison.SCENARIO: "…as a scenario switch (a mixture)"}[method],
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

    fig.update_layout(xaxis_title="Prospect POS  =  P(G | s) × P(column ≥ h | G, pick)",
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
    n.plot(fig, "The chance against threshold: P(G) × F(h) geological, P(G | s) × "
                "F(h | G, pick) updated. The evidence index scales the whole curve; the pick reshapes "
                "it, raising the chance near and above the indicated contact and lowering it below. "
                "The open circle is the posterior median, which lands on the pick. Method: see "
                "8.1.6."
                + _pooled_note(pooled_gap, floor_part))

    n.table(
        pd.DataFrame(rows),
        "POS and its threshold, as a pair. These are readings of the curve above rather than "
        "separate numbers, which is why a volume is taken at the same row as the chance beside "
        "it. The chance to quote is the one at the row the volume was computed at.")

    theme.subsection(TAB, "The two factors")
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
        "8.1.6."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("R, amplitude character" if seen else "R, absent anomaly", _fmt_r(r_applied),
              dhi_core.strength_bands(r_applied)[0] if seen
              else f"(1 − d) / (1 − f·d), d = {float(np.mean(detection.at(result.column_m))):.2f}",
              delta_color="off")
    c2.metric("P(G | s)" if seen else "P(G | absence)", f"{p_g_updated:.1%}",
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
        "indicated_band_m": (tuple(float(v) for v in _outcomes.band_m)
                             if _outcomes is not None else None),
        "prior_pos": float(prior_pos),
        "posterior_pos": float(posterior_pos),
        "p_g_given_amplitude": float(p_g_updated),
        "h_min": float(h_min),
    }

    # ------------------------------------------------------------------ 6 · effective sample size
    theme.heading(TAB, sub=n.sub, text="6 · Effective sample size")
    e1, e2 = st.columns([1, 2])
    e1.metric("Effective sample size", f"{post.effective_sample_size:,.0f}",
              f"of {result.n:,}", delta_color="off")
    e2.caption(
        "Kish's (Σw)² / Σw²: how many of the realisations the updated distribution rests on. "
        "A low value does not mean the interpretation is wrong; it means the answer depends "
        "heavily on it. The geometry channel only; the evidence index updates one number and discards "
        "nothing. Method: see 8.1.5."
    )
    if post.effective_sample_size < 300:
        st.warning(
            f"Effective sample size {post.effective_sample_size:,.0f}. The indicated contact sits "
            f"far out in the tail of the geological prior, so the posterior rests on very few "
            f"realisations. That is a finding about the model or the pick, not a number to "
            f"read off."
        )

    # ------------------------------------------------------------------ 7 · assumptions
    # In the open, not behind a fold. Each is labelled for what it is: an elicited judgement,
    # a heuristic, or a modelling choice. None is solved by wording.
    theme.heading(TAB, sub=n.sub, text="7 · Assumptions driving the update")
    _d_at = detection.at(result.column_m)
    _d_flat = float(_d_at.max() - _d_at.min()) < 1e-3
    st.markdown(
        "Elicited judgements and heuristics.\n\n"
        "- LR(s): the ratio of the two reference densities at the stated evidence index, "
        "capped at " + f"{dhi_core.R_SINGLE_CHANNEL:.0f}" + " : 1 either way. The index is a "
        "judgement on a relative scale; the reference densities are the tool's shipped "
        "relationship, editable, and not a calibration for this basin.\n"
        "- c: stated, or the geometric mean of three graded attributes (a heuristic), or "
        "Monigle et al.'s (2025) rule from a DHI score, calibrated on their database and not on "
        "this basin. This run: " + c_source.lower() + "."
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
        "Method: see 8.1.5 and 8.1.8."
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

        theme.heading(TAB, sub=n.sub, text="8 · What is this answer most sensitive to?")
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
                   f"each moved one at a time: the pick \u03c3 halved and doubled, the indicated contact "
                   f"by half a \u03c3, the detection parameters across the span an assessor cannot "
                   f"pin down.\n\n"
                   f"Where a typed DHI number moves the answer further than the geology does, the "
                   f"posterior is a statement about the seismic assumptions rather than about the "
                   f"prospect. Method: see 8.1.8.")
        else:
            st.info("Not enough weight spread to slice a sensitivity from this posterior.")

        theme.subsection(TAB,
                      f"Which mechanism set the contact, {theme.evidence_basis()}")
        st.markdown(
            "Among the realisations the evidence favours, which mechanisms are more frequent. "
            "It is not the DHI saying which element failed: the element chances on tab 2.0 are "
            "untouched, and the shares move only because the favoured contact depths do. "
            "Method: see 8.1.6."
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
                f"{theme.basis_tag(theme.GIVEN_DHI)} &nbsp; Share of realisations meeting the assessment minimum in "
                f"which each mechanism was the shallowest active limit, before and after the update. "
                f"A mechanism that cannot produce a contact where the amplitude was picked loses "
                f"share; one that naturally produces that contact gains it. The column reads as what "
                f"stopped the column, not as where the risk is.")

        theme.heading(TAB, sub=n.sub, text="9 · Cross-checks")
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
                    st.success("The two readings agree. They are two measurements of one "
                               "anomaly and are compared, not multiplied.")
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
        theme.heading(TAB, sub=n.sub, text="10 · What the scenario switch would have said")
        st.markdown(
            "`IF(DHI valid, DHI contact, geological contact)` is the older method; it moves the "
            "contact and not the chance. A comparison, not an alternative model: its one "
            f"parameter lives inside the likelihood in §3 at p_valid = {p_valid:.2f}. Method: "
            "see 8.1.6."
        )
        if seen:
            switched = comparison.scenario_switch(result, p_valid, contact, sigma)
            s1, s2, s3 = st.columns(3)
            for col, p in ((s1, 90), (s2, 50), (s3, 10)):
                col.metric(f"Contact P{p}, scenario switch",
                           f"{engine.weighted_percentiles(switched, None, float(p))[0]:,.0f} m",
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
    product = pos.accumulation_chance(element_pos)
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
        "indicated_band_m": None,
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

