---
id: harness-inter-09
title: Cap a tool result with head and tail — appending it whole overflows the window, head-only cuts off the answer
topic: agent-harness
level: intermediate
status: ready
time: 22 min
summary: A tool can return anything, and one big result appended whole blows the context window and pushes other results off the end. Truncating to a budget is required — but head-only truncation drops the last line, which is where tools put the result or error. Head+tail truncation fits the same budget and keeps both ends.
eli5: If a tool hands you a hundred pages, you can't paste them all in — there's no room. So you keep some. If you keep only the first pages you miss the ending, and the ending is usually the answer. So you keep the first few pages AND the last few, with a note saying what you skipped.
---

## Why this module

An agent does not control how much a tool hands back, and if the harness appends whatever it gets, one oversized result can wreck the whole turn.

A tool call can return a five-line status or a five-thousand-line log dump — the same interface, wildly different sizes, and the model has no say in which. The context window, meanwhile, is fixed. So when a tool returns something huge and the harness appends it verbatim, that one result eats the budget: it shoves earlier turns out of view, or it crowds out the *other* tool results from the same turn, or it simply overflows and the model errors or silently drops the tail. A single unbounded observation is enough to break an otherwise well-built agent loop.

The obvious fix — cap each tool result at some number of lines or tokens before appending — is necessary but half-thought-through in its usual form. People cap by keeping the first N lines and dropping the rest. That fits the budget, and it throws away exactly the part that matters. Tools put their conclusion last: the final result, the exception and its message, the summary row after the table. Head-only truncation lovingly preserves the boilerplate preamble and discards the one line the agent called the tool to get.

The fix that actually works is head+tail: spend half the budget on the beginning and half on the end, with a marker for what was cut. It costs the same as head-only and preserves both the context that opens the output and the answer that closes it. We will pack three tool results into a window three ways — append them whole and overflow, keep heads only and lose every answer, keep head and tail and fit while keeping all three — and count what survives.

<svg role="img" aria-label="Three tool results packed into a fixed window: appending whole overflows the window boundary, head-only fits, head-plus-tail fits" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <line x1="330" y1="20" x2="330" y2="185" stroke="var(--ink)" stroke-dasharray="4 3"/>
  <text x="336" y="32" font-family="var(--mono)" font-size="9" fill="var(--ink)">window</text>
  <text x="16" y="52" font-family="var(--mono)" font-size="10" fill="var(--ink)">append whole</text>
  <rect x="120" y="40" width="100" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><rect x="220" y="40" width="120" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><rect x="340" y="40" width="80" height="16" fill="var(--s2)" stroke="var(--line)"/>
  <text x="352" y="70" font-family="var(--mono)" font-size="9" fill="var(--s2)">overflow — toolC dropped</text>
  <text x="16" y="102" font-family="var(--mono)" font-size="10" fill="var(--ink)">head only</text>
  <rect x="120" y="90" width="60" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><rect x="182" y="90" width="60" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><rect x="244" y="90" width="60" height="16" fill="var(--acc-soft)" stroke="var(--line)"/>
  <text x="120" y="122" font-family="var(--mono)" font-size="9" fill="var(--muted)">fits — but every tail (answer) cut</text>
  <text x="16" y="152" font-family="var(--mono)" font-size="10" fill="var(--ink)">head + tail</text>
  <rect x="120" y="140" width="30" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><rect x="150" y="140" width="40" height="16" fill="var(--acc-line)" stroke="var(--line)"/><rect x="192" y="140" width="30" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><rect x="222" y="140" width="40" height="16" fill="var(--acc-line)" stroke="var(--line)"/><rect x="264" y="140" width="30" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><rect x="294" y="140" width="30" height="16" fill="var(--acc-line)" stroke="var(--line)"/>
  <text x="120" y="172" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">fits — darker = kept tail (answer)</text>
</svg>
^ Append-whole spills past the window and loses a result; head-only fits but all three tails are cut; head+tail fits and the darker tail segments — the answers — survive.

**A tool result is unbounded input to a bounded window; it must be capped before it is appended, and a cap that keeps only the head throws away the tail where tools put the answer.**

## Concepts

The constraint is that the context window is a fixed budget shared by everything — the system prompt, the conversation, every prior tool result, and this one. A tool result is the one input to that budget whose size you do not control at author time; it is whatever the tool decided to emit. So the harness has to impose a per-result cap: no single observation may consume more than its share, or it starves everything else.

