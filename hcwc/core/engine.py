"""The competing-limits engine: sample every limit, take the shallowest, record which one won.

    for each realisation:
        apex        ~ D_apex
        for each limit L:  active_L ~ Bernoulli(p_L);  h_L ~ D_L
        h           = min(h_L over active L)
        controller  = argmin                     <- the diagnostic
        HCWC        = apex + h

Nothing is blended. This is Hood's (2019, 2024) construction, and the reason for it is that merging
a leak into the background column-height distribution suppresses realisations *above* the leak,
which is not geology — it can even make apparent prospect volume increase when a leak is added.

The ``argmin`` bookkeeping costs one array and is the whole point: it turns a distribution into an
answer about *mechanism*, which is what the per-element depth decomposition is built from.

**The assessment minimum is applied as a flag, not a filter.** Realisations below it stay in the
array marked as failures, because `POS = P(column >= h_min)` is a reading of the same object as the
contact distribution — see ``archive/development_notes/DHI_alignment.md``. Dropping them would make the two impossible to
reconcile, which is the confusion that note exists to resolve.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import numpy as np

from hcwc.core import correlate
from hcwc.core.limits import Group, LimitSet

#: Sentinel for "this limit is not active in this realisation". Chosen as +inf rather than a large
#: finite depth such as 10 000 m: infinity cannot win a `min`, cannot be mistaken for a depth, and
#: cannot silently become a 10 km column if every limit happens to be switched off.
INACTIVE = np.inf


@dataclass(frozen=True)
class EngineResult:
    """One Monte Carlo run, with everything the diagnostics need kept rather than summarised."""
    limit_set: LimitSet
    apex_m: np.ndarray            # (n,)
    uniforms: np.ndarray          # (n, k) the copula draws for the limits, kept so the realised
                                  # correlation can be checked against the one that was asked for
    sampled_m: np.ndarray         # (n, k) column height each limit would impose, active or not
    active: np.ndarray            # (n, k) bool
    column_m: np.ndarray          # (n,) the shallowest active limit
    controller: np.ndarray        # (n,) index into limit_set.limits
    seed: int
    #: (n,) the apex's own copula draw. Kept separately so `uniforms` keeps its (n, k) shape for
    #: the sensitivity slices, while :meth:`realised_correlation` can cover the whole correlated
    #: set. Until 15 Sep 2026 the apex draw was discarded, so a declared Apex|spill pair -- the
    #: one the tab recommends -- could be requested and sampled but never reported as realised.
    apex_uniform: np.ndarray | None = None

    @property
    def n(self) -> int:
        return int(self.apex_m.size)

    @property
    def contact_m(self) -> np.ndarray:
        """Hydrocarbon–water contact depth, m TVDSS."""
        return self.apex_m + self.column_m

    @cached_property
    def above_minimum(self) -> np.ndarray:
        """Realisations meeting the assessment minimum — the success cases."""
        return self.column_m >= self.limit_set.min_column_m

    @property
    def pos(self) -> float:
        """``P(column >= h_min | G)`` — the **conditional** column-height term.

        **This is not the prospect chance of success and must never be labelled one.** The engine
        knows about competing limits and nothing else, so every probability it returns is
        conditional on the four elements having worked: a reservoir that is not there has no
        contact to distribute. The reportable number is

            ``Prospect POS = P(G) x P(column >= h_min | G)``

        with ``P(G)`` the element product from tab 2.0 (E-POS's geological POS). Reporting this term
        alone overstates the prospect by a factor of ``1 / P(G)``, which on the shipped defaults is
        2.5 — 79.8 % where the answer is 32.6 %. The one-page report did exactly that until he
        caught it on 27 Aug 2026, which is why the warning is here at the source rather than in
        the caller that got it wrong.

        Not a standalone number in the other sense either: it is :meth:`exceedance` read at the
        assessment minimum, and the app is required to display it with the threshold attached.
        """
        return float(self.above_minimum.mean())

    def exceedance(self, column_m: np.ndarray | float) -> np.ndarray:
        """``F(h) = P(column >= h)``. The primary risk output.

        Every "POS" in the workflow is this function evaluated somewhere — at the assessment
        minimum, at the well's reservoir entry depth, at a DHI-indicated contact.
        """
        return exceedance(self.column_m, column_m)

    def group_minimum(self, group: Group) -> np.ndarray:
        """Shallowest active limit within one group, per realisation; ``inf`` if none active.

        One per risk element — charge, closure, retention. These are what the per-element
        chance-versus-depth curves are derived from, the part of this tool with no published
        equivalent.
        """
        idx = self.limit_set.indices_in(group)
        if idx.size == 0:
            return np.full(self.n, INACTIVE)
        return np.where(self.active[:, idx], self.sampled_m[:, idx], INACTIVE).min(axis=1)

    def realised_correlation(self) -> np.ndarray:
        """The rank correlation the run actually delivered, over :attr:`LimitSet.correlated_names`.

        The apex is row and column 0 when its draw was kept, matching the order the copula
        sampled in, so every pair that can be declared can be read back. Worth checking rather
        than assuming: the Higham projection moves an inconsistent elicited matrix, and the
        assessor should be able to see how far.
        """
        if self.apex_uniform is None:
            return correlate.realised_spearman(self.uniforms)
        return correlate.realised_spearman(
            np.column_stack([self.apex_uniform, self.uniforms]))

    def realised_pairs(self) -> dict[str, float]:
        """Every declared pair with the rank correlation the run delivered, keyed as declared."""
        names = self.limit_set.correlated_names
        index = {name: i for i, name in enumerate(names)}
        matrix = self.realised_correlation()
        if self.apex_uniform is None:
            # No apex draw kept: the matrix is over the limits alone and apex pairs cannot be
            # read. Reported as nan rather than skipped, so the caller can say so.
            index = {name: i for i, name in enumerate(self.limit_set.names)}
        out = {}
        for key in self.limit_set.correlations:
            a, b = key.split("|")
            if a in index and b in index:
                out[key] = float(matrix[index[a], index[b]])
            else:
                out[key] = float("nan")
        return out

    def controlling_shares(self, *, successes_only: bool = False,
                           weights: np.ndarray | None = None) -> dict[str, float]:
        """Share of realisations each limit controlled the contact in.

        ``successes_only`` restricts to realisations above the assessment minimum, and **the two
        answer different questions**. Unrestricted: *what controls this closure?* Restricted:
        *what controls it, given it is worth drilling?*

        Both are wanted, and reporting only the restricted one would repeat, one level up, exactly
        the selection error this tool criticises in the published column-height statistics: a limit
        that usually kills the prospect outright is under-represented among the survivors
        **because** it is the most severe.

        ``weights`` are per-realisation importance weights — a DHI posterior. Counting becomes
        summing, and the result is *which mechanism controls the contact given the seismic*, which
        is a different answer from the geological one and worth seeing beside it.
        """
        mask = self.above_minimum if successes_only else np.ones(self.n, dtype=bool)
        w = np.ones(self.n) if weights is None else np.asarray(weights, dtype=float)
        total = float(w[mask].sum())
        if total <= 0:
            return {name: 0.0 for name in self.limit_set.names}
        summed = np.bincount(self.controller[mask], weights=w[mask],
                             minlength=len(self.limit_set))
        return {name: float(summed[i] / total)
                for i, name in enumerate(self.limit_set.names)}

    def percentiles(self, exceedance_pct: np.ndarray | float) -> np.ndarray:
        """Contact depth at given **exceedance** percentiles, success cases only.

        P100 is the shallowest contact, P0 the deepest — the industry convention, and the one the
        GeoX importer expects.
        """
        return weighted_percentiles(self.contact_m[self.above_minimum], None, exceedance_pct)


def weighted_percentiles(samples: np.ndarray, weights: np.ndarray | None,
                         exceedance_pct: np.ndarray | float) -> np.ndarray:
    """Values at **exceedance** percentiles of a weighted sample: P100 smallest, P0 largest.

    One estimator for the engine and the DHI posterior. Until 15 Sep 2026 (audit P3-4) the
    engine used ``np.percentile``'s linear order statistics and the posterior a
    midpoint-weighted cumulative, so tabs 4 and 5 could print a prior P50 differing in the
    second decimal. The midpoint form is the one that takes weights, so it is the one kept:
    each sorted sample sits at the middle of its own weight, and the value at a probability is
    interpolated between neighbours. At unit weights it is Hazen's plotting position.
    """
    p = np.atleast_1d(np.asarray(exceedance_pct, dtype=float))
    x = np.asarray(samples, dtype=float)
    if x.size == 0:
        return np.full(p.shape, np.nan)
    w = np.ones(x.size) if weights is None else np.asarray(weights, dtype=float)
    if w.sum() <= 0:
        return np.full(p.shape, np.nan)
    order = np.argsort(x)
    x, w = x[order], w[order]
    cumulative = (np.cumsum(w) - 0.5 * w) / w.sum()
    return np.interp((100.0 - p) / 100.0, cumulative, x)


def run(limit_set: LimitSet, n: int = 10_000, seed: int = 20260825) -> EngineResult:
    """Run the competing-limits Monte Carlo.

    ``seed`` is fixed by default, and exposed rather than buried. An unfixed seed means every
    number on every tab moves between runs and no figure can be regenerated, which is indefensible
    in a document someone will quote from.
    """
    if n < 1:
        raise ValueError("need at least one realisation")
    rng = np.random.default_rng(seed)
    k = len(limit_set)

    # One uniform per **correlated variable** per realisation: the apex first, then each limit.
    # Correlation is entirely a question of where the uniforms come from, and no limit definition
    # knows anything about it. With nothing declared the copula is the identity, which is
    # `rng.random` in distribution -- so the branch is for speed and reproducibility, not
    # correctness.
    #
    # **The apex is column 0 and that is the point.** A depth-stated limit and the apex are picked
    # off the same depth-converted surface, so their errors are shared; leaving the apex outside
    # the copula forced them independent and made `Apex|Spill` inexpressible, while the engine's
    # own refusal message advised exactly that pairing. `LimitSet.correlated_names` owns the
    # ordering.
    names = limit_set.correlated_names
    if limit_set.correlations:
        spearman = correlate.build_matrix(names, limit_set.correlations)
        draws = correlate.correlated_uniforms(rng, spearman, n)
    else:
        draws = rng.random((n, k + 1))
    apex = limit_set.apex.ppf(draws[:, 0])
    uniforms = draws[:, 1:]
    sampled = np.empty((n, k), dtype=float)
    for j, limit in enumerate(limit_set.limits):
        drawn = limit.distribution.ppf(uniforms[:, j])
        if limit.is_depth:
            # Stated in m TVDSS -- a mapped surface. Convert to column height against the apex
            # drawn in the *same* realisation, so the pair stays consistent trial by trial.
            drawn = drawn - apex
            if (drawn < 0).any():
                share = float((drawn < 0).mean())
                raise ValueError(
                    f"{limit.name!r} is stated as a depth (m TVDSS) and lands **above the apex** in "
                    f"{share:.1%} of realisations, which would be a negative column.\n\n"
                    f"Its P1 is {float(limit.distribution.ppf(np.array([0.01]))[0]):,.0f} m and the "
                    f"apex reaches {float(np.max(apex)):,.0f} m. Either the two distributions "
                    f"overlap, or the limit is not really a depth.\n\n"
                    f"This is not clipped to zero on purpose: a clipped negative column would put a "
                    f"spike of realisations exactly at the apex, which reads as a geological result "
                    f"and is not one. Widen the gap, or correlate the apex with this limit -- they "
                    f"are picked off the same depth-converted surface, so a positive correlation "
                    f"is the honest default rather than zero."
                )
        sampled[:, j] = drawn

    active = np.empty((n, k), dtype=bool)
    for j, limit in enumerate(limit_set.limits):
        active[:, j] = True if limit.always_active else rng.random(n) < limit.p_active

    effective = np.where(active, sampled, INACTIVE)
    controller = np.argmin(effective, axis=1)
    column = effective[np.arange(n), controller]

    if not np.isfinite(column).all():
        # LimitSet.__post_init__ requires an always-active limit, so this is unreachable unless
        # that invariant is broken. Better a loud failure than an infinite contact depth.
        raise RuntimeError(
            "some realisations had no active limit, so the column height is unbounded; "
            "this should have been prevented by the always-active check on the limit set"
        )

    return EngineResult(limit_set=limit_set, apex_m=apex, uniforms=uniforms, sampled_m=sampled,
                        active=active, column_m=column, controller=controller, seed=seed,
                        apex_uniform=draws[:, 0])


def limit_ranking(result: EngineResult, *, successes_only: bool = False,
                  weights: np.ndarray | None = None) -> list[tuple[str, float]]:
    """Limits ordered by how often they controlled the contact, most first.

    This is the answer to *which of the numbers I elicited actually mattered*. A limit near zero
    can be left rough; the top two or three are where elicitation effort belongs. It is meant to be
    used as a workflow step, not read once at the end.
    """
    shares = result.controlling_shares(successes_only=successes_only, weights=weights)
    return sorted(shares.items(), key=lambda kv: kv[1], reverse=True)


def controlling_share_by_depth(result: EngineResult, edges: np.ndarray,
                               weights: np.ndarray | None = None, *,
                               within_bin: bool = True) -> dict[str, np.ndarray]:
    """Which limit controls the contact, as a function of contact depth.

    Output 2 of the design, and the figure that answers *how does the controlling mechanism change
    as you step down structure* — the question a contact distribution alone cannot answer.

    ``weights`` are per-realisation importance weights, so the same figure can be drawn on a DHI
    posterior.

    ``within_bin`` decides what the numbers are shares *of*, and the two answer different questions:

    * ``True`` (default) — the fraction **of the realisations in that bin**. Columns sum to 1 in any
      occupied bin, which is what makes the stacked figure readable.
    * ``False`` — the fraction **of all realisations**, so each limit's values sum across bins to
      its overall controlling share.

    The distinction matters more than it looks, and only became visible when the DHI-weighted
    version was drawn beside the geological one: **they were nearly identical.** Normalising within
    a bin conditions on contact depth, and a DHI's evidence is almost entirely *about* contact
    depth, so conditioning throws it away — on the worked prospect the within-bin shares move by at
    most 0.95 points while the overall shares move by 3.9 and the bin occupancies by 9.6. Anything
    trying to show what a DHI did to the controlling mechanism has to use ``within_bin=False``, or
    it will faithfully draw the one view of this diagnostic that a DHI cannot move.
    """
    edges = np.asarray(edges, dtype=float)
    if edges.size < 2:
        raise ValueError("need at least two bin edges")
    w = np.ones(result.n) if weights is None else np.asarray(weights, dtype=float)
    which = np.digitize(result.contact_m, edges) - 1
    n_bins = edges.size - 1
    # `digitize` puts a value equal to the last edge one bin past the end, so a realisation
    # whose contact is exactly the deepest edge fell out of every figure (audit P3-3, 15 Sep
    # 2026). The last bin is right-inclusive; the shares then sum to one over the edges' span.
    which[result.contact_m == edges[-1]] = n_bins - 1
    out = {name: np.zeros(n_bins) for name in result.limit_set.names}
    grand = float(w.sum())
    for b in range(n_bins):
        in_bin = which == b
        total = float(w[in_bin].sum()) if within_bin else grand
        if total <= 0:
            continue
        summed = np.bincount(result.controller[in_bin], weights=w[in_bin],
                             minlength=len(result.limit_set))
        for i, name in enumerate(result.limit_set.names):
            out[name][b] = summed[i] / total
    return out


def exceedance(samples: np.ndarray, at: np.ndarray | float,
               weights: np.ndarray | None = None) -> np.ndarray:
    """``P(sample >= at)``, for one grid of thresholds.

    **One function, because there were six.** The same broadcast --
    ``(samples[None, :] >= grid[:, None]).mean(axis=1)`` -- was written out in `engine`, twice in
    `dhi`, twice in `empirical` and once in `limit_block`. Identical every time, and it is the
    app's single largest allocation, so a fix had to be applied in six places and would have been
    applied in four.

    **And it no longer builds the matrix.** That broadcast materialises a ``len(at) x len(samples)``
    boolean array: 4 MB at the 400-point grids in use against 10 000 realisations, and 400 MB at
    100 000 -- one temporary, inside one expression, with nothing in the UI to suggest why the tab
    had died. Sorting once and using ``searchsorted`` gives the identical answer in O(n log n) with
    no temporary at all.

    ``weights`` carries the DHI posterior, where the sample is the prior's realisations and the
    evidence lives in how much each one counts.
    """
    grid = np.atleast_1d(np.asarray(at, dtype=float))
    values = np.asarray(samples, dtype=float)
    if values.size == 0:
        return np.full(grid.shape, np.nan)

    order = np.argsort(values)
    ordered = values[order]
    if weights is None:
        # Count strictly below each threshold; everything else is at or above it.
        below = np.searchsorted(ordered, grid, side="left")
        return 1.0 - below / values.size

    w = np.asarray(weights, dtype=float)[order]
    total = float(w.sum())
    if not np.isfinite(total) or total <= 0:
        return np.full(grid.shape, np.nan)
    cumulative = np.concatenate(([0.0], np.cumsum(w)))
    return 1.0 - cumulative[np.searchsorted(ordered, grid, side="left")] / total
