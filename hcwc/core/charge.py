"""Charge-limited contact: how deep the available hydrocarbon can fill the structure.

Integrate the area–depth table to a gross rock volume, convert to hydrocarbon pore volume, and
find the depth at which the accumulated pore volume equals the charge the basin model delivered.

**One simplification worth knowing about.** Net-to-gross, porosity and saturation are constant with
depth within a realisation, so hydrocarbon pore volume is just ``HCPV(z) = GRV(z) x k`` with
``k = NTG x phi x Sh``. Finding where ``HCPV(z) = V`` is therefore finding where
``GRV(z) = V / k`` — one interpolation on a fixed curve per realisation, rather than rebuilding an
HCPV curve for each.

**The trap to avoid: interpolating past the end of the table.** An area–depth table stops at the
deepest mapped point. When the charge exceeds what the structure can hold, a lookup that runs off
the end of the table does not fail — it extrapolates, and returns a contact hundreds of metres
below anything that was ever mapped. Those numbers look like contacts and are not.

Here, charge that exceeds the structure's capacity returns **infinity**, not the base of the
table.
That is the difference between "charge fills past the deepest thing we mapped" and "charge sets the
contact at the base" — the first is charge *not being* a limit, and in a competing-limits model a
limit that does not bind must not be able to win the minimum.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

REFERENCE = Path(__file__).resolve().parents[2] / "reference"

#: Column spellings accepted in an uploaded area–depth table, canonical name first.
AREA_DEPTH_ALIASES: dict[str, tuple[str, ...]] = {
    "depth_m": ("depth", "depthm", "depthmtvdss", "tvdss", "tvd", "z", "mtvdss"),
    "top_area_km2": ("toparea", "toparea km2", "areatop", "top", "area", "areakm2",
                     "topareakm2", "toparealkm2"),
    "base_area_km2": ("basearea", "areabase", "base", "baseareakm2"),
}


def _canonical(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _match_columns(columns) -> dict[str, str]:
    """Map canonical field names onto whatever this file happens to call them."""
    seen = {_canonical(c): c for c in columns}
    out: dict[str, str] = {}
    for target, spellings in AREA_DEPTH_ALIASES.items():
        for spelling in (_canonical(target), *(_canonical(s) for s in spellings)):
            if spelling in seen:
                out[target] = seen[spelling]
                break
    return out


@dataclass(frozen=True)
class AreaDepthTable:
    """Top and base reservoir area against depth, and the rock volume between them."""
    depths_m: np.ndarray
    top_area_km2: np.ndarray
    base_area_km2: np.ndarray

    def __post_init__(self) -> None:
        n = self.depths_m.size
        if n < 2:
            raise ValueError("an area-depth table needs at least two depths")
        if not (self.top_area_km2.size == n and self.base_area_km2.size == n):
            raise ValueError("depths, top area and base area must be the same length")
        if not np.all(np.diff(self.depths_m) > 0):
            raise ValueError("depths must increase; the table runs from the apex downwards")
        if np.any(self.base_area_km2 > self.top_area_km2 + 1e-9):
            raise ValueError(
                "base area exceeds top area somewhere, which would make the rock volume negative; "
                "check the two columns have not been swapped"
            )

    @property
    def apex_m(self) -> float:
        return float(self.depths_m[0])

    @property
    def deepest_m(self) -> float:
        return float(self.depths_m[-1])

    @property
    def grv_1e6m3(self) -> np.ndarray:
        """Cumulative gross rock volume from the apex, 1e6 m³.

        Trapezoidal integration of ``top area − base area``. km² × m is 1e6 m³, so the units come
        out without a conversion factor.
        """
        net = self.top_area_km2 - self.base_area_km2
        steps = np.diff(self.depths_m) * 0.5 * (net[:-1] + net[1:])
        return np.concatenate([[0.0], np.cumsum(steps)])

    @property
    def capacity_1e6m3(self) -> float:
        """Gross rock volume down to the deepest mapped depth."""
        return float(self.grv_1e6m3[-1])

    def depth_at_grv(self, target_1e6m3: np.ndarray) -> np.ndarray:
        """Depth at which the cumulative GRV reaches ``target``; ``inf`` beyond the table.

        Infinity rather than the deepest depth is the whole correction to B-4. A charge that fills
        past everything we mapped is charge *failing to be a limit*, and in a competing-limits model
        that must lose the minimum rather than win it at the base of the table.
        """
        target = np.atleast_1d(np.asarray(target_1e6m3, dtype=float))
        grv = self.grv_1e6m3
        out = np.interp(target, grv, self.depths_m, left=self.apex_m, right=np.inf)
        return np.where(target > grv[-1], np.inf, out)

    @classmethod
    def from_csv(cls, path_or_text) -> "AreaDepthTable":
        """Read a table from a path or from CSV text.

        Column spellings are matched loosely, the way the benchmark importer does it, because an
        area–depth table is usually exported from mapping software and nobody renames the columns
        by hand. **Base area is optional**: without it the table is top-area-only, and the caller is
        expected to supply a thickness through :meth:`from_top_and_thickness` rather than have a
        zero base silently assert an infinitely thick reservoir.
        """
        import io as _io

        import pandas as pd

        source = path_or_text
        if isinstance(path_or_text, (str, bytes)) and not isinstance(path_or_text, Path):
            text = (path_or_text.decode("utf-8-sig", errors="replace")
                    if isinstance(path_or_text, bytes) else path_or_text)
            if "\n" in text or "," in text:
                source = _io.StringIO(text)
        frame = pd.read_csv(source, comment="#")
        found = _match_columns(frame.columns)
        missing = [want for want in ("depth_m", "top_area_km2") if want not in found]
        if missing:
            raise ValueError(
                f"an area–depth table needs a depth and a top area, one row per mapped depth. "
                f"Missing: {', '.join(missing)}. The columns in this file are "
                f"{', '.join(map(str, frame.columns))}."
            )
        depths = pd.to_numeric(frame[found["depth_m"]], errors="coerce").to_numpy(float)
        top = pd.to_numeric(frame[found["top_area_km2"]], errors="coerce").to_numpy(float)
        base = (pd.to_numeric(frame[found["base_area_km2"]], errors="coerce").to_numpy(float)
                if "base_area_km2" in found else np.zeros_like(top))
        keep = np.isfinite(depths) & np.isfinite(top)
        if keep.sum() < 2:
            raise ValueError("fewer than two usable rows: a table needs a depth and a top area "
                             "on at least two lines.")
        return cls(depths_m=depths[keep], top_area_km2=top[keep],
                   base_area_km2=np.nan_to_num(base[keep]))

    @classmethod
    def reference(cls) -> "AreaDepthTable":
        """The reference prospect's own area–depth table, 2040–2400 m."""
        return cls.from_csv(REFERENCE / "defaults" / "area_depth.csv")

    @classmethod
    def from_top_and_thickness(cls, depths_m, top_area_km2,
                              thickness_m: float) -> "AreaDepthTable":
        """Derive the base surface by shifting the top down a constant thickness.

        **The common case.** Most assessors have one mapped surface and a thickness, not two mapped
        surfaces. Shifting the top down by ``T`` says the reservoir is a slab of constant gross
        thickness draped on the structure, so the base area at depth ``z`` is the top area at
        ``z - T``: above the crest plus ``T`` there is no base yet, and the rock volume between them
        is the integral of the difference exactly as it is for two mapped surfaces.

        This is the method SCOPE-HC uses in ``scopehc/geom_depth.py`` — the base is a *depth* shift
        of the top, not an area offset — so a prospect carried between the two tools gets the same
        gross rock volume. (SCOPE-HC also exports a second function of the same name from
        ``scopehc/ui/common.py`` which subtracts the thickness from the *area*; it is dead code and
        dimensionally wrong, and it is not the one being matched here.)

        The derived base is clamped at the top area. That only bites where the supplied top surface
        is not monotone with depth, and there the honest reading is a zero-thickness interval rather
        than a negative one.
        """
        depths = np.asarray(depths_m, dtype=float)
        top = np.asarray(top_area_km2, dtype=float)
        if float(thickness_m) < 0.0:
            raise ValueError("the reservoir thickness cannot be negative")
        if depths.size and top.size == depths.size and float(thickness_m) == 0.0:
            # A slab of no thickness holds no rock. Said explicitly, because the alternative is a
            # table that validates, integrates to zero, and reports charge as never limiting.
            raise ValueError(
                "a reservoir thickness of zero encloses no rock, so the gross rock volume is zero "
                "everywhere and charge can never be a limit. Give it a thickness."
            )
        base = np.interp(depths, depths + float(thickness_m), top, left=0.0)
        return cls(depths_m=depths, top_area_km2=top,
                   base_area_km2=np.minimum(base, top))


