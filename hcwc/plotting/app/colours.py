"""One colour per limit, shared by every figure that names mechanisms."""
from __future__ import annotations

from hcwc.core.limits import Group
from hcwc.ui import theme


def limit_colours(limit_set) -> dict[str, str]:
    """One colour per limit: a **variation of its risk element's hue**.

    Rule: fault leakage and the seals are retention mechanisms, so they are
    greens -- but not *the* retention green, which stays reserved for the element itself. Hue says
    which element a limit belongs to at a glance; lightness separates the limits inside it. That
    matters because colouring purely by element left five retention limits in one indistinguishable
    red, which defeats the point of a diagnostic whose whole job is to name mechanisms.

    Until 18 Sep 2026 this lived in `results_tab` and a private copy in `limit_stack`, and three
    tabs imported `results_tab` for it; one implementation here, imported by all.
    """
    out: dict[str, str] = {}
    for group in Group:
        members = [name for name, g in zip(limit_set.names, limit_set.groups) if g is group]
        for name, colour in zip(members, theme.element_shades(group.value, len(members))):
            out[name] = colour
    return out
