---
id: harness-inter-04
title: Compact the context by evicting the oldest unpinned turns — never the pinned ones
topic: agent-harness
level: intermediate
status: ready
time: 8-10h
summary: When an agent's context exceeds its token budget the harness must evict something, and what it drops decides whether the agent keeps working — the system prompt and task are pinned and must survive, while the old conversational turns are evictable oldest-first. The correct policy keeps both pinned items and fills the remaining budget with the most recent turns, landing at exactly 100 tokens with sys, task, and the two latest turns. Plain FIFO — evict the oldest until it fits — also lands at 100 tokens but drops the system prompt and task first, because they are the oldest items, so the context fits the budget and the agent has forgotten who it is and what it is doing. Fitting the budget is necessary but not sufficient: the eviction must preserve the must-keep set, and FIFO passes the size check while failing the one that matters.
eli5: When your backpack is too full, you take out things you do not need right now — not your name tag and the instructions for where you are going. A dumb rule that just removes whatever is at the bottom of the bag will throw out the name tag first, because you packed it earliest. The bag closes fine, but now you are wandering around with no idea who you are or where to go.
---

## Why this module

Every long-running agent hits its context limit, and the harness has to decide what to keep. This is not a rare edge case — it happens on any task long enough to matter, and the eviction policy is one of the quietest, highest-stakes pieces of a harness, because a wrong choice does not crash, it lobotomizes. This module builds the compaction step and the specific bug that a naive implementation falls into: dropping the very items the agent cannot function without, while passing the only check a careless implementation bothers to run — does it fit.

The structure is a must-keep set and an evictable remainder. Some context items are pinned: the system prompt that defines the agent, and the task it is working on. These must survive every compaction, because without them the agent forgets its identity and its goal. Everything else is the conversation, and it is evictable oldest-first, because recent turns carry the live state of the work and old ones are stale. The correct policy keeps all pinned items and fills whatever budget remains with the most recent unpinned turns. The tempting bug is plain FIFO — evict the oldest item until the total fits, pinned or not. And the oldest items in a conversation are precisely the system prompt and the task, set at the very start, so FIFO evicts them first. The result fits the budget perfectly and is useless: the agent has the recent chatter and none of its instructions.

You need the agent-loop framing from the earlier harness modules. Everything runs offline against a context fixture — six items with token costs and pinned flags, over a budget — stdlib Python 3, `$0.00`. The instinct to unlearn is that compaction is a size problem. It is a size problem with a hard constraint: fit the budget while preserving the must-keep set, and an eviction that satisfies the first and violates the second is worse than no compaction at all, because it looks like it worked.

Here is the context, over budget:

```
# modules/agent-harness/code/harness-inter-04/ — COMPLETE, run from that directory
$ python3 compact.py --window

WINDOW — the context (oldest first), budget = 100 tokens
------------------------------------------------------------------
  sys     30 tok  PINNED   system prompt
  task    20 tok  PINNED   the task
  turn1   25 tok           old exchange
  turn2   25 tok           old exchange
  turn3   25 tok           recent exchange
  turn4   25 tok           latest exchange
------------------------------------------------------------------
  total = 150 tokens, over budget by 50.
```

run: 2026-08-26 · deterministic; context is a fixture · budget 100 · `python3 compact.py --window`

Six items totaling 150 tokens against a 100-token budget — 50 must go. The two pinned items sit at the top, because they are the oldest. This module is which 50 tokens you drop, and the bug that drops the wrong ones.

## Concepts

Named here so you can find them again; each is built below.

- **Context budget** — the token limit the assembled context must fit under.
- **Pinned item** — context that must survive compaction: the system prompt, the task.
- **Evictable turn** — conversational context that can be dropped, oldest-first.
- **Compaction** — evicting items to bring the context under budget.
- **Recency** — keeping the most recent turns, which carry the live state.
- **FIFO eviction** — the bug: dropping the oldest item regardless of pinned status.

## Worked example

Source: the context-management step every agent harness implements when the window overflows (summarization and eviction policies, the "keep system + recent, drop the middle" pattern); the items and budget here stand in for a real context so the fit and the retained-pinned check are exact and checkable.

Script and fixture: `modules/agent-harness/code/harness-inter-04/` — `compact.py`, and `context.json`, six items with token costs and pinned flags over a 100-token budget. Every command runs from there.

### The correct policy: keep pinned, fill with recent

Two rules: every pinned item stays, and the remaining budget goes to the most recent unpinned turns.

