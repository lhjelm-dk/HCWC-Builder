"""Every figure and table the app draws, at the paper's scenario, as PNGs named by number.

    python scripts/export_exhibits.py

**The scenario is read from `paper_facts.py`, not typed here.** The exhibits and the paper's
numbers have to describe one prospect at one set of settings. They did not once: the export ran at
the app's opening state while the text quoted a different scenario, and figure 10 carried markers
saying 46.7 % beside a text saying 63.9 % (found 24 Sep 2026). Since 28 Sep 2026 the scenario is
the app's own opening state, by Lars's decision, and :data:`SCENARIO` takes its values from
`paper_facts` so that changing one moves both.

One run of the app through ``AppTest``, then each registered exhibit written to
``paper/figures`` as ``Figure_4.1.1a_<slug>.png`` or ``Table_5.1.4c_<slug>.png``, in the aspect
ratio the browser shows: the app's content column is 1 180 px wide and a figure states its own
height, so the export keeps that ratio at :data:`WIDTH_PX` and doubles the resolution.

Tab 1's two figures are not in the registry -- tab 2 resets it, so the guide and the concept
sketch stay out of the results export -- so they are written from their source files with the
captions read off the rendered page.

``paper/figures/MANIFEST.md`` lists every file with its number, where in the app it comes from,
and its caption.
"""
from __future__ import annotations

import contextlib
import io as _io
import pathlib
import re
import sys
import warnings

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import paper_facts as _facts  # noqa: E402  -- the scenario, so the two cannot drift apart

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = ROOT / "paper" / "figures"
#: The app's content column, from the CSS in `app.py`: the width every figure is laid out at.
CONTENT_PX = 1180
#: What the export is drawn at; `scale=2` doubles the pixels without changing the ratio.
WIDTH_PX = 1400
#: What Streamlit gives a Plotly figure that states no height of its own.
DEFAULT_FIG_HEIGHT_PX = 450
#: What the app is set to before anything is captured, so the exhibits and `paper_facts.py`
#: describe one prospect. Both differ from the app's opening state; everything else does not.
SCENARIO = {
    "min_column_input": _facts.H_MIN_M,
    "dhi_in_strength": _facts.EVIDENCE_INDEX,
}

#: Tab 1's two figures, which the registry does not carry.
TAB_ONE = (
    ("Figure 1.0a", ROOT / "docs" / "figures" / "fig0_workflow_guide.svg",
     "tab 1.0, the guide version of the workflow figure"),
    ("Figure 1.1a", ROOT / "reference" / "defaults" / "concept.png",
     "tab 1.1, the section sketch"),
)


def slug(caption: str, limit: int = 44) -> str:
    """A short, readable tail for the filename, from the first words of the caption."""
    text = re.sub(r"<[^>]+>", " ", caption)
    text = re.sub(r"[`*_$\\]", "", text)
    words = re.findall(r"[A-Za-z0-9]+", text)
    out: list[str] = []
    for word in words:
        if len("-".join(out + [word])) > limit:
            break
        out.append(word.lower())
    return "-".join(out) or "exhibit"


def file_name(label: str, caption: str) -> str:
    """``Figure 4.1.1a`` and its caption -> ``Figure_4.1.1a_the-competition.png``."""
    kind, number = label.split(" ", 1)
    return f"{kind}_{number}_{slug(caption)}.png"


def figure_size(fig) -> tuple[int, int]:
    """The export size, at the ratio the browser shows."""
    height = getattr(fig.layout, "height", None) or DEFAULT_FIG_HEIGHT_PX
    return WIDTH_PX, int(round(WIDTH_PX * height / CONTENT_PX))


def write_plotly(fig, path: pathlib.Path) -> None:
    import plotly.io as pio

    width, height = figure_size(fig)
    fig.update_layout(template="plotly_white", font=dict(size=13),
                      margin=dict(l=70, r=30, t=40, b=60))
    pio.write_image(fig, path, width=width, height=height, scale=2)


def write_image_file(source: pathlib.Path, path: pathlib.Path) -> None:
    """Copy a PNG, or rasterise an SVG at the export width."""
    if source.suffix.lower() == ".svg":
        import plotly.graph_objects as go
        import plotly.io as pio

        data = source.read_bytes()
        import base64

        uri = "data:image/svg+xml;base64," + base64.b64encode(data).decode("ascii")
        # The SVG's own aspect ratio, from its viewBox.
        box = re.search(rb'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"', data)
        ratio = (float(box.group(2)) / float(box.group(1))) if box else 0.5
        height = int(round(WIDTH_PX * ratio))
        fig = go.Figure()
        fig.add_layout_image(dict(source=uri, xref="paper", yref="paper", x=0, y=1,
                                  sizex=1, sizey=1, xanchor="left", yanchor="top",
                                  layer="below", sizing="stretch"))
        fig.update_xaxes(visible=False, range=[0, 1])
        fig.update_yaxes(visible=False, range=[0, 1])
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="white",
                          plot_bgcolor="white")
        pio.write_image(fig, path, width=WIDTH_PX, height=height, scale=2)
    else:
        import shutil

        shutil.copyfile(source, path)


