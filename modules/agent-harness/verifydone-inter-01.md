---
id: verifydone-inter-01
title: Accept a run as done only when a checkable predicate holds — not because the model said "task complete"
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: An agent run ends with a final message — "done", "all tasks complete", a tidy summary — and the easiest thing for a harness to do is treat that message as the stop signal and return the model's result as a success. That is trusting the model's self-assessment of whether the goal was met, which is exactly the assessment models are worst at. A model loses track of a subtask across a long trace, mistakes a partial result for the whole, or simply asserts completion because the conversation reached a natural-feeling end — none of these are lies it knows it is telling, just the ordinary ways a plan drifts. But the harness that believes the claim reports the task done and hands back a result while part of the goal was never accomplished, and the failure is silent: nothing errored, the model was confident, and the only thing checked was its word. Downstream someone ships the report, closes the ticket, or triggers the next stage on a task that was never finished. The fix is to stop treating "done" as a claim and start treating it as a predicate the harness evaluates: define the success criterion as something checkable against the world or the run's own record — the required outputs exist, the required steps ran, the artifact passes its validator — and on the model's "done" evaluate that predicate, accepting termination only if it holds and otherwise continuing, retrying, or failing honestly. On a fixture where a task requires three steps, the agent completed two, and the final message claims completion, a harness that trusts the claim returns success while a harness that checks the predicate returns not-done and names the missing step.
eli5: Imagine you send a helper to do three chores: get the groceries, cook dinner, and take out the trash. When they come back they say "all done!" — and if you just believe them, you might not notice the trash is still sitting in the kitchen. They're not trying to trick you; they just forgot one and felt finished. The smart move is to have a little checklist and actually look: groceries here, dinner cooked, trash gone? You check the trash box and it's empty, so you know the job isn't really done and you can point to exactly what's left. Believing "all done" is easy but sometimes wrong; checking the list against what actually happened is what catches the missing chore.
---

## Why this module

Every agent run has to stop somewhere, and the model offers an obvious place: it announces that it is finished. The harness reads "task complete," takes the result, and reports success. This works often enough to be tempting and fails in exactly the cases that matter most — the long, complicated tasks where the model was most likely to lose the thread. The problem is that the stop signal and the success signal have been fused into one, and that one signal comes entirely from the party least able to judge it objectively.

Models declare completion prematurely for mundane reasons. Across a long trace a subtask scrolls out of attention and is forgotten. A partial result — two of three files written, the happy path handled but not the error case — reads as "the work," and the model summarizes it as done. Sometimes the conversation simply feels concluded and the model closes it out. In none of these is the model lying; it genuinely believes it finished. But belief is not verification, and the harness that accepts the belief inherits the error.

What makes this failure mode nasty is its silence. There is no exception, no timeout, no malformed output — just a confident "done" over an unfinished task, returned as a success. This module contrasts a harness that trusts the claim with one that checks a predicate, on a task whose success criterion is objectively unmet.

**A model's self-reported "done" routinely overstates what was accomplished, so a harness that returns success on the claim ships false completions — termination must be gated on an objective, checkable success predicate, not the model's word.**

## Concepts

The fixture is a task's success criterion (the steps it must accomplish), what the agent actually completed, and the model's final message.

```json filename=modules/agent-harness/code/verifydone-inter-01/verifydone.json:3-5 COMPLETE
  "required": ["fetch_data", "write_report", "send_email"],
  "completed": ["fetch_data", "write_report"],
  "self_report": {"done": true, "message": "All tasks complete."}
}
```

Two ways to decide the run is over. The naive path reads the model's claim: if it says done, it is done. The verified path ignores the claim and checks the predicate: done only if every required step actually appears in what was completed. A helper names the gap.

```python filename=modules/agent-harness/code/verifydone-inter-01/verifydone.py:32-43 COMPLETE
def missing_requirements(required, completed):
    return [r for r in required if r not in completed]


def naive_accept(self_report):
    """Trust the model's claim: done if it says done."""
    return bool(self_report.get("done"))


def verified_done(required, completed):
    """Check the predicate: done only if every required step was completed."""
    return all(r in completed for r in required)
```

The two functions read different inputs entirely. `naive_accept` looks only at the model's message and never at what happened; `verified_done` looks only at what happened and never at the message. That difference in what they trust is the whole module.

<svg role="img" aria-label="Two decision paths: the naive path reads the model's 'done' message and returns success; the verified path checks the required steps against completed steps, finds send_email missing, and returns not-done" viewBox="0 0 320 140">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">what each path looks at to decide 'done'</text>
  <text x="10" y="38" font-size="8" fill="var(--s2)">naive</text>
  <rect x="50" y="28" width="120" height="16" fill="none" stroke="var(--s2)"/><text x="56" y="39" font-size="7.5" fill="var(--ink)">reads: "All tasks complete."</text>
  <text x="180" y="39" font-size="8" fill="var(--s2)">→ success</text>
  <text x="10" y="72" font-size="8" fill="var(--s1)">verified</text>
  <g font-size="7">
  <rect x="50" y="58" width="34" height="14" fill="var(--s1)"/><text x="54" y="68" fill="var(--panel)">fetch ✓</text>
  <rect x="88" y="58" width="40" height="14" fill="var(--s1)"/><text x="92" y="68" fill="var(--panel)">report ✓</text>
  <rect x="132" y="58" width="40" height="14" fill="none" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="136" y="68" fill="var(--ink)">email ✗</text>
  </g>
  <text x="180" y="69" font-size="8" fill="var(--s1)">→ not done</text>
  <text x="10" y="104" font-size="7.5" fill="var(--ink)">the naive path never sees that send_email did not run</text>
  <text x="10" y="122" font-size="7.5" fill="var(--muted)">the predicate checks the world/record, not the claim</text>