```
# compact.py:50-62 — COMPLETE (keep pinned, fill remaining budget with recent unpinned)
def compact_correct(items, budget):
    """Keep every pinned item; fill the rest of the budget with the most RECENT unpinned."""
    pinned = [it for it in items if it["pinned"]]
    unpinned = [it for it in items if not it["pinned"]]
    kept = list(pinned)
    used = total_tokens(pinned)
    for it in reversed(unpinned):          # most recent first
        if used + it["tokens"] <= budget:
            kept.append(it)
            used += it["tokens"]
    # restore chronological order
    order = {it["id"]: i for i, it in enumerate(items)}
    return sorted(kept, key=lambda it: order[it["id"]])
```

The pinned items go in unconditionally, consuming 50 of the 100 tokens. The `reversed(unpinned)` walks the conversation newest-first, adding turns while they fit — so turn4 and turn3 make it (50 tokens), and turn1 and turn2 are left out. The result is restored to chronological order for the model. Run it:

```
# $ python3 compact.py --compact
#   kept:    ['sys', 'task', 'turn3', 'turn4']  (100 tokens)
#   dropped: ['turn1', 'turn2']
#   all pinned retained? True
```

run: 2026-08-26 · deterministic · `python3 compact.py --compact`

The context is now exactly 100 tokens, both pinned items survive, and the two oldest turns are gone — the stale ones, which is correct, because they carry the least live information. The agent keeps its identity, its task, and the recent state of the work. This is compaction done right: the constraint (fit the budget) and the invariant (keep the pinned set) both satisfied.

<svg viewBox="0 0 700 200" role="img" aria-label="The six context items as stacked blocks summing to 150, over a budget line at 100. The correct policy keeps sys, task (pinned, highlighted) and turn3, turn4 (recent), dropping turn1 and turn2 which are shown faded and below the budget line.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">correct compaction: keep pinned + recent, drop the oldest turns</text>
    <line x1="40" y1="70" x2="360" y2="70" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="365" y="73" fill="var(--acc-ink)" font-size="8">budget 100</text>
    <rect x="60" y="150" width="120" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="120" y="167" text-anchor="middle" fill="var(--acc-ink)">sys (pinned)</text>
    <rect x="60" y="122" width="120" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="120" y="139" text-anchor="middle" fill="var(--acc-ink)">task (pinned)</text>
    <rect x="60" y="96" width="120" height="24" fill="var(--s1)"></rect><text x="120" y="112" text-anchor="middle" fill="var(--panel)">turn3</text>
    <rect x="60" y="72" width="120" height="24" fill="var(--s1)"></rect><text x="120" y="88" text-anchor="middle" fill="var(--panel)">turn4</text>
    <text x="120" y="60" text-anchor="middle" fill="var(--s1)" font-size="8">= 100, fits</text>
    <rect x="220" y="130" width="120" height="24" fill="var(--muted)" opacity="0.3"></rect><text x="280" y="146" text-anchor="middle" fill="var(--muted)">turn1 dropped</text>
    <rect x="220" y="156" width="120" height="24" fill="var(--muted)" opacity="0.3"></rect><text x="280" y="172" text-anchor="middle" fill="var(--muted)">turn2 dropped</text>
    <text x="220" y="120" fill="var(--muted)" font-size="8">the stale oldest turns</text>
  </g>
</svg>
^ The kept stack — both pinned items plus the two most recent turns — lands right on the budget line. The dropped turns are the oldest, carrying the least live state. Constraint met, invariant held.

### The bug: FIFO evicts the pinned items first

The naive policy treats compaction as pure size reduction: drop the oldest until it fits.

```
# compact.py:65-69 — COMPLETE (the bug: evict oldest regardless of pinned)
def compact_fifo(items, budget):
    """The bug: drop the oldest item until it fits, pinned or not."""
    kept = list(items)
    while total_tokens(kept) > budget and kept:
        kept.pop(0)                        # evict the oldest -- which is a pinned item first
```

`kept.pop(0)` removes the oldest item, and it loops until the total fits. The oldest item is `sys`, the system prompt — gone. Still over budget, so it pops again: `task`, the task — gone. Now it fits. Run it:

```
# $ python3 compact.py --fifo
#   kept:    ['turn1', 'turn2', 'turn3', 'turn4']  (100 tokens, fits budget 100)
#   dropped: ['sys', 'task']
#   all pinned retained? False  <- dropped the system prompt and task!
```

run: 2026-08-26 · deterministic · `python3 compact.py --fifo`

FIFO produced a context that fits the budget exactly — 100 tokens, same as the correct policy — and is catastrophic. It dropped the system prompt and the task, the two things the agent cannot work without, and kept four turns of conversation that now float free of any instructions. The agent's next step will be made with no idea what it is supposed to be doing. And nothing errored; the size check passed. This is the worst kind of bug: it satisfies the obvious test and violates the one that matters.

