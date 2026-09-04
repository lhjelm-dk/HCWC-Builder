"""Tab 3.0 — HCWC limiters: every mechanism that could stop the column, grouped by risk element.

The replacement for the `st.data_editor` limits table. That table forced twelve very different
mechanisms into one shape — four numeric columns whose meaning depended on a distribution named in
a neighbouring cell — and hid both calculators behind a *Source* cell nobody would think to edit.

The organising principle is now **the risk element**, matching E-POS, so an assessor works down
Charge, then Closure, then Retention, in the order they think. Each limit is one
:func:`hcwc.ui.limit_block.render` instance, and the summary at the top is built from the same
objects the sub-tabs return, so it cannot drift from them.

**The limits are data, not code** (:data:`SPECS`). Adding fault seal later, or a lateral seal, is a
row in that table plus a helper — not a new tab and not a new branch. Grant's mechanical top seal
went in that way on 4 Sep 2026, which is the claim being tested.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hcwc.core import correlate
from hcwc.core.limits import APEX, COLUMN, DEPTH, DepthDistribution, Group, Limit, LimitSet
from hcwc.ui import limit_block, theme
from hcwc.ui.numbering import Numbering
from hcwc.ui.sources import (render_charge_computed, render_empirical_computed,
                             render_mechanical_computed, render_seal_as_top_computed,
                             render_seal_computed)

TAB = 3

CORR_KEY = "limiter_correlations"
EXTRA_KEY = "limiter_extras"

#: Fallback apex when tab 2.0 has not been visited. The reference prospect's own crest.
DEFAULT_APEX = (2049.0, 2051.0)


@dataclass(frozen=True)
class LimitSpec:
    """One named mechanism and how its input block should start.

    ``below_apex`` is the default parameter span expressed as **metres of column below the apex**,
    whatever the limit's own parameterisation. For a ``DEPTH`` limit the block is handed
    ``apex + span`` instead, so a spill point opens with sensible depths rather than with numbers
    an assessor has to translate. Stating both in one place keeps them comparable.
    """
    name: str
    group: Group
    kind: str
    below_apex: tuple[float, float]
    p_active: float = 1.0
    form: str = "pert"
    help: str = ""
    #: Calculators this limit may be computed from, in the order they are offered. A tuple
    #: rather than one name because the base seal offers both its own calculator and a
    #: *same as the top seal* shortcut, and duplicating six sliders to say "the same" is
    #: how the two drift apart.
    computed: tuple[str, ...] = ()
    #: Which source the block opens on. ``None`` means *Typed*; naming a calculator opens on it,
    #: which is right only where the calculator beats anything the assessor would type.
    opens_on: str | None = None
    #: Open on arrival. Reserved for the blocks worth meeting first — the seal
    #: calculator is the piece with real physics and a published calibration, and it
    #: spent a week three clicks deep where nobody found it.
    expanded: bool = False


#: Every ``p_active`` here is Lars's, 26 Aug 2026 — not a placeholder. A limit at **0.0** is in the
#: list but never bites, which is the honest default for a mechanism this prospect does not have:
#: it stays visible and auditable rather than silently absent, and turning it on is one number.
SPECS: tuple[LimitSpec, ...] = (
    # ---- Charge -----------------------------------------------------------------------------
    LimitSpec("Charge", Group.CHARGE, COLUMN, (100.0, 400.0), 1.0, "pert",
              "The column the available charge can fill. Charge that fills past the deepest mapped "
              "depth is **not a shallow limit — it is no limit**, and that share belongs in "
              "`P(active)` rather than as a contact at the base of the structure.",
              computed=("charge",), opens_on="charge"),
    # ---- Closure ----------------------------------------------------------------------------
    LimitSpec("Closure / spill point", Group.CLOSURE, DEPTH, (300.0, 400.0), 1.0, "pert",
              "Where the closure spills. **Always active** — every prospect has a spill point, and "
              "the engine requires at least one limit that always bites."),
    LimitSpec("Fault geometry 1", Group.CLOSURE, DEPTH, (200.0, 320.0), 0.5, "pert",
              "A relay ramp or shear zone that breaches the closure geometrically. This is about "
              "*shape*, not about whether the fault seals — fault leakage is a Retention mechanism "
              "and lives on the next sub-tab, even when it is the same fault."),
    LimitSpec("Fault geometry 2", Group.CLOSURE, DEPTH, (220.0, 340.0), 0.0, "pert",
              "A second independent geometric breach. Off by default in effect — set `P(active)` "
              "to 0 or untick the limit if the structure has only one."),
    LimitSpec("Wedge geometry", Group.CLOSURE, DEPTH, (250.0, 360.0), 0.0, "pert",
              "Pinch-out, truncation or onlap that ends the closure down-dip. Geometry, so it sits "
              "in Closure rather than Reservoir; **Reservoir** in this tool is effectiveness only "
              "and never moves the contact."),
    # ---- Retention --------------------------------------------------------------------------
    LimitSpec("Fault leakage 1", Group.RETENTION, COLUMN, (130.0, 170.0), 0.25, "pert",
              "The column a fault will hold before it leaks — a *capacity*, so it is stated as a "
              "height and does not move when the apex pick moves."),
    LimitSpec("Fault leakage 2", Group.RETENTION, COLUMN, (140.0, 320.0), 0.0, "pert",
              "A second fault, or a second segment of the same one. **Off by default** — most "
              "structures are bounded by one fault worth modelling, and a second one left on "
              "quietly shortens every column. Give it a `P(active)` if this prospect has one."),
    LimitSpec("Top seal (capillary)", Group.RETENTION, COLUMN, (60.0, 250.0), 1.0, "pert",
              "The column the top seal can hold against buoyancy. Use the calculator to derive it "
              "from pore-throat radius and the density contrast rather than typing a number — "
              "`P_c` goes as `1/r`, so the spread on radius dominates everything else.",
              computed=("seal",), expanded=True, opens_on="seal"),
    LimitSpec("Base seal (capillary)", Group.RETENTION, COLUMN, (80.0, 280.0), 0.0, "pert",
              "The same physics below the reservoir, and the same calculator — or take the top "
              "seal's inputs wholesale with *Same as the top seal*, which is the honest default "
              "when one shale unit wraps the reservoir. Usually correlated with the top seal "
              "either way; see the Correlations sub-tab.",
              computed=("seal", "seal_as_top")),
    LimitSpec("Top seal (continuity)", Group.RETENTION, COLUMN, (100.0, 350.0), 0.5, "pert",
              "Not capillary failure but a hole in the seal: a sand-filled channel, an erosional "
              "window, a breaching fault tip."),
    LimitSpec("Base seal (continuity)", Group.RETENTION, COLUMN, (120.0, 380.0), 0.0, "pert",
              "The same, below."),
    LimitSpec("Preservation / tilt", Group.RETENTION, COLUMN, (150.0, 400.0), 0.2, "pert",
              "Post-charge tilting spilling part of the column, or a palaeo-contact left behind. "
              "It bites rarely, but when it does it can be severe."),
    # Grant (2020), eq. 8, added 4 Sep 2026. The mechanism the tool was missing: every other
    # Retention limit here fails because the pore throats are wide enough or because there is a hole
    # in the seal, and this one fails because the *rock parts*. The two are independent -- a shale
    # can have superb capillary properties and still sit against its fracture limit in an
    # overpressured section -- which is the case for competing them rather than choosing.
    #
    # **`P(active)` 0.0, like every other mechanism most prospects do not have.** It bites in
    # overpressured sections; at a normally pressured two kilometres the headroom is hundreds of bar
    # and so thousands of metres of column, far more than any structure holds. Off means visible and
    # auditable rather than silently absent, and turning it on is one number.
    LimitSpec("Top seal (fracture)", Group.RETENTION, COLUMN, (200.0, 500.0), 0.0, "pert",
              "The column the trap can hold before the **top seal parts in tension** — pressure at "
              "the crest reaching the minimum horizontal stress, not the pore throats letting go. "
              "Grant (2020): a pressure-release *valve* rather than a catastrophe, since the "
              "fracture closes and reseals once pressure bleeds off, so it caps a column rather "
              "than emptying a trap. **It only ever controls in overpressured sections.**",
              computed=("fracture",)),
)

#: What each element's sub-tab is for, shown under its coloured heading.
ELEMENT_BLURB: dict[Group, str] = {
    Group.CHARGE: "Is there enough hydrocarbon to fill the closure, and how far down does it reach?",
    Group.CLOSURE: "Where the trap runs out — mapped surfaces, so these are stated as depths.",
    Group.RETENTION: "What the seals and faults will hold — capacities, so these are stated as "
                     "column heights.",
}


SUB_TABS: tuple[tuple[str, Group], ...] = (
    ("Charge", Group.CHARGE),
    ("Closure", Group.CLOSURE),
    ("Retention", Group.RETENTION),
)

#: Which calculator a limit may be computed from. "empirical" is offered on every limit
#: because the censoring-corrected NCS fit is a legitimate fallback for any mechanism
#: nothing better is known about — it was reachable before the tab-3.0 rebuild and was lost
#: in it, which is the kind of regression a restructure makes easy and silent.
COMPUTED = {"charge": render_charge_computed, "seal": render_seal_computed,
            "seal_as_top": render_seal_as_top_computed,
            "fracture": render_mechanical_computed,
            "empirical": render_empirical_computed}


def _apex_distribution() -> DepthDistribution:
    p1, p99 = st.session_state.get("apex", DEFAULT_APEX)
    return DepthDistribution("normal_alt", {"p1": 0.01, "x1": p1, "p2": 0.99, "x2": p99})


def _span_for(spec: LimitSpec) -> tuple[float, float]:
    """The block's opening parameter range, in whatever space the limit is stated in."""
    lo, hi = spec.below_apex
    if spec.kind != DEPTH:
        return lo, hi
    apex = float(np.mean(st.session_state.get("apex", DEFAULT_APEX)))
    if spec.name.startswith("Closure"):
        # The spill point is the one depth limit the user has usually already mapped, so it opens
        # around the value tab 2.0 carries rather than around a generic offset.
        spill = float(st.session_state.get("spill_point", apex + hi))
        return spill - 60.0, spill + 20.0
    return apex + lo, apex + hi