@dataclass(frozen=True)
class ChargeResult:
    """Charge-limited contacts, with the cases where charge did not bind flagged rather than hidden."""
    contact_m: np.ndarray            # inf where charge is not limiting
    reservoir_volume_1e6m3: np.ndarray
    gas_oil_contact_m: np.ndarray | None = None

    @property
    def not_limiting(self) -> np.ndarray:
        """Realisations where charge fills past the deepest mapped depth."""
        return ~np.isfinite(self.contact_m)

    @property
    def fraction_not_limiting(self) -> float:
        return float(self.not_limiting.mean())

    @property
    def dry(self) -> np.ndarray:
        """Realisations with no charge at all — the contact sits at the apex, a zero column."""
        return np.isclose(self.contact_m, np.min(self.contact_m)) & (
            self.reservoir_volume_1e6m3 <= 0.0)


def _fill(table: AreaDepthTable, reservoir_volume_1e6m3: np.ndarray,
          k: np.ndarray) -> np.ndarray:
    """Contact depth for a reservoir-condition volume, given ``k = NTG x phi x Sh``."""
    volume = np.asarray(reservoir_volume_1e6m3, dtype=float)
    k = np.asarray(k, dtype=float)
    if np.any(k <= 0):
        raise ValueError("net-to-gross x porosity x saturation must be positive")
    target_grv = np.where(volume > 0.0, volume / k, 0.0)
    return table.depth_at_grv(target_grv)


