"""Compare version numbers component-by-component as integers, not as strings -- '1.10' sorts before '1.9' lexicographically because the character '1' is less than '9', even though release 1.10 comes after 1.9.

A dotted version like 1.10.0 looks like it could be sorted as text, and for a while it can: while every component is a single digit, string order and version order happen to agree. That coincidence is the trap. A version is not a word and not a decimal number; it is a sequence of integer components, and the correct comparison reads those components left to right and compares each as an integer.

String comparison does something different: it compares raw characters one position at a time. Line up '1.10' and '1.9' -- they share '1' and '.', and then one has '1' (the first digit of the component '10') while the other has '9'. Character '1' is less than character '9', so the string comparison declares '1.10' < '1.9' and stops. The component '10' was never read as the number ten; only its first digit was, against the whole of '9'.

That is why the bug hides and then bites. Up through 1.9, every component is one digit, string and numeric order match, and the naive string sort looks correct. The first time a component reaches double digits -- the 1.10 release -- string order diverges from version order, and 1.10 is suddenly sorted as if it were older than 1.9. Because reaching 1.10 means a project has shipped ten minor releases, this lands on mature, heavily-used software, where an update check or a 'latest version' pick silently regresses.

The fix is to parse before comparing: split each version on the dots, turn each component into an integer, and compare the resulting tuples. Python compares tuples element by element, so (1, 10) > (1, 9) correctly, and shorter versions order before their extensions ((1, 9) < (1, 9, 1)). The comparison must happen in integer space, never in character space.

The rule: compare versions by parsing each into a tuple of integer components and comparing the tuples, never by comparing the version strings lexicographically, because string comparison is per-character and judges '1.10' < '1.9' (the character '1' is less than '9'), sorting a newer release as older the moment a component reaches double digits.

On this fixture the string sort puts 1.10 before 1.2 and 1.9 -- treating the newest release as the oldest -- while the integer-tuple sort orders them 1.2, 1.9, 1.9.1, 1.10 correctly. This computes both.

  --parse    each version string parsed into its integer-component tuple
  --sort     the string-sorted order vs the component-wise integer-sorted order
  --check    string comparison misorders double-digit components; tuple-of-int comparison orders correctly

versions is the fixture; the parsed tuples, the two sort orders, and the disagreeing pair are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "versioncmp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def parse(version):
    """Split on dots and turn each component into an integer -- the correct comparison key."""
    return tuple(int(part) for part in version.split("."))


def string_sorted(versions):
    """Sort by the raw string -- lexicographic, per-character."""
    return sorted(versions)


def version_sorted(versions):
    """Sort by the integer-component tuple -- the correct version order."""
    return sorted(versions, key=parse)


# ----------------------------------------------------------------- printing

def parse_view(data):
    versions = data["versions"]
    print("PARSE — each version string as its integer-component tuple")
    print("-" * 44)
    for v in versions:
        print("  %-8s -> %s" % (v, parse(v)))
    print("-" * 44)
    print("  the tuple is what carries the correct ordering")


def sort_view(data):
    versions = data["versions"]
    print("SORT — string order vs integer-component order")
    print("-" * 54)
    print("  string-sorted : %s" % string_sorted(versions))
    print("  version-sorted: %s" % version_sorted(versions))
    print("-" * 54)
    print("  the string sort puts 1.10 near the front, as if it were the oldest")


def check(data):
    print("SELF-TEST — string comparison misorders double-digit components; tuple-of-int comparison orders correctly")
    print("-" * 112)
    versions = data["versions"]

    string_says_110_less_than_19 = "1.10" < "1.9"
    print("  as strings, '1.10' < '1.9' = %s (character '1' < '9')" % string_says_110_less_than_19)

    version_says_110_greater = parse("1.10") > parse("1.9")
    print("  as integer tuples, 1.10 > 1.9 = %s (%s > %s)" % (version_says_110_greater, parse("1.10"), parse("1.9")))

    ss = string_sorted(versions)
    vs = version_sorted(versions)
    orders_differ = ss != vs
    print("  the two sort orders disagree = %s" % orders_differ)

    string_puts_newest_wrong = ss[-1] != "1.10" and vs[-1] == "1.10"
    print("  the string sort fails to put 1.10 last (newest); the version sort does = %s" % string_puts_newest_wrong)

    tuple_handles_length = parse("1.9.1") > parse("1.9")
    print("  tuple comparison orders 1.9.1 after 1.9 = %s" % tuple_handles_length)

    ok = (string_says_110_less_than_19 and version_says_110_greater and orders_differ
          and string_puts_newest_wrong and tuple_handles_length)
    print("-" * 112)
    print("SELF-TEST %s  string_says_110_less_than_19=%s  version_says_110_greater=%s  orders_differ=%s  string_puts_newest_wrong=%s  tuple_handles_length=%s"
          % ("PASS" if ok else "FAIL", string_says_110_less_than_19, version_says_110_greater,
             orders_differ, string_puts_newest_wrong, tuple_handles_length))
    return ok


def main():
    p = argparse.ArgumentParser(description="Version comparison: compare versions by parsing each into a tuple of integer components and comparing the tuples, never by comparing the version strings lexicographically, because string comparison is per-character and judges '1.10' < '1.9' (the character '1' is less than '9'), sorting a newer release as older the moment a component reaches double digits.")
    p.add_argument("--parse", action="store_true")
    p.add_argument("--sort", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("versions=%s  file=%s  (the versions are a fixture)" % (data["versions"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.parse:
        parse_view(data)
    elif args.sort:
        sort_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