<svg viewBox="0 0 700 180" role="img" aria-label="FIFO eviction: the oldest items sys and task are popped off the bottom and discarded, while turn1 through turn4 are kept. The result fits the budget but the pinned items are in the discard pile, marked with a warning.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">FIFO: pop the oldest until it fits — the pinned items go first</text>
    <text x="60" y="44" fill="var(--s1)">kept (fits 100)</text>
    <rect x="60" y="52" width="120" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="120" y="67" text-anchor="middle" fill="var(--ink)">turn1</text>
    <rect x="60" y="76" width="120" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="120" y="91" text-anchor="middle" fill="var(--ink)">turn2</text>
    <rect x="60" y="100" width="120" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="120" y="115" text-anchor="middle" fill="var(--ink)">turn3</text>
    <rect x="60" y="124" width="120" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="120" y="139" text-anchor="middle" fill="var(--ink)">turn4</text>
    <text x="400" y="44" fill="var(--s2)">discarded</text>
    <rect x="400" y="52" width="150" height="22" fill="var(--s2)" opacity="0.25" stroke="var(--s2)"></rect><text x="475" y="67" text-anchor="middle" fill="var(--s2)">sys (system prompt)</text>
    <rect x="400" y="76" width="150" height="22" fill="var(--s2)" opacity="0.25" stroke="var(--s2)"></rect><text x="475" y="91" text-anchor="middle" fill="var(--s2)">task (the task)</text>
    <text x="400" y="120" fill="var(--s2)" font-size="8">the agent has forgotten</text><text x="400" y="132" fill="var(--s2)" font-size="8">who it is and its goal</text>
  </g>
</svg>
^ FIFO keeps the four recent turns and discards the two pinned items — the exact inverse of what compaction should protect. The budget is satisfied; the agent is lobotomized.

**Context compaction is a size constraint with a hard invariant: fit the budget while preserving the pinned system prompt and task — plain FIFO fits the budget by evicting the oldest items, which are exactly the pinned ones, so it passes the size check and destroys the agent, and only checking the must-keep set catches it.**

### The self-test

The `--check` mode asserts both policies against both requirements: the correct one fits and keeps all pinned and the recent turn, while FIFO fits but drops a pinned item.

```
# $ python3 compact.py --check
#   correct compaction fits the budget = True (100 <= 100)
#   correct compaction retains every pinned item = True (['sys', 'task'])
#   correct compaction keeps the most recent turn = True (turn4)
#   FIFO also fits the budget = True (100 <= 100)
#   ...but FIFO drops a pinned item = True (missing ['sys', 'task'])
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 compact.py --check`

The decisive pairing is the FIFO check: it fits the budget and yet drops a pinned item, on the same input:

```
# compact.py:130-136 — COMPLETE (FIFO fits the budget but violates the invariant)
    fifo = compact_fifo(items, budget)
    fifo_ids = {it["id"] for it in fifo}
    fifo_fits = total_tokens(fifo) <= budget

    fifo_drops_pinned = not pins.issubset(fifo_ids)
```

`fifo_fits` and `fifo_drops_pinned` must both be true — the proof that a passing size check coexists with a broken must-keep set.

The `good_keeps_pinned` line is the correctness anchor: the compacted context must contain every pinned item, and if the policy ever evicted one that would fail. The pairing of `fifo_fits` and `fifo_drops_pinned` is the lesson made unavoidable — FIFO satisfies the size check and violates the invariant on the same input, so the test proves that fitting the budget is not evidence of a correct compaction. A harness that tested only `fits the budget` would ship FIFO.

### The running tally

| policy | fits budget | pinned retained | outcome |
|---|---|---|---|
| correct (keep pinned + recent) | yes (100) | yes (sys, task) | agent keeps working |
| FIFO (evict oldest) | yes (100) | no (dropped both) | agent lobotomized |

<svg viewBox="0 0 700 150" role="img" aria-label="Two rows, correct and FIFO, scored on two checks. Both have a green 'fits budget' mark. Correct has a green 'pinned retained' mark; FIFO has a red cross on 'pinned retained'. Only the second column separates them.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">two checks: fits budget, and pinned retained</text>
    <text x="250" y="44" text-anchor="middle" fill="var(--ink)">fits budget</text><text x="450" y="44" text-anchor="middle" fill="var(--ink)">pinned retained</text>
    <text x="60" y="76" fill="var(--ink)">correct</text>
    <text x="250" y="76" text-anchor="middle" fill="var(--s1)">✓ 100</text><text x="450" y="76" text-anchor="middle" fill="var(--s1)">✓ sys, task</text>
    <text x="60" y="112" fill="var(--ink)">FIFO</text>
    <text x="250" y="112" text-anchor="middle" fill="var(--s1)">✓ 100</text><text x="450" y="112" text-anchor="middle" fill="var(--s2)">✗ dropped both</text>
    <line x1="350" y1="52" x2="350" y2="124" stroke="var(--grid)"></line>
    <text x="450" y="138" text-anchor="middle" fill="var(--s2)" font-size="8">the only column that separates them</text>
  </g>
