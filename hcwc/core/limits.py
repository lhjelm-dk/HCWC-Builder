"""What a limit on the hydrocarbon column is, and the set of them a prospect carries.

A **limit** is one mechanism that could stop the column going deeper: the spill point, a fault
juxtaposition, the top seal's capillary capacity, the charge available, the reservoir pinching out.
Each has a probability of being present at all, and — given it is present — a distribution of the
depth below the apex at which it bites.

Two things are deliberate.

**Distributions are data, not code.** A :class:`DepthDistribution` is a name plus a dict of
parameters, so a limit set round-trips through JSON. That is what makes Hood's "standard background
column height distributions for *families* of related prospects" possible later without a rewrite,
and it costs nothing now.

**Sampling goes through the quantile function**, not through a direct draw. The engine hands each
limit a uniform and asks for a depth. Correlation then becomes a question of where the uniforms come
from — a Gaussian copula upstream — and no limit definition has to know anything about it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from hcwc.core import dists


class Group(str, Enum):
    """The risk element a limit belongs to.

    These are the E-POS pillar names. ``CLOSURE`` is what is elsewhere called "trap geometry":
    it is the element that *defines* the closure, and Lars's ruling (25 Aug 2026) is
    that fault geometry belongs here while fault *leakage* belongs to retention — they are
    different failure mechanisms even when they sit on the same fault.

    ``RESERVOIR`` is the reservoir base or pinchout only. Reservoir *effectiveness* with depth is a
    real effect but it does not move the contact, so it is not a limit; it enters the per-element
    decomposition as a separate multiplicative factor. Conflating the two would break the
    consistency identity the decomposition is checked against.
    """
    CHARGE = "Charge"
    CLOSURE = "Closure"
    RETENTION = "Retention"
    RESERVOIR = "Reservoir"


#: kind -> the quantile function and the parameter names it needs, in order.
_KINDS: dict[str, tuple[Any, tuple[str, ...]]] = {
    "normal_alt": (dists.normal_alt_ppf, ("p1", "x1", "p2", "x2")),
    "beta_subj": (dists.beta_subj_ppf, ("minimum", "mode", "mean", "maximum")),
    "beta_general": (dists.beta_general_ppf, ("alpha1", "alpha2", "minimum", "maximum")),
    "pert": (dists.pert_ppf, ("minimum", "mode", "maximum")),
    "uniform": (dists.uniform_ppf, ("minimum", "maximum")),
    "fixed": (None, ("value",)),
    # Not an elicited distribution: a quantile table, so a branch that computes its own column-height
    # distribution -- the charge branch -- can enter the engine as an ordinary limit. Parameters are
    # lists, and `cumulative` is ASCENDING cumulative probability, deliberately *not* the exceedance
    # convention the GeoX export uses. An inverse CDF wants ascending; getting the two mixed up is
    # the one mistake this would silently survive, so they are named differently.
    "empirical": (None, ("cumulative", "value")),
}


@dataclass(frozen=True)
class DepthDistribution:
    """A column height below the apex, as a named distribution plus its parameters."""
    kind: str
    params: dict[str, float]

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise ValueError(f"unknown distribution {self.kind!r}; choose from {sorted(_KINDS)}")
        _, needed = _KINDS[self.kind]
        missing = set(needed) - set(self.params)
        extra = set(self.params) - set(needed)
        if missing:
            raise ValueError(f"{self.kind} needs {sorted(missing)}")
        if extra:
            # Silently ignoring an unused parameter is how a typo becomes a wrong distribution
            # that still runs.
            raise ValueError(f"{self.kind} does not take {sorted(extra)}; expected {list(needed)}")

    def ppf(self, u: np.ndarray) -> np.ndarray:
        """Column height below the apex, for uniforms ``u`` in [0, 1)."""
        func, needed = _KINDS[self.kind]
        if self.kind == "fixed":
            return np.full(np.shape(u), float(self.params["value"]))
        if self.kind == "empirical":
            cumulative = np.asarray(self.params["cumulative"], dtype=float)
            value = np.asarray(self.params["value"], dtype=float)
            if cumulative.size != value.size:
                raise ValueError("cumulative and value must be the same length")
            if not np.all(np.diff(cumulative) > 0):
                raise ValueError("cumulative probabilities must strictly increase")
            return np.interp(np.asarray(u, dtype=float), cumulative, value)
        return func(u, *(self.params[k] for k in needed))

    @classmethod
    def from_samples(cls, samples: np.ndarray, n_points: int = 201) -> "DepthDistribution":
        """Summarise a computed column-height distribution into a quantile table.

        The charge branch does not have a closed-form distribution — it comes out of an area–depth
        integration against a sampled charge volume. Reducing it to quantiles lets it enter the
        engine as an ordinary limit, and loses nothing, because charge is not correlated with any
        other limit in this model.

        **201 points, half-percent resolution** (audit P2-5, closed 16 Sep 2026; 101 until then).
        The table's ends are the calculator's sampled minimum and maximum, so tails beyond the
        20 000 draws behind it are unreachable and the ends move slightly with the draw; the
        resolution between them is what this number sets. Every calculator-fed limit passes
        through here, so the engine's own percentiles of such a limit change in their last
        digit with this change and nowhere else.

        Non-finite samples are dropped: an infinite charge-limited contact means *charge is not a
        limit in that realisation*, which is a statement about the limit's probability of being
        active, not about its depth. It belongs in ``p_active``, not in the quantile table.
        """
        finite = np.asarray(samples, dtype=float)
        finite = finite[np.isfinite(finite)]
        if finite.size < 2:
            raise ValueError(
                "fewer than two finite samples; charge never limited the column, so it is not a "
                "limit here — remove the row rather than giving it a degenerate distribution"
            )
        cumulative = np.linspace(0.0, 1.0, n_points)
        return cls("empirical", {"cumulative": cumulative.tolist(),
                                 "value": np.percentile(finite, cumulative * 100.0).tolist()})

    def to_dict(self) -> dict:
        return {"kind": self.kind, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, d: dict) -> "DepthDistribution":
        return cls(kind=d["kind"], params=dict(d["params"]))


#: How a limit's distribution is stated. See :class:`Limit`.
COLUMN, DEPTH = "column", "depth"

#: The distributions an assessor can *choose*. Every key of :data:`_KINDS` except ``empirical``,
#: which is a computed quantile table rather than an elicited shape and is never offered as an
#: option. Public so that a reader validating a saved file can check a stored choice against the
#: same list the UI builds its menu from, without importing the UI.
ELICITED_KINDS: tuple[str, ...] = tuple(k for k in _KINDS if k != "empirical")

#: The name the apex answers to in a correlation pair. It is not a limit -- it is the datum every
#: limit is measured from -- but it *is* a sampled depth, and a depth-stated limit shares its
#: depth-conversion error with it. Reserved, so no limit may take the name.
APEX = "Apex"


def to_depth(column_m, apex_m):
    """Column height below the apex -> depth in m TVDSS."""
    return np.asarray(apex_m, dtype=float) + np.asarray(column_m, dtype=float)


def to_column(depth_m, apex_m):
    """Depth in m TVDSS -> column height below the apex."""
    return np.asarray(depth_m, dtype=float) - np.asarray(apex_m, dtype=float)


def convert(values, *, frm: str, to: str, apex_m):
    """Move ``values`` between the two spaces, or return them untouched if they already match.

    The two spaces are interchangeable **for display** and only there: the model always competes
    limits in column height, because that is the space in which the comparison is meaningful. This
    exists so a reader can look at a seal capacity in m TVDSS beside a spill point, or at a spill
    point as a height above the crest, without either being silently reinterpreted.

    ``apex_m`` is a scalar for a display conversion and an array when converting realisation by
    realisation. Both work; passing a scalar where the apex is genuinely uncertain is a
    simplification the caller is making, not one made here.
    """
    if frm not in (COLUMN, DEPTH) or to not in (COLUMN, DEPTH):
        raise ValueError(f"spaces must be {COLUMN!r} or {DEPTH!r}; got {frm!r} -> {to!r}")
    if frm == to:
        return np.asarray(values, dtype=float)
    return to_depth(values, apex_m) if to == DEPTH else to_column(values, apex_m)


@dataclass(frozen=True)
class Limit:
    """One mechanism that can stop the column, with its chance of being present.

    ``kind`` is what the numbers in ``distribution`` mean, and the two are not interchangeable:

    * ``COLUMN`` — **metres of column below the apex**. The natural form for a *capacity*: what a
      seal can hold, what a fault will leak past. It does not move when the apex pick moves.
    * ``DEPTH`` — **metres TVDSS**. The natural form for a *mapped surface*: the spill point, a
      fault's juxtaposition window, a wedge pinch-out. These are read off a depth-converted map and
      an assessor states them as depths.

    Forcing both into one convention is what made the old input awkward in both directions — it
    asked for a seal capacity in metres below sea level, or a spill point as a height above a crest
    the assessor had not fixed yet. The engine converts ``DEPTH`` limits to column heights using the
    apex drawn in the same realisation.

    **The conversion is where the paper's own bias enters the tool.** ``column = depth - apex``
    subtracts two picks off the same depth-converted surface, so an error in the apex propagates
    into every depth-stated limit with the opposite sign — exactly the errors-in-variables coupling
    that inflates the published column-height regression. A depth-stated limit that samples above
    the apex is therefore a real possibility, not a rounding artefact, and
    :func:`hcwc.core.engine.run` refuses rather than clipping: a clipped negative column would put a
    spike at the apex that reads as geology.
    """
    name: str
    group: Group
    p_active: float
    distribution: DepthDistribution
    note: str = ""
    kind: str = COLUMN

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a limit needs a name; it is what the diagnostic reports")
        if not 0.0 <= self.p_active <= 1.0:
            raise ValueError(f"{self.name}: p_active must be in [0, 1], got {self.p_active}")
        if self.kind not in (COLUMN, DEPTH):
            raise ValueError(
                f"{self.name}: kind must be {COLUMN!r} (metres of column below the apex) or "
                f"{DEPTH!r} (metres TVDSS), got {self.kind!r}"
            )

    @property
    def always_active(self) -> bool:
        return self.p_active >= 1.0

    @property
    def is_depth(self) -> bool:
        return self.kind == DEPTH

    @staticmethod
    def label_for(space: str) -> str:
        return "m TVDSS" if space == DEPTH else "m column below apex"

    @property
    def unit_label(self) -> str:
        """What to put on an axis, so a figure can never be ambiguous about which space it is in."""
        return "m TVDSS" if self.is_depth else "m column below apex"

    def to_dict(self) -> dict:
        return {"name": self.name, "group": self.group.value, "p_active": self.p_active,
                "distribution": self.distribution.to_dict(), "note": self.note,
                "kind": self.kind}

    @classmethod
    def from_dict(cls, d: dict) -> "Limit":
        # `kind` defaults to COLUMN so every limit set written before the depth option existed
        # still loads, and means what it meant when it was written.
        return cls(name=d["name"], group=Group(d["group"]), p_active=float(d["p_active"]),
                   distribution=DepthDistribution.from_dict(d["distribution"]),
                   note=d.get("note", ""), kind=d.get("kind", COLUMN))


@dataclass(frozen=True)
class LimitSet:
    """Every limit on one prospect, plus the apex it is all measured from."""
    apex: DepthDistribution
    limits: tuple[Limit, ...]
    name: str = "unnamed"
    min_column_m: float = 0.0
    correlations: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.limits:
            raise ValueError("a prospect with no limits has an unbounded column")
        names = [limit.name for limit in self.limits]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            # The controlling-limit diagnostic reports by name, so duplicates would merge two
            # mechanisms into one bar and nobody would notice.
            raise ValueError(f"limit names must be unique; repeated: {sorted(duplicates)}")
        if APEX in names:
            raise ValueError(
                f"{APEX!r} is reserved: it is the name the apex answers to in a correlation pair, "
                f"so a limit called {APEX!r} would make 'Apex|Closure / spill' ambiguous. Rename "
                f"the limit."
            )
        if not any(limit.always_active for limit in self.limits):
            raise ValueError(
                "at least one limit must have p_active = 1. Every prospect has a spill point, so "
                "there is always something bounding the column; without one, some realisations "
                "have no active limit and an undefined column height. Substituting a large finite "
                "depth for an inactive limit hides this and silently produces a 10 km column "
                "rather than an error."
            )
        if self.min_column_m < 0:
            raise ValueError("the assessment minimum is a column height and cannot be negative")

    def __len__(self) -> int:
        return len(self.limits)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(limit.name for limit in self.limits)

    @property
    def correlated_names(self) -> tuple[str, ...]:
        """Everything the copula spans: the apex first, then the limits in order.

        The apex leads because it is the datum. Its position is also load-bearing -- the engine
        reads column 0 of the uniforms as the apex draw -- so this is the single definition of that
        ordering rather than a convention repeated in two places.
        """
        return (APEX, *self.names)

    @property
    def groups(self) -> tuple[Group, ...]:
        return tuple(limit.group for limit in self.limits)

    def indices_in(self, group: Group) -> np.ndarray:
        return np.array([i for i, limit in enumerate(self.limits) if limit.group is group],
                        dtype=int)

    #: The quantile the declared support is read at. Bounded distributions (PERT, uniform,
    #: fixed, empirical) are unaffected by it; for a normal it is where the tail is cut, since a
    #: normal has no end.
    SUPPORT_TAIL = 0.001

    def contact_support_m(self, tail: float = SUPPORT_TAIL) -> tuple[float, float]:
        """The depth interval in which this model can place a contact, from its declared inputs.

        Shallow end: the apex, at its ``tail`` quantile. Deep end: the shallowest of the deep
        ends of the limits that are always active -- a contact cannot lie below a limit that is
        always there, so the tightest always-active limit bounds the support. A column-stated
        limit's deep end is the apex's deep quantile plus the limit's; a depth-stated limit's is
        its own.

        **Declared, not realised.** Until 14 Sep 2026 the spurious-event density in
        :mod:`hcwc.core.dhi` was ``1 / (max − min)`` of the *sampled* contacts, so the likelihood
        of a picked flat spot depended on the trial count, the seed and whichever extreme the
        sampler happened to draw. A likelihood is a statement about the model; it cannot be
        allowed to change because the Monte Carlo ran longer. This reads the same interval off
        the distributions themselves, and the same limit set returns the same interval whatever
        is done with it afterwards.
        """
        shallow = float(self.apex.ppf(np.array([tail]))[0])
        apex_deep = float(self.apex.ppf(np.array([1.0 - tail]))[0])
        deep_ends = []
        for limit in self.limits:
            if not limit.always_active:
                continue
            q = float(limit.distribution.ppf(np.array([1.0 - tail]))[0])
            deep_ends.append(q if limit.is_depth else apex_deep + q)
        deep = min(deep_ends) if deep_ends else apex_deep
        if not deep > shallow:
            raise ValueError(
                f"{self.name}: the always-active limits reach no deeper than the apex "
                f"({deep:,.0f} m against {shallow:,.0f} m), so the model has no depth interval "
                f"in which to place a contact"
            )
        return shallow, deep

    def to_dict(self) -> dict:
        return {"name": self.name, "apex": self.apex.to_dict(),
                "min_column_m": self.min_column_m,
                "limits": [limit.to_dict() for limit in self.limits],
                "correlations": dict(self.correlations)}

    @classmethod
    def from_dict(cls, d: dict) -> "LimitSet":
        return cls(apex=DepthDistribution.from_dict(d["apex"]),
                   limits=tuple(Limit.from_dict(x) for x in d["limits"]),
                   name=d.get("name", "unnamed"),
                   min_column_m=float(d.get("min_column_m", 0.0)),
                   correlations=dict(d.get("correlations", {})))

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "LimitSet":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def reference_prospect() -> LimitSet:
    """A complete worked prospect: a 350 m closure at about 2 050 m, seal-limited.

    The fixture the tests run against, and the case every default in the app is set from. Two
    conventions worth stating, because both are choices:

    * **A limit that cannot fire is not carried.** Mechanisms this closure does not have are
      omitted rather than included at ``p_active = 0`` with placeholder parameters, which would
      make the controlling-limit diagnostic longer without making it more informative.
    * **Charge and Closure are always active.** Every prospect has a spill point, and charge that
      delivers nothing is a charge *element* failure rather than a shallow contact — that belongs
      in the element chance on tab 2.0, not here.
    """
    return LimitSet(
        name="Reference prospect",
        apex=DepthDistribution("normal_alt", {"p1": 0.0001, "x1": 2049.0,
                                              "p2": 0.9999, "x2": 2051.0}),
        min_column_m=0.0,
        limits=(
            Limit("Charge", Group.CHARGE, 1.0,
                  DepthDistribution("pert", {"minimum": 150.0, "mode": 300.0, "maximum": 420.0}),
                  "A typed stand-in for the charge calculator, charge-limited near 304 m. Use "
                  "the *Computed* source on tab 3.0 to derive it from an area–depth integration."),
            Limit("Closure / spill", Group.CLOSURE, 1.0,
                  DepthDistribution("normal_alt", {"p1": 0.01, "x1": 340.0,
                                                   "p2": 0.99, "x2": 360.0}), ""),
            Limit("Fault 1 geometry", Group.CLOSURE, 0.5,
                  DepthDistribution("normal_alt", {"p1": 0.01, "x1": 130.0,
                                                   "p2": 0.99, "x2": 170.0}), ""),
            Limit("Fault leakage 2", Group.RETENTION, 0.6,
                  DepthDistribution("beta_subj", {"minimum": 200.0, "mode": 250.0,
                                                  "mean": 275.0, "maximum": 400.0}), ""),
            Limit("Top seal (capillary)", Group.RETENTION, 1.0,
                  DepthDistribution("beta_subj", {"minimum": 20.0, "mode": 200.0,
                                                  "mean": 250.0, "maximum": 618.0}), ""),
            Limit("Base seal (capillary)", Group.RETENTION, 1.0,
                  DepthDistribution("beta_subj", {"minimum": 70.0, "mode": 250.0,
                                                  "mean": 300.0, "maximum": 668.0}), ""),
            Limit("Top seal (continuity)", Group.RETENTION, 0.5,
                  DepthDistribution("beta_subj", {"minimum": 300.0, "mode": 350.0,
                                                  "mean": 600.0, "maximum": 1000.0}), ""),
            Limit("Base seal (continuity)", Group.RETENTION, 0.5,
                  DepthDistribution("beta_subj", {"minimum": 300.0, "mode": 350.0,
                                                  "mean": 600.0, "maximum": 1000.0}), ""),
            Limit("Preservation / tilt", Group.RETENTION, 0.2,
                  DepthDistribution("pert", {"minimum": 330.0, "mode": 350.0, "maximum": 370.0}),
                  "Independent of the seal limits — a post-accumulation mechanism, so the "
                  "seals can be perfect while the closure tilts. **PERT, not BetaSubj:** a symmetric "
                  "four-point elicitation — (330, 350, 350, 370), mode at the midpoint of the "
                  "support and equal to the mean — says 'symmetric' and nothing more, so no "
                  "BetaSubj is determined. PERT is defined for exactly that case and uses the "
                  "same min/mode/max."),
        ),
    )


def group_totals(limits: Iterable[Limit]) -> dict[Group, int]:
    """How many limits sit in each group. Used to warn about an unrepresented element."""
    out = {g: 0 for g in Group}
    for limit in limits:
        out[limit.group] += 1
    return out
