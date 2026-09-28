#!/usr/bin/env python3
"""Learned means a dated recall pass, not a checkmark -- and a pass decays.

A curriculum tracks progress, and the easy metric is "modules authored" or
"modules read". Both overcount learning: authoring a module is the teacher's
work, not the learner's, and reading it is not remembering it. The honest metric
is a dated, closed-book RECALL pass -- and even that decays, so a pass from four
months ago is not current mastery. This reads a recall ledger and reports what is
actually retained now versus what merely looks done, the exact gap the labs' own
recall gate has (its ledger, the scan notes, has zero dated passes).

  --ledger        every module: authored, its recall-pass dates, and retained-now
  --progress      authored-count vs retained-count -- the overcount, measured
  --stale         modules whose last pass has decayed past the retention window
  --check         authored overcounts retained; a never-tested and a stale module are not retained

Stdlib only. 'now' is a fixed day number so the whole thing is deterministic and
offline. The ledger is a fixture. Point it at your own recall ledger.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "ledger.json"

WINDOW = 60      # a recall pass older than this many days no longer counts as retained


def load():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    return data["now"], data["modules"]


# ------------------------------------------------------------- the status rules

def authored(m):
    """The teacher's checkmark: the module exists and is marked ready."""
    return m["status"] == "ready"


def last_pass(m):
    """The most recent recall-pass day, or None if never passed."""
    return max(m["passes"]) if m["passes"] else None


def retained(now, m):
    """The honest status: a recall pass exists AND is within the retention window,
    so the learner can still reproduce it today -- not just once, long ago."""
    lp = last_pass(m)
    return lp is not None and (now - lp) <= WINDOW


# ---------------------------------------------------------------- the measurement

def counts(now, modules):
    a = sum(1 for m in modules if authored(m))
    r = sum(1 for m in modules if retained(now, m))
    return a, r


def stale(now, modules):
    """Authored modules whose last pass has decayed past the window (need a refresh)."""
    return [m["id"] for m in modules
            if authored(m) and last_pass(m) is not None and (now - last_pass(m)) > WINDOW]


def never_tested(modules):
    """Authored modules with no recall pass at all -- 'done' but never assessed."""
    return [m["id"] for m in modules if authored(m) and not m["passes"]]


# ------------------------------------------------------------------- printing

def ledger_view(now, modules):
    print("LEDGER — authored vs recall-passed vs retained-now   (now=day %d, window=%dd)" % (now, WINDOW))
    print("-" * 66)
    print("  module         authored  last-pass  age   retained")
    for m in modules:
        lp = last_pass(m)
        age = "%d" % (now - lp) if lp is not None else "-"
        print("  %-13s  %-8s  %-9s  %-4s  %s"
              % (m["id"], "yes" if authored(m) else "DRAFT", lp if lp is not None else "never",
                 age, "yes" if retained(now, m) else "no"))
    print("-" * 66)
    print("  authored is the teacher's checkmark; retained is the learner's -- a")
    print("  dated pass that has not yet decayed. They are not the same column.")


def progress_view(now, modules):
    a, r = counts(now, modules)
    n = len(modules)
    print("PROGRESS — what looks done vs what is retained")
    print("-" * 66)
    print("  authored (looks done)   %d/%d" % (a, n))
    print("  retained (really done)  %d/%d" % (r, n))
    print("-" * 66)
    print("  the gap of %d is unearned progress: modules marked done that the learner" % (a - r))
    print("  cannot currently reproduce closed-book -- never tested, or gone stale.")


def stale_view(now, modules):
    print("STALE & UNTESTED — authored modules that are not retained")
    print("-" * 66)
    st, nt = stale(now, modules), never_tested(modules)
    for mid in nt:
        print("  %-13s never passed a recall check" % mid)
    for mid in st:
        m = next(x for x in modules if x["id"] == mid)
        print("  %-13s last pass day %d, %d days ago -> decayed" % (mid, last_pass(m), now - last_pass(m)))
    print("-" * 66)
    print("  each of these needs a fresh closed-book pass before it counts as learned.")


def check(now, modules):
    print("SELF-TEST — authored overcounts retained; stale and untested do not count")
    print("-" * 66)
    a, r = counts(now, modules)
    print("  authored=%d  retained=%d" % (a, r))

    overcounts = a > r
    print("  authored count overstates retained learning = %s (%d > %d)" % (overcounts, a, r))

    nt = never_tested(modules)
    st = stale(now, modules)
    print("  authored-but-never-tested modules = %s" % nt)
    print("  authored-but-stale modules = %s" % st)
    untested_excluded = all(not retained(now, next(m for m in modules if m["id"] == i)) for i in nt)
    stale_excluded = all(not retained(now, next(m for m in modules if m["id"] == i)) for i in st)
    print("  never-tested modules are not retained = %s" % untested_excluded)
    print("  stale modules are not retained = %s" % stale_excluded)

    # a fresh pass flips a module to retained; a draft never counts.
    fresh = [m for m in modules if retained(now, m)]
    all_fresh_recent = all((now - last_pass(m)) <= WINDOW for m in fresh)
    draft_excluded = all(not retained(now, m) for m in modules if not authored(m))
    print("  every retained module has a within-window pass = %s" % all_fresh_recent)
    print("  a draft module is never retained = %s" % draft_excluded)

    ok = overcounts and untested_excluded and stale_excluded and all_fresh_recent and draft_excluded and len(nt) > 0 and len(st) > 0
    print("-" * 66)
    print("SELF-TEST %s  overcounts=%s  untested_out=%s  stale_out=%s  fresh_ok=%s  draft_out=%s"
          % ("PASS" if ok else "FAIL", overcounts, untested_excluded, stale_excluded, all_fresh_recent, draft_excluded))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retention-based progress from a recall ledger.")
    p.add_argument("--ledger", action="store_true")
    p.add_argument("--progress", action="store_true")
    p.add_argument("--stale", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    now, modules = load()
    print("modules=%d  now=day %d  window=%dd  file=%s  (ledger is a fixture)"
          % (len(modules), now, WINDOW, LEDGER.name))
    print("")

    if args.check:
        return 0 if check(now, modules) else 1
    if args.ledger:
        ledger_view(now, modules)
    elif args.progress:
        progress_view(now, modules)
    elif args.stale:
        stale_view(now, modules)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
