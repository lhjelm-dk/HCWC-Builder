"""The distributions an assessor actually elicits, in the parameterisations they are
elicited in.

Four of the five below are @RISK's parameterisations, named here because they are
defined by that software rather than by convention and there is no other unambiguous
way to say which function is meant. ``RiskBetaSubj`` in particular is not the
"subjective beta" of any textbook, and SCOPE-HC's ``sample_beta_subjective`` is a
different function with the same English name (it fits P10/P50/P90; this one takes
min/mode/mean/max). Both are useful; they are not interchangeable, so both names are
spelled out in full here to stop anyone reaching for the wrong one.

Everything is vectorised on a ``numpy.random.Generator`` and returns an array, because
the engine samples every limit for every realisation at once.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import beta, norm


def bernoulli(rng: np.random.Generator, p: float, n: int) -> np.ndarray:
    """``RiskBernoulli(p)`` -- 1 with probability ``p``, else 0.

    Returned as ``bool`` rather than ``int``: every use in the engine is a mask over
    "is this limit active in this realisation", and a boolean says that out loud.
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"probability must be in [0, 1], got {p}")
    return rng.random(n) < p


def normal_alt(rng: np.random.Generator, p1: float, x1: float,
               p2: float, x2: float, n: int) -> np.ndarray:
    """``RiskNormalAlt(p1, x1, p2, x2)`` -- the normal with ``F(x1)=p1``, ``F(x2)=p2``.

    Preferred to mean/sd throughout because an assessor can state "I am 99 % sure it is
    deeper than 340 m" and cannot state a standard deviation.
    """
    mu, sigma = normal_alt_params(p1, x1, p2, x2)
    return rng.normal(mu, sigma, n)


def normal_alt_params(p1: float, x1: float, p2: float, x2: float) -> tuple[float, float]:
    """The ``(mu, sigma)`` behind :func:`normal_alt`.

    Split out so tests can assert on the parameters rather than on samples -- and so the
    validation lives here, on the path *both* callers take, rather than only on the
    sampling wrapper.
    """
    if not (0.0 < p1 < 1.0 and 0.0 < p2 < 1.0):
        raise ValueError("percentiles must be strictly inside (0, 1)")
    if p1 == p2:
        raise ValueError("the two percentiles must differ")
    z1, z2 = norm.ppf(p1), norm.ppf(p2)
    sigma = (x2 - x1) / (z2 - z1)
    if sigma <= 0:
        raise ValueError(
            f"percentiles imply a non-positive sigma ({sigma:.6g}); "
            "check that x2 is on the same side of the distribution as p2"
        )
    return x1 - sigma * z1, sigma


def beta_general(rng: np.random.Generator, alpha1: float, alpha2: float,
                 minimum: float, maximum: float, n: int) -> np.ndarray:
    """``RiskBetaGeneral(a1, a2, min, max)`` -- Beta(a1, a2) rescaled onto [min, max]."""
    if alpha1 <= 0 or alpha2 <= 0:
        raise ValueError("both shape parameters must be positive")
    if maximum <= minimum:
        raise ValueError(f"max ({maximum}) must exceed min ({minimum})")
    return minimum + rng.beta(alpha1, alpha2, n) * (maximum - minimum)


def beta_subj_params(minimum: float, mode: float, mean: float,
                     maximum: float) -> tuple[float, float]:
    """Shape parameters for ``RiskBetaSubj(min, mode, mean, max)``.

    @RISK's construction: a four-point elicitation solved for the Beta that has exactly
    that mode and that mean on that support. It is over-determined in the sense that not
    every (mode, mean) pair is reachable -- the caller has to have elicited a coherent
    pair, and the checks below are where an incoherent one gets caught rather than
    silently producing a plausible-looking wrong distribution.

    The characteristic failure is a mode outside the support -- asking for a mode of 800 m
    on a distribution whose maximum is the 350 m structural relief. A spreadsheet answers
    that with ``#VALUE!`` in a cell nobody reads; here it raises with the reason.
    """
    if not minimum < maximum:
        raise ValueError(f"max ({maximum}) must exceed min ({minimum})")
    if not minimum <= mode <= maximum:
        raise ValueError(f"mode ({mode}) must lie within [{minimum}, {maximum}]")
    if not minimum < mean < maximum:
        raise ValueError(f"mean ({mean}) must lie strictly within ({minimum}, {maximum})")
    # The midpoint test comes first because it is the more fundamental of the two failures and the
    # only one that names a fix: a mode at the centre of the support kills the construction whatever
    # the mean is, whereas mode == mean is only a problem given some mode. A symmetric
    # four-point elicitation such as RiskBetaSubj(330, 350, 350, 370) trips both, and
    # "use PERT" is the more useful thing to be told.
    if abs(2.0 * mode - minimum - maximum) < 1e-12:
        raise ValueError(
            f"the mode ({mode}) sits exactly at the midpoint of [{minimum}, {maximum}], so the "
            "four points determine symmetry but not shape and no BetaSubj exists. Use PERT, which "
            "is defined for a symmetric three-point elicitation."
        )
    if mode == mean:
        # The limit is symmetric-Beta-like but the formula divides by (mode - mean).
        # Nudging it would hide an elicitation that carries no shape information.
        raise ValueError("mode and mean must differ; they carry the shape between them")

    span = maximum - minimum
    numerator = (mean - minimum) * (2.0 * mode - minimum - maximum)
    denominator = (mode - mean) * span
    alpha1 = numerator / denominator
    alpha2 = alpha1 * (maximum - mean) / (mean - minimum)
    if alpha1 <= 0 or alpha2 <= 0:
        raise ValueError(
            f"min={minimum}, mode={mode}, mean={mean}, max={maximum} imply non-positive "
            f"shapes (a1={alpha1:.4g}, a2={alpha2:.4g}); the mode and mean disagree about "
            "which way the distribution is skewed"
        )
    return alpha1, alpha2


