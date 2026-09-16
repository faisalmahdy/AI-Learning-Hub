---
id: thinkexec-inter-01
title: Execute tool calls only from the action channel, not the model's reasoning — the chain-of-thought names tools it was only considering
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: Modern models emit a reasoning trace — a chain-of-thought or scratchpad — alongside their committed actions, and in that trace they think out loud, routinely naming tools they are weighing but have not chosen: "I could call delete_account to reset it, but first let me check the status." The reasoning is deliberation; the decision is separate, and the tool-calling API keeps them separate on purpose — committed calls come back as structured data in a dedicated action field while the reasoning is free text in a different field. The bug is dispatching by pattern-matching the model's whole output: a harness that greps the text for tool-call-shaped mentions cannot tell "I will call X" from "I could call X but won't," so it executes every tool it finds, including the one the model named only to reject it. It has now performed an action the model deliberately deferred, and if that action is irreversible the harness has caused real harm from a thought — and the more a model reasons about dangerous options (which is what you want it to do), the more such phantom calls a text scanner fires. The fix is to dispatch strictly from the action channel and treat the reasoning purely as data to log, never as a source of executable calls. On a fixture where the model's reasoning mentions delete_account (considered, then deferred) and get_status while its action field commits only to get_status, a text-scanning dispatcher runs both — including the destructive delete — while an action-channel dispatcher runs only get_status.
eli5: Imagine a surgeon thinking out loud while a very literal robot assistant listens: "I could amputate the leg, but that's drastic, so first let me take an X-ray." A good assistant hands over the X-ray machine, because that is what the surgeon actually asked for. A dangerous assistant hears the word "amputate" and starts cutting, because it treats everything the surgeon says as a command instead of noticing that the surgeon was weighing an option and rejected it. Thinking about doing something is not deciding to do it. A tool-running program has to listen only to the surgeon's actual instructions, not to the musing, or it will act on ideas that were considered and thrown away — sometimes the most harmful ones, because those are exactly the ones worth thinking hard about first.
---

## Why this module

An agent turn now has two kinds of output, and conflating them is the whole bug. There is the model's reasoning — a chain-of-thought where it works through the problem, weighs options, and talks itself toward a plan — and there is its action, the tool call it actually commits to. The tool-calling API returns these in separate fields: the reasoning as free text, the committed call as structured data with a tool name and arguments.

The reason to keep them apart is that reasoning is full of tools the model is not going to call. It names candidates to compare them, it raises dangerous options to rule them out, it says "I could do X but that is risky, so instead I will do Y." Every one of those mentions is a tool name sitting in the text, attached to a verb, looking exactly like an intention — and most of them are the opposite of an intention, they are options examined and set aside.

A harness that decides what to run by scanning the model's text for tool-call-shaped mentions cannot tell the difference, because there is no textual difference between "I will call X" and "I could call X but won't" that a pattern match reliably catches. So it executes the considered-and-rejected tools alongside the chosen one. The failure is worst exactly where reasoning is most valuable: the model that carefully thinks through whether to delete something before deciding not to is the model whose careful thought gets executed as a deletion.

**A model's reasoning names tools it is only considering, not committing to, so a harness that extracts tool calls by scanning the reasoning text executes actions the model deferred or rejected — most dangerously the risky options it reasoned about precisely to avoid.**

## Concepts

The clean model is that the turn has two channels, and only one of them is authoritative for execution. The action channel carries the model's decision — structured, unambiguous, a tool and its arguments — and it is the contract by which the model tells the harness what to do. The reasoning channel carries the model's private process — free text, hypotheticals, comparisons — and it is for the model's benefit and for a human reading the trace, not a set of instructions to the runtime.

