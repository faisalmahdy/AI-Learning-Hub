"""Diff the eval item by item, or a higher aggregate score hides the cases the new model broke.

You ship a new model version, run the eval, and the score went up: 7 of 10 versus 5 of 10. Green light.
That single number is a sum, and a sum cannot tell you HOW it changed -- only THAT it did. The new model
could have fixed three cases and broken one, or fixed four and broken two; both net to the same or similar
aggregate, and both look like progress. But a broken case is a regression: something that used to work now
fails, and if it is a case that matters -- a safety refusal, a billing calculation -- a net-positive release
can still be a release you must not ship. The aggregate averages the regression away with the wins.

The fix is to diff the eval at the item level, not compare the totals. Line up each case's old and new
result and count the four cells: still-pass, still-fail, FIXED (fail to pass), and REGRESSED (pass to fail).
The net change equals fixes minus regressions -- so the aggregate is just those two numbers collapsed into
one, throwing away exactly the distinction you need. With the item diff you can gate the release on "zero
regressions on critical cases" no matter how good the aggregate looks.

On this fixture the old model passes 5 of 10 and the new one passes 7 -- a clean +2. The item diff shows
three fixes and one regression: the new model broke safety_refusal, a case the old model handled. The
aggregate said nothing but "better." This computes both.

  --scores     the aggregate pass counts for old and new, and the net change
  --diff       the item-level confusion: fixed, regressed, and unchanged cases by name
  --check      the aggregate improves while a real regression hides inside it

The per-item results are the fixture; every count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "results.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def score(items, key):
    return sum(it[key] for it in items)


def fixed(items):
    """Cases the old model failed and the new model passed."""
    return [it["name"] for it in items if it["a"] == 0 and it["b"] == 1]


def regressed(items):
    """Cases the old model passed and the new model failed -- the ones the aggregate hides."""
    return [it["name"] for it in items if it["a"] == 1 and it["b"] == 0]


# ----------------------------------------------------------------- printing

def scores_view(data):
    items = data["items"]
    a, b = score(items, "a"), score(items, "b")
    n = len(items)
    print("SCORES — aggregate pass counts (%d cases)" % n)
    print("-" * 58)
    print("  old model: %d / %d" % (a, n))
    print("  new model: %d / %d" % (b, n))
    print("  net change: %+d" % (b - a))
    print("-" * 58)
    print("  the total went up; the total cannot say what moved.")


def diff_view(data):
    items = data["items"]
    f, r = fixed(items), regressed(items)
    still_pass = [it["name"] for it in items if it["a"] == 1 and it["b"] == 1]
    still_fail = [it["name"] for it in items if it["a"] == 0 and it["b"] == 0]
    print("DIFF — item-level confusion between old and new")
    print("-" * 58)
    print("  fixed     (fail->pass): %d  %s" % (len(f), f))
    print("  REGRESSED (pass->fail): %d  %s" % (len(r), r))
    print("  still pass:             %d" % len(still_pass))
    print("  still fail:             %d" % len(still_fail))
    print("-" * 58)
    print("  net %+d = %d fixed - %d regressed" % (len(f) - len(r), len(f), len(r)))


def check(data):
    print("SELF-TEST — the aggregate improves while a real regression hides inside it")
    print("-" * 96)
    items = data["items"]
    a, b = score(items, "a"), score(items, "b")
    f, r = fixed(items), regressed(items)

    aggregate_improved = b > a
    print("  the aggregate score improved = %s (%d -> %d, %+d)" % (aggregate_improved, a, b, b - a))

    regressions_exist = len(r) > 0
    print("  at least one case regressed = %s (%s)" % (regressions_exist, r))

    aggregate_hides_regressions = aggregate_improved and regressions_exist
    print("  a positive aggregate hides a regression = %s" % aggregate_hides_regressions)

    net_equals_fixes_minus_regressions = (b - a) == (len(f) - len(r))
    print("  net change = fixes - regressions = %s (%+d = %d - %d)" % (net_equals_fixes_minus_regressions, b - a, len(f), len(r)))

    regression_invisible_in_total = (b - a) > 0 and len(r) > 0 and (b - a) < len(f)
    print("  the total understates the fixes because a regression cancels one = %s (net %+d < %d fixed)"
          % (regression_invisible_in_total, b - a, len(f)))

    ok = aggregate_improved and regressions_exist and aggregate_hides_regressions and net_equals_fixes_minus_regressions and regression_invisible_in_total
    print("-" * 96)
    print("SELF-TEST %s  aggregate_improved=%s  regressions_exist=%s  aggregate_hides_regressions=%s  net_equals_fixes_minus_regressions=%s  regression_invisible_in_total=%s"
          % ("PASS" if ok else "FAIL", aggregate_improved, regressions_exist, aggregate_hides_regressions, net_equals_fixes_minus_regressions, regression_invisible_in_total))
    return ok


def main():
    p = argparse.ArgumentParser(description="Diff an eval item by item so a higher aggregate cannot hide a regression.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--diff", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cases=%d  file=%s  (the per-item results are a fixture)" % (len(data["items"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.diff:
        diff_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