</svg>
^ The naive path decides on the model's message and returns success; the verified path decides on the required-versus-completed steps, sees that send_email never ran, and returns not-done. They reach opposite conclusions because they trust opposite things.

**The naive check reads only the model's claim; the verified check reads only what actually happened — termination should depend on the second, never the first.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the termination check of an agent loop, reduced to a three-step task so the completion predicate is checkable by hand.

Run `--report` to see the goal, the progress, and the claim side by side.

```text filename=verifydone.py --report
  required steps  = ['fetch_data', 'write_report', 'send_email']
  completed steps = ['fetch_data', 'write_report']
  model says done = True ('All tasks complete.')
```

The task requires three steps. The agent completed two — fetch_data and write_report — and never ran send_email. Yet its final message is "All tasks complete." and its done flag is True. This is the whole failure in three lines: the claim and the reality disagree, and only one of them is checkable.

Now `--verify` decides termination both ways — it computes the naive acceptance, the verified predicate, and the gap in one place.

```python filename=modules/agent-harness/code/verifydone-inter-01/verifydone.py:60-65 COMPLETE
def verify_view(data):
    required, completed = data["required"], data["completed"]
    sr = data["self_report"]
    naive = naive_accept(sr)
    verified = verified_done(required, completed)
    missing = missing_requirements(required, completed)
```

The three lines it prints tell the whole story.

```text filename=verifydone.py --verify
  naive (accept model's 'done')     -> success = True
  verified (predicate over steps)   -> done    = False
  missing requirements              = ['send_email']
```

The naive harness returns success — it read "done" and stopped. The verified harness returns not-done, because send_email is required and absent from the completed steps, and it names exactly what is missing. The verified harness does not just reject the claim; it produces the actionable next step — the one thing left to do — which the harness can now retry, escalate, or report as an honest failure instead of a false success.

<svg role="img" aria-label="Outcome comparison: naive harness returns success on an unfinished task (false success), verified harness returns not-done and names send_email as missing" viewBox="0 0 320 110">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">termination outcome (task actually 2 of 3 done)</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">naive</text>
  <rect x="70" y="32" width="100" height="16" fill="var(--s2)"/><text x="84" y="44" font-size="8" fill="var(--panel)">SUCCESS</text>
  <text x="176" y="44" font-size="8" fill="var(--ink)">false — email never sent</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">verified</text>
  <rect x="70" y="62" width="100" height="16" fill="var(--s1)"/><text x="84" y="74" font-size="8" fill="var(--panel)">NOT DONE</text>
  <text x="176" y="74" font-size="8" fill="var(--ink)">missing: send_email</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">same run — the difference is whether 'done' was a claim or a predicate</text>
</svg>
^ On the identical run, the naive harness returns a false success and the verified harness returns not-done with the missing step named. The only difference is whether the harness trusted the model's message or evaluated the predicate.

**The naive harness returns a false success on a task that is two-thirds done; the verified harness returns not-done and names send_email — the actionable gap the claim concealed.**

## Build

The self-test first establishes the trap: the model's message claims completion, and yet a required step was genuinely not completed.

```python filename=modules/agent-harness/code/verifydone-inter-01/verifydone.py:84-91 COMPLETE
    model_claims_done = naive
    print("  the model's final message claims completion = %s (%r)" % (model_claims_done, sr.get("message")))

    requirement_unmet = len(missing) > 0
    print("  a required step was not actually completed = %s (missing %s)" % (requirement_unmet, missing))

    naive_false_success = naive and not verified
    print("  trusting the claim returns a FALSE success = %s" % naive_false_success)
```

Then the fix: the predicate returns not-done, and it names exactly the missing requirement rather than a vague failure.

```python filename=modules/agent-harness/code/verifydone-inter-01/verifydone.py:93-97 COMPLETE
    verify_catches = verified is False
    print("  the predicate returns not-done = %s" % verify_catches)

    verify_names_missing = missing == [r for r in required if r not in completed] and len(missing) > 0
    print("  the predicate names exactly what is missing = %s (%s)" % (verify_names_missing, missing))
```

Running the check confirms every clause.

```text filename=verifydone.py --check
  the model's final message claims completion = True ('All tasks complete.')
  a required step was not actually completed = True (missing ['send_email'])
  trusting the claim returns a FALSE success = True
  the predicate returns not-done = True
  the predicate names exactly what is missing = True (['send_email'])
```

