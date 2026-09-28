---
id: resultcover-inter-01
title: Emit a tool_result for every tool_use id the model produced — a declined or unknown call still needs its result block, or the next request is rejected
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A provider that speaks tool calls enforces a structural rule on the transcript — an assistant message that contains tool_use blocks must be immediately followed by a user message whose tool_result blocks answer every one of those ids. The pairing is on ids, not on outcomes: each tool_use must have exactly one matching tool_result, and there must be no tool_result for an id that was never requested. The trap is that "answer every id" includes the calls the harness did not execute. A call gated as irreversible and declined, a call whose name is unknown, a call skipped because a per-tool budget is spent — none of these did any work, so it feels natural to append nothing for them. But the assistant turn still carries their tool_use blocks, and leaving them unanswered dangles those ids; the provider sees tool_use ids with no answering tool_result and rejects the whole next request, aborting a run in which most of the calls succeeded. So a call's disposition decides the content of its tool_result — a "declined" or "no such tool" observation — never whether one exists. On a fixture where the model emits four tool_use blocks (two to run, one declined, one an unknown name), a naive harness answers only the two it ran and dangles two ids, making the turn malformed; a correct harness answers all four and the turn is well-formed.
eli5: Imagine a waiter takes four orders at your table and carries them to the kitchen. Two are easy, one the kitchen refuses because it's off the menu, and one is for a dish that doesn't exist. When the waiter comes back, they have to say something about all four — "here are your two dishes, sorry we can't make the third, and the fourth isn't a thing we serve" — because you're keeping track of every order you placed. If the waiter just brings the two easy dishes and says nothing about the other two, you're left staring at the table wondering what happened, and you refuse to place the next order until every order from last round is accounted for. A tool-using agent talks to the model the same way: the model placed four calls, so the harness owes it an answer for all four — even the ones it declined or couldn't find. Skip one and the whole next round is rejected.
---

## Why this module

When a model calls tools, the transcript has a shape the provider enforces. The assistant produces a message with one or more tool_use blocks, each carrying a unique id. The harness must then send back a user message whose tool_result blocks answer those calls — and the provider validates that answer structurally before the model runs again. Two conditions have to hold: every tool_use id has exactly one matching tool_result, and no tool_result names an id that was never requested. It is a bijection between the ids going out and the ids coming back.

The pairing is on ids, not on outcomes. This is the part that is easy to get wrong, because a harness naturally thinks in terms of work done. It executes the calls it can, and for each it produces an observation to return. The calls it does not execute — one it gates as irreversible and refuses, one whose name it does not recognize, one it skips because a per-tool budget is exhausted — did no work and produced no observation, so the reflex is to append nothing for them.

That reflex breaks the transcript. The assistant turn still carries the tool_use blocks for those declined and unknown calls; they were part of what the model emitted. Leaving them unanswered dangles their ids, and the provider rejects the entire next request as malformed — not the one bad call, the whole turn, including the two calls that succeeded perfectly. This module runs a turn with a mix of dispositions through a naive harness and a correct one and checks which ids dangle.

**A provider validates the tool transcript on id coverage, not on whether work was done — so every tool_use id needs a tool_result, and a call you decline or cannot resolve still needs one, or the next request is rejected.**

## Concepts

The disposition of a call — run, decline, unknown, over-budget — decides the content of its tool_result, never whether one exists. A normal call gets its real observation. A declined call gets a result whose text says it was refused. An unknown name gets a result whose text says no such tool. Every one of them is a tool_result block bearing the call's id; they differ only in what they say.

That separation is the whole idea. It is tempting to conflate "I did not run this" with "I have nothing to send back", but those are different layers. Whether to run a call is a policy decision — gating, budgets, name resolution — and this module does not argue with any of it. What it insists on is that the policy decision produces a tool_result either way, because the transcript layer underneath does not know or care about your policy; it counts ids.

The failure is silent until the next request. The harness that skips results for declined calls looks fine — it ran the right calls, refused the dangerous one, handled the unknown name gracefully. Everything it chose to do was correct. Then it assembles the next request, the provider counts two tool_use ids with no answering tool_result, and rejects it. A run that made good decisions dies on a bookkeeping rule.

