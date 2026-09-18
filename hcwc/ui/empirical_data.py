"""The data behind tab 6.0: the fits, the samplers and the probit axis.

Split out of ``empirical.py``, which had reached 1 334 lines — the largest module in the repo by a
third, holding ten sections across five subjects that share a tab and almost nothing else. The cost
was not tidiness: a straight-line render function that long, whose later sections depend on locals
from earlier ones, is one nobody wants to restructure, and the Diagnostics block became an expander
rather than a sub-tab for exactly that reason.

**This is the half that is not a render.** Everything here is a pure function of its arguments, all
of it cached, none of it touching the page — so it can be read, tested and changed without holding
the tab in your head. What is left in ``empirical.py`` is the drawing.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import streamlit as st
from scipy.stats import norm

from hcwc.core import censoring, engine
from hcwc.io import benchmarks

REFERENCE = Path(__file__).resolve().parents[2] / "reference"

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


@st.cache_data(show_spinner=False, max_entries=4, ttl=3600)
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


@st.cache_data(show_spinner=False, max_entries=12, ttl=3600)
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
    return engine.exceedance(samples, grid)


def _p_spill(fit, h, z):
    mu = (fit.intercept + fit.coefficients["trap_height"] * np.log(h)
          + fit.coefficients["burial_depth"] * np.log(z))
    return norm.sf((np.log(h) - mu) / fit.sigma)


@st.cache_data(show_spinner=False, max_entries=12, ttl=3600)
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


