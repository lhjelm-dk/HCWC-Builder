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

from dataclasses import dataclass, field
from typing import Literal

import streamlit as st

Kind = Literal["Figure", "Table"]

# Captions carry the GEOLOGICAL / GIVEN THE DHI chip from `theme.basis_tag`, which is a styled
# span. `st.caption` escapes HTML unless told not to, so without this the chip printed as its own
# source -- a caption reading `<span style='background:rgba(76,114,176...` where the label should
# be, which is worse than no label at all.


def render_caption(label: str, caption: str) -> None:
    """One numbered caption, whole.

    There was briefly a Full/Brief control that folded everything after the first paragraph behind
    a "why". Lars removed it (28 Aug 2026): a caption that can be half-read is a caption whose
    second half nobody reads, and the second half is where the caveats are. If the captions are too
    long the answer is to write shorter ones, not to hide the end of them.

    The function stays as the single place a label and a caption are joined, which is worth having
    even with nothing to decide inside it.
    """
    st.caption(f"**{label}** \u2014 {caption}", unsafe_allow_html=True)


#: Where every figure drawn this run is kept as ``{label: (figure, caption)}``, so the Export tab
#: can build a document without each tab having to hand its figures anywhere. Cleared at the top of
#: each run by `Numbering.__post_init__` on the first instance created -- Streamlit reruns top to
#: bottom, so "the first Numbering of the run" is a reliable moment to reset.
#:
#: **The caption travels with the figure.** A figure without one is a picture; the captions here
#: are where the finding is stated and where the caveat lives.
FIGURES_KEY = "_figures"


def figure_order(label: str) -> tuple:
    """Sort key for a figure label, so ``4.10`` follows ``4.9`` rather than ``4.1``.

    Lexical order would put `Figure 4.10` between `Figure 4.1` and `Figure 4.2`, which reads as a
    mis-numbered document rather than as a sorting artefact.
    """
    digits = label.replace("Figure", "").replace("Table", "").strip()
    return tuple(int(part) if part.isdigit() else 0 for part in digits.split("."))


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
    _count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        # The figure store is per *run*, not per session: a figure drawn on the previous run may
        # no longer exist, and exporting a stale one would be worse than exporting none. Tab 1.0 has
        # no Numbering, so the first one created is tab 2.0's and that is early enough.
        if self.tab <= 2:
            st.session_state[FIGURES_KEY] = {}

    _optional: int = field(default=0, init=False)

    @property
    def stem(self) -> str:
        """``5`` without sub-tabs, ``5.2`` with them — the part every label on this page shares."""
        return f"{self.tab}" if self.sub is None else f"{self.tab}.{self.sub}"

    def _label(self, kind: Kind) -> str:
        self._count += 1
        self._optional = 0
        return f"{kind} {self.stem}.{self._count}"

    def optional(self, kind: Kind) -> str:
        """A number for a figure that only appears sometimes: ``4.5.1``, ``4.5.2``, …

        Lars, 27 Aug 2026, on wanting consistent numbering when some figures are conditional. The
        problem is real: a figure that appears only when the DHI is on, or only when a calculator
        is opened, **renumbers everything after it** when it comes and goes. Two readers looking at
        the same tab in different states then disagree about what "Figure 4.6" is, which is worse
        than having no numbers.

        A third level fixes it. An optional figure hangs off the last ordinary one — the figure it
        elaborates — so ``4.5.1`` is *the first optional figure after 4.5* and nothing downstream
        moves when it disappears. The main sequence only ever counts figures that are always there.
        """
        self._optional += 1
        return f"{kind} {self.stem}.{self._count}.{self._optional}"

    def ref(self, kind: Kind) -> str:
        """Take the next number without rendering anything.

        For prose that refers forward — "see Figure 3.4 below" — where the caption is written by
        hand rather than by :meth:`plot`. Use sparingly; a reference that drifts out of step with
        the thing it names is worse than no number.
        """
        return self._label(kind)

    def plot(self, fig, caption: str, *, use_container_width: bool = True,
             optional: bool = False) -> str:
        """Render a Plotly figure with a numbered caption beneath it. Returns the label.

        **The label is also the widget key.** Streamlit derives an element's identity from its type
        and parameters, so two tabs drawing structurally identical figures collide with
        ``StreamlitDuplicateElementId``. That is not hypothetical: tabs 4.0 and 5.0 are the same
        function rendered twice, and the consistency-test figure is identical in both until the
        user changes something. ``Figure 5.3`` and ``Figure 7.3`` are unique by construction, which
        makes the number we already compute the right key.
        """
        label = self.optional("Figure") if optional else self._label("Figure")
        st.plotly_chart(fig, use_container_width=use_container_width, key=label,
                        config=_plotly_config(label))
        # Kept so the Export tab can render every figure without each tab publishing its own.
        st.session_state.setdefault(FIGURES_KEY, {})[label] = (fig, caption)
        render_caption(label, caption)
        return label

    def table(self, data, caption: str, *, hide_index: bool = True,
              optional: bool = False, **kwargs) -> str:
        """Render a dataframe with a numbered caption beneath it. Returns the label.

        Keyed by its label for the same reason as :meth:`plot`.
        """
        label = self.optional("Table") if optional else self._label("Table")
        st.dataframe(data, hide_index=hide_index, use_container_width=True, key=label, **kwargs)
        render_caption(label, caption)
        return label

    def markdown_table(self, body: str, caption: str) -> str:
        """Number a table written as markdown, for the cases where prose formatting wins.

        A markdown table can carry bold, footnote markers and inline code that ``st.dataframe``
        cannot, and some of these tables are argument rather than data.
        """
        label = self._label("Table")
        st.markdown(body)
        render_caption(label, caption)
        return label
