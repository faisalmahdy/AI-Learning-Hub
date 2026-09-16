"""Return partial results when one parallel tool call fails, or you throw away all the work that succeeded.

An agent fires several tool calls at once -- fetch three documents, query four services -- to save time. Now
one of them fails: a timeout, a 500, a bad argument. The harness has to decide what to hand back to the
model. The lazy choice is fail-fast: any call in the batch fails, so the whole batch is an error and the
model gets nothing. That throws away every call that succeeded. The three documents that came back fine are
discarded because the fourth timed out, and the agent has to redo all four -- wasting the successful work
and the latency the parallel call was supposed to save. One flaky call poisons the whole batch.

The better choice is to return partial results: hand back every successful call's result AND a labeled
error for each failed one. The model sees the three documents it got and a clear note that the fourth
failed, so it can proceed with what it has, retry only the one that failed, or adapt its plan -- instead of
starting over. The failure is surfaced, not swallowed (the agent must know a call failed to handle it), and
the successes are preserved. A batch is a bag of independent results, not an all-or-nothing transaction,
unless the calls genuinely depend on each other.

On this fixture a batch of 4 parallel calls has 3 succeed and 1 fail. Fail-fast delivers 0 usable results
and wastes all 3 successes. Partial-results delivers the 3 successes plus 1 labeled error, so the agent
keeps the work and knows exactly what to retry. This computes both.

  --batch      the outcome of each parallel call
  --deliver    what each policy hands the model: usable results and surfaced errors
  --check      fail-fast discards the successes; partial-results keeps them and surfaces the failure

The per-call outcomes are the fixture; every delivery is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "batch.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def successes(batch):
    return [c for c in batch if c["ok"]]


def failures(batch):
    return [c for c in batch if not c["ok"]]


def deliver_failfast(batch):
    """Any failure aborts the batch: the model gets no results and no per-call detail."""
    if failures(batch):
        return {"results": [], "errors": ["batch failed"]}
    return {"results": [c["id"] for c in batch], "errors": []}


def deliver_partial(batch):
    """Return every success and a labeled error per failure -- the model keeps the work and sees the gaps."""
    return {"results": [c["id"] for c in successes(batch)],
            "errors": ["%s: %s" % (c["id"], c["error"]) for c in failures(batch)]}


# ----------------------------------------------------------------- printing

def batch_view(data):
    batch = data["batch"]
    print("BATCH — outcome of each parallel call")
    print("-" * 48)
    for c in batch:
        print("  %-10s %s%s" % (c["id"], "ok" if c["ok"] else "FAILED", "" if c["ok"] else "  (%s)" % c["error"]))
    print("-" * 48)
    print("  %d of %d succeeded." % (len(successes(batch)), len(batch)))


def deliver_view(data):
    batch = data["batch"]
    ff, pr = deliver_failfast(batch), deliver_partial(batch)
    print("DELIVER — what each policy hands the model")
    print("-" * 58)
    print("  fail-fast:  results %s   errors %s" % (ff["results"], ff["errors"]))
    print("  partial:    results %s   errors %s" % (pr["results"], pr["errors"]))
    print("-" * 58)
    print("  fail-fast delivers nothing usable; partial delivers the successes.")


def check(data):
    print("SELF-TEST — fail-fast discards the successes; partial-results keeps them and surfaces the failure")
    print("-" * 96)
    batch = data["batch"]
    ff, pr = deliver_failfast(batch), deliver_partial(batch)
    n_success = len(successes(batch))
    n_fail = len(failures(batch))

    failfast_delivers_nothing = len(ff["results"]) == 0 and n_fail > 0
    print("  fail-fast delivers nothing usable when any call fails = %s (results %s)" % (failfast_delivers_nothing, ff["results"]))

    failfast_wastes_successes = n_success - len(ff["results"]) == n_success
    print("  fail-fast wastes all %d successful calls = %s" % (n_success, failfast_wastes_successes))

    partial_delivers_successes = len(pr["results"]) == n_success
    print("  partial delivers every successful result = %s (%d)" % (partial_delivers_successes, len(pr["results"])))

    partial_surfaces_failures = len(pr["errors"]) == n_fail and n_fail > 0
    print("  partial surfaces each failure as a labeled error = %s (%s)" % (partial_surfaces_failures, pr["errors"]))

    partial_beats_failfast = len(pr["results"]) > len(ff["results"])
    print("  partial delivers more usable results than fail-fast = %s (%d vs %d)" % (partial_beats_failfast, len(pr["results"]), len(ff["results"])))

    ok = failfast_delivers_nothing and failfast_wastes_successes and partial_delivers_successes and partial_surfaces_failures and partial_beats_failfast
    print("-" * 96)
    print("SELF-TEST %s  failfast_delivers_nothing=%s  failfast_wastes_successes=%s  partial_delivers_successes=%s  partial_surfaces_failures=%s  partial_beats_failfast=%s"
          % ("PASS" if ok else "FAIL", failfast_delivers_nothing, failfast_wastes_successes, partial_delivers_successes, partial_surfaces_failures, partial_beats_failfast))
    return ok


def main():
    p = argparse.ArgumentParser(description="Return partial results from a parallel tool batch instead of failing the whole thing.")
    p.add_argument("--batch", action="store_true")
    p.add_argument("--deliver", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%d  file=%s  (the per-call outcomes are a fixture)" % (len(data["batch"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.batch:
        batch_view(data)
    elif args.deliver:
        deliver_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