</svg>
^ The size column is green for both — it cannot tell the working policy from the broken one. Only the pinned-retained column distinguishes them, which is why it must be checked, not assumed.

Both rows fit the budget — that column does not distinguish them, which is exactly why size cannot be the only check. The distinguishing column is pinned-retained, and it is the whole story: same token count, opposite outcomes, because one policy respects the must-keep set and the other is blind to it. The lesson generalizes past this bug: whenever you evict, dropping, or summarizing under a budget, the constraint is never just "fit" — it is "fit while preserving what must survive," and the second half is the half that a naive implementation forgets.

### What we did not settle

Real compaction is richer than keep-or-drop. The standard move is to summarize the evicted middle rather than discard it, so the agent retains a compressed trace of the old turns instead of a hard gap — which is what this session's own harness does when context grows long. Pinning is often more than two items: tool definitions, retrieved documents the task depends on, and a running scratchpad may all be pinned, and the budget math gets tighter. Eviction can be smarter than oldest-first — dropping low-salience turns before recent-but-trivial ones — at the cost of needing a salience estimate. And summarization itself consumes tokens and can lose the one detail that mattered, so what to summarize versus keep verbatim is a live tradeoff. The invariant here — never evict the pinned set to satisfy the budget — holds under all of it.

## Build

The practice in one paragraph: model the context as pinned items plus evictable turns; when the total exceeds the budget, keep every pinned item and fill the remaining budget with the most recent turns, oldest-first eviction; never let a size-reduction policy touch the pinned set, and test the must-keep invariant separately from the fit, because fitting the budget is necessary and not sufficient. Prefer summarizing the evicted middle to discarding it, and treat tool definitions and task-critical documents as pinned too.

We opened on the over-budget window. The number that separates a working compaction from a broken one is not the token count — both fit — it is whether the pinned set survived:

```
# modules/agent-harness/code/harness-inter-04/ — COMPLETE, run from that directory
$ python3 compact.py --fifo
  kept:    ['turn1', 'turn2', 'turn3', 'turn4']  (100 tokens, fits budget 100)
  all pinned retained? False
```

Now build it yourself. Model a context of pinned and unpinned items over a budget, and compact it. Your number to beat is not the fit; it is **whether every pinned item survives the compaction**, which the correct policy guarantees and FIFO violates. Then implement FIFO and confirm it fits the budget while dropping the system prompt. Bring back both policies' kept sets and their pinned-retained flags. Good luck.

## Definition of done

- [ ] A context modelled as pinned items plus evictable turns, with token costs and a budget
- [ ] A compaction that keeps all pinned items and fills the rest with the most recent turns
- [ ] The result verified to fit the budget
- [ ] The result verified to retain every pinned item, checked separately from the fit
- [ ] A FIFO policy implemented, shown to fit the budget while dropping a pinned item
- [ ] `python3 compact.py --check` printing SELF-TEST PASS: good-fits, good-keeps-pinned, keeps-recent, fifo-fits, fifo-drops-pinned
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What two things are pinned in an agent's context, and what happens to the agent if they are evicted?
2. Why is "fits the budget" a necessary but not sufficient check for a correct compaction?
3. FIFO evicts the oldest item first. Why does that drop the system prompt and task, and why is that catastrophic rather than merely suboptimal?
4. The correct policy fills the remaining budget with the most recent turns rather than the oldest. Why recent?
5. Your own context was compacted two ways. Did each fit the budget, and did each retain the pinned set?

## External resources

- Anthropic, context-management and long-conversation guidance for agents — my summary: how production harnesses summarize and evict context under a budget while preserving system and task instructions; read it for the summarization-over-discard pattern this module's hard eviction is the floor of.
- General agent-framework docs on memory and context windows (buffer vs summary memory) — my summary: the standard buffer-with-summary approaches to staying under the token limit; read it for the richer eviction and summarization policies beyond keep-pinned-drop-oldest.
- This hub, *harness-inter-01* — modules/agent-harness/harness-inter-01.md — my summary: the agent loop these context items accumulate within; read it for where compaction fits in the loop — between turns, when the assembled context would overflow.
