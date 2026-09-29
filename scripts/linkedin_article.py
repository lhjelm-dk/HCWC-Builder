"""`paper/ARTICLE.md` as a page that can be pasted into LinkedIn's article editor.

    python scripts/linkedin_article.py

LinkedIn's editor keeps headings, bold, italics, lists and quotes from a rich-text paste, and
supports no maths, no tables and no subscripts. Copying the article from tab 8.2 therefore fails
twice over: KaTeX renders every formula both as styled HTML and as MathML for screen readers, so a
browser copy takes both and each expression arrives doubled -- `P(G)->P(G|s)P(G)->P(G|s)` -- and
what does survive loses its subscripts.

This writes `paper/ARTICLE_LINKEDIN.html` with the maths already flattened to Unicode, the table
turned into lines, and a marker where each figure goes. Open it in a browser, select all, and paste
into the editor: the formatting survives and every formula appears once.

It also writes `paper/LINKEDIN_POST.html` from `paper/LINKEDIN_POST.md`. That one is for the feed
composer rather than the article editor, and the composer is plain text: a rich-text paste arrives
with its bold stripped. The headline is therefore converted to the Unicode sans-serif bold block,
which survives because it is characters rather than formatting.

Nothing here is a second copy of the article or the post. Every page is generated from its Markdown
source on every run, so the source stays the one source.
"""
from __future__ import annotations

import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
#: Each article and the page written from it. The short one is what goes to LinkedIn; the long one
#: is kept paste-ready because it is occasionally wanted as a document.
PAGES = [
    (ROOT / "paper" / "ARTICLE.md", ROOT / "paper" / "ARTICLE_LINKEDIN.html"),
    (ROOT / "paper" / "ARTICLE_SHORT.md", ROOT / "paper" / "ARTICLE_LINKEDIN_SHORT.html"),
]

#: The feed post, which is written and pasted separately from the article.
POST = (ROOT / "paper" / "LINKEDIN_POST.md", ROOT / "paper" / "LINKEDIN_POST.html")

#: Unicode sans-serif bold. The feed composer keeps no formatting, so a headline that has to read
#: as a headline has to be spelled in characters that are already bold.
BOLD = {**{chr(ord("A") + i): chr(0x1D5D4 + i) for i in range(26)},
        **{chr(ord("a") + i): chr(0x1D5EE + i) for i in range(26)},
        **{chr(ord("0") + i): chr(0x1D7EC + i) for i in range(10)}}

#: Unicode subscripts, for the few subscripts whose characters all exist. An uppercase subscript
#: has no Unicode form at all, so `z_HCWC` keeps its underscore rather than losing the structure.
SUBSCRIPTS = str.maketrans("aeioruvxhklmnpst0123456789", "ₐₑᵢₒᵣᵤᵥₓₕₖₗₘₙₚₛₜ₀₁₂₃₄₅₆₇₈₉")

#: LaTeX this article actually uses, in the order the replacements have to happen.
COMMANDS = [
    (r"\\mathrm\{([^}]*)\}", r"{\1}"),
    (r"\\text\{([^}]*)\}", r"{\1}"),
    (r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1) / (\2)"),
    (r"\\left\(", "("), (r"\\right\)", ")"),
    (r"\\left\[", "["), (r"\\right\]", "]"),
    # Binary operators carry a space on each side; the run is collapsed afterwards. Without this
    # `P(G\mid s)` arrives as `P(G| s)`, which is how it read in the editor.
    (r"\\mid", " | "), (r"\\times", " × "), (r"\\geq", " ≥ "), (r"\\leq", " ≤ "),
    (r"\\propto", " ∝ "), (r"\\approx", " ≈ "), (r"\\neg", "¬"), (r"\\ldots", "…"),
    (r"\\Delta", "Δ"), (r"\\rho", "ρ"), (r"\\sigma", "σ"), (r"\\gamma", "γ"),
    (r"\\theta", "θ"), (r"\\min", "min"), (r"\\max", "max"), (r"\\sum", "Σ"),
    (r"\\,", " "), (r"\\;", " "), (r"\\ ", " "), (r"\\!", ""),
    (r"\\qquad", "  "), (r"\\quad", " "),
    (r"\\rightarrow", " → "), (r"\\to\b", " → "), (r"\\cdot", "·"),
    (r"\\cos", "cos"), (r"\\sin", "sin"), (r"\\tan", "tan"),
    (r"\\log", "log"), (r"\\exp", "exp"), (r"\\%", "%"),
]


