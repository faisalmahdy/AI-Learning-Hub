"""Fold case with a locale-independent rule for comparison -- not the OS locale's lower/upper -- or the same case-insensitive check gives different answers on different machines.

Turning a letter from upper to lower case looks universal and is not. The mapping depends on the locale, and the most famous divergence is the letter I. In most locales the uppercase 'I' lowercases to 'i' (dotted). But the Turkish and Azeri alphabets have TWO I letters -- a dotless pair ('I' and 'ı') and a dotted pair ('İ' and 'i') -- so in those locales 'I' lowercases to the dotless 'ı', and it is the dotted 'İ' that lowercases to 'i'. The same call to lower() on the same string returns 'i' on one machine and 'ı' on another, purely because of the locale the process is running in.

That difference wrecks case-insensitive comparison, which is usually implemented by lowercasing both sides and testing equality. Consider a blocklist that forbids the username 'admin' and checks new names by lowercasing them and comparing. On a machine in an English locale, 'ADMIN'.lower() is 'admin', the check matches, and the name is blocked -- correct. On a machine in a Turkish locale, 'ADMIN'.lower() is 'admın' (with a dotless i), which does NOT equal 'admin', so the check misses and the forbidden name is allowed. Same code, same input, different security decision -- decided by the server's locale, which the developer never thought about.

The fix is to stop folding case by the locale and fold it by a fixed, locale-independent rule instead: an invariant case fold that uses the Unicode default mapping (in which 'I' always maps to 'i') regardless of where the code runs, or an explicit invariant-culture API. The comparison then returns the same answer on every machine, because the mapping no longer moves under it. This is the case-comparison cousin of every other 'pin the environment' rule: do not let an implicit locale silently change what your code computes.

The rule: for case-insensitive comparison, fold case with a locale-independent (invariant) mapping, not the OS locale's lower/upper, because case conversion is locale-dependent -- the Turkish dotless-I is the classic example -- so a locale-sensitive fold makes the same check accept or reject the same string differently on different machines.

On this fixture the blocklist forbids 'admin'. Under the invariant fold all three inputs lowercase to 'admin' and are blocked; under the Turkish fold, any input containing an uppercase I lowercases to 'admın' and slips past -- 2 of 3 bypass. This computes both.

  --fold      each input's lowercased form under the invariant vs the Turkish locale
  --block     which inputs the blocklist catches under each locale, and which bypass
  --check     the locale-sensitive fold lets forbidden names bypass on a Turkish-locale machine; the invariant fold blocks them everywhere

forbidden and inputs are the fixture; every folded form and block decision are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "localecase.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def invariant_lower(s):
    """Locale-independent fold: uppercase A-Z map to a-z, so 'I' -> 'i' always."""
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)


def turkish_lower(s):
    """Turkish locale fold: 'I' -> dotless 'ı', dotted 'İ' -> 'i'."""
    out = []
    for c in s:
        if c == "I":
            out.append("ı")
        elif c == "İ":
            out.append("i")
        elif "A" <= c <= "Z":
            out.append(chr(ord(c) + 32))
        else:
            out.append(c)
    return "".join(out)


def blocked(value, forbidden, fold):
    return fold(value) == forbidden


# ----------------------------------------------------------------- printing

def fold_view(data):
    inputs = data["inputs"]
    print("FOLD — each input lowercased under the invariant vs the Turkish locale")
    print("-" * 60)
    print("  input     invariant   turkish")
    for s in inputs:
        print("  %-8s  %-10s  %s" % (s, invariant_lower(s), turkish_lower(s)))
    print("-" * 60)
    print("  an uppercase 'I' folds to 'i' invariantly but to dotless 'ı' in Turkish")


def block_view(data):
    inputs, forbidden = data["inputs"], data["forbidden"]
    print("BLOCK — which inputs the blocklist (forbid %r) catches under each locale" % forbidden)
    print("-" * 62)
    print("  input     invariant blocks?   turkish blocks?")
    for s in inputs:
        inv = blocked(s, forbidden, invariant_lower)
        tr = blocked(s, forbidden, turkish_lower)
        note = "   <- BYPASS in Turkish" if inv and not tr else ""
        print("  %-8s  %-17s  %s%s" % (s, inv, tr, note))
    print("-" * 62)
    print("  the invariant fold blocks every spelling; the Turkish fold lets uppercase-I names through")


def check(data):
    print("SELF-TEST — the locale-sensitive fold lets forbidden names bypass on a Turkish-locale machine; the invariant fold blocks them everywhere")
    print("-" * 136)
    inputs, forbidden = data["inputs"], data["forbidden"]
    inv_blocked = [s for s in inputs if blocked(s, forbidden, invariant_lower)]
    tr_blocked = [s for s in inputs if blocked(s, forbidden, turkish_lower)]
    bypass = [s for s in inputs if blocked(s, forbidden, invariant_lower) and not blocked(s, forbidden, turkish_lower)]

    folds_differ = any(invariant_lower(s) != turkish_lower(s) for s in inputs)
    print("  the two locales fold some input differently = %s" % folds_differ)

    invariant_blocks_all = len(inv_blocked) == len(inputs)
    print("  the invariant fold blocks every spelling of the forbidden name = %s (%d/%d)" % (invariant_blocks_all, len(inv_blocked), len(inputs)))

    turkish_misses_some = len(tr_blocked) < len(inputs)
    print("  the Turkish fold blocks fewer than all = %s (%d/%d)" % (turkish_misses_some, len(tr_blocked), len(inputs)))

    bypass_exists = len(bypass) > 0
    print("  a forbidden name bypasses under the Turkish fold = %s (%s)" % (bypass_exists, bypass))

    locale_changes_decision = inv_blocked != tr_blocked
    print("  the same code makes a different block decision by locale = %s" % locale_changes_decision)

    ok = (folds_differ and invariant_blocks_all and turkish_misses_some and bypass_exists and locale_changes_decision)
    print("-" * 136)
    print("SELF-TEST %s  folds_differ=%s  invariant_blocks_all=%s  turkish_misses_some=%s  bypass_exists=%s  locale_changes_decision=%s"
          % ("PASS" if ok else "FAIL", folds_differ, invariant_blocks_all, turkish_misses_some, bypass_exists, locale_changes_decision))
    return ok


def main():
    p = argparse.ArgumentParser(description="Locale-dependent case folding: for case-insensitive comparison, fold case with a locale-independent (invariant) mapping, not the OS locale's lower/upper, because case conversion is locale-dependent -- the Turkish dotless-I is the classic example -- so a locale-sensitive fold makes the same check accept or reject the same string differently on different machines.")
    p.add_argument("--fold", action="store_true")
    p.add_argument("--block", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("forbidden=%r  inputs=%s  file=%s  (the blocklist and inputs are a fixture)"
          % (data["forbidden"], data["inputs"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.fold:
        fold_view(data)
    elif args.block:
        block_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