<svg role="img" aria-label="A model turn split into two channels. The reasoning channel is free text mentioning delete_account and get_status. The action channel is a structured call to get_status only. An arrow marks the action channel as the one the dispatcher should read." viewBox="0 0 440 140">
<text x="220" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">one model turn, two channels</text>
<rect x="20" y="26" width="400" height="40" fill="var(--panel)" stroke="var(--line)"/>
<text x="30" y="42" fill="var(--muted)" font-size="8">reasoning (free text):</text>
<text x="30" y="56" fill="var(--ink)" font-size="8">"I could call delete_account ... but first check with get_status"</text>
<text x="200" y="80" fill="var(--muted)" font-size="7" text-anchor="middle">deliberation — for logging, not execution</text>
<rect x="20" y="92" width="400" height="30" fill="var(--panel)" stroke="var(--s1)"/>
<text x="30" y="108" fill="var(--muted)" font-size="8">action (structured):</text>
<text x="180" y="108" fill="var(--s1)" font-size="8">get_status(account="a-42")</text>
<text x="360" y="108" fill="var(--s1)" font-size="8">&#8592; dispatch here</text>
</svg>
^ The turn has a free-text reasoning channel (a deliberation that names delete_account and get_status) and a structured action channel (the committed get_status) — only the action channel is a decision.

The bug lives in how the dispatcher reads the turn. A text-scanning dispatcher treats the whole output as one blob and pulls out anything that looks like a call, so it harvests the tools named in the reasoning as well as the real one. Because the reasoning here mentions delete_account only to defer it, the scanner runs a destructive action the model chose not to take. An action-channel dispatcher reads only the structured field, so it runs exactly the model's decision and nothing else.

<svg role="img" aria-label="Two dispatchers reading the same turn. The text scanner reads both channels and executes delete_account and get_status. The action-channel dispatcher reads only the action field and executes get_status." viewBox="0 0 440 140">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">text scanner</text>
<text x="110" y="34" fill="var(--muted)" font-size="8" text-anchor="middle">reads reasoning + action</text>
<rect x="40" y="44" width="140" height="16" fill="var(--s2)"/><text x="110" y="56" fill="var(--ink)" font-size="8" text-anchor="middle">delete_account</text>
<rect x="40" y="62" width="140" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="110" y="74" fill="var(--ink)" font-size="8" text-anchor="middle">get_status</text>
<text x="110" y="94" fill="var(--s2)" font-size="8" text-anchor="middle">runs the deferred delete</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">action channel</text>
<text x="330" y="34" fill="var(--muted)" font-size="8" text-anchor="middle">reads action only</text>
<rect x="260" y="44" width="140" height="16" fill="var(--panel)" stroke="var(--s1)"/><text x="330" y="56" fill="var(--ink)" font-size="8" text-anchor="middle">get_status</text>
<text x="330" y="94" fill="var(--s1)" font-size="8" text-anchor="middle">runs only the decision</text>
</svg>
^ The text scanner harvests both channels and executes the deferred delete_account; the action-channel dispatcher reads only the committed field and executes get_status alone.

This is a distinct trust boundary from a neighboring one. A companion module says tool output is data, not instructions — that is about a message from the tool role trying to command the harness. This is about the model's own turn: even the model's authored text is not all a decision, so the boundary is drawn not by who sent the message but by which channel of the model's own output carries a commitment. Reasoning is the model talking to itself; the action field is the model talking to the harness, and only the latter is an order.

**The turn's action channel carries the model's decision and the reasoning channel carries its deliberation; dispatch only from the action channel, because a text scanner cannot distinguish a considered option from a committed one and will run the tools the model reasoned about rejecting.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/thinkexec-inter-01. The fixture is one model turn: a reasoning string, the tool names it mentions, the structured action it committed to, and which tools are destructive.

```json filename=modules/agent-harness/code/thinkexec-inter-01/thinkexec.json:3-6 COMPLETE
  "reasoning": "The account looks corrupted. I could call delete_account to reset it, but that is irreversible, so first let me check the status with get_status before deciding.",
  "mentioned_tools": ["delete_account", "get_status"],
  "action": {"tool": "get_status", "args": {"account": "a-42"}},
  "destructive_tools": ["delete_account"]
```

The scanning dispatcher executes every tool named anywhere in the output.

```python filename=modules/agent-harness/code/thinkexec-inter-01/thinkexec.py:32-37 COMPLETE
def scan_dispatch(data):
    """BUG: extract tool calls by scanning all the model's output, reasoning included."""
    executed = list(data["mentioned_tools"])      # every tool named anywhere, including in reasoning
    if data["action"]["tool"] not in executed:
        executed.append(data["action"]["tool"])
    return executed
```

