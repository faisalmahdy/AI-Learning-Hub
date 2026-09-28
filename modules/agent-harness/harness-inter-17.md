---
id: harness-inter-17
title: Checkpoint the completed steps — or a crash restarts the plan and re-runs every side effect
topic: agent-harness
level: intermediate
status: ready
time: 19 min
summary: A long agent plan runs step by step, and each step has a side effect on the outside world — charge a card, send an email, write a row. Processes die (a deploy, an OOM kill, a lost node) and the harness restarts the plan. The question is where it restarts. A harness that keeps no record of progress can only begin at the top, so it re-runs the steps it already completed and their effects fire a second time — the card is charged twice. The fix is to checkpoint: after each step commits, durably record it done, and on restart skip the completed steps and resume at the first incomplete one, so each effect fires exactly once across the crash. On a five-step plan that crashes after three, restarting with no checkpoint re-runs all five — eight executions, three double-charges — while restarting from a checkpoint resumes at step four for five executions and zero doubles.
eli5: Imagine following a checklist and someone yanks you away after three items. If you lost the checklist, you would start over and do the first three again — paying twice for things already done. If you kept the list with checkmarks, you would glance at it and pick up at item four. An agent that saves its checkmarks resumes where it stopped; one that does not repeats work that already happened for real.
---

## Why this module

An agent plan that touches the outside world cannot be safely restarted from the top, and "from the top" is the only place a harness with no memory of progress can begin.

Each step in the plan does something real — charges a card, sends a ticket, writes a booking. Processes die mid-plan for reasons that have nothing to do with the plan: a deploy rolls the pod, the node is lost, the OOM killer fires. The harness restarts. If it kept no record of which steps finished, it has one option: run the plan again from step one. Now every completed step executes a second time and its side effect fires again — a double charge, a duplicate email. The plan reports success, but it has caused real-world damage a correct run never should.

**A restart with no memory of progress is not a resume — it is a replay, and a replay re-fires every side effect the first run already committed.**

The fix is to checkpoint: after a step commits its effect, durably record that it is done, and on restart skip the recorded steps and resume at the first incomplete one. Each effect then fires exactly once across the crash. This module runs a plan through a crash both ways and counts how many times each step's effect fires.

## Concepts

A **step** is one unit of the plan with a side effect. A **checkpoint** is a durable record — on disk, in a database — that a given step has completed. Durable means it survives the crash; that is the whole point.

The **no-checkpoint** harness has no such record. On restart it begins at step 0, so every step that ran before the crash runs again. The **checkpoint** harness reads its record on restart, skips the completed steps, and resumes at the first incomplete one.

The critical ordering is that the checkpoint for a step is written **after** the step's effect commits. Then a step is marked done only once it truly is, so resume never skips a step that did not finish and never repeats one that did. Write the checkpoint before the effect and a crash in between loses the effect; write it after and a crash in between merely repeats the resume-safe read.

The trap is assuming a crash is rare enough to ignore, or that "just restart it" is harmless. Restart is harmless only for a plan with no side effects. The moment a step charges money or sends a message, replay is a correctness bug, and crashes are not rare at scale — they are a Tuesday.

**Checkpointing turns restart from a replay into a resume: the completed work is remembered, so its side effects are not repeated.**

The safe ordering is do-then-record: commit the step's effect, then write its checkpoint, so a crash in the gap costs at most one re-run and never a lost effect.

<svg role="img" aria-label="A step's timeline: commit the effect first, then write the checkpoint; a crash after the checkpoint resumes past the step" viewBox="0 0 300 100" width="300" height="100">
  <line x1="20" y1="45" x2="280" y2="45" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="80" cy="45" r="5" fill="var(--s2)"/>
  <text x="45" y="30" fill="var(--s2)" font-size="8">commit effect</text>
  <circle cx="200" cy="45" r="5" fill="var(--ink)"/>
  <text x="165" y="30" fill="var(--ink)" font-size="8">write checkpoint</text>
  <line x1="80" y1="45" x2="200" y2="45" stroke="var(--s1)" stroke-width="2"/>
  <text x="95" y="70" fill="var(--s1)" font-size="7">crash here → step replays (needs idempotency)</text>
  <text x="205" y="70" fill="var(--muted)" font-size="7">crash here → resume past step</text>
</svg>
^ The effect is committed before the checkpoint is written, so a crash after the checkpoint resumes cleanly and a crash in the narrow gap only replays the step — never loses it.

This is the core of durable workflow engines — they persist each step's completion and result so a worker that dies mid-workflow is replaced by one that continues, not one that starts over.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-17/checkpoint.py

