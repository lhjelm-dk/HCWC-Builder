"""Numbering rules, because the whole point is that a number identifies exactly one thing."""
from __future__ import annotations

import pytest

from hcwc.ui.numbering import Numbering


class TestSharedSequence:
    def test_plots_and_tables_share_one_counter(self):
        """Lars's rule: no `2.3 plot` AND `2.3 table`."""
        n = Numbering(2)
        assert n.ref("Figure") == "Figure 2.1"
        assert n.ref("Table") == "Table 2.2"
        assert n.ref("Figure") == "Figure 2.3"

    def test_numbers_are_never_reused_within_a_tab(self):
        n = Numbering(3)
        seen = [n.ref("Figure" if i % 2 else "Table").split()[-1] for i in range(12)]
        assert len(set(seen)) == 12

    def test_the_tab_number_prefixes_everything(self):
        n = Numbering(4)
        assert all(lab.split()[-1].startswith("4.") for lab in
                   (n.ref("Table"), n.ref("Figure"), n.ref("Table")))

    def test_separate_tabs_are_independent(self):
        a, b = Numbering(2), Numbering(5)
        assert a.ref("Figure") == "Figure 2.1"
        assert b.ref("Figure") == "Figure 5.1"

    def test_a_fresh_instance_restarts(self):
        """One per rerun is correct: the numbers describe the page as it is drawn."""
        assert Numbering(3).ref("Figure") == Numbering(3).ref("Figure") == "Figure 3.1"


class TestThemeMapping:
    def test_tabs_are_numbered_contiguously_from_one(self):
        """Not a fixed count — tabs get inserted, and the CSS indexes off these keys."""
        from hcwc.ui import theme
        assert sorted(theme.TAB_COLOURS) == list(range(1, len(theme.TAB_COLOURS) + 1))

    def test_every_tab_has_a_colour_and_a_name(self):
        from hcwc.ui import theme
        for colour, name in theme.TAB_COLOURS.values():
            assert colour.startswith("#") and len(colour) == 7
            assert name

    def test_colours_are_distinct(self):
        from hcwc.ui import theme
        colours = [c for c, _ in theme.TAB_COLOURS.values()]
        assert len(set(colours)) == len(colours)

    def test_labels_are_numbered_and_ordered(self):
        from hcwc.ui import theme
        labels = theme.tab_labels()
        assert len(labels) == len(theme.TAB_COLOURS)
        circled = "①②③④⑤⑥⑦⑧⑨⑩⑪"
        for i, label in enumerate(labels):
            assert label.startswith(circled[i]), f"tab {i + 1} is not numbered"
            assert theme.TAB_COLOURS[i + 1][1] in label

    def test_there_is_a_numeral_for_every_tab(self):
        """A tab added without a numeral would raise KeyError at import; catch it here instead."""
        from hcwc.ui import theme
        theme.tab_labels()

    def test_accent_matches_the_table(self):
        from hcwc.ui import theme
        assert theme.accent(3) == theme.TAB_COLOURS[3][0]

    def test_unknown_tab_is_an_error_not_a_default(self):
        from hcwc.ui import theme
        with pytest.raises(KeyError):
            theme.accent(len(theme.TAB_COLOURS) + 5)


class TestOptionalNumbering:
    """Three-level numbers for figures that only appear sometimes.

    Lars, 27 Aug 2026, asking for consistent numbering when some figures are conditional. The
    problem is real and not cosmetic: a figure that appears only when the DHI is on, or only when
    an assessment minimum is set, **renumbers everything after it** as it comes and goes. Two
    readers looking at the same tab in different states then disagree about what "Figure 4.6" is,
    which is worse than having no numbers at all.
    """

    def test_an_optional_figure_hangs_off_the_last_ordinary_one(self):
        n = Numbering(3)
        assert n.ref("Figure") == "Figure 3.1"
        assert n.optional("Figure") == "Figure 3.1.1"
        assert n.optional("Figure") == "Figure 3.1.2"

    def test_optional_figures_do_not_advance_the_main_sequence(self):
        """The whole point: what comes after is unmoved by whether the optional one appeared."""
        with_optional = Numbering(3)
        with_optional.ref("Figure")
        with_optional.optional("Figure")
        with_optional.optional("Figure")

        without = Numbering(3)
        without.ref("Figure")

        assert with_optional.ref("Table") == without.ref("Table") == "Table 3.2"

    def test_the_optional_counter_resets_at_each_ordinary_number(self):
        """`4.5.1` means *the first optional after 4.5*, so the suffix has to restart. Without the
        reset the second group would continue 4.6.3, which reads as a gap."""
        n = Numbering(4)
        n.ref("Figure")
        assert n.optional("Figure") == "Figure 4.1.1"
        n.ref("Figure")
        assert n.optional("Figure") == "Figure 4.2.1"

    def test_optional_shares_the_counter_with_tables(self):
        """The one-sequence rule still holds one level down: no `3.1.1` figure *and* `3.1.1` table."""
        n = Numbering(3)
        n.ref("Figure")
        assert n.optional("Figure") == "Figure 3.1.1"
        assert n.optional("Table") == "Table 3.1.2"
