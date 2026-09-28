---
id: confirmgate-inter-01
title: Gate irreversible tool calls behind confirmation — run reversible ones freely, never let the model delete or send unchecked
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: An agent harness executes the tool calls the model proposes, and the model is wrong often enough that executing all of them unconditionally is a liability. For most tools that is fine: a read, a search, a list can be retried, ignored, or undone, so running one the model should not have is cheap. But some tools have effects you cannot take back — deleting a file, sending an email, transferring money, deploying — and for those a single wrong call is not a cheap mistake, it is an incident. Treating a delete like a read, executing it the instant the model asks, turns every hallucinated filename or misread instruction into an irreversible action. The distinction that matters is reversibility, not the tool's apparent importance: a tool is safe to auto-run if its effect can be undone or costs nothing when needless, and needs a gate if its effect is permanent. So the harness classifies each proposed call — reversible calls execute automatically, keeping the agent low-friction on the vast majority of its work, while irreversible calls are held, surfaced for explicit confirmation (a human approves, or a dry-run shows what would happen) before they run. The gate keys on the category of action, not the model's confidence, because you cannot trust the model to know when it is about to do something unrecoverable, and it lives in the harness, so it holds even if the model is jailbroken or fed injected instructions. On a fixture where the model proposes two reversible calls (list_files, read_file) and two irreversible ones (delete_file, send_email), the naive harness runs all four — two irreversible actions with no confirmation — while the gated harness auto-runs the two reversible calls and holds the two irreversible ones, so zero irreversible actions happen unconfirmed and friction falls only on the two calls that warrant it.
eli5: Imagine a helper who can do chores for you by pushing buttons. Most buttons are safe — "show me the list," "read that note" — if the helper pushes one by mistake, no harm done, you just ignore it. But a few buttons can't be un-pushed: "shred this document," "mail this letter." A careless setup lets the helper push any button the instant it wants to, so one confused moment and your document is shredded for real. The smart setup is: let the helper push the safe buttons freely, but for the un-undoable ones, make it stop and ask you first — "I'm about to shred this, okay?" You only get interrupted for the handful of buttons that actually matter, and nothing permanent ever happens without your yes.
---

## Why this module

Every agent harness has to decide what to do with a tool call the model just proposed, and the tempting default — run it — is safe right up until the tool does something that cannot be undone. Models hallucinate arguments, misread instructions, and can be steered by content they read mid-task; assuming the proposed call is always the right call is a bet you lose occasionally, and the cost of losing depends entirely on what the tool does. Lose the bet on a read and nothing happens. Lose it on a delete and a file is gone. The harness that treats those two identically has no defense against its worst case.

The right axis to reason about is reversibility. Some tool effects are cheap to get wrong — you can retry, ignore, or roll them back — and some are permanent: a sent email cannot be unsent, a deleted record cannot be un-deleted, a deploy cannot be un-shipped without another deploy. That line, not the tool's name or how confident the model sounds, is what should decide whether a call runs automatically or waits for a human. And it has to be enforced by the harness, not requested in the prompt, because a prompt-level "please confirm before deleting" is exactly the instruction a confused or manipulated model will skip.

This module classifies a batch of proposed calls by reversibility and compares running them all against gating the irreversible ones.

**Classify each proposed tool call by reversibility and gate the irreversible ones behind explicit confirmation while auto-running the reversible ones, rather than executing every call the model proposes, because irreversible actions (delete, send, transfer, deploy) cannot be undone if the model is wrong — so a harness-level confirmation checkpoint on exactly those calls prevents unrecoverable mistakes without adding friction to the safe majority.**

## Concepts

The fixture is a batch of four calls the model proposed in one turn, and a per-tool reversibility flag. `list_files` and `read_file` are reversible; `delete_file` and `send_email` are not.

```json filename=modules/agent-harness/code/confirmgate-inter-01/confirmgate.json:3-9 COMPLETE
  "tools": {
    "list_files": {"reversible": true},
    "read_file": {"reversible": true},
    "delete_file": {"reversible": false},
    "send_email": {"reversible": false}
  },
  "proposed_calls": ["list_files", "read_file", "delete_file", "send_email"]
```

The two policies differ in one decision. The naive harness executes every proposed call; the gated harness auto-runs the reversible calls and holds the irreversible ones for confirmation.

