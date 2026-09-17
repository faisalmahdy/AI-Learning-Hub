"""'String length' is not one number: Python counts code points, JavaScript and Java count UTF-16 code units, and a code point above U+10000 is one code point but two code units -- so the same string has different lengths in different languages, and indexing or truncating by UTF-16 units can split a character in half.

A Unicode code point is a character's number. UTF-16 stores each code point as either one 16-bit code unit (for the Basic Multilingual Plane, below U+10000) or a surrogate pair of two code units (for the astral planes at or above U+10000 -- most emoji, some CJK, historic scripts). Python strings are sequences of code points, so len() counts code points. JavaScript's .length and Java's .length() count UTF-16 code units.

So 'the length of the string' depends on the language. A string of h, i, an emoji, and x is four code points and five UTF-16 code units, because the emoji is one code point encoded as two units. A test that expects length 4 passes in Python and fails in JavaScript on the very same text, and a database column sized in one unit truncates differently than a validator that counted in the other.

The count mismatch is annoying; the splitting is a bug. Indexing or slicing by UTF-16 units can land between the two halves of a surrogate pair, leaving a lone high surrogate -- half of a character, which is not a valid character at all. Truncating this string to three UTF-16 units keeps h and i and then the high surrogate of the emoji, a broken fragment. Truncating by code points can never do this, because a code point is atomic.

On this fixture the string is h, i, the emoji U+1F600, and x. Its code-point length is 4 and its UTF-16 length is 5. A limit of 4 admits it by code points but rejects it by UTF-16 units. Truncating to 3 UTF-16 units splits the emoji; truncating to 3 code points does not. This computes all of it.

  --measure   the code-point length and the UTF-16 code-unit length, and how a limit judges the string under each
  --truncate  truncating by UTF-16 units (splits the emoji into a lone surrogate) versus by code points (safe)
  --check     the two lengths differ because the astral character is two UTF-16 units, a unit-based limit disagrees with a code-point limit, and unit truncation splits a character while code-point truncation does not

the string's code points are the fixture; both lengths and both truncations are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "codeunit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def code_point_len(cps):
    """Length in code points -- what Python's len() returns."""
    return len(cps)


def utf16_len(cps):
    """Length in UTF-16 code units -- what JavaScript's .length and Java's .length() return."""
    return sum(2 if cp >= 0x10000 else 1 for cp in cps)


def unit_list(cps):
    """The UTF-16 code units: an astral code point becomes a high ('H') then low ('L') surrogate."""
    units = []
    for cp in cps:
        if cp >= 0x10000:
            units.append(("H", cp))
            units.append(("L", cp))
        else:
            units.append(("C", cp))
    return units


def truncate_by_units(cps, n):
    """Keep the first n UTF-16 units and rebuild; a trailing lone high surrogate means a split character."""
    u = unit_list(cps)[:n]
    broken = len(u) > 0 and u[-1][0] == "H"
    out, i = [], 0
    while i < len(u):
        if u[i][0] == "C":
            out.append(u[i][1]); i += 1
        elif u[i][0] == "H" and i + 1 < len(u) and u[i + 1][0] == "L":
            out.append(u[i][1]); i += 2
        else:
            i += 1  # lone surrogate: dropped, the split is recorded in `broken`
    return out, broken


def truncate_by_code_points(cps, n):
    """Keep the first n code points -- atomic, so never splits a character."""
    return cps[:n], False


# ----------------------------------------------------------------- printing

def _show(cps, labels):
    return " ".join(labels[i] for i in range(len(cps)))


def measure_view(d):
    cps, labels, limit = d["code_points"], d["labels"], d["limit"]
    print("MEASURE — string: %s" % _show(cps, labels))
    print("-" * 64)
    print("  code-point length (Python len) = %d" % code_point_len(cps))
    print("  UTF-16 length (JS/Java .length) = %d" % utf16_len(cps))
    print("  limit %d: fits by code points? %s   fits by UTF-16 units? %s"
          % (limit, code_point_len(cps) <= limit, utf16_len(cps) <= limit))
    print("-" * 64)
    print("  the same string is two different lengths; a limit judges it differently under each")


def truncate_view(d):
    cps, labels = d["code_points"], d["labels"]
    n = d["truncate_units"]
    by_u, broken_u = truncate_by_units(cps, n)
    by_c, broken_c = truncate_by_code_points(cps, n)
    print("TRUNCATE — cut to %d units vs %d code points" % (n, n))
    print("-" * 64)
    print("  by UTF-16 units: kept code points %s  split a character? %s" % (by_u, broken_u))
    print("  by code points : kept code points %s  split a character? %s" % (by_c, broken_c))
    print("-" * 64)
    print("  cutting at a UTF-16 unit boundary can land inside a surrogate pair; code points cannot")


def check(d):
    print("SELF-TEST — the two lengths differ because the astral character is two UTF-16 units, a unit-based limit disagrees with a code-point limit, and unit truncation splits a character while code-point truncation does not")
    print("-" * 112)
    cps, limit, n = d["code_points"], d["limit"], d["truncate_units"]
    cpl, u16 = code_point_len(cps), utf16_len(cps)

    lengths_differ = cpl != u16
    print("  code-point length differs from UTF-16 length = %s (%d vs %d)" % (lengths_differ, cpl, u16))

    astral = sum(1 for cp in cps if cp >= 0x10000)
    astral_adds_units = (u16 - cpl) == astral
    print("  the extra units equal the number of astral characters = %s (%d extra, %d astral)" % (astral_adds_units, u16 - cpl, astral))

    limit_disagrees = (cpl <= limit) != (u16 <= limit)
    print("  a limit of %d admits the string by one measure but not the other = %s (cp %s, u16 %s)" % (limit, limit_disagrees, cpl <= limit, u16 <= limit))

    _by_u, broken_u = truncate_by_units(cps, n)
    unit_trunc_splits = broken_u
    print("  truncating to %d UTF-16 units splits a character = %s" % (n, unit_trunc_splits))

    _by_c, broken_c = truncate_by_code_points(cps, n)
    codepoint_trunc_safe = not broken_c
    print("  truncating to %d code points never splits a character = %s" % (n, codepoint_trunc_safe))

    ok = (lengths_differ and astral_adds_units and limit_disagrees and unit_trunc_splits and codepoint_trunc_safe)
    print("-" * 112)
    print("SELF-TEST %s  lengths_differ=%s  astral_adds_units=%s  limit_disagrees=%s  unit_trunc_splits=%s  codepoint_trunc_safe=%s"
          % ("PASS" if ok else "FAIL", lengths_differ, astral_adds_units, limit_disagrees, unit_trunc_splits, codepoint_trunc_safe))
    return ok


def main():
    p = argparse.ArgumentParser(description="Code points vs UTF-16 code units: 'string length' is code points in Python but UTF-16 code units in JavaScript and Java, and a code point above U+10000 is one code point but two code units -- so the same string has different lengths across languages, a length limit judges it differently, and indexing or truncating by UTF-16 units can split a surrogate pair into a lone half-character, which truncating by code points cannot.")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--truncate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("code_points=%s  limit=%d  truncate_units=%d  file=%s" % (d["code_points"], d["limit"], d["truncate_units"], DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.measure:
        measure_view(d)
    elif args.truncate:
        truncate_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
