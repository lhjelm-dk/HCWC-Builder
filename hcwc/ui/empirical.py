"""Tab 5.0 — the empirical basis: the statistics and the benchmark comparison, together.

These were two tabs and are now one, because they were never two subjects. The benchmark comparison
*is* the statistics: you cannot sensibly plot a prospect against the published dataset without
having settled what that dataset measures, and settling that is the whole of the statistics
argument. Splitting them put the caveat on one tab and the use of the data on another, which is
exactly how a caveat gets ignored.

Tone is part of the content. Edmundson et al. did the hard part — apex and spill picked from
depth-converted maps for 242 discoveries across three regions — and **published the raw table under
CC-BY**, which is rare and is the only reason any of this is checkable. The tab says so before it
says anything else, and shows both analyses side by side throughout. A reader should be able to
disagree with us and still use the tab.

**On "trap" versus "closure".** Edmundson's measured variable is *trap height* and that is what the
published data, the published figures and the quoted r-values call it, so it keeps that name here.
Our own risk element is *Closure*, matching the pillar name in E-POS. They are the same measurement
— apex to spill — under two names, and the tab says so once at the top rather than leaving a
reader to wonder.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hcwc.core import dhi as dhi_core
from hcwc.core import engine
from hcwc.io import benchmarks
from hcwc.ui import theme
from hcwc.ui.numbering import Numbering

TAB = 6

UNDERFILLED = "#4C72B0"
CENSORED = "#C44E52"
FITTED = "#55A868"
PUBLISHED = "#8172B2"
PROSPECT = "#DD8452"
#: Plotly rejects 8-digit hex for fillcolor, so the translucent form is spelled out.
PROSPECT_FILL = "rgba(221, 132, 82, 0.35)"

#: How many points a violin is drawn from. The shape is a kernel density and settles long before
#: this; the percentile rules beside it are still read off the full sample.
VIOLIN_POINTS = 3_000


# The fits, the samplers and the probit axis moved to `empirical_data`; what stays here draws.
# Imported by name rather than as a module so the call sites below did not have to change — there
# are forty of them and a rename would have been forty chances to miss one.
from hcwc.ui.empirical_data import (  # noqa: E402
    CLOSURE_FAMILY, PROBIT_CLIP, PROBIT_TICKS, _bias_curve, _empirical_prior, _exceedance,
    _fit, _load, _p_spill, _probit, _samples_for, imported_label,
)

def _add_prospect_violin(fig, x: float, samples: np.ndarray, width: float,
                         *, name: str = "this prospect — empirical prior",
                         colour: str = PROSPECT, fill: str = PROSPECT_FILL) -> None:
    """One column-height distribution, drawn into the population cross-plot at ``x``.

    Used for all three things worth putting there: what the statistics predict for a closure of
    these dimensions, what the competing-limits model produced, and what the amplitude did to it.
    Same axis, same units, so they can be read against each other and against the record behind
    them.
    """
    if samples is None or not len(samples):
        return
    # **Thinned before it is sent.** A violin is a kernel density that plotly computes in the
    # browser from the raw points, so the whole sample crosses the wire: forty thousand for the
    # empirical prior and ten thousand for each model, twice over on two figures. The percentile
    # rules below are taken from the *full* sample, so the numbers a reader quotes are unchanged;
    # only the shape is drawn from a subsample, and a violin's shape is settled long before three
    # thousand points.
    samples = np.asarray(samples, dtype=float)
    if samples.size > VIOLIN_POINTS:
        step = samples.size // VIOLIN_POINTS
        drawn = np.sort(samples)[::step]
    else:
        drawn = samples
    fig.add_violin(x=np.full(drawn.size, x), y=drawn, width=width, side="both",
                   points=False, line_color=colour, fillcolor=fill,
                   name=name, hoverinfo="skip", spanmode="hard")
    for pct, dash in ((90, "dot"), (50, "solid"), (10, "dot")):
        v = float(engine.weighted_percentiles(samples, None, float(pct))[0])
        fig.add_scatter(x=[x - width / 2, x + width / 2], y=[v, v], mode="lines",
                        line=dict(color=colour, width=2, dash=dash),
                        showlegend=False, hovertext=f"{name} · P{pct} = {v:.0f} m",
                        hoverinfo="text")


def _model_columns() -> tuple["np.ndarray | None", "np.ndarray | None"]:
    """The built column distribution, geological and given the DHI, or ``None`` for each.

    Success cases only, to match the empirical prior: every discovery in the record had
    hydrocarbons in it, so comparing the whole geological sample against it would put realisations
    that never made a discovery beside a population of discoveries.
    """
    limit_set = st.session_state.get("limit_set")
    if limit_set is None:
        return None, None
    from hcwc.ui import run as engine_run

    result = engine_run.current(limit_set)
    keep = result.above_minimum
    geological = result.column_m[keep] if keep.any() else None

    given_dhi = None
    overlay = st.session_state.get("dhi_overlay")
    posterior = st.session_state.get("dhi_posterior")
    if overlay is not None and posterior is not None:
        apex = float(np.median(posterior.result.apex_m))
        given_dhi = np.asarray(overlay["contact_samples"], dtype=float) - apex
    return geological, given_dhi


def _overlay_models(fig, x: float, width: float) -> list[str]:
    """Draw the built distributions beside the empirical one. Returns what was drawn."""
    geological, given_dhi = _model_columns()
    drawn: list[str] = []
    if geological is not None:
        _add_prospect_violin(fig, x - 0.62 * width, geological, width * 0.55,
                             name="this prospect — geological (tab 4.0)",
                             colour=theme.BASIS_COLOUR[theme.GEOLOGICAL],
                             fill=theme.rgba(theme.BASIS_COLOUR[theme.GEOLOGICAL], 0.30))
        drawn.append("geological")
    if given_dhi is not None:
        _add_prospect_violin(fig, x + 0.62 * width, given_dhi, width * 0.55,
                             name=f"this prospect — {theme.evidence_basis()} (tab 5.0)",
                             colour=theme.BASIS_COLOUR[theme.GIVEN_DHI],
                             fill=theme.rgba(theme.BASIS_COLOUR[theme.GIVEN_DHI], 0.30))
        drawn.append(theme.evidence_basis())
    return drawn


def dhi_columns(n_draw: int = 10_000) -> "np.ndarray | None":
    """This prospect's column distribution **given the evidence**, success cases only, or ``None``.

    Section 8 compared the record against the geological model and nothing else -- Decision:
    *"it looks like it is only the geological that is being compared to stats. I want both."* He is
    right that it is the more interesting comparison: the geological model is what the limits allow,
    and the updated one is what the limits allow *after the amplitude or the well has spoken*. A
    calibration exercise that never sees the second is checking half the tool.

    **Resampled from the column array, not reconstructed from contacts.** The overlay carries
    `contact_samples`, and subtracting a median apex from those is off by however much the apex
    varies -- which is exactly the quantity tab 4.0 spends a section on. The engine already holds
    `column_m` per realisation, so the posterior columns are that array importance-resampled under
    the same weights, with no apex arithmetic anywhere.

    Success cases only, because every trap in every benchmark on this tab is a discovery.
    """
    posterior = st.session_state.get("dhi_posterior")
    if posterior is None:
        return None
    drawn = dhi_core.posterior_columns(posterior, int(n_draw))
    return drawn if drawn.size else None


def _render_import() -> None:
    """Load a column-height dataset of your own, and use it as a fourth benchmark family.

    **Nothing leaves the session.** The file is parsed in memory, fitted in memory, and gone when
    the browser tab closes: no cache file, no upload, no network call. That is asserted in
    ``tests/test_datasets.py`` against the source of :mod:`hcwc.io.datasets`, because the property
    worth protecting is that nobody adds a cache later without noticing what it would mean.
    """
    from hcwc.io import datasets

    with st.expander("Load a dataset: raw discoveries, fitted here, never stored",
                     expanded=st.session_state.get("imported_dataset") is None):
        st.markdown(
            "One row per discovery, two columns required: a closure height and a hydrocarbon "
            "column height, in metres. The reader accepts the usual spellings: `trap_height_m`, "
            "`closure_height`, `relief_m` for the first; `hc_column_m`, `column_height`, "
            "`hcwc_height` for the second.\n\n"
            "Optional columns. `burial_depth_m` makes the fit a two-predictor model rather than "
            "a one-predictor one; `apex_depth_m` stands in for it where absent. "
            "`filled_to_spill` is used directly if present and derived at "
            f"{datasets.FILLED_RULE:.0%} of the closure if not. That flag is what the correction "
            "turns on, because a filled trap measures the closure rather than the seal.\n\n"
            "Raw rows rather than a fitted curve, because the censoring correction runs here. A "
            "fitted shape from elsewhere carries its author's answer to their question; the "
            "discoveries themselves carry the finding on these."
        )
        c1, c2 = st.columns(2)
        name = c1.text_input("Name it", key="import_name", placeholder="e.g. internal fields, 2026")
        source = c2.text_input("Source", key="import_source",
                               placeholder="citation, internal reference, or 'unknown'")
        upload = st.file_uploader(
            "Dataset (.csv)", type=["csv"], key="import_upload",
            help="One row per discovery, with a closure height and a hydrocarbon column height "
                 "under any of the spellings the reader accepts. Comma-separated, up to 10 000 "
                 "rows. Nothing imported is written to disk or sent anywhere; it lives in this "
                 "browser session only.")

        if upload is not None:
            try:
                loaded = datasets.read_csv(upload.getvalue(),
                                           name=name or upload.name.rsplit(".", 1)[0],
                                           source=source)
            except datasets.DatasetError as exc:
                st.session_state.pop("imported_dataset", None)
                st.error(f"The file cannot be read as a column-height dataset. {exc}")
            else:
                st.session_state["imported_dataset"] = loaded
                st.success(
                    f"{loaded.name}: {len(loaded.usable):,} usable rows of {loaded.n:,}, "
                    f"{loaded.censored_fraction:.0%} filled to spill, fitted on "
                    + (" and ".join(x.replace("_", " ") for x in loaded.predictors)) + ".")
                if loaded.notes:
                    st.warning("Assumptions the reader made. Each is a decision taken without "
                               "being asked:\n\n"
                               + "\n\n".join(f"- {note}" for note in loaded.notes))
        elif st.session_state.get("imported_dataset") is not None:
            if st.button("Forget the loaded dataset", key="forget_import"):
                st.session_state.pop("imported_dataset", None)
                st.rerun()


def render() -> None:
    n = Numbering(TAB)
    h, c, z, filled = _load()
    fit, naive = _fit()

    st.subheader("The empirical basis, and how it is analysed")
    st.markdown(
        """
