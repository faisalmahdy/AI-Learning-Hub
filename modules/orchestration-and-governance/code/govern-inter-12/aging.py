"""Age waiting tasks up in priority, or a strict priority queue starves the low-priority work forever.

A priority queue that always serves the highest-priority task first is correct for urgency and catastrophic
for fairness. If high-priority work keeps arriving -- and under load it does -- the queue always has
something more urgent than the low-priority task waiting at the back, so that task is never chosen. It does
not fail; it waits, forever, while the system stays busy serving a stream of higher-priority work. This is
starvation, and it is the default behavior of strict priority scheduling under sustained load.

The fix is aging: let a task's EFFECTIVE priority rise with how long it has waited. A low-priority task that
has waited long enough eventually out-prioritizes a freshly-arrived high-priority task and gets served, so
no task waits unboundedly. Urgency still wins in the short run -- a new high-priority task is served ahead
of a low one that just arrived -- but the longer the low task waits, the more its accumulated age closes the
gap, guaranteeing it a turn. You trade a little promptness on high-priority work for a bound on how long
anything can be starved.

On this fixture a high-priority task (priority 5) arrives every tick and one low-priority task L (priority 1)
arrives at tick 0; the server completes one task per tick. Under strict priority, L is never the highest and
is never served in the 12-tick horizon -- starved. Under aging, L's priority climbs by its wait time, passes
5 after waiting long enough, and it is served at tick 4. This runs both schedulers.

  --queue      the arrival stream and the two scheduling policies
  --schedule   the order each policy serves, and when (or whether) the low task L is served
  --check      strict priority starves L; aging serves it within a bounded wait

The arrival stream and horizon are the fixture; every scheduling decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "queue.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def effective_priority(task, now, aging):
    """Base priority, plus wait time if aging is on -- a long wait lifts a low task above a fresh high one."""
    wait = now - task["arrival"]
    return task["priority"] + (wait if aging else 0)


def schedule(data, aging):
    """Serve one task per tick, picking the highest effective priority (ties: earliest arrival). Returns the served order."""
    pending = []
    arrivals = {}
    for tk in data["tasks"]:
        arrivals.setdefault(tk["arrival"], []).append(tk)
    served = []
    for now in range(data["horizon"]):
        pending.extend(arrivals.get(now, []))
        if not pending:
            continue
        pending.sort(key=lambda tk: (-effective_priority(tk, now, aging), tk["arrival"], tk["id"]))
        served.append((now, pending.pop(0)["id"]))
    return served


def served_tick(order, task_id):
    for tick, tid in order:
        if tid == task_id:
            return tick
    return None


# ----------------------------------------------------------------- printing

def queue_view(data):
    print("QUEUE — %d ticks, one task served per tick" % data["horizon"])
    print("-" * 54)
    highs = [t for t in data["tasks"] if t["priority"] >= 5]
    lows = [t for t in data["tasks"] if t["priority"] < 5]
    print("  a priority-%d task arrives every tick (%d of them)" % (highs[0]["priority"], len(highs)))
    print("  one priority-%d task 'L' arrives at tick %d" % (lows[0]["priority"], lows[0]["arrival"]))
    print("-" * 54)
    print("  with something urgent always arriving, does L ever get served?")


def schedule_view(data):
    strict = schedule(data, aging=False)
    aged = schedule(data, aging=True)
    print("SCHEDULE — served order, strict priority vs aging")
    print("-" * 58)
    print("  strict: %s" % " ".join(tid for _, tid in strict))
    print("    L served at: %s" % (served_tick(strict, "L") if served_tick(strict, "L") is not None else "NEVER (starved)"))
    print("  aging:  %s" % " ".join(tid for _, tid in aged))
    print("    L served at: tick %s" % served_tick(aged, "L"))
    print("-" * 58)
    print("  strict never reaches L; aging lifts it above the fresh high-priority tasks in time.")


def check(data):
    print("SELF-TEST — strict priority starves L; aging serves it within a bounded wait")
    print("-" * 84)
    strict = schedule(data, aging=False)
    aged = schedule(data, aging=True)

    strict_starves = served_tick(strict, "L") is None
    print("  strict priority never serves L in the horizon = %s" % strict_starves)

    aging_serves = served_tick(aged, "L") is not None
    print("  aging serves L = %s (tick %s)" % (aging_serves, served_tick(aged, "L")))

    wait = served_tick(aged, "L")
    bounded_wait = wait is not None and wait < data["horizon"]
    print("  L's wait under aging is bounded (below the horizon) = %s (%s < %d)" % (bounded_wait, wait, data["horizon"]))

    high_still_prompt = served_tick(aged, "H00") is not None and served_tick(aged, "H00") <= 1
    print("  aging still serves an early high-priority task promptly = %s (H00 at tick %s)"
          % (high_still_prompt, served_tick(aged, "H00")))

    ok = strict_starves and aging_serves and bounded_wait and high_still_prompt
    print("-" * 84)
    print("SELF-TEST %s  strict_starves=%s  aging_serves=%s  bounded_wait=%s  high_still_prompt=%s"
          % ("PASS" if ok else "FAIL", strict_starves, aging_serves, bounded_wait, high_still_prompt))
    return ok


def main():
    p = argparse.ArgumentParser(description="Age waiting tasks up in priority to prevent starvation.")
    p.add_argument("--queue", action="store_true")
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tasks=%d  horizon=%d  file=%s  (the arrival stream is a fixture)"
          % (len(data["tasks"]), data["horizon"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.queue:
        queue_view(data)
    elif args.schedule:
        schedule_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
