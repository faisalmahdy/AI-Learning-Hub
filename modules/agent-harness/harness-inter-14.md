---
id: harness-inter-14
title: Gate the irreversible tools for confirmation — not every tool, and not none
topic: agent-harness
level: intermediate
status: ready
time: 21 min
summary: An agent's tools are not equally dangerous, and reversibility is the line. Auto-running everything eventually fires an irreversible action — a delete, an email, a charge — that the user never approved. Confirming every tool is safe but breeds confirmation fatigue, so people approve reflexively and the gate stops mattering. Gating only the irreversible tools asks precisely when it counts. On a 6-call run, auto fires 2 destructive actions unconfirmed, confirm-all prompts 6 times, and gate-by-reversibility holds both destructive calls with just 2 prompts.
eli5: Some buttons you can un-press — reading a page, editing a draft you can undo. Some you can't — deleting with no backup, sending a message, spending money. Asking "are you sure?" before every single button makes people stop reading the question. Asking only before the un-undoable ones keeps the question meaningful, so people actually pay attention when it matters.
---

## Why this module

Treating every tool call the same is the mistake — some can be undone and some cannot, and only the second kind needs a human in the loop.

An agent's tools span a huge range of danger. Reading a file, listing a directory, updating a record you can revert — if the agent does these wrong, you notice, you fix it, you move on; the cost of a mistake is bounded and recoverable. Deleting a record with no backup, sending an email to a customer list, charging a card, terminating a server — get these wrong and there is no undo. The mistake is permanent, and it happened at machine speed with no one watching. The reversibility of the action, not its name or its tool category, is what decides how much it matters that the agent got it right.

Run every tool automatically and you are one bad plan away from a permanent mistake. An agent that can execute irreversible actions without a checkpoint will, eventually, fire one the user never saw coming — delete the wrong rows, email the wrong list, refund the wrong order. The harness treated the DELETE exactly like the SELECT, so nothing stood between the agent's mistake and the irreversible effect. Autonomy is wonderful for the recoverable actions and reckless for the unrecoverable ones, and a uniform auto-run policy cannot tell them apart.

The obvious over-correction — confirm every tool call — is safe and unusable. If the user is prompted to approve reading a file, listing a directory, and every other trivial step, the prompts become noise. Confirmation fatigue sets in: people click "yes" reflexively without reading, because 95% of the prompts were for harmless actions, and the reflex carries straight through the one prompt that actually mattered. A gate that fires constantly trains the user to ignore it, which means it fails exactly when it finally guards something dangerous. Too many confirmations is its own way of being unsafe.

The right policy gates on reversibility: auto-run the read-only and reversible tools, and hold only the irreversible ones for an explicit confirmation. On the fixture, a run issues 6 tool calls — 3 reads, 1 reversible write, and 2 irreversible actions (a delete and an email). Auto-run executes all 6, firing both irreversible actions with no confirmation. Confirm-everything holds all 6, prompting 6 times. Gate-by-reversibility auto-runs the 4 safe calls and holds only the 2 irreversible ones — zero unconfirmed destructive actions, and just 2 prompts.

**Reversibility is the line between tools an agent may run freely and tools that need a human checkpoint; auto-running everything fires irreversible actions unconfirmed, confirming everything breeds fatigue that defeats the gate, and gating only the irreversible tools is both safe and quiet.**

## Concepts

The property to gate on is whether the action can be undone, because that is what determines the cost of a wrong call. A reversible action has a bounded downside — you can revert the record, restore the draft, retry — so letting the agent do it autonomously risks only a recoverable mistake, and the efficiency of not interrupting the user is worth that risk. An irreversible action has an unbounded downside — the deleted data is gone, the email is read, the money is spent — so the value of a human checkpoint is high and the interruption is worth it. Gating on reversibility aligns the friction with the stakes: cheap actions are frictionless, expensive ones are guarded.