def flatten(expression: str) -> str:
    """One LaTeX expression as plain Unicode text."""
    out = expression
    for pattern, replacement in COMMANDS:
        out = re.sub(pattern, replacement, out)
    # `h_{\min}` has become `h_{min}`: subscript it where every character has a Unicode form.
    def _sub(match: re.Match) -> str:
        body = match.group(1)
        # Unicode only for a short, fully representable subscript: hmin and hmax read well that
        # way, z_apex does not, and an uppercase subscript has no Unicode form at all.
        if body and len(body) <= 3 and all(ord(ch) in SUBSCRIPTS for ch in body):
            return body.translate(SUBSCRIPTS)
        return "_" + body
    out = re.sub(r"_\{([^}]*)\}", _sub, out)
    out = re.sub(r"_([A-Za-z0-9])(?![A-Za-z0-9])", _sub, out)
    out = out.replace("{", "").replace("}", "")
    out = re.sub(r"\s*=\s*", " = ", out)
    out = re.sub(r"\s+", " ", out)
    # Tidy what the spacing above leaves at brackets and commas.
    out = re.sub(r"\(\s+", "(", out)
    out = re.sub(r"\s+\)", ")", out)
    out = re.sub(r"\s+([,;.])", r"\1", out)
    out = re.sub(r",(?=\S)", ", ", out)
    return out.strip()


def inline(text: str) -> str:
    """A line of Markdown as HTML, with `$...$` flattened and bold and italics kept."""
    text = re.sub(r"(?<!\$)\$(?!\$)([^$\n]+)\$(?!\$)", lambda m: flatten(m.group(1)), text)
    text = html.escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def convert(markdown: str) -> str:
    """The article as HTML blocks, in the order LinkedIn will receive them."""
    out: list[str] = []
    lines = markdown.splitlines()
    i, paragraph, table, figure = 0, [], [], None

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def flush_table() -> None:
        if not table:
            return
        out.append('<p><strong>Table — LinkedIn has no tables; these are its rows.</strong></p>')
        for row in table:
            cells = [inline(c.strip()) for c in row.strip().strip("|").split("|")]
            cells = [c for c in cells if c and not set(c) <= {"-", ":"}]
            if cells:
                out.append("<p>" + " — ".join(cells) + "</p>")
        table.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("$$"):                      # a display formula, possibly wrapped
            flush_paragraph()
            block = line
            while not block.count("$$") >= 2:
                i += 1
                block += " " + lines[i]
            out.append("<p><strong>" + html.escape(flatten(block.replace("$$", ""))) + "</strong></p>")
        elif line.startswith("!["):                     # an image: a marker, the file, the caption
            flush_paragraph()
            match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            figure = (match.group(1), pathlib.PurePosixPath(match.group(2)).name) if match else None
        elif line.startswith("> "):                     # a caption, which follows its image
            paragraph.append(line[2:])
            if i + 1 >= len(lines) or not lines[i + 1].startswith("> "):
                quoted = inline(" ".join(paragraph))
                paragraph.clear()
                if figure is None:
                    # A block quote that is not a caption: the two questions of 10.2, the rule
                    # of 14. LinkedIn keeps a quote, so it stays one.
                    out.append(f"<blockquote>{quoted}</blockquote>")
                else:
                    out.append(f'<p style="background:#fff3cd;padding:6px">'
                               f'[UPLOAD IMAGE: {html.escape(figure[1])}]</p>')
                    out.append(f"<p><em>{quoted}</em></p>")
                    figure = None
        elif line.startswith("|"):
            flush_paragraph()
            table.append(line)
        elif line.startswith("#"):
            flush_paragraph(); flush_table()
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{min(level, 3)}>{inline(line.lstrip('# ').strip())}</h{min(level, 3)}>")
        elif re.match(r"^\s*(\d+\.|[-*])\s", line):
            flush_paragraph(); flush_table()
            out.append("<p>" + inline(re.sub(r"^\s*(\d+\.|[-*])\s", "• ", line)) + "</p>")
        elif not line.strip():
            flush_paragraph(); flush_table()
        else:
            paragraph.append(line.strip())
        i += 1
    flush_paragraph(); flush_table()
    return "\n".join(out)


def unicode_bold(text: str) -> str:
    """One run of text in the Unicode bold alphabet. Anything outside it is left as it is."""
    return "".join(BOLD.get(character, character) for character in text)


def section(markdown: str, heading: str) -> str:
    """The body under one `## ` heading, to the next heading or horizontal rule."""
    lines = markdown.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading) + 1
    except StopIteration:
        return ""
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## ") or line.strip() == "---":
            break
        body.append(line)
    return "\n".join(body).strip()


