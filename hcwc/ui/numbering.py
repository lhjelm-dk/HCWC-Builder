"""Figure and table numbers: ``2.1``, ``2.2``, ``3.1`` — one sequence per tab, or per sub-tab.

Lars, 25 Aug 2026: *"plot 2.2 is the second plot in tab 2, and table 4.3 is the 3rd table in tab 4.
It's either a plot or a table so no 2.3 plot **and** 2.3 table!"*

That last clause decides the design. If plots and tables each had their own counter, "Figure 2.3"
and "Table 2.3" would both exist and a reader told to "look at 2.3" would have to ask which. So
**one counter per tab, shared between plots and tables**, and the word in front says which kind it
is. A consequence worth being explicit about: the second *plot* on a tab is not necessarily 2.2 —
it is 2.2 only if no table came between. The number locates the item on the page, which is what it
is for.

Numbers are assigned **in render order**, not from a hand-maintained table. WellVolPOS keeps a dict
of key → number (`wellvolpos/ui/numbering.py`) and it works there because figures are stable and
each has an identity that outlives its position. Here the mix of plots and tables would make such a
dict wrong every time anything was inserted, silently, and the whole value of the numbers is that
they match what the reader is scrolling past.

Streamlit re-runs a script top to bottom on every interaction, so render order is deterministic and
a plain counter is sufficient. Each tab makes its own::

    n = Numbering(3)
    n.plot(fig, "Column height against closure height")
    n.table(df, "Elasticities, published and corrected")
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

import streamlit as st

Kind = Literal["Figure", "Table"]

# Captions carry the GEOLOGICAL / GIVEN THE DHI chip from `theme.basis_tag`, which is a styled
# span. `st.caption` escapes HTML unless told not to, so without this the chip printed as its own
# source -- a caption reading `<span style='background:rgba(76,114,176...` where the label should
# be, which is worse than no label at all.


#: Passed as ``basis`` to mean *use the sequence's own*, so that ``None`` can still mean
#: *no basis on this one* -- which is a real answer for a figure that is neither, like the
#: detection function, and has to be distinguishable from "not specified".
INHERIT = "__inherit__"


def render_caption(label: str, caption: str, basis: str | None = None) -> None:
    """One numbered caption, whole.

    There was briefly a Full/Brief control that folded everything after the first paragraph behind
    a "why". Lars removed it (28 Aug 2026): a caption that can be half-read is a caption whose
    second half nobody reads, and the second half is where the caveats are. If the captions are too
    long the answer is to write shorter ones, not to hide the end of them.

    The function stays as the single place a label and a caption are joined, which is worth having
    even with nothing to decide inside it.
    """
    from hcwc.ui import theme

    chip = f"{theme.basis_tag(basis)} &nbsp; " if basis else ""
    st.caption(f"**{label}** \u2014 {chip}{caption}", unsafe_allow_html=True)


#: Where every figure drawn this run is kept as ``{label: (figure, caption)}``, so the Export tab
#: can build a document without each tab having to hand its figures anywhere. Cleared at the top of
#: each run by `Numbering.__post_init__` on the first instance created -- Streamlit reruns top to
#: bottom, so "the first Numbering of the run" is a reliable moment to reset.
#:
#: **The caption travels with the figure.** A figure without one is a picture; the captions here
#: are where the finding is stated and where the caveat lives.
FIGURES_KEY = "_figures"

#: The same, for tables: ``{label: (payload, caption)}`` where the payload is a dataframe or the
#: markdown of a hand-written table.
#:
#: **The report shipped every figure and no table.** Thirty-three figures and twenty-odd tables are
#: drawn on a run, and only the figures reached the document -- so the limits as entered, the group
#: minima, the allocation comparison and the whole benchmark section were absent from "the full
#: report". Lars, 4 Sep 2026: *"I want the tables."* They were never registered anywhere, which is
#: why nothing noticed.
TABLES_KEY = "_tables"


def theme_tag(basis: str) -> str:
    """The basis chip, imported late so ``hcwc.ui.theme`` and this module stay independent."""
    from hcwc.ui import theme

    return theme.basis_tag(basis)


def _letter(k: int) -> str:
    """``1 -> a`` … ``26 -> z``, then ``aa``, ``ab``: the exhibit's place inside its section."""
    out = ""
    while k > 0:
        k, rem = divmod(k - 1, 26)
        out = chr(97 + rem) + out
    return out