Gating on the wrong property is a common way to get this subtly wrong. Gating by tool name (an allowlist of "safe" tools) is brittle because the same tool can be safe or dangerous depending on arguments — a "run query" tool is fine for a SELECT and catastrophic for a DELETE. Gating by whether a tool "writes" is closer but still imprecise, because many writes are reversible (updating a field you can update back) and gating all of them reintroduces fatigue. The clean criterion is reversibility of the specific effect, which is why production systems tag tools (or tool calls, considering arguments) with a reversibility or "requires confirmation" annotation rather than inferring it from the name.

<svg role="img" aria-label="A safety-versus-friction plane: auto-run is bottom-right (unsafe, no friction), confirm-all is top-left (safe, high friction), gate-by-reversibility is top-right (safe, low friction)" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">safety (up) vs friction (right)</text>
  <line x1="50" y1="165" x2="440" y2="165" stroke="var(--line)"/>
  <line x1="50" y1="165" x2="50" y2="35" stroke="var(--line)"/>
  <text x="20" y="45" font-family="var(--mono)" font-size="7" fill="var(--muted)">safe</text>
  <text x="380" y="180" font-family="var(--mono)" font-size="7" fill="var(--muted)">high friction</text>
  <circle cx="110" cy="150" r="6" fill="var(--s2)"/>
  <text x="80" y="140" font-family="var(--mono)" font-size="8" fill="var(--s2)">auto (unsafe, easy)</text>
  <circle cx="360" cy="60" r="6" fill="var(--muted)"/>
  <text x="270" y="52" font-family="var(--mono)" font-size="8" fill="var(--muted)">confirm-all (safe, noisy)</text>
  <circle cx="130" cy="60" r="7" fill="var(--acc-line)"/>
  <text x="90" y="50" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">gate-irrev (safe, quiet)</text>
</svg>
^ Auto and confirm-all sit at opposite corners — one gives up safety, the other gives up ease — while gating by reversibility reaches the top-left region that has both: safe and low-friction.

The two failure modes are symmetric and both real. Under-gating (auto-run all) optimizes for throughput and pays with the occasional permanent disaster — rare but catastrophic. Over-gating (confirm all) optimizes for safety and pays with fatigue that erodes the safety it was buying — constant and corrosive. The reason gate-by-reversibility beats both is that it is not a compromise on a single axis; it separates the actions onto the axis that matters and applies the right policy to each. The safe actions keep full autonomy (no throughput loss), and the dangerous actions keep full scrutiny (no missed confirmations), because the two groups are handled differently rather than uniformly.

This is a specific instance of matching oversight to blast radius, which runs through agent safety. The same logic scales: within irreversible actions you can gate harder on higher blast radius (deleting one row versus dropping a table), add a dry-run/preview step that shows what an irreversible action would do before doing it, or require a typed confirmation for the most dangerous. The complement is designing tools to be reversible where possible — soft-deletes instead of hard-deletes, drafts instead of sends, staged instead of applied — which shrinks the set that needs gating at all. But the load-bearing idea is this module's: classify by reversibility and spend your confirmations only where they are irreplaceable.

**Reversibility determines the cost of a wrong call, so it is the right gating axis; gating by name or by "writes" is too coarse, and the two uniform policies fail symmetrically — auto-run risks permanent mistakes, confirm-all breeds fatigue — while gating by reversibility gives safe actions autonomy and dangerous ones scrutiny.**

## Worked example

The fixture is a set of tools classified by reversibility and the run the agent made.

```json filename=modules/agent-harness/code/harness-inter-14/tools.json:3-12 COMPLETE
  "tools": {
    "read_file": "read",
    "list_dir": "read",
    "read_config": "read",
    "update_record": "reversible",
    "delete_record": "irreversible",
    "send_email": "irreversible"
  },
  "run": ["read_file", "list_dir", "update_record", "delete_record", "send_email", "read_config"]
```

Three reads, one reversible write, two irreversible actions. Each policy decides, per call, whether to run it automatically or hold it for confirmation.

