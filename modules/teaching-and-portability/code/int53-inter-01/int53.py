"""An integer ID larger than 2^53 loses precision the moment it passes through a 64-bit float, so a JSON parser that decodes numbers as doubles, a JavaScript Number, a spreadsheet cell, or a float column silently returns a different, wrong ID -- and two distinct IDs can collapse to the same value -- while carrying the ID as a string keeps every digit exact.

A double has a 52-bit mantissa plus one implicit leading bit, so it represents every integer exactly up to 2^53 = 9007199254740992 and no further. Above that, the representable values step by 2, then 4, then 8, so most integers in the range are simply not representable and snap to the nearest one that is. This is not a rounding you asked for; it is the type's ceiling.

It bites because so many pipes are secretly doubles. JavaScript has one number type and it is a double, so JSON.parse turns a big integer ID into a double. Spreadsheets store numbers as doubles. A float column does too. Send a 64-bit ID -- a Twitter/snowflake ID, a Discord ID, a bigint primary key -- through any of them and it comes back changed. Nothing raises: the number is a valid number, just the wrong one, and a lookup by it hits the wrong row or none.

The tell is that IDs at or below 2^53 - 1 (JavaScript calls it Number.MAX_SAFE_INTEGER) survive the round trip, and IDs above it do not. Worse than a single corrupted ID: because whole runs of integers snap to the same double, two different IDs can come back identical, so they collide and become indistinguishable.

The fix is to never let a large integer ID travel as a JSON or JavaScript number. Carry it as a string -- the digits are just text, so they survive any parser -- or decode with a parser that produces a big integer or a decimal. On this fixture Python's float IS the 64-bit double, so int(float(id)) reproduces exactly what a double-based parser does. This computes the round trip for each ID and the collision for two snowflake IDs.

  --roundtrip  each ID through a double and back: small ones survive, ones above 2^53 come back wrong
  --collide    two distinct snowflake IDs collapse to the same double, but stay distinct as strings
  --check      IDs within the safe range survive, an ID above it is corrupted, two distinct IDs collide, and the string form preserves them all

max_safe_int is 2^53 - 1; each ID's value is the fixture; every round trip, corruption, and collision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "int53.json"
TWO_53 = 2 ** 53


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def through_double(n):
    """Pass an integer through a 64-bit float and back -- exactly what a double-based JSON parser does."""
    return int(float(n))


def is_corrupted(n):
    """True if the value does not survive the double round trip."""
    return through_double(n) != n


def in_safe_range(n):
    """True if the integer is small enough to be exactly representable as a double (|n| <= 2^53)."""
    return abs(n) <= TWO_53


def collide(a, b):
    """True if two distinct integers map to the same double -- indistinguishable after the round trip."""
    return a != b and float(a) == float(b)


# ----------------------------------------------------------------- printing

def roundtrip_view(data):
    print("ROUNDTRIP — each ID through a 64-bit float and back (max safe = %d)" % data["max_safe_int"])
    print("-" * 72)
    for it in data["ids"]:
        v = it["value"]
        got = through_double(v)
        mark = "ok" if got == v else "CORRUPTED -> %d" % got
        print("  %-18s %-20d safe=%-5s %s" % (it["label"], v, in_safe_range(v), mark))
    print("-" * 72)
    print("  every ID above 2^53 comes back as a different number -- a valid, wrong ID")


def collide_view(data):
    ids = {it["label"]: it["value"] for it in data["ids"]}
    a, b = ids["snowflake_a"], ids["snowflake_b"]
    print("COLLIDE — two distinct snowflake IDs that differ by 1")
    print("-" * 72)
    print("  snowflake_a = %d" % a)
    print("  snowflake_b = %d" % b)
    print("  as doubles: %d and %d" % (through_double(a), through_double(b)))
    print("  collide as numbers? %s   (distinct as strings? %s)" % (collide(a, b), str(a) != str(b)))
    print("-" * 72)
    print("  through a double they are the same ID; as strings they stay two IDs")


def check(data):
    print("SELF-TEST — IDs within the safe range survive, an ID above it is corrupted, two distinct IDs collide, and the string form preserves them all")
    print("-" * 112)
    ids = {it["label"]: it["value"] for it in data["ids"]}

    safe_ids_survive = all(not is_corrupted(v) for v in ids.values() if in_safe_range(v))
    print("  every ID within the safe range survives the double round trip = %s" % safe_ids_survive)

    unsafe_corrupts = is_corrupted(ids["2^53+1"])
    print("  the ID just past 2^53 is corrupted = %s (%d -> %d)" % (unsafe_corrupts, ids["2^53+1"], through_double(ids["2^53+1"])))

    boundary_exact = not is_corrupted(ids["2^53"])
    print("  2^53 itself is still exact (the last exact one) = %s" % boundary_exact)

    ids_collide = collide(ids["snowflake_a"], ids["snowflake_b"])
    print("  two distinct snowflake IDs collide as doubles = %s (both -> %d)" % (ids_collide, through_double(ids["snowflake_a"])))

    string_preserves = all(int(str(v)) == v for v in ids.values()) and str(ids["snowflake_a"]) != str(ids["snowflake_b"])
    print("  carrying IDs as strings preserves every value and keeps them distinct = %s" % string_preserves)

    ok = (safe_ids_survive and unsafe_corrupts and boundary_exact and ids_collide and string_preserves)
    print("-" * 112)
    print("SELF-TEST %s  safe_ids_survive=%s  unsafe_corrupts=%s  boundary_exact=%s  ids_collide=%s  string_preserves=%s"
          % ("PASS" if ok else "FAIL", safe_ids_survive, unsafe_corrupts, boundary_exact, ids_collide, string_preserves))
    return ok


def main():
    p = argparse.ArgumentParser(description="Large-integer-as-double: an integer ID above 2^53 loses precision passing through a 64-bit IEEE-754 float, which is what a JSON parser decoding numbers as doubles, a JavaScript Number, a spreadsheet, or a float column all do -- so the ID round-trips as a different, wrong number and two distinct IDs can collapse to one; carry large integer IDs as strings (or parse to a big integer) so every digit survives.")
    p.add_argument("--roundtrip", action="store_true")
    p.add_argument("--collide", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("max_safe_int=%d (2^53-1)  ids=%d  file=%s" % (data["max_safe_int"], len(data["ids"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.roundtrip:
        roundtrip_view(data)
    elif args.collide:
        collide_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