The action-channel dispatcher executes only the committed call.

```python filename=modules/agent-harness/code/thinkexec-inter-01/thinkexec.py:40-42 COMPLETE
def action_dispatch(data):
    """FIX: execute only the call committed in the structured action channel."""
    return [data["action"]["tool"]]
```

Either way, we flag which executed tools are irreversible.

```python filename=modules/agent-harness/code/thinkexec-inter-01/thinkexec.py:45-47 COMPLETE
def destructive_executed(executed, data):
    """Which executed tools are irreversible."""
    return [t for t in executed if t in data["destructive_tools"]]
```

Before running it, predict: the reasoning mentions delete_account only to defer it, so a text scanner will execute it even though the action field commits only to get_status. Run `--scan`:

```text filename=thinkexec.py --scan
SCAN — a dispatcher that pattern-matches the model's whole output
--------------------------------------------------------
  reasoning : The account looks corrupted. I could call delete_account to reset it, but that is irreversible, so first let me check the status with get_status before deciding.
  executed  : ['delete_account', 'get_status']
  destructive among them: ['delete_account']
--------------------------------------------------------
  it ran ['delete_account'], which the model only considered and then deferred
```

The prediction holds, and the harm is concrete. The scanner executed both delete_account and get_status, and delete_account is irreversible — the account is gone. But read the reasoning: the model named delete_account specifically to reject it ("that is irreversible, so first let me check the status"), and committed to get_status instead. The scanner turned the model's careful decision *not* to delete into a deletion, because it read the deliberation as instructions.

Now the action-channel dispatcher on the identical turn. Run `--action`:

```text filename=thinkexec.py --action
ACTION — a dispatcher that runs only the committed action channel
--------------------------------------------------------
  action field: {'tool': 'get_status', 'args': {'account': 'a-42'}}
  executed    : ['get_status']
  destructive among them: []
--------------------------------------------------------
  it ran only the call the model actually decided on
```

Same turn, same reasoning, but this dispatcher reads only the structured action field and runs get_status alone — nothing destructive, exactly the model's decision. The model's reasoning is untouched as a decision-maker; it can be logged and shown to a human, but it does not drive execution. The only difference between a data lookup and a destroyed account was which channel the harness dispatched from.

<svg role="img" aria-label="A comparison of executed tools. The text scanner executes get_status and delete_account, with delete_account marked destructive and 'deferred by the model'. The action channel executes only get_status." viewBox="0 0 440 120">
<text x="20" y="18" fill="var(--muted)" font-size="9">executed tools</text>
<text x="70" y="44" fill="var(--ink)" font-size="8" text-anchor="end">scan</text>
<rect x="78" y="34" width="90" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="123" y="46" fill="var(--ink)" font-size="8" text-anchor="middle">get_status</text>
<rect x="172" y="34" width="110" height="16" fill="var(--s2)"/><text x="227" y="46" fill="var(--ink)" font-size="8" text-anchor="middle">delete_account</text>
<text x="292" y="46" fill="var(--s2)" font-size="7">destructive, deferred</text>
<text x="70" y="80" fill="var(--ink)" font-size="8" text-anchor="end">action</text>
<rect x="78" y="70" width="90" height="16" fill="var(--s1)"/><text x="123" y="82" fill="var(--ink)" font-size="8" text-anchor="middle">get_status</text>
<text x="180" y="82" fill="var(--s1)" font-size="7">only the committed call</text>
</svg>
^ The scanner executes the committed get_status plus the deferred, destructive delete_account; the action channel executes only get_status.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the reasoning mentions a destructive tool, that the committed action is not that tool, that the text scanner executes the destructive tool, that the action-channel dispatcher runs only the committed call, and that it runs nothing destructive.