```python filename=modules/agent-harness/code/harness-inter-14/confirm.py:49-58 COMPLETE
def decide(call, tools, policy):
    """Return 'run' (executed automatically) or 'confirm' (held for user approval)."""
    e = effect(call, tools)
    if policy == "auto":
        return "run"
    if policy == "confirm-all":
        return "confirm"
    if policy == "gate-irreversible":
        return "confirm" if e == IRREVERSIBLE else "run"
    raise ValueError(policy)
```

The two quantities that matter are unconfirmed destructive actions (the safety failure) and prompt count (the fatigue cost).

```python filename=modules/agent-harness/code/harness-inter-14/confirm.py:65-71 COMPLETE
def unconfirmed_destructive(run, tools, policy):
    """Irreversible actions that executed without confirmation -- the ones that can't be undone."""
    return [c for c, e, d in outcomes(run, tools, policy) if e == IRREVERSIBLE and d == "run"]


def prompts(run, tools, policy):
    return [c for c, e, d in outcomes(run, tools, policy) if d == "confirm"]
```

The safe-throughput check reuses one helper — the safe calls a policy still auto-runs — to confirm gating does not slow the harmless work.

```python filename=modules/agent-harness/code/harness-inter-14/confirm.py:74-75 COMPLETE
def auto_ran_safe(run, tools, policy):
    return [c for c, e, d in outcomes(run, tools, policy) if e in SAFE and d == "run"]
```

Predict: auto runs all 6 (both irreversible fire unconfirmed); confirm-all holds all 6 (6 prompts); gate-irreversible runs the 4 safe and confirms the 2 irreversible. Look at the decisions.

```text filename=modules/agent-harness/code/harness-inter-14/confirm.py --run
RUN — each tool call's effect and each policy's decision
------------------------------------------------------------------
  call            effect         auto     confirm-all  gate-irrev
  read_file       read           run      confirm      run
  list_dir        read           run      confirm      run
  update_record   reversible     run      confirm      run
  delete_record   irreversible   run      confirm      confirm
  send_email      irreversible   run      confirm      confirm
  read_config     read           run      confirm      run
------------------------------------------------------------------
  gate-irrev runs the safe calls and confirms only the irreversible ones.
```

Read down the columns. Auto says "run" to everything, including delete_record and send_email — the two calls that cannot be undone execute with no checkpoint. Confirm-all says "confirm" to everything, including three file reads that could not possibly do harm. Gate-irrev is the only column that varies with the effect: "run" for the reads and the reversible write, "confirm" for the delete and the email. It puts the friction exactly on the two rows where a mistake is permanent. Now the tally.

```text filename=modules/agent-harness/code/harness-inter-14/confirm.py --tally
TALLY — unconfirmed destructive actions and prompt count per policy
------------------------------------------------------------------
  policy              unconfirmed destructive   prompts
  auto                2                        0
  confirm-all         0                        6
  gate-irreversible   0                        2
------------------------------------------------------------------
  auto is unsafe (fires destructive); confirm-all is noisy; gate-irrev is both safe and quiet.
```

Auto has 2 unconfirmed destructive actions and 0 prompts — maximally convenient, unsafe. Confirm-all has 0 destructive and 6 prompts — safe, exhausting. Gate-irreversible has 0 destructive and 2 prompts — the only policy that is both safe (no irreversible action ran unconfirmed) and quiet (it asked only about the two calls that warranted it). It matched auto's zero prompts on the safe calls and confirm-all's zero destructive on the dangerous ones, taking the good half of each.