def oil_contact(table: AreaDepthTable, stoiip_1e6sm3: np.ndarray, bo_m3_per_sm3: np.ndarray,
                k: np.ndarray) -> ChargeResult:
    """Pure oil. ``V_res = STOIIP x Bo``."""
    v = np.asarray(stoiip_1e6sm3, dtype=float) * np.asarray(bo_m3_per_sm3, dtype=float)
    return ChargeResult(contact_m=_fill(table, v, k), reservoir_volume_1e6m3=v)


def gas_contact(table: AreaDepthTable, giip_1e6sm3: np.ndarray, inv_bg_sm3_per_m3: np.ndarray,
                k: np.ndarray) -> ChargeResult:
    """Pure gas. ``V_res = GIIP / (1/Bg)``."""
    inv_bg = np.asarray(inv_bg_sm3_per_m3, dtype=float)
    if np.any(inv_bg <= 0):
        raise ValueError("1/Bg must be positive")
    v = np.asarray(giip_1e6sm3, dtype=float) / inv_bg
    return ChargeResult(contact_m=_fill(table, v, k), reservoir_volume_1e6m3=v)


def mixed_separate(table: AreaDepthTable, oil_leg_stoiip_1e6sm3: np.ndarray,
                   gas_cap_giip_1e6sm3: np.ndarray, bo_m3_per_sm3: np.ndarray,
                   inv_bg_sm3_per_m3: np.ndarray, k: np.ndarray) -> ChargeResult:
    """Oil leg and gas cap charged independently.

    The oil–water contact is set by the **total** volume, the gas–oil contact by the gas alone —
    gas sits above oil, so the gas cap fills first and the oil leg fills below it.
    """
    v_oil = np.asarray(oil_leg_stoiip_1e6sm3, dtype=float) * np.asarray(bo_m3_per_sm3, dtype=float)
    v_gas = np.asarray(gas_cap_giip_1e6sm3, dtype=float) / np.asarray(inv_bg_sm3_per_m3, dtype=float)
    return ChargeResult(contact_m=_fill(table, v_oil + v_gas, k),
                        reservoir_volume_1e6m3=v_oil + v_gas,
                        gas_oil_contact_m=_fill(table, v_gas, k))