def figure_order(label: str) -> tuple:
    """Sort key for an exhibit label, so ``4.1.10a`` follows ``4.1.9a`` and ``4.1.3b`` follows
    ``4.1.3a``, with an optional ``4.1.3b.1`` between ``4.1.3b`` and ``4.1.3c``.

    Lexical order would put `4.10` between `4.1` and `4.2`, which reads as a mis-numbered document
    rather than as a sorting artefact.
    """
    digits = label.replace("Figure", "").replace("Table", "").strip()
    key: list = []
    for part in digits.split("."):
        m = re.match(r"^(\d+)([a-z]*)$", part)
        if m:
            key.append(int(m.group(1)))
            key.append(m.group(2))
        else:
            key.append(0)
            key.append(part)
    return tuple(key)


def _plotly_config(label: str) -> dict:
    """Modebar options, so the camera button saves something worth keeping.

    Named by the figure's own number and rendered at 3x, because the default is `newplot.png` at
    whatever the browser window happens to be -- fine for a glance, useless in a document.
    """
    return {"toImageButtonOptions": {"format": "png", "scale": 3,
                                     "filename": label.replace(" ", "_").replace(".", "-")},
            "displaylogo": False}


@dataclass
class Numbering:
    """One numbering sequence, for one tab.

    Create it at the top of the tab body. It is deliberately not cached and not stored in session
    state: a fresh one per rerun is exactly right, because the numbers describe the page as it is
    being drawn.
    """
    tab: int
    #: Which sub-tab this sequence belongs to, when the tab has them. With it, labels carry three
    #: parts -- ``Figure 5.2.1`` is the first exhibit on tab 5.0's second sub-tab -- so a number
    #: locates the page as well as the position on it. Tab 5.0 needs this and tab 4.0 will when its
    #: two sub-tabs grow; a tab that passes nothing keeps two-part numbers and is untouched.
    sub: int | None = None
    #: Which contact distribution everything in this sequence is drawn from, or ``None`` where the
    #: question does not apply.
    #:
    #: **The caption is where this belongs, not only the banner at the top of the tab.** The banner
    #: was the original fix, and its own docstring says why -- *"a reader who has scrolled to Figure
    #: 7.2 will not scroll back to check"*. But a caption travels and a banner does not: the export
    #: on tab 7.0 ships every figure with its caption and no banner, and so does the camera button
    #: on any chart. Nineteen exhibits on tabs 4.0 and 5.0 carried **byte-identical captions** across
    #: the two tabs -- `Figure 4.1.1` and `Figure 5.3.1` were the same words over two different
    #: distributions -- and nothing on either said which. Lars, 4 Sep 2026, asking exactly that.
    #:
    #: Set on the sequence rather than passed at each call because the failure mode is *forgetting*,
    #: and the three exhibits that had a chip were the three somebody had remembered.
    basis: str | None = None
    _count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        # The figure store is per *run*, not per session: a figure drawn on the previous run may
        # no longer exist, and exporting a stale one would be worse than exporting none. Tab 1.0 has
        # no Numbering, so the first one created is tab 2.0's and that is early enough.
        if self.tab <= 2:
            st.session_state[FIGURES_KEY] = {}
            st.session_state[TABLES_KEY] = {}
        from hcwc.ui import theme

        theme.CURRENT_SECTION.pop((self.tab, self.sub), None)

    _optional: int = field(default=0, init=False)
    #: The section the last exhibit was numbered under, and how many exhibits it has had.
    _section: str = field(default="", init=False)

    @property
    def stem(self) -> str:
        """``5`` without sub-tabs, ``5.2`` with them — the part every label on this page shares."""
        return f"{self.tab}" if self.sub is None else f"{self.tab}.{self.sub}"

    def _current_section(self) -> str:
        from hcwc.ui import theme

        return theme.CURRENT_SECTION.get((self.tab, self.sub), "0")

    def _label(self, kind: Kind) -> str:
        """``Figure 4.1.3a``: the section the exhibit sits under, then its place inside it.

        **Exhibits are numbered by section, with a letter** (Lars, 17 Sep 2026). Until then
        exhibits ran in their own sequence beside the sections' -- section 4.1.3 held Figure
        4.1.7 and "Figure 4.1.3" was somewhere else -- so one number named two things. Now
        ``4.1.3`` names the section, ``4.1.3a`` its first exhibit, and figures and tables share
        the letters so the order they are read in survives. The section is whatever
        :func:`hcwc.ui.theme.heading` last drew on this tab and sub-tab.
        """
        section = self._current_section()
        if section != self._section:
            self._section, self._count = section, 0
        self._count += 1
        self._optional = 0
        return f"{kind} {self.stem}.{section}{_letter(self._count)}"

    def optional(self, kind: Kind) -> str:
        """A number for an exhibit that only appears sometimes: ``4.1.3b.1``, ``4.1.3b.2``, …

        Lars, 27 Aug 2026, on wanting consistent numbering when some figures are conditional. The
        problem is real: a figure that appears only when the DHI is on, or only when a calculator
        is opened, **renumbers everything after it** when it comes and goes. Two readers looking at
        the same tab in different states then disagree about what "Figure 4.6" is, which is worse
        than having no numbers.

        An optional exhibit hangs off the last ordinary one, the exhibit it elaborates, so
        ``4.1.3b.1`` is *the first optional exhibit after 4.1.3b* and nothing downstream moves
        when it disappears. The letters only ever count exhibits that are always there.
        """
        self._optional += 1
        return f"{kind} {self.stem}.{self._section or self._current_section()}" \
               f"{_letter(self._count)}.{self._optional}"

    def upcoming(self, kind: Kind, ahead: int = 1) -> str:
        """The label ``ahead`` ordinary exhibits from now, without taking it.

        For a fold's label that names the exhibits inside it, so the reader knows which numbers
        the fold holds before opening it.
        """
        section = self._current_section()
        count = self._count if section == self._section else 0
        return f"{kind} {self.stem}.{section}{_letter(count + ahead)}"

    def ref(self, kind: Kind) -> str:
        """Take the next number without rendering anything.

        For prose that refers forward — "see Figure 3.4 below" — where the caption is written by
        hand rather than by :meth:`plot`. Use sparingly; a reference that drifts out of step with
        the thing it names is worse than no number.
        """
        return self._label(kind)

    def plot(self, fig, caption: str, *, width: str = "stretch",
             optional: bool = False, basis: str | None = INHERIT) -> str:
        """Render a Plotly figure with a numbered caption beneath it. Returns the label.

        **The label is also the widget key.** Streamlit derives an element's identity from its type
        and parameters, so two tabs drawing structurally identical figures collide with
        ``StreamlitDuplicateElementId``. That is not hypothetical: tabs 4.0 and 5.0 are the same
        function rendered twice, and the consistency-test figure is identical in both until the
        user changes something. ``Figure 5.3`` and ``Figure 7.3`` are unique by construction, which
        makes the number we already compute the right key.
        """
        label = self.optional("Figure") if optional else self._label("Figure")
        st.plotly_chart(fig, width=width, key=label,
                        config=_plotly_config(label))
        # Kept so the Export tab can render every figure without each tab publishing its own.
        basis = self.basis if basis == INHERIT else basis
        # Stored with the chip already in it, because this dict *is* what the report renders and a
        # figure exported without its basis is the whole problem this solves.
        stored = caption if not basis else f"{theme_tag(basis)} &nbsp; {caption}"
        st.session_state.setdefault(FIGURES_KEY, {})[label] = (fig, stored)
        render_caption(label, caption, basis)
        return label

    def table(self, data, caption: str, *, hide_index: bool = True,
              optional: bool = False, basis: str | None = INHERIT, **kwargs) -> str:
        """Render a dataframe with a numbered caption beneath it. Returns the label.

        Keyed by its label for the same reason as :meth:`plot`.
        """
        label = self.optional("Table") if optional else self._label("Table")
        st.dataframe(data, hide_index=hide_index, width="stretch", key=label, **kwargs)
        basis = self.basis if basis == INHERIT else basis
        stored = caption if not basis else f"{theme_tag(basis)} &nbsp; {caption}"
        st.session_state.setdefault(TABLES_KEY, {})[label] = (data, stored, hide_index)
        render_caption(label, caption, basis)
        return label

    def image(self, path, caption: str, *, basis: str | None = INHERIT) -> str:
        """Render an image file with a numbered caption beneath it. Returns the label.

        For a figure that is drawn outside Plotly, such as the workflow diagram of 8.1.1, an
        SVG laid out by ``scripts/workflow_figure.py``. Registered like any figure, with the
        path as the payload, so the report carries it in number order.
        """
        label = self._label("Figure")
        st.image(str(path), width="stretch")
        basis = self.basis if basis == INHERIT else basis
        stored = caption if not basis else f"{theme_tag(basis)} &nbsp; {caption}"
        st.session_state.setdefault(FIGURES_KEY, {})[label] = (path, stored)
        render_caption(label, caption, basis)
        return label

    def markdown_table(self, body: str, caption: str) -> str:
        """Number a table written as markdown, for the cases where prose formatting wins.

        A markdown table can carry bold, footnote markers and inline code that ``st.dataframe``
        cannot, and some of these tables are argument rather than data.
        """
        label = self._label("Table")
        st.markdown(body)
        stored = caption if not self.basis else f"{theme_tag(self.basis)} &nbsp; {caption}"
        st.session_state.setdefault(TABLES_KEY, {})[label] = (body, stored, True)
        render_caption(label, caption, self.basis)
        return label