def convert_post(markdown: str) -> str:
    """The post text as HTML paragraphs, with `**bold**` spelled in bold characters.

    No `<strong>`: the composer would drop it. The paragraphs are `<p>` only so that copying the
    block keeps the blank line between them, which the composer does preserve.
    """
    out: list[str] = []
    for block in re.split(r"\n\s*\n", section(markdown, "## Post text")):
        block = " ".join(line.strip() for line in block.splitlines() if line.strip())
        if not block:
            continue
        block = re.sub(r"\*\*([^*]+)\*\*", lambda m: unicode_bold(m.group(1)), block)
        out.append("<p>" + html.escape(block) + "</p>")
    return "\n".join(out)


#: What the feed composer allows. It counts UTF-16 code units, so every bold headline character
#: costs two: the Unicode bold block sits outside the basic plane.
POST_LIMIT = 3000


def post_length(markdown: str) -> int:
    """The post as the composer will count it, with the placeholder replaced by the real link."""
    text = re.sub(r"<[^>]+>", "", convert_post(markdown).replace("</p>", "\n\n"))
    text = html.unescape(text).replace("APP_URL", "https://hcwc-builder.streamlit.app").strip()
    return len(text.encode("utf-16-le")) // 2


def write_post(source: pathlib.Path, OUT: pathlib.Path) -> None:
    markdown = source.read_text(encoding="utf-8")
    comment = " ".join(line.strip() for line in section(
        markdown, "## First comment (post immediately after publishing)").splitlines())
    OUT.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>HCWC post, for the LinkedIn composer</title>"
        "<body style='font:16px/1.6 -apple-system,Segoe UI,sans-serif;max-width:40em;margin:2em auto'>"
        "<p style='background:#e7f3ff;padding:10px'><strong>How to use this page.</strong> "
        "Select the boxed post below and copy it, then paste into LinkedIn\u2019s post composer. "
        "The composer keeps no formatting, so the headline is written in Unicode bold characters "
        "and arrives bold. Replace <code>ARTICLE_URL</code> and <code>APP_URL</code>, add the three "
        "images named in <code>LINKEDIN_POST.md</code>, and post the second box as the first "
        "comment. Generated from <code>" + source.name + "</code>; regenerate rather than editing "
        "this file.</p>\n"
        "<div style='border:1px solid #bbb;padding:1em'>\n" + convert_post(markdown) + "\n</div>\n"
        "<p style='background:#e7f3ff;padding:10px'><strong>First comment</strong>, posted "
        "immediately after publishing.</p>\n"
        "<div style='border:1px solid #bbb;padding:1em'><p>" + html.escape(comment) + "</p></div>"
        "</body>",
        encoding="utf-8")
    length = post_length(markdown)
    over = "" if length <= POST_LIMIT else f"  OVER THE LIMIT by {length - POST_LIMIT}"
    print(f"  {OUT.relative_to(ROOT)}  ({length} of {POST_LIMIT} characters){over}")


def main() -> None:
    for source, out in PAGES:
        if source.exists():
            write(source, out)
    if POST[0].exists():
        write_post(*POST)


def write(source: pathlib.Path, OUT: pathlib.Path) -> None:
    body = convert(source.read_text(encoding="utf-8"))
    # A LaTeX command the table above does not know would reach LinkedIn as source. Say so rather
    # than let it through: the article gains expressions over time and this file lags them.
    unknown = sorted(set(re.findall(r"\\[a-zA-Z]+", re.sub(r"<[^>]+>", "", body))))
    if unknown:
        print(f"  unhandled LaTeX in {source.name}, add it to COMMANDS:", ", ".join(unknown))
    OUT.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>HCWC article, for the LinkedIn editor</title>"
        "<body style='font:16px/1.6 -apple-system,Segoe UI,sans-serif;max-width:46em;margin:2em auto'>"
        "<p style='background:#e7f3ff;padding:10px'><strong>How to use this page.</strong> "
        "Select all and copy, then paste into LinkedIn's article editor: headings, bold, italics "
        "and links survive, and every formula is plain text so it arrives once. Where a yellow "
        "line names a file, upload that figure from <code>paper/figures/</code> and put the "
        "italic line under it as the caption. Generated from <code>" + source.name + "</code>; "
        "regenerate rather than editing this file.</p>\n" + body + "</body>",
        encoding="utf-8")
    print(f"  {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
