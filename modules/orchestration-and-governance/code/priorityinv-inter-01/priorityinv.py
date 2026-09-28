"""Let a lock-holder inherit the priority of the task waiting on it (priority inheritance) -- without it, an unrelated medium-priority task preempts the low-priority holder and a high-priority task is stuck behind it.

A preemptive scheduler runs the highest-priority runnable task at every instant, which is exactly what you want -- until a shared lock is involved. Suppose a low-priority task L holds a lock that a high-priority task H needs. H must wait for L to release it. That direct wait is unavoidable and bounded by L's critical section: H is blocked by L only for as long as L holds the lock, which is a cost you can reason about.

The pathology comes from a third, unrelated task. A medium-priority task M that needs no lock becomes runnable while L holds the lock. Because M outranks L, the scheduler preempts L to run M -- and while M runs, L cannot make progress, so it cannot release the lock, so H stays blocked. H outranks M, yet H is now waiting behind M for as long as M chooses to run. A high-priority task has been delayed by a lower-priority one it has no dependency on, through the lock it does not even know M is unrelated to. This is priority inversion, and the duration is unbounded: any number of medium-priority tasks can keep preempting L while H waits.

Priority inheritance closes it with a small rule: while L holds a lock that a higher-priority task is blocked on, L temporarily inherits that waiter's priority. Now L is effectively high-priority for the duration of the critical section, so M -- which is lower than H -- can no longer preempt it. L runs its critical section to completion, releases the lock, drops back to its own priority, and H proceeds. The high-priority task waits only for the critical section it actually depends on, never for the unrelated medium task.

The rule: have a lock-holder inherit the priority of the highest-priority task waiting on that lock (priority inheritance), because otherwise a medium-priority task preempts the low-priority holder and blocks the high-priority waiter behind it for an unbounded time -- inheritance bounds the wait to the critical section the high-priority task actually depends on.

On this fixture H needs a lock held by low-priority L, and medium-priority M needs no lock. Without inheritance, M preempts L and H waits 16 units; with inheritance, M cannot preempt L and H waits 6 -- the 10-unit difference is exactly M's work, which never should have delayed H. This computes both.

  --schedule   which task runs at each tick, under no-inheritance vs priority-inheritance
  --wait       H's lock-acquisition time and wait under each policy, and the inversion cost
  --check      without inheritance a medium task delays the high-priority task; inheritance bounds the wait to the critical section

tasks is the fixture; H's wait under each policy is computed by simulation. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "priorityinv.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def simulate(tasks, inherit, horizon=200):
    """Preemptive priority scheduling with one shared lock. Returns (H_acquire_time, trace of runner per tick)."""
    rem = {k: v["work"] for k, v in tasks.items()}
    done, waiting = set(), []
    lock_holder = None
    h_acquire = None
    trace = []
    for t in range(horizon):
        if len(done) == len(tasks):
            break
        runnable = []
        for k, v in tasks.items():
            if k in done or t < v["arrive"]:
                continue
            if v["needs_lock"]:
                if lock_holder == k or lock_holder is None:
                    runnable.append(k)
                elif k not in waiting:
                    waiting.append(k)          # blocked on the lock
            else:
                runnable.append(k)

        def effective_priority(k):
            p = tasks[k]["priority"]
            if inherit and lock_holder == k and waiting:
                p = max(p, max(tasks[w]["priority"] for w in waiting))
            return p

        if not runnable:
            trace.append((t, None))
            continue
        cur = max(runnable, key=effective_priority)
        if tasks[cur]["needs_lock"] and lock_holder is None:
            lock_holder = cur
            if cur in waiting:
                waiting.remove(cur)
            if cur == "H" and h_acquire is None:
                h_acquire = t
        rem[cur] -= 1
        trace.append((t, cur))
        if rem[cur] == 0:
            done.add(cur)
            if lock_holder == cur:
                lock_holder = None
    return h_acquire, trace


# ----------------------------------------------------------------- printing

def schedule_view(data):
    tasks = data["tasks"]
    _, tn = simulate(tasks, inherit=False)
    _, ti = simulate(tasks, inherit=True)
    n = max(len(tn), len(ti))
    print("SCHEDULE — task running at each tick (. = idle)")
    print("-" * 60)
    print("  tick:      " + "".join("%2d" % t for t in range(n)))
    print("  no-inherit " + "".join("%2s" % (dict(tn).get(t) or ".") for t in range(n)))
    print("  inherit    " + "".join("%2s" % (dict(ti).get(t) or ".") for t in range(n)))
    print("-" * 60)
    print("  without inheritance M runs before L releases the lock; with it, L runs through")


def wait_view(data):
    tasks = data["tasks"]
    hn, _ = simulate(tasks, inherit=False)
    hi, _ = simulate(tasks, inherit=True)
    arrive = tasks["H"]["arrive"]
    print("WAIT — when the high-priority task H acquires the lock (H arrives at t=%d)" % arrive)
    print("-" * 60)
    print("  no-inheritance:  H acquires at t=%d, wait %d" % (hn, hn - arrive))
    print("  inheritance:     H acquires at t=%d, wait %d" % (hi, hi - arrive))
    print("  inversion cost (extra wait)       = %d  (= M's work %d)" % (hn - hi, tasks["M"]["work"]))
    print("-" * 60)
    print("  the extra wait is exactly the medium task's work — time H should never have lost")


def check(data):
    print("SELF-TEST — without inheritance a medium task delays the high-priority task; inheritance bounds the wait to the critical section")
    print("-" * 128)
    tasks = data["tasks"]
    hn, tn = simulate(tasks, inherit=False)
    hi, ti = simulate(tasks, inherit=True)
    arrive = tasks["H"]["arrive"]
    wait_n, wait_i = hn - arrive, hi - arrive

    h_is_highest = tasks["H"]["priority"] == max(t["priority"] for t in tasks.values())
    print("  H is the highest-priority task = %s" % h_is_highest)

    m_runs_before_release_noinherit = any(who == "M" and t < hn for t, who in tn)
    print("  without inheritance the medium task M runs while H waits = %s" % m_runs_before_release_noinherit)

    m_blocked_under_inherit = all(not (who == "M" and t < hi) for t, who in ti)
    print("  with inheritance M does NOT run before H acquires the lock = %s" % m_blocked_under_inherit)

    inheritance_reduces_wait = wait_i < wait_n
    print("  inheritance reduces H's wait = %s (%d < %d)" % (inheritance_reduces_wait, wait_i, wait_n))

    cost_equals_medium_work = (wait_n - wait_i) == tasks["M"]["work"]
    print("  the extra wait equals the medium task's work = %s (%d == %d)" % (cost_equals_medium_work, wait_n - wait_i, tasks["M"]["work"]))

    ok = (h_is_highest and m_runs_before_release_noinherit and m_blocked_under_inherit
          and inheritance_reduces_wait and cost_equals_medium_work)
    print("-" * 128)
    print("SELF-TEST %s  h_is_highest=%s  m_runs_before_release_noinherit=%s  m_blocked_under_inherit=%s  inheritance_reduces_wait=%s  cost_equals_medium_work=%s"
          % ("PASS" if ok else "FAIL", h_is_highest, m_runs_before_release_noinherit, m_blocked_under_inherit, inheritance_reduces_wait, cost_equals_medium_work))
    return ok


def main():
    p = argparse.ArgumentParser(description="Priority inversion: have a lock-holder inherit the priority of the highest-priority task waiting on that lock (priority inheritance), because otherwise a medium-priority task preempts the low-priority holder and blocks the high-priority waiter behind it for an unbounded time -- inheritance bounds the wait to the critical section the high-priority task actually depends on.")
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--wait", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tasks=%s  file=%s  (the tasks are a fixture)"
          % ({k: (v["priority"], v["arrive"], v["work"], "lock" if v["needs_lock"] else "-") for k, v in data["tasks"].items()}, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.schedule:
        schedule_view(data)
    elif args.wait:
        wait_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