```python filename=modules/agent-harness/code/confirmgate-inter-01/confirmgate.py:36-45 COMPLETE
def naive_execute(calls, tools):
    """Naive harness: execute every proposed call immediately."""
    return {"executed": list(calls), "held": []}


def gated_execute(calls, tools):
    """Gated harness: auto-run reversible calls, hold irreversible ones for confirmation."""
    executed = [c for c in calls if reversible(c, tools)]
    held = [c for c in calls if not reversible(c, tools)]
    return {"executed": executed, "held": held}
```

The metric that matters is how many irreversible calls a policy executed without confirmation — the count of unrecoverable actions taken on the model's unverified say-so.

```python filename=modules/agent-harness/code/confirmgate-inter-01/confirmgate.py:48-50 COMPLETE
def unconfirmed_irreversible(result, tools):
    """How many irreversible calls this policy executed without confirmation."""
    return sum(1 for c in result["executed"] if not reversible(c, tools))
```

<svg role="img" aria-label="Four proposed calls flowing through a gate: two reversible pass straight to execute, two irreversible are diverted to a confirmation hold" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">proposed calls</text>
  <rect x="10" y="24" width="80" height="14" fill="var(--s1)"/><text x="16" y="35" font-size="7.5" fill="var(--panel)">list_files (rev)</text>
  <rect x="10" y="42" width="80" height="14" fill="var(--s1)"/><text x="16" y="53" font-size="7.5" fill="var(--panel)">read_file (rev)</text>
  <rect x="10" y="64" width="80" height="14" fill="var(--s2)"/><text x="16" y="75" font-size="7.5" fill="var(--panel)">delete_file</text>
  <rect x="10" y="82" width="80" height="14" fill="var(--s2)"/><text x="16" y="93" font-size="7.5" fill="var(--panel)">send_email</text>
  <rect x="150" y="30" width="30" height="66" fill="none" stroke="var(--ink)" stroke-width="1.5"/><text x="155" y="66" font-size="8" fill="var(--ink)">gate</text>
  <line x1="90" y1="31" x2="150" y2="40" stroke="var(--s1)" stroke-width="1"/>
  <line x1="90" y1="49" x2="150" y2="50" stroke="var(--s1)" stroke-width="1"/>
  <line x1="90" y1="71" x2="150" y2="70" stroke="var(--s2)" stroke-width="1"/>
  <line x1="90" y1="89" x2="150" y2="86" stroke="var(--s2)" stroke-width="1"/>
  <rect x="230" y="30" width="80" height="24" fill="var(--s1)"/><text x="238" y="45" font-size="7.5" fill="var(--panel)">auto-execute</text>
  <rect x="230" y="70" width="80" height="24" fill="var(--s2)"/><text x="238" y="85" font-size="7.5" fill="var(--panel)">hold: confirm</text>
  <line x1="180" y1="45" x2="230" y2="42" stroke="var(--s1)" stroke-width="1"/>
  <line x1="180" y1="80" x2="230" y2="82" stroke="var(--s2)" stroke-width="1"/>
</svg>
^ The gate sorts calls by reversibility: reversible ones flow straight to auto-execute, irreversible ones divert to a confirmation hold. Only the permanent actions stop; the safe ones never do.

**The gate is a harness-level classifier on the category of action, not a request in the prompt — so it holds regardless of how the model behaves, which is the whole point of putting it below the model.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the tool-dispatch step of an agent harness, reduced to four calls so every classification is checkable by hand.

Run `--calls` to see each call's reversibility and how each policy handles it.

```text filename=confirmgate.py --calls
  call          reversible   naive       gated
  list_files    True         execute     execute
  read_file     True         execute     execute
  delete_file   False        execute     HOLD (confirm)
  send_email    False        execute     HOLD (confirm)
  the gate keys on reversibility, not on the model's confidence
```

The naive column executes all four regardless of reversibility. The gated column diverges exactly on the irreversible calls: `list_files` and `read_file` execute (reversible, safe to auto-run), while `delete_file` and `send_email` are held for confirmation. Note what the gate does not consider — the arguments, the model's stated confidence, the phrasing of the request. It keys on one thing: can this be undone?

Now `--gate` runs both policies and counts the unconfirmed irreversible actions.

```text filename=confirmgate.py --gate
  naive: executed ['list_files', 'read_file', 'delete_file', 'send_email'] ; held none
         irreversible run WITHOUT confirmation: 2
  gated: executed ['list_files', 'read_file'] ; held ['delete_file', 'send_email']
         irreversible run WITHOUT confirmation: 0
  gating held 2 irreversible call(s) for approval; the safe calls still ran
```

