"""Per-element chance against depth — derived from the competing limits, not allocated across them.

This is the part of the tool with no published equivalent.

**Why it matters.** WellVolPOS computes one location factor, ``r = P(contact > z_entry | success)``,
and then spreads it across the risk elements by a weighting scheme. Its own docstring is candid
about the limit: *"Spreading a single number across four elements presents it differently; it does
not add information about charge or closure."*

The competing-limits model can do better, because it knows *which* element bound the column in each
realisation. Take the shallowest active limit **within each element** — its group minimum — and
each element gets its own genuine curve:

    P_e(z) = P(element e's shallowest active limit lies deeper than z)

That is a derivation. The allocation is a presentation.

**The consistency test.** Under independent limits, ``P(min > z) = prod_e P_e(z)``, so the product
of the element curves must reproduce the contact distribution. Where it does not, the elements are
not independent — and that gap is exactly the double-count the whole three-tool architecture is
arranged to avoid, so it is computed and shown rather than assumed away.

**One subtlety a tightly picked apex hides.** The elements share the apex: every
element's *contact* is ``apex + h_e``, so even with perfectly independent limits the depth-space
curves are dependent through the common apex, and their product is not the contact distribution.
The identity is exact only in **column-height space**. Both are computed here, and the difference
between the two residuals is the apex contribution — negligible when the apex spans two metres,
and not negligible for a prospect with real depth-conversion uncertainty.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hcwc.core.engine import EngineResult
from hcwc.core.limits import Group

#: The elements a contact-controlling limit can belong to, in E-POS's canonical order.
ELEMENTS: tuple[Group, ...] = (Group.CHARGE, Group.CLOSURE, Group.RESERVOIR, Group.RETENTION)


@dataclass(frozen=True)
class ReservoirEffectiveness:
    """Reservoir quality against depth — the *other* reservoir effect, which is not a limit.

    Two things are called "reservoir vs depth" and only one of them moves the contact:

    * **R2, the base or pinchout** — the reservoir ends, so the column cannot continue. That is a
      geometric limit exactly like spill, and it belongs in the engine's ``MIN``.
    * **R1, effectiveness** — diagenesis, cementation, a net-to-gross trend. Below some depth the
      rock is not a reservoir. This does **not** move the contact; it changes the chance of success
      *at* a depth.

    Conflating them breaks the consistency identity, because R1 multiplies into the element product
    without appearing in the contact distribution. So it is carried here, separately, and the
    identity is checked over the three contact-controlling elements only.

    ``full_to_m`` is the depth to which the reservoir is fully effective; ``none_below_m`` the depth
    below which it is not a reservoir at all. Linear in between — deliberately crude, because
    nothing constrains the shape and pretending otherwise would be invention.
    """
    full_to_m: float = np.inf
    none_below_m: float = np.inf

    def __post_init__(self) -> None:
        if self.none_below_m < self.full_to_m:
            raise ValueError(
                f"the reservoir cannot stop being effective ({self.none_below_m} m) above the "
                f"depth to which it is fully effective ({self.full_to_m} m)"
            )

    @property
    def active(self) -> bool:
        return np.isfinite(self.full_to_m) or np.isfinite(self.none_below_m)

    def at(self, depth_m: np.ndarray) -> np.ndarray:
        z = np.asarray(depth_m, dtype=float)
        if not self.active:
            return np.ones_like(z)
        if not np.isfinite(self.none_below_m):
            return np.where(z <= self.full_to_m, 1.0, 1.0)
        if self.none_below_m == self.full_to_m:
            return np.where(z <= self.full_to_m, 1.0, 0.0)
        ramp = (self.none_below_m - z) / (self.none_below_m - self.full_to_m)
        return np.clip(ramp, 0.0, 1.0)


@dataclass(frozen=True)
class Decomposition:
    """Per-element chance curves, in both depth and column-height space, with the identity check."""
    depths_m: np.ndarray
    columns_m: np.ndarray
    by_element_depth: dict[Group, np.ndarray]
    by_element_column: dict[Group, np.ndarray]
    product_depth: np.ndarray
    product_column: np.ndarray
    direct_depth: np.ndarray
    direct_column: np.ndarray
    reservoir_effectiveness: np.ndarray

    @property
    def residual_depth(self) -> np.ndarray:
        """``prod_e P_e(z) - P(contact > z)``. Non-zero means the elements are not independent."""
        return self.product_depth - self.direct_depth

    @property
    def residual_column(self) -> np.ndarray:
        """The same in column space, where the identity is exact under independent limits."""
        return self.product_column - self.direct_column

    @property
    def max_abs_residual_column(self) -> float:
        return float(np.max(np.abs(self.residual_column)))

    @property
    def max_abs_residual_depth(self) -> float:
        return float(np.max(np.abs(self.residual_depth)))

    @property
    def apex_contribution(self) -> float:
        """How much of the depth-space gap is the shared apex rather than limit dependence.

        The elements share one apex draw, so their *contact* curves are dependent even when their
        *column* curves are not. This is the difference between the two residuals, and it is the
        number that says whether the depth-space test can be read at face value.
        """
        return self.max_abs_residual_depth - self.max_abs_residual_column

    def element_pos_at_depth(self, element_pos: dict[Group, float]) -> dict[Group, np.ndarray]:
        """``POS_e x P_e(z)`` — the prospect's element chance, taken down structure.

        ``element_pos`` are the four numbers E-POS produces: play times conditional, per element.
        This is what WellVolPOS should consume in place of allocating one location factor.
        """
        out = {}
        for element in ELEMENTS:
            curve = self.by_element_depth.get(element)
            if curve is None:
                continue
            out[element] = float(element_pos.get(element, 1.0)) * curve
        if Group.RESERVOIR in out:
            out[Group.RESERVOIR] = out[Group.RESERVOIR] * self.reservoir_effectiveness
        return out

    def factorised_pos(self, element_pos: dict[Group, float]) -> np.ndarray:
        """``Q(z)`` — the product of the element curves."""
        curves = self.element_pos_at_depth(element_pos)
        out = np.ones_like(self.depths_m)
        for curve in curves.values():
            out = out * curve
        return out

    def direct_pos(self, element_pos: dict[Group, float]) -> np.ndarray:
        """``R(z) = POS_total x P(contact > z)`` — the same quantity, read directly.

        Compare against :meth:`factorised_pos`. They agree exactly when the elements are
        independent and reservoir effectiveness is flat; the gap between them is the same
        information as :attr:`residual_depth`, scaled — and it is the number a downstream tool would
        be double-counting if it applied a depth penalty of its own on top.
        """
        total = 1.0
        for element in ELEMENTS:
            total *= float(element_pos.get(element, 1.0))
        return total * self.direct_depth * self.reservoir_effectiveness


def limit_curves_at_depth(result: EngineResult, depths_m: np.ndarray,
                          weights: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Each individual limit's exceedance curve: ``P(active AND deeper than z)``.

    One level below :meth:`Decomposition.element_pos_at_depth`, which aggregates to the four risk
    elements. This is the sub-element breakdown: which *mechanism* within Retention is doing the
    work at 2 200 m, not merely that Retention is.

    **Not conditional on being active**, which is the decision that makes the curve readable. A
    limit with ``p_active = 0.5`` flattens at 50 %, and reading that number straight off the curve
    is the point -- it says *this mechanism only ever bites in half the realisations*. The
    conditional form throws that away and makes a rare severe limit look identical to a common
    mild one.
    """
    out: dict[str, np.ndarray] = {}
    for j, name in enumerate(result.limit_set.names):
        effective = np.where(result.active[:, j], result.sampled_m[:, j], np.inf)
        contact_j = result.apex_m + effective
        out[name] = _share(contact_j[None, :] > depths_m[:, None], weights)
    return out


