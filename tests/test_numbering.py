"""Numbering rules, because the whole point is that a number identifies exactly one thing."""
from __future__ import annotations

import pytest

from hcwc.ui.numbering import Numbering


def _under(n: Numbering, section: str) -> None:
    """Draw a section heading's effect without Streamlit: the section the exhibits sit under."""
    from hcwc.ui import theme
    theme.CURRENT_SECTION[(n.tab, n.sub)] = section


class TestSharedSequence:
    """Exhibits are numbered by the section they sit under, with a letter (Lars, 17 Sep 2026):
    ``Figure 4.1.3a`` is the first exhibit of section 4.1.3, and figures and tables share the
    letters so the reading order survives. One number names one thing."""

    def test_plots_and_tables_share_one_sequence_within_a_section(self):
        """Lars's rule: no `2.3a plot` AND `2.3a table`."""
        n = Numbering(2)
        _under(n, "3")
        assert n.ref("Figure") == "Figure 2.3a"
        assert n.ref("Table") == "Table 2.3b"
        assert n.ref("Figure") == "Figure 2.3c"

    def test_the_letters_restart_at_each_section(self):
        n = Numbering(4)
        _under(n, "1")
        assert n.ref("Figure") == "Figure 4.1a"
        _under(n, "2")
        assert n.ref("Figure") == "Figure 4.2a"
        assert n.ref("Table") == "Table 4.2b"

    def test_numbers_are_never_reused_within_a_tab(self):
        n = Numbering(3)
        _under(n, "1")
        seen = [n.ref("Figure" if i % 2 else "Table").split()[-1] for i in range(12)]
        assert len(set(seen)) == 12

    def test_the_tab_number_prefixes_everything(self):
        n = Numbering(4)
        _under(n, "2")
        assert all(lab.split()[-1].startswith("4.2") for lab in
                   (n.ref("Table"), n.ref("Figure"), n.ref("Table")))

    def test_a_sub_tab_carries_its_page(self):
        n = Numbering(5, sub=2)
        _under(n, "3")
        assert n.ref("Figure") == "Figure 5.2.3a"

    def test_separate_tabs_are_independent(self):
        a, b = Numbering(2), Numbering(5)
        _under(a, "1"); _under(b, "1")
        assert a.ref("Figure") == "Figure 2.1a"
        assert b.ref("Figure") == "Figure 5.1a"

    def test_a_fresh_instance_restarts(self):
        """One per rerun is correct: the numbers describe the page as it is drawn."""
        a = Numbering(3); _under(a, "1"); first = a.ref("Figure")
        b = Numbering(3); _under(b, "1")
        assert first == b.ref("Figure") == "Figure 3.1a"

    def test_before_any_heading_the_section_is_zero(self):
        """An exhibit above the first heading is numbered under section 0, visibly, rather than
        stealing section 1's letters."""
        n = Numbering(6)
        assert n.ref("Table") == "Table 6.0a"

    def test_upcoming_peeks_without_taking(self):
        n = Numbering(4, sub=1)
        _under(n, "2")
        n.ref("Figure")
        assert n.upcoming("Table", 1) == "Table 4.1.2b"
        assert n.upcoming("Figure", 2) == "Figure 4.1.2c"
        assert n.ref("Table") == "Table 4.1.2b"

    def test_the_report_orders_letters_and_optionals(self):
        from hcwc.ui.numbering import figure_order
        labels = ["Figure 4.1.10a", "Figure 4.1.9a", "Table 4.1.3b", "Figure 4.1.3a",
                  "Figure 4.1.3b.1", "Figure 4.1.3c"]
        assert sorted(labels, key=figure_order) == [
            "Figure 4.1.3a", "Table 4.1.3b", "Figure 4.1.3b.1", "Figure 4.1.3c",
            "Figure 4.1.9a", "Figure 4.1.10a"]


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
        for i, label in enumerate(labels):
            assert label.startswith(f"{i + 1}.0"), f"tab {i + 1} is not numbered"
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
    """Optional exhibits hang off the last ordinary one, so nothing downstream moves.

    Lars, 27 Aug 2026, asking for consistent numbering when some figures are conditional. The
    problem is real and not cosmetic: a figure that appears only when the DHI is on, or only when
    an assessment minimum is set, **renumbers everything after it** as it comes and goes. Two
    readers looking at the same tab in different states then disagree about what "Figure 4.6" is,
    which is worse than having no numbers at all.
    """

    def test_an_optional_figure_hangs_off_the_last_ordinary_one(self):
        n = Numbering(3)
        _under(n, "1")
        assert n.ref("Figure") == "Figure 3.1a"
        assert n.optional("Figure") == "Figure 3.1a.1"
        assert n.optional("Figure") == "Figure 3.1a.2"

    def test_optional_figures_do_not_advance_the_main_sequence(self):
        """The whole point: what comes after is unmoved by whether the optional one appeared."""
        with_optional = Numbering(3)
        _under(with_optional, "1")
        with_optional.ref("Figure")
        with_optional.optional("Figure")
        with_optional.optional("Figure")

        without = Numbering(3)
        _under(without, "1")
        without.ref("Figure")

        assert with_optional.ref("Table") == without.ref("Table") == "Table 3.1b"

    def test_the_optional_counter_resets_at_each_ordinary_number(self):
        n = Numbering(4)
        _under(n, "5")
        n.ref("Figure")
        assert n.optional("Figure") == "Figure 4.5a.1"
        n.ref("Figure")
        assert n.optional("Figure") == "Figure 4.5b.1"

    def test_optional_shares_the_counter_with_tables(self):
        n = Numbering(3)
        _under(n, "1")
        n.ref("Figure")
        assert n.optional("Figure") == "Figure 3.1a.1"
        assert n.optional("Table") == "Table 3.1a.2"


