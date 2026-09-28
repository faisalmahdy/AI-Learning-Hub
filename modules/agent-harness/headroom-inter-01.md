---
id: headroom-inter-01
title: Reserve a completion budget — the input and the output share the context window, so packing the input truncates the reply
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A context window is a hard limit on the whole request: every token sent in plus every token generated out must fit inside it. The easy mistake is to treat the window as a bound on the input alone and fill the conversation history until the input reaches the window — but the output has not been generated yet, and it needs tokens too. An input that fills the window leaves zero for the response, so depending on the API the request is rejected because input plus the reserved output exceeds the limit, or the model is handed only the few leftover tokens and its answer is cut off mid-sentence; either way the agent stops being able to act, and it happens precisely as the conversation gets long. The fix is to reserve the output budget before packing the input: decide a max_tokens the response may need, cap the input at window minus that, and evict or compact history to fit, keeping the most recent turns. On the fixture the window is 1000, the system prompt 100, tools 150, the reserved completion budget 300, and history four turns of 200: packing everything makes the input 1050 — already over the window, with −50 room for output — while reserving 300 caps the input at 700, trims history to the two most recent turns, gives an input of 650, and leaves 350 for the response (input plus reserved 950 ≤ 1000). The rule: the context window is shared between what you send and what you get back, so the input budget is the window minus the space you have set aside for the answer, not the whole window.
eli5: Think of the context window as a suitcase of a fixed size, and you have to fit both the stuff you pack AND the souvenirs you'll buy on the trip. If you fill the suitcase to the brim before you leave, there's nowhere to put the souvenirs — you either can't close it, or you have to jam them in and they get crushed. The souvenirs here are the model's reply: it needs room too. So before packing, set aside a corner for what's coming back, and only fill the rest with your history — dropping the oldest, least useful items first. Then the reply always has somewhere to go.
---

## Why this module

Long agent conversations fail in a way short ones never reveal, and the failure looks baffling: the model, which was answering fine, suddenly returns a truncated reply or the request errors outright — with no change to the code, only to the length of the history. The cause is a budgeting error that only bites once the history has grown large enough.

The error is treating the context window as the budget for the input. It is not; it is the budget for the input and the output together. A harness that fills history up to the window is spending the response's tokens on history without realizing there is a response to pay for.

**The context window is shared between what you send and what the model generates, so the input can never be allowed to fill it.**

## Concepts

A model request has a single token limit, the context window, and it covers the entire round trip: the system prompt, the tool definitions, the conversation history, and the tokens the model will generate in reply. All of it must fit under the one number.

The intuitive picture — window bounds the input — is wrong because the output is invisible at packing time. It has not been generated yet, so it is tempting to pack the input against the window and let the model "use whatever is left." But if the input already equals the window, what is left is nothing. The model needs tokens to answer, and there are none.

What happens next depends on the API, and both outcomes are bad. Some APIs add the requested output allowance (max_tokens) to the input and reject the request when the sum exceeds the window — the agent simply stops, erroring on every turn once history is large. Others let the request through and cap the generation at the few tokens remaining, so the reply is truncated mid-sentence — a tool call that never closes its JSON, an answer that stops halfway. Either way the agent is broken exactly when the conversation has become long and valuable.

The fix is to budget the output first. Choose max_tokens — how long the response might need to be — and treat the input budget as window minus max_tokens. Pack the system prompt and tools, then fit history under what remains, evicting or compacting the oldest turns because recent context matters most. Now the input plus the reserved output always fit, and the model always has room to reply, no matter how long the conversation runs.

The cost is that you carry less history than the window could nominally hold — you have set aside space you are not filling with context. That is the correct trade: unused-looking headroom is not waste, it is the response's seat, and a conversation that keeps every old turn but cannot answer is worse than one that drops old turns and can.

**Budget the output before the input: the input's real limit is the window minus the reserved completion, and history fills only what is left.**

<svg role="img" aria-label="Two mental models of the window. Wrong: the whole window is the input budget, output is an afterthought with no space. Right: the window is split into an input budget and a reserved output budget." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">what the window actually budgets</text>
<text x="20" y="44" fill="var(--s1)" font-size="10">wrong:</text>
<rect x="70" y="32" width="210" height="18" fill="var(--s2)"></rect>
<text x="110" y="45" fill="var(--panel)" font-size="9">input fills the whole window</text>
<text x="20" y="72" fill="var(--s1)" font-size="9">&#8594; output has nowhere to go</text>
<text x="20" y="104" fill="var(--s2)" font-size="10">right:</text>
<rect x="70" y="92" width="150" height="18" fill="var(--s2)"></rect>
<text x="90" y="105" fill="var(--panel)" font-size="9">input budget</text>
<rect x="220" y="92" width="60" height="18" fill="var(--s1)"></rect>
<text x="224" y="105" fill="var(--panel)" font-size="9">output</text>
<text x="20" y="132" fill="var(--muted)" font-size="9">input limit = window &#8722; reserved output</text>
</svg>
^ The window is one budget shared by input and output; reserving the output's share first turns "fill to the window" into "fill to the window minus the reply."

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/agent-harness/code/headroom-inter-01/headroom.py