<svg role="img" aria-label="Two stacked layers: a policy layer that assigns each call a disposition, and a transcript layer beneath it that requires one result per id regardless of disposition" viewBox="0 0 440 150">
<rect x="20" y="20" width="400" height="45" fill="var(--panel)" stroke="var(--line)"/>
<text x="30" y="38" fill="var(--ink)" font-size="10">policy layer: pick disposition</text>
<text x="70" y="56" fill="var(--s1)" font-size="9" text-anchor="middle">run</text>
<text x="150" y="56" fill="var(--s1)" font-size="9" text-anchor="middle">decline</text>
<text x="240" y="56" fill="var(--s1)" font-size="9" text-anchor="middle">unknown</text>
<text x="340" y="56" fill="var(--s1)" font-size="9" text-anchor="middle">over-budget</text>
<line x1="70" y1="65" x2="70" y2="90" stroke="var(--muted)"/>
<line x1="150" y1="65" x2="150" y2="90" stroke="var(--muted)"/>
<line x1="240" y1="65" x2="240" y2="90" stroke="var(--muted)"/>
<line x1="340" y1="65" x2="340" y2="90" stroke="var(--muted)"/>
<rect x="20" y="90" width="400" height="45" fill="var(--panel)" stroke="var(--line)"/>
<text x="30" y="108" fill="var(--ink)" font-size="10">transcript layer: one tool_result per id</text>
<text x="220" y="127" fill="var(--muted)" font-size="9" text-anchor="middle">every disposition still produces exactly one result block</text>
</svg>
^ The policy layer decides the disposition; the transcript layer beneath it demands one result per id whatever that disposition was.

**Deciding not to run a call and having nothing to return are different layers: the policy layer picks the disposition, the transcript layer still demands one tool_result per id — so a declined call's result exists, it just says "declined".**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/resultcover-inter-01. The fixture is one assistant turn's tool_use blocks, each with an id, a name, and the disposition the harness assigned.

```json filename=modules/agent-harness/code/resultcover-inter-01/resultcover.json:3-8 COMPLETE
  "calls": [
    {"id": "call_a1", "name": "search_docs", "disposition": "run"},
    {"id": "call_b2", "name": "read_file", "disposition": "run"},
    {"id": "call_c3", "name": "delete_record", "disposition": "decline"},
    {"id": "call_d4", "name": "frobnicate", "disposition": "unknown"}
  ]
```

The naive harness emits a tool_result only for the calls it actually executed.

```python filename=modules/agent-harness/code/resultcover-inter-01/resultcover.py:32-34 COMPLETE
def naive_results(calls):
    """A naive harness emits a tool_result only for calls it actually executed."""
    return [c["id"] for c in calls if c["disposition"] == "run"]
```

The correct harness emits one tool_result for every id, whatever its disposition.

```python filename=modules/agent-harness/code/resultcover-inter-01/resultcover.py:37-39 COMPLETE
def correct_results(calls):
    """A correct harness emits one tool_result for every id, whatever its disposition."""
    return [c["id"] for c in calls]
```

A turn is well-formed only when the two id sets are a bijection.

```python filename=modules/agent-harness/code/resultcover-inter-01/resultcover.py:48-51 COMPLETE
def well_formed(calls, result_ids):
    """A turn is well-formed iff the tool_use ids and tool_result ids are a bijection."""
    use_ids = [c["id"] for c in calls]
    return sorted(use_ids) == sorted(result_ids)
```

Before running it, predict: the two `run` calls get a result under both harnesses; the `decline` and `unknown` calls get one only under the correct harness. Run `--coverage`:

```text filename=resultcover.py --coverage
COVERAGE — does each tool_use id get a tool_result?
------------------------------------------------------------------
  id         name            disposition   naive   correct
  call_a1    search_docs     run           True    True
  call_b2    read_file       run           True    True
  call_c3    delete_record   decline       False   True
  call_d4    frobnicate      unknown       False   True
------------------------------------------------------------------
  the naive harness only answers the calls it ran; the correct one answers all
```