Given that you must drop lines, the question is which ones. This is an information-placement question, and the answer comes from how tools actually write output. The structure is almost always preamble-then-conclusion: setup, progress, intermediate detail, and then — at the very end — the thing you wanted. A compiler prints warnings then the final error. A test run prints each case then the summary. A query prints rows then the count. An exception prints the stack then, on the last line, the message. The signal density is highest at the tail. Head-only truncation cuts against the grain of that structure, keeping the low-signal opening and discarding the high-signal close.

Head+tail truncation matches the structure. It keeps the opening, which carries what the tool was doing and what inputs it saw, and the closing, which carries the result. In between it leaves a marker — "[... 6 lines truncated ...]" — so the model knows content was removed and roughly how much, rather than being handed a seamless lie. The marker is not decoration; a model that cannot tell truncation happened may reason as though it saw the whole output.

The cap is a budget split, and the split is a judgment. Even head and tail is the default and is right when you do not know where the answer sits. If you know the tool always concludes on the last line, weight toward the tail; if it front-loads a status code, weight toward the head. What you almost never want is all of the budget on one end, because that guarantees you lose the other end entirely — and for most tools the end you lose that way is the one with the answer.

**Tool output is preamble-then-conclusion, so the signal is densest at the tail; a cap must preserve both ends, because dropping either loses information the other cannot supply.**

## Worked example

The fixture is three tool results that must share one window, with the answer placed where tools actually put it — last.

```json filename=modules/agent-harness/code/harness-inter-09/results.json:7-9 COMPLETE
 "window_lines": 21,
 "per_result_cap": 6,
 "results": [
```

A 21-line window, a 6-line cap per result. Three results of 10, 12, and 8 lines — thirty lines fighting for twenty-one. Each result's salient line is its last.

```text filename=modules/agent-harness/code/harness-inter-09/truncate.py --results
RESULTS — three tool outputs; the salient line is the last of each
------------------------------------------------------
  toolA  10 lines, ends: toolA RESULT: ok=42
  toolB  12 lines, ends: toolB ERROR: OOM at step 900
  toolC   8 lines, ends: toolC RESULT: done
------------------------------------------------------
  window=21 lines, per-result cap=6; the three total 30 lines.
```

The three answers are the last lines: `ok=42`, an out-of-memory error, and `done`. Everything before them is preamble. The naive harness appends all thirty lines.

```python filename=modules/agent-harness/code/harness-inter-09/truncate.py:44-49 COMPLETE
def pack_append_whole(results, window, cap):
    """Append every line, uncapped. Returns the full transcript -- only its first `window` lines fit."""
    transcript = []
    for r in results:
        transcript.extend(r["lines"])
    return transcript
```

Head-only keeps the first `cap` lines of each — fits the budget, cuts the tail.

```python filename=modules/agent-harness/code/harness-inter-09/truncate.py:57-62 COMPLETE
def pack_head_only(results, window, cap):
    """Keep the first `cap` lines of each result -- fits the budget but drops the tail where the answer is."""
    transcript = []
    for r in results:
        transcript.extend(r["lines"][:cap])
    return transcript
```

Head+tail keeps the first half and the last half with a marker between.

```python filename=modules/agent-harness/code/harness-inter-09/truncate.py:65-78 COMPLETE
def pack_head_tail(results, window, cap):
    """Keep the first cap/2 and last cap/2 lines of each, with a marker -- fits AND keeps both ends."""
    transcript = []
    for r in results:
        lines = r["lines"]
        if len(lines) <= cap:
            transcript.extend(lines)
            continue
        half = cap // 2
        cut = len(lines) - 2 * half
        transcript.extend(lines[:half])
        transcript.append("[... %d lines truncated ...]" % cut)
        transcript.extend(lines[-half:])
    return transcript
```

Predict the three outcomes before running. Append-whole is 30 lines into a 21-line window: it overflows, and the results at the end fall off. Head-only is 18 lines: fits, but each result is cut at line 6, so every last line — at lines 10, 12, 8 — is gone. Head+tail is 21 lines: fits, and each result keeps its last three lines including the answer. Now run it.

```text filename=modules/agent-harness/code/harness-inter-09/truncate.py --pack
PACK — lines produced, fits window, and salient last-lines kept (of 3)
--------------------------------------------------------------
  append whole  30 lines  OVERFLOW  salients kept: 1/3
  head only     18 lines  fits      salients kept: 0/3
  head + tail   21 lines  fits      salients kept: 3/3
```

Three strategies, three verdicts. Append-whole overflows at 30 lines; only the first 21 survive into the window, which happens to include just toolA's answer — toolB and toolC's answers fell off the end, 1 of 3 kept. Head-only fits comfortably at 18 lines and keeps 0 of 3 answers, because it truncated every result before its last line: the harness dutifully bounded the output and threw away every conclusion. Head+tail fits at 21 and keeps 3 of 3 — same budget as head-only, every answer preserved. The difference between 0 and 3 is entirely which end of each result the cap kept.

