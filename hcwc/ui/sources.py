"""Where a limit's distribution comes from.

A limit row is either **typed** — min/mode/mean/max, as an assessor states them — or **computed**
by a helper. Charge integrates an area–depth table against a basin-modelled volume; seal capacity
comes out of `Pc = 2γcosθ/r`; the empirical source reads the censoring-corrected NCS fit.

**Every helper hands over the same two things: a column-height distribution, and a ``P(active)``.**
That uniformity is the whole design. It is why one ``Source`` column in the limits table can stand
for all of them, why a helper can open in place under the row it feeds rather than as a tab of its
own, and why adding fault seal later will not touch the tab strip.

The split between the two returned things matters and is easy to get wrong: the **distribution**
carries *where* a mechanism bites, the **probability** carries *whether* it does. Charge makes this
vivid — a charge that fills past the deepest mapped depth is not a shallow limit, it is no limit,
and it belongs in ``P(active)``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hcwc.core import charge as ch
from hcwc.core import censoring, seals
from hcwc.core.limits import DepthDistribution
from hcwc.io import benchmarks
from hcwc.ui import theme


#: Gross reservoir thickness, and so the offset between the top seal's crest and the base seal's.
#: Lars's number, 2 Sep 2026.
DEFAULT_RESERVOIR_THICKNESS_M = 50.0


@dataclass(frozen=True)
class Handover:
    """What a helper gives back to the row that opened it."""
    distribution: DepthDistribution
    p_active: float
    summary: str




# --------------------------------------------------------------------------- charge
def render_charge(key: str, n_trials: int, seed: int,
                  table: "ch.AreaDepthTable | None" = None) -> Handover | None:
    st.markdown(
        "Gross rock volume from the area–depth table, hydrocarbon pore volume from the reservoir "
        "properties, then the depth at which the accumulated pore volume equals the charge the "
        "basin model delivered."
    )
    # Handed in by `_area_depth_panel`, which owns the table so that editing it, uploading one and
    # the export all read the same object. The fallback keeps the function usable on its own.
    if table is None:
        try:
            table = ch.AreaDepthTable.reference()
        except FileNotFoundError:
            st.error("`reference/area_depth.csv` is missing from this checkout.")
            return None

    rng = np.random.default_rng(seed + 991)
    # These three are only ever used as a product, and saying so is worth more than three separate
    # definitions: an assessor who agonises over porosity while leaving net-to-gross at a default
    # is tightening one factor of a number whose other factors are still loose.
    st.caption(
        "The three below multiply to one number — the fraction of gross rock volume that is "
        "hydrocarbon. Only the **product** enters the calculation, so a range that is honest "
        "about all three beats a precise value for one of them."
    )
    c1, c2, c3 = st.columns(3)
    ntg = c1.slider(
        "Net-to-gross", 0.05, 1.0, (0.50, 0.80), key=f"{key}_ntg",
        help="Fraction of the gross interval that is reservoir at all. The range is the "
             "uncertainty, and it is sampled independently in every realisation.")
    por = c2.slider(
        "Porosity", 0.02, 0.45, (0.20, 0.30), key=f"{key}_por",
        help="Of the net rock, the fraction that is pore space. Use the range you would defend "
             "from analogues at this burial depth, not a log average from one well.")
    sat = c3.slider(
        "HC saturation", 0.20, 1.0, (0.50, 0.80), key=f"{key}_sat",
        help="Of the pore space, the fraction filled with hydrocarbon rather than water. The rest "
             "is irreducible water, which is why the top of this range is below 1.")

    case = st.selectbox(
        "Phase case", ["Pure oil", "Pure gas"], key=f"{key}_case",
        help="Which fluid the basin model delivered. It sets the conversion below and the default "
             "volumes, which differ by more than two orders of magnitude — a gas charge in oil "
             "units would fill any closure. It should agree with the seal calculator's fluid: the "
             "same seal holds a much shorter column of gas.")
    st.session_state["charge_phase"] = case
    f1, f2, f3 = st.columns(3)
    mean = f1.number_input(
        "Charge mean (10⁶ Sm³)", 0.0, 500_000.0,
        80.0 if case == "Pure oil" else 39600.0, 1.0, key=f"{key}_mean",
        help="What the basin model says arrived in this closure, at **surface** conditions. This "
             "is the volume charged, not the volume trapped — how much of it the structure can "
             "hold is what the calculation below works out.")
    sd = f2.number_input(
        "Charge sd (10⁶ Sm³)", 0.0, 200_000.0,
        30.0 if case == "Pure oil" else 5500.0, 1.0, key=f"{key}_sd",
        help="One standard deviation on that volume, sampled as a normal and clipped at zero. "
             "Charge volumes are poorly known, so a wide spread here is usually the honest input — "
             "it is what decides how often charge limits the column at all.")
    factor = f3.number_input(
        "Bo (m³/Sm³)" if case == "Pure oil" else "1/Bg (Sm³/m³)",
        0.01, 500.0, 1.35 if case == "Pure oil" else 235.0, 0.01, key=f"{key}_factor",
        help=("Oil formation volume factor: how many reservoir m³ one surface Sm³ occupies down "
              "there. Above 1 because dissolved gas expands the oil in the reservoir."
              if case == "Pure oil" else
              "Inverse gas formation volume factor: how many surface Sm³ fit into one reservoir "
              "m³. Large because gas is compressed at reservoir pressure — which is why a gas "
              "charge quoted in surface units fills so much less rock than it looks like."))

    def tri(pair):
        lo, hi = pair
        return rng.uniform(lo, hi, n_trials)

    k = tri(ntg) * tri(por) * tri(sat)
    volume = rng.normal(mean, sd, n_trials).clip(0.0)
    result = (ch.oil_contact(table, volume, np.full(n_trials, factor), k) if case == "Pure oil"
              else ch.gas_contact(table, volume, np.full(n_trials, factor), k))

    finite = result.contact_m[np.isfinite(result.contact_m)]
    p_active = 1.0 - result.fraction_not_limiting
    m1, m2 = st.columns(2)
    m1.metric("Charge is not limiting", f"{result.fraction_not_limiting:.1%}",
              "fills past the deepest mapped depth", delta_color="off")
    if finite.size:
        m2.metric("P50 contact, when limiting", f"{np.median(finite):,.0f} m")

    if finite.size < 2:
        st.warning(
            "Charge never limits the column with these inputs. That is a legitimate answer — the "
            "prospect is charge-rich — and the honest way to say it is to **delete this row**, not "
            "to give it a distribution at the base of the structure."
        )
        return None

    columns = finite - table.apex_m
    fig = go.Figure()
    fig.add_histogram(y=finite, nbinsy=50, marker_color=theme.PILLAR_COLOURS["Charge"])
    fig.update_layout(xaxis_title="Realisations", yaxis_title="Depth (m TVDSS)",
                      yaxis=dict(autorange="reversed"), height=320, margin=dict(t=10),
                      showlegend=False)
    st.plotly_chart(fig, width="stretch", key=f"{key}_charge_fig")
    st.caption(
        f"Over the {finite.size:,} realisations in which charge bound the column. The other "
        f"{result.fraction_not_limiting:.0%} are carried as `P(active)`, not as a contact at the "
        f"base of the table. Charge that fills past the deepest mapped depth is not a "
        f"shallow limit — it is no limit, and that share belongs in `P(active)`."
    )
    return Handover(DepthDistribution.from_samples(columns), float(p_active),
                    f"{case}, mean {mean:,.0f}")



def _slider_default(pair: tuple[float, float], lo: float, hi: float) -> tuple[float, float]:
    """Clamp a derived range onto a slider's track, as an ordered pair of floats.

    Two ways this goes wrong, both found in one check rather than in the browser:

    * ``round()`` with no ndigits returns an **int**, and Streamlit refuses a slider whose value
      type does not match its float bounds.
    * Clamping the ends independently can **invert** the pair. A burial depth near zero gives a
      temperature range below the slider's floor, and clamping the low end up while leaving the
      high end alone produced ``(10.0, 5.0)`` — a low above its high, which Streamlit also refuses.

    So both ends are clamped, then re-ordered, then floated.
    """
    low, high = (float(min(max(x, lo), hi)) for x in pair)
    if low > high:
        low, high = high, low
    return float(round(low)), float(round(high))

# --------------------------------------------------------------------------- seal capacity
def render_seal(key: str, n_trials: int, seed: int) -> Handover | None:
    st.markdown(
        "`h_max = P_c / (Δρ·g)` with `P_c = 2γcos θ / r`. Inputs are **ranges**, because a limit "
        "needs a distribution rather than a number — and because `P_c` goes as `1/r`, the spread "
        "on pore-throat radius dominates everything else here."
    )
    # The temperature defaults from the burial depth set on tab 2, so a deep prospect cannot be
    # assessed with a shallow prospect's seal. Interfacial tension falls with temperature, so
    # deeper is a weaker seal, and previously the two numbers were typed independently.
    from hcwc.ui.prospect_tab import temperature_range
    burial = st.session_state.get("burial_depth")
    # `if burial` rather than `is not None` treated a burial of zero as no burial at all. Zero is
    # a strange depth but it is one the widget accepts, and the temperature it implies is the one
    # to use.
    default_t = _slider_default(
        temperature_range(float(burial)) if burial is not None else (70.0, 90.0), 10.0, 160.0)

    c1, c2, c3 = st.columns(3)
    # Oil first, so it is the default. The charge calculator opens on *Pure oil* and the tab
    # refuses to run a prospect whose charge and seal disagree about the fluid -- correctly, since
    # capacity is `P_c / (delta-rho . g)` and the same seal holds a much shorter gas column. Leaving
    # this on gas while charge opened on oil would have greeted every new user with that refusal.
    fluid = c1.selectbox(
        "Fluid", ["Oil", "Gas"], key=f"{key}_fluid",
        help="Must agree with the charge calculator's phase. Capacity depends on the density "
             "contrast with formation water, so the same seal holds a much shorter column of gas "
             "than of oil — running one phase through charge and the other through the seal "
             "produces a contact that belongs to no prospect, and tab 3.0 refuses it.")
    st.session_state["seal_fluid"] = fluid
    temp = c2.slider("Temperature (°C)", 10.0, 160.0, default_t, key=f"{key}_t",
                     help=(f"Defaulted from the {burial:,.0f} m burial depth on tab 2.0, at "
                           f"25–40 °C/km. Override if you have a measured gradient."
                           if burial else "Set a burial depth on tab 2.0 to default this."))
    theta = c3.slider(
        "Contact angle θ (°)", 0.0, 60.0, (0.0, 30.0), key=f"{key}_theta",
        help="How strongly the rock prefers water to hydrocarbon. 0° is fully water-wet, which "
             "gives the strongest seal; the range says you do not know it exactly. Rarely "
             "measured, so a range from 0 is the usual honest answer.")

    c4, c5 = st.columns(2)
    r_seal = c4.slider("Seal pore-throat radius (µm)", 0.01, 2.0, (0.01, 0.10), 0.01,
                       key=f"{key}_rs",
                       help="The single most sensitive input, because `P_c` goes as `1/r` — the "
                            "spread here dominates everything else in the calculator. A good shale "
                            "is at or below 0.1 µm, which is where the default range ends.")
    r_res = c5.slider("Reservoir pore-throat radius (µm)", 0.1, 10.0, (2.0, 3.5), 0.1,
                      help="The reservoir's own throats, which set the pressure already in the "
                           "column. They must be **wider** than the seal's — that difference is "
                           "what holds hydrocarbons back.",
                      key=f"{key}_rr")

    c6, c7 = st.columns(2)
    rho_w = c6.slider(
        "Water density (g/cm³)", 0.95, 1.20, (1.00, 1.10), 0.01, key=f"{key}_rw",
        help="**Formation water at reservoir conditions**, not a surface sample. Above 1.00 for "
             "anything saline; temperature pushes it back down a little, so 1.00–1.10 covers most "
             "of the NCS.")
    rho_hc = c7.slider(
        "HC density (g/cm³)", 0.10, 1.00, (0.70, 0.85), 0.01, key=f"{key}_rh",
        help="**In situ, at reservoir pressure and temperature** — not stock-tank oil and not gas "
             "at standard conditions. Only the *difference* from the water matters: capacity is "
             "the entry pressure divided by it, so a light fluid buoys harder and the same seal "
             "holds a much shorter column of it.\n\n"
             "Typical in-situ values: **gas 0.15–0.35**, rising with depth; **live oil 0.60–0.85**, "
             "lighter than the stock-tank oil you would measure at surface because the dissolved "
             "gas is still in it. Surface-condition gas, around 0.0008, is not on this scale and "
             "would give a column height of nonsense.")
    # The one pairing that is quietly wrong. The fluid selector drives the interfacial-tension
    # correlation and the density slider drives the buoyancy, and nothing tied them together: the
    # shipped default used to be gas tension against an oil density contrast, which is the most
    # generous combination the calculator can produce and is not a fluid. Lars asked what these
    # densities are; this is the check that goes with the answer.
    _mid_hc = 0.5 * (rho_hc[0] + rho_hc[1])
    if fluid == "Gas" and _mid_hc > GAS_OIL_DENSITY_BOUNDARY:
        st.warning(
            f"**That is an oil density against a gas interfacial tension.** In situ gas runs about "
            f"0.15–0.35 g/cm³ at these depths, and this is set around {_mid_hc:.2f}. The two "
            f"inputs disagree about which fluid this is, and the combination is the most generous "
            f"the calculator can produce — high tension with a small density contrast — so the "
            f"capacity it returns is larger than either fluid would really give."
        )
    elif fluid == "Oil" and _mid_hc < GAS_OIL_DENSITY_BOUNDARY:
        st.warning(
            f"**That is a gas density against an oil interfacial tension.** Live oil in situ runs "
            f"about 0.60–0.85 g/cm³, and this is set around {_mid_hc:.2f}. Oil–water tension is "
            f"roughly a third of gas–water, so pairing it with a gas density understates the "
            f"capacity rather than overstating it — but it is still not a fluid."
        )

    # Hood (2019) slide 18 wants a GOC and an OWC both set by capillary capacity, and this
    # calculator holds one fluid at a time. Flagged rather than silently absent, because an
    # assessor on a two-phase prospect will come here looking for it and the honest answer is
    # "run the phases separately, and here is why that is not the same thing". The plan is
    # written; see docs/PLAN_DUAL_PHASE_SEAL.md.
    with st.expander("**Two phases in one closure?** — what this calculator will not do"):
        st.markdown(
            "This holds **one fluid at a time**. On a prospect with a gas cap over an oil leg, run "
            "the two as separate cases — which is Hood's own advice, and what tab 3.0 tells you to "
            "do if the charge and seal calculators disagree about the phase.\n\n"
            "**It is not the same as a two-phase answer, and not conservatively so.** A single "
            "seal sees gas at the crest and oil on the flanks between the two contacts, so the "
            "gas cap is rated at the gas entry pressure while the oil leg below is rated at the "
            "oil one. The oil leg is unchanged by the gas above it, and the gas cap sits on top "
            "of it — so the *total* column a two-phase trap can hold is **taller than either "
            "single-phase answer**, not somewhere between them.\n\n"
            "On these shipped defaults that is roughly 150 m of oil under 130 m of gas against "
            "150 m pure oil or 183 m pure gas. Spill and every other limit still apply on top, so "
            "the effect only shows on a closure tall enough to let it.\n\n"
            "Two-phase capacity is **not implemented**: the numbers above are what the physics in "
            "`hcwc/core/seals.py` gives when the two constraints are written out, not something "
            "this tool computes for you. `docs/PLAN_DUAL_PHASE_SEAL.md` is the plan. The "
            "charge-driven route to a gas–oil contact exists in `hcwc.core.charge` "
            "(`mixed_separate`, `mixed_joint`) and is not wired to any control either."
        )

    net = st.toggle("Subtract the reservoir's own entry pressure", value=True, key=f"{key}_net",
                    help="The physically complete form — hydrocarbon already occupies the "
                         "reservoir pores, so only the *difference* must be overcome.")

    try:
        inputs = seals.SealInputs(temperature_c=temp, contact_angle_deg=theta,
                                  seal_radius_um=r_seal, reservoir_radius_um=r_res,
                                  water_density_g_cm3=rho_w, hc_density_g_cm3=rho_hc,
                                  fluid=fluid, subtract_reservoir=net)
        capacity = seals.sample_max_column_m(inputs, n_trials, seed + 313)
    except ValueError as exc:
        st.error(str(exc))
        return None

    # The base seal's crest sits one reservoir thickness below the structural apex everything in
    # this tool is measured from, so its capacity bites that much deeper. The *Same as the top seal*
    # shortcut already carries the offset; a base seal computed from its own parameters is the same
    # geometry and needs it too, or the two routes to one limit would disagree about where it is.
    thickness = 0.0
    if is_base_seal(key):
        thickness = st.number_input(
            "Reservoir thickness (m)", 0.0, 2000.0, DEFAULT_RESERVOIR_THICKNESS_M, 5.0,
            key=f"{key}_thickness",
            help="Gross thickness between the top reservoir and its base. The base seal's crest "
                 "sits this far below the structural apex, so its capacity is measured from there "
                 "and its limit lands that much deeper. Only asked for on the base seal — the top "
                 "seal *is* the datum.")

    elicited = capacity
    with st.expander("**Pull this toward the NCS record** — a shrinkage prior on seal capacity"):
        st.markdown(
            "Edmundson's §5.2 asks for base rates to be *integrated* with the geological "
            "assessment and does not say how. This is the safest place in the tool to do it: the "
            "censoring-corrected NCS fit predicts **the same quantity this calculator computes** "
            "— a seal capacity in metres of column — so the two can be averaged without either "
            "having to stand in for the other.\n\n"
            "**Against burial depth alone, and the omission is on purpose.** The fit also carries "
            "a trap-height term, which is real in the data, but a *capacity* that knew how big "
            "your closure was would smuggle geometry into a capillary property — and the engine "
            "already takes `min(capacity, spill)` on top of it. Compaction closing pore throats is "
            "the part with a physical reason to track burial, and it is the part borrowed."
        )
        weight = 0.0
        if not burial:
            st.info("Set a burial depth on tab 2.0 to draw the NCS capacity for this prospect.")
        else:
            weight = st.slider(
                "Weight on the NCS record", 0.0, 1.0, 0.0, 0.05, key=f"{key}_shrink",
                help="0 leaves your calculator untouched; 1 replaces it with the record. In "
                     "between, the two quantile functions are averaged, so the answer sits "
                     "*between* them rather than becoming two humps — which is what shrinking "
                     "toward a population means.")
            reference = benchmarks.ncs_seal_capacity(float(burial), n_trials, seed + 977)
            if weight > 0:
                capacity = benchmarks.shrink_toward(elicited, reference, weight)
            r1, r2, r3 = st.columns(3)
            for col, p, label in ((r1, 10, "P90"), (r2, 50, "P50"), (r3, 90, "P10")):
                col.metric(f"NCS {label}", f"{np.percentile(reference, p):,.0f} m",
                           f"yours {np.percentile(elicited, p):,.0f} m", delta_color="off")
            fit = benchmarks._capacity_fit()
            st.caption(
                f"The capacities the NCS record implies at **{burial:,.0f} m** burial, from the "
                f"censoring-corrected fit `log S = {fit.intercept:.2f} + "
                f"{fit.slope:.2f}·log(burial)`. Fitted naively the burial term is about half that, "
                "because censoring hides exactly the deep, well-sealed traps that carry the "
                "relationship.\n\n"
                "⚠ **The record is discoveries only.** All 242 of those traps held hydrocarbons, "
                "so this is a prior on *how much a seal holds where it holds something*. It says "
                "nothing about whether yours does, and it must never touch the chance."
            )

    m1, m2, m3 = st.columns(3)
    shrunk = capacity is not elicited
    m1.metric("P90 capacity", f"{np.percentile(capacity, 10):,.0f} m",
              f"before shrinking {np.percentile(elicited, 10):,.0f} m" if shrunk else None,
              delta_color="off")
    m2.metric("P50 capacity", f"{np.percentile(capacity, 50):,.0f} m",
              f"before shrinking {np.percentile(elicited, 50):,.0f} m" if shrunk else None,
              delta_color="off")
    m3.metric("P10 capacity", f"{np.percentile(capacity, 90):,.0f} m",
              f"before shrinking {np.percentile(elicited, 90):,.0f} m" if shrunk else None,
              delta_color="off")

    from plotly.subplots import make_subplots
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_histogram(x=capacity, nbinsx=60, name="Realisations",
                      marker_color=theme.PILLAR_COLOURS["Retention"], opacity=0.8)
    grid = np.linspace(float(capacity.min()), float(capacity.max()), 240)
    fig.add_scatter(x=grid, y=(capacity[None, :] >= grid[:, None]).mean(axis=1), mode="lines",
                    name="Probability of exceedance", secondary_y=True,
                    line=dict(color="#DD8452", width=2.4))
    for label, value in (("P90", np.percentile(capacity, 10)),
                         ("P50", np.percentile(capacity, 50)),
                         ("P10", np.percentile(capacity, 90))):
        fig.add_vline(x=float(value), line=dict(color="#888", width=1, dash="dash"),
                      annotation_text=f"{label}: {value:,.0f}", annotation_font_size=10)
    fig.update_layout(height=330, margin=dict(t=30), bargap=0.02,
                      legend=dict(orientation="h", y=1.16))
    fig.update_xaxes(title_text="Column the seal can hold (m)")
    fig.update_yaxes(title_text="Realisations", secondary_y=False)
    fig.update_yaxes(title_text="P(capacity at least this)", range=[0, 1.02], secondary_y=True)
    st.plotly_chart(fig, width="stretch", key=f"{key}_seal_fig")
    st.caption(
        "⚠ **Check the units on any capacity you compare this against.** Interfacial "
        "tension is quoted in dyne/cm and the conversion to N/m is `× 1e-3`; a stray "
        "`/100` gives a column ten times too long and looks entirely plausible on a chart."
    )

    with st.expander("Is this capacity plausible? — the published calibration", expanded=False):
        st.markdown(
            "Every published model on one axis, computed live from this prospect's fluids rather "
            "than read off a chart. Porosity comes down with burial "
            "(Hansen, 1996), each published model turns porosity into a capillary entry pressure, "
            "and Schowalter's (1979) balance turns that into a column: "
            "`H = 2γcosθ (1/r − 1/R) / (g·Δρ)`. Dotted lines are each model's ±5 porosity-point "
            "cases.\n\n"
            "**The four disagree by roughly a factor of five, and that is the finding rather than a "
            "defect.** Picking one as *the* answer would be false precision; the spread between them "
            "is the honest uncertainty on any capacity derived this way, and it is why the "
            "calculator asks for ranges. **The black bar is what you have selected above** — if it "
            "sits outside the envelope at your burial depth, either the pore-throat radius or the "
            "envelope is wrong, and it is worth knowing which."
        )
        st.plotly_chart(
            calibration_figure(float(np.mean(rho_w)), float(np.mean(rho_hc)),
                               st.session_state.get("burial_depth"), capacity),
            width="stretch", key=f"{key}_calib")
    if thickness:
        st.caption(
            f"**The limit is the capacity plus the reservoir thickness.** This seal holds "
            f"{np.percentile(capacity, 50):,.0f} m at P50, and it holds it starting "
            f"{thickness:,.0f} m below the structural apex — so it bites at "
            f"{np.percentile(capacity + thickness, 50):,.0f} m of column, which is the number the "
            f"engine competes on."
        )
    return Handover(DepthDistribution.from_samples(capacity + thickness), 1.0,
                    f"{fluid}, r {r_seal[0]:.2f}–{r_seal[1]:.2f} µm"
                    + (f" +{thickness:,.0f} m" if thickness else ""))


# --------------------------------------------------------------------------- empirical
def render_empirical(key: str, n_trials: int, seed: int) -> Handover | None:
    st.markdown(
        "What the 242 NCS discoveries predict for a closure of these dimensions, **corrected for "
        "the spill-point censoring** — seal capacity from the censored fit, then capped at the "
        "closure, which is the same `min(S, H)` the geology applies. The fallback for a prospect "
        "with nothing better, and the benchmark for one that has."
    )
    c1, c2 = st.columns(2)
    closure = c1.number_input("Closure height (m)", 20.0, 1500.0, 350.0, 10.0, key=f"{key}_h")
    burial = c2.number_input("Burial depth (m)", 200.0, 6000.0, 2050.0, 50.0, key=f"{key}_z")
    try:
        d = benchmarks.load_edmundson().rows
    except FileNotFoundError as exc:
        st.error(str(exc))
        return None
    fit = censoring.censored_loglinear(
        {"trap_height": d.trap_height_m.to_numpy(float),
         "burial_depth": d.burial_depth_m.to_numpy(float)},
        d.hc_column_m.to_numpy(float), d.trap_height_m.to_numpy(float))
    mu = (fit.intercept + fit.coefficients["trap_height"] * np.log(closure)
          + fit.coefficients["burial_depth"] * np.log(burial))
    rng = np.random.default_rng(seed + 77)
    samples = np.minimum(np.exp(rng.normal(mu, fit.sigma, n_trials)), closure)

    m1, m2 = st.columns(2)
    m1.metric("P50 column", f"{np.median(samples):,.0f} m")
    m2.metric("Fills to spill", f"{np.mean(samples >= closure - 1e-9):.0%}",
              "of realisations", delta_color="off")
    st.caption(
        "⚠ Discovery-conditioned, and the spike at the closure height is the filled-to-spill point "
        "mass. Use it as a prior only where nothing better exists — tab 6.0 sets out what it is and "
        "is not measuring."
    )
    return Handover(DepthDistribution.from_samples(samples), 1.0,
                    f"NCS fit, closure {closure:,.0f} m at {burial:,.0f} m")

# --------------------------------------------------------------------------- block adapters
def _as_triple(handover: "Handover | None"):
    """`limit_block.render` wants a plain triple, not a `Handover`.

    Kept as a one-line adapter rather than changing the renderers, because the `Handover` dataclass
    is what makes the contract obvious when reading `render_charge` on its own.
    """
    if handover is None:
        return None
    return handover.distribution, handover.p_active, handover.summary


def render_charge_computed(key: str, n_trials: int, seed: int):
    """The charge filling calculator, for use as a `limit_block` ``computed`` hook.

    The **area-depth table is drawn here**, next to the integration that consumes it. It used to
    sit on tab 2, one tab away from the only thing that reads it, which is half of why the charge
    branch was impossible to find.
    """
    table = _area_depth_panel()
    if table is None:
        return None
    return _as_triple(render_charge(key, n_trials, seed, table))


def render_empirical_computed(key: str, n_trials: int, seed: int):
    """The censoring-corrected NCS fit, for use as a `limit_block` ``computed`` hook."""
    return _as_triple(render_empirical(key, n_trials, seed))


def render_seal_computed(key: str, n_trials: int, seed: int):
    """The seal-capacity calculator, for use as a `limit_block` ``computed`` hook."""
    return _as_triple(render_seal(key, n_trials, seed))


#: The key prefix `limiters_tab` gives the top seal's block. The base seal reads its widgets from
#: here rather than owning a second copy, which is the whole point of the *same as top* source.
#: Where an in-situ hydrocarbon density stops looking like gas and starts looking like oil.
#:
#: Not a physical constant — a screen. Gas at 2–4 km rarely exceeds 0.45 g/cm³ and live oil rarely
#: falls below 0.55, so anything either side of the middle of that gap is almost certainly the
#: wrong fluid rather than an unusual one.
GAS_OIL_DENSITY_BOUNDARY = 0.50

TOP_SEAL_KEY = "lim_Top seal (capillary)"


def is_base_seal(key: str) -> bool:
    """Whether a seal block is the base seal, and so sits a reservoir thickness deeper.

    By name rather than by an extra argument through two call sites, because the limit's name is
    already the thing that decides it and `limit_block` passes the key everywhere.
    """
    return "Base seal" in key


def render_seal_as_top(key: str, n_trials: int, seed: int) -> Handover | None:
    """The top seal's calculator, run again for the base seal, on the top seal's own inputs.

    One shale unit often wraps the reservoir, and where it does, typing the same six ranges twice
    is not a second opinion — it is two copies that will drift apart the first time one is edited.
    This reads the top seal's widgets directly, so there is exactly one place to change them.

    It needs the top seal to actually be on its calculator. If it is typed, there are no inputs to
    borrow and saying so is better than silently falling back to a default nobody chose.
    """
    have = all(f"{TOP_SEAL_KEY}_{suffix}" in st.session_state
               for suffix in ("fluid", "t", "theta", "rs", "rr", "rw", "rh", "net"))
    if not have:
        st.info(
            "**The top seal is not on its calculator, so there are no inputs to copy.** Open "
            "*Top seal (capillary)* above and set it to *From seal capacity* first — or compute "
            "this one on its own with *From seal capacity* here."
        )
        return None

    # The one thing that is *not* the same as the top seal: where it sits.
    #
    # Every capacity in this tool is measured downward from the **structural apex**, which is the
    # crest of the top reservoir. The base seal's own crest is one reservoir thickness below that.
    # So the same shale, with the same capacity in metres of column, bites a reservoir thickness
    # deeper -- and without the offset a base seal identical to the top seal would be entered as
    # though it sat at the crest, which is the one place it certainly does not.
    thickness = st.number_input(
        "Reservoir thickness (m)", 0.0, 2000.0, DEFAULT_RESERVOIR_THICKNESS_M, 5.0,
        key=f"{key}_thickness",
        help="Gross thickness between the top reservoir and its base. It is the offset between "
             "the two seals: the base seal's crest sits this far below the structural apex, so "
             "its capacity is measured from there and its limit lands that much deeper.")

    read = lambda suffix: st.session_state[f"{TOP_SEAL_KEY}_{suffix}"]  # noqa: E731
    try:
        inputs = seals.SealInputs(
            temperature_c=read("t"), contact_angle_deg=read("theta"),
            seal_radius_um=read("rs"), reservoir_radius_um=read("rr"),
            water_density_g_cm3=read("rw"), hc_density_g_cm3=read("rh"),
            fluid=read("fluid"), subtract_reservoir=read("net"))
        capacity = seals.sample_max_column_m(inputs, n_trials, seed + 313)
    except ValueError as exc:
        st.error(str(exc))
        return None

    st.markdown(
        "**Taken from the top seal, unchanged.** Same shale, same fluids, same physics — edit it "
        "above and this follows.\n\n"
        f"- pore-throat radius **{read('rs')[0]:g} – {read('rs')[1]:g} µm**\n"
        f"- temperature **{read('t')[0]:,.0f} – {read('t')[1]:,.0f} °C**, "
        f"contact angle **{read('theta')[0]:,.0f} – {read('theta')[1]:,.0f}°**\n"
        f"- {read('fluid').lower()} at **{read('rh')[0]:g} – {read('rh')[1]:g} g/cm³** against "
        f"water at **{read('rw')[0]:g} – {read('rw')[1]:g} g/cm³**"
    )
    # What the engine competes on: the capacity, carried down to where this seal actually is.
    limit = capacity + float(thickness)
    m1, m2, m3 = st.columns(3)
    m1.metric("P90 limit", f"{np.percentile(limit, 10):,.0f} m",
              f"capacity {np.percentile(capacity, 10):,.0f} m", delta_color="off")
    m2.metric("P50 limit", f"{np.percentile(limit, 50):,.0f} m",
              f"capacity {np.percentile(capacity, 50):,.0f} m", delta_color="off")
    m3.metric("P10 limit", f"{np.percentile(limit, 90):,.0f} m",
              f"capacity {np.percentile(capacity, 90):,.0f} m", delta_color="off")
    st.caption(
        f"**Both numbers are metres of column below the structural apex, and they differ by the "
        f"reservoir thickness.** The *capacity* is what this shale can hold, which is the top "
        f"seal's number unchanged. The *limit* is where it bites — {thickness:,.0f} m deeper, "
        f"because the base seal's crest is {thickness:,.0f} m below the crest everything else in "
        f"this tool is measured from."
    )
    st.caption(
        "⚠ **Identical inputs are not an identical outcome, and the difference is on the "
        "Correlations sub-tab.** Sampled independently, top and base seal fail at different "
        "columns in the same realisation, which is a claim that one shale can be tight above and "
        "leaky below at the same moment. If it is one unit, correlate them — the pairing is "
        "already listed there, waiting for a number."
    )
    return Handover(DepthDistribution.from_samples(limit), 1.0,
                    f"as top seal +{thickness:,.0f} m — {read('fluid').lower()}, "
                    f"r {read('rs')[0]:.2f}–{read('rs')[1]:.2f} µm")


def render_seal_as_top_computed(key: str, n_trials: int, seed: int):
    """`render_seal_as_top`, for use as a `limit_block` ``computed`` hook."""
    return _as_triple(render_seal_as_top(key, n_trials, seed))


#: Session keys for the area–depth table. `AREA_DEPTH_ROWS` holds the live grid; the rest are
#: widgets. All are saved with the prospect — but only when the charge calculator is the source of
#: the Charge limit, since otherwise the table is decoration and a saved file should not carry it.
AREA_DEPTH_ROWS = "charge_ad_rows"
AREA_DEPTH_METHOD = "charge_ad_method"
AREA_DEPTH_THICKNESS = "charge_ad_thickness"

SURFACES, THICKNESS = "Two mapped surfaces", "Top surface and a thickness"


def _seed_rows() -> "pd.DataFrame":
    """The shipped example, as an editable frame."""
    table = ch.AreaDepthTable.reference()
    return pd.DataFrame({"Depth (m TVDSS)": table.depths_m,
                         "Top area (km²)": table.top_area_km2,
                         "Base area (km²)": table.base_area_km2})


def _table_from_rows(frame: "pd.DataFrame", method: str,
                     thickness_m: float) -> "ch.AreaDepthTable":
    """Build the table the engine uses from whatever is in the grid."""
    clean = frame.dropna(subset=["Depth (m TVDSS)", "Top area (km²)"])
    clean = clean.sort_values("Depth (m TVDSS)")
    depths = clean["Depth (m TVDSS)"].to_numpy(float)
    top = clean["Top area (km²)"].to_numpy(float)
    if method == THICKNESS:
        return ch.AreaDepthTable.from_top_and_thickness(depths, top, thickness_m)
    base = clean["Base area (km²)"].fillna(0.0).to_numpy(float)
    return ch.AreaDepthTable(depths_m=depths, top_area_km2=top, base_area_km2=base)


def current_area_depth() -> "ch.AreaDepthTable | None":
    """The area–depth table in force, wherever it is needed outside the charge panel.

    The grid on tab 3.0 is the single source of truth, and two other places read it: the WellVolPOS
    export writes an area and a gross rock volume per realisation, and the DHI area cross-check on
    tab 5.0 turns an anomaly's areal extent into a contact depth. Both used to load
    ``reference/area_depth.csv`` directly, which was harmless while the table was fixed and would
    have been a silent lie the moment it became editable — an export describing a structure the
    assessor had replaced.

    Falls back to the shipped example when the grid has not been built yet, which is what those two
    call sites were doing anyway.
    """
    rows = st.session_state.get(AREA_DEPTH_ROWS)
    if rows is not None and len(rows):
        try:
            return _table_from_rows(
                rows, st.session_state.get(AREA_DEPTH_METHOD, SURFACES),
                float(st.session_state.get(AREA_DEPTH_THICKNESS, 50.0)))
        except (ValueError, KeyError):
            return None
    try:
        return ch.AreaDepthTable.reference()
    except FileNotFoundError:
        return None


def _area_depth_panel() -> "ch.AreaDepthTable | None":
    """The structure the charge has to fill — shown, editable, and importable.

    **The table used to be invisible and fixed.** It was read straight off
    ``reference/area_depth.csv`` on every render and drawn as a chart, so a reader could see the
    shape of the structure and not one of the numbers behind it, and could not describe their own
    prospect at all. It is the input the whole charge calculation rests on.

    One grid is the single source of truth: the calculator below, the gross-rock-volume curve and
    the WellVolPOS export all read what is in it.
    """
    st.markdown(
        "**The structure the charge has to fill.** Gross rock volume is the trapezoidal integral "
        "of *top area minus base area* — km² × m is 10⁶ m³, so no conversion factor is needed."
    )

    method = st.radio(
        "How is the structure described?", [SURFACES, THICKNESS], horizontal=True,
        key=AREA_DEPTH_METHOD,
        help="**Two mapped surfaces** takes a base area for every depth, which is what you have "
             "when the base reservoir is mapped. **Top surface and a thickness** derives the base "
             "by shifting the top down a constant gross thickness — the common case, and the same "
             "construction SCOPE-HC uses, so a prospect carried between the two tools gets the "
             "same volume.")

    # A reloaded prospect arrives as three flat lists rather than a frame -- the save format
    # holds scalars and sequences, not tables. Rebuilt here, once, before the grid is drawn.
    if "charge_ad_depth_m" in st.session_state and AREA_DEPTH_ROWS not in st.session_state:
        depths = list(st.session_state.pop("charge_ad_depth_m"))
        top = list(st.session_state.pop("charge_ad_top_km2", []))
        base = list(st.session_state.pop("charge_ad_base_km2", []))
        if len(top) == len(depths):
            st.session_state[AREA_DEPTH_ROWS] = pd.DataFrame({
                "Depth (m TVDSS)": depths, "Top area (km²)": top,
                "Base area (km²)": base if len(base) == len(depths) else [0.0] * len(depths)})

    if AREA_DEPTH_ROWS not in st.session_state:
        try:
            st.session_state[AREA_DEPTH_ROWS] = _seed_rows()
        except FileNotFoundError:
            st.error("`reference/area_depth.csv` is missing from this checkout, so there is no "
                     "table to start from. Upload one below.")
            st.session_state[AREA_DEPTH_ROWS] = pd.DataFrame(
                {"Depth (m TVDSS)": [], "Top area (km²)": [], "Base area (km²)": []})

    c1, c2 = st.columns([2, 1])
    with c1:
        upload = st.file_uploader(
            "Import an area–depth table (.csv)", type=["csv"], key="charge_ad_upload",
            help="One row per mapped depth, with a depth and a top area. A base area column is "
                 "used if present and ignored under *top surface and a thickness*. Column "
                 "spellings are matched loosely — `TVDSS`, `Top area (km2)` and similar all work — "
                 "because these come out of mapping software and nobody renames them by hand.")
    with c2:
        thickness = st.number_input(
            "Gross reservoir thickness (m)", 0.0, 2000.0, 50.0, 5.0,
            key="charge_ad_thickness", disabled=method != THICKNESS,
            help="The vertical gross thickness of the reservoir slab. The base surface is the top "
                 "shifted down by this, so above the crest plus this depth there is no base yet.")
        if st.button("Reset to the shipped example", width="stretch",
                     key="charge_ad_reset"):
            try:
                st.session_state[AREA_DEPTH_ROWS] = _seed_rows()
                st.rerun()
            except FileNotFoundError:
                st.error("`reference/area_depth.csv` is not in this checkout.")

    if upload is not None and st.session_state.get("charge_ad_upload_name") != upload.name:
        try:
            imported = ch.AreaDepthTable.from_csv(upload.getvalue())
        except (ValueError, UnicodeDecodeError) as exc:
            st.error(f"**That file could not be read.** {exc}")
        else:
            st.session_state[AREA_DEPTH_ROWS] = pd.DataFrame(
                {"Depth (m TVDSS)": imported.depths_m,
                 "Top area (km²)": imported.top_area_km2,
                 "Base area (km²)": imported.base_area_km2})
            st.session_state["charge_ad_upload_name"] = upload.name
            st.success(f"Read {imported.depths_m.size} rows from **{upload.name}**.")
            st.rerun()

    columns = ["Depth (m TVDSS)", "Top area (km²)"] + (
        [] if method == THICKNESS else ["Base area (km²)"])
    edited = st.data_editor(
        st.session_state[AREA_DEPTH_ROWS], key="charge_ad_editor", num_rows="dynamic",
        width="stretch", height=280,
        column_order=columns,
        column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in columns})
    st.session_state[AREA_DEPTH_ROWS] = edited

    try:
        table = _table_from_rows(edited, method, float(thickness))
    except ValueError as exc:
        st.error(f"**This table cannot be integrated.** {exc}")
        return None

    s1, s2, s3 = st.columns(3)
    s1.metric("Apex of the mapped surface", f"{table.apex_m:,.0f} m")
    s2.metric("Deepest mapped", f"{table.deepest_m:,.0f} m")
    s3.metric("Gross rock volume", f"{table.capacity_1e6m3:,.0f} ×10⁶ m³")

    # Area and cumulative volume on one depth axis. They are read together -- *how big is the
    # structure here* and *how much has it held by here* -- and putting them on two figures makes
    # the reader carry a depth in their head between them.
    fig = go.Figure()
    fig.add_scatter(x=table.top_area_km2, y=table.depths_m, mode="lines", name="top reservoir",
                    line=dict(color=theme.PILLAR_COLOURS["Closure"], width=2.5))
    fig.add_scatter(x=table.base_area_km2, y=table.depths_m, mode="lines", name="base reservoir",
                    line=dict(color=theme.PILLAR_COLOURS["Reservoir"], width=2.5))
    fig.add_scatter(x=table.grv_1e6m3, y=table.depths_m, mode="lines",
                    name="cumulative gross rock volume", xaxis="x2",
                    line=dict(color=theme.PILLAR_COLOURS["Charge"], width=3.2, dash="dash"))
    fig.update_layout(
        xaxis=dict(title="Area (km²)", side="bottom"),
        xaxis2=dict(title="Cumulative GRV (×10⁶ m³)", overlaying="x", side="top",
                    showgrid=False),
        yaxis=dict(title="Depth (m TVDSS)", autorange="reversed"),
        height=430, margin=dict(t=44), legend=dict(orientation="h", y=-0.22))
    st.plotly_chart(fig, width="stretch", key="area_depth_charge")
    st.caption(
        f"**Two readings on one depth axis.** Solid lines are area against depth, on the bottom "
        f"axis; the dashed line is the rock volume accumulated from the apex down, on the top "
        f"axis. The charge calculation below is one lookup on that dashed curve — it converts the "
        f"charge volume into a pore volume and reads off the depth where the structure has held "
        f"that much."
        + (f"\n\n**The base surface is derived**, not mapped: the top shifted down "
           f"{thickness:,.0f} m. On the shipped example that reproduces the mapped base exactly, "
           f"which is a useful check that the two methods agree."
           if method == THICKNESS else "")
    )
    return table


#: One colour per published entry-pressure model.
MODEL_COLOURS = {"Ibrahim": "#4C72B0", "Hildebrand": "#C44E52",
                 "PetroMod": "#55A868", "Greenland": "#E8A33D"}


def calibration_figure(rho_w: float, rho_hc: float, burial_m: float | None,
                       capacity: "np.ndarray | None" = None) -> "go.Figure":
    """Max column height against shale burial depth, for all four published models.

    Every published entry-pressure model on one axis, computed live rather than read off a
    published chart. Porosity comes down from Hansen (1996),
    each model turns porosity into a capillary entry pressure, and Schowalter's balance turns that
    into a column: `H = 2γcosθ(1/r − 1/R) / (g·Δρ)`.

    **The four disagree by a factor of five, and that is the finding, not a defect.** Offering one
    of them as *the* answer would be a false precision; the spread between them is the honest
    uncertainty on any seal capacity derived this way, and it is why the calculator above asks for
    a range rather than a number.

    ``capacity`` overlays the distribution currently selected, so an assessor can see at a glance
    whether what they have elicited is inside the published envelope at their own burial depth.
    """
    depths = np.linspace(500.0, 5000.0, 120)
    fig = go.Figure()
    for model, colour in MODEL_COLOURS.items():
        for case, dash, width, show in (("low", "dot", 1, False), ("mid", None, 2.6, True),
                                        ("high", "dot", 1, False)):
            y = seals.max_column_height_curve(depths, rho_w, rho_hc, model=model, case=case)
            fig.add_scatter(x=depths, y=y, mode="lines", name=model, legendgroup=model,
                            showlegend=show, line=dict(color=colour, width=width, dash=dash),
                            hovertemplate=f"{model} {case}<br>%{{x:,.0f}} m → %{{y:,.0f}} m"
                                          "<extra></extra>")

    if burial_m:
        fig.add_vline(x=float(burial_m), line=dict(color="#8A8A8A", width=1, dash="dash"),
                      annotation_text=f"this prospect, {burial_m:,.0f} m",
                      annotation_position="top left", annotation_font_size=10)
        if capacity is not None and len(capacity):
            p90, p50, p10 = np.percentile(capacity, [10, 50, 90])
            fig.add_scatter(x=[burial_m, burial_m], y=[p90, p10], mode="lines",
                            name="selected input", legendgroup="input",
                            line=dict(color=theme.INK, width=6), opacity=0.55,
                            hovertemplate="P90–P10 %{y:,.0f} m<extra></extra>")
            fig.add_scatter(x=[burial_m], y=[p50], mode="markers", name="selected P50",
                            legendgroup="input", showlegend=False,
                            marker=dict(color=theme.INK, size=11, symbol="diamond"),
                            hovertemplate="P50 %{y:,.0f} m<extra></extra>")

    fig.update_layout(xaxis_title="Max shale burial depth below mudline (m)",
                      yaxis_title="Max potential HC column height (m)",
                      yaxis_range=[0, 1000], height=430, margin=dict(t=30),
                      legend=dict(orientation="h", y=-0.22))
    return fig


# --------------------------------------------------------------------------- mechanical top seal
#: Typical gradients used only to *default* the two pressure sliders from the crest depth, so the
#: calculator opens on numbers of the right size rather than on zeros. Both are wrong for any
#: particular prospect, which is the point of asking.
HYDROSTATIC_BAR_PER_M = 0.105
FRACTURE_BAR_PER_M = 0.158


def _crest_depth_m() -> float:
    """The structural apex from tab 2.0, or the reference prospect's own crest."""
    apex = st.session_state.get("apex")
    if apex:
        return float(np.mean(apex))
    return 2050.0


