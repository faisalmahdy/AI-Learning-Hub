"""Compute a rate from a cumulative counter with reset-aware differences, not a plain subtraction -- when the process restarts the counter drops back to zero, so current minus previous goes negative, an impossible rate for a counter that only climbs, and any total summed from those deltas is short by the traffic that happened before the restart.

A cumulative counter -- requests_total, bytes_sent, errors_total -- only ever increases while a process runs. A monitoring system samples it every scrape interval and reports the per-interval increase as current minus previous. That is exactly right, until the process restarts.

On a restart the counter is re-created at zero. The next scrape reads a small value where the previous scrape read a large one, so current minus previous is a large NEGATIVE number. A counter cannot decrease, so a negative delta is not a real rate -- it is the arithmetic of subtracting the pre-restart total from the fresh post-restart value. On a dashboard it shows as a sharp downward spike or a nonsensical negative throughput, and worse, any total built by summing the deltas is short by roughly the pre-restart value, because that negative delta cancels real traffic.

The fix is to recognize the reset. A counter that reads smaller than it did a moment ago must have restarted, and after a restart the increase since the last scrape is the new reading itself -- the rise from zero -- not new minus old. So: if current is at least previous, the delta is current minus previous; if current is smaller, the counter reset and the delta is current. This is exactly what a monitoring system's rate() and increase() functions do internally.

On this fixture the counter climbs to 40, the process restarts, and it climbs again from 5 to 33. The plain difference produces a delta of 5 minus 40 = -35 and a window total of 23; the reset-aware difference replaces that -35 with 5 and totals 63, which matches the real in-window increase of (40 - 10) before the reset plus (33 - 0) after it. This computes both.

  --plain     the naive per-scrape difference: a negative delta at the reset and a total short by the pre-restart traffic
  --reset     the reset-aware difference: non-negative throughout, total equal to the real increase
  --check     the plain deltas include a negative value and a low total, while the reset-aware deltas are all non-negative and total the true in-window increase

the scrape readings are the fixture; every plain and reset-aware delta, both totals, and the reset detection are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "counterreset.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def plain_deltas(readings):
    """Per-scrape increase as current minus previous -- correct until the counter resets."""
    return [cur - prev for prev, cur in zip(readings, readings[1:])]


def reset_aware_deltas(readings):
    """Per-scrape increase, but a reading smaller than the last means a reset, so the increase is the new reading."""
    out = []
    for prev, cur in zip(readings, readings[1:]):
        out.append(cur - prev if cur >= prev else cur)
    return out


def true_increase(readings):
    """The real in-window increase: sum each rising run, and count a drop as a rise from zero."""
    total = 0
    for prev, cur in zip(readings, readings[1:]):
        total += (cur - prev) if cur >= prev else cur
    return total


# ----------------------------------------------------------------- printing

def _row(readings, deltas):
    for i, ((prev, cur), d) in enumerate(zip(zip(readings, readings[1:]), deltas)):
        mark = "   <- reset (reading dropped)" if cur < prev else ""
        print("  scrape %d->%d:  %3d -> %3d   delta %+d%s" % (i, i + 1, prev, cur, d, mark))


def plain_view(data):
    r = data["readings"]
    d = plain_deltas(r)
    print("PLAIN — per-scrape delta as current minus previous")
    print("-" * 64)
    _row(r, d)
    print("-" * 64)
    print("  total = %d   (a negative delta at the reset cancels real traffic)" % sum(d))


def reset_view(data):
    r = data["readings"]
    d = reset_aware_deltas(r)
    print("RESET-AWARE — a drop means a restart, so the delta is the new reading")
    print("-" * 64)
    _row(r, d)
    print("-" * 64)
    print("  total = %d   (matches the true in-window increase)" % sum(d))


def check(data):
    print("SELF-TEST — the plain deltas include a negative value and a low total, while the reset-aware deltas are all non-negative and total the true in-window increase")
    print("-" * 112)
    r = data["readings"]
    plain = plain_deltas(r)
    reset = reset_aware_deltas(r)
    truth = true_increase(r)

    plain_goes_negative = any(d < 0 for d in plain)
    print("  plain deltas include a negative (impossible for a counter) = %s (%s)" % (plain_goes_negative, plain))

    reset_all_nonneg = all(d >= 0 for d in reset)
    print("  reset-aware deltas are all non-negative = %s (%s)" % (reset_all_nonneg, reset))

    reset_detected = any(cur < prev for prev, cur in zip(r, r[1:]))
    print("  a reset was detected (a reading dropped) = %s" % reset_detected)

    reset_total_correct = sum(reset) == truth
    print("  reset-aware total equals the true in-window increase = %s (%d == %d)" % (reset_total_correct, sum(reset), truth))

    plain_total_undercounts = sum(plain) < truth
    print("  plain total undercounts the true increase = %s (%d < %d)" % (plain_total_undercounts, sum(plain), truth))

    ok = (plain_goes_negative and reset_all_nonneg and reset_detected
          and reset_total_correct and plain_total_undercounts)
    print("-" * 112)
    print("SELF-TEST %s  plain_goes_negative=%s  reset_all_nonneg=%s  reset_detected=%s  reset_total_correct=%s  plain_total_undercounts=%s"
          % ("PASS" if ok else "FAIL", plain_goes_negative, reset_all_nonneg, reset_detected,
             reset_total_correct, plain_total_undercounts))
    return ok


def main():
    p = argparse.ArgumentParser(description="Counter reset handling: compute a rate from a cumulative counter with reset-aware differences, because a process restart drops the counter to zero and a plain current-minus-previous goes negative -- an impossible rate that shows as a downward spike and makes any summed total short by the pre-restart traffic; when a reading is smaller than the last, treat the increase as the new reading (the rise from zero), which is what rate()/increase() do.")
    p.add_argument("--plain", action="store_true")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("readings=%s  scrapes=%d  file=%s" % (data["readings"], len(data["readings"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.plain:
        plain_view(data)
    elif args.reset:
        reset_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
