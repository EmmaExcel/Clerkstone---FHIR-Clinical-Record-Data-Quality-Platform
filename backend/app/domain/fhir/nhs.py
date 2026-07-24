"""NHS Number: modulus-11 check digit and reserved test ranges.

The NHS Number is 10 digits; the last is a modulus-11 check digit. Digits are
weighted 10..2, summed, and the check digit is ``11 - (sum mod 11)`` (where a
result of 11 maps to 0 and a result of 10 means the number is invalid).
"""

from __future__ import annotations

_WEIGHTS = (10, 9, 8, 7, 6, 5, 4, 3, 2)


def check_digit(first9: str) -> str | None:
    """Return the check digit for a 9-digit prefix, or None if the prefix is
    malformed or would yield an unusable check digit of 10."""
    if len(first9) != 9 or not first9.isdigit():
        return None
    total = sum(int(d) * w for d, w in zip(first9, _WEIGHTS, strict=True))
    remainder = total % 11
    check = 11 - remainder
    if check == 11:
        check = 0
    if check == 10:
        return None
    return str(check)


def is_valid(number: str) -> bool:
    """True iff ``number`` is a well-formed NHS Number with a correct check digit."""
    if not isinstance(number, str) or len(number) != 10 or not number.isdigit():
        return False
    return check_digit(number[:9]) == number[9]


def is_reserved_test_range(number: str) -> bool:
    """True iff the number falls in the 99-prefix range reserved for synthetic data."""
    return number.startswith("99")


def make_valid_nhs_number(prefix9: str) -> str:
    """Build a full 10-digit NHS number from a 9-digit prefix."""
    cd = check_digit(prefix9)
    if cd is None:
        raise ValueError(f"prefix {prefix9!r} cannot produce a valid check digit")
    return prefix9 + cd
