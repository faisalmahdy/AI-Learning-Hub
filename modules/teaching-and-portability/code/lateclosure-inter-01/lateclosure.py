"""Bind the loop variable at definition time -- a closure created in a loop captures the variable, not its value, so they all see the last one.

Building a function inside a loop is routine: a click handler per button, a callback per row, a small function per item in a list. Each one refers to the loop variable to know which item it belongs to. And every one of them ends up belonging to the SAME item -- the last one -- because a closure does not snapshot the loop variable when it is created; it captures the variable itself, a live reference. When the loop finishes, that variable holds its final value, and since all the closures point at the same variable, they all read the final value when called. You built N functions expecting N different behaviors and got N copies of the last one.

The trap is precise and worth stating exactly: closing over a variable captures the variable, not a snapshot of its value at capture time. So the value a closure sees is whatever the variable holds WHEN THE CLOSURE RUNS, not when it was defined. In a loop, all iterations reuse one loop variable, so every closure shares it, and by the time any closure runs the loop has advanced the variable to its last value. Nothing is wrong with any single closure; the mistake is expecting each to have frozen its own copy of the loop variable, which closures do not do.

The fix is to bind the value at definition time instead of referring to the shared variable. The idiom in Python is a default argument: a parameter whose default is the current loop value. Default arguments are evaluated once, at the moment the function is defined, so each closure's default captures that iteration's value and stores it in the function itself -- independent of the shared loop variable. Now each closure returns its own item. (Other languages solve the same trap the same way: a fresh binding per iteration -- JavaScript's `let` instead of `var`, or an immediately-invoked function that takes the value as an argument.)

The rule: when creating closures in a loop, bind the loop value at definition time -- e.g. as a default argument -- rather than referring to the loop variable directly, because a closure captures the variable, not its value, so all closures share the one loop variable and read its final value when they run, making every closure behave as if it belonged to the last iteration.

On this fixture three closures are built over items 'a','b','c', each meant to return its own item. The naive closures all return 'c' (the last item), because they share the loop variable; the default-argument closures return 'a','b','c', because each captured its value at definition. This computes both by actually building and calling the closures.

  --naive    the closures that refer to the loop variable directly, and what each returns
  --fixed    the closures that bind the value as a default argument, and what each returns
  --check    the naive closures all return the last item; the default-argument closures return their own

items is the fixture; the naive and fixed closure results are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lateclosure.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def build_naive(items):
    """Each closure refers to the loop variable `item` directly -- they all share it."""
    return [lambda: item for item in items]


def build_fixed(items):
    """Each closure binds the current value as a default argument -- captured at definition."""
    return [lambda item=item: item for item in items]


def results(closures):
    """Call every closure and collect what it returns."""
    return [c() for c in closures]


# ----------------------------------------------------------------- printing

def naive_view(data):
    items = data["items"]
    res = results(build_naive(items))
    print("NAIVE — closures that refer to the loop variable directly")
    print("-" * 56)
    print("  items            = %s" % items)
    print("  closure results  = %s" % res)
    print("-" * 56)
    print("  every closure returned '%s' (the last item) -- they share the loop variable" % res[-1])


def fixed_view(data):
    items = data["items"]
    res = results(build_fixed(items))
    print("FIXED — closures that bind the value as a default argument")
    print("-" * 56)
    print("  items            = %s" % items)
    print("  closure results  = %s" % res)
    print("-" * 56)
    print("  each closure returned its own item -- the default captured the value at definition")


def check(data):
    print("SELF-TEST — the naive closures all return the last item; the default-argument closures return their own")
    print("-" * 112)
    items = data["items"]
    naive = results(build_naive(items))
    fixed = results(build_fixed(items))

    naive_all_same = len(set(naive)) == 1
    print("  the naive closures all return the same value = %s (%s)" % (naive_all_same, naive))

    naive_all_last = all(r == items[-1] for r in naive)
    print("  that value is the LAST item = %s ('%s')" % (naive_all_last, items[-1]))

    naive_not_distinct = naive != items
    print("  the naive results do NOT match the items = %s (%s != %s)" % (naive_not_distinct, naive, items))

    fixed_matches_items = fixed == items
    print("  the default-argument closures return their own items = %s (%s)" % (fixed_matches_items, fixed))

    fixed_distinct = len(set(fixed)) == len(items)
    print("  the fixed results are all distinct (one per closure) = %s" % fixed_distinct)

    same_loop_different_binding = naive != fixed
    print("  same loop, different binding, different behavior = %s" % same_loop_different_binding)

    ok = naive_all_same and naive_all_last and naive_not_distinct and fixed_matches_items and fixed_distinct and same_loop_different_binding
    print("-" * 112)
    print("SELF-TEST %s  naive_all_same=%s  naive_all_last=%s  naive_not_distinct=%s  fixed_matches_items=%s  fixed_distinct=%s  same_loop_different_binding=%s"
          % ("PASS" if ok else "FAIL", naive_all_same, naive_all_last, naive_not_distinct, fixed_matches_items, fixed_distinct, same_loop_different_binding))
    return ok


def main():
    p = argparse.ArgumentParser(description="Late-binding closures: when creating closures in a loop, bind the loop value at definition time (e.g. as a default argument) rather than referring to the loop variable directly, because a closure captures the variable, not its value, so all closures share the one loop variable and read its final value when they run, making every closure behave as if it belonged to the last iteration.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--fixed", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("items=%s  file=%s  (the items looped over are a fixture)" % (data["items"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.fixed:
        fixed_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
