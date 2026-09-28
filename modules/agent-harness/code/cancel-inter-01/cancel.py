"""Cancel the outstanding tool calls when a turn is aborted -- don't just stop awaiting them -- because a running call left alone finishes anyway, spending budget and, if it is effectful, applying a side effect the abandoned run no longer wants.

A harness fires several tool calls in parallel and waits. Then the turn ends early: the user interrupts, a deadline fires, an error aborts the loop, or one call returns a result that makes the rest unnecessary. At that instant some calls are done and some are still running, and the harness has to decide what to do with the ones still running.

The lazy answer is to stop waiting -- drop the futures, return, move on. But stopping the wait does not stop the work. A fire-and-forget call keeps executing in the background to completion: it finishes its computation, spends its tokens or its API quota, and if it has a side effect it carries that effect out. The agent was interrupted, but the email it was in the middle of sending still sends; the order still places; the file still writes. The run is gone and its actions are not.

That is the real danger, sharper than the wasted compute: an effectful call outliving the run that requested it performs an action nobody is waiting for and nobody expected, because the decision to make that call was part of a plan that has since been abandoned. Wasted tokens are money; an unwanted side effect is a wrong action in the world.

Active cancellation fixes both. When the turn aborts, the harness sends a cancel to every outstanding call, so the running work stops instead of completing: no more budget spent, and the pending side effects are prevented (or, for effects already partly applied, handed to compensation). Cancellation has to be an explicit step the harness performs, because the default behavior of an unawaited call is to run to completion, not to stop.

The rule: on abort, actively cancel the still-running tool calls rather than merely stopping the wait -- because an unawaited call runs to completion anyway, spending budget and applying its side effect, so only cancellation stops the wasted work and prevents the effect the abandoned run no longer wants.

On this fixture four calls are in flight when the turn aborts -- one done, three still running, two of them effectful. Fire-and-forget lets all three running calls complete and applies two unwanted side effects; active cancel stops the three and prevents both effects. This computes both.

  --state     each in-flight call: done or running, effectful, and its fate under fire-and-forget vs cancel
  --impact    the wasted work and the unwanted side effects each policy leaves behind
  --check     fire-and-forget lets running effectful calls apply their side effects; cancel stops them

calls is the fixture; the running set, wasted work, and applied side effects under each policy are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "cancel.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def running(calls):
    """Calls still in progress at the moment the turn aborts."""
    return [c for c in calls if not c["done"]]


def fire_and_forget(calls):
    """Stop awaiting, but the running calls complete anyway -- work done, effects applied."""
    run = running(calls)
    return {"completed_after_abort": [c["id"] for c in run],
            "side_effects_applied": [c["id"] for c in run if c["effectful"]]}


def active_cancel(calls):
    """Cancel the running calls -- they stop, so no extra work and no pending effects."""
    return {"completed_after_abort": [], "side_effects_applied": []}


# ----------------------------------------------------------------- printing

def state_view(data):
    calls = data["calls"]
    print("STATE — in-flight calls at the abort, and their fate under each policy")
    print("-" * 66)
    print("  id    status    effectful   fire-and-forget   cancel")
    for c in calls:
        if c["done"]:
            faf = cxl = "already done"
        else:
            faf = "runs to done" + ("*" if c["effectful"] else "")
            cxl = "stopped"
        print("  %-4s  %-8s  %-9s   %-15s   %s"
              % (c["id"], "done" if c["done"] else "running", c["effectful"], faf, cxl))
    print("-" * 66)
    print("  * a running effectful call that completes applies its side effect")


def impact_view(data):
    calls = data["calls"]
    faf = fire_and_forget(calls)
    cxl = active_cancel(calls)
    print("IMPACT — what each policy leaves behind after the abort")
    print("-" * 60)
    print("  fire-and-forget: %d calls keep running, %d side effects applied %s"
          % (len(faf["completed_after_abort"]), len(faf["side_effects_applied"]), faf["side_effects_applied"]))
    print("  active cancel:   %d calls keep running, %d side effects applied %s"
          % (len(cxl["completed_after_abort"]), len(cxl["side_effects_applied"]), cxl["side_effects_applied"]))
    print("-" * 60)
    print("  cancel turns wasted work and unwanted effects into nothing")


def check(data):
    print("SELF-TEST — fire-and-forget lets running effectful calls apply their side effects; cancel stops them")
    print("-" * 108)
    calls = data["calls"]
    run = running(calls)
    faf = fire_and_forget(calls)
    cxl = active_cancel(calls)

    some_running = len(run) > 0
    print("  some calls are still running at the abort = %s (%s)" % (some_running, [c["id"] for c in run]))

    faf_completes_running = set(faf["completed_after_abort"]) == set(c["id"] for c in run)
    print("  fire-and-forget lets every running call finish = %s" % faf_completes_running)

    faf_applies_effects = len(faf["side_effects_applied"]) > 0
    print("  fire-and-forget applies unwanted side effects = %s (%s)" % (faf_applies_effects, faf["side_effects_applied"]))

    cancel_stops_all = cxl["completed_after_abort"] == []
    print("  active cancel stops every running call = %s" % cancel_stops_all)

    cancel_prevents_effects = cxl["side_effects_applied"] == []
    print("  active cancel prevents all pending side effects = %s" % cancel_prevents_effects)

    ok = (some_running and faf_completes_running and faf_applies_effects
          and cancel_stops_all and cancel_prevents_effects)
    print("-" * 108)
    print("SELF-TEST %s  some_running=%s  faf_completes_running=%s  faf_applies_effects=%s  cancel_stops_all=%s  cancel_prevents_effects=%s"
          % ("PASS" if ok else "FAIL", some_running, faf_completes_running,
             faf_applies_effects, cancel_stops_all, cancel_prevents_effects))
    return ok


def main():
    p = argparse.ArgumentParser(description="Tool-call cancellation: on abort, actively cancel the still-running tool calls rather than merely stopping the wait -- because an unawaited call runs to completion anyway, spending budget and applying its side effect, so only cancellation stops the wasted work and prevents the effect the abandoned run no longer wants.")
    p.add_argument("--state", action="store_true")
    p.add_argument("--impact", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    n = len(data["calls"])
    r = len(running(data["calls"]))
    print("calls=%d  running_at_abort=%d  file=%s  (the in-flight calls are a fixture)" % (n, r, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.state:
        state_view(data)
    elif args.impact:
        impact_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
