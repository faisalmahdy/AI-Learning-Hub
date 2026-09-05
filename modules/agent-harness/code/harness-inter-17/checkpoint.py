"""Checkpoint the completed steps, or a crash restarts the plan and re-runs every side effect.

A long agent plan runs step by step, and each step has a side effect that touches the outside world: charge
a card, send an email, write a row. Processes die -- a deploy, an OOM kill, a lost node -- and the harness
restarts the plan. The question is where it restarts. A harness that keeps no record of progress has only one
place to begin: the top. So on restart it re-runs the steps it already completed, and their side effects fire
a SECOND time -- the card is charged twice, the ticket is emailed twice. The plan does eventually finish, but
it has done real-world damage that a "successful" run should never cause.

The fix is to checkpoint: after each step completes, durably record that it is done. On restart, read the
checkpoint and skip the steps already marked complete, resuming at the first incomplete one. Now each step's
effect fires exactly once across the crash, because the completed work is remembered rather than repeated. The
checkpoint must be durable (survive the crash) and written after the step's effect commits, so a step is only
marked done once it truly is. This is how durable workflow engines turn a crashy process into an
exactly-once plan.

On this fixture the plan has five steps and the process crashes after completing three. Restarting with no
checkpoint re-runs all five, so the first three steps execute twice -- eight executions, three double-charges.
Restarting from a checkpoint resumes at step four, so every step executes exactly once -- five executions,
zero double-charges. This computes both.

  --replay     the executions each strategy performs across the crash and restart, step by step
  --counts     how many times each step runs, and the total, for no-checkpoint vs checkpoint
  --check      no checkpoint re-runs completed steps; the checkpoint resumes and runs each exactly once

The steps and the crash point are the fixture; every execution is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "plan.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run_no_checkpoint(steps, completed_before):
    """First run completes some steps, crashes; restart begins again at step 0 (no memory of progress)."""
    first = list(range(completed_before))          # steps done before the crash
    restart = list(range(len(steps)))              # nothing remembered -> start over from the top
    return first, restart


def run_checkpoint(steps, completed_before):
    """First run completes some steps and checkpoints each; restart resumes at the first incomplete step."""
    first = list(range(completed_before))          # steps done and checkpointed before the crash
    restart = list(range(completed_before, len(steps)))   # resume after the last completed step
    return first, restart


def exec_counts(first, restart, n):
    counts = {i: 0 for i in range(n)}
    for i in first + restart:
        counts[i] += 1
    return counts


# ----------------------------------------------------------------- printing

def replay_view(data):
    steps, cb = data["steps"], data["completed_before"]
    print("REPLAY — executions across the crash (crash after %d of %d steps)" % (cb, len(steps)))
    print("-" * 66)
    for label, runner in (("no checkpoint", run_no_checkpoint), ("checkpoint", run_checkpoint)):
        first, restart = runner(steps, cb)
        print("  %-14s first run:  %s" % (label, [steps[i] for i in first]))
        print("  %-14s -- crash, restart --" % "")
        print("  %-14s restart:    %s" % ("", [steps[i] for i in restart]))
        print("-" * 66)
    print("  no checkpoint restarts at the top; the checkpoint resumes after step %d." % cb)


def counts_view(data):
    steps, cb = data["steps"], data["completed_before"]
    n = len(steps)
    nc = exec_counts(*run_no_checkpoint(steps, cb), n)
    ck = exec_counts(*run_checkpoint(steps, cb), n)
    print("COUNTS — times each step's side effect fires")
    print("-" * 66)
    print("  %-14s no-checkpoint   checkpoint" % "step")
    for i, name in enumerate(steps):
        flag = "  <- double!" if nc[i] > 1 else ""
        print("  %-14s %8d %13d%s" % (name, nc[i], ck[i], flag))
    print("-" * 66)
    print("  total: no-checkpoint %d, checkpoint %d" % (sum(nc.values()), sum(ck.values())))


def check(data):
    print("SELF-TEST — no checkpoint re-runs completed steps; the checkpoint resumes and runs each exactly once")
    print("-" * 104)
    steps, cb = data["steps"], data["completed_before"]
    n = len(steps)
    nc = exec_counts(*run_no_checkpoint(steps, cb), n)
    ck = exec_counts(*run_checkpoint(steps, cb), n)
    _, ck_restart = run_checkpoint(steps, cb)

    no_checkpoint_reexecutes = any(nc[i] > 1 for i in range(n))
    doubled = [steps[i] for i in range(n) if nc[i] > 1]
    print("  no-checkpoint runs some steps more than once = %s (%s)" % (no_checkpoint_reexecutes, doubled))

    no_checkpoint_total_exceeds = sum(nc.values()) > n
    print("  no-checkpoint total executions exceed the step count = %s (%d > %d)" % (no_checkpoint_total_exceeds, sum(nc.values()), n))

    checkpoint_resumes_at_crash = ck_restart[0] == cb
    print("  the checkpoint resumes at the first incomplete step = %s (step %d)" % (checkpoint_resumes_at_crash, cb))

    checkpoint_each_once = all(ck[i] == 1 for i in range(n))
    print("  the checkpoint runs every step exactly once = %s (total %d)" % (checkpoint_each_once, sum(ck.values())))

    both_complete = set(range(n)) == {i for i in range(n) if nc[i] >= 1} == {i for i in range(n) if ck[i] >= 1}
    print("  both strategies eventually complete every step = %s" % both_complete)

    ok = no_checkpoint_reexecutes and no_checkpoint_total_exceeds and checkpoint_resumes_at_crash and checkpoint_each_once and both_complete
    print("-" * 104)
    print("SELF-TEST %s  no_checkpoint_reexecutes=%s  no_checkpoint_total_exceeds=%s  checkpoint_resumes_at_crash=%s  checkpoint_each_once=%s  both_complete=%s"
          % ("PASS" if ok else "FAIL", no_checkpoint_reexecutes, no_checkpoint_total_exceeds, checkpoint_resumes_at_crash, checkpoint_each_once, both_complete))
    return ok


def main():
    p = argparse.ArgumentParser(description="Checkpoint completed steps so a crash resumes the plan instead of replaying its side effects.")
    p.add_argument("--replay", action="store_true")
    p.add_argument("--counts", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steps=%d  completed_before_crash=%d  file=%s  (the plan and crash point are a fixture)"
          % (len(data["steps"]), data["completed_before"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.replay:
        replay_view(data)
    elif args.counts:
        counts_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