<svg role="img" aria-label="Two-axis comparison: auto has zero prompts but two unconfirmed destructive actions; confirm-all has zero destructive but six prompts; gate-irreversible has zero destructive and only two prompts" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">safety (unconfirmed destructive) and cost (prompts)</text>
  <text x="20" y="46" font-family="var(--mono)" font-size="9" fill="var(--s2)">auto</text>
  <rect x="130" y="36" width="60" height="14" fill="var(--s2)"/>
  <text x="196" y="47" font-family="var(--mono)" font-size="7" fill="var(--s2)">2 destructive unconfirmed — unsafe</text>
  <text x="20" y="90" font-family="var(--mono)" font-size="9" fill="var(--muted)">confirm-all</text>
  <rect x="130" y="80" width="180" height="14" fill="var(--muted)"/>
  <text x="316" y="91" font-family="var(--mono)" font-size="7" fill="var(--muted)">6 prompts — fatigue</text>
  <text x="20" y="134" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">gate-irrev</text>
  <rect x="130" y="124" width="60" height="14" fill="var(--acc-line)"/>
  <text x="196" y="135" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">0 destructive, 2 prompts — safe and quiet</text>
  <line x1="130" y1="150" x2="130" y2="168" stroke="var(--line)"/>
  <text x="60" y="182" font-family="var(--mono)" font-size="8" fill="var(--muted)">gate-irrev takes auto's quiet on safe calls and confirm-all's safety on dangerous ones</text>
</svg>
^ Auto is unsafe (bar = destructive actions), confirm-all is noisy (bar = prompts), and gate-irreversible is short on both — zero destructive and only two prompts, the two irreversible calls.

## Build

Reproduce the policies. Pure standard library, deterministic, so the 2 unconfirmed destructive under auto and the 2 prompts under gating come out exactly.

Run `--run` for the per-call decisions, `--tally` for the summary, `--check` for the gate. <svg role="img" aria-label="Decision flow: a tool call splits on reversibility; reversible or read runs automatically, irreversible is held for confirmation" viewBox="0 0 470 160" width="470" height="160">
  <rect x="0" y="0" width="470" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">gate-by-reversibility, per call</text>
  <rect x="30" y="60" width="90" height="34" fill="var(--panel)" stroke="var(--line)"/>
  <text x="40" y="80" font-family="var(--mono)" font-size="8" fill="var(--ink)">tool call</text>
  <text x="124" y="78" font-family="var(--mono)" font-size="9" fill="var(--muted)">reversible?</text>
  <line x1="120" y1="77" x2="220" y2="45" stroke="var(--acc-line)"/>
  <line x1="120" y1="77" x2="220" y2="115" stroke="var(--s2)"/>
  <rect x="220" y="30" width="150" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="228" y="49" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">yes → run automatically</text>
  <rect x="220" y="100" width="180" height="30" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="228" y="119" font-family="var(--mono)" font-size="8" fill="var(--s2)">no → hold for confirmation</text>
  <text x="150" y="42" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">read / reversible</text>
  <text x="150" y="128" font-family="var(--mono)" font-size="7" fill="var(--s2)">irreversible</text>
</svg>
^ Every call splits on one question — is the effect reversible? — sending the recoverable ones straight to execution and the irreversible ones to a confirmation prompt.

The self-test pins that auto fires destructive actions, gating holds them all, and gating still runs every safe call.

```python filename=modules/agent-harness/code/harness-inter-14/confirm.py:112-116 COMPLETE
    auto_fires_destructive = len(unconfirmed_destructive(run, tools, "auto")) > 0
    print("  auto-run fires irreversible actions with no confirmation = %s (%s)"
          % (auto_fires_destructive, unconfirmed_destructive(run, tools, "auto")))

    gate_holds_destructive = len(unconfirmed_destructive(run, tools, "gate-irreversible")) == 0
    print("  gate-irreversible lets no irreversible action run unconfirmed = %s" % gate_holds_destructive)
```

```text filename=modules/agent-harness/code/harness-inter-14/confirm.py --check
SELF-TEST — auto fires destructive actions unconfirmed; gating only the irreversible ones is safe and quiet
------------------------------------------------------------------------------------------------------------
  auto-run fires irreversible actions with no confirmation = True (['delete_record', 'send_email'])
  gate-irreversible lets no irreversible action run unconfirmed = True
  gate-irreversible still auto-runs every safe call = True (4 safe)
  gate-irreversible prompts less than confirm-all = True (2 vs 6)
  the prompts are exactly the irreversible calls = True (['delete_record', 'send_email'])
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  auto_fires_destructive=True  gate_holds_destructive=True  gate_runs_safe=True  gate_fewer_prompts=True  prompts_are_destructive=True
```

