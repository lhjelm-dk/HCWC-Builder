"""`paper/cheatsheet.html` as an A3 PDF.

    python scripts/cheatsheet.py

The sheet is a single self-contained HTML file: all the text is plain markup, the whole design is
one `<style>` block at the top, and every figure is one the app exported into `paper/figures/`.
Edit it in any text editor and reload it in a browser; nothing is generated from a template.

The PDF is printed by headless Chrome or Edge, which is the only renderer here that honours the
`@page { size: A3 landscape }` rule and the print stylesheet. Without a browser on the machine the
HTML is still the deliverable: open it and print to PDF by hand.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
#: Which sheet to print. The first design is the default; pass a stem for any other, so the
#: designs sit beside each other rather than replacing one another.
STEM = sys.argv[1] if len(sys.argv) > 1 else "cheatsheet"
SHEET = ROOT / "paper" / f"{STEM}.html"
PDF = ROOT / "paper" / f"{STEM}.pdf"

#: Where a browser is, if one is. Chrome first: its `--print-to-pdf` honours `@page` size.
BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def _browser() -> str | None:
    for path in BROWSERS:
        if pathlib.Path(path).exists():
            return path
    return shutil.which("chrome") or shutil.which("msedge") or shutil.which("chromium")


def standalone(sheet: pathlib.Path) -> pathlib.Path:
    """The sheet with every figure inlined, so it survives being moved or emailed.

    The sheet references ``figures/*.png`` beside it, which is right for editing and for the PDF
    and wrong the moment the file travels on its own: a viewer that loads it without a base path
    resolves none of them, which is what the desktop preview does by serving it as a ``data:`` URL.
    This writes a copy with each PNG as a ``data:`` URI: several megabytes, and portable.
    """
    import base64
    import re

    html = sheet.read_text(encoding="utf-8")

    def _inline(match: re.Match) -> str:
        src = match.group(1)
        image = sheet.parent / src
        if not image.exists():
            print(f"  missing, left as a path: {src}")
            return match.group(0)
        data = base64.b64encode(image.read_bytes()).decode("ascii")
        return f'<img src="data:image/png;base64,{data}"'

    html = re.sub(r'<img src="([^"]+\.png)"', _inline, html)
    out = sheet.with_name(sheet.stem + "-standalone.html")
    out.write_text(html, encoding="utf-8")
    return out


def main() -> int:
    if not SHEET.exists():
        print(f"{SHEET.relative_to(ROOT)} not found")
        return 1
    exe = _browser()
    if exe is None:
        print("no Chrome or Edge found; open paper/cheatsheet.html and print to PDF by hand")
        return 1

    # A profile of its own, so the run cannot touch the user's browser session, and a virtual time
    # budget so the webfonts and the twelve figures are in before the page is printed.
    with __import__("tempfile").TemporaryDirectory() as profile:
        subprocess.run(
            [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
             f"--user-data-dir={profile}", "--window-size=1600,1200",
             "--run-all-compositor-stages-before-draw", "--virtual-time-budget=20000",
             "--no-pdf-header-footer", f"--print-to-pdf={PDF}", SHEET.as_uri()],
            check=True, capture_output=True)

    print(f"  {PDF.relative_to(ROOT)}  ({PDF.stat().st_size // 1024} KB)")
    one = standalone(SHEET)
    print(f"  {one.relative_to(ROOT)}  ({one.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