```python filename=modules/agent-harness/code/thinkexec-inter-01/thinkexec.py:81-93 COMPLETE
    reasoning_mentions_destructive = any(t in data["destructive_tools"] for t in data["mentioned_tools"])
    print("  the reasoning mentions a destructive tool = %s (%s)" % (reasoning_mentions_destructive, [t for t in data["mentioned_tools"] if t in data["destructive_tools"]]))

    committed_is_not_destructive = committed not in data["destructive_tools"]
    print("  the committed action is NOT that destructive tool = %s (committed %s)" % (committed_is_not_destructive, committed))

    scan_runs_destructive = len(destructive_executed(scan, data)) > 0
    print("  the text scanner executes the destructive tool = %s (%s)" % (scan_runs_destructive, destructive_executed(scan, data)))

    action_runs_only_committed = act == [committed]
    print("  the action-channel dispatcher runs only the committed call = %s (%s)" % (action_runs_only_committed, act))

    action_runs_nothing_destructive = len(destructive_executed(act, data)) == 0
    print("  the action-channel dispatcher runs nothing destructive = %s" % action_runs_nothing_destructive)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the scanner ever stopped running the deferred tool or the action channel ever leaked one:

```text filename=thinkexec.py --check
SELF-TEST — the text scanner executes a deferred destructive tool from the reasoning; the action channel executes only the committed call
----------------------------------------------------------------------------------------------------------------
  the reasoning mentions a destructive tool = True (['delete_account'])
  the committed action is NOT that destructive tool = True (committed get_status)
  the text scanner executes the destructive tool = True (['delete_account'])
  the action-channel dispatcher runs only the committed call = True (['get_status'])
  the action-channel dispatcher runs nothing destructive = True
```

**The self-test asserts the committed action is not the destructive tool and yet the scanner runs it — pinning the exact gap: the harm is not a wrong decision by the model (it decided correctly) but the harness executing a thought the model explicitly set aside.**

## Definition of done

You can explain the difference between a turn's reasoning channel and its action channel, and which is authoritative for execution.
You can explain why reasoning routinely names tools the model is not going to call, including dangerous ones.
You can explain why a text scanner cannot distinguish a considered option from a committed one.
You can explain why this is a distinct trust boundary from "tool output is data" — it concerns the model's own output, split by channel.
You can predict that the failure is worst for exactly the careful reasoning you want the model to do.

## Boss fight

Suppose your provider does not give a clean structured action channel — it returns one text blob, and tool calls are expected inline in an agreed format (a JSON block, a specific tag). Reason about how to recover the boundary. You cannot rely on the model's prose discipline, so you have to impose the structure: define one unambiguous, machine-checkable action syntax (a fenced tool-call block, a required schema) and execute only calls that appear in that exact form, treating everything outside it — including tool names in ordinary sentences — as reasoning. This is why structured output and constrained decoding matter: they recreate the action channel the API would otherwise provide, giving you a syntactic marker that separates commitment from musing. The weak version — "look for a line starting with CALL:" — is better than scanning prose but still fragile if the model writes "CALL: delete... just kidding"; the robust version constrains the model to emit calls only in a form the harness parses and the model cannot accidentally produce while thinking. The principle: if the channel is not given, manufacture it, and never fall back to interpreting free prose as commands.

Now the trap that makes this bug re-appear at the confirmation gate. Suppose you correctly dispatch only from the action channel, but you also show the user the model's reasoning and let them approve actions from a summary. If the summary or the confirmation prompt is generated from the reasoning text rather than the action channel, a human can approve "get status" while the action field actually carries something else, or vice versa — the display and the executed call have drifted apart. The safety property is that everything a human sees and approves must be rendered from the same action channel that is executed, not from the prose that accompanies it. The general rule generalizes the module: the reasoning is never the source of truth for what runs — not for the dispatcher, and not for the confirmation UI — because the moment any execution-relevant decision is read from the deliberation, a considered-but-rejected option can slip through as a real one.

**When the provider gives no structured action channel, manufacture one with a strict, machine-checkable call syntax (structured output / constrained decoding) and execute only calls in that exact form; and render every confirmation and audit view from the action channel too, never from the reasoning, so what a human approves is always what actually runs.**

## External resources

The tool-use / function-calling documentation for major model APIs specifies that committed tool calls are returned in a dedicated structured field separate from any assistant text or reasoning, and that only that field should be executed.
Writing on agent security and prompt-injection defense distinguishes the model's deliberation from its committed actions and warns against parsing actions out of free-form model text.
The topic's own module on treating tool output as data, not instructions, covers the neighboring trust boundary (an untrusted message role), while this one draws the boundary inside the model's own turn, between its reasoning and its action.