The naive harness executed two irreversible actions with no confirmation — if the model hallucinated the filename or misread the request, the file is deleted and the email is sent, and neither can be recovered. The gated harness executed zero irreversible actions unconfirmed: it ran the two safe calls immediately and held the two irreversible ones for approval. The agent still made progress on everything reversible; the only thing that stopped was the pair of actions that could not be taken back.

<svg role="img" aria-label="Four tools placed on a reversibility axis: list_files and read_file on the reversible side auto-run, delete_file and send_email on the irreversible side gated" viewBox="0 0 320 110">
  <line x1="20" y1="55" x2="300" y2="55" stroke="var(--line)" stroke-width="1"/>
  <text x="20" y="20" font-size="8" fill="var(--s1)">reversible → auto-run</text>
  <text x="200" y="20" font-size="8" fill="var(--s2)">irreversible → gate</text>
  <line x1="160" y1="30" x2="160" y2="80" stroke="var(--ink)" stroke-width="1.3" stroke-dasharray="3 2"/>
  <circle cx="55" cy="55" r="4" fill="var(--s1)"/><text x="30" y="72" font-size="7" fill="var(--muted)">list_files</text>
  <circle cx="100" cy="55" r="4" fill="var(--s1)"/><text x="78" y="72" font-size="7" fill="var(--muted)">read_file</text>
  <circle cx="215" cy="55" r="4" fill="var(--s2)"/><text x="192" y="72" font-size="7" fill="var(--muted)">delete_file</text>
  <circle cx="270" cy="55" r="4" fill="var(--s2)"/><text x="248" y="72" font-size="7" fill="var(--muted)">send_email</text>
  <text x="120" y="98" font-size="7.5" fill="var(--ink)">the line is "can it be undone?" — not importance or confidence</text>
</svg>
^ Each tool sits on one axis — can its effect be undone? The two on the left auto-run; the two on the right are gated. The classification ignores how important the tool seems or how sure the model is; only reversibility decides.

**The naive harness took two unrecoverable actions on the model's unverified word; the gated harness took none, while still auto-running the safe calls — the checkpoint fell exactly on the two calls where a mistake is permanent.**

## Build

The self-test asserts the failure and the fix: the batch contains irreversible calls, the naive harness runs them unconfirmed, and gating holds every one of them for confirmation.

```python filename=modules/agent-harness/code/confirmgate-inter-01/confirmgate.py:90-97 COMPLETE
    has_irreversible = len(irreversible_calls) > 0
    print("  the batch contains irreversible calls = %s (%s)" % (has_irreversible, irreversible_calls))

    naive_runs_irreversible = unconfirmed_irreversible(n, tools) > 0
    print("  the naive harness runs irreversible calls without confirmation = %s (%d)" % (naive_runs_irreversible, unconfirmed_irreversible(n, tools)))

    gated_holds_all_irreversible = set(g["held"]) == set(irreversible_calls)
    print("  gating holds every irreversible call for confirmation = %s (%s)" % (gated_holds_all_irreversible, g["held"]))
```

<svg role="img" aria-label="Two bars of unconfirmed irreversible actions: naive at 2, gated at 0, with a note that gated still ran the 2 safe calls" viewBox="0 0 320 110">
  <text x="10" y="18" font-size="8.5" fill="var(--muted)">irreversible actions run WITHOUT confirmation</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">naive</text>
  <rect x="70" y="32" width="120" height="16" fill="var(--s2)"/><text x="196" y="45" font-size="8" fill="var(--ink)">2</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">gated</text>
  <rect x="70" y="62" width="4" height="16" fill="var(--s1)"/><text x="80" y="75" font-size="8" fill="var(--ink)">0</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">gated still auto-ran the 2 reversible calls — no friction on the safe majority</text>
</svg>
^ The naive harness takes two unrecoverable actions on the model's say-so; the gated harness takes zero, holding both for approval — while still auto-running the reversible calls, so the safety costs nothing on the safe path.

Running the check confirms every clause, including that gating still runs the safe calls and the friction falls only on the irreversible minority.

```text filename=confirmgate.py --check
  the batch contains irreversible calls = True (['delete_file', 'send_email'])
  the naive harness runs irreversible calls without confirmation = True (2)
  gating holds every irreversible call for confirmation = True (['delete_file', 'send_email'])
  gating executes zero irreversible calls unconfirmed = True
  gating still auto-runs the reversible (safe) calls = True (['list_files', 'read_file'])
  confirmation friction falls only on the irreversible minority = True (2 of 4)
```

