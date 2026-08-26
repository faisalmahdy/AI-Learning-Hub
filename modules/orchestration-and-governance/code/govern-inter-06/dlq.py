#!/usr/bin/env python3
"""Dead-letter a poison task after max retries -- or it blocks the whole fan-out.

Fan work out to a worker and some tasks will fail. Most failures are transient: retry
and they pass. But some tasks fail EVERY time -- a malformed input, a permanently broken
dependency, a poison message. Retrying those is not resilience, it is a trap: the worker
loops on the bad task forever and every task behind it starves. A queue with one poison
message and no escape hatch stops processing entirely.

The fix is a retry bound plus a dead-letter queue. Retry a failing task up to max_retries;
if it still fails, move it to the dead-letter queue -- set aside for inspection -- and move
on. The poison task is contained, the rest of the fan-out drains, and you have a record of
what could not be processed. This runs a bounded worker both ways: with dead-lettering the
queue drains; without it, the poison task consumes the attempt budget and the later tasks
are never reached.

  --run         the correct worker: retry to a bound, dead-letter the rest, drain the queue
  --broken      the broken worker: retry forever; watch the poison task starve the rest
  --check       correct drains and dead-letters the poison; broken starves the tasks behind it

Deterministic: a task needs `attempts_to_succeed` attempts (huge = poison). Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "queue.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the worker

def run_queue(data, dead_letter):
    """Process the queue within the attempt budget.

    dead_letter=True: retry up to max_retries, then move on (to the DLQ). False: retry
    forever (the bug). Returns (done, dlq, unreached, attempts_used).
    """
    tasks = data["tasks"]
    max_retries = data["max_retries"]
    budget = data["attempt_budget"]

    done, dlq = [], []
    attempts_used = 0
    i = 0
    while i < len(tasks) and attempts_used < budget:
        task = tasks[i]
        tries = 0
        while attempts_used < budget:
            tries += 1
            attempts_used += 1
            if tries >= task["attempts_to_succeed"]:      # succeeds on this attempt
                done.append(task["id"])
                i += 1
                break
            if dead_letter and tries >= max_retries:      # give up, dead-letter it
                dlq.append(task["id"])
                i += 1
                break
            # else: retry (dead_letter=False loops until budget runs out on a poison task)
    unreached = [t["id"] for t in tasks[i:]]
    return done, dlq, unreached, attempts_used


# ----------------------------------------------------------------- printing

def run_view(data):
    done, dlq, unreached, used = run_queue(data, dead_letter=True)
    print("RUN — correct worker: retry to max_retries=%d, then dead-letter" % data["max_retries"])
    print("-" * 66)
    print("  done:        %s" % done)
    print("  dead-letter: %s" % dlq)
    print("  unreached:   %s" % unreached)
    print("  attempts used: %d of %d budget" % (used, data["attempt_budget"]))
    print("-" * 66)
    print("  every task reached a terminal state; the poison task is contained in the DLQ.")


def broken_view(data):
    done, dlq, unreached, used = run_queue(data, dead_letter=False)
    print("BROKEN — retry forever: the poison task blocks everything behind it")
    print("-" * 66)
    print("  done:        %s" % done)
    print("  dead-letter: %s  (no DLQ -- nothing is ever given up)" % dlq)
    print("  unreached:   %s  <- starved by the poison task" % unreached)
    print("  attempts used: %d of %d budget (all burned on the poison task)" % (used, data["attempt_budget"]))
    print("-" * 66)
    print("  one bad input stalled the whole fan-out.")


def check(data):
    print("SELF-TEST — correct drains and dead-letters the poison; broken starves the rest")
    print("-" * 66)
    tasks = [t["id"] for t in data["tasks"]]

    done, dlq, unreached, used = run_queue(data, dead_letter=True)
    all_terminal = set(done) | set(dlq) == set(tasks) and unreached == []
    print("  correct: every task reached a terminal state (done or DLQ) = %s" % all_terminal)

    poison_dead_lettered = "t2" in dlq
    print("  correct: the poison task is dead-lettered = %s (DLQ=%s)" % (poison_dead_lettered, dlq))

    later_processed = "t3" in done and "t4" in done
    print("  correct: tasks after the poison one still ran = %s (t3, t4 done)" % later_processed)

    b_done, b_dlq, b_unreached, b_used = run_queue(data, dead_letter=False)
    broken_starves = "t3" in b_unreached and "t4" in b_unreached
    print("  broken: tasks behind the poison are STARVED = %s (unreached %s)" % (broken_starves, b_unreached))

    broken_burns_budget = b_used == data["attempt_budget"]
    print("  broken: the poison task burned the whole attempt budget = %s (%d)" % (broken_burns_budget, b_used))

    ok = all_terminal and poison_dead_lettered and later_processed and broken_starves and broken_burns_budget
    print("-" * 66)
    print("SELF-TEST %s  all_terminal=%s  poison_dead_lettered=%s  later_processed=%s  broken_starves=%s  broken_burns_budget=%s"
          % ("PASS" if ok else "FAIL", all_terminal, poison_dead_lettered, later_processed, broken_starves, broken_burns_budget))
    return ok


def main():
    p = argparse.ArgumentParser(description="Dead-letter queue: contain a poison task, drain the fan-out.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--broken", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tasks=%d  max_retries=%d  attempt_budget=%d  file=%s  (outcomes are a fixture)"
          % (len(data["tasks"]), data["max_retries"], data["attempt_budget"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.broken:
        broken_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