def _render_group(group: Group, n_trials: int, seed: int) -> list[Limit]:
    """Every limit in one risk element, each in its own expander.

    The section carries the **element's own colour** from tab 2.0, so the same hue that labels
    Charge there labels it here. Each limit inside gets a *variation* of that hue, never the pure
    one, so the two levels do not compete.
    """
    theme.element_heading(group.value, group.value, ELEMENT_BLURB.get(group, ""))
    if group is Group.RETENTION:
        st.caption(
            "**These are *how much* the seals and faults hold, not *whether* they work.** Whether "
            "Retention works at the crest is the element chance on tab 2.0. Entering the same "
            "uncertainty in both places counts it twice — the error Beha et al. (2012) is written "
            "about, which understates POS and overstates volume. See tab 8.0 → *Beha et al. (2012)*."
        )
    built: list[Limit] = []
    specs = [s for s in SPECS if s.group is group]
    shades = theme.element_shades(group.value, max(len(specs), 1))

    for spec, colour in zip(specs, shades):
        with st.expander(f"**{spec.name}**", expanded=spec.expanded or len(specs) == 1):
            options = list(spec.computed)
            if spec.kind == COLUMN:
                options.append("empirical")
            limit = limit_block.render(
                spec.name, spec.group, key=f"lim_{spec.name}", default_kind=spec.kind,
                default_form=spec.form, span=_span_for(spec), default_p_active=spec.p_active,
                colour=colour, help_text=spec.help,
                default_source=spec.opens_on or "Typed",
                computed={name: (lambda key, fn=COMPUTED[name]: fn(key, n_trials, seed))
                          for name in options} or None)
        if limit is not None:
            built.append(limit)

    # ---- user-added limits ---------------------------------------------------------------
    extras = st.session_state.setdefault(EXTRA_KEY, {}).setdefault(group.value, [])
    for index, name in enumerate(list(extras)):
        with st.expander(f"**{name}** — added", expanded=False):
            renamed = st.text_input("Name", value=name, key=f"extra_name_{group.value}_{index}")
            if renamed != name:
                extras[index] = renamed
            if st.button("Remove this limit", key=f"extra_del_{group.value}_{index}"):
                extras.pop(index)
                st.rerun()
            limit = limit_block.render(
                renamed or name, group, key=f"extra_{group.value}_{index}",
                default_kind=COLUMN, span=(100.0, 350.0),
                colour=theme.PILLAR_COLOURS[group.value])
        if limit is not None:
            built.append(limit)

    if st.button(f"Add another {group.value.lower()} limit", key=f"add_{group.value}"):
        extras.append(f"{group.value} limit {len(extras) + 1}")
        st.rerun()

    return built


