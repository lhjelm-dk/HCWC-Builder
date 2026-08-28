"""Correlated sampling, by Gaussian copula.

The engine draws one uniform per limit per realisation and takes each limit's quantile function.
That was arranged deliberately in Phase 2: correlation is then entirely a question of **where the
uniforms come from**, and no limit definition has to know anything about it. This module is the
"where".

The construction is lifted from SCOPE-HC's ``scopehc/sampling.py`` — Higham (2002) nearest-
correlation projection, then Cholesky, then the normal CDF — because it is already written, already
in use, and handles the awkward cases. Two things are added here.

**Rank correlation in, copula parameter out.** An assessor who says "these two are 0.7 correlated"
means a *rank* correlation, and so does @RISK: ``RiskCorrmat`` is Spearman, applied by Iman–Conover.
A Gaussian copula's parameter is a correlation on the **normal scores**, which is a different
number. For a Gaussian copula they are related exactly by ``rho_s = (6/pi) arcsin(rho/2)``, so the
input is taken as Spearman and converted. Skipping that step would quietly deliver a weaker
correlation than the one asked for — about 4 % low at 0.7, and it is free to get right.

**Two failure modes this is written against**, both of which are easy to commit in a spreadsheet
and invisible afterwards. A pair declared at **1.0** is perfect dependence — a claim that two
limits are the same rock, not merely that they are related. And a correlation matrix that is
*referenced* but empty leaves the pair uncorrelated while every label says otherwise; here an
undeclared pair is explicitly independent, and :func:`describe` prints what was asked for beside
what was sampled.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

#: Beyond this, a Cholesky factor is numerically unusable and the pair is treated as perfectly
#: dependent instead. SCOPE-HC uses the same threshold.
PERFECT = 0.999


def spearman_to_gaussian(rho_s: float | np.ndarray) -> float | np.ndarray:
    """Rank correlation to the Gaussian copula's normal-score parameter.

    ``rho = 2 sin(pi rho_s / 6)``, the exact inverse of ``rho_s = (6/pi) arcsin(rho/2)``.
    """
    return 2.0 * np.sin(np.pi * np.asarray(rho_s, dtype=float) / 6.0)


def gaussian_to_spearman(rho: float | np.ndarray) -> float | np.ndarray:
    """The forward direction, for reporting what a fitted copula actually implies."""
    return (6.0 / np.pi) * np.arcsin(np.asarray(rho, dtype=float) / 2.0)


def _force_psd(m: np.ndarray, floor: float = 1e-10) -> np.ndarray:
    """Clip the eigenvalues at ``floor`` and renormalise back to a unit diagonal.

    Rescaling by ``D^-1/2 M D^-1/2`` preserves positive definiteness, so this **guarantees** a
    usable correlation matrix. It is not the *nearest* one — that is Higham's job — which is why it
    runs only as a final safety net.
    """
    eigval, eigvec = np.linalg.eigh(0.5 * (m + m.T))
    out = (eigvec * np.clip(eigval, floor, None)) @ eigvec.T
    scale = np.sqrt(np.diag(out))
    out = out / np.outer(scale, scale)
    out = 0.5 * (out + out.T)
    np.fill_diagonal(out, 1.0)
    return out


def nearest_correlation_matrix(a: np.ndarray, tol: float = 1e-10,
                               max_iter: int = 200) -> np.ndarray:
    """Higham (2002) alternating projection onto the nearest valid correlation matrix.

    Elicited correlations are almost never internally consistent — say A and B are 0.9 correlated,
    B and C are 0.9, and A and C are −0.9, and no set of random variables has that matrix. Refusing
    would be unhelpful; the projection finds the closest matrix that *is* achievable, which is what
    the assessor meant.

    **Not lifted verbatim from SCOPE-HC, and the difference matters.** That implementation computes
    the Dykstra correction ``dS = X - R`` *after* forcing the unit diagonal, so the correction
    absorbs both projections rather than only the positive-semi-definite one, and the iteration does
    not converge. It also clips the result to ±0.999 at the end, which can reintroduce
    indefiniteness in a matrix that had just been repaired. On the example above it returns a matrix
    whose smallest eigenvalue is still **−0.267**, and `validate_dependency_matrix` reports that as
    valid — so SCOPE-HC accepts the input and then raises `LinAlgError` from inside
    `correlated_samples`. Worth fixing there; see the note in `docs/HCWC_Builder_PLAN.md`.

    Here the correction is taken from the PSD projection alone, convergence is tested on the actual
    iterate, and :func:`_force_psd` runs afterwards so a Cholesky factor always exists.
    """
    x = 0.5 * (np.array(a, dtype=float, copy=True) + np.array(a, dtype=float).T)
    np.fill_diagonal(x, 1.0)
    y = x.copy()
    delta = np.zeros_like(x)
    previous = y.copy()
    for _ in range(max_iter):
        r = y - delta
        eigval, eigvec = np.linalg.eigh(r)
        psd = (eigvec * np.clip(eigval, 0.0, None)) @ eigvec.T
        psd = 0.5 * (psd + psd.T)
        delta = psd - r                       # the PSD projection only, not the diagonal fix
        y = psd.copy()
        np.fill_diagonal(y, 1.0)
        if np.linalg.norm(y - previous, ord="fro") <= tol * max(1.0,
                                                                np.linalg.norm(y, ord="fro")):
            break
        previous = y.copy()
    off = ~np.eye(y.shape[0], dtype=bool)
    y[off] = np.clip(y[off], -PERFECT, PERFECT)
    return _force_psd(y)


def build_matrix(names: tuple[str, ...], pairs: dict[str, float]) -> np.ndarray:
    """A Spearman correlation matrix from ``{"A|B": rho}`` entries.

    Pairs, not a full matrix, because a full matrix over fourteen limits is 91 numbers and nobody
    fills that in. An assessor states the two or three couplings they actually believe in and the
    rest are zero — which is a modelling statement, and the right default.
    """
    index = {name: i for i, name in enumerate(names)}
    matrix = np.eye(len(names))
    for key, rho in pairs.items():
        try:
            left, right = key.split("|")
        except ValueError:
            raise ValueError(f"correlation key {key!r} must be 'name|name'") from None
        if left not in index or right not in index:
            missing = [x for x in (left, right) if x not in index]
            raise KeyError(f"correlation {key!r} names limits that do not exist: {missing}")
        if left == right:
            raise ValueError(f"correlation {key!r} pairs a limit with itself")
        if not -1.0 <= rho <= 1.0:
            raise ValueError(f"correlation {key!r} is {rho}, outside [-1, 1]")
        matrix[index[left], index[right]] = matrix[index[right], index[left]] = float(rho)
    return matrix


def correlated_uniforms(rng: np.random.Generator, spearman: np.ndarray, n: int) -> np.ndarray:
    """``(n, k)`` uniforms with the requested **rank** correlation structure.

    Independent columns come out of this unchanged in distribution, so the engine can call it
    unconditionally: an identity matrix gives exactly ``rng.random((n, k))`` in distribution.
    """
    spearman = np.asarray(spearman, dtype=float)
    if spearman.ndim != 2 or spearman.shape[0] != spearman.shape[1]:
        raise ValueError("the correlation matrix must be square")
    if not np.allclose(spearman, spearman.T, atol=1e-8):
        raise ValueError("the correlation matrix must be symmetric")
    if not np.allclose(np.diag(spearman), 1.0, atol=1e-8):
        raise ValueError("the correlation matrix must have 1.0 on the diagonal")

    k = spearman.shape[0]
    rho = nearest_correlation_matrix(spearman_to_gaussian(spearman))
    z = rng.standard_normal((n, k))
    try:
        chol = np.linalg.cholesky(rho)
    except np.linalg.LinAlgError as exc:  # pragma: no cover - Higham should prevent this
        raise np.linalg.LinAlgError(
            "no Cholesky factor even after the Higham projection; the requested correlations are "
            "further from achievable than the projection could repair"
        ) from exc
    return norm.cdf(z @ chol.T)


def realised_spearman(uniforms: np.ndarray) -> np.ndarray:
    """The rank correlation actually delivered, for checking against what was asked for.

    Always a ``(k, k)`` matrix. ``scipy.stats.spearmanr`` returns a **scalar** for exactly two
    columns and a matrix for three or more, which is the kind of shape-dependent return that turns
    into an ``IndexError`` on the one case a test happens not to cover.
    """
    from scipy.stats import spearmanr
    k = uniforms.shape[1]
    if k < 2:
        return np.ones((k, k))
    if k == 2:
        rho = float(spearmanr(uniforms[:, 0], uniforms[:, 1]).statistic)
        return np.array([[1.0, rho], [rho, 1.0]])
    return np.asarray(spearmanr(uniforms).statistic, dtype=float)


def describe(names: tuple[str, ...], spearman: np.ndarray,
             threshold: float = 0.005) -> list[tuple[str, str, float, float]]:
    """Non-trivial pairs as ``(a, b, requested, achievable)``.

    The two numbers differ where the elicited matrix was not positive semi-definite and the Higham
    projection had to move it. Showing both is the point: a correlation silently reduced from 0.9 to
    0.6 because of what was said about a third limit is something the assessor should see.
    """
    fixed = gaussian_to_spearman(nearest_correlation_matrix(spearman_to_gaussian(spearman)))
    out = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if abs(spearman[i, j]) > threshold or abs(fixed[i, j]) > threshold:
                out.append((names[i], names[j], float(spearman[i, j]), float(fixed[i, j])))
    return sorted(out, key=lambda row: -abs(row[2]))
