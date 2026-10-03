"""Figure 5.2.2a in all three of its views, for the cheat sheet.

The registry export takes whatever the radio defaults to, which is Given the DHI. The sheet wants
the three side by side, so this drives `controlling_view_5` through its options and writes one PNG
per view beside the other exports.
"""
import contextlib
import io as _io
import pathlib
import sys
import warnings

ROOT = pathlib.Path(r"D:/Dokumenter/Lars/Pythonscripts/HCWC builder")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import export_exhibits as ex          # noqa: E402  (path set above)
from streamlit.testing.v1 import AppTest   # noqa: E402
from hcwc.ui import numbering, theme       # noqa: E402

OUT = ROOT / "paper" / "figures"
LABEL = "Figure 5.2.2a"
KEY = "controlling_view_5"

at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=900)
with contextlib.redirect_stderr(_io.StringIO()):
    at.run()
assert not at.exception, "\n".join(str(e.value) for e in at.exception)

for key, value in ex.SCENARIO.items():
    at.session_state[key] = value
with contextlib.redirect_stderr(_io.StringIO()):
    at.run()
assert not at.exception, "\n".join(str(e.value) for e in at.exception)

VIEWS = {
    "geological": "Geological",
    "given-dhi": theme.evidence_title(),
    "what-changed": "What the evidence changed",
}

for slug, option in VIEWS.items():
    at.session_state[KEY] = option
    with contextlib.redirect_stderr(_io.StringIO()):
        at.run()
    assert not at.exception, "\n".join(str(e.value) for e in at.exception)
    figures = at.session_state[numbering.FIGURES_KEY] or {}
    assert LABEL in figures, f"{LABEL} not in the registry for view {option!r}"
    payload, caption = figures[LABEL]
    name = f"Figure_5.2.2a_view-{slug}.png"
    ex.write_plotly(payload, OUT / name)
    print(f"  {name}   [{option}]")
    print(f"      {caption.splitlines()[0][:130]}")