The fixture is a five-step booking plan that crashes after completing three steps.

```json filename=modules/agent-harness/code/harness-inter-17/plan.json:1-6 COMPLETE
{
  "_meta": "A sequential agent plan whose steps each have a side effect (charge a card, send an email, write a row). The process runs the steps in order, but crashes after completing some of them: completed_before is how many steps finished before the crash. Then the harness restarts. The question: on restart, does it re-run the steps it already completed, or resume where it left off?",
  "steps": ["reserve_seat", "charge_card", "send_ticket", "log_booking", "notify_ops"],
  "completed_before": 3
}
```

The two harnesses differ in one line: what the restart runs. No-checkpoint restarts over the whole plan; checkpoint restarts at the first incomplete step.

```python filename=modules/agent-harness/code/harness-inter-17/checkpoint.py:41-59 COMPLETE
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
```

Run `--replay` and watch what each restart executes.

```text filename=--replay
REPLAY — executions across the crash (crash after 3 of 5 steps)
------------------------------------------------------------------
  no checkpoint  first run:  ['reserve_seat', 'charge_card', 'send_ticket']
                 -- crash, restart --
                 restart:    ['reserve_seat', 'charge_card', 'send_ticket', 'log_booking', 'notify_ops']
  checkpoint     first run:  ['reserve_seat', 'charge_card', 'send_ticket']
                 -- crash, restart --
                 restart:    ['log_booking', 'notify_ops']
------------------------------------------------------------------
  no checkpoint restarts at the top; the checkpoint resumes after step 3.
```

Both first runs complete the same three steps and crash. On restart, the no-checkpoint harness runs all five — repeating reserve, charge, and send — while the checkpoint harness runs only the two that never happened. The word "restart" hides the difference; the executed lists reveal it.

<svg role="img" aria-label="No-checkpoint restart re-runs steps 1 to 3 then 4 to 5; checkpoint restart runs only steps 4 to 5" viewBox="0 0 300 140" width="300" height="140">
  <text x="10" y="16" fill="var(--muted)" font-size="8">no checkpoint</text>
  <text x="10" y="30" fill="var(--muted)" font-size="7">first run</text>
  <rect x="70" y="22" width="40" height="12" fill="var(--s2)"/><rect x="112" y="22" width="40" height="12" fill="var(--s2)"/><rect x="154" y="22" width="40" height="12" fill="var(--s2)"/>
  <text x="10" y="48" fill="var(--s1)" font-size="7">restart</text>
  <rect x="70" y="40" width="40" height="12" fill="none" stroke="var(--s1)" stroke-width="1"/><rect x="112" y="40" width="40" height="12" fill="none" stroke="var(--s1)" stroke-width="1"/><rect x="154" y="40" width="40" height="12" fill="none" stroke="var(--s1)" stroke-width="1"/><rect x="196" y="40" width="40" height="12" fill="var(--s2)"/><rect x="238" y="40" width="40" height="12" fill="var(--s2)"/>
  <text x="70" y="64" fill="var(--s1)" font-size="7">steps 1-3 re-run (double effects)</text>
  <line x1="10" y1="78" x2="290" y2="78" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="94" fill="var(--muted)" font-size="8">checkpoint</text>
  <text x="10" y="108" fill="var(--muted)" font-size="7">first run</text>
  <rect x="70" y="100" width="40" height="12" fill="var(--s2)"/><rect x="112" y="100" width="40" height="12" fill="var(--s2)"/><rect x="154" y="100" width="40" height="12" fill="var(--s2)"/>
  <text x="10" y="126" fill="var(--muted)" font-size="7">restart</text>
  <rect x="196" y="118" width="40" height="12" fill="var(--s2)"/><rect x="238" y="118" width="40" height="12" fill="var(--s2)"/>
  <text x="70" y="138" fill="var(--muted)" font-size="7">resumes at step 4 — no repeats</text>
</svg>
^ The no-checkpoint restart (hollow boxes) re-executes the three completed steps before continuing; the checkpoint restart resumes directly at step 4.

## Build

The counts view tallies each step's firings under both strategies and flags the doubled ones.

```python filename=modules/agent-harness/code/harness-inter-17/checkpoint.py:77-86 COMPLETE
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
```

Count the side-effect firings with `--counts` — this is where the replay becomes a bug.

```text filename=--counts
COUNTS — times each step's side effect fires
------------------------------------------------------------------
  step           no-checkpoint   checkpoint
  reserve_seat          2             1  <- double!
  charge_card           2             1  <- double!
  send_ticket           2             1  <- double!
  log_booking           1             1
  notify_ops            1             1
------------------------------------------------------------------
  total: no-checkpoint 8, checkpoint 5
```

