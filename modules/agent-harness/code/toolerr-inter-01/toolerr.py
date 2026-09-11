"""Return structured errors from tools, not raw tracebacks -- the harness needs a field to branch on, and the model needs a hint, not a stack dump.

When a tool call fails, the harness has to turn the failure into something it puts back in the conversation. The path of least resistance is to catch the exception and hand back its traceback -- the full Python stack, file paths, and all. It runs, and it is almost always wrong, for two audiences at once. The harness's own retry logic gets a blob of text with no machine-readable signal: nothing it can read to decide whether this failure is worth retrying, so it either retries everything (wasting calls on permanent errors) or retries nothing (giving up on transient ones). And the model gets a wall of internal stack frames -- implementation paths, library versions -- that is mostly noise, costs a pile of tokens, and buries the one thing it needs: what to do next.

A STRUCTURED error fixes both. It is a small object with the fields a decision actually turns on: a stable machine-readable CODE (rate_limited, invalid_argument), a short human MESSAGE, a RETRYABLE flag, an optional retry_after, and a HINT written for the model -- the concrete next action. Now the harness branches on retryable: retry the transient failures (after the suggested delay), and do not retry the permanent ones. And the model, if it sees the error at all, gets a compact instruction ('fix the user_id argument to a number') instead of a traceback it has to parse.

The two failure classes are the whole point. A rate limit is transient: the exact same call will likely succeed after a short wait, so it is retryable. A bad argument is permanent: retrying the identical call will fail forever -- the fix is to change the argument, which only the model (or the harness's validation) can do. A raw traceback does not distinguish these; a blanket retry policy therefore retries the un-retryable and wastes calls, or refuses to retry the retryable and gives up on a call that would have worked. The retryable flag is exactly the distinction the traceback throws away.

The rule: have tools return a structured error -- a machine-readable code, a retryable flag, an optional retry_after, and a short actionable hint -- rather than passing the raw exception traceback back to the harness and the model, because the harness needs a field to make the retry decision and the model needs a next action, and a traceback is a large, noisy blob that carries neither the retryable signal nor an instruction.

On this fixture the transient rate-limit error and the permanent bad-argument error are given both ways. Reading the raw tracebacks, the harness has no retryable field and a blanket policy mishandles one of the two; reading the structured errors, it retries the transient one, does not retry the permanent one, and the structured payloads are a fraction of the traceback size. This computes both.

  --errors    each failure as its raw traceback and as its structured error, with the byte sizes
  --decide    the retry decision from the structured flag vs the missing signal in the traceback, per failure
  --check     the traceback carries no retryable field and mishandles a failure class; the structured error drives the correct decision, smaller

failures is the fixture; the raw-vs-structured sizes, the retryable extraction, and the retry decisions are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "toolerr.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def structured(f):
    """The fields a tool should return on failure: code, message, retryable, retry_after, hint."""
    return {"code": f["code"], "message": f["message"], "retryable": f["retryable"], "retry_after_s": f["retry_after_s"], "hint": f["hint"]}


def structured_size(f):
    return len(json.dumps(structured(f)))


def raw_size(f):
    return len(f["raw_traceback"])


def retryable_from_structured(f):
    """The harness reads the retryable flag directly."""
    return f["retryable"]


def retryable_from_traceback(f):
    """There is no machine-readable retryable field in a traceback -- None means 'cannot decide'."""
    return None


def decision_from(retryable, f):
    """The harness's action given a retryable value (or None when it cannot tell)."""
    if retryable is None:
        return "unknown (no signal)"
    if retryable:
        return "retry after %ds" % f["retry_after_s"]
    return "do not retry; surface hint to model"


def blanket_retry_correct(failures, always_retry):
    """A traceback-only harness must pick ONE blanket policy; count how many failure classes it mishandles."""
    mishandled = 0
    for f in failures:
        acted_retry = always_retry
        should_retry = f["retryable"]
        if acted_retry != should_retry:
            mishandled += 1
    return mishandled


# ----------------------------------------------------------------- printing

def errors_view(data):
    print("ERRORS — each failure as raw traceback vs structured error")
    print("-" * 66)
    for f in data["failures"]:
        print("  tool %s (%s):" % (f["tool"], f["code"]))
        print("    raw traceback (%d chars):" % raw_size(f))
        for line in f["raw_traceback"].splitlines():
            print("      %s" % line)
        print("    structured (%d chars): %s" % (structured_size(f), json.dumps(structured(f))))
        print("")


