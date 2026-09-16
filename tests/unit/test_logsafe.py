"""Tests for the log-line sanitiser.

The threat is not a crash. It is a value that carries a newline into a log
file and becomes a second record, which whoever reads the file -- a person, a
`grep`, or a shipper turning each line into an event -- cannot distinguish
from one the application wrote.
"""

from backend.core.logsafe import MAX_LENGTH, scrub

NL = chr(10)
CR = chr(13)
TAB = chr(9)
NUL = chr(0)
ESC = chr(27)
BACKSLASH = chr(92)


class TestForgedRecords:
    def test_a_newline_cannot_start_a_second_line(self):
        forged = "mychannel" + NL + "INFO  user admin logged in"

        result = scrub(forged)

        assert NL not in result
        assert result == "mychannel" + BACKSLASH + "nINFO  user admin logged in"

    def test_a_carriage_return_cannot_either(self):
        assert CR not in scrub("chan" + CR + "INFO forged")

    def test_a_tab_cannot_forge_a_column(self):
        """Relevant wherever logs are read as TSV."""
        assert TAB not in scrub("chan" + TAB + "extra-column")

    def test_an_escaped_value_is_distinguishable_from_a_real_newline(self):
        """The reason backslash is escaped first.

        Without it, an attacker writes the two characters `\\` and `n` and the
        log shows exactly what a real newline would have shown.
        """
        literal = scrub("chan" + BACKSLASH + "nINFO forged")
        real = scrub("chan" + NL + "INFO forged")

        assert literal != real


class TestControlCharacters:
    def test_a_nul_byte_is_escaped(self):
        assert scrub("a" + NUL + "b") == "a" + BACKSLASH + "x00b"

    def test_an_ansi_escape_cannot_colour_the_terminal(self):
        """A log read in a terminal is a rendering surface too."""
        result = scrub("chan" + ESC + "[31mRED")

        assert ESC not in result
        assert BACKSLASH + "x1b" in result

    def test_delete_is_escaped(self):
        assert chr(127) not in scrub("a" + chr(127) + "b")


class TestOrdinaryValues:
    def test_a_normal_value_is_returned_unchanged(self):
        assert scrub("content-updates") == "content-updates"

    def test_unicode_survives(self):
        """Scrubbing is about control characters, not about ASCII."""
        assert scrub("قناة-عربية") == "قناة-عربية"

    def test_a_non_string_is_coerced(self):
        assert scrub(None) == "None"
        assert scrub(42) == "42"


class TestLength:
    def test_an_unbounded_value_is_truncated(self):
        result = scrub("x" * 5000)

        assert result.endswith("...[truncated]")
        assert len(result) == MAX_LENGTH + len("...[truncated]")

    def test_a_value_at_the_limit_is_left_alone(self):
        assert scrub("x" * MAX_LENGTH) == "x" * MAX_LENGTH

    def test_truncation_counts_escaped_length_not_input_length(self):
        """A value of newlines doubles in length when escaped; the cap applies
        to what actually reaches the file."""
        result = scrub(NL * 5000)

        assert len(result) == MAX_LENGTH + len("...[truncated]")