The prediction holds. The two `run` ids are covered by both; the declined `call_c3` and the unknown `call_d4` are covered only by the correct harness. Those two Falses in the naive column are the dangling ids the provider will reject on.

<svg role="img" aria-label="Four tool_use ids on the left connect to tool_result blocks on the right; under the naive harness two ids have arrows and two have none, under the correct harness all four have arrows" viewBox="0 0 440 200">
<text x="110" y="20" fill="var(--ink)" font-size="11" text-anchor="middle">naive</text>
<text x="60" y="45" fill="var(--muted)" font-size="9">tool_use</text>
<text x="160" y="45" fill="var(--muted)" font-size="9">tool_result</text>
<text x="40" y="70" fill="var(--ink)" font-size="10">call_a1</text>
<line x1="80" y1="66" x2="150" y2="66" stroke="var(--s1)"/>
<rect x="152" y="59" width="30" height="12" fill="var(--s1)"/>
<text x="40" y="92" fill="var(--ink)" font-size="10">call_b2</text>
<line x1="80" y1="88" x2="150" y2="88" stroke="var(--s1)"/>
<rect x="152" y="81" width="30" height="12" fill="var(--s1)"/>
<text x="40" y="114" fill="var(--muted)" font-size="10">call_c3</text>
<text x="152" y="118" fill="var(--s2)" font-size="14">?</text>
<text x="40" y="136" fill="var(--muted)" font-size="10">call_d4</text>
<text x="152" y="140" fill="var(--s2)" font-size="14">?</text>
<text x="110" y="165" fill="var(--s2)" font-size="10" text-anchor="middle">2 dangling: rejected</text>
<text x="330" y="20" fill="var(--ink)" font-size="11" text-anchor="middle">correct</text>
<text x="280" y="45" fill="var(--muted)" font-size="9">tool_use</text>
<text x="380" y="45" fill="var(--muted)" font-size="9">tool_result</text>
<text x="260" y="70" fill="var(--ink)" font-size="10">call_a1</text>
<line x1="300" y1="66" x2="370" y2="66" stroke="var(--s1)"/>
<rect x="372" y="59" width="30" height="12" fill="var(--s1)"/>
<text x="260" y="92" fill="var(--ink)" font-size="10">call_b2</text>
<line x1="300" y1="88" x2="370" y2="88" stroke="var(--s1)"/>
<rect x="372" y="81" width="30" height="12" fill="var(--s1)"/>
<text x="260" y="114" fill="var(--ink)" font-size="10">call_c3</text>
<line x1="300" y1="110" x2="370" y2="110" stroke="var(--s1)"/>
<rect x="372" y="103" width="30" height="12" fill="var(--s1)"/>
<text x="260" y="136" fill="var(--ink)" font-size="10">call_d4</text>
<line x1="300" y1="132" x2="370" y2="132" stroke="var(--s1)"/>
<rect x="372" y="125" width="30" height="12" fill="var(--s1)"/>
<text x="330" y="165" fill="var(--ink)" font-size="10" text-anchor="middle">0 dangling: well-formed</text>
</svg>
^ The naive harness leaves the declined and unknown ids unanswered; the correct harness answers all four, so the id sets match.

Now the verdict the provider actually computes — is the pairing a bijection? Run `--wellformed`:

```text filename=resultcover.py --wellformed
WELL-FORMED — is the tool_use / tool_result pairing a bijection?
----------------------------------------------------------------
  tool_use ids: ['call_a1', 'call_b2', 'call_c3', 'call_d4']
  naive   results=['call_a1', 'call_b2']  dangling=['call_c3', 'call_d4']  well_formed=False
  correct results=['call_a1', 'call_b2', 'call_c3', 'call_d4']  dangling=[]  well_formed=True
```

The naive turn is not well-formed — two ids dangle — and the provider rejects the next request outright. The correct turn has no dangling ids and passes. The two calls that ran successfully are identical in both; the only difference is whether the two calls that did no work got their result blocks anyway.

