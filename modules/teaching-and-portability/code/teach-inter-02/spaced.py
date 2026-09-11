#!/usr/bin/env python3
"""Schedule reviews by whether you recalled -- not by how many times you looked.

A boss-fight recall ledger records, per concept, each review and whether you actually
recalled it. Spaced repetition turns that into a schedule: a concept you keep nailing
is pushed further out (double the gap each time), and a concept you blank on comes
back soon (reset the gap). Done right, your limited daily review budget flows to the
things you do not know. This builds that scheduler and the one-line bug that quietly
inverts it: growing the interval on every review REGARDLESS of the result.

The bug is seductive because it looks like progress -- each review pushes the concept
further out, the queue empties, everything feels mastered. But a concept you have
failed four times in a row gets pushed out just as far as one you have aced, so the
scheduler stops showing you exactly the material you most need to see. It marks
chronic failure as mastery. The fix is to read the result of each review, not merely
count that one occurred: reset the interval on a fail.

  --schedule    each concept's interval and next-due day under the correct scheduler
  --compare     correct vs naive (grow-always) intervals, side by side
  --due         what is due today under each scheduler -- and what the bug hides
  --check       correct resets failed concepts; naive pushes them out (the bug)

Stdlib only. Deterministic. 'today' comes from the fixture, not a clock.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "reviews.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the schedulers

def interval_correct(history):
    """Double the interval on a pass; RESET to 1 on a fail. Returns (interval, last_day)."""
    interval = 1
    last_day = 0
    for review in history:
        if review["result"] == "pass":
            interval *= 2
        else:
            interval = 1  # blanked -> bring it back tomorrow
        last_day = review["day"]
    return interval, last_day


def interval_naive(history):
    """The bug: grow the interval on EVERY review, ignoring pass/fail."""
    interval = 1
    last_day = 0
    for review in history:
        interval *= 2  # never reads review["result"] -- failures pushed out like passes
        last_day = review["day"]
    return interval, last_day


def next_due(interval_fn, history):
    interval, last_day = interval_fn(history)
    return last_day + interval


def is_due(interval_fn, concept, today):
    return next_due(interval_fn, concept["history"]) <= today


def recent_fails(history):
    """How many of the trailing reviews were fails (0 if the last was a pass)."""
    n = 0
    for review in reversed(history):
        if review["result"] == "fail":
            n += 1
        else:
            break
    return n


# ----------------------------------------------------------------- printing

def schedule_view(data):
    print("SCHEDULE — correct scheduler: interval and next-due day (today=%d)" % data["today"])
    print("-" * 66)
    for c in data["concepts"]:
        interval, last = interval_correct(c["history"])
        due = last + interval
        tail = recent_fails(c["history"])
        note = "DUE" if due <= data["today"] else "in %d days" % (due - data["today"])
        print("  %-18s interval=%-3d last=day%-3d due=day%-3d  %s%s"
              % (c["name"], interval, last, due, note, "  (failing)" if tail else ""))
    print("-" * 66)
    print("  failed concepts have a short interval and come due fast -- that is the point.")


def compare_view(data):
    print("COMPARE — correct (reset on fail) vs naive (grow always) intervals")
    print("-" * 66)
    print("  concept            trailing-fails  correct-interval  naive-interval")
    for c in data["concepts"]:
        ic, _ = interval_correct(c["history"])
        inv, _ = interval_naive(c["history"])
        print("  %-18s %-15d %-17d %d" % (c["name"], recent_fails(c["history"]), ic, inv))
    print("-" * 66)
    print("  the naive scheduler pushes failed concepts as far out as mastered ones.")


def due_view(data):
    today = data["today"]
    correct_due = [c["name"] for c in data["concepts"] if is_due(interval_correct, c, today)]
    naive_due = [c["name"] for c in data["concepts"] if is_due(interval_naive, c, today)]
    hidden = [n for n in correct_due if n not in naive_due]
    print("DUE — what each scheduler surfaces today (today=%d)" % today)
    print("-" * 66)
    print("  correct scheduler due: %s" % correct_due)
    print("  naive scheduler due:   %s" % naive_due)
    print("  hidden by the bug:     %s" % hidden)
    print("-" * 66)
    print("  the naive scheduler buries concepts you are actively failing.")


def check(data):
    print("SELF-TEST — correct resets failed concepts; naive pushes them out (the bug)")
    print("-" * 66)
    concepts = {c["name"]: c["history"] for c in data["concepts"]}

    # A concept failed repeatedly must have a tiny interval under the correct scheduler.
    bpe_c, _ = interval_correct(concepts["bpe-tokens"])
    failed_stays_short = bpe_c == 1
    print("  correct: a repeatedly-failed concept stays at interval 1 = %s (bpe-tokens=%d)"
          % (failed_stays_short, bpe_c))

    # Under the naive scheduler that same concept is pushed far out -- the bug.
    bpe_n, _ = interval_naive(concepts["bpe-tokens"])
    naive_pushes_failed = bpe_n >= 8
    print("  naive: the same failed concept is pushed far out = %s (bpe-tokens=%d)"
          % (naive_pushes_failed, bpe_n))

    # A mastered concept (all passes) reaches a long interval under the correct scheduler.
    att_c, _ = interval_correct(concepts["attention"])
    mastered_grows = att_c >= 8
    print("  correct: an all-pass concept reaches a long interval = %s (attention=%d)"
          % (mastered_grows, att_c))

    # The bug hides at least one actively-failing concept from today's due queue.
    today = data["today"]
    correct_due = {c["name"] for c in data["concepts"] if is_due(interval_correct, c, today)}
    naive_due = {c["name"] for c in data["concepts"] if is_due(interval_naive, c, today)}
    bug_hides = "bpe-tokens" in correct_due and "bpe-tokens" not in naive_due
    print("  the naive scheduler hides a failing concept that the correct one shows = %s" % bug_hides)

    ok = failed_stays_short and naive_pushes_failed and mastered_grows and bug_hides
    print("-" * 66)
    print("SELF-TEST %s  failed_stays_short=%s  naive_pushes_failed=%s  mastered_grows=%s  bug_hides=%s"
          % ("PASS" if ok else "FAIL", failed_stays_short, naive_pushes_failed, mastered_grows, bug_hides))
    return ok


def main():
    p = argparse.ArgumentParser(description="Spaced-repetition scheduling from a recall ledger.")
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--due", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("concepts=%d  today=%d  file=%s  (review histories are a fixture)"
          % (len(data["concepts"]), data["today"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.schedule:
        schedule_view(data)
    elif args.compare:
        compare_view(data)
    elif args.due:
        due_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