**The check pins the false success to the gap between a confident claim and an unmet requirement, and shows the predicate both rejecting the premature 'done' and naming the missing step — the failure caught and made actionable.**

## Definition of done

Done means the naive harness returns a success the predicate refutes, and the predicate not only rejects it but names the missing requirement. The "names exactly what is missing" clause matters: a termination check that only says "not done" forces the agent to rediscover the gap, while one that returns the unmet requirements gives the loop a concrete next action — retry send_email — turning verification from a gate into guidance.

Two clarifications keep this practical. First, the predicate has to be genuinely checkable, and its quality is the whole game: "the report file exists and is non-empty," "the test suite passes," "the response JSON has these fields," "the email API returned a 2xx" are checkable; "the report is good" is not, and a vacuous predicate (one that is always true, or just re-reads the model's own claim) reintroduces the failure it was meant to prevent. The best predicates check the world (an artifact, an API result) or the run's own tamper-proof record (which tool calls actually executed), not the model's narration of them. Second, this is not a license to loop forever: the verified check pairs with a budget — if the predicate stays unmet after the allotted retries or steps, the harness fails honestly ("incomplete: send_email not done") rather than either looping unbounded or, worse, giving up and reporting success. A truthful failure is a better outcome than a false success, because a false success is acted on and a truthful failure is retried.

<svg role="img" aria-label="A termination gate: the model's done enters, the predicate checks required against completed; if met, return success; if unmet and budget remains, continue; if unmet and budget spent, fail honestly" viewBox="0 0 320 140">
  <rect x="120" y="10" width="80" height="18" fill="none" stroke="var(--muted)"/><text x="132" y="23" font-size="7.5" fill="var(--ink)">model: "done"</text>
  <rect x="110" y="42" width="100" height="18" fill="none" stroke="var(--s1)"/><text x="120" y="55" font-size="7.5" fill="var(--s1)">predicate holds?</text>
  <line x1="160" y1="28" x2="160" y2="42" stroke="var(--line)"/>
  <text x="40" y="92" font-size="7.5" fill="var(--s1)">yes → return SUCCESS</text>
  <line x1="130" y1="60" x2="80" y2="82" stroke="var(--s1)"/>
  <text x="205" y="86" font-size="7.5" fill="var(--s2)">no, budget left → continue</text>
  <line x1="190" y1="60" x2="240" y2="80" stroke="var(--s2)"/>
  <text x="150" y="120" font-size="7.5" fill="var(--ink)">no, budget spent → fail HONESTLY (name the gap)</text>
  <line x1="175" y1="60" x2="200" y2="112" stroke="var(--ink)"/>
</svg>
^ The predicate is the gate on termination: met, return success; unmet with budget left, keep working; unmet with budget spent, fail honestly and name the gap. No path returns success without the predicate holding.

**Done means termination is gated on a checkable predicate that both refutes a premature 'done' and names the unmet requirement, paired with a budget so an unmet predicate ends in an honest failure rather than a false success or an unbounded loop.**

## Boss fight

An agent that files expense reports is reported as "working" — it runs, ends each session with "Expense report submitted successfully," and the harness marks the task complete. But finance says a meaningful fraction of reports never actually arrived, with no errors logged anywhere. The agent's traces all end with a confident success message. What is going wrong, and how would you make the harness trustworthy?

The harness is trusting the model's self-reported completion, and the model is sometimes wrong without knowing it. On the runs that fail silently, the agent did some of the work — gathered the receipts, filled the form — and then, across a long trace, either skipped the final submit step or mistook a draft for a submission, and summarized the whole thing as "submitted successfully." Nothing errors because nothing checked whether a submission actually happened; the only completion signal is the model's message, and that message reflects the model's belief, not the outcome. The fix is to gate termination on a checkable predicate tied to the real outcome: the submission API returned a success response and a submission id, or the report appears in the finance system's queue, or the run's tool-call record shows the submit tool actually executed with a 2xx result. On "done," the harness evaluates that predicate; if the submission is not verifiably present, the task is not complete no matter what the model said, and the harness retries the submit step or, after its budget, fails honestly with "submission not confirmed" so finance sees a real failure instead of a phantom success. Two guardrails make it robust: the predicate must check the external system or the tamper-proof tool log, not the model's narration of them (otherwise it just relaunders the claim), and it must pair with a retry budget so an unconfirmed submission is retried a bounded number of times and then reported as incomplete rather than looping forever. The principle: an agent's "done" is a proposal to stop, and the harness must verify the goal state before accepting it.

## External resources

Writing on agent evaluation and task success criteria (the distinction between an agent asserting success and an environment-checked success signal, and the design of verifiable/checkable tasks in agent benchmarks) — the reason self-reported completion is an unreliable metric and how graded environments verify the goal state instead.

Guidance on building agent loops with explicit termination and verification (LangGraph, and agent-framework patterns for a "done" condition evaluated by code rather than the model, plus the pairing of verification with step/token budgets) — the production mechanics of gating termination on a predicate and failing honestly when it stays unmet.
