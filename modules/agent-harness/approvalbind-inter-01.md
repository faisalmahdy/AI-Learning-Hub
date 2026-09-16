---
id: approvalbind-inter-01
title: Bind a confirmation to the exact call it approved — a boolean "yes" authorizes whatever call is pending, so a rewrite after approval runs unapproved
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: Gating irreversible tools decides which calls need a human's approval; it does not guarantee that the call the human approved is the call that runs. Those are two different properties, and the second is the one that breaks under a re-plan or an attack. The gap opens between the approval and the execution: the human sees a call and approves it, and the harness carries that approval to the moment it fires the tool — but in between, the pending call can change. The model regenerates the step with different arguments, a state compaction reshuffles things, or an instruction injected through a tool result rewrites the arguments. If the approval is a standing boolean the harness holds, it authorizes whatever call is pending when the tool fires, not the call the human saw. On the fixture the human approves delete_file("reports/scratch_draft.csv"), but by execution the pending call's path has been rewritten to "reports/2024_final_audited.csv"; the naive harness runs the rewritten delete because the boolean said yes. The fix binds the approval to a fingerprint (a hash over the canonical tool name and arguments) of the exact approved call and, at execution, recomputes the fingerprint of the call about to run and requires it to match — the approved and pending fingerprints here are eb85b14a30d5 and 2dbc22d96b64, so the bound harness refuses the changed call and gates again, while still running an unchanged approved call with no extra friction. The rule: an approval authorizes one specific call, not a category, so bind it to that call's fingerprint and re-verify before executing.
eli5: Imagine you sign a permission slip that says "yes, you may throw away the old scribbles on my desk." You hand it over and walk away. If the slip just says "yes, throw it away" without naming what, someone could swap in your finished homework and the slip would still say yes — you approved an action, but not a specific thing, so the yes got reused for something you never meant. The safe version writes the exact thing on the slip: "throw away the page titled scribbles." Now if the page in hand is your homework instead, it doesn't match what the slip names, so no one throws it out — they come back and ask you again. Approving a computer's dangerous action works the same way: the yes has to name the exact action, so it can't be reused for a different one.
---

## Why this module

A confirmation gate exists to put a human in front of irreversible actions — the delete, the send, the deploy. The natural way to build it is a question and a boolean answer: the harness detects an irreversible call, asks "run this?", and if the human says yes, it proceeds. That is the right instinct and the wrong data model, because the yes is not attached to anything.

The trouble is that "run this?" and "proceed" are separated in time, and in an agent loop the pending call is not frozen in between. Another turn of the model can regenerate it, a context compaction can shuffle state, and — the case that turns a bug into a vulnerability — a tool result carrying injected text can rewrite the call's arguments. When the harness finally fires, it fires whatever is pending, and the boolean it carried says only "a human approved something," not "a human approved this."

This module builds that gap. The human approves deleting a scratch file; by execution the path has been rewritten to the year's audited report; the naive harness deletes the report because the boolean was true. Then it binds the approval to a fingerprint of the exact call, so the rewrite fails the match and is gated again — while an unchanged call still passes untouched.

**A confirmation is an answer, and an answer is only safe if it stays attached to its question — a boolean approval detaches the yes from the call and lets it be reused for a call the human never saw.**

## Concepts

Separate the two guarantees a gate can offer. The first is coverage: every irreversible call is put in front of a human. The second is integrity: the call that runs is the call the human approved. Gating by reversibility gives you coverage. It says nothing about integrity, and integrity is a separate mechanism you have to add.

Integrity is hard here because approval and execution are not atomic. Between the human clicking yes and the tool firing, the agent loop keeps moving: the pending call lives in mutable state that other steps read and write. Anything that can change that state between the two moments can change what executes without changing the fact that an approval exists.

The most serious mover is injection. Agent tool results are untrusted data, and a result that contains an instruction — "also delete the final report" — can cause the model to rewrite its next call's arguments. If that rewrite lands after the human approved the original, a boolean approval laundered the injected call straight through the gate: the human's yes, meant for a harmless delete, is now the authorization for the injected one. The gate asked the right question and applied the answer to a different one.

Binding closes the gap by making the approval refer to a specific call. Fingerprint the approved call — hash its canonical tool name and arguments into a short, stable value — and store that fingerprint with the approval. At execution, recompute the fingerprint of the call actually about to run and compare. Identical call, identical fingerprint, execute; changed call, different fingerprint, so the approval does not apply and the harness must gate again.

