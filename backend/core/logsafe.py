"""Make untrusted values safe to put in a log line.

A log file is parsed -- by a human reading it, by `grep`, and increasingly by a
shipper that turns each line into a structured event. A value that reaches it
carrying a newline stops being a value and becomes a second line, which the
reader has no way to tell from one the application actually wrote. That is the
whole of log injection: not a crash, a forged record.

Nothing here escapes for HTML or for a shell. It is only about keeping one
logical record on one line.
"""

from __future__ import annotations

import re

# Any remaining C0 control character, plus DEL. The four handled by the
# explicit replaces below are excluded so this pass cannot double-escape them.
_REMAINING_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MAX_LENGTH = 256


def scrub(value: object, max_length: int = MAX_LENGTH) -> str:
    """Return `value` as a single-line string that is safe to log."""
    text = value if isinstance(value, str) else str(value)

    # Written as an explicit replace chain rather than a character loop
    # because this is the shape CodeQL's py/log-injection model recognises as
    # a barrier. A loop that does the same thing is invisible to it, which
    # leaves five permanently-open alerts and no way to see a sixth.
    #
    # Backslash goes first. Otherwise a value that already contained the two
    # characters backslash and 'n' would come out identical to one that
    # contained a real newline, and the distinction this function exists to
    # preserve would be gone.
    scrubbed = (
        text.replace("\\", "\\\\")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )

    # Escaped rather than stripped, so the value stays readable and, more
    # importantly, stays visibly tampered with. ANSI escapes go with them: a
    # log read in a terminal is a rendering surface too.
    scrubbed = _REMAINING_CONTROLS.sub(
        lambda match: "\\x{:02x}".format(ord(match.group())), scrubbed
    )

    # An unbounded value is its own problem: a megabyte of text in one record
    # is a denial of service against whoever has to read the file.
    if len(scrubbed) > max_length:
        scrubbed = scrubbed[:max_length] + "...[truncated]"

    return scrubbed
