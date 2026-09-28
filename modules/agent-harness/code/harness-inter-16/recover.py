"""Return a tool error as an observation, or one transient failure aborts the loop and discards the work.

A sequential agent runs a plan step by step: each step is a tool call, and the result feeds the next step.
Tools fail transiently all the time -- a timeout, a rate limit, a flaky socket -- and recover on a retry.
The question is what the harness does with that failure. The naive harness lets the tool's exception
propagate: it unwinds the loop, so the run ends at the failing step. Every step that already succeeded is
thrown away, because the loop returned an error and the caller sees only failure. A momentary blip on step 2
costs you the completed step 1 and the steps 3 and 4 that never ran.

The fix is to treat a tool error as data, not as control flow. Catch the failure and return it to the agent
as an observation -- "the tool failed with X" -- exactly the way a successful result is returned. Now the
agent can act on it: retry the same step (with backoff, up to a cap), try a different tool, or report a
specific failure. A transient error becomes a retried step and the plan completes; a permanent error becomes
a clear, localized report instead of an opaque stack trace that loses the context of what had worked.

On this fixture the plan has four steps and step 2 (fetch_data) fails on its first attempt but succeeds if
retried. The raising harness aborts at step 2 with only one step done. The recovering harness returns the
error as an observation, retries step 2 once, and finishes all four steps. Same plan, same transient failure;
only the error handling differs. This computes both.

  --run        each harness step by step: what completes, what aborts, and where
  --attempts   the recovering harness's attempt count per step, showing the one retry
  --check      the raising harness aborts early and discards completed work; the recovering one finishes

The plan and retry cap are the fixture; every outcome is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "plan.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run_raise(steps):
    """Naive harness: a tool exception propagates, so the loop aborts at the first failure."""
    done = []
    for s in steps:
        if s["fails_first"]:                       # one attempt only; the exception unwinds the loop
            return done, "ABORTED at %s" % s["name"]
        done.append(s["name"])
    return done, "DONE"


def run_recover(steps, max_retries):
    """Recovering harness: a tool error is returned as an observation and the step is retried up to the cap."""
    done, attempts = [], {}
    for s in steps:
        attempt = 0
        while True:
            attempt += 1
            failed = s["fails_first"] and attempt == 1   # transient: fails only on the first attempt
            if not failed or attempt >= 1 + max_retries:
                break
        attempts[s["name"]] = attempt
        if s["fails_first"] and attempt == 1:            # never recovered within the cap
            return done, attempts, "FAILED at %s" % s["name"]
        done.append(s["name"])
    return done, attempts, "DONE"


# ----------------------------------------------------------------- printing

def run_view(data):
    steps, mr = data["steps"], data["max_retries"]
    rd, rstatus = run_raise(steps)
    cd, _, cstatus = run_recover(steps, mr)
    print("RUN — sequential plan of %d steps (step 2 fails transiently)" % len(steps))
    print("-" * 64)
    print("  raising harness:    done %s" % rd)
    print("                      status: %s" % rstatus)
    print("  recovering harness: done %s" % cd)
    print("                      status: %s" % cstatus)
    print("-" * 64)
    print("  the raise unwinds the loop at step 2; the recover retries and continues.")


def attempts_view(data):
    steps, mr = data["steps"], data["max_retries"]
    _, attempts, _ = run_recover(steps, mr)
    print("ATTEMPTS — attempts per step in the recovering harness (cap %d retries)" % mr)
    print("-" * 64)
    for s in steps:
        n = attempts[s["name"]]
        print("  %-12s %d attempt(s)%s" % (s["name"], n, "   <- retried after a transient error" if n > 1 else ""))
    print("-" * 64)
    print("  only the transient step needed a retry; the rest passed first try.")


def check(data):
    print("SELF-TEST — the raising harness aborts early and discards completed work; the recovering one finishes")
    print("-" * 100)
    steps, mr = data["steps"], data["max_retries"]
    rd, rstatus = run_raise(steps)
    cd, attempts, cstatus = run_recover(steps, mr)

    raise_aborts_early = len(rd) < len(steps)
    print("  the raising harness stops before the end = %s (%d of %d steps)" % (raise_aborts_early, len(rd), len(steps)))

    raise_discards_completed = rstatus != "DONE" and len(rd) >= 1
    print("  the raising harness reports failure though %d step(s) succeeded = %s (%r)" % (len(rd), raise_discards_completed, rstatus))

    recover_completes_all = len(cd) == len(steps) and cstatus == "DONE"
    print("  the recovering harness finishes every step = %s (%d of %d, %r)" % (recover_completes_all, len(cd), len(steps), cstatus))

    failing = next(s["name"] for s in steps if s["fails_first"])
    recover_retried_transient = attempts[failing] > 1
    print("  the recovering harness retried the transient step = %s (%s took %d attempts)" % (recover_retried_transient, failing, attempts[failing]))

    others_passed_first = all(attempts[s["name"]] == 1 for s in steps if not s["fails_first"])
    print("  every non-failing step passed on the first attempt = %s" % others_passed_first)

    ok = raise_aborts_early and raise_discards_completed and recover_completes_all and recover_retried_transient and others_passed_first
    print("-" * 100)
    print("SELF-TEST %s  raise_aborts_early=%s  raise_discards_completed=%s  recover_completes_all=%s  recover_retried_transient=%s  others_passed_first=%s"
          % ("PASS" if ok else "FAIL", raise_aborts_early, raise_discards_completed, recover_completes_all, recover_retried_transient, others_passed_first))
    return ok


def main():
    p = argparse.ArgumentParser(description="Return a tool error as an observation so the agent recovers instead of aborting.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--attempts", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steps=%d  max_retries=%d  file=%s  (the plan is a fixture)"
          % (len(data["steps"]), data["max_retries"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.attempts:
        attempts_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