<svg role="img" aria-label="Bar chart of salient answers kept out of three: append-whole 1, head-only 0, head-plus-tail 3" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">answers kept (of 3)</text>
  <line x1="60" y1="130" x2="440" y2="130" stroke="var(--line)"/>
  <rect x="90" y="97" width="70" height="33" fill="var(--s2)" stroke="var(--line)"/><text x="112" y="91" font-family="var(--mono)" font-size="11" fill="var(--ink)">1</text><text x="88" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">whole</text>
  <rect x="210" y="130" width="70" height="2" fill="var(--s2)" stroke="var(--line)"/><text x="232" y="124" font-family="var(--mono)" font-size="11" fill="var(--s2)">0</text><text x="205" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">head-only</text>
  <rect x="330" y="31" width="70" height="99" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="352" y="25" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">3</text><text x="332" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">head+tail</text>
</svg>
^ Same window budget, three outcomes: head-only keeps nothing, append-whole keeps one by luck, head+tail keeps all three.

<svg role="img" aria-label="One 10-line result truncated two ways: head-only keeps lines 1 to 6 and loses the last line; head plus tail keeps lines 1 to 3 and 8 to 10, preserving the answer on line 10" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">a 10-line result, cap 6</text>
  <text x="30" y="40" font-family="var(--mono)" font-size="10" fill="var(--muted)">head-only</text>
  <g stroke="var(--line)">
    <rect x="30" y="46" width="120" height="14" fill="var(--acc-soft)"/><rect x="30" y="60" width="120" height="14" fill="var(--acc-soft)"/><rect x="30" y="74" width="120" height="14" fill="var(--acc-soft)"/>
    <rect x="30" y="88" width="120" height="14" fill="var(--acc-soft)"/><rect x="30" y="102" width="120" height="14" fill="var(--acc-soft)"/><rect x="30" y="116" width="120" height="14" fill="var(--acc-soft)"/>
    <rect x="30" y="130" width="120" height="42" fill="var(--panel)" stroke-dasharray="3 3"/>
    <rect x="30" y="172" width="120" height="14" fill="var(--s2)"/>
  </g>
  <text x="155" y="182" font-family="var(--mono)" font-size="9" fill="var(--s2)">answer LOST</text>
  <text x="300" y="40" font-family="var(--mono)" font-size="10" fill="var(--muted)">head + tail</text>
  <g stroke="var(--line)">
    <rect x="300" y="46" width="120" height="14" fill="var(--acc-soft)"/><rect x="300" y="60" width="120" height="14" fill="var(--acc-soft)"/><rect x="300" y="74" width="120" height="14" fill="var(--acc-soft)"/>
    <rect x="300" y="88" width="120" height="28" fill="var(--panel)" stroke-dasharray="3 3"/><text x="312" y="106" font-family="var(--mono)" font-size="8" fill="var(--muted)">[... cut ...]</text>
    <rect x="300" y="116" width="120" height="14" fill="var(--acc-soft)"/><rect x="300" y="130" width="120" height="14" fill="var(--acc-soft)"/>
    <rect x="300" y="144" width="120" height="14" fill="var(--acc-line)"/>
  </g>
  <text x="300" y="182" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">answer KEPT (line 10)</text>
</svg>
^ Head-only spends all six kept lines on the opening and loses line 10; head+tail spends three on the opening and three on the close, so the answer on line 10 survives.

## Build

Reproduce the packing. Pure standard library, deterministic, so 30/18/21 lines and 1/0/3 salients come out exactly.

Run `--results` for the inputs, `--pack` for the three strategies, `--check` for the gate. The self-test pins each strategy's specific failure or success — that append-whole overflows and loses answers, that head-only fits but loses them all, and that head+tail fits and keeps them all.

```python filename=modules/agent-harness/code/harness-inter-09/truncate.py:121-133 COMPLETE
    whole = pack_append_whole(results, window, cap)
    whole_overflows = len(whole) > window
    whole_kept = salients_kept(in_context(whole, window), results)
    whole_drops = whole_kept < len(results)
    print("  appending whole overflows the window and drops a result = %s (%d lines > %d, %d/%d salients)"
          % (whole_overflows and whole_drops, len(whole), window, whole_kept, len(results)))

    head = pack_head_only(results, window, cap)
    head_fits = len(head) <= window
    head_loses = salients_kept(head, results) == 0
    print("  head-only fits but loses every salient tail = %s (%d lines, %d/%d salients)"
          % (head_fits and head_loses, len(head), salients_kept(head, results), len(results)))
```