Five True flags. Auto_fires_destructive: auto runs delete_record and send_email unconfirmed. Gate_holds_destructive: gating lets no irreversible action run without confirmation. Gate_runs_safe: it still auto-runs all 4 safe calls, so throughput on the harmless work is untouched. Gate_fewer_prompts: it prompts twice versus confirm-all's six. Prompts_are_destructive: and those two prompts are exactly the irreversible calls, nothing else. The last flag is the precision claim — the confirmations are spent only where they are irreplaceable.

**The prompts-are-destructive flag is the whole win — gating asks about exactly the two irreversible calls and nothing else, so it keeps auto-run's quiet on safe work and confirm-all's safety on dangerous work without inheriting either's flaw.**

## Definition of done

You are done when you reproduce the three policies' tallies and can explain why reversibility is the right axis.

Concretely: `--run` shows gate-irreversible confirming only the delete and the email; `--tally` shows auto at 2 destructive / 0 prompts, confirm-all at 0 / 6, and gate-irreversible at 0 / 2; `--check` prints PASS with five True flags. You can explain that reversibility determines the cost of a wrong call so it is the right thing to gate on, that gating by name or by "writes" is too coarse, and that the two uniform policies fail symmetrically (auto risks permanent mistakes, confirm-all breeds fatigue) while gating by reversibility gives safe actions autonomy and dangerous ones scrutiny. You can name the extensions: dry-run previews, blast-radius tiers, and designing tools to be reversible.

The habit to carry: tag each tool (and, where arguments matter, each call) by reversibility, auto-run the reversible ones, and require confirmation only for the irreversible ones — and prefer designing tools to be reversible (soft-delete, draft, stage) so the gated set stays small. When users complain an agent did something unrecoverable they never approved, the harness was auto-running irreversible tools; when they complain they approve so many prompts they stopped reading, it was gating everything. Spend confirmations where they cannot be taken back.

## Boss fight

The instructive failure is an agent that either deletes production data unprompted or trains its users to rubber-stamp everything.

A team ships an ops agent that can query and modify infrastructure. In the first version it auto-runs every tool, and one day a bad plan has it run a destructive teardown on the wrong environment with no confirmation — a permanent outage. Overreacting, they flip to confirming every tool call, and within a week engineers are approving twenty prompts an hour, almost all for read-only status checks, so they approve on reflex — and the next dangerous action sails through a reflexive click just like the harmless ones. Neither extreme is safe. The fix is to classify each tool by reversibility (reads and reversible changes auto-run; teardowns, deletes, and external sends require confirmation, ideally with a dry-run preview of what will happen), so the prompts are rare enough that engineers actually read them.

Your turn, two moves. First, add blast-radius tiers within the irreversible class — a delete of one record versus a drop of a whole table — and gate the high-blast-radius ones harder (a typed confirmation, say), confirming that spreading scrutiny by severity keeps even the irreversible prompts proportionate. Second, redesign a tool to be reversible: replace the hard delete with a soft delete (mark deleted, purge later) and reclassify it as reversible, then confirm the gated set shrinks and a whole category of prompts disappears — showing that the cheapest way to reduce dangerous confirmations is to make the actions recoverable in the first place.

## External resources

Human-in-the-loop patterns in agent frameworks (LangGraph's interrupt/approval nodes, and similar "require approval before tool execution" hooks) implement exactly this gate, and their docs discuss classifying which tools need approval.

The Model Context Protocol's tool annotations include hints like readOnlyHint and destructiveHint, which are the reversibility tags this module gates on, letting a client decide what to auto-run and what to confirm.

Writing on automation and alarm fatigue (from aviation, medicine, and security operations) is the evidence base for why confirm-everything fails — when alerts are mostly noise, operators habituate and miss the real one, which is the human factor behind gating only the actions that matter.
