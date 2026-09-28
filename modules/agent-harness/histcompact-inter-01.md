---
id: histcompact-inter-01
title: Pin the system prompt and task when compacting history — naive FIFO drops the oldest, which is exactly the goal
topic: agent-harness
level: intermediate
status: ready
time: 14 min
summary: An agent's conversation grows every turn — system prompt, user task, then a lengthening trail of thoughts and tool observations — and the model's context window is fixed, so eventually the transcript no longer fits and the harness must trim it before the next turn. The obvious trim is FIFO, drop the oldest until it fits, and it is exactly wrong, because the oldest messages are the system prompt and the original task: the standing instructions that say what the agent is and the goal that says what it is doing. Evict those and the agent is a capable model with no instructions and no objective, working only from recent tool chatter, so it drifts, repeats work, or invents a new goal — and the failure is silent, because the transcript still fits and the model still responds fluently, just to the wrong (missing) prompt. The fix is to compact by priority, not age: pin the system prompt and task, always keep them, and spend the remaining budget on the most recent turns (summarizing the expendable middle), so the kept context is the goal plus the latest state. On a fixture of 870 tokens against a 500-token budget, FIFO drops the system prompt (200) and task (150) and keeps the four most recent turns (420 tokens) with no goal, while pinned compaction keeps system + task (350) plus the single most recent turn (470 tokens) and stays on task — both within budget.
eli5: Imagine a long meeting where you can only keep one page of notes. If you keep the LAST page and throw away the first, you lose the part that said what the meeting was even about — so your notes are recent but pointless. The smarter move is to always keep the line stating the goal, then fill the rest of the page with the most recent developments, and boil the middle down to a sentence. An AI agent trimming its conversation has the same choice: throw away the oldest messages (which include its instructions and its task) and it forgets why it's working, or pin the goal and keep the latest context and stay on track.
---

## Why this module

An agent runs long enough that its own transcript outgrows the context window, and the harness has to throw some of it away. The natural instinct — drop the oldest — targets precisely the two messages that must never leave: the instructions and the goal. The result is an agent that keeps talking, keeps calling tools, and has quietly forgotten what it was asked to do.

An agent's conversation grows every turn: the system prompt, the user's task, then a lengthening trail of assistant thoughts and tool observations. The model's context window is fixed, so sooner or later the transcript no longer fits and the harness must trim it before the next turn. The obvious trim is FIFO — drop the oldest messages until it fits — and it is exactly wrong, because the oldest messages are the system prompt and the original task: the standing instructions that tell the agent what it is and the goal that tells it what it is doing. Evict those and the agent, on its very next turn, is a capable model with no instructions and no objective, working only from the recent tool chatter, so it drifts, repeats work, or invents a new goal. The bug is silent: the transcript still fits, the model still responds fluently, it just responds to the wrong (missing) prompt.

The fix is to compact with priorities, not by age. Mark the messages that must survive — the system prompt and the task — as pinned, always keep them, and spend the remaining budget on the most recent turns, because recency is what the agent needs to continue, while the middle of the transcript is the most expendable (and, in a real system, is where you put a short summary of what happened rather than dropping it outright). So the kept context is the goal (pinned) plus the latest state (recent), with the stale middle compacted away — on-task and current, within the same budget FIFO used to lose the task. This module trims a transcript both ways.

**When an agent transcript exceeds the context budget, naive FIFO drops the oldest messages — the system prompt and the task — so the agent forgets its instructions and goal; pin those and fill the rest of the budget with the most recent turns (summarizing the middle) so the agent stays on-task and current.**

## Concepts

**FIFO compaction** drops from the front until the transcript fits, treating every message the same by age — so the system prompt and task, being oldest, go first.

```python filename=modules/agent-harness/code/histcompact-inter-01/histcompact.py:47-52 COMPLETE
def fifo_compact(messages, budget):
    """Drop the oldest messages until the transcript fits -- ignores what each message is."""
    kept = list(messages)
    while total(kept) > budget:
        kept.pop(0)
    return kept
```

**Pinned compaction** keeps the pinned messages unconditionally, then fills the remaining budget from the most recent turns backward — so the goal always survives and the newest context is preferred over the stale middle.

