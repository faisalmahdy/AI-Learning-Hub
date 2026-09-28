"""Emit a tool_result for every tool_use id the model produced -- a call the harness declines or cannot run still needs its result block, or the provider rejects the next request as malformed and the run aborts.

A provider that speaks tool calls enforces a structural rule on the transcript: an assistant message that contains tool_use blocks must be immediately followed by a user message whose tool_result blocks answer every one of those ids. The pairing is on ids, not on outcomes. Each tool_use must have exactly one matching tool_result, and there must be no tool_result for an id that was never requested. If those two conditions do not hold, the message is malformed and the next request is rejected before the model ever runs.

The trap is that "answer every id" includes the calls the harness did not execute. A call gated as irreversible and declined, a call whose name the harness does not recognize, a call skipped because a per-tool budget is spent -- none of these did any work, so it feels natural to append nothing for them. But the assistant turn still carries their tool_use blocks, and leaving them unanswered dangles those ids. The provider sees tool_use ids with no answering tool_result and rejects the whole turn, aborting a run in which most of the calls actually succeeded.

So the disposition of a call -- run, decline, unknown, over-budget -- decides the CONTENT of its tool_result, never whether one exists. A declined call gets a result saying it was refused; an unknown name gets a result saying no such tool; a normal call gets its real observation. Every id in, every id back out, one for one.

The rule: emit exactly one tool_result for every tool_use id in the turn -- including the calls you decline, cannot resolve, or skip -- because the provider validates the transcript on id coverage, not on whether work was done, and a single dangling id rejects the entire next request.

On this fixture the model emits four tool_use blocks: two to run, one declined as irreversible, one an unknown name. A naive harness answers only the two it ran and leaves two ids dangling, so the turn is malformed; a correct harness answers all four and the turn is well-formed. This computes both.

  --coverage    each tool_use id and whether it gets a tool_result under the naive vs the correct harness
  --wellformed  whether the turn is well-formed (bijection between tool_use ids and tool_result ids), naive vs correct
  --check       a harness that answers only executed calls dangles the declined and unknown ids; answering every id is well-formed

calls is the fixture; the result sets, dangling ids, and well-formedness are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "resultcover.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_results(calls):
    """A naive harness emits a tool_result only for calls it actually executed."""
    return [c["id"] for c in calls if c["disposition"] == "run"]


def correct_results(calls):
    """A correct harness emits one tool_result for every id, whatever its disposition."""
    return [c["id"] for c in calls]


def dangling(calls, result_ids):
    """tool_use ids left with no answering tool_result -- what the provider rejects on."""
    answered = set(result_ids)
    return [c["id"] for c in calls if c["id"] not in answered]


def well_formed(calls, result_ids):
    """A turn is well-formed iff the tool_use ids and tool_result ids are a bijection."""
    use_ids = [c["id"] for c in calls]
    return sorted(use_ids) == sorted(result_ids)


# ----------------------------------------------------------------- printing

def coverage_view(data):
    calls = data["calls"]
    naive = set(naive_results(calls))
    correct = set(correct_results(calls))
    print("COVERAGE — does each tool_use id get a tool_result?")
    print("-" * 66)
    print("  id         name            disposition   naive   correct")
    for c in calls:
        print("  %-9s  %-14s  %-11s   %-5s   %s"
              % (c["id"], c["name"], c["disposition"],
                 c["id"] in naive, c["id"] in correct))
    print("-" * 66)
    print("  the naive harness only answers the calls it ran; the correct one answers all")


def wellformed_view(data):
    calls = data["calls"]
    nr, cr = naive_results(calls), correct_results(calls)
    print("WELL-FORMED — is the tool_use / tool_result pairing a bijection?")
    print("-" * 64)
    print("  tool_use ids: %s" % [c["id"] for c in calls])
    print("  naive   results=%s  dangling=%s  well_formed=%s"
          % (nr, dangling(calls, nr), well_formed(calls, nr)))
    print("  correct results=%s  dangling=%s  well_formed=%s"
          % (cr, dangling(calls, cr), well_formed(calls, cr)))
    print("-" * 64)
    print("  a single dangling id makes the provider reject the whole next request")


def check(data):
    print("SELF-TEST — a harness that answers only executed calls dangles the declined and unknown ids; answering every id is well-formed")
    print("-" * 128)
    calls = data["calls"]
    nr, cr = naive_results(calls), correct_results(calls)
    nd, cd = dangling(calls, nr), dangling(calls, cr)

    naive_has_dangling = len(nd) > 0
    print("  naive: some tool_use ids have no tool_result = %s (%s)" % (naive_has_dangling, nd))

    naive_malformed = not well_formed(calls, nr)
    print("  naive: the turn is malformed (not a bijection) = %s" % naive_malformed)

    dangling_are_nonrun = set(nd) == set(c["id"] for c in calls if c["disposition"] != "run")
    print("  naive: exactly the non-executed calls dangle = %s" % dangling_are_nonrun)

    correct_no_dangling = len(cd) == 0
    print("  correct: every tool_use id has a tool_result = %s" % correct_no_dangling)

    correct_wellformed = well_formed(calls, cr)
    print("  correct: the turn is well-formed (bijection) = %s" % correct_wellformed)

    ok = (naive_has_dangling and naive_malformed and dangling_are_nonrun
          and correct_no_dangling and correct_wellformed)
    print("-" * 128)
    print("SELF-TEST %s  naive_has_dangling=%s  naive_malformed=%s  dangling_are_nonrun=%s  correct_no_dangling=%s  correct_wellformed=%s"
          % ("PASS" if ok else "FAIL", naive_has_dangling, naive_malformed, dangling_are_nonrun, correct_no_dangling, correct_wellformed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Tool-result coverage: emit exactly one tool_result for every tool_use id in the turn -- including the calls you decline, cannot resolve, or skip -- because the provider validates the transcript on id coverage, not on whether work was done, and a single dangling id rejects the entire next request.")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--wellformed", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    calls = data["calls"]
    print("calls=%d  run=%d  decline=%d  unknown=%d  file=%s  (the calls are a fixture)"
          % (len(calls),
             sum(c["disposition"] == "run" for c in calls),
             sum(c["disposition"] == "decline" for c in calls),
             sum(c["disposition"] == "unknown" for c in calls),
             DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.coverage:
        coverage_view(data)
    elif args.wellformed:
        wellformed_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