def _rows_from_markdown(body: str) -> tuple[list[str], list[list[str]]]:
    lines = [ln.strip() for ln in body.strip().split("\n") if ln.strip().startswith("|")]
    grid = [[c.strip() for c in ln.strip("|").split("|")] for ln in lines]
    grid = [row for row in grid if not all(set(c) <= set("-: ") for c in row)]
    return (grid[0], grid[1:]) if grid else ([], [])


def write_table(payload, path: pathlib.Path) -> None:
    """A table as an image, in the app's reading order, at the export width."""
    if isinstance(payload, str):
        header, rows = _rows_from_markdown(payload)
    else:
        frame = payload
        header = [str(c) for c in frame.columns]
        rows = [[("" if v is None else str(v)) for v in row] for row in frame.to_numpy()]
    if not header:
        header, rows = ["(empty)"], []
    n = max(len(rows), 1)
    fig, ax = plt.subplots(figsize=(WIDTH_PX / 200, max(1.0, 0.34 * (n + 1.6))), dpi=200)
    ax.axis("off")
    table = ax.table(cellText=rows or [[""] * len(header)], colLabels=header,
                     cellLoc="left", colLoc="left", loc="upper left")
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.35)
    for (row, _col), cell in table.get_celld().items():
        cell.set_linewidth(0.4)
        cell.set_edgecolor("#dfe3e8")
        if row == 0:
            cell.set_facecolor("#eef1f5")
            cell.set_text_props(weight="bold")
    with contextlib.suppress(Exception):
        table.auto_set_column_width(range(len(header)))
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    from streamlit.testing.v1 import AppTest

    from hcwc.exhibits import figure_order
    from hcwc.plotting.paper import manifest
    from hcwc.ui import numbering

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=900)
    with contextlib.redirect_stderr(_io.StringIO()):
        at.run()
    assert not at.exception, "\n".join(str(e.value) for e in at.exception)

    # The paper's scenario, drawn a second time: the widgets exist only after the first run.
    for key, value in SCENARIO.items():
        at.session_state[key] = value
    with contextlib.redirect_stderr(_io.StringIO()):
        at.run()
    assert not at.exception, "\n".join(str(e.value) for e in at.exception)
    live = at.session_state["limit_set"].min_column_m
    assert live == SCENARIO["min_column_input"], (
        f"the assessment minimum did not take: {live} m, not {SCENARIO['min_column_input']} m")

    figures = at.session_state[numbering.FIGURES_KEY] or {}
    tables = at.session_state[numbering.TABLES_KEY] or {}
    captions = "\n".join(str(c.value) for c in at.caption) + "\n" + \
               "\n".join(str(m.value) for m in at.markdown)

    OUT.mkdir(parents=True, exist_ok=True)
    entries: list[manifest.Entry] = []

    # Tab 1 first: its two figures are not in the registry.
    for label, source, where in TAB_ONE:
        found = re.search(rf"\*\*{re.escape(label)}\*\*\s*[—-]?\s*(.+)", captions)
        caption = manifest.strip_chips(found.group(1).strip()) if found else ""
        name = file_name(label, caption or source.stem)
        write_image_file(source, OUT / name)
        entries.append(manifest.Entry(label, name, where, caption))
        print(f"  {name}")

    for label in sorted(set(figures) | set(tables), key=figure_order):
        if label in figures:
            payload, caption = figures[label]
            caption = manifest.strip_chips(caption)
            name = file_name(label, caption)
            if isinstance(payload, (str, pathlib.Path)):
                write_image_file(pathlib.Path(payload), OUT / name)
                where = f"the app's {label}, from {pathlib.Path(payload).name}"
            else:
                write_plotly(payload, OUT / name)
                where = f"the app's {label}"
        else:
            payload, caption, _hide = tables[label]
            caption = manifest.strip_chips(caption)
            name = file_name(label, caption)
            write_table(payload, OUT / name)
            where = f"the app's {label}"
        entries.append(manifest.Entry(label, name, where, caption))
        print(f"  {name}")

    manifest.write(OUT / "MANIFEST.md", entries, {
        "prospect": ("the app's defaults (Tiramisu-C4) at the paper's scenario -- assessment "
                     "minimum 120 m, evidence index 20 -- `paper/figures/prospect.json`"),
        "seed": 20260825, "realisations": 10_000,
        "export": f"{WIDTH_PX} px wide at scale 2, the browser's ratio "
                  f"({CONTENT_PX} px content column)",
        "script": "`scripts/export_exhibits.py`",
    })
    print(f"  MANIFEST.md\n\n{len(entries)} exhibits written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
