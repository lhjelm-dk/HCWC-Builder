"""Saving and reloading a whole prospect.

Until this existed, everything lived in ``st.session_state`` and closing the browser tab threw away
an hour of eliciting twelve limits. The core could already round-trip a
:class:`~hcwc.core.limits.LimitSet` through JSON; nothing in the app called it.

**What is saved is the inputs, not the answer.** Every widget the user touched, keyed exactly as
Streamlit keys it, plus a copy of the resolved limit set for provenance. Reloading replays the
inputs and the engine recomputes — so a file opened after the model changes gives the *new* answer
to the *old* question, which is what you want from a record of an assessment. Saving the outputs
instead would produce a file that quietly disagreed with the tool that opened it.

**Why the widget keys and not a tidy schema.** A tidy schema would have to be kept in step with
twelve limit blocks, three calculators and their dozen sliders each, by hand, forever — and the
first thing to drift would be a calculator input, silently, so a reloaded prospect would recompute
from different numbers and nobody would notice. The keys *are* the schema, and
:data:`PREFIXES` says which of them belong to the document.
"""
from __future__ import annotations

import json
import math
from typing import Any

#: Bumped when the meaning of a key changes, not when one is added. Readers refuse a newer major.
FORMAT_VERSION = 1

#: Session-state keys that make up a saved prospect. Exact names first, then prefixes.
#:
#: Deliberately an allow-list. A deny-list would let every future widget into the file by default,
#: including caches and one-shot UI state, and a saved file would then restore things like an open
#: expander or a stale DHI overlay.
EXACT: frozenset[str] = frozenset({
    "prospect_name", "apex_p1", "apex_p99", "spill_input", "burial_input",
    "dhi_toggle", "min_column_input", "n_trials_input", "seed_input", "gradient_range",
    "stack_space", "stack_mode",
})

#: Any key starting with one of these is part of the document.
#:
#: ``lim_`` and ``extra_`` carry every limit block — the include toggle, ``P(active)``, the space,
#: the distribution and its parameters, the source radio, **and each calculator's own inputs**, so
#: a computed limit recomputes from the numbers it was computed from rather than from defaults.
PREFIXES: tuple[str, ...] = ("lim_", "extra_", "src_", "play_", "cond_")


def _items(state) -> list[tuple[str, Any]]:
    """Key/value pairs, from a plain dict **or** from Streamlit's session state.

    ``SafeSessionState`` is not a ``Mapping`` and is unhelpful about it. It has no ``.items()``,
    no ``.keys()`` and no ``.to_dict()``; attribute access on a missing name **raises** instead of
    returning a bound method, so ``state.items()`` fails with *"items not found in session_state"*,
    which reads like a missing key rather than a missing method; and iterating it yields integer
    indices, so ``list(state)`` then fails looking up a key called ``"0"``.

    Its one usable accessor is ``filtered_state``, a plain dict of the user-visible keys. Plain
    dicts are handled first so the tests can pass one in.
    """
    if isinstance(state, dict):
        return list(state.items())
    filtered = getattr(state, "filtered_state", None)
    if isinstance(filtered, dict):
        return list(filtered.items())
    return list(dict(state).items())


def document(state, *, limit_set=None) -> dict:
    """Build the saveable document from the live session state."""
    inputs = {k: _plain(v) for k, v in _items(state)
              if (k in EXACT or k.startswith(PREFIXES)) and _saveable(v)}
    doc: dict[str, Any] = {
        "format": FORMAT_VERSION,
        "tool": "HCWC Distribution Builder",
        "name": str(inputs.get("prospect_name", "Prospect")),
        "inputs": inputs,
    }
    if limit_set is not None:
        # A copy of the resolved model, for provenance and for reading the file without the app.
        # Never read back on load: the inputs are the source of truth, and restoring both would
        # create two places for the same fact to live.
        doc["resolved"] = limit_set.to_dict()
    return doc


def to_json(state, *, limit_set=None) -> str:
    return json.dumps(document(state, limit_set=limit_set), indent=2)


