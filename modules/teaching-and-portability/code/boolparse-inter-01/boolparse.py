"""Parse a boolean config value against known tokens, never with bool() on the string -- bool() of a string tests emptiness, not meaning, so bool('false') is True and every human way of writing 'off' turns the setting on.

A boolean setting almost never reaches your code as a boolean. It comes from a config file, a command-line flag, or an environment variable, and all of those carry text: the string 'false', not the value False. Somewhere the string has to be turned into a boolean, and the tempting one-liner is bool(value).

That is the bug. bool() applied to a string does not read the string's meaning; it asks whether the string is empty. Every non-empty string is truthy, so bool('true') is True and bool('false') is True and bool('0') is True and bool('no') is True -- only the empty string is False. The one value that behaves as you might hope, the empty string, is an accident, not comprehension.

The consequence is a setting inverted for exactly the values a person uses to turn something off. Someone writes FEATURE_ENABLED=false in the config, fully expecting the feature off, and bool('false') hands back True, so the feature is on. There is no error and no warning -- the flag simply means the opposite of what the config says, for 'false', 'False', '0', 'no', and 'off' alike, while 'true' and '1' happen to come out right, which makes the bug look like it works in a quick test that only tries the true case.

The fix is an explicit parser: lowercase the string, strip it, and match it against a known set of truthy tokens (true, 1, yes, on) and falsy tokens (false, 0, no, off), returning the corresponding boolean and rejecting anything else rather than guessing. The meaning of the string is decided by the parser, not by whether the string has characters in it.

On this fixture nine config strings are interpreted both ways. bool() reads all eight non-empty strings as True -- including 'false', '0', 'no', 'off' -- and only the empty string as False; the explicit parser reads the four falsy tokens as False and the truthy ones as True. This computes both.

  --naive   bool() applied to each config string
  --parse   the explicit token parser applied to each config string
  --check   bool() reads every non-empty string as True, inverting the falsy ones; the explicit parser reads them correctly

values is the fixture; bool() and the explicit parser results for each are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "boolparse.json"

TRUTHY = {"true", "1", "yes", "on"}
FALSY = {"false", "0", "no", "off"}


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_bool(s):
    """The bug: bool() of a string tests emptiness, not meaning."""
    return bool(s)


def parse_bool(s):
    """Map the string against known tokens; raise on anything unrecognized rather than guess."""
    key = s.strip().lower()
    if key in TRUTHY:
        return True
    if key in FALSY:
        return False
    raise ValueError("not a recognized boolean: %r" % s)


# ----------------------------------------------------------------- printing

def naive_view(data):
    print("NAIVE — bool() applied to each config string")
    print("-" * 44)
    for v in data["values"]:
        print("  bool(%-8r) = %s" % (v, naive_bool(v)))
    print("-" * 44)
    print("  every non-empty string is True -- 'false', '0', 'no', 'off' all read as on")


def parse_view(data):
    print("PARSE — the explicit token parser applied to each config string")
    print("-" * 44)
    for v in data["values"]:
        try:
            print("  parse_bool(%-8r) = %s" % (v, parse_bool(v)))
        except ValueError as e:
            print("  parse_bool(%-8r) -> ValueError (%s)" % (v, e))
    print("-" * 44)
    print("  the falsy tokens read as False; an unrecognized value is rejected, not guessed")


def check(data):
    print("SELF-TEST — bool() reads every non-empty string as True, inverting the falsy ones; the explicit parser reads them correctly")
    print("-" * 112)
    values = data["values"]

    falsy_strings = ["false", "False", "0", "no", "off"]
    bool_true_on_falsy = all(naive_bool(s) is True for s in falsy_strings)
    print("  bool() is True for every falsy-looking string = %s (%s)" % (bool_true_on_falsy, falsy_strings))

    only_empty_is_false = [v for v in values if naive_bool(v) is False] == [""]
    print("  the only string bool() reads as False is the empty string = %s" % only_empty_is_false)

    naive_inverts_falsy = all(naive_bool(s) != parse_bool(s) for s in ["false", "0", "no", "off"])
    print("  bool() and the parser disagree on every falsy token = %s" % naive_inverts_falsy)

    parser_reads_falsy = all(parse_bool(s) is False for s in ["false", "False", "0", "no", "off"])
    print("  the parser reads the falsy tokens as False = %s" % parser_reads_falsy)

    parser_reads_truthy = all(parse_bool(s) is True for s in ["true", "1", "yes", "on"])
    print("  the parser reads the truthy tokens as True = %s" % parser_reads_truthy)

    ok = (bool_true_on_falsy and only_empty_is_false and naive_inverts_falsy
          and parser_reads_falsy and parser_reads_truthy)
    print("-" * 112)
    print("SELF-TEST %s  bool_true_on_falsy=%s  only_empty_is_false=%s  naive_inverts_falsy=%s  parser_reads_falsy=%s  parser_reads_truthy=%s"
          % ("PASS" if ok else "FAIL", bool_true_on_falsy, only_empty_is_false, naive_inverts_falsy,
             parser_reads_falsy, parser_reads_truthy))
    return ok


def main():
    p = argparse.ArgumentParser(description="Boolean parsing: parse a boolean config value against known tokens, never with bool() on the string, because bool() of a string tests emptiness not meaning -- so bool('false') is True and every human way of writing 'off' turns the setting on.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--parse", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("values=%s  file=%s  (the values are a fixture)" % (data["values"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.parse:
        parse_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