The no-checkpoint plan fires eight side effects for a five-step plan: reserve, charge, and send each happen twice. `charge_card` twice is a duplicate charge — a real financial bug, not a wasted cycle. The checkpoint plan fires exactly five, one per step. The three extra executions are precisely the three steps completed before the crash, replayed.

<svg role="img" aria-label="Side-effect firings: no-checkpoint total 8 with three steps doubled, checkpoint total 5 all singles" viewBox="0 0 300 120" width="300" height="120">
  <line x1="90" y1="12" x2="90" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="90" y1="90" x2="285" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <rect x="90" y="30" width="160" height="16" fill="var(--s1)"/>
  <text x="10" y="42" fill="var(--muted)" font-size="8">no-checkpoint</text>
  <text x="255" y="42" fill="var(--muted)" font-size="8">8 fires</text>
  <rect x="90" y="58" width="100" height="16" fill="var(--s2)"/>
  <text x="10" y="70" fill="var(--muted)" font-size="8">checkpoint</text>
  <text x="195" y="70" fill="var(--muted)" font-size="8">5 fires</text>
  <text x="90" y="108" fill="var(--muted)" font-size="8">the 3 extra fires are the completed steps, charged again</text>
</svg>
^ Eight side effects versus five: the three-firing gap is exactly the completed steps replayed, and one of them is a second charge.

## Definition of done

The self-test pins the replay and the fix: no-checkpoint re-runs some steps, its total exceeds the step count, the checkpoint resumes at the crash point, runs every step exactly once, and both eventually complete all steps.

```python filename=modules/agent-harness/code/harness-inter-17/checkpoint.py:101-114 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — no checkpoint re-runs completed steps; the checkpoint resumes and runs each exactly once
--------------------------------------------------------------------------------------------------------
  no-checkpoint runs some steps more than once = True (['reserve_seat', 'charge_card', 'send_ticket'])
  no-checkpoint total executions exceed the step count = True (8 > 5)
  the checkpoint resumes at the first incomplete step = True (step 3)
  the checkpoint runs every step exactly once = True (total 5)
  both strategies eventually complete every step = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  no_checkpoint_reexecutes=True  no_checkpoint_total_exceeds=True  checkpoint_resumes_at_crash=True  checkpoint_each_once=True  both_complete=True
```

**Done means the replay damage is counted, not hand-waved: the no-checkpoint run fires 8 effects for 5 steps — the 3 completed steps charged again — while the checkpoint run fires exactly 5.**

## Boss fight

The checkpoint resumes cleanly here. Predict what breaks if the crash happens between a step's effect committing and its checkpoint being written. It is tempting to think the checkpoint always saves you.

That gap is the one hard case, and it is why checkpointing alone is not enough. If `charge_card` commits but the process dies before the checkpoint records it, the resume sees the step as incomplete and runs it again — a double charge, the exact bug you were fixing, just narrowed to a tiny window. You cannot make "commit effect" and "write checkpoint" a single atomic action across two systems (the payment API and your store). So durable systems pair checkpointing with idempotency: each step carries an idempotency key so that re-running a committed step is a no-op at the effect's owner. Checkpointing minimizes replays; idempotency makes the unavoidable replay harmless.

The mirror-image mistake is checkpointing to non-durable storage — an in-memory set, a local temp file on the pod that dies with it. If the checkpoint does not survive the crash, the restart reads nothing and replays everything, and you have paid the cost of checkpointing with none of the benefit. The checkpoint has to outlive the process, which means shared durable storage, not process memory.

```python filename=modules/agent-harness/code/harness-inter-17/checkpoint.py:48-52 COMPLETE
def run_checkpoint(steps, completed_before):
    """First run completes some steps and checkpoints each; restart resumes at the first incomplete step."""
    first = list(range(completed_before))          # steps done and checkpointed before the crash
    restart = list(range(completed_before, len(steps)))   # resume after the last completed step
    return first, restart
```

**Checkpoint each completed step to durable storage and make each step idempotent: the checkpoint turns replay into resume, and idempotency makes the one replay the crash can still force do no harm.**

## External resources

The Temporal and AWS Step Functions documentation on durable execution — workflows persist each step's completion and result so a crashed worker resumes rather than restarts, the production form of this module.

The saga and workflow chapters of "Designing Data-Intensive Applications" (Kleppmann) — why exactly-once effects require durable progress plus idempotency, the boss-fight pairing.

The write-ahead log / checkpoint literature (any database-internals text) — the "write the record after the effect commits" ordering that makes resume safe, generalized from crash recovery.