The fixture is a 1000-token window with a growing history.

```json filename=modules/agent-harness/code/headroom-inter-01/headroom.json:3-7 COMPLETE
  "window": 1000,
  "system": 100,
  "tools": 150,
  "max_tokens": 300,
  "history": [200, 200, 200, 200]
```

The naive input packs everything, ignoring the output.

```python filename=modules/agent-harness/code/headroom-inter-01/headroom.py:30-32 COMPLETE
def naive_input(d):
    """Pack everything: system + tools + all of history, ignoring the output's need for tokens."""
    return d["system"] + d["tools"] + sum(d["history"])
```

```python filename=modules/agent-harness/code/headroom-inter-01/headroom.py:51-53 COMPLETE
def output_room(d, input_tokens):
    """Tokens left in the window for the model's response after the input."""
    return d["window"] - input_tokens
```

```text filename=headroom.py --naive
NAIVE — fill the input to the window 1000
----------------------------------------------------------------
  system 100 + tools 150 + history [200, 200, 200, 200] = input 1050
  room left for output = -50   (need 300)
----------------------------------------------------------------
  the input alone meets or exceeds the window, so the response has no room
```

The input is 1050 — already 50 over the 1000-token window before the model generates a single token. Room for output is −50: there is not only no space for the 300-token reply, there is no space at all. The request is rejected, and it was fine two turns ago when history was smaller.

<svg role="img" aria-label="A window bar of 1000 tokens. The naive input stacks system 100, tools 150, and four history blocks of 200, totaling 1050, which overflows past the end of the window bar, leaving no room for output." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">naive input overflows the window (1000)</text>
<line x1="30" y1="40" x2="290" y2="40" stroke="var(--line)"></line>
<line x1="290" y1="34" x2="290" y2="120" stroke="var(--ink)"></line>
<text x="270" y="132" fill="var(--muted)" font-size="9">window end</text>
<rect x="30" y="60" width="26" height="20" fill="var(--muted)"></rect>
<rect x="56" y="60" width="39" height="20" fill="var(--line)"></rect>
<rect x="95" y="60" width="52" height="20" fill="var(--s2)"></rect>
<rect x="147" y="60" width="52" height="20" fill="var(--s2)"></rect>
<rect x="199" y="60" width="52" height="20" fill="var(--s2)"></rect>
<rect x="251" y="60" width="52" height="20" fill="var(--s1)"></rect>
<text x="256" y="98" fill="var(--s1)" font-size="9">spills past</text>
<text x="30" y="108" fill="var(--muted)" font-size="9">sys+tools+4 history = 1050 &#8594; no room for output</text>
</svg>
^ The stacked input runs past the window's end, so the response has negative room — the request cannot even be sent, let alone answered.

## Build

The reserved plan caps the input at the window minus the completion budget and trims history to fit.

```python filename=modules/agent-harness/code/headroom-inter-01/headroom.py:35-43 COMPLETE
def reserved_history(d):
    """Keep the most recent history turns that fit under window - max_tokens (after system + tools)."""
    budget = d["window"] - d["max_tokens"] - d["system"] - d["tools"]
    kept, total = [], 0
    for turn in reversed(d["history"]):
        if total + turn <= budget:
            kept.insert(0, turn)
            total += turn
    return kept
```

```text filename=headroom.py --reserved
RESERVED — cap the input at window - max_tokens = 700
----------------------------------------------------------------
  kept history (most recent): [200, 200]   (dropped 2 of 4 turns)
  system 100 + tools 150 + history 400 = input 650
  room left for output = 350   (need 300)   input + reserved = 950 <= 1000
----------------------------------------------------------------
  the reserved output budget is protected, and the newest turns are kept
```

Reserving 300 for the output caps the input at 700. History is trimmed from the back — the two most recent turns fit (400 tokens), the two oldest are dropped — so the input is 650, leaving 350 for the reply and keeping the whole request (650 + 300 = 950) inside the 1000 window. The agent can answer, and it kept the turns most likely to matter.