```python filename=modules/agent-harness/code/histcompact-inter-01/histcompact.py:55-63 COMPLETE
def pinned_compact(messages, budget):
    """Keep pinned messages always, then fill the remaining budget with the most recent unpinned turns."""
    kept = [m for m in messages if m["pin"]]
    used = total(kept)
    for m in reversed([m for m in messages if not m["pin"]]):
        if used + m["tokens"] <= budget:
            kept.append(m)
            used += m["tokens"]
    return [m for m in messages if m in kept]  # restore original order
```

<svg role="img" aria-label="A transcript stack exceeding the budget line: FIFO cuts from the bottom (oldest, the system prompt and task), pinned compaction cuts from the middle and keeps the pinned system prompt and task plus the newest turn" viewBox="0 0 300 122" width="300" height="122">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the oldest messages are the system prompt and the task</text>
  <text x="20" y="34" fill="var(--muted)" font-size="7">transcript (newest on top)</text>
  <g transform="translate(20,40)" font-size="6" fill="var(--panel)">
  <rect x="0" y="0" width="80" height="11" fill="var(--s1)"/><text x="4" y="8">t5 (recent)</text>
  <rect x="0" y="12" width="80" height="11" fill="var(--muted)"/><text x="4" y="20">t4</text>
  <rect x="0" y="24" width="80" height="11" fill="var(--muted)"/><text x="4" y="32">t3 · t2 · t1</text>
  <rect x="0" y="42" width="80" height="11" fill="var(--s2)"/><text x="4" y="50">task (pinned)</text>
  <rect x="0" y="54" width="80" height="11" fill="var(--s2)"/><text x="4" y="62">system (pinned)</text>
  </g>
  <line x1="10" y1="76" x2="110" y2="76" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="112" y="79" fill="var(--muted)" font-size="6">budget line</text>
  <text x="150" y="52" fill="var(--muted)" font-size="7">FIFO cuts the bottom</text>
  <text x="150" y="64" fill="var(--muted)" font-size="7">→ loses system + task</text>
  <text x="150" y="90" fill="var(--muted)" font-size="7">pinned cuts the middle</text>
  <text x="150" y="102" fill="var(--muted)" font-size="7">→ keeps goal + newest</text>
</svg>
^ The transcript overflows the budget line; FIFO removes from the bottom where the pinned system prompt and task sit, while pinned compaction removes the expendable middle and keeps the pinned goal plus the most recent turn.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/histcompact-inter-01/histcompact.py

The fixture is a seven-message transcript (870 tokens) with the system prompt and task pinned, against a 500-token budget.

```json filename=modules/agent-harness/code/histcompact-inter-01/histcompact.json:3-12 COMPLETE
  "budget": 500,
  "messages": [
    {"id": "system", "role": "system", "tokens": 200, "pin": true},
    {"id": "task", "role": "user", "tokens": 150, "pin": true},
    {"id": "t1", "role": "assistant", "tokens": 100, "pin": false},
    {"id": "t2", "role": "tool", "tokens": 100, "pin": false},
    {"id": "t3", "role": "assistant", "tokens": 100, "pin": false},
    {"id": "t4", "role": "tool", "tokens": 100, "pin": false},
    {"id": "t5", "role": "assistant", "tokens": 120, "pin": false}
  ]
```

Run `--compact` to trim it both ways.

```text filename=--compact
COMPACT — trim 870 tokens to a 500-token budget
--------------------------------------------------------------
  FIFO (drop oldest) keeps  : ['t2', 't3', 't4', 't5']  = 420 tokens
  pinned compaction keeps   : ['system', 'task', 't5']  = 470 tokens
```

Both results fit the 500-token budget, but they kept completely different things. FIFO dropped from the front — system (200), then task (150), then t1 (100) — until the remaining four turns fit at 420 tokens, so the surviving context is `[t2, t3, t4, t5]`: recent tool chatter with no system prompt and no task. Pinned compaction kept the two pinned messages (system + task = 350) and then added turns from the newest backward, fitting only t5 (120) before the next would overflow, for `[system, task, t5]` at 470 tokens. The difference is not the budget — both used roughly the same number of tokens — it is *which* tokens. FIFO spent its whole budget on the four most recent turns and none on the goal; pinned spent 350 of its 500 on the goal and the rest on the single latest turn. On the next model call, one of these agents knows what it is trying to do and one does not, and nothing in the token count would tell you which.