def mixed_joint(table: AreaDepthTable, total_stoiip_1e6sm3: np.ndarray,
                total_giip_1e6sm3: np.ndarray, gor_sm3_per_sm3: np.ndarray,
                cgr_sm3_per_1e6sm3: np.ndarray, bo_m3_per_sm3: np.ndarray,
                inv_bg_sm3_per_m3: np.ndarray, k: np.ndarray) -> ChargeResult:
    """One charge stream, split into an oil leg and a free gas cap by GOR and CGR.

    Total oil is the oil leg plus condensate dropped out of the non-associated gas; total gas is the
    gas dissolved in the oil plus that free gas. Solving the pair::

        O = (L - CGR x M) / (1 - CGR x GOR)      free gas  Q = M - GOR x O

    **A negative Q means there is no free gas cap** — every molecule of gas is accounted for as
    solution gas in the oil leg. That is a real outcome and a common one, and the temptation is to
    carry the negative volume onward, which reports a gas–oil contact at the apex: a gas cap of
    zero thickness rather than no gas cap at all. Here the GOC is ``nan`` for those realisations,
    so it cannot be plotted as if it were a contact.
    """
    cgr = np.asarray(cgr_sm3_per_1e6sm3, dtype=float) / 1e6
    gor = np.asarray(gor_sm3_per_sm3, dtype=float)
    total_oil = np.asarray(total_stoiip_1e6sm3, dtype=float)
    total_gas = np.asarray(total_giip_1e6sm3, dtype=float)

    denominator = 1.0 - cgr * gor
    if np.any(np.isclose(denominator, 0.0)):
        raise ValueError(
            "CGR x GOR = 1, so the oil and gas streams cannot be separated; check the units — "
            "CGR is Sm3 per million Sm3 and GOR is Sm3 per Sm3"
        )
    oil = (total_oil - cgr * total_gas) / denominator
    free_gas = total_gas - gor * oil

    v_oil = np.clip(oil, 0.0, None) * np.asarray(bo_m3_per_sm3, dtype=float)
    v_gas = np.clip(free_gas, 0.0, None) / np.asarray(inv_bg_sm3_per_m3, dtype=float)
    goc = np.where(free_gas > 0.0, _fill(table, v_gas, k), np.nan)
    return ChargeResult(contact_m=_fill(table, v_oil + v_gas, k),
                        reservoir_volume_1e6m3=v_oil + v_gas,
                        gas_oil_contact_m=goc)


def column_height_from_contact(contact_m: np.ndarray, apex_m: np.ndarray) -> np.ndarray:
    """Contact depths to column heights below the apex, for the engine's limit interface.

    ``inf`` passes straight through, which is what makes a non-limiting charge lose the minimum.
    """
    return np.asarray(contact_m, dtype=float) - np.asarray(apex_m, dtype=float)


@dataclass(frozen=True)
class ChargeColumns:
    """Charge-limited columns below the *prospect's* apex, with what the conversion had to do."""
    #: Column height below the prospect apex, finite realisations only, metres.
    column_m: np.ndarray
    #: Table crest minus the prospect apex, metres. Positive means the table starts below the
    #: apex the assessor elicited; negative means above it.
    crest_offset_m: float
    #: Share of the limiting realisations whose contact lay above the prospect apex and were
    #: set to a zero column. Dry realisations (no charge) are counted here too: their contact is
    #: the table crest, and a zero column is their true value in any frame.
    share_clipped: float


def columns_below_apex(result: ChargeResult, prospect_apex_m: float,
                       table: AreaDepthTable) -> ChargeColumns:
    """Audit finding P2-2, 14 Sep 2026: measure the charge column from the prospect apex.

    The fill depth is a depth on the area-depth table's own map. The engine states a charge
    limit as a column and adds the apex it drew in each realisation, so a column measured from
    the *table's* crest lands the contact deeper by the gap between that crest and the elicited
    apex -- 10 m on the shipped prospect, unbounded on an imported table whose first row is not
    the crest. Measured from the prospect apex instead, the engine's contact reproduces the
    table's fill depth to within the apex draw, which is the map's own uncertainty.

    A contact above the prospect apex is a zero column: either the realisation carried no charge
    and its contact is the crest, or the table's crest sits above the apex and the volume filled
    less than the gap. Both are reported through ``share_clipped`` rather than hidden, and
    ``crest_offset_m`` says how far the two crests disagree so the panel can warn.
    """
    finite = result.contact_m[np.isfinite(result.contact_m)]
    raw = finite - float(prospect_apex_m)
    clipped = raw < 0.0
    return ChargeColumns(column_m=np.where(clipped, 0.0, raw),
                         crest_offset_m=float(table.apex_m - prospect_apex_m),
                         share_clipped=float(clipped.mean()) if raw.size else 0.0)


def table_short_of_spill(table: AreaDepthTable, spill_m: float | None) -> float | None:
    """Audit finding P2-3, 14 Sep 2026: metres by which the table ends above the spill.

    A charge that fills past the table's last row is declared not limiting, which is right when
    the table reaches the spill and wrong when it stops short: charge that would have bound
    between the table's end and the spill is then counted as no limit at all. Returns the gap
    in metres when the table ends above the spill, ``0.0`` when it reaches it, and ``None`` when
    no spill depth is known. The caller decides whether to warn or refuse.
    """
    if spill_m is None:
        return None
    gap = float(spill_m) - table.deepest_m
    return gap if gap > 0.0 else 0.0
