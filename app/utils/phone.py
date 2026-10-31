"""Bangladesh phone normalization.

Ported verbatim in behaviour from System A (`app/utils/phone.py`) so that the
Kotlin payment bridge (`BangladeshPhone.kt`) and the backend agree byte for
byte: both normalize `01700000017`, `+8801700000017` and `8801700000017`
to `8801700000017`.
"""

from __future__ import annotations

import re

BD_MOBILE_LOCAL = re.compile(r"^0\d{10}$")
BD_MOBILE_INTERNATIONAL = re.compile(r"^880\d{10}$")


def normalize_phone(phone: str | None) -> str | None:
    """Canonical `8801XXXXXXXXX`, or None when not a Bangladesh mobile.

    Returns None for empty/None input. Raises ValueError when the value is
    present but not a valid BD mobile number, matching System A's contract
    so the device bridge can return 422 for malformed identifiers.
    """
    if phone is None:
        return None
    cleaned = re.sub(r"[^0-9+]", "", phone.strip())
    if not cleaned:
        return None
    if cleaned.startswith("+88"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("880"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("0"):
        pass
    else:
        cleaned = "0" + cleaned
    if not re.fullmatch(r"^0\d{10}$", cleaned):
        raise ValueError("Phone number must be a valid Bangladesh mobile number")
    return "880" + cleaned[1:]


def normalize_phone_or_none(phone: str | None) -> str | None:
    """Like `normalize_phone` but returns None instead of raising."""
    try:
        return normalize_phone(phone)
    except ValueError:
        return None


def digits_only(value: str | None) -> str | None:
    """Digit-only normalization used for loose receiving-number comparisons."""
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits or None


def phones_equivalent(left: str | None, right: str | None) -> bool:
    """True when two phone strings refer to the same number.

    Compares canonical forms when both parse; otherwise compares the last
    10 digits, which absorbs +880/880/0 prefixes and separators.
    """
    left_canonical = normalize_phone_or_none(left)
    right_canonical = normalize_phone_or_none(right)
    if left_canonical and right_canonical:
        return left_canonical == right_canonical

    left_digits = digits_only(left)
    right_digits = digits_only(right)
    if not left_digits or not right_digits:
        return False
    return left_digits[-10:] == right_digits[-10:]
