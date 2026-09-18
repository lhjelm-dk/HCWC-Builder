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
    #: An explicit PERT mode, where the 40 %-of-span default is not the one wanted.
    #: `None` leaves it derived. **Declared after `help` on purpose**: dataclass field
    #: order is the positional signature, and every spec below passes `help`
    #: positionally, so a field inserted above it silently re-binds them all.
    mode: float | None = None
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
              "depth is no limit at all; that share belongs in `P(active)`, not as a contact at "
              "the base of the structure.",
              computed=("charge",), opens_on="charge"),
    # ---- Closure ----------------------------------------------------------------------------
    LimitSpec("Closure / spill point", Group.CLOSURE, DEPTH, (300.0, 400.0), 1.0, "pert",
              "Where the closure spills. Always active: every prospect has a spill point, and the "
              "engine requires at least one limit that always applies."),
    LimitSpec("Fault geometry 1", Group.CLOSURE, DEPTH, (200.0, 320.0), 0.5, "pert",
              "A relay ramp or shear zone that breaches the closure geometrically. This concerns "
              "shape, not whether the fault seals; fault leakage is a Retention mechanism on the "
              "next sub-tab, even where it is the same fault."),
    LimitSpec("Fault geometry 2", Group.CLOSURE, DEPTH, (220.0, 340.0), 0.0, "pert",
              "A second independent geometric breach. Off in effect by default; `P(active)` at 0, "
              "or the limit unticked, where the structure has only one."),
    LimitSpec("Wedge geometry", Group.CLOSURE, DEPTH, (250.0, 360.0), 0.0, "pert",
              "Pinch-out, truncation or onlap that ends the closure down-dip. Geometry, so it sits "
              "in Closure rather than Reservoir; Reservoir in this tool is effectiveness only and "
              "never moves the contact."),
    # ---- Retention --------------------------------------------------------------------------
    LimitSpec("Fault leakage 1", Group.RETENTION, COLUMN, (130.0, 170.0), 0.25, "pert",
              "The column a fault holds before it leaks. A capacity, so it is stated as a height "
              "and does not move when the apex pick moves."),
    LimitSpec("Fault leakage 2", Group.RETENTION, COLUMN, (140.0, 320.0), 0.0, "pert",
              "A second fault, or a second segment of the same one. Off by default: most "
              "structures are bounded by one fault worth modelling, and a second left on shortens "
              "every column. It needs a `P(active)` where the prospect has one."),
    LimitSpec("Top seal (capillary)", Group.RETENTION, COLUMN, (100.0, 500.0), 1.0, "pert",
              "The column the top seal holds against buoyancy. Opens typed, at a range wide enough "
              "to admit a seal that outlives the closure. The Computed source derives it from "
              "pore-throat radius and the density contrast instead; `P_c` goes as `1/r`, and the "
              "radius carries about three quarters of the spread that calculator produces.",
              mode=250.0, computed=("seal",), expanded=True),
    LimitSpec("Base seal (capillary)", Group.RETENTION, COLUMN, (80.0, 280.0), 0.0, "pert",
              "The same physics below the reservoir, with the same calculator. Same as the top "
              "seal takes the top seal's inputs wholesale, which is the usual case where one shale "
              "unit wraps the reservoir. Usually correlated with the top seal either way; see the "
              "Correlations sub-tab.",
              computed=("seal", "seal_as_top")),
    LimitSpec("Top seal (continuity)", Group.RETENTION, COLUMN, (100.0, 350.0), 0.3, "pert",
              "Not capillary failure but a hole in the seal: a sand-filled channel, an erosional "
              "window, a breaching fault tip."),
    LimitSpec("Base seal (continuity)", Group.RETENTION, COLUMN, (120.0, 380.0), 0.0, "pert",
              "The same, below."),
    LimitSpec("Preservation / tilt", Group.RETENTION, COLUMN, (150.0, 400.0), 0.2, "pert",
              "Post-charge tilting that spills part of the column, or a palaeo-contact left "
              "behind. It applies rarely, and can be severe when it does."),
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
              "The column the trap holds before the top seal parts in tension: pressure at the "
              "crest reaching the minimum horizontal stress, rather than the pore throats letting "
              "go. Grant (2020) describes it as a pressure-release valve rather than a catastrophe, "
              "since the fracture closes and reseals once pressure bleeds off, so it caps a column "
              "rather than emptying a trap. It controls only in overpressured sections.",
              computed=("fracture",)),
)