**The check pins both sides: zero unconfirmed irreversible actions under gating, and the reversible calls still auto-run — safety on the permanent actions without slowing the safe ones.**

## Definition of done

Two properties close it, and together they are the whole value proposition. Gating must execute zero irreversible calls unconfirmed (the safety), and it must still auto-run the reversible calls with friction only on the irreversible minority (the low cost). A gate that stopped everything would be safe but useless; a gate that stopped nothing would be fast but unsafe; this one stops exactly the unrecoverable slice.

```python filename=modules/agent-harness/code/confirmgate-inter-01/confirmgate.py:99-106 COMPLETE
    gated_zero_unconfirmed = unconfirmed_irreversible(g, tools) == 0
    print("  gating executes zero irreversible calls unconfirmed = %s" % gated_zero_unconfirmed)

    gated_runs_safe = set(g["executed"]) == set(reversible_calls)
    print("  gating still auto-runs the reversible (safe) calls = %s (%s)" % (gated_runs_safe, g["executed"]))

    friction_only_on_irreversible = len(g["held"]) == len(irreversible_calls) and len(g["held"]) < len(calls)
    print("  confirmation friction falls only on the irreversible minority = %s (%d of %d)" % (friction_only_on_irreversible, len(g["held"]), len(calls)))
```

Three clarifications keep the gate well-calibrated. First, the classification is the hard part and must be conservative: when in doubt, treat a tool as irreversible, because a false "reversible" is an unrecoverable mistake while a false "irreversible" is only an extra confirmation. The reversibility flag should be a property of the tool declared at registration, not inferred per call. Second, confirmation does not have to mean a human every time — for an autonomous agent it can be a dry-run that previews the exact effect, a policy check, or a scoped allowlist (this agent may delete files under /tmp but nowhere else); the invariant is that an irreversible effect never fires purely on the model's unchecked proposal. Third, the gate belongs in the harness precisely because the threat includes a misbehaving model: prompt injection, jailbreaks, and confusion all produce confidently-wrong tool calls, and a prompt-level rule is the first thing they bypass — a harness-level gate is not. It pairs naturally with argument-level guards (like path-jailing a delete) and a step budget, each closing a different failure.

**Done means zero irreversible calls execute unconfirmed while the reversible ones still auto-run — a harness-enforced checkpoint on exactly the unrecoverable actions, conservative in classification and independent of how the model behaves.**

## Boss fight

An autonomous agent that manages cloud infrastructure runs fine for weeks, then one night deletes a production database. The postmortem finds the model received an ambiguous instruction, concluded the database was a leftover test resource, and called the delete tool — which the harness executed immediately, as it does every tool call. A teammate proposes adding "always ask before deleting anything important" to the system prompt. Why is that inadequate, and what would you actually build?

Putting the rule in the system prompt is inadequate because it relies on the very component that failed — the model's judgment — to enforce the safety. The model already decided the database was unimportant; a prompt instruction to "ask before deleting anything important" would not have fired, because the model did not believe this deletion was important. And a prompt-level rule is bypassed by exactly the situations you most need protection from: an ambiguous instruction, a confused chain of reasoning, or a prompt-injection attack that tells the model to ignore prior instructions. The safety has to live below the model, in the harness, where the model cannot reason its way around it. What to build: classify every tool by reversibility at registration, mark destructive infrastructure actions (delete database, terminate instance, drop table) irreversible, and have the harness gate every irreversible call behind a checkpoint that does not depend on the model's opinion — a required human approval for production-scoped resources, or at minimum a dry-run that surfaces exactly what will be destroyed plus a policy check (for example, refuse to delete any resource tagged production, or anything outside an explicit allowlist, regardless of what the model concluded). Layer argument-level guards too: even an approved delete should be scoped so the agent cannot target production resources it was never meant to touch. The principle is that an unrecoverable action never executes on the model's unverified say-so; the confirmation is a property of the system, not a sentence in the prompt.

## External resources

Anthropic's and OpenAI's guidance on tool use and human-in-the-loop confirmation for high-impact actions — the practice of marking tools that require approval and gating them in the application layer rather than trusting the model to self-restrict.

The literature on prompt injection and agent security (Simon Willison's writing on prompt injection, and the OWASP LLM Top 10's "excessive agency" entry) — why safety-critical controls must be enforced outside the model, and why reversibility-based gating and scoped permissions are the standard defense against an agent taking unrecoverable actions.