def render_mechanical(key: str, n_trials: int, seed: int) -> Handover | None:
    """The fracture-limited column: how much pressure the trap can take before the seal parts.

    Grant (2020) equation 8, and the mechanism the tool was missing. Every other Retention limit
    here is capillary or geometric -- a seal leaks because its pore throats are wide enough, or
    because there is a hole in it. This one is neither: the seal *breaks*, because the pressure at
    the crest reaches the minimum horizontal stress and the rock parts in tension.

    The two are independent. A shale can have superb capillary properties and still sit against its
    fracture limit in an overpressured section, and a mediocre one can be nowhere near it. Which is
    exactly the case for competing them rather than picking the one that sounds most likely.
    """
    st.markdown(
        "`H = (S_Hmin − P_p) / (grad_w − grad_h)` — Grant (2020), eq. 8.\n\n"
        "The trap can take **`S_Hmin − P_p`** more bar at its crest before the seal hydrofractures. "
        "A buoyant column raises the crest pressure above the aquifer's by `grad_w − grad_h` per "
        "metre, so that headroom divided by the excess is how many metres fit. Tensile strength is "
        "taken as zero and folded into `S_Hmin`: natural flaws and pre-existing sealed fractures "
        "make an intact rock's tensile strength the wrong number to use."
    )

    crest = _crest_depth_m()
    c1, c2 = st.columns(2)
    p_pore = c1.slider(
        "Reservoir pore pressure at the crest (bar)", 0.0, 1200.0,
        (float(round(crest * HYDROSTATIC_BAR_PER_M - 5)),
         float(round(crest * HYDROSTATIC_BAR_PER_M + 5))), 1.0,
        key=f"{key}_pp",
        help=f"From an MDT, RFT or a pressure model, at **{crest:,.0f} m** — the crest from tab "
             f"2.0. Defaulted at a hydrostatic {HYDROSTATIC_BAR_PER_M:.3f} bar/m; a prospect with "
             f"any overpressure sits above that, and overpressure is what makes this mechanism "
             f"bite at all.")
    s_hmin = c2.slider(
        "Minimum horizontal stress S_Hmin at the crest (bar)", 0.0, 1500.0,
        (float(round(crest * FRACTURE_BAR_PER_M - 10)),
         float(round(crest * FRACTURE_BAR_PER_M + 10))), 1.0,
        key=f"{key}_shmin",
        help="From the lower envelope of regional leak-off tests (Gaarenstroom et al. 1993), from "
             "a pore-pressure/stress coupling model, or from an offset structure known to be "
             "leaking. The *lower* envelope, not the mean: a seal fails at its weakest point.")

    c3, c4 = st.columns(2)
    rho_w = c3.slider(
        "Water density (g/cm³)", 0.95, 1.20, (1.00, 1.10), 0.01, key=f"{key}_rw",
        help="**Formation water at reservoir conditions.** Only the contrast with the hydrocarbon "
             "matters here — it is what converts spare pressure into metres.")
    rho_hc = c4.slider(
        "HC density (g/cm³)", 0.10, 1.00, (0.70, 0.85), 0.01, key=f"{key}_rh",
        help="**In situ, at reservoir pressure and temperature.** Typical: gas 0.15–0.35, live oil "
             "0.60–0.85. A lighter fluid buoys harder, so the same headroom holds a shorter column "
             "of gas than of oil — the opposite way round from how it feels.")

    try:
        inputs = seals.MechanicalSealInputs(s_hmin_bar=s_hmin, pore_pressure_bar=p_pore,
                                           water_density_g_cm3=rho_w, hc_density_g_cm3=rho_hc)
        column = seals.sample_mechanical_column_m(inputs, n_trials, seed + 617)
    except ValueError as exc:
        st.error(str(exc))
        return None

    headroom = seals.fracture_headroom_bar(np.mean(s_hmin), np.mean(p_pore))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Headroom at the crest", f"{headroom:,.0f} bar",
              f"{np.mean(s_hmin):,.0f} − {np.mean(p_pore):,.0f}", delta_color="off")
    for col, p, label in ((m2, 10, "P90"), (m3, 50, "P50"), (m4, 90, "P10")):
        col.metric(f"{label} column", f"{np.percentile(column, p):,.0f} m", delta_color="off")

    st.caption(
        f"At **{crest:,.0f} m** those are gradients of "
        f"**{np.mean(p_pore) / crest:.3f} bar/m** pore pressure "
        f"({np.mean(p_pore) / crest / seals.EMW_PER_BAR_PER_M:.2f} s.g. equivalent mud weight) and "
        f"**{np.mean(s_hmin) / crest:.3f} bar/m** minimum stress "
        f"({np.mean(s_hmin) / crest / seals.EMW_PER_BAR_PER_M:.2f} s.g.). "
        "Worth reading back: a pore-pressure gradient much above 0.105 bar/m is overpressure, and "
        "overpressure is the whole reason this mechanism ever controls a column."
    )

    # **Say when it cannot bite.** A normally pressured trap at two kilometres has hundreds of bar
    # of headroom, which is thousands of metres of column -- far more than any structure holds. The
    # limit is then correct and irrelevant, and a reader who is not told that will wonder why it
    # never appears in the controlling-limit statistics. It is also the honest reading of Grant's
    # own Figure 5c, where the mechanical seal holds "a long oil column" and nothing else happens.
    relief = _structural_relief_m()
    median = float(np.percentile(column, 50))
    if relief and median > 3.0 * relief:
        st.info(
            f"**This trap is nowhere near its fracture limit.** {headroom:,.0f} bar of headroom is "
            f"about {median:,.0f} m of column, against roughly {relief:,.0f} m of structural "
            f"relief — the mechanism cannot control the contact here and will sit far to the right "
            f"of every other curve on tab 4.0. That is a finding, not a fault: it says the trap "
            f"fails capillary or geometrically, if at all, and never mechanically. It bites in "
            f"overpressured sections, where the headroom is tens of bar rather than hundreds."
        )

    st.plotly_chart(_pressure_depth_figure(crest, np.mean(p_pore), np.mean(s_hmin),
                                           float(np.mean(rho_w)), float(np.mean(rho_hc)), median),
                    width="stretch", key=f"{key}_pd_fig")
    st.caption(
        "**The P50 realisation as a pressure–depth plot**, the frame this mechanism is read in "
        "(Grant 2020, fig. 5c). The aquifer runs through the crest pressure at the water gradient. "
        "The hydrocarbon leg leaves it at the contact and climbs the shallower hydrocarbon "
        "gradient, so the gap between the two lines is buoyancy. The column is the depth at which "
        "that gap has grown enough for the crest pressure to reach `S_Hmin` — where the "
        "hydrocarbon line meets the stress marker. Anything deeper parts the seal."
    )

    return Handover(DepthDistribution.from_samples(column), 1.0,
                    f"headroom {headroom:,.0f} bar at {crest:,.0f} m")


