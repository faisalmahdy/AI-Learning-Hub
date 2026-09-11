#!/usr/bin/env python3
"""The rebuild-then-diff gate: a generated file must be byte-reproducible, or CI is blind.

A committed file that is generated from source (an index, a lockfile, a rendered
doc) is only trustworthy if rebuilding it from the same source gives the same
bytes. The classic CI gate is 'rebuild, then git diff --exit-code': if the rebuild
matches what is committed, the artifact is honest; if not, either someone
hand-edited the generated file or the generator is non-deterministic. And a
generator that stamps the build time into its output fails this gate on every run
for no real change, so teams disable the gate -- and then a real hand-edit sails
through. This builds a generator two ways and measures reproducibility.

  --build [now]   render the artifact deterministically and with a build timestamp
  --repro         build twice at different clock times; are the bytes identical?
  --drift         rebuild vs the committed artifact; catch a hand-edit
  --check         the timestamped build is not reproducible; the deterministic one is

Stdlib only. No network. 'now' is passed in to simulate two CI runs at different
times, so the whole thing is deterministic and offline. The source is a fixture.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source.json"


def load():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    return data["items"], data["committed"]


# --------------------------------------------------------------- the generator

def build(items, deterministic, now=0):
    """Render the index. Deterministic: sort the items, no timestamp -- same source,
    same bytes. Non-deterministic: stamp the build time, so every run differs."""
    lines = ["# generated index"]
    if not deterministic:
        lines.append("# built at %d" % now)          # <- the reproducibility killer
    order = sorted(items) if deterministic else items
    for name in order:
        lines.append("- %s" % name)
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------- the gate

def reproducible(items, deterministic):
    """The heart of the gate: build the same source twice (here, at two clock
    times) and check the bytes are identical."""
    a = build(items, deterministic, now=1000)
    b = build(items, deterministic, now=2000)
    return a == b, a, b


def diff(expected, actual):
    """Return the first differing line pair, or None if identical."""
    e, a = expected.splitlines(), actual.splitlines()
    for i in range(max(len(e), len(a))):
        le = e[i] if i < len(e) else "(missing)"
        la = a[i] if i < len(a) else "(missing)"
        if le != la:
            return i + 1, le, la
    return None


# ------------------------------------------------------------------- printing

def build_view(items, now):
    print("BUILD — deterministic vs timestamped")
    print("-" * 60)
    print("  deterministic:")
    for ln in build(items, True).splitlines():
        print("    " + ln)
    print("  timestamped (now=%d):" % now)
    for ln in build(items, False, now).splitlines():
        print("    " + ln)
    print("-" * 60)
    print("  the timestamp line is real source-independent noise: it changes with")
    print("  the clock, not with the data the file is supposed to represent.")


def repro_view(items):
    print("REPRODUCIBILITY — build twice at different clock times, compare bytes")
    print("-" * 60)
    for label, det in (("timestamped (bug)", False), ("deterministic (fix)", True)):
        same, a, b = reproducible(items, det)
        print("  %-22s two builds identical = %s" % (label, same))
        if not same:
            d = diff(a, b)
            print("      first difference at line %d: %r vs %r" % d)
    print("-" * 60)
    print("  a gate on the timestamped build fails every run for no real change;")
    print("  teams then switch the gate off, and real drift walks in behind it.")


def drift_view(items, committed):
    print("DRIFT — rebuild (deterministic) vs the committed artifact")
    print("-" * 60)
    rebuilt = build(items, True)
    d = diff(rebuilt, committed)
    if d is None:
        print("  committed matches the rebuild: no drift.")
    else:
        line, exp, act = d
        print("  MISMATCH at line %d:" % line)
        print("    rebuild   : %r" % exp)
        print("    committed : %r" % act)
        print("  the committed file was hand-edited; the gate rejects it.")
    print("-" * 60)


def check(items, committed):
    print("SELF-TEST — timestamped build is not reproducible; deterministic one is")
    print("-" * 60)

    ts_same, _, _ = reproducible(items, False)
    det_same, _, _ = reproducible(items, True)
    print("  timestamped build reproducible = %s   deterministic build reproducible = %s"
          % (ts_same, det_same))
    ts_bug = ts_same is False
    det_ok = det_same is True

    # the deterministic build is stable no matter the clock.
    stable = build(items, True, now=1) == build(items, True, now=9999)
    print("  deterministic build ignores the clock = %s" % stable)

    # the gate catches the hand-edit in the committed fixture.
    drift = diff(build(items, True), committed)
    caught = drift is not None
    print("  rebuild-vs-committed catches the hand-edit = %s (line %s)"
          % (caught, drift[0] if drift else "-"))

    # sorting makes the output order-independent of the source listing order.
    shuffled = list(reversed(items))
    order_free = build(items, True) == build(shuffled, True)
    print("  deterministic build is independent of source order = %s" % order_free)

    ok = ts_bug and det_ok and stable and caught and order_free
    print("-" * 60)
    print("SELF-TEST %s  ts_not_repro=%s  det_repro=%s  clock_free=%s  drift_caught=%s  order_free=%s"
          % ("PASS" if ok else "FAIL", ts_bug, det_ok, stable, caught, order_free))
    return ok


def main():
    p = argparse.ArgumentParser(description="A rebuild-then-diff reproducibility gate.")
    p.add_argument("--build", nargs="?", const=1000, type=int, metavar="NOW")
    p.add_argument("--repro", action="store_true")
    p.add_argument("--drift", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    items, committed = load()
    print("items=%d  file=%s  (source is a fixture)" % (len(items), SOURCE.name))
    print("")

    if args.check:
        return 0 if check(items, committed) else 1
    if args.build is not None:
        build_view(items, args.build)
    elif args.repro:
        repro_view(items)
    elif args.drift:
        drift_view(items, committed)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
