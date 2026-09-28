"""Format numbers locale-independently for interchange -- or a comma-decimal locale writes data another machine misreads.

Locales disagree on how to write a number. The United States writes one-thousand-two-hundred-thirty-four-point-five as
1,234.5 -- period for the decimal, comma for thousands. Much of Europe writes the same value as 1.234,5 -- comma for the
decimal, period for thousands. Both are correct locally, and both are ambiguous globally: the string '1.234' is a little
over one in the US convention and one thousand two hundred thirty-four in the German one. So a program that formats or
parses numbers using whatever locale the machine is set to produces data that another machine, set to a different
locale, cannot read -- and the dangerous part is that it often does not fail. It silently reads the number as a
different value: the European '1.234,5' parsed by a US-locale reader becomes 1.234, off by a factor of a thousand, with
no error to warn you.

The fix is to stop using the DISPLAY locale for DATA. Any number that will be stored, transmitted, compared, or parsed
-- a CSV field, a JSON value, a config entry, a cache key -- must use a single fixed, locale-independent format: a
period decimal, no thousands separators, the same on every machine (1234.5), parsed the same way everywhere. Locale
formatting is for showing a number to a human in their own convention; it must never be the format you round-trip
through, because the moment the writer's locale and the reader's locale differ, the value changes. Use the display
locale at the edge, for humans; use the fixed format for everything a program reads back.

On this fixture the value 1234.5 formats as '1,234.5' in the US locale and '1.234,5' in the DE locale -- different text
for the same number. Parsing the US string with DE rules, or the DE string with US rules, yields the wrong value; only
the fixed format, parsed with fixed rules, round-trips to 1234.5 exactly. This computes both.

  --format     the value written in the US locale, the DE locale, and the fixed locale-independent format
  --roundtrip  each locale's string parsed by its OWN rules (correct) vs by the OTHER locale's rules (wrong)
  --check      the locale strings differ and cross-parse to wrong values; the fixed format round-trips everywhere

The value and locale conventions are the fixture; every format and parse is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "numlocale.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def fmt(value, decimal, thousands):
    """Write `value` with the given decimal and thousands separators."""
    whole, frac = ("%.1f" % value).split(".")
    if thousands:
        groups = []
        while len(whole) > 3:
            groups.insert(0, whole[-3:])
            whole = whole[:-3]
        groups.insert(0, whole)
        whole = thousands.join(groups)
    return whole + decimal + frac


def parse(s, decimal, thousands):
    """Read a number string under the given separators: drop thousands, normalize the decimal to a period, to float."""
    if thousands:
        s = s.replace(thousands, "")
    s = s.replace(decimal, ".")
    return float(s)


# ----------------------------------------------------------------- printing

def format_view(data):
    v, loc, fixed = data["value"], data["locales"], data["fixed"]
    print("FORMAT — the same number written three ways")
    print("-" * 50)
    for name in loc:
        print("  %-8s locale:  %s" % (name, fmt(v, loc[name]["decimal"], loc[name]["thousands"])))
    print("  fixed (interchange): %s" % fmt(v, fixed["decimal"], fixed["thousands"]))
    print("-" * 50)
    print("  same value, three strings -- and '1.234' means different numbers in US and DE.")


def roundtrip_view(data):
    v, loc, fixed = data["value"], data["locales"], data["fixed"]
    us_s = fmt(v, loc["US"]["decimal"], loc["US"]["thousands"])
    de_s = fmt(v, loc["DE"]["decimal"], loc["DE"]["thousands"])
    print("ROUNDTRIP — parse each string by its own rules vs the other locale's rules")
    print("-" * 66)
    print("  US string %-9s parsed as US = %-8s  parsed as DE = %s" % (us_s, parse(us_s, loc["US"]["decimal"], loc["US"]["thousands"]), parse(us_s, loc["DE"]["decimal"], loc["DE"]["thousands"])))
    print("  DE string %-9s parsed as DE = %-8s  parsed as US = %s" % (de_s, parse(de_s, loc["DE"]["decimal"], loc["DE"]["thousands"]), parse(de_s, loc["US"]["decimal"], loc["US"]["thousands"])))
    fx = fmt(v, fixed["decimal"], fixed["thousands"])
    print("  fixed  %-12s parsed fixed = %s" % (fx, parse(fx, fixed["decimal"], fixed["thousands"])))
    print("-" * 66)
    print("  cross-locale parsing silently returns the wrong number; the fixed format round-trips.")


def check(data):
    print("SELF-TEST — the locale strings differ and cross-parse to wrong values; the fixed format round-trips everywhere")
    print("-" * 112)
    v, loc, fixed = data["value"], data["locales"], data["fixed"]
    us, de = loc["US"], loc["DE"]
    us_s = fmt(v, us["decimal"], us["thousands"])
    de_s = fmt(v, de["decimal"], de["thousands"])

    strings_differ = us_s != de_s
    print("  the US and DE strings differ for the same value = %s (%r vs %r)" % (strings_differ, us_s, de_s))

    same_locale_ok = parse(us_s, us["decimal"], us["thousands"]) == v and parse(de_s, de["decimal"], de["thousands"]) == v
    print("  each string parsed by its OWN locale gives the right value = %s" % same_locale_ok)

    cross_parse_wrong = parse(us_s, de["decimal"], de["thousands"]) != v and parse(de_s, us["decimal"], us["thousands"]) != v
    print("  parsing across locales gives the WRONG value = %s (US-as-DE %s, DE-as-US %s)"
          % (cross_parse_wrong, parse(us_s, de["decimal"], de["thousands"]), parse(de_s, us["decimal"], us["thousands"])))

    fx = fmt(v, fixed["decimal"], fixed["thousands"])
    fixed_roundtrips = parse(fx, fixed["decimal"], fixed["thousands"]) == v
    print("  the fixed format round-trips to the exact value = %s (%r -> %s)" % (fixed_roundtrips, fx, parse(fx, fixed["decimal"], fixed["thousands"])))

    fixed_is_clean = fixed["decimal"] == "." and fixed["thousands"] == "" and "," not in fx
    print("  the fixed format is a period decimal with no thousands separator = %s (%r)" % (fixed_is_clean, fx))

    ok = strings_differ and same_locale_ok and cross_parse_wrong and fixed_roundtrips and fixed_is_clean
    print("-" * 112)
    print("SELF-TEST %s  strings_differ=%s  same_locale_ok=%s  cross_parse_wrong=%s  fixed_roundtrips=%s  fixed_is_clean=%s"
          % ("PASS" if ok else "FAIL", strings_differ, same_locale_ok, cross_parse_wrong, fixed_roundtrips, fixed_is_clean))
    return ok


def main():
    p = argparse.ArgumentParser(description="Format numbers with a fixed locale-independent format (period decimal, no thousands separator) for any data that is stored, transmitted, or parsed, because locale formatting makes one machine's numbers unreadable or misread on another.")
    p.add_argument("--format", action="store_true")
    p.add_argument("--roundtrip", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("value=%s  locales=%s  file=%s  (the value and separators are a fixture)"
          % (data["value"], list(data["locales"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.format:
        format_view(data)
    elif args.roundtrip:
        roundtrip_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
