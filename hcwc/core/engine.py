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
contact distribution — see ``docs/DHI_alignment.md``. Dropping them would make the two impossible to
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
    uniforms: np.ndarray          # (n, k) the copula draws, kept so the realised correlation
                                  # can be checked against the one that was asked for
    sampled_m: np.ndarray         # (n, k) column height each limit would impose, active or not
    active: np.ndarray            # (n, k) bool
    column_m: np.ndarray          # (n,) the shallowest active limit
    controller: np.ndarray        # (n,) index into limit_set.limits
    seed: int

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

        with ``P(G)`` the element product from tab ② (E-POS's geological POS). Reporting this term
        alone overstates the prospect by a factor of ``1 / P(G)``, which on Lars's defaults is
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
        h = np.atleast_1d(np.asarray(column_m, dtype=float))
        return (self.column_m[None, :] >= h[:, None]).mean(axis=1)

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
        """The rank correlation the run actually delivered.

        Worth checking rather than assuming: the Higham projection moves an inconsistent elicited
        matrix, and the assessor should be able to see how far.
        """
        return correlate.realised_spearman(self.uniforms)

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
        p = np.atleast_1d(np.asarray(exceedance_pct, dtype=float))
        contacts = self.contact_m[self.above_minimum]
        if contacts.size == 0:
            return np.full(p.shape, np.nan)
        return np.percentile(contacts, 100.0 - p)


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
                        active=active, column_m=column, controller=controller, seed=seed)


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
                               weights: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Which limit controls the contact, as a function of contact depth.

    Output 2 of the design, and the figure that answers *how does the controlling mechanism change
    as you step down structure* — the question a contact distribution alone cannot answer.

    Returns, per limit, the fraction of realisations in each depth bin that limit controlled.
    Columns sum to 1 in any bin that contains realisations.

    ``weights`` are per-realisation importance weights, so the same figure can be drawn on a DHI
    posterior. **That version is the more interesting one**: a fluid indicator does not re-attribute
    the geological risk, but it does change which mechanism is most likely to have stopped the
    column *at the depth the amplitude points to* — and until this took weights, the DHI tab could
    only say that in a table.
    """
    edges = np.asarray(edges, dtype=float)
    if edges.size < 2:
        raise ValueError("need at least two bin edges")
    w = np.ones(result.n) if weights is None else np.asarray(weights, dtype=float)
    which = np.digitize(result.contact_m, edges) - 1
    n_bins = edges.size - 1
    out = {name: np.zeros(n_bins) for name in result.limit_set.names}
    for b in range(n_bins):
        in_bin = which == b
        total = float(w[in_bin].sum())
        if total <= 0:
            continue
        summed = np.bincount(result.controller[in_bin], weights=w[in_bin],
                             minlength=len(result.limit_set))
        for i, name in enumerate(result.limit_set.names):
            out[name][b] = summed[i] / total
    return out
