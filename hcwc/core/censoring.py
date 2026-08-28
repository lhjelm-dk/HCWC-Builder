"""Filled-to-spill observations are right-censored. Treat them that way.

The problem
-----------
For a discovery we can measure the trap height ``H`` (apex to spill) and the observed
hydrocarbon column ``C``. What we actually want, for a pre-drill column-height
distribution, is the *seal capacity* ``S`` — the column the seal could support. The
three are related by exactly the competing-limits identity this whole tool is built on::

    C = min(S, H)

So:

* **Underfilled** (``C < H``) — the seal bound the column, and ``C = S``. We observe ``S``.
* **Filled to spill** (``C = H``) — geometry bound the column, and all we learn is
  ``S >= H``. We do **not** observe ``S``. This is a right-censored observation.

Hood (2019) states the geology of this plainly: pools controlled by geometric limits
"document the minimum column that the seal can support but not the upper limit". What
nobody appears to have done is carry that statement into the statistics. Published
column-height studies regress ``C`` on ``H``, and report a correlation, over datasets in
which roughly half the points are filled to spill and therefore sit *exactly* on the
line ``C = H`` by definition rather than by physics.

Why that matters, in one number
-------------------------------
Simulate seal capacity that is **completely independent** of trap height — zero physics,
by construction — let ``C = min(S, H)``, and regress ``C`` on ``H`` over 242 points, the
size of the Edmundson dataset. Naive OLS returns a slope near **0.58** and a Pearson
``r`` near **0.56**: a "strong positive correlation" that is a pure artefact of the
censoring. See ``tests/test_censoring.py``, which asserts this.

Dropping the filled-to-spill points does **not** fix it. That trades censoring bias for
truncation bias — conditioning on ``S < H`` keeps only low ``S`` at low ``H``, which
manufactures the same positive relationship a second way. In the same simulation the
filtered slope is ~0.54, no better than the naive one.

:func:`censored_slope` fits the relationship by maximum likelihood with the censoring
modelled, and recovers the true slope to three decimals.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm


@dataclass(frozen=True)
class CensoredFit:
    """A right-censored log-linear fit of seal capacity on a predictor.

    ``slope`` is on log-log axes, so it is an elasticity: a slope of 1.0 means seal
    capacity scales in proportion to the predictor. ``n_censored`` is reported because
    it is the single number that decides how much the naive estimate would have lied —
    it is the fraction of the dataset carrying no information about ``S`` at all.
    """
    intercept: float
    slope: float
    sigma: float
    n_total: int
    n_censored: int
    converged: bool

    @property
    def censored_fraction(self) -> float:
        return self.n_censored / self.n_total if self.n_total else 0.0


def spill_censoring(column: np.ndarray, trap_height: np.ndarray,
                    tol_m: float = 1.0) -> np.ndarray:
    """Which observations are filled to spill, and therefore right-censored.

    ``tol_m`` exists because measured contacts and mapped spill points never agree to
    the metre. A trap-fill ratio of 0.997 is filled to spill; treating it as an exact
    observation of seal capacity would be reading noise as signal. One metre is a
    deliberately tight default — it should be set from the depth-conversion uncertainty
    of the dataset, not left at whatever shipped.
    """
    column = np.asarray(column, dtype=float)
    trap_height = np.asarray(trap_height, dtype=float)
    if column.shape != trap_height.shape:
        raise ValueError("column and trap_height must have the same shape")
    if np.any(column > trap_height + tol_m):
        raise ValueError(
            "some columns exceed their trap height by more than the tolerance; "
            "a column cannot be taller than its closure, so check the mapping or the units"
        )
    return column >= trap_height - tol_m


def censored_slope(predictor: np.ndarray, column: np.ndarray,
                   trap_height: np.ndarray, *, tol_m: float = 1.0) -> CensoredFit:
    """Fit ``log S = a + b·log(predictor) + eps`` with filled-to-spill right-censored.

    ``predictor`` is whatever you are testing the seal capacity against — trap height
    (the Edmundson Fig. 7 regression) or burial depth. Passing trap height is the
    interesting case, because that is the regression the censoring corrupts most.

    The likelihood has two kinds of term. Underfilled points contribute a normal density
    at the observed ``log C``. Filled-to-spill points contribute a survival term,
    ``P(log S >= log H)`` — all the information a censored point carries.
    """
    x = np.log(np.asarray(predictor, dtype=float))
    y = np.log(np.asarray(column, dtype=float))
    censored = spill_censoring(column, trap_height, tol_m=tol_m)
    observed = ~censored

    if observed.sum() < 3:
        raise ValueError(
            f"only {observed.sum()} underfilled observations; the seal-capacity "
            "relationship is not identifiable from an almost entirely censored sample"
        )

    def negative_log_likelihood(params: np.ndarray) -> float:
        intercept, slope, log_sigma = params
        sigma = np.exp(log_sigma)
        mu = intercept + slope * x
        ll = norm.logpdf(y[observed], mu[observed], sigma).sum()
        if censored.any():
            ll += norm.logsf(y[censored], mu[censored], sigma).sum()
        return -ll

    # Seed from the naive fit on the uncensored points. It is biased -- that is the whole
    # point of this module -- but it is in the right part of the space to start from.
    seed_slope, seed_intercept = np.polyfit(x[observed], y[observed], 1)
    seed_sigma = float(np.std(y[observed] - (seed_intercept + seed_slope * x[observed])))
    result = minimize(
        negative_log_likelihood,
        np.array([seed_intercept, seed_slope, np.log(max(seed_sigma, 1e-3))]),
        method="Nelder-Mead",
        options={"maxiter": 5000, "xatol": 1e-8, "fatol": 1e-8},
    )
    intercept, slope, log_sigma = result.x
    return CensoredFit(
        intercept=float(intercept),
        slope=float(slope),
        sigma=float(np.exp(log_sigma)),
        n_total=int(x.size),
        n_censored=int(censored.sum()),
        converged=bool(result.success),
    )


@dataclass(frozen=True)
class CensoredMultiFit:
    """A right-censored log-linear fit against several predictors at once.

    Needed because trap height and burial depth have to be separated: censoring biases
    the two in *opposite directions*, so fitting them one at a time cannot show it.
    ``log_likelihood`` is kept so nested models can be compared by likelihood ratio.
    """
    intercept: float
    coefficients: dict[str, float]
    sigma: float
    log_likelihood: float
    n_total: int
    n_censored: int
    converged: bool


def censored_loglinear(predictors: dict[str, np.ndarray], column: np.ndarray,
                       trap_height: np.ndarray, *, tol_m: float = 1.0) -> CensoredMultiFit:
    """Fit ``log S = a + sum_k b_k log(x_k) + eps``, right-censored at the spill point.

    Coefficients are log-log elasticities. Pass ``{"trap_height": H, "burial_depth": D}``
    to get the result that matters: on the published NCS data the naive fit reports
    ``b_trap_height = 0.880`` and ``b_burial_depth = 0.143``, while the censored fit
    reports ``0.701`` and ``0.277`` at the default tolerance. Censoring *inflates* the trap-height term and
    *halves* the burial-depth term, which is why "burial depth is the weaker control"
    does not survive the correction.

    **The trap-height coefficient is mildly sensitive to** ``tol_m``, which decides how close to
    its closure a column has to be before it counts as censored: 0.720 at 0.5 m, 0.701 at the
    1 m default, 0.697 at 2 m. Worth knowing before quoting the third decimal -- an earlier version
    of this docstring quoted 0.721, which is the 0.5 m answer, against a function that defaults to
    1 m.
    """
    if not predictors:
        raise ValueError("at least one predictor is required")
    y = np.log(np.asarray(column, dtype=float))
    names = list(predictors)
    design = np.column_stack(
        [np.ones(y.size)] + [np.log(np.asarray(predictors[k], dtype=float)) for k in names]
    )
    censored = spill_censoring(column, trap_height, tol_m=tol_m)
    observed = ~censored
    if observed.sum() <= design.shape[1]:
        raise ValueError(
            f"{observed.sum()} underfilled observations cannot identify "
            f"{design.shape[1]} parameters"
        )

    def negative_log_likelihood(params: np.ndarray) -> float:
        beta, sigma = params[:-1], np.exp(params[-1])
        mu = design @ beta
        ll = norm.logpdf(y[observed], mu[observed], sigma).sum()
        if censored.any():
            ll += norm.logsf(y[censored], mu[censored], sigma).sum()
        return -ll

    seed, *_ = np.linalg.lstsq(design[observed], y[observed], rcond=None)
    resid = float(np.std(y[observed] - design[observed] @ seed))
    result = minimize(
        negative_log_likelihood,
        np.append(seed, np.log(max(resid, 1e-3))),
        method="Nelder-Mead",
        options={"maxiter": 40000, "maxfev": 40000, "xatol": 1e-9, "fatol": 1e-9},
    )
    return CensoredMultiFit(
        intercept=float(result.x[0]),
        coefficients={k: float(v) for k, v in zip(names, result.x[1:-1])},
        sigma=float(np.exp(result.x[-1])),
        log_likelihood=float(-result.fun),
        n_total=int(y.size),
        n_censored=int(censored.sum()),
        converged=bool(result.success),
    )


def naive_slope(predictor: np.ndarray, column: np.ndarray) -> float:
    """The log-log OLS slope a published study would report. Here to be compared against."""
    x = np.log(np.asarray(predictor, dtype=float))
    y = np.log(np.asarray(column, dtype=float))
    return float(np.polyfit(x, y, 1)[0])


def filtered_slope(predictor: np.ndarray, column: np.ndarray,
                   trap_height: np.ndarray, *, tol_m: float = 1.0) -> float:
    """OLS slope after dropping the filled-to-spill points — the tempting fix that fails.

    Kept as a named function precisely so the test suite can demonstrate that it does not
    work, rather than leaving the next person to rediscover it.
    """
    censored = spill_censoring(column, trap_height, tol_m=tol_m)
    return naive_slope(np.asarray(predictor)[~censored], np.asarray(column)[~censored])