<svg role="img" aria-label="A window bar of 1000. The reserved plan places system 100, tools 150, two history blocks of 200 (input 650), and a reserved output block of 300, all fitting within the window with 50 to spare." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">reserved plan fits input + output in the window</text>
<line x1="30" y1="40" x2="290" y2="40" stroke="var(--line)"></line>
<line x1="290" y1="34" x2="290" y2="120" stroke="var(--ink)"></line>
<rect x="30" y="60" width="26" height="20" fill="var(--muted)"></rect>
<rect x="56" y="60" width="39" height="20" fill="var(--line)"></rect>
<rect x="95" y="60" width="52" height="20" fill="var(--s2)"></rect>
<rect x="147" y="60" width="52" height="20" fill="var(--s2)"></rect>
<rect x="199" y="60" width="78" height="20" fill="var(--s1)"></rect>
<text x="205" y="74" fill="var(--panel)" font-size="9">output 300</text>
<text x="95" y="98" fill="var(--s2)" font-size="9">2 recent turns</text>
<text x="30" y="112" fill="var(--muted)" font-size="9">input 650 + reserved 300 = 950 &#8804; 1000 (50 spare)</text>
</svg>
^ The reserved output block is placed first, so the input is packed only into what remains — the whole request fits, and the newest history is kept.

The self-test contrasts the two budgets and confirms the reserved plan keeps recent turns.

```python filename=modules/agent-harness/code/headroom-inter-01/headroom.py:86-91 COMPLETE
    naive_no_room = output_room(d, n_in) < mt
    print("  naive leaves less than the needed output budget = %s (room %d < %d)" % (naive_no_room, output_room(d, n_in), mt))

    r_in = reserved_input(d)
    reserved_reserves = output_room(d, r_in) >= mt
    print("  reserved keeps at least max_tokens for the output = %s (room %d >= %d)" % (reserved_reserves, output_room(d, r_in), mt))
```

```text filename=headroom.py --check
SELF-TEST — the naive input leaves less than the reserved output while the reserved plan keeps at least max_tokens for output, stays within the window, and keeps the most recent turns
----------------------------------------------------------------------------------------------------------------
  naive leaves less than the needed output budget = True (room -50 < 300)
  reserved keeps at least max_tokens for the output = True (room 350 >= 300)
  reserved input plus reserved output fits the window = True (950 <= 1000)
  reserved keeps the most recent turns (a suffix of history) = True ([200, 200])
  reserved dropped at least one old turn to make room = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_no_room=True  reserved_reserves=True  reserved_within_window=True  reserved_keeps_recent=True  reserved_dropped=True
```

**reserved_within_window is the invariant to hold every turn: input + max_tokens ≤ window, checked before the call, so the response's seat is guaranteed rather than hoped for.**

## Definition of done

You can state what the context window actually bounds — the input and the output together — and why treating it as the input's budget truncates or rejects the response.

You can compute the correct input budget (window minus the reserved completion) and explain why history must be trimmed to fit it, keeping recent turns.

You can describe both failure modes of the naive approach — a rejected request when the API adds max_tokens, and a truncated reply when it does not — and why both appear only once history has grown.

You can name the trade the reservation makes — carrying less history than the window could nominally hold — and argue why that headroom is the response's seat, not waste.

## Boss fight

Your agent works for the first dozen turns of a session and then starts returning replies that cut off mid-sentence, and occasionally the API rejects the request entirely with a context-length error. The code has not changed within the session.

First: explain why the failure appears only after many turns and not at the start, and why the two symptoms — truncated reply versus outright rejection — are the same root cause showing up under two different API behaviors.

Then: you add a reserved completion budget. Picking max_tokens is a real choice — set it too high and you can carry almost no history, too low and complex answers truncate. Explain how you would size it, and why a fixed max_tokens interacts badly with a task whose responses vary wildly in length (a one-word answer versus a long tool-call argument).

Finally: trimming old turns to fit is lossy — the dropped turns may hold facts the agent still needs. Contrast three ways to make room within the reserved input budget — dropping oldest turns, summarizing old turns into fewer tokens, and moving old turns to an external store the agent can retrieve from — and say which preserves the most usable context per token spent, and its cost.

## External resources

The Anthropic and OpenAI API references define the context window as covering input plus output and document max_tokens as the reserved generation budget — reading them makes explicit that the input limit is the window minus max_tokens, which is the whole of this module.

Guidance on long-conversation agents (context management, memory, and summarization strategies) covers the follow-on question the boss fight raises: once you must trim to fit the reserved budget, how to lose the least useful context, via eviction, summarization, or retrieval.