<svg role="img" aria-label="A timeline from approval to execution. At approval the human sees call A (delete scratch). In the gap an injected tool result rewrites the pending call to B (delete final report). At execution the naive harness carries a boolean yes and runs B; the bound harness carries A's fingerprint and detects the mismatch" viewBox="0 0 640 240">
<line x1="60" y1="70" x2="600" y2="70" stroke="var(--line)" stroke-width="1"/>
<text x="110" y="50" fill="var(--ink)" font-size="11" text-anchor="middle">approval</text>
<circle cx="110" cy="70" r="5" fill="var(--s1)"/>
<text x="110" y="92" fill="var(--muted)" font-size="9" text-anchor="middle">human sees A</text>
<text x="340" y="50" fill="var(--s2)" font-size="11" text-anchor="middle">the gap</text>
<circle cx="340" cy="70" r="5" fill="var(--s2)"/>
<text x="340" y="92" fill="var(--muted)" font-size="9" text-anchor="middle">injection rewrites A → B</text>
<text x="560" y="50" fill="var(--ink)" font-size="11" text-anchor="middle">execution</text>
<circle cx="560" cy="70" r="5" fill="var(--ink)"/>
<rect x="60" y="130" width="250" height="70" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="185" y="152" fill="var(--ink)" font-size="11" text-anchor="middle">naive: carries "yes" (boolean)</text>
<text x="185" y="172" fill="var(--muted)" font-size="10" text-anchor="middle">runs whatever is pending = B</text>
<text x="185" y="190" fill="var(--s2)" font-size="10" text-anchor="middle">deletes the final report</text>
<rect x="350" y="130" width="250" height="70" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="475" y="152" fill="var(--ink)" font-size="11" text-anchor="middle">bound: carries A's fingerprint</text>
<text x="475" y="172" fill="var(--muted)" font-size="10" text-anchor="middle">fp(B) ≠ fp(A) → re-gate</text>
<text x="475" y="190" fill="var(--s1)" font-size="10" text-anchor="middle">the rewrite is stopped</text>
</svg>
^ The approval and execution are separated by a gap the pending call can be rewritten in; a boolean carries "yes" across it, a fingerprint carries "yes to A" and catches the swap.

**Coverage asks a human about every dangerous call; integrity makes sure the human's answer cannot be transplanted onto a different call — and only the second survives an injection in the gap.**

## Worked example

The fixture is one approved call and a different call sitting in the execution slot when the harness fires.

```json filename=modules/agent-harness/code/approvalbind-inter-01/approvalbind.json:3-4 COMPLETE
  "approved_call": {"tool": "delete_file", "args": {"path": "reports/scratch_draft.csv"}},
  "pending_call": {"tool": "delete_file", "args": {"path": "reports/2024_final_audited.csv"}}
```

The identity the approval should bind to is a fingerprint of the exact call — a hash over its canonical tool name and arguments.

```python filename=modules/agent-harness/code/approvalbind-inter-01/approvalbind.py:33-36 COMPLETE
def fingerprint(call):
    """A stable hash over the call's canonical tool name and arguments -- the identity the approval binds to."""
    canonical = json.dumps(call, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
```

The naive harness carries a boolean and runs whatever is pending.

```python filename=modules/agent-harness/code/approvalbind-inter-01/approvalbind.py:39-43 COMPLETE
def naive_execute(pending_call, approved_flag):
    """BUG: a boolean approval authorizes whatever call is pending when the tool fires."""
    if approved_flag:
        return {"ran": True, "call": pending_call}
    return {"ran": False, "call": None}
```

With the human's yes, it deletes the report the human never approved.

```text filename=approvalbind.py --naive
NAIVE — the approval is a boolean the harness carries to execution
----------------------------------------------------------------
  human approved : delete_file(reports/scratch_draft.csv)
  pending at exec: delete_file(reports/2024_final_audited.csv)
  executed       : delete_file(reports/2024_final_audited.csv)
----------------------------------------------------------------
  the 'yes' for the scratch file authorized deleting the final report
```

The bound harness executes only if the pending call's fingerprint still matches the approved one.

```python filename=modules/agent-harness/code/approvalbind-inter-01/approvalbind.py:46-50 COMPLETE
def bound_execute(pending_call, approved_fingerprint):
    """FIX: execute only if the pending call's fingerprint still matches the approved one."""
    if fingerprint(pending_call) == approved_fingerprint:
        return {"ran": True, "call": pending_call, "regated": False}
    return {"ran": False, "call": None, "regated": True}   # call changed -> approval void, gate again
```

