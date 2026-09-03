"""Reading element risk out of an E-POS prospect file.

E-POS is upstream: it produces the four element chances this tool multiplies its derived curves by
on tab 4.0. Retyping them is the obvious way to get a number wrong, so they are read from the file
E-POS already writes.

**The parsing target is E-POS's own save format**, ``data/prospect_schema.py`` — a CSV whose
leading ``#`` rows carry metadata, one of which is::

    # Classic POS, <charge>, <closure>, <reservoir>, <retention>

Fixed order, four floats, no ambiguity. That row is the contract.

**What this deliberately does not do is recompute the ESL rollup.** E-POS's headline number comes
from combining belief masses up a play × conditional tree with an uncertainty *stance* applied once
at the top (``logic/dfi_context.py::esl_rollup_prior_at_w``), and per-pillar figures come from
``policy_pos`` at that stance. Reimplementing any of that here would duplicate the part of E-POS
most likely to change, and the two copies would drift silently — the failure mode being a POS in
this tool that no longer matches the one the analyst booked. So an ESL prospect is *detected* and
*reported*, and the user is told to confirm the numbers against E-POS rather than being handed a
reconstruction.

The second accepted form is a flat JSON object, which is what a future "export element POS" button
in E-POS should write, and what anyone integrating a different risk tool can produce in a line.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field

#: E-POS's pillar order in the ``# Classic POS`` row. Positional, so it cannot be reordered.
CLASSIC_ORDER: tuple[str, ...] = ("Charge", "Closure", "Reservoir", "Retention")


@dataclass(frozen=True)
class ElementPos:
    """Four element chances, with where they came from and what to distrust about them."""

    values: dict[str, float]
    source: str
    title: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        missing = [p for p in CLASSIC_ORDER if p not in self.values]
        if missing:
            raise ValueError(f"missing element chances for {', '.join(missing)}")
        for name, value in self.values.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} chance must be a probability, got {value}")


def _from_classic_row(row: list[str]) -> dict[str, float]:
    return {name: float(row[i + 1]) for i, name in enumerate(CLASSIC_ORDER)}


def read_epos_csv(text: str) -> ElementPos:
    """Parse an E-POS prospect CSV and return its four element chances.

    Raises if the ``# Classic POS`` row is absent, rather than falling back to defaults. A silent
    default here would be indistinguishable from a real elicitation downstream.
    """
    title = ""
    values: dict[str, float] | None = None
    has_esl = False

    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        head = row[0].strip()
        if head.startswith(("# E-POS Prospect", "# GeoRisk Prospect")) and len(row) > 1:
            title = row[1].strip()
        elif head.startswith("# Classic POS") and len(row) >= 5:
            try:
                values = _from_classic_row(row)
            except (TypeError, ValueError):
                continue
        elif head.startswith(("# ESL play", "# ESL conditional")) and len(row) >= 2:
            try:
                if json.loads(row[1]):
                    has_esl = True
            except json.JSONDecodeError:
                pass

    if values is None:
        raise ValueError(
            "no `# Classic POS` row found. This does not look like an E-POS prospect file — "
            "E-POS writes that row on every save, in the order Charge, Closure, Reservoir, "
            "Retention."
        )

    warnings: list[str] = []
    if has_esl:
        warnings.append(
            "This prospect also carries **ESL** play and conditional evidence, and E-POS's headline "
            "P(G, ESL) is a belief-mass rollup with an uncertainty stance applied at the top — not "
            "the Classic POS read here, and usually not equal to it. These four numbers are "
            "therefore the *Classic* figures. If you book the ESL number, read the per-pillar Pg "
            "off E-POS and override below."
        )
    return ElementPos(values=values, source="E-POS prospect CSV (Classic POS row)",
                      title=title, warnings=tuple(warnings))


def read_json(text: str) -> ElementPos:
    """Parse the flat interchange form: ``{"Charge": 0.9, "Closure": 1.0, ...}``.

    Also accepts the four keys nested under ``"element_pos"``, and a ``"title"`` beside it, so the
    same reader takes both a bare object and a fuller export.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object mapping element names to probabilities")

    body = payload.get("element_pos", payload)
    if not isinstance(body, dict):
        raise ValueError("`element_pos` must be an object mapping element names to probabilities")

    # Case-insensitive so "charge" and "Charge" both land, but never abbreviated: a tool that
    # guessed "Ret" meant Retention would eventually guess wrong.
    lowered = {str(k).strip().lower(): v for k, v in body.items()}
    missing = [p for p in CLASSIC_ORDER if p.lower() not in lowered]
    if missing:
        raise ValueError(
            f"missing {', '.join(missing)}. Expected all four of {', '.join(CLASSIC_ORDER)}"
        )
    try:
        values = {p: float(lowered[p.lower()]) for p in CLASSIC_ORDER}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"element chances must be numbers: {exc}") from exc

    return ElementPos(values=values, source="JSON element-POS export",
                      title=str(payload.get("title", "")))


def read(text: str) -> ElementPos:
    """Accept either form, chosen by content rather than by file extension.

    Extension-based dispatch fails on the case that actually happens — a `.csv` saved out of a
    spreadsheet as JSON, or the reverse — so the leading non-whitespace character decides.
    """
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return read_json(text)
    return read_epos_csv(text)


def to_json(values: dict[str, float], title: str = "") -> str:
    """Write the interchange form, so this tool can hand element risk on as well as take it."""
    return json.dumps({"title": title,
                       "element_pos": {p: round(float(values[p]), 6) for p in CLASSIC_ORDER}},
                      indent=2)