class TestNoCircledNumeralsSurvive:
    """The tab numbering moved from ① to `1.0` on 3 Sep 2026. Two of them were written as `\u2463`
    escapes rather than as the character, so a scan for the glyph could not see them and they
    rendered as circled numerals on a page where everything else had changed."""

    @staticmethod
    def _sources():
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        return [root / "app.py"] + sorted((root / "hcwc").rglob("*.py"))

    def test_no_source_file_carries_one(self):
        import re

        # Two kinds, because the second is what got missed: a numeral written as a backslash-u
        # escape is not the character, so a scan for the character walks straight past it.
        glyph = "[\u2460-\u2473]"
        escaped = "\\\\u24(?:6[0-9A-Fa-f]|7[0-3])"
        pattern = re.compile(f"{glyph}|{escaped}")
        offenders = []
        for path in self._sources():
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                # No exemptions any more. Tab 3.0's sub-tabs were the last holdout and went to
                # letters on 3 Sep 2026, so the scan can be absolute rather than carrying a
                # `"Charge" not in line` escape hatch that would hide the next one.
                if pattern.search(line):
                    offenders.append(f"{path.name}:{i}")
        assert not offenders, f"circled numerals left in: {offenders}"

    def test_tab_threes_sub_tabs_are_lettered(self):
        """The one place the `N.0` scheme could not reach. Numbering them 3.1-3.4 would collide with
        `Figure 3.1` and `Table 3.2`, which is exactly the ambiguity the scheme exists to avoid, so
        Lars settled it on 3 Sep 2026 with letters — outside the number sequence altogether."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        text = (root / "hcwc" / "ui" / "limiters_tab.py").read_text(encoding="utf-8")
        assert ('["A · Charge", "B · Closure", "C · Retention", "D · Reservoir", '
                '"E · Correlations"]') in text

    def test_the_figures_on_tab_three_ignore_the_letters(self):
        """The sub-tab letters are not sections: an exhibit is numbered by the numbered section
        it sits under wherever the sub-tab is, which is what makes a reference findable."""
        n = Numbering(3)
        _under(n, "2")
        assert [n.ref("Figure") for _ in range(4)] == [
            "Figure 3.2a", "Figure 3.2b", "Figure 3.2c", "Figure 3.2d"]
