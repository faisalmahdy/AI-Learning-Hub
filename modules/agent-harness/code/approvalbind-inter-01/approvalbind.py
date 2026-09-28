"""Bind a confirmation to the exact call it approved -- a human 'yes' for deleting a scratch file must not authorize deleting the final report, so if the pending call changed after approval, gate it again.

Gating irreversible tools decides which calls need a human's approval. It does not, by itself, guarantee that the call the human approved is the call that runs. Those are two different properties, and the second is the one an attacker or a flaky model breaks.

The gap opens between the approval and the execution. The human sees a call, approves it, and the harness carries that approval to the moment it fires the tool. In between, the pending call can change: the model regenerates the step with different arguments, a state compaction reshuffles things, or -- the case that matters for security -- an instruction injected through a tool result rewrites the arguments. If the approval is a standing boolean the harness holds, it authorizes whatever call is pending when the tool fires, not the call the human actually saw.

So a 'yes' meant for delete_file('scratch_draft.csv') becomes authorization for delete_file('2024_final_audited.csv'), because the harness never checked that the call still matched what was approved. The confirmation gate did its job -- it asked -- and was defeated anyway, because the answer was applied to a different question.

The fix is to bind the approval to the exact call. Fingerprint the approved call (a hash over its canonical tool name and arguments) and store that with the approval. At execution, recompute the fingerprint of the call actually about to run; execute only if it matches the approved fingerprint, and if it does not, discard the approval and gate again. An unchanged call still passes, so there is no extra friction on the normal path; only a call that changed after approval is stopped.

On this fixture the human approved deleting a scratch file, but the pending call's path has been rewritten to the final audited report. This computes what each harness executes.

  --naive    the approval is a boolean; the harness runs whatever is pending -- the rewritten, unapproved delete
  --bound    the approval is bound to the approved call's fingerprint; the changed call fails the check and is re-gated
  --check    the pending call differs from what was approved, the naive harness runs it anyway, and the bound harness blocks it while still allowing an unchanged call

approved_call and pending_call are the fixture; the fingerprints and what each harness executes are computed. Stdlib only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "approvalbind.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def fingerprint(call):
    """A stable hash over the call's canonical tool name and arguments -- the identity the approval binds to."""
    canonical = json.dumps(call, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def naive_execute(pending_call, approved_flag):
    """BUG: a boolean approval authorizes whatever call is pending when the tool fires."""
    if approved_flag:
        return {"ran": True, "call": pending_call}
    return {"ran": False, "call": None}


def bound_execute(pending_call, approved_fingerprint):
    """FIX: execute only if the pending call's fingerprint still matches the approved one."""
    if fingerprint(pending_call) == approved_fingerprint:
        return {"ran": True, "call": pending_call, "regated": False}
    return {"ran": False, "call": None, "regated": True}   # call changed -> approval void, gate again


# ----------------------------------------------------------------- printing

def _path(call):
    return call["args"]["path"] if call else None


def naive_view(data):
    approved, pending = data["approved_call"], data["pending_call"]
    result = naive_execute(pending, approved_flag=True)   # the human said yes (to the approved call)
    print("NAIVE — the approval is a boolean the harness carries to execution")
    print("-" * 64)
    print("  human approved : %s(%s)" % (approved["tool"], _path(approved)))
    print("  pending at exec: %s(%s)" % (pending["tool"], _path(pending)))
    print("  executed       : %s(%s)" % (result["call"]["tool"], _path(result["call"])))
    print("-" * 64)
    print("  the 'yes' for the scratch file authorized deleting the final report")


def bound_view(data):
    approved, pending = data["approved_call"], data["pending_call"]
    approved_fp = fingerprint(approved)
    changed = bound_execute(pending, approved_fp)
    unchanged = bound_execute(approved, approved_fp)
    print("BOUND — the approval is bound to the approved call's fingerprint")
    print("-" * 64)
    print("  approved fingerprint : %s  (%s)" % (approved_fp, _path(approved)))
    print("  pending fingerprint  : %s  (%s)" % (fingerprint(pending), _path(pending)))
    print("  changed call  -> ran=%s  regated=%s" % (changed["ran"], changed["regated"]))
    print("  unchanged call-> ran=%s" % unchanged["ran"])
    print("-" * 64)
    print("  the rewritten call fails the match and is gated again; an unchanged call still passes")


def check(data):
    print("SELF-TEST — the pending call differs from what was approved, the naive harness runs it anyway, and the bound harness blocks it while still allowing an unchanged call")
    print("-" * 112)
    approved, pending = data["approved_call"], data["pending_call"]
    approved_fp = fingerprint(approved)

    approved_and_pending_differ = approved != pending
    print("  the pending call differs from the approved call = %s (%s vs %s)" % (approved_and_pending_differ, _path(approved), _path(pending)))

    fingerprints_differ = fingerprint(approved) != fingerprint(pending)
    print("  their fingerprints differ = %s (%s vs %s)" % (fingerprints_differ, approved_fp, fingerprint(pending)))

    naive_runs_unapproved = naive_execute(pending, True)["call"] == pending
    print("  the naive harness executes the unapproved (changed) call = %s (%s)" % (naive_runs_unapproved, _path(pending)))

    bound_blocks_changed = bound_execute(pending, approved_fp)["ran"] is False
    print("  the bound harness blocks the changed call and re-gates = %s" % bound_blocks_changed)

    bound_allows_unchanged = bound_execute(approved, approved_fp)["ran"] is True
    print("  the bound harness still runs an unchanged, approved call = %s" % bound_allows_unchanged)

    ok = (approved_and_pending_differ and fingerprints_differ and naive_runs_unapproved
          and bound_blocks_changed and bound_allows_unchanged)
    print("-" * 112)
    print("SELF-TEST %s  approved_and_pending_differ=%s  fingerprints_differ=%s  naive_runs_unapproved=%s  bound_blocks_changed=%s  bound_allows_unchanged=%s"
          % ("PASS" if ok else "FAIL", approved_and_pending_differ, fingerprints_differ, naive_runs_unapproved,
             bound_blocks_changed, bound_allows_unchanged))
    return ok


def main():
    p = argparse.ArgumentParser(description="Approval binding: bind a human confirmation to a fingerprint of the exact tool call approved (tool name plus arguments) and re-verify it at execution, because a boolean approval authorizes whatever call is pending when the tool fires -- so a call rewritten after approval (by a model re-plan or an injected instruction) runs unapproved unless the harness gates it again.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--bound", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("approved=%s(%s)  pending=%s(%s)  file=%s  (these are a fixture)"
          % (data["approved_call"]["tool"], data["approved_call"]["args"]["path"],
             data["pending_call"]["tool"], data["pending_call"]["args"]["path"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.bound:
        bound_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
