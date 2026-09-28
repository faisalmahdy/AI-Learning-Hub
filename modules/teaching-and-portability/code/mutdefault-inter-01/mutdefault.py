"""A mutable default argument is created once at def time and shared by every call -- so it accumulates instead of resetting.

Python evaluates a function's default argument values ONCE, at the moment the `def` statement runs, not each time the
function is called. For an immutable default like 0 or None that distinction never shows, because you cannot change the
value in place. For a MUTABLE default -- a list, a dict, a set -- it is a trap: the single object created when the
function was defined becomes the default for every call that omits the argument, and if the body mutates it (appends to
the list, adds to the dict), the change persists into the next call. So `def add(item, bucket=[])` does not give each
call a fresh empty list; it gives every call the SAME list, which fills up across calls. The function that looks like it
starts from empty each time is quietly accumulating state between invocations, and the bug surfaces as 'why does the
second call already contain the first call's data?' -- often far from the definition, and often only in production where
the function is called more than once.

The cause is that the default value is an attribute of the function object (stored in its __defaults__), fixed when the
function is created. `bucket=[]` runs the `[]` exactly once and binds that list as the default forever; calling the
function without a bucket reuses that same bound list. The fix is the standard sentinel: default the argument to None --
an immutable, safe default -- and create the fresh mutable object INSIDE the body when the argument is None. Now each
call that omits the argument builds its own new list, and the shared-state bug is gone. The rule is simple and absolute:
never use a mutable object as a default argument value; default to None and construct inside.

On this fixture three items are appended one per call, each call omitting the bucket. The buggy version (default []) shares
one list, so the calls return ['a'], then ['a','b'], then ['a','b','c'] -- the same object, growing. The fixed version
(default None, list built inside) returns ['a'], then ['b'], then ['c'] -- a fresh list each time. This computes both.

  --buggy   append three items through the mutable-default function -- the list accumulates across calls
  --fixed   append the same three through the None-sentinel function -- each call gets a fresh list
  --check   the buggy default is one shared object that accumulates; the fixed version resets; the default is mutated in place

The items are the fixture; every call result is computed by running the two functions. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "mutdefault.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def make_buggy():
    """A collector with a MUTABLE default -- the [] is evaluated once at def time and shared by every call."""
    def add(item, bucket=[]):
        bucket.append(item)
        return bucket
    return add


def make_fixed():
    """The same collector with the None-sentinel fix -- a fresh list is built inside the body per call."""
    def add(item, bucket=None):
        if bucket is None:
            bucket = []
        bucket.append(item)
        return bucket
    return add


def run(add, items):
    """Call add once per item, omitting the bucket, and snapshot the result after each call."""
    return [list(add(item)) for item in items]


# ----------------------------------------------------------------- printing

def buggy_view(data):
    items = data["items"]
    print("BUGGY — def add(item, bucket=[]): the default list is shared across calls")
    print("-" * 62)
    add = make_buggy()
    for item, result in zip(items, run(add, items)):
        print("  add(%r)  -> %s" % (item, result))
    print("-" * 62)
    print("  each call reused the SAME default list, so it accumulated to %s." % run(make_buggy(), items)[-1])


def fixed_view(data):
    items = data["items"]
    print("FIXED — def add(item, bucket=None): build a fresh list inside when None")
    print("-" * 62)
    add = make_fixed()
    for item, result in zip(items, run(add, items)):
        print("  add(%r)  -> %s" % (item, result))
    print("-" * 62)
    print("  each call built its own list, so every result is a fresh single-item list.")


def check(data):
    print("SELF-TEST — the buggy default is one shared object that accumulates; the fixed version resets; the default is mutated in place")
    print("-" * 124)
    items = data["items"]

    buggy_results = run(make_buggy(), items)
    buggy_accumulates = buggy_results == [["a"], ["a", "b"], ["a", "b", "c"]]
    print("  the buggy function accumulates across calls = %s (%s)" % (buggy_accumulates, buggy_results))

    fixed_results = run(make_fixed(), items)
    fixed_resets = fixed_results == [["a"], ["b"], ["c"]]
    print("  the fixed function resets each call = %s (%s)" % (fixed_resets, fixed_results))

    b = make_buggy()
    r1, r2 = b("x"), b("y")
    buggy_same_object = r1 is r2
    print("  the buggy calls return the SAME list object = %s" % buggy_same_object)

    f = make_fixed()
    s1, s2 = f("x"), f("y")
    fixed_fresh_object = s1 is not s2
    print("  the fixed calls return DIFFERENT list objects = %s" % fixed_fresh_object)

    d = make_buggy()
    default_before = d.__defaults__[0]
    d("z")
    default_after = d.__defaults__[0]
    default_mutated = default_before is default_after and default_after == ["z"]
    print("  the default stored on the function is mutated in place = %s (__defaults__[0] = %s)" % (default_mutated, default_after))

    ok = buggy_accumulates and fixed_resets and buggy_same_object and fixed_fresh_object and default_mutated
    print("-" * 124)
    print("SELF-TEST %s  buggy_accumulates=%s  fixed_resets=%s  buggy_same_object=%s  fixed_fresh_object=%s  default_mutated=%s"
          % ("PASS" if ok else "FAIL", buggy_accumulates, fixed_resets, buggy_same_object, fixed_fresh_object, default_mutated))
    return ok


def main():
    p = argparse.ArgumentParser(description="Mutable default argument: a default like bucket=[] is evaluated once at def time and shared by every call that omits the argument, so mutating it accumulates state across calls; default to None and construct the mutable object inside the body instead.")
    p.add_argument("--buggy", action="store_true")
    p.add_argument("--fixed", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("items=%s  file=%s  (the items are a fixture; the bug is in how defaults are evaluated)"
          % (data["items"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.buggy:
        buggy_view(data)
    elif args.fixed:
        fixed_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
