"""Multi-key sorting by successive single-key sorts relies on the sort being STABLE -- preserving the input order of records that tie -- and an unstable sort silently scrambles the secondary ordering while still getting the primary key right, so the bug is invisible unless you inspect the ties.

The standard way to sort by a primary key and then a secondary key, when your sort takes one key at a time, is two passes: sort by the secondary key first, then sort by the primary key. The trick works because of a property of the second sort called stability.

A stable sort preserves the relative order of records that compare equal on its key. So when the second pass sorts by the primary key, all the records that share a primary key keep the order the first pass gave them -- which was secondary-key order. The result is sorted by primary key, and within each primary group, by secondary key. Exactly what was wanted.

An unstable sort makes no such promise. It is free to place equal-key records in any order, so the second pass can reorder the records within a primary group however its internal mechanics happen to land -- discarding the secondary ordering the first pass so carefully built. The output is still correctly sorted by the primary key, because those keys differ; only the ties are scrambled. That is what makes it dangerous: the sort looks right at a glance and is wrong in the detail you used two passes to get.

On this fixture five employees are sorted by department then name. The stable two-pass sort leaves each department's names in ascending order. The unstable primary sort -- modeled here by breaking ties in reverse input order, a valid unstable behavior -- leaves each department's names reversed. Both put the departments in the right order; only the stable one keeps the names sorted within a department. This computes both.

  --stable    two passes with a stable primary sort: departments ordered, names ascending within each
  --unstable  two passes with an unstable primary sort: departments ordered, names scrambled within each
  --check     both order the primary key correctly, but only the stable sort keeps each group's secondary key in order

the records and the two keys are the fixture; both two-pass results and the per-group secondary ordering checks are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path
from itertools import groupby

HERE = Path(__file__).resolve().parent
DATA = HERE / "sortstable.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def stable_sort(items, key):
    """A stable sort: equal-key records keep their input order (Python's sorted is stable)."""
    return sorted(items, key=key)


def unstable_sort(items, key):
    """An unstable sort: equal-key records are reordered (here, into reverse input order)."""
    return [x for _idx, x in sorted(enumerate(items), key=lambda p: (key(p[1]), -p[0]))]


def two_pass(records, primary, secondary, primary_sort):
    """Sort by the secondary key (stably), then by the primary key with the given sort."""
    by_secondary = stable_sort(records, key=lambda r: r[secondary])
    return primary_sort(by_secondary, key=lambda r: r[primary])


def groups_in_order(records, primary, secondary):
    """For each primary group in the output, is its secondary key in ascending order?"""
    result = {}
    for k, grp in groupby(records, key=lambda r: r[primary]):
        names = [r[secondary] for r in grp]
        result[k] = (names, names == sorted(names))
    return result


# ----------------------------------------------------------------- printing

def _fmt(records, primary, secondary):
    return [(r[primary], r[secondary]) for r in records]


def _view(d, primary_sort, label, note):
    out = two_pass(d["records"], d["primary_key"], d["secondary_key"], primary_sort)
    print("%s — sorted by %s then %s" % (label, d["primary_key"], d["secondary_key"]))
    print("-" * 64)
    print("  result: %s" % _fmt(out, d["primary_key"], d["secondary_key"]))
    for k, (names, ok) in groups_in_order(out, d["primary_key"], d["secondary_key"]).items():
        print("  %-6s names %s  ordered=%s" % (k, names, ok))
    print("-" * 64)
    print("  %s" % note)


def stable_view(d):
    _view(d, stable_sort, "STABLE",
          "the primary sort kept the name order the first pass built, so names stay ascending")


def unstable_view(d):
    _view(d, unstable_sort, "UNSTABLE",
          "the primary sort reordered the ties, throwing away the name order the first pass built")


def check(d):
    print("SELF-TEST — both order the primary key correctly, but only the stable sort keeps each group's secondary key in order")
    print("-" * 112)
    primary, secondary = d["primary_key"], d["secondary_key"]

    st = two_pass(d["records"], primary, secondary, stable_sort)
    un = two_pass(d["records"], primary, secondary, unstable_sort)

    st_primary = [r[primary] for r in st]
    un_primary = [r[primary] for r in un]
    both_primary_sorted = st_primary == sorted(st_primary) and un_primary == sorted(un_primary)
    print("  both put the primary key in correct order = %s" % both_primary_sorted)

    st_groups = groups_in_order(st, primary, secondary)
    stable_keeps_secondary = all(ok for _names, ok in st_groups.values())
    print("  stable sort keeps every group's secondary key in order = %s (%s)" % (stable_keeps_secondary, {k: n for k, (n, _o) in st_groups.items()}))

    un_groups = groups_in_order(un, primary, secondary)
    unstable_breaks_secondary = any(not ok for _names, ok in un_groups.values())
    print("  unstable sort breaks some group's secondary order = %s (%s)" % (unstable_breaks_secondary, {k: n for k, (n, _o) in un_groups.items()}))

    same_primary_diff_ties = st_primary == un_primary and st != un
    print("  same primary order, different tie arrangement (the invisible part) = %s" % same_primary_diff_ties)

    ok = (both_primary_sorted and stable_keeps_secondary and unstable_breaks_secondary and same_primary_diff_ties)
    print("-" * 112)
    print("SELF-TEST %s  both_primary_sorted=%s  stable_keeps_secondary=%s  unstable_breaks_secondary=%s  same_primary_diff_ties=%s"
          % ("PASS" if ok else "FAIL", both_primary_sorted, stable_keeps_secondary, unstable_breaks_secondary, same_primary_diff_ties))
    return ok


def main():
    p = argparse.ArgumentParser(description="Sort stability: multi-key sorting by successive single-key sorts (sort by secondary, then by primary) is correct only if the primary sort is stable -- preserving the input order of records that tie on the primary key -- because a stable sort leaves tied records in the secondary order the first pass built, while an unstable sort reorders them and silently scrambles the secondary ordering, all while still sorting the primary key correctly so the bug hides in the ties.")
    p.add_argument("--stable", action="store_true")
    p.add_argument("--unstable", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("primary=%s  secondary=%s  records=%d  file=%s"
          % (d["primary_key"], d["secondary_key"], len(d["records"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.stable:
        stable_view(d)
    elif args.unstable:
        unstable_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
