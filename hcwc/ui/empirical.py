"""Tab ⑤ — the empirical basis: the statistics and the benchmark comparison, together.

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
— apex to spill — under two names, and §0 says so once rather than leaving a reader to wonder.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import norm

from hcwc.core import censoring
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


@st.cache_data(show_spinner=False)
def _load():
    d = benchmarks.load_edmundson().rows
    return (d.trap_height_m.to_numpy(float), d.hc_column_m.to_numpy(float),
            d.burial_depth_m.to_numpy(float), d.filled_to_spill.to_numpy(bool))


@st.cache_data(show_spinner=False)
def _fit():
    h, c, z, _ = _load()
    fit = censoring.censored_loglinear({"trap_height": h, "burial_depth": z}, c, h)
    naive, *_ = np.linalg.lstsq(np.column_stack([np.ones(c.size), np.log(h), np.log(z)]),
                                np.log(c), rcond=None)
    return fit, naive


#: The shipped errors-in-variables curve. See :func:`_bias_curve`.
_BIAS_CURVE = benchmarks.REFERENCE / "bias_curve.json"


@st.cache_data(show_spinner=False)
def _bias_curve(sigmas: tuple[float, ...]):
    """Mean fitted elasticity against apex-pick error, for both estimators.

    **Loaded, not computed, unless the sigmas have changed.** It is 540 censored MLE fits and it
    took about six seconds of every cold start -- while being *constant*: fixed sigmas, a seeded
    generator, and nothing the user enters reaching it. It demonstrates how the two estimators
    behave under depth-conversion error; it is not a result about anyone's prospect.

    The file records the sigmas it was built for and is ignored if they no longer match, because a
    stale curve would be worse than a slow one. Regenerate with ``scripts/bias_curve.py``.
    """
    if _BIAS_CURVE.exists():
        import json
        cached = json.loads(_BIAS_CURVE.read_text(encoding="utf-8"))
        if tuple(cached.get("sigmas_m", ())) == tuple(sigmas):
            return cached["naive"], cached["censored"]

    rng = np.random.default_rng(5)
    naive_out, censored_out = [], []
    for sigma in sigmas:
        nv, cn = [], []
        for _ in range(60):
            apex = rng.normal(2500.0, 400.0, 242)
            spill = apex + np.exp(rng.normal(np.log(200.0), 0.7, 242))
            capacity = np.exp(rng.normal(np.log(250.0), 0.8, 242))
            contact = apex + np.minimum(capacity, spill - apex)
            err = rng.normal(0.0, sigma, 242)
            hh = np.clip(spill - (apex + err), 5.0, None)
            cc = np.minimum(np.clip(contact - (apex + err), 1.0, None), hh)
            nv.append(censoring.naive_slope(hh, cc))
            cn.append(censoring.censored_slope(hh, cc, hh).slope)
        naive_out.append(float(np.mean(nv)))
        censored_out.append(float(np.mean(cn)))
    return naive_out, censored_out


CLOSURE_FAMILY = (100.0, 200.0, 300.0, 400.0, 600.0, 800.0)

#: The label a loaded dataset appears under. Its own name, so two people comparing screens
#: can tell whose data they are looking at rather than both seeing "imported".
def imported_label(dataset) -> str:
    return f"{dataset.name} (yours)"


@st.cache_data(show_spinner=False)
def _family_samples(source: str, closures: tuple[float, ...], burial_m: float,
                    n: int = 40_000) -> dict[float, np.ndarray]:
    """Column-height samples for a family of closure heights, from one benchmark.

    The three sources are deliberately *not* averaged into a house curve. They are conditioned
    differently and disagree informatively, and the disagreement is the finding.
    """
    out: dict[float, np.ndarray] = {}
    rng = np.random.default_rng(20260825)
    fit, naive = _fit()
    for closure in closures:
        if source == "Graham et al. (2015)":
            out[closure] = benchmarks.graham_column_height(rng, closure, n)
            continue
        if source == "NCS, as the paper fits it":
            mu = naive[0] + naive[1] * np.log(closure) + naive[2] * np.log(burial_m)
            sigma = fit.sigma
        else:
            mu = (fit.intercept + fit.coefficients["trap_height"] * np.log(closure)
                  + fit.coefficients["burial_depth"] * np.log(burial_m))
            sigma = fit.sigma
        out[closure] = np.minimum(np.exp(rng.normal(mu, sigma, n)), closure)
    return out


def _samples_for(source: str, closures: tuple[float, ...], burial_m: float,
                 n: int = 40_000) -> dict[float, np.ndarray]:
    """Samples from whichever benchmark is selected, built-in or imported.

    The dispatch exists because `_family_samples` is cached on its arguments and an imported
    dataset cannot be one: it holds a DataFrame, it is different for every user, and caching it
    would mean one person's confidential data sitting in a cache keyed by a name someone else
    might also use. The imported path is deliberately uncached -- it costs one fit per rerun and
    keeps the data in the session where it belongs.
    """
    imported = st.session_state.get("imported_dataset")
    if imported is not None and source == imported_label(imported):
        from hcwc.io import datasets
        rng = np.random.default_rng(20260825)
        fitted = datasets.fit(imported)
        return {h: datasets.column_height(imported, rng, h, burial_m, n, fitted=fitted)
                for h in closures}
    return _family_samples(source, closures, burial_m, n)


#: Probabilities the probit axis is ticked at. Chosen to be the ones people quote (P90/P50/P10)
#: plus enough tail to show where the curves separate, which is the point of the scale.
PROBIT_TICKS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)

#: How close to 0 or 1 a probability may get before the probit transform sends it to infinity.
#: An exceedance curve legitimately reaches exactly 1 at the origin and exactly 0 past the spill,
#: and both would otherwise take the axis with them.
PROBIT_CLIP = 1e-4


def _probit(p: np.ndarray) -> np.ndarray:
    """``z = Phi^-1(p)``, clipped so the certain ends of an exceedance curve stay on the page."""
    return norm.ppf(np.clip(np.asarray(p, dtype=float), PROBIT_CLIP, 1.0 - PROBIT_CLIP))


def _exceedance(samples: np.ndarray, grid: np.ndarray) -> np.ndarray:
    return (samples[None, :] >= grid[:, None]).mean(axis=1)


def _p_spill(fit, h, z):
    mu = (fit.intercept + fit.coefficients["trap_height"] * np.log(h)
          + fit.coefficients["burial_depth"] * np.log(z))
    return norm.sf((np.log(h) - mu) / fit.sigma)


@st.cache_data(show_spinner=False)
def _empirical_prior(closure_m: float, burial_m: float, n: int = 40_000) -> np.ndarray:
    """Column height the NCS data predicts for a closure of this height at this burial depth.

    Not a placeholder. Sample seal capacity from the censoring-corrected fit, apply the same
    ``min(S, H)`` the geology applies, and the result is a genuine empirical prior for a prospect of
    these dimensions — the thing the engine's output will eventually be compared against.
    """
    fit, _ = _fit()
    mu = (fit.intercept + fit.coefficients["trap_height"] * np.log(closure_m)
          + fit.coefficients["burial_depth"] * np.log(burial_m))
    rng = np.random.default_rng(20260825)
    return np.minimum(np.exp(rng.normal(mu, fit.sigma, n)), closure_m)


def _add_prospect_violin(fig, x: float, samples: np.ndarray, width: float) -> None:
    """The prospect's predicted column height, drawn into the population cross-plot."""
    fig.add_violin(x=np.full(samples.size, x), y=samples, width=width, side="both",
                   points=False, line_color=PROSPECT, fillcolor=PROSPECT_FILL,
                   name="this prospect — empirical prior", hoverinfo="skip", spanmode="hard")
    for pct, dash in ((90, "dot"), (50, "solid"), (10, "dot")):
        v = float(np.percentile(samples, 100 - pct))
        fig.add_scatter(x=[x - width / 2, x + width / 2], y=[v, v], mode="lines",
                        line=dict(color=PROSPECT, width=2, dash=dash),
                        showlegend=False, hovertext=f"P{pct} = {v:.0f} m", hoverinfo="text")


