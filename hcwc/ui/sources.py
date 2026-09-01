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
import plotly.graph_objects as go
import streamlit as st

from hcwc.core import charge as ch
from hcwc.core import censoring, seals
from hcwc.core.limits import DepthDistribution
from hcwc.io import benchmarks
from hcwc.ui import theme


@dataclass(frozen=True)
class Handover:
    """What a helper gives back to the row that opened it."""
    distribution: DepthDistribution
    p_active: float
    summary: str




# --------------------------------------------------------------------------- charge
def render_charge(key: str, n_trials: int, seed: int) -> Handover | None:
    st.markdown(
        "Gross rock volume from the area–depth table, hydrocarbon pore volume from the reservoir "
        "properties, then the depth at which the accumulated pore volume equals the charge the "
        "basin model delivered."
    )
    try:
        table = ch.AreaDepthTable.reference()
    except FileNotFoundError:
        st.error("`reference/area_depth.csv` is missing from this checkout.")
        return None

    rng = np.random.default_rng(seed + 991)
    c1, c2, c3 = st.columns(3)
    ntg = c1.slider("Net-to-gross", 0.05, 1.0, (0.50, 0.80), key=f"{key}_ntg")
    por = c2.slider("Porosity", 0.02, 0.45, (0.20, 0.30), key=f"{key}_por")
    sat = c3.slider("HC saturation", 0.20, 1.0, (0.50, 0.80), key=f"{key}_sat")

    case = st.selectbox("Phase case", ["Pure oil", "Pure gas"], key=f"{key}_case")
    st.session_state["charge_phase"] = case
    f1, f2, f3 = st.columns(3)
    mean = f1.number_input("Charge mean (10⁶ Sm³)", 0.0, 500_000.0,
                           120.0 if case == "Pure oil" else 39600.0, 1.0, key=f"{key}_mean")
    sd = f2.number_input("Charge sd (10⁶ Sm³)", 0.0, 200_000.0,
                         25.0 if case == "Pure oil" else 5500.0, 1.0, key=f"{key}_sd")
    factor = f3.number_input("Bo (m³/Sm³)" if case == "Pure oil" else "1/Bg (Sm³/m³)",
                             0.01, 500.0, 1.35 if case == "Pure oil" else 235.0, 0.01,
                             key=f"{key}_factor")

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
    st.plotly_chart(fig, use_container_width=True, key=f"{key}_charge_fig")
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
    default_t = _slider_default(
        temperature_range(float(burial)) if burial else (70.0, 90.0), 10.0, 160.0)

    c1, c2, c3 = st.columns(3)
    fluid = c1.selectbox("Fluid", ["Gas", "Oil"], key=f"{key}_fluid")
    st.session_state["seal_fluid"] = fluid
    temp = c2.slider("Temperature (°C)", 10.0, 160.0, default_t, key=f"{key}_t",
                     help=(f"Defaulted from the {burial:,.0f} m burial depth on tab ②, at "
                           f"25–40 °C/km. Override if you have a measured gradient."
                           if burial else "Set a burial depth on tab ② to default this."))
    theta = c3.slider("Contact angle θ (°)", 0.0, 60.0, (0.0, 30.0), key=f"{key}_theta")

    c4, c5 = st.columns(2)
    r_seal = c4.slider("Seal pore-throat radius (µm)", 0.01, 2.0, (0.03, 0.12), 0.01,
                       key=f"{key}_rs",
                       help="The single most sensitive input. A good shale is well below 0.1 µm.")
    r_res = c5.slider("Reservoir pore-throat radius (µm)", 0.1, 10.0, (0.8, 3.0), 0.1,
                      key=f"{key}_rr")

    c6, c7 = st.columns(2)
    rho_w = c6.slider("Water density (g/cm³)", 0.95, 1.20, (1.00, 1.10), 0.01, key=f"{key}_rw")
    rho_hc = c7.slider("HC density (g/cm³)", 0.10, 1.00, (0.70, 0.85), 0.01, key=f"{key}_rh")
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
            st.info("Set a burial depth on tab ② to draw the NCS capacity for this prospect.")
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
    st.plotly_chart(fig, use_container_width=True, key=f"{key}_seal_fig")
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
            use_container_width=True, key=f"{key}_calib")
    return Handover(DepthDistribution.from_samples(capacity), 1.0,
                    f"{fluid}, r {r_seal[0]:.2f}–{r_seal[1]:.2f} µm")


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
        "mass. Use it as a prior only where nothing better exists — tab ⑥ sets out what it is and "
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
    _area_depth_panel()
    return _as_triple(render_charge(key, n_trials, seed))


