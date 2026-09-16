"""Accept an agent's run as done only when a checkable success predicate holds -- not because the model said 'task complete'.

An agent run ends with a final message: 'done', 'all tasks complete', a tidy summary. The easiest thing for a harness to do is treat that message as the stop signal -- the model says it finished, so return its result as a success. That is trusting the model's self-assessment of whether the goal was met, and it is exactly the assessment models are worst at. A model loses track of a subtask across a long trace, mistakes a partial result for the whole, or simply asserts completion because the conversation has reached a natural-feeling end. None of those are lies the model knows it is telling; they are the ordinary ways a plan drifts. But the harness that believes the claim reports the task done and hands back a result while part of the goal was never accomplished.

The failure is silent, which is what makes it dangerous. Nothing errored. The model was confident. The only thing the harness checked was the model's word, and the model's word was wrong. Downstream, someone acts on a 'completed' task -- ships the report, closes the ticket, triggers the next stage -- that was never actually finished.

The fix is to stop treating 'done' as a claim and start treating it as a predicate the harness evaluates. Define the task's success criterion as something checkable against the world or the run's own record: the required output files exist, the required steps ran, the produced artifact passes its validator, the answer contains every required field. On the model's 'done', evaluate that predicate. If it holds, the task really is complete and the harness returns success. If it does not, the task is not done no matter what the model said -- the harness continues, retries the missing part, or fails honestly, but it does not return a wrong success.

The rule: verify termination against an objective, checkable success predicate before accepting a run as complete, because a model's self-reported 'done' routinely overstates what was accomplished -- so trusting the claim returns false successes, while checking the predicate catches the unmet requirement and names exactly what is missing.

On this fixture the task requires three steps; the agent completed two and its final message claims completion. A harness that trusts the claim returns success; a harness that checks the predicate finds it unmet and names the missing step. This computes both.

  --report    the required steps, what the agent completed, and the model's self-reported done
  --verify    the naive (trust-the-claim) outcome vs the verified (check-the-predicate) outcome
  --check     the model claims done but a requirement is unmet; trusting the claim returns a false success, the predicate catches it

required, completed, and self_report are the fixture; the naive and verified outcomes and the missing requirements are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "verifydone.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def missing_requirements(required, completed):
    return [r for r in required if r not in completed]


def naive_accept(self_report):
    """Trust the model's claim: done if it says done."""
    return bool(self_report.get("done"))


def verified_done(required, completed):
    """Check the predicate: done only if every required step was completed."""
    return all(r in completed for r in required)


# ----------------------------------------------------------------- printing

def report_view(data):
    required, completed = data["required"], data["completed"]
    sr = data["self_report"]
    print("REPORT — the goal, the actual progress, and the model's claim")
    print("-" * 60)
    print("  required steps  = %s" % required)
    print("  completed steps = %s" % completed)
    print("  model says done = %s (%r)" % (sr.get("done"), sr.get("message")))
    print("-" * 60)
    print("  the model claims completion; two of three required steps actually ran")


def verify_view(data):
    required, completed = data["required"], data["completed"]
    sr = data["self_report"]
    naive = naive_accept(sr)
    verified = verified_done(required, completed)
    missing = missing_requirements(required, completed)
    print("VERIFY — trust the claim vs check the predicate")
    print("-" * 60)
    print("  naive (accept model's 'done')     -> success = %s" % naive)
    print("  verified (predicate over steps)   -> done    = %s" % verified)
    print("  missing requirements              = %s" % missing)
    print("-" * 60)
    print("  the claim returns success; the predicate returns not-done and names the gap")


def check(data):
    print("SELF-TEST — the model claims done but a requirement is unmet; trusting the claim returns a false success, the predicate catches it")
    print("-" * 128)
    required, completed = data["required"], data["completed"]
    sr = data["self_report"]
    missing = missing_requirements(required, completed)
    naive = naive_accept(sr)
    verified = verified_done(required, completed)

    model_claims_done = naive
    print("  the model's final message claims completion = %s (%r)" % (model_claims_done, sr.get("message")))

    requirement_unmet = len(missing) > 0
    print("  a required step was not actually completed = %s (missing %s)" % (requirement_unmet, missing))

    naive_false_success = naive and not verified
    print("  trusting the claim returns a FALSE success = %s" % naive_false_success)

    verify_catches = verified is False
    print("  the predicate returns not-done = %s" % verify_catches)

    verify_names_missing = missing == [r for r in required if r not in completed] and len(missing) > 0
    print("  the predicate names exactly what is missing = %s (%s)" % (verify_names_missing, missing))

    ok = (model_claims_done and requirement_unmet and naive_false_success and verify_catches and verify_names_missing)
    print("-" * 128)
    print("SELF-TEST %s  model_claims_done=%s  requirement_unmet=%s  naive_false_success=%s  verify_catches=%s  verify_names_missing=%s"
          % ("PASS" if ok else "FAIL", model_claims_done, requirement_unmet, naive_false_success, verify_catches, verify_names_missing))
    return ok


def main():
    p = argparse.ArgumentParser(description="Verified termination: verify a run against an objective, checkable success predicate before accepting it as complete, because a model's self-reported 'done' routinely overstates what was accomplished -- so trusting the claim returns false successes, while checking the predicate catches the unmet requirement and names exactly what is missing.")
    p.add_argument("--report", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("required=%d  completed=%d  file=%s  (the goal, progress, and claim are a fixture)"
          % (len(data["required"]), len(data["completed"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.report:
        report_view(data)
    elif args.verify:
        verify_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