#: What each element's sub-tab is for, shown under its coloured heading.
ELEMENT_BLURB: dict[Group, str] = {
    Group.CHARGE: "Whether the available hydrocarbon fills the closure, and how far down it reaches.",
    Group.CLOSURE: "Where the trap runs out. Mapped surfaces, so these are stated as depths.",
    Group.RETENTION: "What the seals and faults hold. Capacities, so these are stated as column "
                     "heights.",
    Group.RESERVOIR: "Where the reservoir ends: a base or pinch-out that stops the column. A "
                     "mapped surface, stated as a depth. Reservoir effectiveness with depth does "
                     "not move the contact and is entered on tab 4.2, not here.",
}


SUB_TABS: tuple[tuple[str, Group], ...] = (
    ("Charge", Group.CHARGE),
    ("Closure", Group.CLOSURE),
    ("Retention", Group.RETENTION),
    ("Reservoir", Group.RESERVOIR),
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


def _reservoir_span() -> tuple[float, float]:
    """Where an added reservoir base or pinch-out opens: inside the closure, above the spill."""
    apex = float(np.mean(st.session_state.get("apex", DEFAULT_APEX)))
    spill = float(st.session_state.get("spill_point", apex + 350.0))
    return apex + 0.5 * (spill - apex), spill


def _render_group(group: Group, n_trials: int, seed: int,
                  share_slots: dict[str, object] | None = None) -> list[Limit]:
    """Every limit in one risk element, each in its own expander.

    The section carries the **element's own colour** from tab 2.0, so the same hue that labels
    Charge there labels it here. Each limit inside gets a *variation* of that hue, never the pure
    one, so the two levels do not compete.

    ``share_slots`` collects one placeholder per limit, drawn at the top of its block, which
    :func:`render` fills with the limit's current controlling share once the run exists. The
    ranking figure says the same thing for all limits at once; this puts each limit's number
    beside the inputs that set it, which is where the question "is this one worth eliciting"
    is asked.
    """
    theme.element_heading(group.value, group.value, ELEMENT_BLURB.get(group, ""))
    if group is Group.RETENTION:
        st.caption(
            "These are how much the seals and faults hold, not whether they work. Whether "
            "Retention works at the crest is the element chance on tab 2.0. Entering the same "
            "uncertainty in both places counts it twice, which understates POS and overstates "
            "volume (Beha et al. 2012)."
        )
    built: list[Limit] = []
    specs = [s for s in SPECS if s.group is group]
    shades = theme.element_shades(group.value, max(len(specs), 1))

    for spec, colour in zip(specs, shades):
        with st.expander(f"**{spec.name}**", expanded=spec.expanded or len(specs) == 1):
            if share_slots is not None:
                share_slots[spec.name] = st.empty()
            options = list(spec.computed)
            if spec.kind == COLUMN:
                options.append("empirical")
            limit = limit_block.render(
                spec.name, spec.group, key=f"lim_{spec.name}", default_kind=spec.kind,
                default_form=spec.form, span=_span_for(spec), default_p_active=spec.p_active,
                default_mode=spec.mode,
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
            if share_slots is not None:
                share_slots[renamed or name] = st.empty()
            # A reservoir limit is a mapped base or pinch-out, so it opens as a depth; the other
            # elements' added limits open as columns, as before.
            limit = limit_block.render(
                renamed or name, group, key=f"extra_{group.value}_{index}",
                default_kind=DEPTH if group is Group.RESERVOIR else COLUMN,
                span=(100.0, 350.0) if group is not Group.RESERVOIR else _reservoir_span(),
                colour=theme.PILLAR_COLOURS[group.value])
        if limit is not None:
            built.append(limit)

    if not specs and not extras:
        st.caption(
            "No reservoir limit is defined. The contact is then never reservoir-controlled and "
            "the Reservoir element chance from tab 2.0 applies unchanged with depth. A base or "
            "pinch-out that the column cannot pass is added below."
        )
    if st.button(f"Add another {group.value.lower()} limit"
                 if specs or extras else f"Add a {group.value.lower()} limit",
                 key=f"add_{group.value}"):
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
        f"Pairs rather than a matrix. A full matrix over {len(SPECS)} limits is "
        f"{len(SPECS) * (len(SPECS) - 1) // 2} numbers. The assessor states the couplings "
        "they hold and the rest are zero, which is itself a modelling statement, and usually "
        "a wrong one for the seal pairs.\n\n"
        "Values are rank correlations, as in `RiskCorrmat`. They are converted to the Gaussian "
        "copula's normal-score parameter before sampling; without that step the sampled "
        "correlation is weaker than the one stated."
    )
    st.info(
        "Apex to a depth-stated limit is the pair most worth setting: the spill point and the "
        "apex are picked off the same surface, and left independent a realisation can put the "
        "spill above the apex. Method: see 8.1.5."
    )
    # Audit finding P1-1, 14 Sep 2026: the presence draws are outside the copula, and the place
    # to say so is beside the control that a reader would expect to reach them.
    st.caption(
        "Correlations couple depths and capacities only. Whether a limit is present is drawn "
        "independently of everything, including the presence of every other limit. Modelling "
        "choice; a presence copula is not implemented. Method: see 8.1.5."
    )

    if CORR_KEY not in st.session_state:
        st.session_state[CORR_KEY] = pd.DataFrame([
            {"Limit A": "Top seal (capillary)", "Limit B": "Base seal (capillary)",
             "Rank correlation": 0.7},
            {"Limit A": "Top seal (continuity)", "Limit B": "Base seal (continuity)",
             "Rank correlation": 0.7},
        ])
    rows = st.data_editor(
        st.session_state[CORR_KEY], num_rows="dynamic", width="stretch",
        column_config={
            "Limit A": st.column_config.SelectboxColumn(options=list(choices), width="medium"),
            "Limit B": st.column_config.SelectboxColumn(options=list(choices), width="medium"),
            "Rank correlation": st.column_config.NumberColumn(
                min_value=-1.0, max_value=1.0, step=0.05, format="%.2f",
                help="Spearman. Top and base seal at 1.0 is perfect dependence, a claim that "
                     "they are the same rock. Usually correlated; rarely identical."),
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

    Tab 1.0 §1.3 says the elicitation effort belongs on the top two or three limits this ranking
    names. It lived on tab 4.0, so following that instruction meant
    a round trip on every refinement cycle — and people do not make round trips. They either elicit
    all of them carefully or none of them, which are the two outcomes the ranking exists to prevent.

    So it is here too, above the inputs it directs, updating as they change. Tab 4.0 §2b keeps the full
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

    theme.heading(TAB, "1 · Which limits control the contact")
    colour_of = limit_colours(limit_set)
    fig = go.Figure()
    fig.add_bar(x=[s for _, s in live][::-1], y=[nm for nm, _ in live][::-1], orientation="h",
                marker_color=[colour_of[nm] for nm, _ in live][::-1],
                hovertemplate="%{y}<br>%{x:.1%} of realisations<extra></extra>")
    fig.update_layout(xaxis_title="Share of realisations in which this limit set the contact",
                      height=max(200, 34 * len(live)), margin=dict(t=10, b=40),
                      showlegend=False, xaxis_tickformat=".0%")
    n.plot(fig,
           f"The share of realisations in which each limit set the contact, at the current "
           f"inputs. {live[0][0]} sets it in {live[0][1]:.0%} of realisations; limits near the "
           f"bottom can stay at rough values. All realisations, not only those meeting the minimum; the view "
           f"restricted to them is on tab 4.1.2 (Figure 4.1.2b). Method: see 8.1.3.")
    idle = [name for name, share in ranking if share <= 0.0005]
    if idle:
        st.caption(
            f"Never sets the contact: {', '.join(idle)}. Either it is always deeper than "
            f"something else, which is a finding, or it is switched on with a distribution that "
            f"puts it below the spill point, in which case eliciting it further has no effect."
        )


def render() -> None:
    n = Numbering(TAB)
    st.subheader("HCWC limiters")
    st.markdown(
        "Every mechanism that may stop the column going deeper, grouped by the risk element it "
        "belongs to. Each has a probability of being present and, given that it is, a "
        "distribution of the depth or capacity at which it applies. In every realisation the "
        "shallowest active limit sets the contact. Limits are sampled, not blended. Method: "
        "see 8.1.2 and 8.1.3.\n\n"
        "The ranking (3.1) and the summary (3.2) are the result and update as the inputs below "
        "change; the checks (3.3) follow them."
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
    charge_tab, closure_tab, retention_tab, reservoir_tab, corr_tab = st.tabs(
        ["A · Charge", "B · Closure", "C · Retention", "D · Reservoir", "E · Correlations"])
    # Names this strip so the stylesheet can colour it by risk element. It used to be picked out by
    # being four sub-tabs long, which was true until tab 5.0 grew a fourth and started wearing these
    # element colours by accident.
    for _panel in (charge_tab, closure_tab, retention_tab, reservoir_tab, corr_tab):
        with _panel:
            st.markdown(theme.subtab_marker(TAB), unsafe_allow_html=True)
    # One placeholder per limit, at the top of its block, filled with its controlling share once
    # the run exists. The ranking at the top of the tab says it for all limits at once; this says
    # it beside the inputs that set each one.
    share_slots: dict[str, object] = {}
    limits: list[Limit] = []
    with charge_tab:
        limits += _render_group(Group.CHARGE, n_trials, seed, share_slots)
    with closure_tab:
        limits += _render_group(Group.CLOSURE, n_trials, seed, share_slots)
    with retention_tab:
        limits += _render_group(Group.RETENTION, n_trials, seed, share_slots)
    with reservoir_tab:
        limits += _render_group(Group.RESERVOIR, n_trials, seed, share_slots)

    charge_phase = st.session_state.get("charge_phase")
    seal_fluid = st.session_state.get("seal_fluid")
    phase_clash = (charge_phase and seal_fluid
                   and charge_phase.replace("Pure ", "").lower() != seal_fluid.lower())

    if not limits:
        with summary_slot:
            st.error("No limits are switched on, so there is nothing to run.")
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
            # `correlated_names`, not `names`: the apex is a member of the correlated set and a
            # declared Apex|spill pair raised KeyError here until 14 Sep 2026.
            names = tuple(limit_set.correlated_names)
            moved = [r for r in correlate.describe(names, correlate.build_matrix(names, pairs))
                     if abs(r[2] - r[3]) > 0.01]
            if moved:
                st.warning(
                    "Some correlations are not jointly achievable and have been projected onto "
                    "the nearest matrix that is. Stated, then sampled:\n\n"
                    + "\n".join(f"- {a} / {b}: {req:+.2f} → {got:+.2f}"
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
        st.error(f"This limit set cannot be sampled.\n\n{exc}")
        st.session_state.pop("limit_set", None)
        return

    st.session_state["limit_set"] = limit_set

    # ---- each limit's share, into the placeholder at the top of its block ----------------
    _result = engine_run.run(limit_set.to_dict(), n_trials, seed)
    _all = _result.controlling_shares()
    _won = _result.controlling_shares(successes_only=True)
    for _name, _slot in share_slots.items():
        if _name not in _all:
            continue
        _slot.caption(
            f"Controls the contact in {_all[_name]:.0%} of realisations, and in "
            f"{_won[_name]:.0%} of those above the assessment minimum."
            + (" Not a limit on this prospect at these inputs; it can stay rough."
               if _all[_name] < 0.005 else ""))

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
                "Every limit as entered, in its own units: a depth-stated limit reads in m TVDSS "
                "and a capacity in metres of column, with no conversion for display. Percentiles "
                "are exceedance; P90 is the shallow end.",
                height=min(60 + 35 * len(rows), 480))
        # ------------------------------------------------------------ checks
        theme.heading(TAB, "3 · Checks")
        if charge_phase and seal_fluid and not phase_clash:
            st.success(f"Phases agree: the charge and seal calculators both hold "
                       f"{seal_fluid.lower()}.")
        elif not (charge_phase and seal_fluid):
            st.caption("The phase check runs once both the charge and the seal calculators are "
                       "in use; with one or neither, there is nothing to compare.")
        if phase_clash:
            st.error(
                f"Phase mismatch: the charge calculator is filling with "
                f"{charge_phase.replace('Pure ', '').lower()} and the seal calculator is holding "
                f"back {seal_fluid.lower()}.\n\n"
                f"Seal capacity is `h_max = P_c / (Δρ·g)`, so it depends on the density contrast "
                f"between the hydrocarbon and the water; the same seal holds a much shorter gas "
                f"column than an oil one. One phase through the charge and the other through the "
                f"seal produces a contact that belongs to no prospect. Both should be set to the "
                f"same fluid, or the two phases run as separate cases.\n\n"
                f"This check is the only link between the two calculators. Within a realisation "
                f"the seal's hydrocarbon density and the charge's formation volume factor are "
                f"drawn from separate streams, so the two do not share a fluid beyond its phase."
            )

        always = [x.name for x in limit_set.limits if x.always_active]
        st.success(
            f"Bounded: {len(limit_set.limits)} limits, of which {len(always)} always active "
            f"({', '.join(always)}). At least one must be, because every prospect has a spill "
            f"point; the engine refuses a set in which the column could be unbounded."
        )