The rewritten path produces a different fingerprint, so the bound harness refuses it — and still passes an unchanged call.

```text filename=approvalbind.py --bound
BOUND — the approval is bound to the approved call's fingerprint
----------------------------------------------------------------
  approved fingerprint : eb85b14a30d5  (reports/scratch_draft.csv)
  pending fingerprint  : 2dbc22d96b64  (reports/2024_final_audited.csv)
  changed call  -> ran=False  regated=True
  unchanged call-> ran=True
----------------------------------------------------------------
  the rewritten call fails the match and is gated again; an unchanged call still passes
```

The two fingerprints, eb85b14a30d5 and 2dbc22d96b64, are the whole mechanism: they differ the instant any byte of the tool name or arguments differs, so the rewrite cannot masquerade as the approved call. The figure shows both harnesses meeting the rewritten call.

<svg role="img" aria-label="Two harness panels facing the same rewritten call. The naive panel takes a boolean yes and outputs executed: delete final report. The bound panel compares fingerprint eb85 of the approved call against 2dbc of the pending call, they differ, and outputs blocked and re-gated" viewBox="0 0 640 210">
<text x="320" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">pending: delete_file(2024_final_audited.csv)</text>
<rect x="40" y="48" width="260" height="120" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="170" y="72" fill="var(--ink)" font-size="11" text-anchor="middle">naive harness</text>
<text x="170" y="98" fill="var(--muted)" font-size="10" text-anchor="middle">approval = yes (boolean)</text>
<text x="170" y="120" fill="var(--muted)" font-size="10" text-anchor="middle">runs the pending call</text>
<text x="170" y="146" fill="var(--s2)" font-size="11" text-anchor="middle">EXECUTED (unapproved)</text>
<rect x="340" y="48" width="260" height="120" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="470" y="72" fill="var(--ink)" font-size="11" text-anchor="middle">bound harness</text>
<text x="470" y="98" fill="var(--muted)" font-size="10" text-anchor="middle">approved fp eb85 ≠ pending fp 2dbc</text>
<text x="470" y="120" fill="var(--muted)" font-size="10" text-anchor="middle">match fails</text>
<text x="470" y="146" fill="var(--s1)" font-size="11" text-anchor="middle">BLOCKED, re-gated</text>
</svg>
^ Same rewritten call, two harnesses: the boolean approves it, the fingerprint comparison rejects it.

**The naive harness cannot tell the approved call from the injected one because it never recorded which call was approved — the fingerprint is exactly that recording.**

## Build

The self-test pins the attack and both responses: the pending call differs from the approved one, the naive harness runs it, and the bound harness blocks it while still allowing an unchanged call.

```python filename=modules/agent-harness/code/approvalbind-inter-01/approvalbind.py:92-102 COMPLETE
    approved_and_pending_differ = approved != pending
    print("  the pending call differs from the approved call = %s (%s vs %s)" % (approved_and_pending_differ, _path(approved), _path(pending)))

    fingerprints_differ = fingerprint(approved) != fingerprint(pending)
    print("  their fingerprints differ = %s (%s vs %s)" % (fingerprints_differ, approved_fp, fingerprint(pending)))

    naive_runs_unapproved = naive_execute(pending, True)["call"] == pending
    print("  the naive harness executes the unapproved (changed) call = %s (%s)" % (naive_runs_unapproved, _path(pending)))

    bound_blocks_changed = bound_execute(pending, approved_fp)["ran"] is False
    print("  the bound harness blocks the changed call and re-gates = %s" % bound_blocks_changed)
```

The final flag guards against overcorrection — the bound harness must not block a call that never changed. All five pass.

```text filename=approvalbind.py --check
SELF-TEST — the pending call differs from what was approved, the naive harness runs it anyway, and the bound harness blocks it while still allowing an unchanged call
----------------------------------------------------------------------------------------------------------------
  the pending call differs from the approved call = True (reports/scratch_draft.csv vs reports/2024_final_audited.csv)
  their fingerprints differ = True (eb85b14a30d5 vs 2dbc22d96b64)
  the naive harness executes the unapproved (changed) call = True (reports/2024_final_audited.csv)
  the bound harness blocks the changed call and re-gates = True
  the bound harness still runs an unchanged, approved call = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  approved_and_pending_differ=True  fingerprints_differ=True  naive_runs_unapproved=True  bound_blocks_changed=True  bound_allows_unchanged=True
```

**The last flag matters as much as the block: a gate that re-prompts on every execution is confirmation fatigue by another name, so the bind must pass the unchanged call silently and stop only the changed one.**