<svg role="img" aria-label="Two request outcomes: the naive turn with two dangling ids is stamped rejected, the correct turn with full coverage is stamped accepted" viewBox="0 0 440 120">
<rect x="20" y="30" width="180" height="60" fill="var(--panel)" stroke="var(--s2)"/>
<text x="110" y="52" fill="var(--ink)" font-size="10" text-anchor="middle">naive turn</text>
<text x="110" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">2 of 4 ids answered</text>
<text x="110" y="105" fill="var(--s2)" font-size="11" text-anchor="middle">next request REJECTED</text>
<rect x="240" y="30" width="180" height="60" fill="var(--panel)" stroke="var(--s1)"/>
<text x="330" y="52" fill="var(--ink)" font-size="10" text-anchor="middle">correct turn</text>
<text x="330" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">4 of 4 ids answered</text>
<text x="330" y="105" fill="var(--s1)" font-size="11" text-anchor="middle">next request ACCEPTED</text>
</svg>
^ One dangling id is enough: the naive turn's next request is rejected whole, while the fully-covered turn proceeds.

## Build

The self-test plants the failure and names each claim as a boolean flag. It builds the naive and correct result sets, computes the dangling ids of each, and checks that the naive turn dangles exactly the non-executed calls and is malformed, while the correct turn covers every id and is well-formed.

```python filename=modules/agent-harness/code/resultcover-inter-01/resultcover.py:92-104 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly the moment the harness stops covering every id:

```text filename=resultcover.py --check
SELF-TEST — a harness that answers only executed calls dangles the declined and unknown ids; answering every id is well-formed
--------------------------------------------------------------------------------------------------------------------------------
  naive: some tool_use ids have no tool_result = True (['call_c3', 'call_d4'])
  naive: the turn is malformed (not a bijection) = True
  naive: exactly the non-executed calls dangle = True
  correct: every tool_use id has a tool_result = True
  correct: the turn is well-formed (bijection) = True
--------------------------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_has_dangling=True  naive_malformed=True  dangling_are_nonrun=True  correct_no_dangling=True  correct_wellformed=True
```

**The self-test asserts that exactly the non-executed calls dangle — not just that something is missing — so a harness that also drops a call it did run, or invents a result for an id nobody requested, fails a different flag instead of passing.**

## Definition of done

You can state the provider's transcript invariant as a bijection: every tool_use id has exactly one tool_result, and no tool_result names an unrequested id.
You can explain why a declined or unknown call still needs a tool_result, and describe what that result's content should say.
You can separate the two layers — the policy decision of whether to run a call from the transcript requirement that it be answered — and say which one this rule lives in.
You can predict that the failure is silent until the next request, and that the rejection discards the whole turn including the calls that succeeded.
You can name the two ways a turn fails the bijection: a tool_use id left unanswered, and a tool_result for an id that was never requested.

## Boss fight

Add a fifth disposition to the fixture — a call marked `over-budget`, skipped because a per-tool cap was hit — and rerun `--check` without changing the harness. The naive harness still answers only `run` calls, so the over-budget id joins the dangling set; the `dangling_are_nonrun` flag stays true because that id is genuinely non-run, and the naive turn is still malformed. The correct harness answers it too, so it stays well-formed. The lesson holds under a new disposition: the transcript layer does not care why you skipped, only that the id is unanswered.

Now try the other failure mode. Make `correct_results` return the ids twice — a duplicate tool_result for one id — and rerun. The `well_formed` check is `sorted(use_ids) == sorted(result_ids)`, so a duplicated result id makes the result list longer than the tool_use list, the sorted lists differ, and `correct_wellformed` flips to false. The bijection catches over-answering just as it catches under-answering: two tool_results for one call is as malformed as none.

**The invariant is symmetric — a missing result and a duplicate result both break the bijection — so a correct harness emits one result per id, not at-least-one and not at-most-one.**

## External resources

Anthropic's tool-use documentation specifies that an assistant message with tool_use blocks must be followed by a user message with a tool_result for each, and describes returning errors as tool_results rather than omitting them.
The OpenAI function-calling guide states the parallel requirement — every tool call in a turn must be answered with a matching tool message id before the next completion — for that provider's transcript format.
The topic's own modules on returning tool errors as observations and on handling unknown tool names cover the content of these result blocks; this module covers the structural rule that one must exist at all.