def _render_correlations(names: tuple[str, ...]) -> dict[str, float]:
    # **The apex is selectable, and until 28 Aug 2026 it was not.** The box below has always said
    # apex-to-spill is the pair most worth setting, and the engine's own refusal message advised
    # exactly that pairing -- while the matrix was built from limit names only, so neither could be
    # acted on. `LimitSet.correlated_names` owns the ordering; this owns the offer.
    choices = (APEX, *names)
    st.markdown(
        f"Pairs, not a matrix. A full matrix over {len(SPECS)} limits is "
        f"{len(SPECS) * (len(SPECS) - 1) // 2} numbers and nobody fills that "
        "in; an assessor states the couplings they believe in and the rest are zero — which is "
        "itself a modelling statement, and usually a wrong one for the seal pairs.\n\n"
        "Values are **rank** correlations, which is what an assessor means and what `RiskCorrmat` "
        "uses. They are converted to the Gaussian copula's normal-score parameter before sampling; "
        "skipping that step would quietly deliver a weaker correlation than the one asked for."
    )
    st.info(
        "**Apex ↔ a depth-stated limit is the pair most worth setting.** A spill point and the "
        "apex are picked off the *same* depth-converted surface, so a depth-conversion error moves "
        "both together. Leaving them independent is what lets a realisation put the spill above "
        "the apex — and it is the same errors-in-variables coupling that inflates the published "
        "column-height regression on tab 6.0. Correlating them is the honest default, not a "
        "refinement.\n\n"
        "**How much it is worth.** On a 120 m apex uncertainty with a mapped spill, treating the "
        "two as independent gives the derived closure height a spread of 33 m; correlating them at "
        "0.9 gives 11 m. Two thirds of that spread was manufactured by the assumption, not by the "
        "geology."
    )

    if CORR_KEY not in st.session_state:
        st.session_state[CORR_KEY] = pd.DataFrame([
            {"Limit A": "Top seal (capillary)", "Limit B": "Base seal (capillary)",
             "Rank correlation": 0.7},
            {"Limit A": "Top seal (continuity)", "Limit B": "Base seal (continuity)",
             "Rank correlation": 0.7},
        ])
    rows = st.data_editor(
        st.session_state[CORR_KEY], num_rows="dynamic", use_container_width=True,
        column_config={
            "Limit A": st.column_config.SelectboxColumn(options=list(choices), width="medium"),
            "Limit B": st.column_config.SelectboxColumn(options=list(choices), width="medium"),
            "Rank correlation": st.column_config.NumberColumn(
                min_value=-1.0, max_value=1.0, step=0.05, format="%.2f",
                help="Spearman. Top and base seal at 1.0 would be perfect dependence — a claim that "
                     "they are the same rock. Correlated, usually; identical, rarely."),
        }, key="limiter_corr_editor")
    st.session_state[CORR_KEY] = rows

    pairs: dict[str, float] = {}
    for _, row in rows.iterrows():
        a, b = str(row["Limit A"]).strip(), str(row["Limit B"]).strip()
        if not a or not b or a == b or a not in choices or b not in choices:
            continue
        try:
            pairs[f"{a}|{b}"] = float(row["Rank correlation"])
        except (TypeError, ValueError):
            continue
    return pairs