def render_empirical_computed(key: str, n_trials: int, seed: int):
    """The censoring-corrected NCS fit, for use as a `limit_block` ``computed`` hook."""
    return _as_triple(render_empirical(key, n_trials, seed))


def render_seal_computed(key: str, n_trials: int, seed: int):
    """The seal-capacity calculator, for use as a `limit_block` ``computed`` hook."""
    return _as_triple(render_seal(key, n_trials, seed))


#: The key prefix `limiters_tab` gives the top seal's block. The base seal reads its widgets from
#: here rather than owning a second copy, which is the whole point of the *same as top* source.
TOP_SEAL_KEY = "lim_Top seal (capillary)"


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
    m1, m2, m3 = st.columns(3)
    m1.metric("P90 capacity", f"{np.percentile(capacity, 10):,.0f} m")
    m2.metric("P50 capacity", f"{np.percentile(capacity, 50):,.0f} m")
    m3.metric("P10 capacity", f"{np.percentile(capacity, 90):,.0f} m")
    st.caption(
        "⚠ **Identical inputs are not an identical outcome, and the difference is on the "
        "Correlations sub-tab.** Sampled independently, top and base seal fail at different "
        "columns in the same realisation, which is a claim that one shale can be tight above and "
        "leaky below at the same moment. If it is one unit, correlate them — the pairing is "
        "already listed there, waiting for a number."
    )
    return Handover(DepthDistribution.from_samples(capacity), 1.0,
                    f"as top seal — {read('fluid').lower()}, "
                    f"r {read('rs')[0]:.2f}–{read('rs')[1]:.2f} µm")


def render_seal_as_top_computed(key: str, n_trials: int, seed: int):
    """`render_seal_as_top`, for use as a `limit_block` ``computed`` hook."""
    return _as_triple(render_seal_as_top(key, n_trials, seed))


def _area_depth_panel() -> None:
    """Top and base reservoir area against depth, and the rock volume between them."""
    try:
        table = ch.AreaDepthTable.reference()
    except FileNotFoundError:
        st.error("`reference/area_depth.csv` is not in this checkout, so the charge "
                 "calculator cannot run.")
        return

    st.markdown(
        "**The structure the charge has to fill.** Gross rock volume is the trapezoidal integral "
        "of *top area minus base area* — km2 x m is 1e6 m3, so no conversion factor is needed."
    )
    s1, s2, s3 = st.columns(3)
    s1.metric("Apex of the mapped surface", f"{table.apex_m:,.0f} m")
    s2.metric("Deepest mapped", f"{table.deepest_m:,.0f} m")
    s3.metric("Gross rock volume", f"{table.capacity_1e6m3:,.0f} x10^6 m3")

    fig = go.Figure()
    fig.add_scatter(x=table.top_area_km2, y=table.depths_m, mode="lines", name="top reservoir",
                    line=dict(color=theme.PILLAR_COLOURS["Closure"], width=2.5))
    fig.add_scatter(x=table.base_area_km2, y=table.depths_m, mode="lines", name="base reservoir",
                    line=dict(color=theme.PILLAR_COLOURS["Reservoir"], width=2.5))
    fig.update_layout(xaxis_title="Area (km2)", yaxis_title="Depth (m TVDSS)",
                      yaxis=dict(autorange="reversed"), height=340, margin=dict(t=10),
                      legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True, key="area_depth_charge")


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