The head-only leg checks two things at once — `head_fits and head_loses` — and that conjunction is the whole point of the module. It is not enough to show head-only loses the answers; you have to show it loses them *while fitting the budget*, because that is what makes it seductive. A strategy that overflowed would be obviously broken; head-only looks correct — it bounded the output, it fits — and is silently useless. The test insists on both halves so the failure is the subtle one, not a strawman. Here is the full gate.

```text filename=modules/agent-harness/code/harness-inter-09/truncate.py --check
SELF-TEST — append-whole overflows; head-only loses the salient tails; head+tail fits and keeps them
--------------------------------------------------------------------------------------------
  appending whole overflows the window and drops a result = True (30 lines > 21, 1/3 salients)
  head-only fits but loses every salient tail = True (18 lines, 0/3 salients)
  head+tail fits AND keeps every salient tail = True (21 lines, 3/3 salients)
  head+tail preserves more answers than head-only at the same cap = True (3 vs 0)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  whole_overflows=True  head_loses=True  headtail_keeps=True  headtail_beats_head=True
```

Four True flags. Whole_overflows: appending everything blows the window and drops results. Head_loses: head-only fits but keeps zero answers. Headtail_keeps: head+tail fits and keeps all three. Headtail_beats_head: at the same cap, head+tail preserves three answers to head-only's zero. The last flag is the comparison that matters — same budget, opposite outcome, decided entirely by keeping the tail.

**The head-only leg asserts fits-and-loses together, because a truncation that fits the budget while silently dropping every answer is the failure that looks like success.**

## Definition of done

You are done when you reproduce the packing and can explain why head+tail wins at no extra cost.

Concretely: `--pack` shows append-whole overflowing at 30 lines (1/3 answers), head-only fitting at 18 (0/3), head+tail fitting at 21 (3/3); `--check` prints PASS with four True flags. You can say why a tool result must be capped at all — it is unbounded input to a fixed window — and why head-only is the wrong cap: tools conclude on the last line, and head-only drops it. You can describe the head+tail split and its marker, and say when you would weight the budget toward one end. And you can name the failure mode that makes head-only dangerous: it fits, so it looks correct, while losing exactly the information the tool was called for.

The habit to carry: never append a tool result of unknown size without a cap, and never cap by keeping only the head. Default to head+tail with a truncation marker, and weight the split toward whichever end your tools put the answer on.

## Boss fight

The instructive failure is an agent that "can't read errors" and gets blamed on the model.

An agent runs a build tool that fails. The tool emits four hundred lines: the full compile log, warnings, progress — and on the last line, `error: undefined reference to 'foo'`. The harness caps tool output at the first 50 lines to protect the window. The model receives fifty lines of warnings and no error message, concludes the build succeeded or guesses wildly, and the developer says "the agent is bad at debugging." The agent never saw the error. Head+tail truncation would have kept the last lines — the actual error — within the same 50-line budget, and the agent would have fixed the reference. The bug was in the harness's truncation, and it presented as a model capability problem, which is the hardest kind of bug to diagnose because you are looking at the wrong component.

Your turn, two moves. First, move the answer and watch which strategy is robust. Put the salient line in the *middle* of each result instead of the end. Predict: head-only still loses it (it keeps only the top), head+tail may also lose it (it keeps only the ends), and now neither pure strategy suffices — which is the real lesson that the answer's position drives the truncation policy, and that a tool with an unknown answer position wants a summary, not a slice. Second, tune the split. Change head+tail to keep 1 head line and 5 tail lines instead of 3 and 3, and predict: for these tail-heavy results it keeps every answer and more trailing context, at the cost of the opening — better here, worse for a tool that front-loads its status code. Sit with the trade: there is no universal split, only a split matched to where your tools put their signal, and the one thing that is always wrong is spending the whole budget on the end that does not have the answer.

## External resources

The context-management chapters of any agent framework's docs (LangChain, LlamaIndex, the Anthropic and OpenAI agent guides) cover tool-output truncation; the recurring advice is to bound observations and to summarize or head+tail rather than hard-cut.

For the general principle — that truncation should preserve the high-signal regions — the "lost in the middle" literature on long-context models (Liu et al.) is the empirical backdrop: models attend most to the beginning and end of their context, which is another reason head+tail beats a middle-preserving or head-only cut.

For production patterns, search for "tool result truncation" and "observation compression" in agent-harness codebases; the mature ones truncate to a token budget, insert an explicit elision marker, and offer a "fetch full output" tool so the agent can pull the complete result when the truncated view is not enough.