def _render_ranking(n: Numbering, limit_set: LimitSet, n_trials: int, seed: int) -> None:
    """Which of these twelve is actually setting the contact — **on the tab where you edit them**.

    Tab 1.0 calls the ranking *"the point of the whole tool"* and tells the assessor to run once, read
    it, then elicit only the top two or three. It lived on tab 4.0, so following that instruction meant
    a round trip on every refinement cycle — and people do not make round trips. They either elicit
    all of them carefully or none of them, which are the two outcomes the ranking exists to prevent.

    So it is here too, above the inputs it directs, updating as they change. Tab 4.0 §3 keeps the full
    version — the successes-only toggle, the shift table, the selection-effect argument. This is the
    workflow instrument: which rows are worth an afternoon.

    Deliberately **unrestricted** (all realisations, not successes only). The question being asked at
    elicitation time is *what controls this closure*, not *what controls it given it is worth
    drilling*; a limit that usually kills the prospect outright is exactly the one you must not leave
    rough, and the restricted view is where it disappears.
    """
    from hcwc.core import engine
    from hcwc.ui import run as engine_run
    from hcwc.ui.results_tab import limit_colours

    result = engine_run.run(limit_set.to_dict(), n_trials, seed)
    ranking = engine.limit_ranking(result)
    live = [(name, share) for name, share in ranking if share > 0.0005]
    if not live:
        return

    theme.heading(TAB, "1 · Which of these actually matters?")
    colour_of = limit_colours(limit_set)
    fig = go.Figure()
    fig.add_bar(x=[s for _, s in live][::-1], y=[nm for nm, _ in live][::-1], orientation="h",
                marker_color=[colour_of[nm] for nm, _ in live][::-1],
                hovertemplate="%{y}<br>%{x:.1%} of realisations<extra></extra>")
    fig.update_layout(xaxis_title="Share of realisations in which this limit set the contact",
                      height=max(200, 34 * len(live)), margin=dict(t=10, b=40),
                      showlegend=False, xaxis_tickformat=".0%")
    n.plot(fig,
           f"**Run first, elicit second.** The blocks below are open at their defaults; this says "
           f"which of them your afternoon should go to. **{live[0][0]}** sets the contact in "
           f"{live[0][1]:.0%} of realisations, and anything near the bottom can stay rough — it is "
           f"not moving the answer.\n\n"
           f"All realisations, not successes only: at elicitation time the question is *what "
           f"controls this closure*, and a limit that usually kills the prospect outright is the "
           f"one you least want to leave at a default. The restricted view, the shift between them "
           f"and why the difference matters are on tab 4.0 §3.")
    idle = [name for name, share in ranking if share <= 0.0005]
    if idle:
        st.caption(
            f"**Never sets the contact:** {', '.join(idle)}. Either it is genuinely always deeper "
            f"than something else — which is a finding, not a fault — or it is switched on with a "
            f"distribution that puts it below the spill point, in which case it is costing you "
            f"elicitation effort for nothing."
        )