def _share(indicator: np.ndarray, weights: np.ndarray | None) -> np.ndarray:
    """The share of realisations satisfying ``indicator``, weighted or not.

    One line, but it is the whole of the DHI-against-depth feature: every curve in this module is a
    mean over realisations, so giving that mean a weight vector turns the entire decomposition into
    its posterior twin.
    """
    if weights is None:
        return indicator.mean(axis=1)
    total = float(np.sum(weights))
    if total <= 0 or not np.isfinite(total):
        return indicator.mean(axis=1)
    return (indicator * weights[None, :]).sum(axis=1) / total


def decompose(result: EngineResult, *, n_points: int = 200,
              reservoir: ReservoirEffectiveness | None = None,
              weights: np.ndarray | None = None) -> Decomposition:
    """Build the per-element curves from a completed engine run.

    ``weights`` are per-realisation importance weights — :attr:`hcwc.core.dhi.DhiPosterior.weights`
    — and turn every curve here into its **given the DHI** counterpart.

    **Why this is allowed, since it looks like it should not be.** E-POS's resolution ceiling says a
    fluid indicator cannot tell you *which* element failed, and that stands: the element **chances**
    are inputs from tab 2.0 and this function never touches them. What reweights is where each
    element's limits *bite*, which is a geometric statement about the success cases — and the
    contact depth is **observed**, so it is ordinary inference on a latent variable.

    The two questions, kept apart:

    * *Given the prospect failed, which element failed?* — the DHI cannot say. Multipliers fixed.
    * *Given it worked and the contact is here, which mechanism stopped it there?* — the DHI can
      say, and this is how.

    The grid stays on the **prior's** contact range on purpose, so a geological and a posterior
    decomposition are drawn on identical depths and can be overlaid without interpolation.
    """
    reservoir = reservoir or ReservoirEffectiveness()
    contact = result.contact_m
    depths = np.linspace(float(contact.min()), float(contact.max()), n_points)
    columns = depths - float(np.median(result.apex_m))

    by_depth: dict[Group, np.ndarray] = {}
    by_column: dict[Group, np.ndarray] = {}
    for element in ELEMENTS:
        idx = result.limit_set.indices_in(element)
        if idx.size == 0:
            continue
        h_e = result.group_minimum(element)          # inf where the element never binds
        contact_e = result.apex_m + h_e              # inf stays inf
        by_depth[element] = _share(contact_e[None, :] > depths[:, None], weights)
        by_column[element] = _share(h_e[None, :] > columns[:, None], weights)

    product_depth = np.ones_like(depths)
    product_column = np.ones_like(columns)
    for element, curve in by_depth.items():
        product_depth = product_depth * curve
    for element, curve in by_column.items():
        product_column = product_column * curve

    direct_depth = _share(contact[None, :] > depths[:, None], weights)
    direct_column = _share(result.column_m[None, :] > columns[:, None], weights)

    return Decomposition(
        depths_m=depths, columns_m=columns,
        by_element_depth=by_depth, by_element_column=by_column,
        product_depth=product_depth, product_column=product_column,
        direct_depth=direct_depth, direct_column=direct_column,
        reservoir_effectiveness=reservoir.at(depths),
    )


