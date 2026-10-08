import re

_PATTERN_RE = re.compile(r"^\s*([A-Z])(\d+)-(\d+)\s*$")


class InvalidSeatsPattern(ValueError):
    """Некорректный seats_pattern."""


def parse_seats_pattern(pattern: str | None) -> set[str]:
    if not pattern:
        return set()

    result: set[str] = set()
    for chunk in pattern.split(","):
        if not chunk.strip():
            continue
        match = _PATTERN_RE.match(chunk)
        if not match:
            raise InvalidSeatsPattern(f"bad chunk: {chunk!r}")
        section, start_s, end_s = match.groups()
        start, end = int(start_s), int(end_s)
        if start > end:
            raise InvalidSeatsPattern(f"start > end: {chunk!r}")
        for n in range(start, end + 1):
            result.add(f"{section}{n}")
    return result


def is_valid_seat(pattern: str | None, seat: str) -> bool:
    if not seat:
        return False
    try:
        return seat.upper() in parse_seats_pattern(pattern)
    except InvalidSeatsPattern:
        return False