def _render_import() -> None:
    """Load a column-height dataset of your own, and use it as a fourth benchmark family.

    **Nothing leaves the session.** The file is parsed in memory, fitted in memory, and gone when
    the browser tab closes: no cache file, no upload, no network call. That is asserted in
    ``tests/test_datasets.py`` against the source of :mod:`hcwc.io.datasets`, because the property
    worth protecting is that nobody adds a cache later without noticing what it would mean.
    """
    from hcwc.io import datasets

    with st.expander("**Load your own dataset** — raw discoveries, fitted here, never stored",
                     expanded=st.session_state.get("imported_dataset") is None):
        st.markdown(
            "**One row per discovery, two columns required:** a closure height and a hydrocarbon "
            "column height, in metres. The reader accepts the usual spellings — `trap_height_m`, "
            "`closure_height`, `relief_m` for the first; `hc_column_m`, `column_height`, "
            "`hcwc_height` for the second.\n\n"
            "**Worth adding if you have them.** `burial_depth_m` makes the fit a two-predictor "
            "model rather than a one-predictor one; `apex_depth_m` stands in for it if you do "
            "not. `filled_to_spill` is used directly if present and derived at "
            f"{datasets.FILLED_RULE:.0%} of the closure if not — and **that flag is what the "
            "whole correction turns on**, because a filled trap measures the closure rather than "
            "the seal.\n\n"
            "**Why raw rows rather than a fitted curve.** The censoring correction runs here, on "
            "your data. Handing the tool someone else's fitted shape would give you their answer "
            "to their question; handing it your discoveries gives you the finding on yours."
        )
        c1, c2 = st.columns(2)
        name = c1.text_input("Name it", key="import_name", placeholder="e.g. internal fields, 2026")
        source = c2.text_input("Source", key="import_source",
                               placeholder="citation, internal reference, or 'unknown'")
        upload = st.file_uploader("Dataset (.csv)", type=["csv"], key="import_upload")

        if upload is not None:
            try:
                loaded = datasets.read_csv(upload.getvalue(),
                                           name=name or upload.name.rsplit(".", 1)[0],
                                           source=source)
            except datasets.DatasetError as exc:
                st.session_state.pop("imported_dataset", None)
                st.error(f"**That file cannot be read as a column-height dataset.** {exc}")
            else:
                st.session_state["imported_dataset"] = loaded
                st.success(
                    f"**{loaded.name}** — {len(loaded.usable):,} usable rows of {loaded.n:,}, "
                    f"{loaded.censored_fraction:.0%} filled to spill, fitted on "
                    + (" and ".join(x.replace("_", " ") for x in loaded.predictors)) + ".")
                if loaded.notes:
                    st.warning("**What the reader had to assume.** Every one of these is a "
                               "decision it made on your behalf:\n\n"
                               + "\n\n".join(f"- {note}" for note in loaded.notes))
        elif st.session_state.get("imported_dataset") is not None:
            if st.button("Forget the loaded dataset", key="forget_import"):
                st.session_state.pop("imported_dataset", None)
                st.rerun()