def _structural_relief_m() -> float | None:
    """Apex to spill, from tab 2.0, for the *can this even bite* check. ``None`` if not set yet."""
    apex, spill = st.session_state.get("apex"), st.session_state.get("spill_point")
    if not apex or spill is None:
        return None
    relief = float(spill) - float(np.mean(apex))
    return relief if relief > 0 else None


def _pressure_depth_figure(crest: float, p_pore: float, s_hmin: float,
                           rho_w: float, rho_hc: float, column: float):
    """Aquifer, hydrocarbon leg and the stress limit, on one pressure–depth frame."""
    import plotly.graph_objects as go

    grad_w = rho_w * seals.BAR_PER_M_PER_G_CM3
    grad_h = rho_hc * seals.BAR_PER_M_PER_G_CM3
    # Drawn over the column itself plus a margin, so the geometry is legible whatever its size.
    top, base = crest - 0.15 * max(column, 50.0), crest + 1.15 * max(column, 50.0)
    depths = np.linspace(top, base, 120)

    fig = go.Figure()
    fig.add_scatter(x=p_pore + grad_w * (depths - crest), y=depths, mode="lines", name="Aquifer",
                    line=dict(color=theme.PILLAR_COLOURS["Closure"], width=2))
    contact = crest + column
    leg = np.linspace(crest, contact, 60)
    fig.add_scatter(x=p_pore + grad_w * (contact - crest) - grad_h * (contact - leg), y=leg,
                    mode="lines", name="Hydrocarbon leg",
                    line=dict(color=theme.PILLAR_COLOURS["Retention"], width=3))
    fig.add_scatter(x=[s_hmin], y=[crest], mode="markers+text", name="S_Hmin at the crest",
                    marker=dict(color="#C44E52", size=12, symbol="x"),
                    text=["  S_Hmin"], textposition="middle right")
    fig.add_scatter(x=[p_pore], y=[crest], mode="markers", name="Aquifer at the crest",
                    marker=dict(color=theme.PILLAR_COLOURS["Closure"], size=9))
    fig.add_hline(y=contact, line=dict(color="#8A8A8A", width=1, dash="dot"),
                  annotation_text=f"contact {contact:,.0f} m", annotation_position="top left",
                  annotation_font_size=10)
    fig.update_xaxes(title_text="Pressure (bar)")
    fig.update_yaxes(title_text="Depth (m TVDSS)", range=[base, top], autorange=False)
    fig.update_layout(height=380, margin=dict(t=30, b=20),
                      legend=dict(orientation="h", y=1.16), plot_bgcolor="rgba(0,0,0,0)")
    return fig


def render_mechanical_computed(key: str, n_trials: int, seed: int):
    """The fracture-pressure calculator, for use as a `limit_block` ``computed`` hook."""
    return _as_triple(render_mechanical(key, n_trials, seed))