<svg role="img" aria-label="Two token budgets of the same size: FIFO spends all its tokens on recent turns and zero on the goal, pinned spends 350 on the goal and 120 on the latest turn" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same ~budget, spent differently: goal vs recent turns</text>
  <text x="10" y="36" fill="var(--muted)" font-size="7">FIFO</text>
  <g transform="translate(60,26)">
  <rect x="0" y="0" width="200" height="14" fill="var(--muted)"/><text x="70" y="10" fill="var(--panel)" font-size="6">420 tokens of recent turns, 0 on goal</text>
  </g>
  <text x="10" y="66" fill="var(--muted)" font-size="7">pinned</text>
  <g transform="translate(60,56)">
  <rect x="0" y="0" width="140" height="14" fill="var(--s2)"/><text x="8" y="10" fill="var(--panel)" font-size="6">350 goal (system+task)</text>
  <rect x="142" y="0" width="48" height="14" fill="var(--s1)"/><text x="146" y="10" fill="var(--panel)" font-size="6">120 latest</text>
  </g>
  <text x="10" y="92" fill="var(--muted)" font-size="7">FIFO buys four recent turns and no goal; pinned buys the goal and the newest turn</text>
</svg>
^ Both strategies spend a similar token budget, but FIFO buys only recent turns (nothing on the goal) while pinned buys the pinned goal first and then the single most recent turn — the allocation, not the amount, decides whether the agent keeps its instructions.

## Build

What the agent actually retains is the real measure. Run `--recall`.

```text filename=--recall
RECALL — what the agent still knows on the next turn
----------------------------------------------------------
  FIFO     has system prompt = False  has task = False  has latest turn = True
  pinned   has system prompt = True   has task = True   has latest turn = True
```

FIFO enters the next turn with no system prompt and no task — it has the latest turn, so it will fluently continue *something*, but it has lost the instructions that constrain its behavior and the objective that directs it. In practice this is where agents go off the rails after a long run: they start ignoring output-format rules from the system prompt, or they re-do a subtask because the task that said it was already planned is gone, or they latch onto whatever the last tool returned as if it were the goal. Pinned compaction enters the next turn with the system prompt, the task, and the latest turn — everything it needs to make a correct next step. Notice that pinned keeps *fewer* messages than FIFO (three versus four) yet retains far more of what matters: the value of a message is not its recency, it is its role, and compaction has to be role-aware. Whether a message survived is just membership in the kept set.

```python filename=modules/agent-harness/code/histcompact-inter-01/histcompact.py:115-119 COMPLETE
    pinned_keeps_recent = latest in pids
    print("  pinned compaction keeps the most recent turn (%s) = %s" % (latest, pinned_keeps_recent))

    both_under_budget = total(f) <= budget and total(p) <= budget
    print("  both strategies fit the budget = %s (FIFO %d, pinned %d, budget %d)" % (both_under_budget, total(f), total(p), budget))
```

<svg role="img" aria-label="A recall table: FIFO has lost the system prompt and task but kept the latest turn, pinned has kept the system prompt, task, and latest turn" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">what survives compaction: goal vs recency</text>
  <text x="70" y="30" fill="var(--muted)" font-size="7">system</text><text x="130" y="30" fill="var(--muted)" font-size="7">task</text><text x="185" y="30" fill="var(--muted)" font-size="7">latest</text>
  <text x="10" y="50" fill="var(--muted)" font-size="7">FIFO</text>
  <text x="78" y="50" fill="var(--s2)" font-size="9">✗</text><text x="135" y="50" fill="var(--s2)" font-size="9">✗</text><text x="195" y="50" fill="var(--s1)" font-size="9">✓</text>
  <text x="10" y="70" fill="var(--muted)" font-size="7">pinned</text>
  <text x="78" y="70" fill="var(--s1)" font-size="9">✓</text><text x="135" y="70" fill="var(--s1)" font-size="9">✓</text><text x="195" y="70" fill="var(--s1)" font-size="9">✓</text>
  <text x="10" y="90" fill="var(--muted)" font-size="7">FIFO kept more messages but lost the two that define the job</text>
</svg>
^ FIFO retains the latest turn but has dropped both the system prompt and the task, so the agent forgets its rules and goal; pinned retains all three, keeping the goal and the current state.

## Definition of done