def render() -> None:
    n = Numbering(TAB)
    st.subheader("HCWC limiters")
    st.markdown(
        "Every mechanism that could stop the column going deeper, grouped by the risk element it "
        "belongs to. Each has a chance of being present at all and — given it is — a distribution "
        "of where it bites. **In every realisation the shallowest active one wins.**\n\n"
        "Nothing is blended. Merging a leak into the background column-height distribution "
        "suppresses realisations *above* the leak, which is not geology — it can even make apparent "
        "prospect volume rise when a leak is added (Hood, 2024)."
    )

    summary_slot = st.container()

    n_trials = int(st.session_state.get("n_trials", 10_000))
    seed = int(st.session_state.get("seed", 20260825))

    # **Letters, not numbers.** Lars, 3 Sep 2026, settling the one place the `N.0` tab numbering
    # could not reach: numbering these `3.1`-`3.4` would collide head-on with `Figure 3.1` and
    # `Table 3.2`, and the whole point of the scheme is that a number names exactly one thing.
    # Letters sit outside that sequence entirely, so they can label a position without claiming one.
    # The figures and tables here go on counting straight through A, B, C, D as one sequence —
    # `Figure 3.4` is the fourth exhibit on this tab wherever it happens to sit.
    charge_tab, closure_tab, retention_tab, corr_tab = st.tabs(
        ["A · Charge", "B · Closure", "C · Retention", "D · Correlations"])
    # Names this strip so the stylesheet can colour it by risk element. It used to be picked out by
    # being four sub-tabs long, which was true until tab 5.0 grew a fourth and started wearing these
    # element colours by accident.
    for _panel in (charge_tab, closure_tab, retention_tab, corr_tab):
        with _panel:
            st.markdown(theme.subtab_marker(TAB), unsafe_allow_html=True)
    limits: list[Limit] = []
    with charge_tab:
        limits += _render_group(Group.CHARGE, n_trials, seed)
    with closure_tab:
        limits += _render_group(Group.CLOSURE, n_trials, seed)
    with retention_tab:
        limits += _render_group(Group.RETENTION, n_trials, seed)

    charge_phase = st.session_state.get("charge_phase")
    seal_fluid = st.session_state.get("seal_fluid")
    phase_clash = (charge_phase and seal_fluid
                   and charge_phase.replace("Pure ", "").lower() != seal_fluid.lower())

    if not limits:
        with summary_slot:
            st.error("**No limits are switched on**, so there is nothing to run.")
        st.session_state.pop("limit_set", None)
        return

    with corr_tab:
        pairs = _render_correlations(tuple(limit.name for limit in limits))

    try:
        limit_set = LimitSet(apex=_apex_distribution(), limits=tuple(limits),
                             name=str(st.session_state.get("prospect_name", "Prospect")),
                             min_column_m=float(st.session_state.get("min_column", 0.0)),
                             correlations=pairs)
    except ValueError as exc:
        with summary_slot:
            st.error(str(exc))
        st.session_state.pop("limit_set", None)
        return

    with corr_tab:
        if pairs:
            names = tuple(limit_set.names)
            moved = [r for r in correlate.describe(names, correlate.build_matrix(names, pairs))
                     if abs(r[2] - r[3]) > 0.01]
            if moved:
                st.warning(
                    "**Some correlations are not jointly achievable** and have been projected onto "
                    "the nearest matrix that is. Asked for, then sampled:\n\n"
                    + "\n".join(f"- {a} / {b}: **{req:+.2f}** → **{got:+.2f}**"
                                for a, b, req, got in moved))

    # The engine checks the geometry while it samples -- a depth-stated limit that lands above the
    # apex is the usual one -- and it *raises*, because there is no honest column to return. That
    # left the failure wherever the engine happened to run first, as an uncaught exception, and
    # Streamlit replaced the whole page with a traceback. One selectbox was enough to trigger it:
    # Charge is elicited in metres of column, and switching *Stated as* to m TVDSS makes 100/220/400
    # depths far above the apex.
    #
    # Checking here keeps the failure on the tab that owns the mistake, and shows the sentence the
    # engine already writes -- it names the limit, gives its P1 against the apex, and says why the
    # column is not clipped to zero. The set is published only once it is known to run, so every
    # downstream tab falls back to its existing "define the limits first" path instead of crashing.
    from hcwc.ui import run as engine_run
    try:
        engine_run.run(limit_set.to_dict(), n_trials, seed)
    except ValueError as exc:
        st.error(f"**This limit set cannot be sampled.**\n\n{exc}")
        st.session_state.pop("limit_set", None)
        return

    st.session_state["limit_set"] = limit_set

    # ---- the summary, written into the slot reserved at the top --------------------------
    with summary_slot:
        _render_ranking(n, limit_set, n_trials, seed)
        theme.heading(TAB, "2 · Summary")
        rows = []
        for limit in limit_set.limits:
            # The same twenty thousand draws the limit's own preview already made, through the same
            # cache. This line used to redraw them -- identical distribution, identical seed --
            # which made the summary table cost as much as all twelve previews put together and
            # made it the single largest remaining chunk of the rerun.
            drawn = limit_block._preview_samples(
                limit.distribution.kind, limit_block._param_key(limit.distribution.params), 20_000)
            stats = limit_block.stats_row(drawn)
            rows.append({
                "Limit": limit.name,
                "Element": limit.group.value,
                "P(active)": f"{limit.p_active:.2f}",
                "Stated as": "m TVDSS" if limit.is_depth else "m column",
                "Distribution": limit.distribution.kind,
                "P90": f"{stats['P90']:,.0f}",
                "P50": f"{stats['P50']:,.0f}",
                "P10": f"{stats['P10']:,.0f}",
            })
        n.table(pd.DataFrame(rows),
                "Every limit as entered, in its own space — so a depth-stated limit reads in "
                "m TVDSS and a capacity reads in metres of column, and neither has been silently "
                "converted for display. Percentiles are exceedance: **P90 is the shallow end.**",
                height=min(60 + 35 * len(rows), 480))
        if phase_clash:
            st.error(
                f"**Phase mismatch: the charge calculator is filling with "
                f"*{charge_phase.replace('Pure ', '').lower()}* and the seal calculator is holding "
                f"back *{seal_fluid.lower()}*.**\n\n"
                f"That is not a labelling nicety. Seal capacity is `h_max = P_c / (Δρ·g)`, so it "
                f"depends on the density contrast between the hydrocarbon and the water — the same "
                f"seal holds a much shorter gas column than an oil one. Running one phase through "
                f"the charge and the other through the seal produces a contact that belongs to no "
                f"prospect. Set both to the same fluid, or run the two phases as separate cases."
            )

        always = [x.name for x in limit_set.limits if x.always_active]
        st.caption(
            f"**{len(limit_set.limits)} limits**, of which "
            f"{len(always)} always active ({', '.join(always) if always else 'none'}). "
            f"At least one must always be active, because every prospect has a spill point — the "
            f"engine refuses a set where the column could be unbounded."
        )