def allocation_comparison(decomposition: Decomposition, element_pos: dict[Group, float],
                          z_entry_m: float) -> dict[str, float]:
    """This tool's derived element chances at a well depth, beside WellVolPOS's allocations.

    The three allocation schemes WellVolPOS ships all reproduce the *same* ``P_well`` and differ
    only in how they present it. The derived curves are a different kind of object: they can
    disagree with every scheme, because they carry information about which element actually binds
    at that depth rather than a rule for dividing one number.
    """
    i = int(np.argmin(np.abs(decomposition.depths_m - z_entry_m)))
    derived = {e: float(c[i]) for e, c in decomposition.element_pos_at_depth(element_pos).items()}
    p_well_derived = float(np.prod(list(derived.values()))) if derived else float("nan")

    pos_total = 1.0
    for element in ELEMENTS:
        pos_total *= float(element_pos.get(element, 1.0))
    r = float(decomposition.direct_depth[i])

    out = {f"derived::{e.value}": v for e, v in derived.items()}
    out["derived::P_well"] = p_well_derived
    out["allocated::P_well"] = pos_total * r
    out["r_location"] = r
    # Equal cube-root, WellVolPOS's `equal_cube_root`: r^(1/3) on charge, closure and retention.
    for element in (Group.CHARGE, Group.CLOSURE, Group.RETENTION):
        out[f"allocated::{element.value}"] = float(element_pos.get(element, 1.0)) * r ** (1 / 3)
    out[f"allocated::{Group.RESERVOIR.value}"] = float(element_pos.get(Group.RESERVOIR, 1.0))
    return out