The self-test pins FIFO's loss of the pinned messages and pinned compaction's retention of the goal.

```python filename=modules/agent-harness/code/histcompact-inter-01/histcompact.py:106-113 COMPLETE
    fifo_drops_system = "system" not in fids
    print("  FIFO drops the system prompt = %s (kept %s)" % (fifo_drops_system, fids))

    fifo_drops_task = "task" not in fids
    print("  FIFO drops the original task = %s" % fifo_drops_task)

    pinned_keeps_goal = "system" in pids and "task" in pids
    print("  pinned compaction keeps system + task = %s (kept %s)" % (pinned_keeps_goal, pids))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — FIFO drops the pinned system and task; pinned keeps both plus a recent turn; both stay within budget
----------------------------------------------------------------------------------------------------------------------
  FIFO drops the system prompt = True (kept ['t2', 't3', 't4', 't5'])
  FIFO drops the original task = True
  pinned compaction keeps system + task = True (kept ['system', 'task', 't5'])
  pinned compaction keeps the most recent turn (t5) = True
  both strategies fit the budget = True (FIFO 420, pinned 470, budget 500)
```

**Done means the compaction failure and fix are proven on real token counts: FIFO drops the pinned system prompt and task (keeping only recent turns) while pinned compaction keeps system + task plus the most recent turn — both within the 500-token budget — so history must be compacted by role priority, not by age, or the agent silently loses its instructions and goal.**

## Boss fight

Predict two ways real compaction is more than "pin the system prompt," because the expendable middle is not actually expendable and pinning has its own limits.

The first trap is that dropping the middle outright loses real progress, so production compaction *summarizes* rather than deletes. The middle turns hold what the agent has already learned and done — files it read, decisions it made, dead ends it should not revisit — and if you simply delete them (as this module does, for clarity) the agent keeps its goal but loses its progress, so it may redo completed work or repeat a failed approach. The real technique is to replace the dropped span with a compact summary ("explored the auth module, found the bug in login.py, tried fix A which failed the test") that costs a fraction of the tokens but preserves the state, and to keep durable facts in an external memory or scratchpad the agent can re-read rather than relying on the transcript at all. So the budget is spent three ways, not two: pinned goal, a running summary of the compacted middle, and the most recent verbatim turns — and getting the summary right (lossy in the right places) is the hard part, because a summary that drops the one fact the agent needs is the same failure in a subtler form.

The second trap is that pinning is a fixed decision made before you know what will matter, and it interacts with tool-call structure and with cost. If the system prompt itself is enormous (many tool definitions, long instructions), pinning all of it can leave almost no room for recent context, so even the pin set needs a budget — trimming rarely-used tool definitions, or moving reference material out of the always-present prompt. Compaction also must not break the conversation's structure: many model APIs require a tool call and its result to stay together, or require the sequence to start after the system message in a valid role order, so a naive drop that removes a tool call but keeps its orphaned result (or vice versa) produces an invalid request, not just a lossy one. And there is a cost dimension: with prompt caching, the stable prefix (system prompt + early turns) is cached and cheap to resend, so aggressively rewriting the middle every turn can *invalidate the cache* and cost more than keeping a longer prefix — meaning the compaction strategy trades off token budget, information retention, structural validity, and cache economics all at once. The rule "pin the goal, summarize the middle, keep the recent" is the skeleton; a real implementation also budgets the pin set, preserves tool-call/result pairing, and is cache-aware.

**Production history compaction summarizes the dropped middle (and offloads durable facts to external memory) rather than deleting it, or the agent keeps its goal but loses its progress; and pinning is not free — the pin set itself needs a budget, compaction must preserve tool-call/result pairing and valid role order, and it should stay cache-aware — so the real strategy budgets goal, summary, and recent turns together rather than trimming by age or by a naive pin.**

## External resources

Agent-framework documentation on context/memory management and conversation summarization — how transcripts are compacted, the summarize-the-middle pattern, and external memory or scratchpad stores for durable facts.

Model-provider guidance on context windows, prompt caching, and message/tool-call structure — why compaction must preserve tool-call/result pairing and valid role order, and how rewriting the prefix affects cache hits and cost.

The companion observation-truncation and per-tool-budget modules in this topic — all three are about spending a scarce resource deliberately (one tool result, tool calls, and here the whole conversation's token budget) by priority rather than by a naive default.
