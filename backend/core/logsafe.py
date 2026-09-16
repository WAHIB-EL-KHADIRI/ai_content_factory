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

# Control characters are rendered as an escape rather than dropped, so the
# value stays readable and, more importantly, stays visibly tampered with.
_ESCAPES = {
    "\\": "\\\\",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}

MAX_LENGTH = 256


def scrub(value: object, max_length: int = MAX_LENGTH) -> str:
    """Return `value` as a single-line string that is safe to log.

    Backslash is escaped first, so a value that already contained the two
    characters backslash and 'n' cannot be confused with one that contained a
    real newline.
    """
    text = value if isinstance(value, str) else str(value)

    out = []
    for char in text:
        escape = _ESCAPES.get(char)
        if escape is not None:
            out.append(escape)
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append("\\x{:02x}".format(ord(char)))
        else:
            out.append(char)

    scrubbed = "".join(out)

    # An unbounded value is its own problem: a megabyte of text in one record
    # is a denial of service against whoever has to read the file.
    if len(scrubbed) > max_length:
        scrubbed = scrubbed[:max_length] + "...[truncated]"

    return scrubbed