Edmundson et al. (2021) assembled 242 measured discoveries across the Norwegian Continental
Shelf, each with an apex and a spill point picked from depth-converted maps, and published the
raw table under CC-BY 4.0. What follows differs from the published analysis in one estimator,
not in the data. Edmundson's trap height is this tool's closure height, one measurement under
two names; their term is kept where their data are quoted. Method: see 8.1.9.
"""
    )

    # ------------------------------------------------------------------ 0 · the dataset
    theme.heading(TAB, "1 · The dataset")
    n.table(
        pd.DataFrame({
            "Property": ["Discoveries", "Filled to spill (right-censored)",
                         "Measuring seal capacity", "Closure height range",
                         "Burial depth range", "Licence", "Source"],
            "Value": [f"{len(h)}", f"{filled.sum()} ({filled.mean():.1%})", f"{(~filled).sum()}",
                      f"{h.min():.0f} – {h.max():.0f} m", f"{z.min():.0f} – {z.max():.0f} m",
                      "CC-BY 4.0", "osf.io/6ysbv"],
        }),
        "The Edmundson et al. (2021) NCS dataset, as shipped in `reference/`. Their published "
        "probability matrix reproduces from these rows exactly.",
    )

    # ------------------------------------------------------------------ the prospect
    theme.heading(TAB, "2 · The prospect against the population")
    st.markdown(
        "The closure height and burial depth place the prospect in the population. The orange "
        "distribution is what the NCS data predicts for a closure of these dimensions: seal "
        "capacity drawn from the censoring-corrected fit, then capped at the closure, which is the "
        "same `min(S, H)` the geology applies. It is the empirical prior the engine's output is "
        "compared against."
    )
    ca, cb, cc = st.columns([1, 1, 2])
    closure = ca.number_input("Closure height (m)", 20.0, 1500.0, 350.0, 10.0,
                              help="Apex to spill. Edmundson calls this trap height; it is the "
                                   "same measurement. Their data spans 14–715 m.")
    burial = cb.number_input("Burial depth (m)", 200.0, 6000.0, 2050.0, 50.0,
                             help="Overburden thickness to the reservoir. Needed because the "
                                  "corrected fit finds burial depth to be a much stronger control "
                                  "than the published analysis reported; see Table 6.3a.")
    prior = _empirical_prior(closure, burial)
    # **On by arrival.**  The empirical prior on its own is a statement about the
    # NCS record; the comparison is the reason anyone is on this tab, and a toggle defaulting off
    # made the more interesting of the two figures the one you had to know to ask for.
    show_models = st.toggle(
        "Draw what this tool produced beside it", value=True, key="empirical_show_models",
        help="Adds the geological contact distribution from tab 4.0, and the DHI-updated one from "
             "tab 5.0 where there is one, as violins next to the empirical prior. All three are "
             "column height in metres and all three are conditional on the assessment minimum, so they are directly "
             "comparable, and they are compared against the discoveries the fit was made on "
             "rather than against each other in the abstract.")
    cc.metric("Empirical prior, P50 column",
              f"{engine.weighted_percentiles(prior, None, 50.0)[0]:.0f} m",
              f"P90 {engine.weighted_percentiles(prior, None, 90.0)[0]:.0f} m · "
              f"P10 {engine.weighted_percentiles(prior, None, 10.0)[0]:.0f} m",
              delta_color="off")

    show = st.radio("Regression shown", ["Both", "As published (OLS)",
                                         "Censoring-corrected (MLE)"], horizontal=True)

    # -------- Figure: their Fig 6A equivalent -------------------------------------------
    figA = go.Figure()
    figA.add_scatter(x=h[~filled], y=c[~filled], mode="markers",
                     name="underfilled — observes the seal",
                     marker=dict(size=7, opacity=0.7, color=UNDERFILLED))
    figA.add_scatter(x=h[filled], y=c[filled], mode="markers",
                     name="filled to spill — observes the closure (censored)",
                     marker=dict(size=7, opacity=0.8, color=CENSORED, symbol="diamond"))
    lim = float(h.max()) * 1.05
    figA.add_scatter(x=[0, lim], y=[0, lim], mode="lines", name="1:1 — filled to spill",
                     line=dict(dash="dash", color="#555", width=1))
    grid = np.linspace(float(h.min()), float(h.max()), 80)
    slope, intercept = np.polyfit(h, c, 1)
    ols_r = float(np.corrcoef(h, c)[0, 1])
    ols_cross = intercept / (1.0 - slope) if slope < 1.0 else None

    # A censored fit has no ordinary R². This is the correlation between what the model predicts
    # and what was observed, over the **uncensored** discoveries only — the ones whose column is a
    # measurement of seal capacity rather than of the closure. Including the filled-to-spill points
    # would flatter it, because the model is not trying to predict those.
    fitted_all = np.exp(fit.intercept + fit.coefficients["trap_height"] * np.log(h)
                        + fit.coefficients["burial_depth"] * np.log(z))
    mle_r = float(np.corrcoef(fitted_all[~filled], c[~filled])[0, 1])

    if show in ("Both", "As published (OLS)"):
        figA.add_scatter(x=grid, y=intercept + slope * grid, mode="lines",
                         name=f"published OLS (r = {ols_r:.2f})",
                         line=dict(color=PUBLISHED, width=3))
    if show in ("Both", "Censoring-corrected (MLE)"):
        median_z = float(np.median(z))
        pred = np.exp(fit.intercept + fit.coefficients["trap_height"] * np.log(grid)
                      + fit.coefficients["burial_depth"] * np.log(median_z))
        figA.add_scatter(x=grid, y=pred, mode="lines",
                         name=f"censored MLE — median seal capacity (r = {mle_r:.2f})",
                         line=dict(color=FITTED, width=3))
    _add_prospect_violin(figA, closure, prior, width=45.0)
    if show_models:
        _overlay_models(figA, closure, 45.0)
    # Column height increases downward: a column is a depth below the apex,
    # and every other depth axis in the tool reads that way.
    figA.update_layout(xaxis_title="Closure height (m)",
                       yaxis=dict(title="Hydrocarbon column height (m)", autorange="reversed"),
                       height=560, legend=dict(orientation="h", y=-0.16), margin=dict(t=20))
    n.plot(figA, "Column height against closure height, after Edmundson et al. Fig. 6A. Red "
                 "diamonds lie on the 1:1 line by definition: they record the closure, not the "
                 "seal. The censored fit sits below the OLS line because it estimates seal "
                 "capacity rather than the observed column. Both `r` values are correlations with "
                 "the observed column; the MLE's is computed over the uncensored discoveries "
                 "only, since those are the ones it predicts. Both lines cross the 1:1 at the "
                 "left-hand end; the note below gives the two crossings.")

    # Computed, not typed. These were hard-coded as "63 %", "35 %" and "144 m" inside an f-string
    # whose crossing was already being calculated a line above -- so the prose could drift away from
    # the figure without anything failing, and by the time it was checked it had: the real split is
    # 62/36. Anything quoted here is now derived from the same fit the line is drawn from.
    mle_cross = float(np.exp(fit.intercept + fit.coefficients["burial_depth"]
                             * np.log(float(np.median(z))))
                      ** (1.0 / (1.0 - fit.coefficients["trap_height"])))
    below, above = h < mle_cross, h >= mle_cross
    with st.expander("Both lines cross the 1:1 line, and the two crossings mean different things"):
        st.info(
            f"The censored MLE crossing is a prediction: seal capacity may exceed the closure, "
            f"and above the 1:1 line the model says the closure will fill. It crosses at "
            f"{mle_cross:.0f} m, and in the data {filled[below].mean():.0%} of closures below "
            f"that filled to spill against {filled[above].mean():.0%} above.\n\n"
            f"The published OLS crossing is an artefact of fitting a line to a bounded quantity: "
            f"below {ols_cross:.0f} m it predicts a column the data cannot contain, and "
            f"{int((h < ols_cross).sum())} of {h.size} discoveries ({(h < ols_cross).mean():.0%}) "
            f"sit there; its intercept is {intercept:+.0f} m. Kept as published. Method: see "
            f"8.1.9."
        )

    # -------- Figure: their Fig 6B equivalent -------------------------------------------
    figB = go.Figure()
    figB.add_scatter(x=z[~filled], y=c[~filled], mode="markers", name="underfilled",
                     marker=dict(size=7, opacity=0.7, color=UNDERFILLED))
    figB.add_scatter(x=z[filled], y=c[filled], mode="markers", name="filled to spill (censored)",
                     marker=dict(size=7, opacity=0.8, color=CENSORED, symbol="diamond"))
    zgrid = np.linspace(float(z.min()), float(z.max()), 80)
    if show in ("Both", "As published (OLS)"):
        s2, i2 = np.polyfit(z, c, 1)
        figB.add_scatter(x=zgrid, y=i2 + s2 * zgrid, mode="lines", name="published OLS (r = 0.31)",
                         line=dict(color=PUBLISHED, width=3))
    if show in ("Both", "Censoring-corrected (MLE)"):
        pred2 = np.exp(fit.intercept + fit.coefficients["trap_height"] * np.log(float(np.median(h)))
                       + fit.coefficients["burial_depth"] * np.log(zgrid))
        figB.add_scatter(x=zgrid, y=pred2, mode="lines", name="censored MLE — median seal capacity",
                         line=dict(color=FITTED, width=3))
    _add_prospect_violin(figB, burial, prior, width=260.0)
    if show_models:
        _overlay_models(figB, burial, 260.0)
    figB.update_layout(xaxis_title="Burial depth (m)",
                       yaxis=dict(title="Hydrocarbon column height (m)", autorange="reversed"),
                       height=560, legend=dict(orientation="h", y=-0.16), margin=dict(t=20))
    n.plot(figB, "Column height against burial depth, after Edmundson et al. Fig. 6B. This is "
                 "the panel where the two analyses disagree most: the corrected fit is roughly "
                 "twice as steep, because censoring suppressed the depth signal.")

    # ------------------------------------------------------------------ the issue
    # Sections 3 to 5 argue for the METHOD rather than about the reader's prospect, and they
    # were about half of the longest tab in the app -- sitting between "here is the data" and
    # "here is your prospect against it", which is the line a reader actually wants to walk.
    # Folded rather than moved to a document: they are live figures computed from the data, and
    # a static page would lose the calibration plot and the bias curve, which ARE the evidence.
    with st.expander("The correction: what the published fit measures, whether the corrected one "
                     "holds, and the bias it does not remove", expanded=False):
        st.caption(
            "Three sections on the estimator rather than on the prospect, kept so the correction "
            "can be checked and folded so a first pass can go past them."
        )
        theme.heading(TAB, "3 · What the published regression measures")
        st.markdown(
            """
    The quantity a pre-drill model needs is seal capacity `S`, the column the seal could hold. What
    is measured is the column that is there, and the two differ by the identity the tool is built on:

    ```
    observed column  C = min(S, H)          H = closure height
    ```

    * Underfilled (`C < H`): the seal bound the column, so `C = S`. Seal capacity is observed.
    * Filled to spill (`C = H`): geometry bound it. All that is learned is `S ≥ H`. The observation
      is right-censored; the seal's capacity was not tested.

    111 of 242 rows, 46 %, are of the second kind. Method: see 8.1.9.
    """
        )

        n.markdown_table(
            f"""
    | Log-log elasticity | As published (OLS) | Censoring-corrected (MLE) | |
    |---|---:|---:|---|
    | Closure height | {naive[1]:.3f} | {fit.coefficients['trap_height']:.3f} | overstated |
    | Burial depth | {naive[2]:.3f} | {fit.coefficients['burial_depth']:.3f} | understated; roughly doubles |
    """,
            "Censoring biases the two in opposite directions, which is why fitting them one at a "
            "time does not reveal it. Closure height and burial depth are close to uncorrelated "
            "here (r = 0.085), so this is not confounding. Both terms are significant by likelihood "
            "ratio (p = 8e-19 and p = 5e-4).",
        )

        st.markdown(
            "Corrected, closure height matters less than published and burial depth roughly "
            "twice as much. Method: see 8.1.9."
        )

        with st.expander("Why not simply drop the filled-to-spill points?"):
            st.markdown(
                """
    Dropping them trades censoring bias for truncation bias. Simulated with seal capacity
    independent of closure height, 242 points to match:

    | Estimator | Slope (truth = 0.000) |
    |---|---:|
    | Naive OLS, all points | 0.580 |
    | OLS after dropping filled-to-spill | 0.543 |
    | Censored MLE | −0.009 |

    Only the censored likelihood recovers the truth (`tests/test_censoring.py`). Method: see
    8.1.9.
    """
            )

        # ------------------------------------------------------------------ calibration
        theme.heading(TAB, "4 · Does the corrected model fit?")
        bands = [(0, 150), (150, 250), (250, 400), (400, 10**9)]
        labels, obs, mod, ns = [], [], [], []
        for lo, hi in bands:
            m = (h >= lo) & (h < hi)
            labels.append(f"{lo}–{hi} m" if hi < 10**8 else f"> {lo} m")
            obs.append(float(filled[m].mean()))
            mod.append(float(np.mean([_p_spill(fit, hh, zz) for hh, zz in zip(h[m], z[m])])))
            ns.append(int(m.sum()))
        cal = go.Figure()
        cal.add_bar(x=labels, y=obs, name="observed fill-to-spill rate", marker_color=CENSORED,
                    text=[f"n={v}" for v in ns], textposition="outside")
        cal.add_bar(x=labels, y=mod, name="predicted by the censored model", marker_color=FITTED)
        cal.update_layout(barmode="group", yaxis_title="P(filled to spill)", height=380,
                          yaxis_range=[0, 0.8], legend=dict(orientation="h", y=-0.2),
                          margin=dict(t=20), xaxis_title="Closure height")
        n.plot(cal, "Calibration by closure-height band. The fitted model reproduces the observed "
                    "fill rate throughout, which is what validates the parametric form.")

        st.caption(
            f"Graham et al.'s global 40 % is a population average over closures below 250 m; on "
            f"the same basis the NCS gives {filled[h < 250].mean():.0%}, a regional difference, "
            f"since the NCS is charge-rich. Method: see 8.1.9."
        )

        theme.heading(TAB, "5 · A second bias, which the correction does not remove")
        st.markdown(
            """
    The corrected closure-height elasticity is still about 0.70, higher than a rock property should
    be. The reason is measurement rather than selection:

    ```
    column  height = contact − apex
    closure height = spill   − apex        ← the same apex pick
    ```

    A depth-conversion error moves both the same way and manufactures a relationship no censored
    estimator can see. Method: see 8.1.9.
    """
        )
        sigmas = (0.0, 10.0, 25.0, 50.0, 75.0, 100.0)
        nv, cn = _bias_curve(sigmas)
        bias = go.Figure()
        bias.add_scatter(x=list(sigmas), y=nv, mode="lines+markers", name="naive OLS",
                         line=dict(color=PUBLISHED, width=3))
        bias.add_scatter(x=list(sigmas), y=cn, mode="lines+markers", name="censored MLE",
                         line=dict(color=FITTED, width=3))
        bias.add_hline(y=0.0, line=dict(dash="dash", color="#555"),
                       annotation_text="truth — no relationship at all", annotation_position="top left")
        bias.add_vrect(x0=25, x1=75, fillcolor=CENSORED, opacity=0.10, line_width=0,
                       annotation_text="typical NCS depth conversion, 1–3 % of 2 500 m",
                       annotation_position="top right")
        bias.update_layout(xaxis_title="Apex pick error σ (m)",
                           yaxis_title="Estimated closure-height elasticity", height=400,
                           legend=dict(orientation="h", y=-0.2), margin=dict(t=20))
        n.plot(bias, f"Spurious elasticity from a shared apex pick, on data with no true "
                     f"relationship. At 50 m, 2 % at 2 500 m and ordinary depth conversion, the "
                     f"censored estimator returns about 0.58. The fitted "
                     f"{fit.coefficients['trap_height']:.2f} is therefore an upper bound rather than "
                     f"an estimate. The burial-depth result survives this: the same absolute error is "
                     f"about 25 % of a 200 m closure and about 2 % of a 2 500 m burial depth.")

        # ------------------------------------------------------------------ benchmark families
    theme.heading(TAB, "6 · The benchmark families")
    imported = st.session_state.get("imported_dataset")
    n.table(
        pd.DataFrame({
            "Benchmark": ["Edmundson (2021) — NCS", "Graham et al. (2015) — global",
                          imported.name if imported else "imported data"],
            "Size": ["242 discoveries, per-observation", "not stated; parameters only",
                     f"{len(imported.usable):,} usable of {imported.n:,}" if imported
                     else "none loaded"],
            "Stratified by": ["burial depth × closure height", "closure height band",
                              "burial × closure" if imported and imported.full_model
                              else "closure height" if imported else "—"],
            "Status": ["open, CC-BY 4.0", "abstract only — distributions never published",
                       f"source: {imported.source}" if imported else "load one below"],
        }),
        "Kept separate rather than merged into one empirical prior: they are conditioned "
        "differently and disagree informatively.",
    )
    st.markdown("The measured dataset is Norwegian, and there is no second one; a prospect "
                "outside the NCS is compared against Norwegian rock, and an in-house trap-fill "
                "database, loaded below, is the only way to a benchmark conditioned on its own "
                "basin. Method: see 8.1.9.")
    _render_import()

    # ------------------------------------------------------------------ family curves
    theme.heading(TAB, "7 · The prior a benchmark gives")
    st.markdown(
        "Column height runs down the page and relief picks the curve. Each curve reads: for a "
        "closure of this relief, the probability that the column is at least this tall. The "
        "horizontal step at the bottom of each curve is the filled-to-spill probability mass, a "
        "point mass rather than a tail. Method: see 8.1.9."
    )

    options = ["NCS, censoring-corrected", "NCS, as the paper fits it", "Graham et al. (2015)"]
    imported = st.session_state.get("imported_dataset")
    if imported is not None:
        options.append(imported_label(imported))

    f1, f2, f3 = st.columns([2, 1, 1])
    source = f1.radio(
        "Benchmark", options, horizontal=True,
        help="The second option is the paper's own naive fit, drawn on the same axes. The gap "
             "between it and the first is what the correction is worth to the deliverable, rather "
             "than to a coefficient.")
    burial = f2.number_input("Burial depth (m)", 500.0, 6000.0, 2500.0, 100.0,
                             key="family_burial",
                             disabled=source == "Graham et al. (2015)"
                             or (imported is not None and source == imported_label(imported)
                                 and not imported.full_model),
                             help="Graham is stratified by closure height only, so its curve does "
                                  "not move with depth. The NCS fits use burial depth, and so "
                                  "does an imported dataset that carries one \u2014 disabled here when "
                                  "it does not.")
    scale = f3.radio(
        "Probability scale", ["Linear", "Probit"], horizontal=True, key="family_scale",
        help="Probit plots the normal score of the probability, so a lognormal column-height "
             "distribution becomes a straight line. Curvature then means departure from "
             "lognormal, and the tails stop being squashed against the top and bottom.")
    probit = scale == "Probit"

    def _y(p):
        """Every probability on this figure goes through here, so none can miss the transform."""
        return _probit(p) if probit else p


    samples = _samples_for(source, CLOSURE_FAMILY, float(burial))
    grid = np.linspace(0.0, max(CLOSURE_FAMILY), 400)
    shades = theme.element_shades("Closure", len(CLOSURE_FAMILY))

    fam = go.Figure()
    for colour, closure in zip(shades, CLOSURE_FAMILY):
        drawn = samples[closure]
        spill = float(np.mean(drawn >= closure - 1e-9))
        inside = grid[grid < closure]
        fam.add_scatter(x=inside, y=_y(_exceedance(drawn, inside)), mode="lines",
                        name=f"{closure:,.0f} m closure",
                        line=dict(color=colour, width=2.5))
        # The drop: the curve does not decay to zero, it stops, and the height of the stop is the
        # filled-to-spill mass. Dashed so it reads as a discontinuity rather than as data.
        fam.add_scatter(x=[closure, closure], y=_y([spill, PROBIT_CLIP]), mode="lines",
                        showlegend=False,
                        line=dict(color=colour, width=2.0, dash="dot"),
                        hovertemplate=f"fills to spill: {spill:.0%}<extra></extra>")
        fam.add_scatter(x=[closure], y=_y([spill]), mode="markers", showlegend=False,
                        marker=dict(color=colour, size=8),
                        hovertemplate=f"{closure:,.0f} m closure<br>"
                                      f"fills to spill: {spill:.0%}<extra></extra>")
    # The prospect you have actually built, on the same axes as the benchmark it is being judged
    # against. Without it the reader has to carry a number across two tabs and compare it by eye.
    limit_set = st.session_state.get("limit_set")
    own_relief = None
    if limit_set is not None:
        from hcwc.ui import run as engine_run
        built = engine_run.current(limit_set)
        column = built.column_m
        built_grid = np.linspace(0.0, float(np.max(column)), 300)

        # The benchmark curve at **this prospect's own** structural relief. Without it the reader
        # is invited to compare a 350 m closure against whichever of the six family curves happens
        # to be nearest, which is the wrong comparison and an easy one to make by accident.
        apex_mid = float(np.mean(st.session_state.get("apex", (2049.0, 2051.0))))
        own_relief = float(st.session_state.get("spill_point", apex_mid + 350.0)) - apex_mid
        if own_relief > 0:
            matched = _samples_for(source, (round(own_relief, 1),), float(burial))
            if matched:
                drawn = next(iter(matched.values()))
                fam.add_scatter(x=built_grid, y=_y(_exceedance(drawn, built_grid)), mode="lines",
                                name=f"benchmark at this prospect's relief ({own_relief:,.0f} m)",
                                line=dict(color="#555555", width=3, dash="dash"))

        # The DHI-updated distribution, when there is one. Drawn so both are seen
        # against the data; the caption carries why the comparison is weaker than the geological
        # one, since the benchmarks cannot be conditioned the same way.
        # Column space, as the benchmarks are: F_post(h) from the posterior itself, the same
        # normalisation as the geological curve beside it. Until 21 Sep 2026 this read the
        # depth-space chance curve back into columns through one apex and divided by the
        # headline, which normalised it to one at h_min where the geological curve was not.
        _posterior = st.session_state.get("dhi_posterior")
        if _posterior is not None and st.session_state.get("dhi_on"):
            fam.add_scatter(
                x=built_grid,
                y=_y(np.asarray(_posterior.exceedance(built_grid), dtype=float)),
                # Same weight and style as the geological curve, different colour. They are two
                # readings of the same prospect and the question is which is deeper -- a dotted
                # line reads as provisional or as a construction line, which this is not.
                mode="lines", name=f"this prospect, {theme.evidence_basis()}",
                line=dict(color=theme.BASIS_COLOUR[theme.GIVEN_DHI], width=4.5))

        fam.add_scatter(x=built_grid, y=_y(_exceedance(column, built_grid)), mode="lines",
                        name="this prospect, geological",
                        line=dict(color=PROSPECT, width=4.5))
        fam.add_scatter(x=[float(np.median(column))], y=_y([0.5]), mode="markers",
                        showlegend=False,
                        marker=dict(color=PROSPECT, size=11, symbol="diamond"),
                        hovertemplate="built P50 %{x:,.0f} m<extra></extra>")

    # Column height down the page and probability across, so the family
    # reads like every other exceedance figure in the tool. The traces were built with the
    # column on x; they are transposed here in one place rather than at each of the nine sites.
    for _trace in fam.data:
        _trace.x, _trace.y = _trace.y, _trace.x
    fam.update_layout(xaxis_title="Probability the column is at least this tall",
                      yaxis=dict(title="Hydrocarbon column (m)", autorange="reversed"),
                      height=700, margin=dict(t=20),
                      legend=dict(orientation="v", x=1.02, y=1.0, xanchor="left"))
    if probit:
        # Ticked in probability and positioned in normal score, so the reader never has to think
        # in z: the axis still says 0.9, it is just no longer evenly spaced.
        fam.update_xaxes(tickmode="array",
                         tickvals=[float(_probit(p)) for p in PROBIT_TICKS],
                         ticktext=[f"{p:.2f}".rstrip("0").rstrip(".") for p in PROBIT_TICKS],
                         range=[float(_probit(PROBIT_TICKS[0])) - 0.3,
                                float(_probit(PROBIT_TICKS[-1])) + 0.3],
                         title_text="P(column at least this tall) \u2014 probit scale")
        # **And the column axis goes logarithmic with it.** A lognormal is straight on probit
        # against LOG column, not against linear -- measured on a pure lognormal, r = -1.00000
        # against log and only -0.921 against linear. Offering probit with a linear column axis
        # would be offering the scale without the property it exists for, and the reader would
        # read the residual curvature as a finding.
        # A fixed window on the log column axis, 9 to 1 001 m, so the
        # probit view keeps the same frame whatever the family or prospect draws; reversed by
        # giving the range deep end first. Plotly takes log-axis ranges as log10 of the values.
        fam.update_yaxes(type="log", autorange=False,
                         range=[np.log10(1001.0), np.log10(9.0)],
                         title_text="Hydrocarbon column (m) — log scale")
    else:
        fam.update_xaxes(range=[0, 1.02])
    if probit:
        st.caption(
            "Probit, with the column axis logarithmic to match. A lognormal column-height distribution "
            "is a straight line on these axes, so curvature is a departure from lognormal, and the "
            "tails, squashed into a few pixels on a linear axis, open up. The benchmark families "
            "are lognormal capacities clipped at the closure, so each runs straight and then turns "
            "over where the closure starts binding: the bend is the fill-to-spill point mass."
        )
    n.plot(fam, ("Orange is the prospect built on tab 3.0; the dashed grey beside it is the "
                 "benchmark at the same structural relief. Those two are the like-for-like pair; "
                 "the six coloured curves are the family it sits inside, not its comparators. "
                 "Below the dashed grey the model is more optimistic than the empirical record "
                 "for a closure of this size, above it more pessimistic. Where the "
                 "prospect has a DHI, its updated curve is drawn in red at the same weight: two "
                 "readings of one prospect, and the question is which sits deeper.  "
                 if limit_set is not None and own_relief else "")
                + f"Column-height exceedance by closure height, {source}"
                + ("" if source == "Graham et al. (2015)"
                   else f", at {burial:,.0f} m burial")
                + ". Dotted segments are the filled-to-spill point mass, marked at its depth. "
                  "The chart shape is the pre-drill benchmark family in common use; the middle "
                  "option draws the published estimator on the same axes as the corrected one.")

    rows = []
    for closure in CLOSURE_FAMILY:
        drawn = samples[closure]
        rows.append({
            "Closure height (m)": f"{closure:,.0f}",
            "P90 column (m)": f"{engine.weighted_percentiles(drawn, None, 90.0)[0]:,.0f}",
            "P50 column (m)": f"{engine.weighted_percentiles(drawn, None, 50.0)[0]:,.0f}",
            "P10 column (m)": f"{engine.weighted_percentiles(drawn, None, 10.0)[0]:,.0f}",
            "Fills to spill": f"{np.mean(drawn >= closure - 1e-9):.0%}",
            "Fill fraction, P50": f"{engine.weighted_percentiles(drawn, None, 50.0)[0] / closure:.0%}",
        })
    n.table(pd.DataFrame(rows),
            "The same family as numbers. Fill fraction is the P50 column as a share of the "
            "closure, and it falls as closure height rises, since a bigger closure is harder to "
            "fill. A benchmark on which it stays flat says the closure does not bind, which for "
            "large closures is not what the data shows.")

    if st.session_state.get("dhi_on") and st.session_state.get("dhi_overlay") is not None:
        st.markdown("The geological curve is the like-for-like comparison; the DHI curve shows "
                    "how far the evidence moved the prospect, not whether the model is "
                    "calibrated. Method: see 8.1.9.")

    if imported is not None and source == imported_label(imported):
        st.info(
            "What this series is. The C&C and ExxonMobil families are the same banded model, "
            "sharing the same fill-to-spill weight. They differ in one thing: the distribution "
            "drawn when the closure does not fill to spill. ExxonMobil draws uniformly between a "
            "20 m floor and the relief; C&C draws a strongly top-weighted shape over the same "
            "range.\n\n"
            "It is not a second dataset. It is one modelling choice, and the fill fractions in the "
            "table above against Graham's show how much that choice moves the answer. The "
            "parameters are held outside the repository, and the series does not appear on a "
            "machine without them."
        )

    if source == "NCS, as the paper fits it":
        st.markdown("This is the published estimator, drawn for comparison and not for use. "
                    "Fitted without treating the filled-to-spill discoveries as censored, it "
                    "under-fills small closures and over-fills the largest, and does not "
                    "reproduce the dataset's own fill-to-spill rate. Method: see 8.1.9.")

    # ------------------------------------------------------------------ summary
    # -------- Are we optimistic or pessimistic? ------------------------------------------
    theme.heading(TAB, "8 · Optimistic or pessimistic against the record")
    limit_set_cal = st.session_state.get("limit_set")
    _calibratable = limit_set_cal is not None and bool(own_relief) and own_relief > 0
    built_column = np.asarray([], dtype=float)
    if _calibratable:
        from hcwc.ui import run as engine_run
        _built_result = engine_run.current(limit_set_cal)
        built_column = _built_result.column_m[_built_result.above_minimum]

    if not _calibratable:
        st.info("Calibration against the benchmarks needs the limits on tab 3.0 and a spill point "
                "on tab 2.0.")
    elif built_column.size == 0:
        # Drawn before anything is compared. A minimum above every achievable column leaves nothing
        # to place inside a benchmark, and `np.percentile` of an empty array is an IndexError out of
        # numpy -- which is what a reader got. The honest answer is that the prospect does not reach
        # the threshold. It is a real setting, not a silly one: on the worked prospect 300 m still
        # reports POS 0.4 %, and from about 330 m there are no success cases left at all.
        st.info(
            "No realisation reaches the assessment minimum, so there is no column distribution "
            "to place inside a benchmark. The prospect still has a contact distribution; no "
            "realisation meets this assessment minimum. A lower minimum on tab 2.0 restores them."
        )
    else:
        from hcwc.core import calibration

        # **Both bases, throughout.** Which exhibit shows them together and which asks you to pick
        # is decided by the medium, not by preference: a table can carry a `Basis` column and be
        # read; four benchmarks times two bases on one Q-Q plot is eight curves and is not.
        updated_column = dhi_columns(built_column.size)
        bases = [(theme.GEOLOGICAL, built_column)]
        if updated_column is not None:
            bases.append((theme.evidence_basis(), updated_column))

        st.markdown(
            f"Every benchmark below is evaluated at this prospect's structural relief of "
            f"{own_relief:,.0f} m and its {burial:,.0f} m burial depth, so the comparison is like "
            f"for like rather than against a family the closure is not in.\n\n"
            f"The number is the exceedance percentile the median column lands on. A P50 at the "
            f"benchmark's P25 means a quarter of comparable closures reach it, which is optimistic. "
            f"Below 50 is optimistic, above 50 conservative."
        )

        sources = ["NCS, censoring-corrected", "NCS, as the paper fits it",
                   "Graham et al. (2015)"]
        loaded = st.session_state.get("imported_dataset")
        if loaded is not None:
            sources.append(imported_label(loaded))

        # One comparison per (benchmark, basis). `comparisons` stays the geological list because
        # the Q-Q and ratio figures below draw one basis at a time; `all_comparisons` carries both
        # for the table, which can show them side by side without becoming unreadable.
        comparisons = []
        all_comparisons = []
        for label in sources:
            drawn = _samples_for(label, (round(own_relief, 1),), float(burial))
            if not drawn:
                continue
            sample = next(iter(drawn.values()))
            for basis, columns in bases:
                comparison = calibration.compare(columns, sample, label)
                all_comparisons.append((basis, comparison))
                if basis == theme.GEOLOGICAL:
                    comparisons.append(comparison)

        if not comparisons:
            st.info("No benchmark could be evaluated at this relief.")
        else:
            n.table(
                pd.DataFrame([
                    {"Benchmark": c.name,
                     "Basis": basis,
                     "Their P90": f"{c.bench_p90:,.0f}",
                     "Their P50": f"{c.bench_p50:,.0f}",
                     "Their P10": f"{c.bench_p10:,.0f}",
                     "This P50": f"{c.built_p50:,.0f}",
                     "Ratio": f"{c.ratio:.2f}",
                     "This P50 is their": f"P{c.p50_lands_at:.0f}",
                     "Verdict": c.verdict}
                    for basis, c in all_comparisons]),
                (f"{theme.basis_tag(theme.GEOLOGICAL)} "
                 + (f"{theme.basis_tag(theme.GIVEN_DHI)} &nbsp; Two rows per benchmark, one "
                    f"per basis, because the question has a different answer before and after "
                    f"the evidence. "
                    if len(bases) > 1 else "&nbsp; ")
                 + f"All columns in metres, at "
                f"{own_relief:,.0f} m relief. The ratio says how far apart the medians are; the "
                f"percentile says how unusual this median would be among closures of this size. "
                f"The spread between benchmarks matters too: a model optimistic against one and in "
                f"line with another disagrees with them less than they disagree with each other."))

            for c in comparisons:
                st.markdown(f"- {c.sentence}"
                            + (f" *({theme.GEOLOGICAL})*" if len(bases) > 1 else ""))

            # **The verdict is a calibration statement, and only one basis supports one.** §7
            # already argues this at length against figure 6.8, in the strongest terms the tab
            # uses: *"use the DHI curve to see how far the evidence moved you, not to judge whether
            # you are calibrated."* That warning is a section away by the time a reader reaches the
            # Verdict column here, and once both bases are in the table it is the column most
            # likely to be misread. So the short form goes where the number is.
            #
            # The argument, compressed: Graham et al. say in their opening sentence that their
            # synthesis is for the case *without* DHIs; Edmundson's 242 carry no DHI flag and are
            # discoveries, so DHI-supported wells are over-represented among them by selection; and
            # detectability rises with column height, so that over-representation is concentrated in
            # exactly the long columns the comparison turns on.
            if len(bases) > 1:
                st.info(
                    "Only the geological row is a calibration verdict. The benchmarks cannot be "
                    "conditioned on a DHI: Graham et al. is the no-DHI prior, and Edmundson's "
                    "discoveries are partly selected by other people's amplitudes, enriched in "
                    "long columns because that is what detectability does. A posterior judged "
                    "against them counts the DHI twice and reads as less optimistic than it is. "
                    "Method: see 8.1.9.\n\n"
                    "The updated row reads as displacement rather than as a score: how far the "
                    "evidence moved the prospect against a fixed backdrop. The distance between "
                    "the two rows is the quantity to quote."
                )

            # **A selector rather than both at once, and the medium decides it.** Four benchmarks
            # against two bases is eight curves on a figure whose whole reading is which side of one
            # diagonal a curve sits; the table above shows both together because a table can carry
            # that. Flipping this is the comparison -- if the curve crosses the diagonal when you
            # switch, the evidence moved you from optimistic to conservative, which is a finding.
            qq_basis, qq_column = theme.GEOLOGICAL, built_column
            if len(bases) > 1:
                qq_basis = st.radio(
                    "Draw these two figures on", [b for b, _ in bases], horizontal=True,
                    key="calibration_basis",
                    help="The table above carries both at once. These two read one distribution "
                         "against the benchmarks, so they take one basis at a time; switching "
                         "shows whether the evidence moved the prospect across the diagonal.")
                qq_column = dict(bases)[qq_basis]
            qq_comparisons = [c for basis, c in all_comparisons if basis == qq_basis]
            qq_tag = theme.basis_tag(theme.GEOLOGICAL if qq_basis == theme.GEOLOGICAL
                                     else theme.GIVEN_DHI)

            qq = go.Figure()
            lo = min(c.bench_p90 for c in qq_comparisons) * 0.75
            hi = max(max(c.built_p10 for c in qq_comparisons),
                     max(c.bench_p10 for c in qq_comparisons)) * 1.1
            edge = np.array([lo, hi])

            # The two zones, named. On a Q-Q plot "which side of the diagonal" is the whole
            # reading, and leaving the reader to work out which side means what — on an axis that
            # is also reversed — is exactly the kind of small ambiguity that gets a figure
            # misquoted. So the sides are shaded and labelled, and the labels say the consequence
            # rather than the direction.
            qq.add_scatter(x=np.concatenate([edge, edge[::-1]]),
                           y=np.concatenate([edge, [hi, hi]]), fill="toself",
                           fillcolor=theme.rgba("#C44E52", 0.09), mode="lines",
                           line=dict(width=0), hoverinfo="skip", showlegend=False)
            qq.add_scatter(x=np.concatenate([edge, edge[::-1]]),
                           y=np.concatenate([edge, [lo, lo]]), fill="toself",
                           fillcolor=theme.rgba("#4C72B0", 0.09), mode="lines",
                           line=dict(width=0), hoverinfo="skip", showlegend=False)

            # The corridor: inside it the disagreement is smaller than the benchmarks' own spread.
            band = calibration.CORRIDOR
            qq.add_scatter(x=np.concatenate([edge, edge[::-1]]),
                           y=np.concatenate([edge * (1 + band), edge[::-1] * (1 - band)]),
                           fill="toself", fillcolor="rgba(120,120,120,0.13)", mode="lines",
                           line=dict(width=0), hoverinfo="skip",
                           name=f"within {band:.0%}")
            qq.add_scatter(x=edge, y=edge, mode="lines", name="agreement",
                           line=dict(color="#555", width=1.6, dash="dash"))

            for c, colour in zip(qq_comparisons, (FITTED, PUBLISHED, "#E8A33D", "#4C72B0")):
                drawn = next(iter(_samples_for(
                    c.name, (round(own_relief, 1),), float(burial)).values()))
                mine, theirs = calibration.quantile_pairs(qq_column, drawn)
                share = calibration.corridor_share(qq_column, drawn)
                qq.add_scatter(x=theirs, y=mine, mode="lines",
                               name=f"{c.name} — {share:.0%} in band",
                               line=dict(color=colour, width=2.6),
                               hovertemplate=f"{c.name}<br>benchmark %{{x:,.0f}} m<br>"
                                             f"this prospect %{{y:,.0f}} m<extra></extra>")
                # P90/P50/P10 marked, so the three numbers anyone quotes can be located on the
                # curve rather than inferred from its shape.
                # P50 only. Marking all three turned the middle of the figure into overlapping
                # labels, and the median is the one anyone quotes.
                mid = mine.size // 2
                qq.add_scatter(x=[theirs[mid]], y=[mine[mid]], mode="markers",
                               marker=dict(color=colour, size=10, symbol="diamond",
                                           line=dict(color="white", width=1)),
                               showlegend=False,
                               hovertemplate=f"{c.name} P50<br>benchmark %{{x:,.0f}} m<br>"
                                             f"this prospect %{{y:,.0f}} m<extra></extra>")

            # Anchored to the plot area, not to data: a label positioned in data coordinates on an
            # axis whose range depends on the prospect will eventually fall off the edge, and one
            # of them did.
            qq.add_annotation(xref="paper", yref="paper", x=0.03, y=0.05,
                              text="<b>taller column than the record</b><br>optimistic",
                              showarrow=False, xanchor="left", yanchor="bottom",
                              font=dict(size=11, color="#8A2F33"), align="left")
            qq.add_annotation(xref="paper", yref="paper", x=0.97, y=0.95,
                              text="<b>shorter column than the record</b><br>conservative",
                              showarrow=False, xanchor="right", yanchor="top",
                              font=dict(size=11, color="#2E4C73"), align="right")

            qq.update_layout(xaxis_title="Benchmark column at this relief (m)",
                             height=600, margin=dict(t=20),
                             legend=dict(orientation="h", y=-0.16))
            qq.update_xaxes(range=[lo, hi])
            # Reversed, consistent with every other column axis in the tool: a
            # taller column reaches further down the structure, so "further down the page" has to
            # mean "more column" whichever axis it is on. The consequence is that the optimistic
            # zone is the LOWER one, which is why both zones are labelled rather than left to
            # convention.
            qq.update_yaxes(title_text="This prospect's column (m), larger downward",
                            range=[hi, lo], autorange=False)
            n.plot(qq,
                   f"{qq_tag} &nbsp; Matched quantiles, this prospect against the benchmark, "
                   f"with agreement as the dashed diagonal and the two zones named. The y-axis "
                   f"reads downward like every other column axis here, so a taller predicted "
                   f"column falls into the lower, red zone.\n\n"
                   f"The grey corridor is ±{band:.0%}, and the legend gives the share of each "
                   f"curve inside it: how much of the distribution agrees, not only where its "
                   f"median lands. ±{band:.0%} is chosen because the four benchmarks disagree with "
                   f"each other by more than that at most reliefs; a tighter band would report a "
                   f"miscalibration against a spread the literature does not resolve.\n\n"
                   f"The shape matters more than the size. A curve parallel to the diagonal is "
                   f"uniform bias, correctable with one number. A curve that meets the diagonal "
                   f"in the middle and departs at P10 is disagreement in the upside only, the "
                   f"tail the volume comes from.")

            # The same comparison as a ratio, which is the form the question was asked in: *by how
            # much*, and *where*. A Q-Q plot shows two distributions; this shows the one number
            # that separates them, at every percentile, against a flat line at parity.
            ratio = go.Figure()
            # **Exceedance, like every other percentile in this tool.** P100 is the shallowest
            # contact and P0 the deepest, so the shallow end of a column distribution is P99 and
            # the deep end is P1. This axis said the opposite until it was caught
            # -- `quantile_pairs` returns shallow-to-deep, which numpy indexes as an *ascending*
            # percentile, and the label was taken from the numpy call rather than from the
            # convention. The grid now comes from `calibration.exceedance_grid`, beside the pairs
            # it labels, and the axis is reversed so shallow still reads on the left.
            probabilities = calibration.exceedance_grid()
            ratio.add_hrect(y0=1.0, y1=3.0, fillcolor=theme.rgba("#C44E52", 0.10),
                            line_width=0, layer="below")
            ratio.add_hrect(y0=0.0, y1=1.0, fillcolor=theme.rgba("#4C72B0", 0.10),
                            line_width=0, layer="below")
            ratio.add_hrect(y0=1 - calibration.CORRIDOR, y1=1 + calibration.CORRIDOR,
                            fillcolor="rgba(120,120,120,0.16)", line_width=0, layer="below")
            ratio.add_hline(y=1.0, line=dict(color="#555", width=1.6, dash="dash"))

            for c, colour in zip(qq_comparisons, (FITTED, PUBLISHED, "#E8A33D", "#4C72B0")):
                drawn = next(iter(_samples_for(
                    c.name, (round(own_relief, 1),), float(burial)).values()))
                ratio.add_scatter(
                    x=probabilities, y=calibration.quantile_ratios(qq_column, drawn),
                    mode="lines", name=c.name, line=dict(color=colour, width=2.6),
                    hovertemplate=f"{c.name}<br>exceedance P%{{x:.0f}}<br>"
                                  f"%{{y:.2f}}× the benchmark<extra></extra>")

            ratio.add_annotation(xref="paper", yref="paper", x=0.02, y=0.97,
                                 text="<b>above 1: more column than the record</b>",
                                 showarrow=False, xanchor="left", yanchor="top",
                                 font=dict(size=11, color="#8A2F33"))
            ratio.add_annotation(xref="paper", yref="paper", x=0.02, y=0.03,
                                 text="<b>below 1: less</b>", showarrow=False,
                                 xanchor="left", yanchor="bottom",
                                 font=dict(size=11, color="#2E4C73"))
            ratio.update_layout(
                xaxis_title="Exceedance percentile (P99 shallow column → P1 deep column)",
                yaxis_title="This prospect's column ÷ benchmark column",
                height=430, margin=dict(t=20), legend=dict(orientation="h", y=-0.22))
            ratio.update_yaxes(range=[0, 2.0])
            # Reversed so P99 sits on the left: shallow reads left-to-right into deep, the way
            # P90 / P50 / P10 are read aloud, even though the numbers themselves count down.
            ratio.update_xaxes(autorange="reversed")
            n.plot(ratio, optional=True,
                   caption=f"{qq_tag} &nbsp; The same comparison as one number, at every "
                           f"percentile. Parity is the dashed line, the grey band is "
                           f"±{calibration.CORRIDOR:.0%}, and the shaded halves give the "
                           f"direction of the disagreement.\n\n"
                           f"The percentiles are exceedance percentiles, as everywhere else here: "
                           f"P100 is the shallowest contact and P0 the deepest, so the shallow end "
                           f"of a column distribution is P99 and the deep end is P1. The axis is "
                           f"reversed so shallow reads on the left.\n\n"
                           f"The slope is the finding, not the level. A flat curve away from 1 is "
                           f"a uniform bias, one number correctable in one place. A curve that "
                           f"tilts is a disagreement about shape, which no single correction "
                           f"fixes: the distribution and the record disagree about how quickly "
                           f"column height runs out down the structure.")

        st.markdown("#### The model, the record, and the two combined")
        st.markdown(
            "The comparison above is a number and a shape. This is the three distributions on "
            "one axis: what the limits produced, what the record says for a closure of this "
            "relief, and the two combined."
        )

        fuse_weight = st.slider(
            "Benchmark blend weight", 0.0, 1.0, 0.0, 0.05, key="fuse_benchmark",
            help="A blend, not an update: 0 is the model untouched, 1 is the benchmark, and in "
                 "between the two quantile functions are averaged at this weight, the same "
                 "operation the seal limit offers on tab 3.0.")

        bench_source = st.selectbox(
            "Benchmark to combine with", sources, key="fuse_source",
            help="The censoring-corrected NCS fit is the default because the naive one carries the "
                 "filled-to-spill bias §3 is about.")
        # **The argument moved to a document on 5 Sep 2026.** It is six hundred words of
        # pure reasoning with no figure and no computed number in it, which is the exact
        # shape of a thing that belongs in `docs/` rather than between a slider and the
        # chart it drives. What stays is the conclusion, which is what a reader at this
        # slider actually needs, and a pointer for the reader who wants to argue with it.
        st.caption(
            "A weight, not a Bayesian update. The model is already built out of relief and burial, "
            "since the spill point is the relief, so multiplying in a record conditioned on both "
            "would count the geometry twice. Two priors combine by weighting, which is why this is "
            "a slider starting at zero. Method: see 8.1.9."
        )

        bench_draw = _samples_for(bench_source, (round(own_relief, 1),), float(burial))

        if not bench_draw:
            st.info("That benchmark cannot be evaluated at this relief.")
        else:
            bench = next(iter(bench_draw.values()))

            top = float(max(np.percentile(built_column, 99.5), np.percentile(bench, 99.5)))
            grid = np.linspace(0.0, top, 320)

            # **Every basis gets a combined curve, not just the geological one.**
            # *"in 6.12 is the combined just the geological, or what about the |DHI?"*
            # It was the geological one, and drawing the updated model beside a fusion that
            # ignored it made the figure read as though the evidence had been folded in when
            # it had not. The fusion is a weighted quantile average, so it applies to either
            # basis unchanged -- there was never a reason for one to be privileged.
            #
            # The `curves` list is built basis by basis so the model and its fusion sit
            # together in the legend, sharing a colour and separated by the dash.
            fused_by_basis = {}
            curves = []
            for basis, columns in bases:
                colour = (theme.BASIS_COLOUR[theme.GEOLOGICAL] if basis == theme.GEOLOGICAL
                          else theme.BASIS_COLOUR[theme.GIVEN_DHI])
                curves.append((f"this model, {basis}", columns, colour, "solid", 3.2))
                fused_by_basis[basis] = benchmarks.shrink_toward(columns, bench, fuse_weight)
                if fuse_weight > 0:
                    curves.append((f"{basis}, blended with the benchmark at weight {fuse_weight:.2f}",
                                   fused_by_basis[basis], colour, "dot", 3.0))

            curves.append((f"{bench_source}, at {own_relief:,.0f} m relief", bench,
                           "#8172B2", "dash", 2.4))

            fig_fuse = go.Figure()
            for label, sample, colour, dash, width in curves:
                # Column height down the page, probability across.
                fig_fuse.add_scatter(x=engine.exceedance(sample, grid), y=grid, mode="lines",
                                     name=label,
                                     line=dict(color=colour, width=width, dash=dash))
            fig_fuse.update_layout(
                xaxis_title="P(column ≥ this)", xaxis_range=[0, 1.02],
                yaxis=dict(title="Hydrocarbon column (m)", autorange="reversed"),
                height=560, margin=dict(t=20),
                legend=dict(orientation="v", x=1.02, y=1.0, xanchor="left"))
            n.plot(fig_fuse,
                   (f"{theme.basis_tag(theme.GEOLOGICAL)} "
                    + (f"{theme.basis_tag(theme.GIVEN_DHI)} &nbsp; Both distributions are here, "
                       f"each with its own combined curve in the same colour, dotted.\n\n"
                       if len(bases) > 1 else "&nbsp; ")
                    + "Every curve is conditional on the prospect working: these are column "
                   "distributions, not chances. The combined curve is a weighted average of "
                   "quantiles, not a Bayesian update, so it lies between the two. Method: see "
                   "8.1.9."))

            for basis, columns in bases:
                if len(bases) > 1:
                    st.caption(f"Combined with the benchmark, on the {basis} model")
                f1, f2, f3 = st.columns(3)
                for col, pct_ in ((f1, 90), (f2, 50), (f3, 10)):
                    mine_v = float(engine.weighted_percentiles(columns, None, float(pct_))[0])
                    fused_v = float(engine.weighted_percentiles(fused_by_basis[basis], None, float(pct_))[0])
                    col.metric(f"Combined P{pct_}", f"{fused_v:,.0f} m",
                               f"model {mine_v:,.0f} m", delta_color="off")

        st.warning(
            "A sanity check rather than a score: every benchmark is conditioned on discovery. A "
            "prospect can be optimistic on good grounds where the evidence for it can be named. "
            "Method: see 8.1.9."
        )

    theme.heading(TAB, "9 · The base rate for a comparable prospect")
    st.markdown(
        "Edmundson's §5.2 recommends base-rate figures beside the geological assessment: their "
        "matrix for a prospect of these dimensions, beside what the limits produced, with the "
        "sample size in view. Nothing here changes a number. Method: see 8.1.9."
    )

    matrix_limits = st.session_state.get("limit_set")
    if matrix_limits is None or not own_relief or own_relief <= 0:
        st.info("The matching cell needs the limits on tab 3.0 and a spill point on tab 2.0.")
    else:
        from hcwc.ui import run as engine_run

        matrix = benchmarks.load_edmundson_matrix()
        height_bin = ("0-150m" if own_relief <= 150 else
                      "151-300m" if own_relief <= 300 else "300+m")
        depth_bin = ("0-1500m" if burial <= 1500 else
                     "1501-3000m" if burial <= 3000 else "3000+m")
        cell = matrix[(matrix.trap_height_bin == height_bin)
                      & (matrix.burial_depth_bin == depth_bin)]

        _built_fill = engine_run.current(matrix_limits)
        if cell.empty:
            st.info("No cell in the published matrix matches this relief and burial depth.")
        elif not _built_fill.above_minimum.any():
            # The third place an assessment minimum above every achievable column shows up. Here it
            # was not a crash but a "Mean of empty slice" warning and a row of NaN percentages
            # presented beside real published ones -- which is worse, because it looks like data.
            st.info(
                "No realisation reaches the assessment minimum, so there is no fill fraction "
                "to compare against the published matrix. A lower minimum on tab 2.0 restores one."
            )
        else:
            cell = cell.iloc[0]
            # Restricted to the success cases, because every one of the 242 is a discovery. The
            # comparison is only like-for-like against realisations that would have been drilled
            # and found something.
            built = _built_fill
            bands = ((0.0, 0.5), (0.5, 0.75), (0.75, 0.99))

            def _fill_shares(columns: np.ndarray) -> list[float]:
                """Share of realisations in each fill band, plus filled-to-spill."""
                fill = np.clip(np.asarray(columns, float) / float(own_relief), 0.0, 1.0)
                return ([float(((fill > lo) & (fill <= hi)).mean()) for lo, hi in bands]
                        + [float((fill > 0.99).mean())])

            # Both bases, as bars. *"in 6.13 maybe a bar for the |DHI?"* The base
            # rate is `P(trap fill | discovery)`, and what the amplitude or the well says about
            # where the contact sits changes the fill fraction directly -- so leaving the updated
            # model out compared the record against the half of the tool that had not heard the
            # evidence.
            fill_bases = [(theme.GEOLOGICAL, built.column_m[built.above_minimum])]
            _updated = dhi_columns(int(built.above_minimum.sum()) or 1)
            if _updated is not None:
                fill_bases.append((theme.evidence_basis(), _updated))
            shares = {basis: _fill_shares(columns) for basis, columns in fill_bases}
            mine = shares[theme.GEOLOGICAL][:3]
            theirs = [float(cell.p_fill_0_50), float(cell.p_fill_51_75),
                      float(cell.p_fill_76_99)]

            c1, c2, c3 = st.columns(3)
            c1.metric("Matching cell", f"{height_bin} · {depth_bin}")
            c2.metric("Discoveries in it", f"{int(cell.n)}",
                      "the whole basis for this row", delta_color="off")
            c3.metric("Of those, filled to spill", f"{float(cell.p_fill_100):.0%}",
                      "censored; capacity not observed", delta_color="off")

            labels = ("0–50%", "51–75%", "76–99%", "100%, censored")
            published = theirs + [float(cell.p_fill_100)]
            rows = []
            for i, label in enumerate(labels):
                row = {"Trap fill": label, "This cell": f"{published[i]:.1%}"}
                for basis, _ in fill_bases:
                    row[f"This model · {basis}"] = f"{shares[basis][i]:.1%}"
                    row[f"Difference · {basis}"] = f"{shares[basis][i] - published[i]:+.1%}"
                rows.append(row)
            comparison = pd.DataFrame(rows)

            axis = ["0–50%", "51–75%", "76–99%", "100%"]
            fig_base = go.Figure()
            for basis, _ in fill_bases:
                fig_base.add_bar(
                    x=shares[basis], y=axis, orientation="h", name=f"this model · {basis}",
                    marker_color=(theme.BASIS_COLOUR[theme.GEOLOGICAL]
                                  if basis == theme.GEOLOGICAL
                                  else theme.BASIS_COLOUR[theme.GIVEN_DHI]))
            fig_base.add_bar(y=axis, x=published, orientation="h",
                             name=f"NCS base rate (n = {int(cell.n)})", marker_color="#8172B2")
            fig_base.update_layout(barmode="group", height=330, margin=dict(t=20),
                                   xaxis_title="Share of cases", xaxis_tickformat=".0%",
                                   yaxis_title="Trap fill", yaxis=dict(autorange="reversed"),
                                   legend=dict(orientation="h", y=-0.28))
            n.plot(fig_base,
                   (f"{theme.basis_tag(theme.GEOLOGICAL)} "
                    + (f"{theme.basis_tag(theme.GIVEN_DHI)} &nbsp; "
                       if len(fill_bases) > 1 else "&nbsp; ")
                    + f"The competing limits against the {int(cell.n)} NCS discoveries in the same "
                   f"trap-height and burial-depth cell, restricted to the realisations meeting "
                   f"the assessment minimum because every one of theirs is a discovery.\n\n"
                   "The bottom pair reads apart from the other three. The 100 % bar is not a fill "
                   "outcome; it is the share of traps whose seal capacity was not observed, "
                   "because geometry stopped the column first. It is a right-censoring rate, and "
                   "the model's filled-to-spill share is a different kind of number."))
            n.table(comparison,
                    "A disagreement here is a finding rather than an error. The base rate "
                    "describes what was drilled and found on the NCS; the model describes what "
                    "the mechanisms allow. They are built from different information and may "
                    "differ. The question a difference raises is which elicited limit would have "
                    "to move to close it, and §8 gives the direction.")

            if len(fill_bases) > 1:
                st.caption(
                    "The updated bars are displacement against a fixed backdrop, not "
                    "calibration. Method: see 8.1.9."
                )
            st.warning(
                f"This informs the contact distribution and never the chance: the matrix is "
                f"`P(trap fill | discovery)`, and all {int(cell.n)} of those traps had "
                f"hydrocarbons in them. {int(cell.n)} discoveries is a thin basis, which is why "
                f"the two are shown side by side and not combined. Method: see 8.1.9."
            )

            # Seven hundred words of argument about somebody else's arithmetic, with a
            # sourcing paragraph and a fixed-point table, and nothing on this page depends
            # on it. Moved to docs on 5 Sep 2026, now 8.1.9 of docs/THEORY.md. The sentence that
            # governs what the reader does next stays here.
            st.caption(
                "Side by side, not merged: the rule usually attached to base-rate neglect is "
                "symmetric, returning the same answer when its two inputs are swapped, which no "
                "Bayesian update does. Method: see 8.1.9."
            )

    theme.heading(TAB, "10 · Scope of the claims")
    st.markdown(
        "Two selection effects remain uncorrected in every analysis on this page: discovery-only "
        "conditioning, so this is `P(column | discovery)`, and left-truncation at the well's "
        "reservoir entry, which removes the small-column tail. Stacked, the record is truncated "
        "below and censored above, and both push it to look better filled than reality. "
        "Method: see 8.1.9; limitations: 8.1.10."
    )
    st.caption(
        "Data: Edmundson, I., Davies, R., Frette, L.U., Mackie, S., Kavli, E.A., Rotevatn, A., "
        "Yielding, G. & Dunbar, A. (2021), AAPG Bulletin 105(12), 2381–2403, "
        "doi:10.1306/03122119223. Raw table https://osf.io/6ysbv/ under CC-BY 4.0. "
        "Full references in 8.1.11."
    )