def beta_subj(rng: np.random.Generator, minimum: float, mode: float, mean: float,
              maximum: float, n: int) -> np.ndarray:
    """``RiskBetaSubj(min, mode, mean, max)`` -- the retention-limit workhorse."""
    alpha1, alpha2 = beta_subj_params(minimum, mode, mean, maximum)
    return beta_general(rng, alpha1, alpha2, minimum, maximum, n)


def pert(rng: np.random.Generator, minimum: float, mode: float, maximum: float,
         n: int, lam: float = 4.0) -> np.ndarray:
    """PERT -- a smooth three-point alternative where no mean has been elicited.

    Offered because a PERT is the usual stand-in for ``RiskBetaSubj`` when no mean has
    been elicited, and keeping both available lets the tests quantify what that
    approximation costs rather than leaving it assumed.
    """
    if not minimum < maximum:
        raise ValueError(f"max ({maximum}) must exceed min ({minimum})")
    if not minimum <= mode <= maximum:
        raise ValueError(f"mode ({mode}) must lie within [{minimum}, {maximum}]")
    span = maximum - minimum
    alpha1 = 1.0 + lam * (mode - minimum) / span
    alpha2 = 1.0 + lam * (maximum - mode) / span
    return beta_general(rng, alpha1, alpha2, minimum, maximum, n)


# --------------------------------------------------------------------------- inverse CDFs
# The engine samples through these rather than through the `rng.*` draws above, so that a
# Gaussian copula can be dropped in later without touching any limit definition: correlation
# becomes a matter of *where the uniforms come from*, and nothing else changes. Sampling
# `u ~ U(0,1)` and taking `ppf(u)` is identical in distribution to drawing directly.

def normal_alt_ppf(u: np.ndarray, p1: float, x1: float, p2: float, x2: float) -> np.ndarray:
    """Quantile function for :func:`normal_alt`."""
    mu, sigma = normal_alt_params(p1, x1, p2, x2)
    return norm.ppf(u, loc=mu, scale=sigma)


def beta_general_ppf(u: np.ndarray, alpha1: float, alpha2: float,
                     minimum: float, maximum: float) -> np.ndarray:
    """Quantile function for :func:`beta_general`."""
    if alpha1 <= 0 or alpha2 <= 0:
        raise ValueError("both shape parameters must be positive")
    if maximum <= minimum:
        raise ValueError(f"max ({maximum}) must exceed min ({minimum})")
    return minimum + beta.ppf(u, alpha1, alpha2) * (maximum - minimum)


def beta_subj_ppf(u: np.ndarray, minimum: float, mode: float, mean: float,
                  maximum: float) -> np.ndarray:
    """Quantile function for :func:`beta_subj`."""
    alpha1, alpha2 = beta_subj_params(minimum, mode, mean, maximum)
    return beta_general_ppf(u, alpha1, alpha2, minimum, maximum)


def pert_ppf(u: np.ndarray, minimum: float, mode: float, maximum: float,
             lam: float = 4.0) -> np.ndarray:
    """Quantile function for :func:`pert`."""
    if not minimum < maximum:
        raise ValueError(f"max ({maximum}) must exceed min ({minimum})")
    if not minimum <= mode <= maximum:
        raise ValueError(f"mode ({mode}) must lie within [{minimum}, {maximum}]")
    span = maximum - minimum
    return beta_general_ppf(u, 1.0 + lam * (mode - minimum) / span,
                            1.0 + lam * (maximum - mode) / span, minimum, maximum)


def uniform_ppf(u: np.ndarray, minimum: float, maximum: float) -> np.ndarray:
    """Quantile function for a uniform. Graham's underfilled branch is one of these."""
    if maximum <= minimum:
        raise ValueError(f"max ({maximum}) must exceed min ({minimum})")
    return minimum + np.asarray(u) * (maximum - minimum)