def render() -> None:
    n = Numbering(TAB)
    h, c, z, filled = _load()
    fit, naive = _fit()

    st.subheader("The empirical basis, and how it should be analysed")
    st.markdown(
        """
**Start with the credit, because it is owed.** Edmundson et al. (2021) assembled 242 measured
discoveries across the Norwegian Continental Shelf — every one needing an apex and a spill point
picked from depth-converted top-reservoir maps — and then **published the raw table openly under
CC-BY 4.0**. That is rare, and everything on this tab is possible only because they did it. The
dataset is a genuine contribution and nothing below detracts from it.

What follows is a disagreement about **one estimator**, not about the data.

> **A note on names.** Edmundson measures *trap height*; this tool calls the same quantity
> *closure height*, and its risk element *Closure*, matching E-POS. Apex to spill, one measurement,
> two names. Their term is kept whenever their data or their figures are being quoted, so that the
> numbers here can be checked against the paper without translation.
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
    theme.heading(TAB, "2 · Your prospect against the population")
    st.markdown(
        "Enter the closure height and burial depth and the panels below place the prospect in the "
        "population. The orange distribution is **what the NCS data predicts for a closure of these "
        "dimensions** — seal capacity drawn from the censoring-corrected fit, then capped at the "
        "closure, which is the same `min(S, H)` the geology applies. It is the empirical prior the "
        "engine's output will be compared against."
    )
    ca, cb, cc = st.columns([1, 1, 2])
    closure = ca.number_input("Closure height (m)", 20.0, 1500.0, 350.0, 10.0,
                              help="Apex to spill. Edmundson calls this trap height; it is the "
                                   "same measurement. Their data spans 14–715 m.")
    burial = cb.number_input("Burial depth (m)", 200.0, 6000.0, 2050.0, 50.0,
                             help="Overburden thickness to the reservoir. Needed because the "
                                  "corrected fit finds burial depth to be a much stronger control "
                                  "than the published analysis reported — see Table 7.4.")
    prior = _empirical_prior(closure, burial)
    cc.metric("Empirical prior, P50 column",
              f"{np.percentile(prior, 50):.0f} m",
              f"P90 {np.percentile(prior, 10):.0f} m · P10 {np.percentile(prior, 90):.0f} m",
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
    figA.update_layout(xaxis_title="Closure height (m)",
                       yaxis_title="Hydrocarbon column height (m)", height=560,
                       legend=dict(orientation="h", y=-0.16), margin=dict(t=20))
    n.plot(figA, "Column height against closure height, after Edmundson et al. Fig. 6A. Red "
                 "diamonds lie on the 1:1 line **by definition, not by physics** — they record the "
                 "closure, not the seal. The censored fit sits below the OLS line because it "
                 "estimates seal capacity rather than the observed column. Both `r` values are "
                 "correlations with the observed column; the MLE's is computed over the "
                 "**uncensored** discoveries only, since those are the ones it is trying to "
                 "predict.")

    st.info(
        f"**Both lines cross the 1:1, and it means opposite things.**\n\n"
        f"**The censored MLE crossing is a prediction, and it holds.** It estimates *seal "
        f"capacity*, which is allowed to exceed the closure — that is precisely what filling to "
        f"spill is. Above the 1:1 line the model is saying *this closure will fill*. It crosses at "
        f"**{(np.exp(fit.intercept + fit.coefficients['burial_depth'] * np.log(float(np.median(z)))))**(1 / (1 - fit.coefficients['trap_height'])):.0f} m**, "
        f"and in the data **63 % of closures below 144 m filled to spill against 35 % above** — so "
        f"the crossing lands where the filling behaviour actually changes.\n\n"
        f"**The published OLS crossing is a defect.** It is fitted to the *observed column*, which "
        f"cannot exceed the closure by construction, so below **{ols_cross:.0f} m** it predicts "
        f"something the data cannot contain — and **{int((h < ols_cross).sum())} of {h.size} "
        f"discoveries ({(h < ols_cross).mean():.0%})** sit there. Its intercept is "
        f"**{intercept:+.0f} m**, which says a closure of zero height holds {intercept:.0f} m of "
        f"column.\n\n"
        f"This is a *separate* criticism from the censoring one and needs no estimator theory to "
        f"see: a straight line through data bounded by `c ≤ h` will always do this unless it is "
        f"forced through the origin with a slope below one. It is kept here exactly as published."
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
    figB.update_layout(xaxis_title="Burial depth (m)", yaxis_title="Hydrocarbon column height (m)",
                       height=560, legend=dict(orientation="h", y=-0.16), margin=dict(t=20))
    n.plot(figB, "Column height against burial depth, after Edmundson et al. Fig. 6B. **This is "
                 "the panel where the two analyses disagree most** — the corrected fit is roughly "
                 "twice as steep, because censoring was suppressing the depth signal.")

    # ------------------------------------------------------------------ the issue
    # Sections 3 to 5 argue for the METHOD rather than about the reader's prospect, and they
    # were about half of the longest tab in the app -- sitting between "here is the data" and
    # "here is your prospect against it", which is the line a reader actually wants to walk.
    # Folded rather than moved to a document: they are live figures computed from the data, and
    # a static page would lose the calibration plot and the bias curve, which ARE the evidence.
    with st.expander("**The case for the correction** — why the published fit is biased, "
                     "whether ours holds up, and the bias it does not remove", expanded=False):
        st.caption(
            "Three sections of argument, kept because a correction nobody can check is worth "
            "nothing — and folded because they are about the estimator, not about your "
            "prospect. Open them when you want to disagree with the method; skip them when you "
            "want to use it."
        )
        theme.heading(TAB, "3.1 · Why the published regression measures the wrong thing")
        st.markdown(
            """
    The quantity a pre-drill model needs is **seal capacity `S`** — the column the seal *could* hold.
    What is measured is the column that is *there*, and the two differ by the same identity this whole
    tool is built on:

    ```
    observed column  C = min(S, H)          H = closure height
    ```

    * **Underfilled** (`C < H`) — the seal bound the column, so `C = S`. Seal capacity is observed.
    * **Filled to spill** (`C = H`) — geometry bound it. All that is learned is `S ≥ H`.
      **The observation is right-censored**; the seal's capacity was never tested.

    Hood (2019) states the geology plainly — pools controlled by geometric limits *"document the minimum
    column that the seal can support but not the upper limit"* — but the statistical consequence has not
    been carried into the published estimators. **111 of 242 rows, 46 %, are of this kind.**
    """
        )

        n.markdown_table(
            f"""
    | Log-log elasticity | As published (OLS) | Censoring-corrected (MLE) | |
    |---|---:|---:|---|
    | **Closure height** | {naive[1]:.3f} | **{fit.coefficients['trap_height']:.3f}** | overstated |
    | **Burial depth** | {naive[2]:.3f} | **{fit.coefficients['burial_depth']:.3f}** | **understated — roughly doubles** |
    """,
            "Censoring biases the two **in opposite directions**, which is why fitting them one at a "
            "time cannot reveal it. Closure height and burial depth are essentially uncorrelated here "
            "(r = 0.085), so this is not confounding. Both terms are significant by likelihood ratio "
            "(p = 8e-19 and p = 5e-4).",
        )

        st.markdown(
            """
    **What this does to the paper's conclusions.** The primary finding — closure height matters — stands,
    but is overstated. The secondary finding, that burial depth is the *weaker* control, does **not**
    survive: corrected, it roughly doubles. That is the physically expected direction, because seals
    compact and strengthen with depth. Censoring was hiding the depth signal, because deep closures fill
    to spill more often and so contribute censored rather than informative observations.
    """
        )

        with st.expander("Why not simply drop the filled-to-spill points?"):
            st.markdown(
                """
    It is the obvious fix and it does not work. Dropping them trades censoring bias for **truncation
    bias**: conditioning on `S < H` keeps only low capacity at low closure height, which manufactures
    the same positive relationship a second way.

    Simulated with seal capacity **completely independent** of closure height — zero physics, by
    construction, 242 points to match:

    | Estimator | Slope (truth = 0.000) |
    |---|---:|
    | Naive OLS, all points | 0.580 |
    | OLS after dropping filled-to-spill | 0.543 |
    | **Censored MLE** | **−0.009** |

    Only the censored likelihood recovers the truth, at every correlation tested. Asserted in
    `tests/test_censoring.py`, so if the claim is wrong the suite fails.
    """
            )

        # ------------------------------------------------------------------ calibration
        theme.heading(TAB, "3.2 · Does the corrected model fit?")
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
        n.plot(cal, "Calibration by closure-height band. The fitted model reproduces the observed fill "
                    "rate throughout — **this is what validates the parametric form**. The correction "
                    "is not buying a better story at the cost of fit.")

        st.warning(
            f"""**A correction to an earlier draft of this tab.** It previously claimed the model's 39 %
    fill rate *at* 250 m matched Graham et al.'s independent global 40 %, and called that a cross-check.
    It was not one — Graham states a population **average** over closures *below* 250 m, not the value
    at 250 m. Compared properly the NCS gives **{filled[h < 250].mean():.0%}** against Graham's 40 %.
    That gap is a **real regional difference**, not a discrepancy: Edmundson et al. note the NCS is
    charge-rich, so its closures fill more often than the global average — itself a good illustration of
    Graham's warning against global benchmarks without trap-specific geology."""
        )

        # ------------------------------------------------------------------ second bias
        theme.heading(TAB, "3.3 · A second bias, which the correction does not remove")
        st.markdown(
            """
    The corrected closure-height elasticity is still ~0.70, higher than a rock property should be —
    seal capacity has no business caring how tall the closure is. The reason is not selection, it is
    measurement, and it applies to **every** study of this kind:

    ```
    column  height = contact − apex
    closure height = spill   − apex        ← the same apex pick
    ```

    They **share the apex**. A depth-conversion error moves both in the same direction and manufactures
    a relationship out of nothing — and no censored estimator can see it, because it is handed the
    mismeasured numbers. Errors-in-variables sitting on top of censoring, pointing the same way.
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
        n.plot(bias, f"Spurious elasticity from a shared apex pick, on data with **no true relationship "
                     f"whatsoever**. At 50 m — 2 % at 2 500 m, ordinary depth conversion — the censored "
                     f"estimator returns ~0.58. Our own {fit.coefficients['trap_height']:.2f} is "
                     f"therefore an **upper bound, not an estimate**. The burial-depth result survives "
                     f"this: the same absolute error is ~25 % of a 200 m closure but ~2 % of a 2 500 m "
                     f"burial depth.")

        # ------------------------------------------------------------------ benchmark families
    theme.heading(TAB, "6 · The benchmark families, and adding your own")
    imported = st.session_state.get("imported_dataset")
    n.table(
        pd.DataFrame({
            "Benchmark": ["Edmundson (2021) — NCS", "Graham et al. (2015) — global",
                          imported.name if imported else "your own data"],
            "Size": ["242 discoveries, per-observation", "not stated; parameters only",
                     f"{len(imported.usable):,} usable of {imported.n:,}" if imported
                     else "none loaded"],
            "Stratified by": ["burial depth × closure height", "closure height band",
                              "burial × closure" if imported and imported.full_model
                              else "closure height" if imported else "—"],
            "Status": ["open, CC-BY 4.0", "abstract only — distributions never published",
                       f"source: {imported.source}" if imported else "load one below"],
        }),
        "Kept separate rather than merged into one 'empirical prior'. They are conditioned "
        "differently and disagree informatively — the NCS/global gap in §4 is an example, and a "
        "benchmark that agrees with the others tells you less than one that does not.",
    )
    st.warning(
        "**The measured dataset is Norwegian, and there is no second one.** A search for a public "
        "non-NCS dataset relating column height to *closure* height (28 Aug 2026) found none — "
        "tab ⑧ → *Benchmark sources* records what was checked. Edmundson et al. explain why in "
        "their own introduction: picking an apex and a spill point for every field needs 3D "
        "seismic and a velocity model, so *\"few studies of this kind have been carried out "
        "before\"*. The prior compilations — Gulf of Mexico, Malay Basin — report column-height "
        "distributions with **no trap geometry**, which cannot answer the question this tab asks."
        "\n\n"
        "**So a prospect outside the NCS is being compared against Norwegian rock.** Not fatal — "
        "the physics travels further than the stratigraphy does — but it is a real limitation and "
        "it belongs in any document that quotes these curves. If you have an in-house trap-fill "
        "database, loading it below is the only way to get a benchmark conditioned on your own "
        "basin."
    )
    _render_import()

    # ------------------------------------------------------------------ family curves
    theme.heading(TAB, "7 · The prior a benchmark actually gives you")
    st.info(
        "**Why the x-axis is column height and not structural relief.** Relief is what picks *which "
        "curve you are on* — it is the family parameter, one curve per value of it, and it labels "
        "the legend. The axis has to be the thing whose probability is being read, and that is the "
        "**column**: each curve answers *given a closure of this relief, how likely is a column of "
        "at least x?*\n\n"
        "Putting relief on the axis would answer a different question — how column varies with "
        "relief — and would collapse each curve to a point, which is why the built prospect could "
        "not be drawn on it. On these axes it can: it has a column distribution, so it has an "
        "exceedance curve, and it goes on the same axis as the benchmark for its own relief."
    )
    st.markdown(
        "A benchmark is only useful as **a curve for a closure of your size**, and the families "
        "below are what each one delivers. Read one curve as: for a closure of this relief, the "
        "probability that the column is at least *x* metres.\n\n"
        "**The vertical drop at the right-hand end of every curve is the point.** It is the "
        "filled-to-spill probability mass — the share of prospects of that relief whose column is "
        "set by the closure rather than by the seal. It is a point mass, not a tail, and no smooth "
        "distribution typed into a volumetrics package has one. Squashing it into a lognormal is "
        "exactly the error §3 identifies, arriving one step later in the workflow."
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
        "Vertical scale", ["Linear", "Probit"], horizontal=True, key="family_scale",
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
                                name=f"benchmark at YOUR relief ({own_relief:,.0f} m)",
                                line=dict(color="#555555", width=3, dash="dash"))

        # The DHI-updated distribution, when there is one. Drawn because Lars asked to see both
        # against the data; the caption carries why the comparison is weaker than the geological
        # one, since the benchmarks cannot be conditioned the same way.
        overlay = st.session_state.get("dhi_overlay")
        if overlay is not None and st.session_state.get("dhi_on"):
            posterior_column = np.asarray(overlay["depths_m"], dtype=float) - apex_mid
            fam.add_scatter(
                x=built_grid,
                y=_y(np.interp(built_grid, posterior_column,
                               np.asarray(overlay["pos_curve"], dtype=float)
                               / max(float(overlay["posterior_pos"]), 1e-12))),
                # Same weight and style as the geological curve, different colour. They are two
                # readings of the same prospect and the question is which is deeper -- a dotted
                # line reads as provisional or as a construction line, which this is not.
                mode="lines", name="THIS PROSPECT, given the DHI",
                line=dict(color=theme.BASIS_COLOUR[theme.GIVEN_DHI], width=4.5))

        fam.add_scatter(x=built_grid, y=_y(_exceedance(column, built_grid)), mode="lines",
                        name="THIS PROSPECT, geological",
                        line=dict(color=PROSPECT, width=4.5))
        fam.add_scatter(x=[float(np.median(column))], y=_y([0.5]), mode="markers",
                        showlegend=False,
                        marker=dict(color=PROSPECT, size=11, symbol="diamond"),
                        hovertemplate="built P50 %{x:,.0f} m<extra></extra>")

    fam.update_layout(xaxis_title="Hydrocarbon column (m)",
                      yaxis_title="Probability the column is at least this tall",
                      height=460, margin=dict(t=20), legend=dict(orientation="h", y=-0.18))
    if probit:
        # Ticked in probability and positioned in normal score, so the reader never has to think
        # in z: the axis still says 0.9, it is just no longer evenly spaced.
        fam.update_yaxes(tickmode="array",
                         tickvals=[float(_probit(p)) for p in PROBIT_TICKS],
                         ticktext=[f"{p:.2f}".rstrip("0").rstrip(".") for p in PROBIT_TICKS],
                         range=[float(_probit(PROBIT_TICKS[0])) - 0.3,
                                float(_probit(PROBIT_TICKS[-1])) + 0.3],
                         title_text="P(column at least this tall) \u2014 probit scale")
        # **And the x-axis goes logarithmic with it.** A lognormal is straight on probit-y against
        # LOG-x, not against linear x -- measured on a pure lognormal, r = -1.00000 against log x
        # and only -0.921 against linear. Offering probit with a linear x would be offering the
        # scale without the property it exists for, and the reader would read the residual
        # curvature as a finding.
        fam.update_xaxes(type="log", title_text="Hydrocarbon column (m) — log scale")
    else:
        fam.update_yaxes(range=[0, 1.02])
    if probit:
        st.caption(
            "**Probit, and the x-axis has gone logarithmic with it.** A lognormal column-height "
            "distribution is a **straight line** on these axes, so curvature is a departure from "
            "lognormal rather than something to interpret — and the tails, squashed into a few "
            "pixels on a linear axis, open up. The benchmark families are lognormal capacities "
            "clipped at the closure, so each one runs straight and then turns over where the "
            "closure starts binding: **the bend is the fill-to-spill point mass**, and where it "
            "sits is the most useful thing on this chart."
        )
    n.plot(fam, ("**Orange is the prospect you built on tab ③; the dashed grey beside it is the "
                 "benchmark at your own structural relief.** Those two are the like-for-like pair "
                 "— the six coloured curves are the family it sits inside, not its comparators. "
                 "Read the gap between orange and dashed grey: to the right of it your model is "
                 "more optimistic than the empirical record for a closure of this size, to the "
                 "left more pessimistic. **When the prospect has a DHI, its updated curve is drawn "
                 "in red at the same weight** — two readings of one prospect, and the question is "
                 "which of them sits deeper. Neither is dotted, because neither is provisional.  "
                 if limit_set is not None and own_relief else "")
                + f"Column-height exceedance by closure height — **{source}**"
                + ("" if source == "Graham et al. (2015)"
                   else f", at {burial:,.0f} m burial")
                + ". Dotted segments are the filled-to-spill point mass, marked at its height. "
                  "This is the chart shape used as a pre-drill benchmark family across the "
                  "industry; what is new here is the middle option, which draws the published "
                  "estimator on the same axes as the corrected one.")

    rows = []
    for closure in CLOSURE_FAMILY:
        drawn = samples[closure]
        rows.append({
            "Closure height (m)": f"{closure:,.0f}",
            "P90 column (m)": f"{np.percentile(drawn, 10):,.0f}",
            "P50 column (m)": f"{np.percentile(drawn, 50):,.0f}",
            "P10 column (m)": f"{np.percentile(drawn, 90):,.0f}",
            "Fills to spill": f"{np.mean(drawn >= closure - 1e-9):.0%}",
            "Fill fraction, P50": f"{np.percentile(drawn, 50) / closure:.0%}",
        })
    n.table(pd.DataFrame(rows),
            "The same family as numbers. **Fill fraction** is the P50 column as a share of the "
            "closure, and it is the quantity that must fall as closure height rises — a bigger "
            "closure is harder to fill. A benchmark on which it stays flat is telling you the "
            "closure does not bind, which for large closures is not what the data says.")

    if st.session_state.get("dhi_on") and st.session_state.get("dhi_overlay") is not None:
        st.warning(
            "**Read the DHI-updated curve against these benchmarks with care — they cannot be "
            "conditioned the same way.**\n\n"
            "**Graham et al. settle it for their own data**, in their opening sentence: the "
            "synthesis is for column-height modelling *“in the absence of direct hydrocarbon "
            "indicators (DHIs) or known fill controls”*. It is explicitly the **no-DHI prior**, "
            "so judging a DHI-updated distribution against it compares evidence you have with a "
            "curve built for not having it.\n\n"
            "**Edmundson's 242 rows carry no DHI flag at all** — there is no such column, and the "
            "paper does not discuss it. The population is *discoveries*, and a prospect with a "
            "supportive amplitude is more likely to have been drilled, so DHI-supported wells are "
            "over-represented among them by selection.\n\n"
            "**And the bias has a direction this tool can name.** Detectability rises with column "
            "height — that is the detection function `D(h)` on tab ⑤ — so whatever share of "
            "these discoveries was DHI-driven is **enriched in large columns**, because short "
            "columns do not produce mappable anomalies. Comparing your posterior against them "
            "therefore risks **counting the DHI twice**: once in your own update, and once already "
            "baked into a population partly selected by other people's DHIs. It will make you look "
            "*less* optimistic than you are.\n\n"
            "**The geological curve is the like-for-like comparison.** Use the DHI curve to see how "
            "far the evidence moved you, not to judge whether you are calibrated."
        )

    if imported is not None and source == imported_label(imported):
        st.info(
            "**What this series is, precisely.** The C&C and ExxonMobil families are the *same* "
            "banded model, sharing the same fill-to-spill weight. They differ in exactly one "
            "thing: the distribution "
            "drawn when the closure does **not** fill to spill. ExxonMobil draws uniformly between "
            "a 20 m floor and the relief; C&C draws a strongly top-weighted shape over the same "
            "range.\n\n"
            "So this is not a second dataset. It is one modelling choice, and it is worth seeing "
            "how much that single choice moves the answer — compare the fill fractions in the "
            "table above against Graham's. **The parameters are held outside the repository** and "
            "the series simply does not appear on a machine without them."
        )

    if source == "NCS, as the paper fits it":
        st.warning(
            "**This is the published estimator, drawn for comparison, and it should not be used.** "
            "Fitted to observed columns without treating the filled-to-spill discoveries as "
            "censored, it reads each closure's own ceiling as evidence about the seal, and so "
            "overstates how strongly closure height controls column height — elasticity 0.880 "
            "against 0.701 corrected.\n\n"
            "**The consequence is that the family fans out too far**, and it goes the opposite way "
            "at the two ends. At 2 500 m burial it under-fills small closures (P50 82 m of a 100 m "
            "closure, against 100 m corrected; 37 % filling to spill against 59 %) and over-fills "
            "the largest (514 m of an 800 m closure, against 490 m). A prior built from it is "
            "pessimistic on exactly the small closures where the spill point is the binding "
            "control, which is where the censoring it omits does its damage.\n\n"
            "**The sharpest way to see it needs no simulated data at all.** Ask each fit to "
            "reproduce the one statistic everybody can check — how often a discovery fills to "
            "spill. In the 242 discoveries, **45.9 %** do. Draw a column for every discovery at its "
            "own closure height and burial depth: the corrected fit predicts **47.2 %**, the "
            "published fit **32.1 %** — both computed exactly rather than simulated, and both "
            "given the *same* spread so that only the mean function differs. The published "
            "estimator cannot reproduce the filling "
            "behaviour of the dataset it was fitted to, and it fails in the direction the omitted "
            "censoring predicts."
        )

    # ------------------------------------------------------------------ summary
    # -------- Are we optimistic or pessimistic? ------------------------------------------
    theme.heading(TAB, "8 · Am I optimistic or pessimistic?")
    limit_set_cal = st.session_state.get("limit_set")
    if limit_set_cal is None or not own_relief or own_relief <= 0:
        st.info("Build the limits on tab ③ and set a spill point on tab ② to calibrate against "
                "the benchmarks.")
    else:
        from hcwc.core import calibration
        from hcwc.ui import run as engine_run

        built_result = engine_run.current(limit_set_cal)
        built_column = built_result.column_m[built_result.above_minimum]

        st.markdown(
            f"Every benchmark below is evaluated at **this prospect's own structural relief of "
            f"{own_relief:,.0f} m** and its {burial:,.0f} m burial depth, so the comparison is "
            f"like for like rather than against a family your closure is not in.\n\n"
            f"**The number is the exceedance percentile your median column lands on.** If your P50 "
            f"is the benchmark's P25, only a quarter of comparable closures reach it and you are "
            f"optimistic. **Below 50 optimistic, above 50 conservative** — the direction never "
            f"needs interpreting."
        )

        sources = ["NCS, censoring-corrected", "NCS, as the paper fits it",
                   "Graham et al. (2015)"]
        loaded = st.session_state.get("imported_dataset")
        if loaded is not None:
            sources.append(imported_label(loaded))

        comparisons = []
        for label in sources:
            drawn = _samples_for(label, (round(own_relief, 1),), float(burial))
            if not drawn:
                continue
            comparisons.append(
                calibration.compare(built_column, next(iter(drawn.values())), label))

        if not comparisons:
            st.info("No benchmark could be evaluated at this relief.")
        else:
            n.table(
                pd.DataFrame([
                    {"Benchmark": c.name,
                     "Their P90": f"{c.bench_p90:,.0f}",
                     "Their P50": f"{c.bench_p50:,.0f}",
                     "Their P10": f"{c.bench_p10:,.0f}",
                     "Your P50": f"{c.built_p50:,.0f}",
                     "Ratio": f"{c.ratio:.2f}",
                     "Your P50 is their": f"P{c.p50_lands_at:.0f}",
                     "Verdict": c.verdict}
                    for c in comparisons]),
                f"{theme.basis_tag(theme.GEOLOGICAL)} &nbsp; All columns in metres, at "
                f"{own_relief:,.0f} m relief. **Read the last two columns.** The ratio says how far "
                f"apart the medians are; the percentile says how unusual your median would be among "
                f"closures of this size. The spread *between* benchmarks matters too — if you are "
                f"optimistic against one and in line with another, they disagree more than you do.")

            for c in comparisons:
                st.markdown(f"- {c.sentence}")

            qq = go.Figure()
            lo = min(c.bench_p90 for c in comparisons) * 0.75
            hi = max(max(c.built_p10 for c in comparisons),
                     max(c.bench_p10 for c in comparisons)) * 1.1
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

            for c, colour in zip(comparisons, (FITTED, PUBLISHED, "#E8A33D", "#4C72B0")):
                drawn = next(iter(_samples_for(
                    c.name, (round(own_relief, 1),), float(burial)).values()))
                mine, theirs = calibration.quantile_pairs(built_column, drawn)
                share = calibration.corridor_share(built_column, drawn)
                qq.add_scatter(x=theirs, y=mine, mode="lines",
                               name=f"{c.name} — {share:.0%} in band",
                               line=dict(color=colour, width=2.6),
                               hovertemplate=f"{c.name}<br>benchmark %{{x:,.0f}} m<br>"
                                             f"yours %{{y:,.0f}} m<extra></extra>")
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
                                             f"yours %{{y:,.0f}} m<extra></extra>")

            # Anchored to the plot area, not to data: a label positioned in data coordinates on an
            # axis whose range depends on the prospect will eventually fall off the edge, and one
            # of them did.
            qq.add_annotation(xref="paper", yref="paper", x=0.03, y=0.05,
                              text="<b>you predict a TALLER column</b><br>optimistic against the "
                                   "record", showarrow=False, xanchor="left", yanchor="bottom",
                              font=dict(size=11, color="#8A2F33"), align="left")
            qq.add_annotation(xref="paper", yref="paper", x=0.97, y=0.95,
                              text="<b>you predict a SHORTER column</b><br>conservative against "
                                   "the record", showarrow=False, xanchor="right", yanchor="top",
                              font=dict(size=11, color="#2E4C73"), align="right")

            qq.update_layout(xaxis_title="Benchmark column at this relief (m)",
                             height=600, margin=dict(t=20),
                             legend=dict(orientation="h", y=-0.16))
            qq.update_xaxes(range=[lo, hi])
            # Reversed, as Lars asked, and consistent with every other column axis in the tool: a
            # taller column reaches further down the structure, so "further down the page" has to
            # mean "more column" whichever axis it is on. The consequence is that the optimistic
            # zone is the LOWER one, which is why both zones are labelled rather than left to
            # convention.
            qq.update_yaxes(title_text="Your column (m) — larger downward",
                            range=[hi, lo], autorange=False)
            n.plot(qq,
                   f"{theme.basis_tag(theme.GEOLOGICAL)} &nbsp; **Matched quantiles, yours against "
                   f"theirs, with agreement as the dashed diagonal and the two zones named.** The "
                   f"y-axis reads **downward like every other column axis here**, so a taller "
                   f"predicted column falls into the lower, red zone.\n\n"
                   f"**The grey corridor is ±{band:.0%}**, and the legend gives the share of each "
                   f"curve inside it — the number the single percentile cannot: *how much* of the "
                   f"distribution agrees, not just where its median lands. ±{band:.0%} is chosen "
                   f"because the four benchmarks disagree with **each other** by more than that at "
                   f"most reliefs; a tighter band would report you as miscalibrated against a "
                   f"spread the literature does not resolve.\n\n"
                   f"**The shape still matters more than the size.** A curve parallel to the "
                   f"diagonal is uniform bias, which you can correct with one number. A curve that "
                   f"meets the diagonal in the middle and departs at P10 is disagreement "
                   f"**in the upside only** — the tail the volume comes from and the tail that "
                   f"justifies the well.")

            # The same comparison as a ratio, which is the form the question was asked in: *by how
            # much*, and *where*. A Q-Q plot shows two distributions; this shows the one number
            # that separates them, at every percentile, against a flat line at parity.
            ratio = go.Figure()
            # **Exceedance, like every other percentile in this tool.** P100 is the shallowest
            # contact and P0 the deepest, so the shallow end of a column distribution is P99 and
            # the deep end is P1. This axis said the opposite until Lars caught it on 27 Aug 2026
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

            for c, colour in zip(comparisons, (FITTED, PUBLISHED, "#E8A33D", "#4C72B0")):
                drawn = next(iter(_samples_for(
                    c.name, (round(own_relief, 1),), float(burial)).values()))
                ratio.add_scatter(
                    x=probabilities, y=calibration.quantile_ratios(built_column, drawn),
                    mode="lines", name=c.name, line=dict(color=colour, width=2.6),
                    hovertemplate=f"{c.name}<br>exceedance P%{{x:.0f}}<br>"
                                  f"%{{y:.2f}}× the benchmark<extra></extra>")

            ratio.add_annotation(xref="paper", yref="paper", x=0.02, y=0.97,
                                 text="<b>above 1 — you predict more column</b>",
                                 showarrow=False, xanchor="left", yanchor="top",
                                 font=dict(size=11, color="#8A2F33"))
            ratio.add_annotation(xref="paper", yref="paper", x=0.02, y=0.03,
                                 text="<b>below 1 — you predict less</b>", showarrow=False,
                                 xanchor="left", yanchor="bottom",
                                 font=dict(size=11, color="#2E4C73"))
            ratio.update_layout(
                xaxis_title="Exceedance percentile (P99 shallow column → P1 deep column)",
                yaxis_title="Your column ÷ benchmark column",
                height=430, margin=dict(t=20), legend=dict(orientation="h", y=-0.22))
            ratio.update_yaxes(range=[0, 2.0])
            # Reversed so P99 sits on the left: shallow reads left-to-right into deep, the way
            # P90 / P50 / P10 are read aloud, even though the numbers themselves count down.
            ratio.update_xaxes(autorange="reversed")
            n.plot(ratio, optional=True,
                   caption=f"{theme.basis_tag(theme.GEOLOGICAL)} &nbsp; **The same comparison as "
                           f"one number, at every percentile.** Parity is the dashed line, the grey "
                           f"band is ±{calibration.CORRIDOR:.0%}, and the shaded halves say which "
                           f"way you are wrong.\n\n"
                           f"**The percentiles are exceedance percentiles**, as everywhere else "
                           f"here: P100 is the shallowest contact and P0 the deepest, so the "
                           f"shallow end of a column distribution is **P99** and the deep end is "
                           f"**P1**. The axis is reversed so shallow still reads on the left. "
                           f"Nothing about the curve changes — this is a label, and it was the "
                           f"wrong one until 27 Aug 2026.\n\n"
                           f"**The slope is the finding, not the level.** A flat curve away from 1 "
                           f"is a uniform bias — one number wrong, correctable in one place. A "
                           f"curve that *tilts* is a disagreement about **shape**, which no single "
                           f"correction fixes: it means your distribution and the record disagree "
                           f"about how quickly column height runs out as you go down the structure.")

        st.warning(
            "**This is a sanity check, not a score, and the reason is structural.** Every benchmark "
            "is conditioned on **discovery** — your prospect is not one yet and every closure in "
            "these datasets is. Some of \"optimistic against the NCS record\" is a statement about "
            "which wells got written down, not about your model.\n\n"
            "**And a prospect can be legitimately optimistic.** A better seal than the average NCS "
            "closure, or a charge system that fills reliably, is a real thing to believe — it just "
            "has to be believed **on evidence you can name**, not by accident. Use this to find out "
            "which it is."
        )

    theme.heading(TAB, "9 · The base rate for a prospect like yours")
    st.markdown(
        "Edmundson's §5.2 recommends including **base-rate figures** and integrating them with the "
        "geological assessment, citing Milkov (2017) on base-rate neglect — and gives no method "
        "for the combination. This section is the part of that recommendation that carries no "
        "risk: their matrix for a prospect of your dimensions, beside what your limits produced, "
        "with the sample size in view.\n\n"
        "**Nothing here changes a number.** The two are not merged, because merging them needs a "
        "weight nobody can yet defend — see the note under the table."
    )

    matrix_limits = st.session_state.get("limit_set")
    if matrix_limits is None or not own_relief or own_relief <= 0:
        st.info("Build the limits on tab ③ and set a spill point on tab ② to find the matching "
                "cell.")
    else:
        from hcwc.ui import run as engine_run

        matrix = benchmarks.load_edmundson_matrix()
        height_bin = ("0-150m" if own_relief <= 150 else
                      "151-300m" if own_relief <= 300 else "300+m")
        depth_bin = ("0-1500m" if burial <= 1500 else
                     "1501-3000m" if burial <= 3000 else "3000+m")
        cell = matrix[(matrix.trap_height_bin == height_bin)
                      & (matrix.burial_depth_bin == depth_bin)]

        if cell.empty:
            st.info("No cell in the published matrix matches this relief and burial depth.")
        else:
            cell = cell.iloc[0]
            # Restricted to the success cases, because every one of the 242 is a discovery. The
            # comparison is only like-for-like against realisations that would have been drilled
            # and found something.
            built = engine_run.current(matrix_limits)
            fill = np.clip(built.column_m[built.above_minimum] / float(own_relief), 0.0, 1.0)
            bands = ((0.0, 0.5), (0.5, 0.75), (0.75, 0.99))
            mine = [float(((fill > lo) & (fill <= hi)).mean()) for lo, hi in bands]
            mine_spill = float((fill > 0.99).mean())
            theirs = [float(cell.p_fill_0_50), float(cell.p_fill_51_75),
                      float(cell.p_fill_76_99)]

            c1, c2, c3 = st.columns(3)
            c1.metric("Matching cell", f"{height_bin} · {depth_bin}")
            c2.metric("Discoveries in it", f"{int(cell.n)}",
                      "the whole basis for this row", delta_color="off")
            c3.metric("Of those, filled to spill", f"{float(cell.p_fill_100):.0%}",
                      "censored — capacity never observed", delta_color="off")

            comparison = pd.DataFrame([
                {"Trap fill": label, "Your model": f"{a:.1%}", "This cell": f"{b:.1%}",
                 "Difference": f"{a - b:+.1%}"}
                for label, a, b in zip(("0–50%", "51–75%", "76–99%"), mine, theirs)
            ] + [{"Trap fill": "100% — censored", "Your model": f"{mine_spill:.1%}",
                  "This cell": f"{float(cell.p_fill_100):.1%}",
                  "Difference": f"{mine_spill - float(cell.p_fill_100):+.1%}"}])

            fig_base = go.Figure()
            fig_base.add_bar(x=mine + [mine_spill],
                             y=["0–50%", "51–75%", "76–99%", "100%"], orientation="h",
                             name="your model",
                             marker_color=theme.BASIS_COLOUR[theme.GEOLOGICAL])
            fig_base.add_bar(y=["0–50%", "51–75%", "76–99%", "100%"],
                             x=theirs + [float(cell.p_fill_100)], orientation="h",
                             name=f"NCS base rate (n = {int(cell.n)})", marker_color="#8172B2")
            fig_base.update_layout(barmode="group", height=330, margin=dict(t=20),
                                   xaxis_title="Share of cases", xaxis_tickformat=".0%",
                                   yaxis_title="Trap fill", yaxis=dict(autorange="reversed"),
                                   legend=dict(orientation="h", y=-0.28))
            n.plot(fig_base,
                   f"**Your competing limits against the {int(cell.n)} NCS discoveries in the same "
                   f"trap-height and burial-depth cell.** Restricted to your success cases, because "
                   "every one of theirs is a discovery.\n\n"
                   "**Read the bottom pair apart from the other three.** The 100 % bar is not a "
                   "fill outcome — it is the share of traps whose seal capacity was never "
                   "observed, because geometry stopped the column first. It is a right-censoring "
                   "rate, and comparing your model's filled-to-spill share against it compares "
                   "two different kinds of number.")
            n.table(comparison,
                    "**A disagreement here is a finding, not an error.** The base rate describes "
                    "what was drilled and found on the NCS; your model describes what your "
                    "mechanisms allow. They are built from different information and are allowed "
                    "to differ — the question a difference raises is *which of my elicited limits "
                    "would have to move to close it*, and §8 above answers the direction.")

            st.warning(
                f"**This informs the contact distribution and never the chance.** The matrix is "
                f"`P(trap fill | discovery)` — all {int(cell.n)} of those traps had hydrocarbons "
                "in them. Used against POS it would silently condition on success, which is "
                "precisely the error the rest of this tool is arranged to prevent. Moving a "
                "chance would need a dataset containing dry holes, and this one has none.\n\n"
                f"**And {int(cell.n)} discoveries is a thin basis.** Letting a cell this size "
                "reshape a ten-thousand-realisation mechanistic model would be a strong move on "
                "weak evidence, which is why the two are shown side by side and not combined. "
                "The honest use is to notice a disagreement and go back to the limit that causes "
                "it."
            )

            with st.expander("**A note on combining a base rate with a prospect estimate** — "
                             "and one arithmetic to avoid"):
                st.markdown(
                    "Milkov (2017) is right about the problem, and the paper is worth reading: "
                    "explorers do under-use population frequencies, and a portfolio that ignores "
                    "them drifts. Nothing below disputes that.\n\n"
                    "**The difficulty is in the arithmetic usually attached to it.** The "
                    "combination rule takes the base rate `b` and the prospect's own PoS `q` and "
                    "multiplies their odds:"
                )
                st.latex(r"P_{\mathrm{updated}} = \frac{b\,q}{b\,q + (1-b)(1-q)}")
                st.markdown(
                    "**That rule is symmetric.** Feed it a base rate of 0.2 and a prospect PoS of "
                    "0.9 and it returns 69.2 %; feed it 0.9 and 0.2 and it returns 69.2 % again. "
                    "It cannot tell which input is the population and which is the prospect — and "
                    "**a Bayesian update is never symmetric between a prior and its evidence.** "
                    "That symmetry is the diagnostic: what the formula performs is a *fusion of "
                    "two opinions*, not an update of one by the other.\n\n"
                    "Two consequences follow, and both cut against the paper's own purpose:\n\n"
                    "- **A confident assessor erases the base rate entirely.** At `q = 1` the "
                    "result is 1 whatever `b` is; at `q = 0` it is 0. The base rate has no "
                    "influence exactly where over-confidence needs restraining.\n"
                    "- **It double-counts whenever the assessor already used base-rate "
                    "knowledge** — which is the behaviour the paper is asking for.\n\n"
                    "The underlying assumption is that both numbers are likelihood ratios against "
                    "an even prior. A geologist who says *20 %* is not saying that; they are "
                    "stating a probability that already contains a prior of their own.\n\n"
                    "**Why this section stops where it does.** Combining a base rate with a "
                    "prospect estimate needs a stated weight and a defence of it, and no rule that "
                    "hides the weight inside an identity can supply one. So the two are shown side "
                    "by side above and not merged.\n\n"
                    "*The formula quoted here reproduces a spreadsheet implementation exactly "
                    "(99 of 99 rows, to machine precision) against the paper's own 25-well "
                    "dataset. The paper itself is paywalled and has not been read directly, so it "
                    "is quoted as the rule commonly applied rather than verbatim from the text. "
                    "Schofield (GEOAdvisors) raises a separate and independent objection about the "
                    "choice of reference class — pooling the mature North Sea with the emerging "
                    "Barents.*"
                )

    theme.heading(TAB, "10 · What we are and are not claiming")
    left, right = st.columns(2)
    left.success(
        "**Stands**\n\n"
        "- The dataset itself, and the decision to publish it openly.\n"
        "- Closure height is a genuine control on column height.\n"
        "- The core message: one pre-drill distribution does not fit all prospects.\n"
        "- The fitted correction is calibrated band by band."
    )
    right.error(
        "**Does not stand, or needs qualifying**\n\n"
        "- Burial depth as the *weaker* control — corrected, it roughly doubles.\n"
        "- The magnitude of the closure-height control — overstated, and still an upper bound.\n"
        "- Reading the four trap-fill bins together as a column-height distribution: the 100 % bin "
        "is a **censoring rate**, not a fill outcome like the other three."
    )
    st.markdown(
        """
**Two selection effects remain uncorrected in every analysis on this page, ours included:**

1. **Discovery-only conditioning.** Dry wells are excluded by construction — the paper says so. This
   is `P(column | discovery)`, not `P(column)`.
2. **Left-truncation at the well's reservoir entry depth.** If the true contact sits *above* where
   the well entered the reservoir, the well finds water and is logged as a dry hole. The
   small-column tail is missing from every discovery dataset.

Stacked, the empirical record is **truncated below and censored above**, and both push it to look
better filled than reality. **Used as a pre-drill prior it is optimistic at both ends.**
"""
    )
    st.caption(
        "Data: Edmundson, I., Davies, R., Frette, L.U., Mackie, S., Kavli, E.A., Rotevatn, A., "
        "Yielding, G. & Dunbar, A. (2021), AAPG Bulletin 105(12), 2381–2403, "
        "doi:10.1306/03122119223. Raw table https://osf.io/6ysbv/ under CC-BY 4.0. "
        "Full references in tab ⑧."
    )