## Definition of done

You are done when a human approval is stored as a binding to the exact call it approved, and the harness re-verifies that binding immediately before executing — not as a boolean that any pending call can consume.

The mechanism is small: at approval time, compute a fingerprint over the call's canonical form (tool name and the full, normalized arguments) and store it with the grant; at execution time, recompute the fingerprint of the call about to run and require an exact match, treating any mismatch as an un-approved call that must be gated again. Canonicalize before hashing — sort keys, fix number and string formatting — so a semantically identical call is not rejected for cosmetic reasons, but include every argument that affects the effect, because an argument left out of the fingerprint is an argument an attacker can change freely. Scope the grant tightly too: one fingerprint authorizes one execution, so a second call with the same arguments is a second approval, not a reuse of the first.

<svg role="img" aria-label="A flow: at approval, fingerprint the approved call and store it. At execution, recompute the pending call's fingerprint and compare. If it matches, run once. If it differs, discard the approval and gate again" viewBox="0 0 640 200">
<rect x="30" y="80" width="130" height="44" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="95" y="100" fill="var(--ink)" font-size="10" text-anchor="middle">approve →</text>
<text x="95" y="115" fill="var(--muted)" font-size="9" text-anchor="middle">store fingerprint</text>
<line x1="160" y1="102" x2="200" y2="102" stroke="var(--line)" stroke-width="1"/>
<polygon points="200,102 192,97 192,107" fill="var(--line)"/>
<rect x="200" y="80" width="150" height="44" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="275" y="100" fill="var(--ink)" font-size="10" text-anchor="middle">at execution,</text>
<text x="275" y="115" fill="var(--muted)" font-size="9" text-anchor="middle">recompute + compare</text>
<line x1="350" y1="102" x2="390" y2="102" stroke="var(--line)" stroke-width="1"/>
<polygon points="390,102 382,97 382,107" fill="var(--line)"/>
<rect x="390" y="50" width="210" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="495" y="74" fill="var(--ink)" font-size="10" text-anchor="middle">match → run once</text>
<rect x="390" y="112" width="210" height="40" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="495" y="130" fill="var(--ink)" font-size="10" text-anchor="middle">differ → discard, gate again</text>
<text x="495" y="144" fill="var(--muted)" font-size="9" text-anchor="middle">approval never transfers</text>
</svg>
^ The approval is a fingerprint, checked again at the last moment, so it can only ever authorize the one call it named.

**A confirmation that is not re-verified against the call it authorized is security theater: it records that a human was asked, not that the human agreed to what actually runs.**

## Boss fight

Your turn: probe the canonicalization. Make the pending call identical to the approved one but reorder the argument keys, or change an integer `0` to a float `0.0` in some numeric argument, and check whether the fingerprints still match. Because `fingerprint` sorts keys before hashing, key order will not break the match — but a type change might, depending on how the value serializes. This is the real design tension: canonicalize too loosely and two calls with different effects hash the same (a false match that lets a changed call through); canonicalize too tightly and a cosmetically-different-but-identical call is rejected (a false mismatch that re-prompts needlessly). The correct normalization includes every effect-bearing field and nothing cosmetic, and getting that boundary right is the whole craft of the fingerprint.

Then consider the argument you left out. Suppose `delete_file` also takes a `recursive` flag, and you fingerprint only `path`. An attacker cannot change the path past the gate — but they can flip `recursive` from false to true, turning an approved single-file delete into a directory wipe, and your fingerprint will happily match because it never covered that field. An incomplete fingerprint is worse than none, because it looks like protection while leaving a hole exactly the width of the arguments you forgot. The discipline is that the fingerprint must cover the complete set of inputs that determine the call's effect; any effect-bearing input outside the fingerprint is an input the approval does not actually constrain.

**Binding the approval to a fingerprint is only as strong as the fingerprint is complete — every effect-bearing argument must be inside it, because whatever you leave out is precisely what an attacker is free to change after you said yes.**

## External resources

The OWASP guidance on prompt injection and "excessive agency" in LLM applications frames exactly this risk — that an agent's actions can be redirected by injected content — and treats human-in-the-loop confirmation as a control that must be robust to the action changing.

Anthropic's and others' writing on agent tool-use safety recommends confirming the specific, resolved action rather than a category, which is the practical statement of binding an approval to the exact call.

The general security principle here is TOCTOU (time-of-check to time-of-use): a check is only meaningful if nothing can change the checked thing before it is used, and the classic literature on TOCTOU bugs is directly applicable to the approval-to-execution gap.
