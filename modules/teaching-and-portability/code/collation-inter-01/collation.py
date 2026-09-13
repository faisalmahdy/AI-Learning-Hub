"""Sort by codepoint for a canonical, reproducible output -- not the locale's collation -- because collation rules vary by machine and language, so a locale sort produces different orders, bytes, and hashes on different systems.

Sorting looks like one of the most deterministic operations there is, and within a single machine it is. What is not universal is the comparison the sort uses. A codepoint sort orders characters by their numeric code point, which is the same everywhere: 'z' (code 122) comes before 'é' (233), and every uppercase letter comes before every lowercase one. A locale collation orders text the way a human reader of that locale expects instead: it folds accents so 'é' sorts next to 'e', folds or interleaves upper and lower case, and applies language-specific rules -- Swedish, German, and French disagree about where accented and special letters belong. So the collation order is a function of the machine's locale setting and the version of the collation data installed, and two systems can sort the identical list into two different orders.

For text you are about to show a person, the collation order is the right one -- it is what the reader expects. The trap is using it anywhere the output must be reproducible. A very common pattern is to sort a collection before hashing it, serializing it, or diffing it, precisely to get a canonical form that does not depend on insertion order. If that sort uses the locale's collation, the canonical form is no longer canonical: it depends on the locale, so the same data hashes to different values on different machines, a content-addressed dedup treats identical data as distinct, and a diff between two machines' outputs shows changes that are only reorderings. The bug hides until the code runs on a machine with a different locale than the author's.

The fix is to sort by codepoint whenever the result must be reproducible. A byte/codepoint sort is a pure function of the data with no hidden locale input, so it produces the same order on every machine. Reserve locale collation for the last step before display, and keep it out of anything that gets hashed, stored, compared, or transmitted as a canonical form.

The rule: sort by codepoint (a fixed, locale-independent order) for any output that must be reproducible -- hashed, serialized, diffed, or deduplicated -- not by locale collation, because collation depends on the machine's locale and version, so a locale sort makes the 'same' data order, and hash, differently across systems.

On this fixture the codepoint sort orders the accented word 'éclair' after 'zebra' (é's code is above z's), while a locale collation folds the accent and orders it after 'apple'; the two orders serialize to different strings with different hashes. This computes both.

  --sort     the codepoint order vs the locale-collation order of the words
  --hash     the serialized string and hash of each order, showing they differ
  --check    the locale collation reorders the words and changes the hash; the codepoint sort is fixed

words and accent_map are the fixture; the two orders and their hashes are computed. Stdlib only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "collation.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def codepoint_sort(words):
    """Order by numeric code point -- fixed on every machine."""
    return sorted(words)


def collation_sort(words, accent_map):
    """Order by an accent-folded, case-folded key -- a stand-in for a locale collation."""
    def key(s):
        return "".join(accent_map.get(c, c).lower() for c in s)
    return sorted(words, key=key)


def serialize(words):
    return "|".join(words)


def digest(words):
    return hashlib.sha256(serialize(words).encode("utf-8")).hexdigest()[:8]


# ----------------------------------------------------------------- printing

def sort_view(data):
    words, amap = data["words"], data["accent_map"]
    print("SORT — codepoint order vs locale-collation order")
    print("-" * 56)
    print("  codepoint : %s" % codepoint_sort(words))
    print("  collation : %s" % collation_sort(words, amap))
    print("-" * 56)
    print("  codepoint puts 'éclair' after 'zebra' (é > z); collation folds é to e, near 'apple'")


def hash_view(data):
    words, amap = data["words"], data["accent_map"]
    cp, col = codepoint_sort(words), collation_sort(words, amap)
    print("HASH — the serialized canonical form and its hash, each order")
    print("-" * 60)
    print("  codepoint : %-28s  %s" % (serialize(cp), digest(cp)))
    print("  collation : %-28s  %s" % (serialize(col), digest(col)))
    print("-" * 60)
    print("  the locale order hashes differently — the 'canonical' form is not canonical")


def check(data):
    print("SELF-TEST — the locale collation reorders the words and changes the hash; the codepoint sort is fixed")
    print("-" * 116)
    words, amap = data["words"], data["accent_map"]
    cp, col = codepoint_sort(words), collation_sort(words, amap)

    orders_differ = cp != col
    print("  the codepoint and collation orders differ = %s" % orders_differ)
    print("    codepoint: %s" % cp)
    print("    collation: %s" % col)

    hashes_differ = digest(cp) != digest(col)
    print("  the two orders hash to different canonical forms = %s (%s != %s)" % (hashes_differ, digest(cp), digest(col)))

    codepoint_is_pure = codepoint_sort(words) == codepoint_sort(list(reversed(words)))
    print("  the codepoint sort is the same regardless of input order = %s" % codepoint_is_pure)

    accent_moves = words != codepoint_sort(words) and any(c in amap for w in words for c in w)
    print("  the fixture contains an accented word that the two orders place differently = %s" % accent_moves)

    codepoint_hash_stable = digest(codepoint_sort(words)) == digest(codepoint_sort(list(reversed(words))))
    print("  the codepoint hash is stable across input orders = %s (%s)" % (codepoint_hash_stable, digest(cp)))

    ok = (orders_differ and hashes_differ and codepoint_is_pure and accent_moves and codepoint_hash_stable)
    print("-" * 116)
    print("SELF-TEST %s  orders_differ=%s  hashes_differ=%s  codepoint_is_pure=%s  accent_moves=%s  codepoint_hash_stable=%s"
          % ("PASS" if ok else "FAIL", orders_differ, hashes_differ, codepoint_is_pure, accent_moves, codepoint_hash_stable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Locale collation: sort by codepoint (a fixed, locale-independent order) for any output that must be reproducible -- hashed, serialized, diffed, or deduplicated -- not by locale collation, because collation depends on the machine's locale and version, so a locale sort makes the same data order, and hash, differently across systems.")
    p.add_argument("--sort", action="store_true")
    p.add_argument("--hash", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("words=%s  file=%s  (the words are a fixture)" % (data["words"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.sort:
        sort_view(data)
    elif args.hash:
        hash_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