def decide_view(data):
    print("DECIDE — retry decision from the structured flag vs the traceback")
    print("-" * 68)
    for f in data["failures"]:
        sr = retryable_from_structured(f)
        tr = retryable_from_traceback(f)
        print("  %s (%s):" % (f["tool"], f["code"]))
        print("    from structured: retryable=%s -> %s" % (sr, decision_from(sr, f)))
        print("    from traceback:  retryable=%s -> %s" % (tr, decision_from(tr, f)))
    print("-" * 68)
    print("  blanket 'always retry' mishandles %d of %d; blanket 'never retry' mishandles %d of %d"
          % (blanket_retry_correct(data["failures"], True), len(data["failures"]),
             blanket_retry_correct(data["failures"], False), len(data["failures"])))


def check(data):
    print("SELF-TEST — the traceback carries no retryable field and mishandles a failure class; the structured error drives the correct decision, smaller")
    print("-" * 142)
    failures = data["failures"]
    transient = next(f for f in failures if f["retryable"])
    permanent = next(f for f in failures if not f["retryable"])

    traceback_has_no_flag = all(retryable_from_traceback(f) is None for f in failures)
    print("  the raw traceback carries no machine-readable retryable field = %s" % traceback_has_no_flag)

    structured_exposes_flag = all(isinstance(retryable_from_structured(f), bool) for f in failures)
    print("  the structured error exposes a retryable flag = %s" % structured_exposes_flag)

    structured_decides_transient = decision_from(retryable_from_structured(transient), transient).startswith("retry")
    print("  structured drives RETRY for the transient rate-limit = %s (%s)" % (structured_decides_transient, decision_from(retryable_from_structured(transient), transient)))

    structured_decides_permanent = decision_from(retryable_from_structured(permanent), permanent).startswith("do not retry")
    print("  structured drives NO-RETRY for the permanent bad-argument = %s (%s)" % (structured_decides_permanent, decision_from(retryable_from_structured(permanent), permanent)))

    blanket_always_mis = blanket_retry_correct(failures, True)
    blanket_never_mis = blanket_retry_correct(failures, False)
    blanket_always_mishandles = blanket_always_mis > 0 and blanket_never_mis > 0
    print("  every blanket traceback-only policy mishandles a failure class = %s (always-retry %d, never-retry %d)" % (blanket_always_mishandles, blanket_always_mis, blanket_never_mis))

    structured_smaller = sum(structured_size(f) for f in failures) < sum(raw_size(f) for f in failures)
    print("  the structured errors are smaller than the tracebacks = %s (%d < %d chars)" % (structured_smaller, sum(structured_size(f) for f in failures), sum(raw_size(f) for f in failures)))

    traceback_leaks_paths = all("/app/harness" in f["raw_traceback"] for f in failures)
    print("  the tracebacks leak internal file paths (noise) = %s" % traceback_leaks_paths)

    ok = (traceback_has_no_flag and structured_exposes_flag and structured_decides_transient and structured_decides_permanent
          and blanket_always_mishandles and structured_smaller and traceback_leaks_paths)
    print("-" * 142)
    print("SELF-TEST %s  traceback_has_no_flag=%s  structured_exposes_flag=%s  structured_decides_transient=%s  structured_decides_permanent=%s  blanket_always_mishandles=%s  structured_smaller=%s  traceback_leaks_paths=%s"
          % ("PASS" if ok else "FAIL", traceback_has_no_flag, structured_exposes_flag, structured_decides_transient, structured_decides_permanent, blanket_always_mishandles, structured_smaller, traceback_leaks_paths))
    return ok


def main():
    p = argparse.ArgumentParser(description="Structured tool errors: have tools return a structured error -- a machine-readable code, a retryable flag, an optional retry_after, and a short actionable hint -- rather than passing the raw exception traceback back to the harness and the model, because the harness needs a field to make the retry decision and the model needs a next action, and a traceback is a large, noisy blob that carries neither the retryable signal nor an instruction.")
    p.add_argument("--errors", action="store_true")
    p.add_argument("--decide", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("failures=%d  file=%s  (the tool failures, raw and structured, are a fixture)"
          % (len(data["failures"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.errors:
        errors_view(data)
    elif args.decide:
        decide_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