def read(text: str) -> dict:
    """Parse and validate a saved prospect, returning the ``inputs`` mapping to apply.

    Raises with a reason rather than half-applying. A partially restored prospect is worse than a
    refused one: it looks like it worked.
    """
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not a valid JSON file: {exc}") from exc
    if not isinstance(doc, dict) or "inputs" not in doc:
        raise ValueError("this does not look like a saved prospect — no `inputs` section")
    version = doc.get("format", 0)
    if not isinstance(version, int) or version > FORMAT_VERSION:
        raise ValueError(
            f"saved by a newer version of the tool (format {version}, this reads {FORMAT_VERSION}). "
            "Update the app rather than editing the file."
        )
    inputs = doc["inputs"]
    if not isinstance(inputs, dict):
        raise ValueError("`inputs` must be an object of widget keys")
    unknown = [k for k in inputs if not (k in EXACT or k.startswith(PREFIXES))]
    if unknown:
        raise ValueError(
            "the file carries keys this version does not recognise: "
            + ", ".join(sorted(unknown)[:6])
            + ("…" if len(unknown) > 6 else "")
        )
    _check_values(inputs)
    return {k: _restore(v) for k, v in inputs.items()}


#: Widget keys whose value must be a number, and the range the widget that owns it will accept.
#: Anything outside makes Streamlit raise **while building the widget** — which happens after these
#: values are already in session state, at module scope in ``app.py``, where there is nothing to
#: catch it. The result is a full-page traceback with no way back but clearing the session.
#:
#: So the check has to happen here, before anything is written. Only the keys with fixed bounds are
#: listed; the rest are checked for type alone, which is enough to stop a string reaching a numeric
#: widget.
NUMERIC_BOUNDS: dict[str, tuple[float, float]] = {
    "n_trials_input": (1_000, 100_000),
    "seed_input": (0, 2**31 - 1),
    "min_column_input": (0.0, 10_000.0),
    "apex_p1": (0.0, 10_000.0),
    "apex_p99": (0.0, 10_000.0),
    "spill_input": (0.0, 10_000.0),
    "burial_input": (0.0, 10_000.0),
}

#: What a restored value is allowed to be. Widget state is scalars and sequences of scalars; a
#: mapping is never one, and a value carrying a mapping is a file that was hand-edited or produced
#: by something else.
_SCALARS = (bool, int, float, str)


def _check_values(inputs: dict) -> None:
    """Refuse a file whose values would crash a widget, rather than half-applying it.

    The key check above is an allow-list and it is good. This is the other half: a **recognised**
    key carrying ``"banana"`` or ``-5`` used to pass straight through, land in session state, and
    take the page down on the next render. Refusing here keeps the promise the docstring already
    makes — that a partially restored prospect is worse than a refused one.
    """
    for key, raw in sorted(inputs.items()):
        # A range slider is stored as `{"__tuple__": [...]}` by `_plain`, so an object is a legal
        # encoding here and only its *contents* can be wrong. Decode first, then judge — the first
        # version of this check rejected every seal calculator in every saved prospect.
        if isinstance(raw, dict) and set(raw) != {"__tuple__"}:
            raise ValueError(f"`{key}` holds an object where a value was expected")
        value = _restore(raw)

        if isinstance(value, (list, tuple)):
            if not all(isinstance(v, _SCALARS) or v is None for v in value):
                raise ValueError(f"`{key}` holds a list with something other than numbers in it")
            continue
        if not (value is None or isinstance(value, _SCALARS)):
            raise ValueError(f"`{key}` holds a {type(value).__name__}, which is not a widget value")

        low_high = NUMERIC_BOUNDS.get(key)
        if low_high is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"`{key}` must be a number, and this file has {value!r}")
        if not math.isfinite(value):
            raise ValueError(f"`{key}` is {value!r}, which is not a finite number")
        low, high = low_high
        if not low <= value <= high:
            raise ValueError(
                f"`{key}` is {value:g}, outside the {low:g} to {high:g} this version accepts. "
                "The file was probably written by a different build."
            )


def _saveable(value: Any) -> bool:
    if isinstance(value, (str, bool, int, float)) or value is None:
        return True
    return isinstance(value, (list, tuple)) and all(
        isinstance(x, (str, bool, int, float)) for x in value)


def _plain(value: Any):
    """Tuples become lists so the JSON round-trip is lossless in shape as well as value."""
    if isinstance(value, tuple):
        return {"__tuple__": [_plain(x) for x in value]}
    return value


def _restore(value: Any):
    """Undo :func:`_plain`.

    Range sliders hold a **tuple**, and Streamlit rejects a list where it expects one — so the
    distinction has to survive the file. Encoding it explicitly is uglier than letting JSON flatten
    it, and it is the difference between a seal calculator that reopens and one that raises.
    """
    if isinstance(value, dict) and "__tuple__" in value:
        return tuple(_restore(x) for x in value["__tuple__"])
    return value
