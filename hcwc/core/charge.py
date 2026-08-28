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
    def from_csv(cls, path: str | Path) -> "AreaDepthTable":
        import pandas as pd
        d = pd.read_csv(path, comment="#")
        return cls(depths_m=d.depth_m.to_numpy(float),
                   top_area_km2=d.top_area_km2.to_numpy(float),
                   base_area_km2=d.base_area_km2.to_numpy(float))

    @classmethod
    def reference(cls) -> "AreaDepthTable":
        """The reference prospect's own area–depth table, 2040–2400 m."""
        return cls.from_csv(REFERENCE / "area_depth.csv")


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
