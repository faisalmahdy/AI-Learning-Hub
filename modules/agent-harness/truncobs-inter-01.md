---
id: truncobs-inter-01
title: Truncate an oversized tool observation by relevance, not by position — head/tail truncation can delete the answer
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: An agent reads the observation a tool returns, but observations do not respect a context budget — a log search, a file read, a query can each return far more text than the harness can paste back. So the harness truncates, and how it truncates decides what the agent can still know. Positional truncation — keep the first N lines (head) or the last N (tail) — is trivial and treacherous, because the line that answers the agent's question has no reason to sit at an end; a grep hit, an error, the one requested row lands wherever the data puts it, often in the middle, and keeping the ends deletes the middle. The agent then reads a plausible observation with the answer removed, concludes "not found", and gives up or hallucinates — and nothing in the transcript reveals that the harness, not the tool, hid it. The fix is to truncate by relevance to the query the agent is pursuing: score lines by the query, keep the matches plus a little context, drop the filler, all within the same budget. On a fixture where a log tool returns 20 lines with the one ERROR line at line 10 and the budget is 6, head keeps lines 1–6 and tail keeps 15–20 — both miss the outage and report "healthy" — while relevance keeps lines 7–12 and finds "disk full", the same 6-line budget reaching the opposite conclusion.
eli5: Imagine you ask a friend to read you the important part of a long letter, but they can only read six lines out loud. If they always read the first six lines, or always the last six, they might completely skip the one line in the middle that says "the payment bounced." You'd hear a normal-sounding letter and think everything was fine. A smarter friend reads the six lines that actually mention what you asked about — so even though they still only read six lines, they read the six that matter, and you hear the bad news. The number of lines didn't change; which six lines they chose did, and that choice decided whether you learned the truth.
---

## Why this module

An agent is only as good as the observations it reads, and observations are routinely too big to read whole. The harness has to cut them down — and the obvious way to cut, keeping the top or the bottom, quietly throws away the one line the agent needed, leaving a transcript that looks complete and is wrong.

An agent works by calling a tool and reading the observation it returns. But observations do not fit a fixed budget: a log search, a file read, a database query can each return far more text than the harness can paste back into the model's limited context. So the harness truncates, and *how* it truncates decides what the agent can still know. The easy truncations are positional — keep the first N lines (head) or the last N lines (tail). They are trivial to implement and they are a trap, because the line that actually answers the agent's question has no reason to sit at the top or bottom of the output. A grep hit, an error, the one row you asked for lands wherever the data puts it, often in the middle, and a positional truncation that keeps the ends deletes exactly the middle. The agent then reads a plausible-looking observation with the answer removed, concludes "not found", and either gives up or hallucinates — and nothing in the transcript shows that the harness, not the tool, hid the answer.

The fix is to truncate by relevance to the query the agent is pursuing: keep the lines that match, plus a little surrounding context, and drop the non-matching filler, all within the same budget. A matching line is worth more than a filler line, so under a tight budget you spend the budget on the match. This needs no model — the agent already has a query (the term it searched, the id it asked about), so the harness scores lines by that query and keeps the highest-scoring ones. The deeper principle: an observation budget is a scarce resource, and spending it on whatever happened to be printed first is the one allocation guaranteed to sometimes spend it all on filler. This module truncates a 20-line log three ways under a 6-line budget and shows the answer survive or die.

**A tool observation must be truncated to fit the context budget, and positional (head/tail) truncation deletes any answer that sits in the middle, so the harness should truncate by relevance to the agent's query — keeping the matching lines under the same budget rather than whatever printed at the ends.**

## Concepts

**Positional truncation** keeps a window at one end — the first `budget` lines, or the last `budget`. It never looks at what the agent asked for, so whether it keeps the answer is pure luck of where the answer landed.

```python filename=modules/agent-harness/code/truncobs-inter-01/truncobs.py:46-53 COMPLETE
def truncate_head(lines, budget):
    """Keep the first `budget` lines -- positional, ignores what the agent asked for."""
    return lines[:budget]


def truncate_tail(lines, budget):
    """Keep the last `budget` lines -- positional, ignores what the agent asked for."""
    return lines[-budget:]
```

**Relevance truncation** scores lines by the agent's query: keep the matching lines, then expand outward to neighbors for context until the budget is full. The budget is spent on the lines that answer the question, not on filler that happened to print first.

```python filename=modules/agent-harness/code/truncobs-inter-01/truncobs.py:56-73 COMPLETE
def truncate_relevant(lines, query, budget):
    """Keep the lines matching `query`, then expand outward for context until the budget is full."""
    matched = [i for i, line in enumerate(lines) if query in line]
    if not matched:
        return lines[:budget]
    selected = set(matched)
    radius = 1
    while len(selected) < budget:
        grew = False
        for m in matched:
            for j in (m - radius, m + radius):
                if 0 <= j < len(lines) and j not in selected and len(selected) < budget:
                    selected.add(j)
                    grew = True
        if not grew:
            break
        radius += 1
    return [lines[i] for i in sorted(selected)]
```

<svg role="img" aria-label="A strip of 20 log lines with the ERROR needle at line 10; the head window covers lines 1 to 6 and the tail window covers 15 to 20, both missing the needle, while the relevance window covers 7 to 12 and contains it" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">20 lines, needle at line 10, budget 6 — which window keeps it?</text>
  <g transform="translate(20,20)">
  <rect x="0" y="0" width="260" height="14" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="117" y="0" width="13" height="14" fill="var(--s2)"/>
  <text x="112" y="26" fill="var(--muted)" font-size="7">needle (line 10)</text>
  <text x="0" y="-2" fill="var(--muted)" font-size="6">1</text><text x="250" y="-2" fill="var(--muted)" font-size="6">20</text>
  </g>
  <g transform="translate(20,50)">
  <rect x="0" y="0" width="78" height="10" fill="var(--muted)"/><text x="0" y="20" fill="var(--muted)" font-size="7">head 1-6 → miss</text>
  </g>
  <g transform="translate(20,74)">
  <rect x="182" y="0" width="78" height="10" fill="var(--muted)"/><text x="182" y="20" fill="var(--muted)" font-size="7">tail 15-20 → miss</text>
  </g>
  <g transform="translate(20,98)">
  <rect x="78" y="0" width="78" height="10" fill="var(--s1)"/><text x="78" y="20" fill="var(--muted)" font-size="7">relevant 7-12 → hit</text>
  </g>
</svg>
^ Head keeps the first six lines and tail the last six; the needle sits at line 10, in neither window, so both positional strategies drop it — only the relevance window, centered on the match, keeps the answer under the same 6-line budget.

**Positional truncation keeps a window chosen by position and blind to the query, so it keeps the answer only by luck; relevance truncation spends the same budget on the lines that match the agent's query, so the answer survives by construction.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/truncobs-inter-01/truncobs.py

The fixture is a 20-line log-search result with a 6-line budget, and the query the agent is chasing.

```json filename=modules/agent-harness/code/truncobs-inter-01/truncobs.json:2-3 COMPLETE
  "query": "ERROR",
  "budget": 6,
```

The one ERROR line — "write failed: disk full" — is line 10 of 20, in the middle. Run `--truncate` to see which lines each strategy keeps.

```text filename=--truncate
TRUNCATE — 20 lines into a 6-line budget; needle = the 'ERROR' line
------------------------------------------------------------------
  head      keeps: ['line 01', 'line 02', 'line 03', 'line 04', 'line 05', 'line 06']
            needle present = False
  tail      keeps: ['line 15', 'line 16', 'line 17', 'line 18', 'line 19', 'line 20']
            needle present = False
  relevant  keeps: ['line 07', 'line 08', 'line 09', 'line 10', 'line 11', 'line 12']
            needle present = True
```

Head keeps lines 1–6 and tail keeps 15–20 — both windows sit entirely to one side of line 10, so the ERROR is present in neither, and the relevance strategy keeps lines 7–12, centered on the match. Each strategy kept exactly six lines; they differ only in *which* six. That is the whole point: the budget was never the problem, the allocation was.

<svg role="img" aria-label="Three rows of six budget slots each: head and tail fill all six with filler lines and zero matches, relevance fills one slot with the match and five with context" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the same 6 slots, spent differently — only relevance buys the match</text>
  <g transform="translate(70,22)">
  <text x="-60" y="12" fill="var(--muted)" font-size="7">head</text>
  <rect x="0" y="2" width="16" height="12" fill="var(--muted)"/><rect x="20" y="2" width="16" height="12" fill="var(--muted)"/><rect x="40" y="2" width="16" height="12" fill="var(--muted)"/><rect x="60" y="2" width="16" height="12" fill="var(--muted)"/><rect x="80" y="2" width="16" height="12" fill="var(--muted)"/><rect x="100" y="2" width="16" height="12" fill="var(--muted)"/>
  <text x="124" y="12" fill="var(--muted)" font-size="7">0 matches</text>
  </g>
  <g transform="translate(70,44)">
  <text x="-60" y="12" fill="var(--muted)" font-size="7">tail</text>
  <rect x="0" y="2" width="16" height="12" fill="var(--muted)"/><rect x="20" y="2" width="16" height="12" fill="var(--muted)"/><rect x="40" y="2" width="16" height="12" fill="var(--muted)"/><rect x="60" y="2" width="16" height="12" fill="var(--muted)"/><rect x="80" y="2" width="16" height="12" fill="var(--muted)"/><rect x="100" y="2" width="16" height="12" fill="var(--muted)"/>
  <text x="124" y="12" fill="var(--muted)" font-size="7">0 matches</text>
  </g>
  <g transform="translate(70,66)">
  <text x="-60" y="12" fill="var(--muted)" font-size="7">relevant</text>
  <rect x="0" y="2" width="16" height="12" fill="var(--s1)"/><rect x="20" y="2" width="16" height="12" fill="var(--s1)"/><rect x="40" y="2" width="16" height="12" fill="var(--s2)"/><rect x="60" y="2" width="16" height="12" fill="var(--s1)"/><rect x="80" y="2" width="16" height="12" fill="var(--s1)"/><rect x="100" y="2" width="16" height="12" fill="var(--s1)"/>
  <text x="124" y="12" fill="var(--muted)" font-size="7">1 match + context</text>
  </g>
  <text x="10" y="100" fill="var(--muted)" font-size="7">filler slot = plain; match slot = highlighted; context slot = light</text>
</svg>
^ All three strategies spend six budget slots; head and tail spend every slot on non-matching filler, while relevance spends one slot on the ERROR match and five on its context — so the answer is in view for the same cost. Head and tail spent all six lines on routine "handled request" filler and had nothing left for the one line that mattered, while relevance spent its six on the match and its immediate neighbors. Note also how invisible the failure is — a positionally-truncated observation of a healthy-looking log is exactly what a broken system produces, and the agent has no signal that a truncation happened at all, let alone that it removed the answer.

## Build

The observation the agent reads becomes the conclusion the agent reaches. Run `--answer`.

```text filename=--answer
ANSWER — what the agent concludes from each truncated observation
------------------------------------------------------------------
  head      -> no 'ERROR' in view: agent reports the service healthy (WRONG)
  tail      -> no 'ERROR' in view: agent reports the service healthy (WRONG)
  relevant  -> found: line 10: ERROR write failed: disk full on /var/data
```

Under head and tail truncation the agent sees no error and reports the service healthy — a confident, wrong conclusion drawn from an observation the harness silently gutted. Under relevance truncation the same agent, on the same tool output and the same 6-line budget, finds the disk-full failure. The divergence is decided entirely by the truncation strategy, upstream of any reasoning the agent does; a perfect reasoner reading the head-truncated log still concludes "healthy", because the evidence was removed before it ever reached the model. Whether a line survived is just a membership test against the kept view.

```python filename=modules/agent-harness/code/truncobs-inter-01/truncobs.py:76-77 COMPLETE
def contains(view, query):
    return any(query in line for line in view)
```

<svg role="img" aria-label="Three truncated observations feeding an agent: head and tail lead to a wrong healthy verdict, relevance leads to finding the disk-full error" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same budget, same agent — the truncation decides the verdict</text>
  <g transform="translate(10,24)">
  <rect x="0" y="0" width="60" height="18" fill="none" stroke="var(--line)"/><text x="8" y="12" fill="var(--muted)" font-size="7">head 1-6</text>
  <rect x="0" y="30" width="60" height="18" fill="none" stroke="var(--line)"/><text x="8" y="42" fill="var(--muted)" font-size="7">tail 15-20</text>
  <rect x="0" y="60" width="60" height="18" fill="none" stroke="var(--s1)"/><text x="6" y="72" fill="var(--muted)" font-size="7">relevant 7-12</text>
  </g>
  <line x1="72" y1="33" x2="150" y2="20" stroke="var(--muted)"/>
  <line x1="72" y1="45" x2="150" y2="20" stroke="var(--muted)"/>
  <line x1="72" y1="93" x2="150" y2="90" stroke="var(--s1)"/>
  <g transform="translate(152,10)">
  <rect x="0" y="0" width="130" height="24" fill="none" stroke="var(--muted)"/>
  <text x="6" y="11" fill="var(--muted)" font-size="7">"service healthy"</text>
  <text x="6" y="20" fill="var(--muted)" font-size="7">WRONG — outage missed</text>
  </g>
  <g transform="translate(152,78)">
  <rect x="0" y="0" width="130" height="24" fill="none" stroke="var(--s1)"/>
  <text x="6" y="11" fill="var(--muted)" font-size="7">"disk full on /var/data"</text>
  <text x="6" y="20" fill="var(--muted)" font-size="7">correct — outage found</text>
  </g>
</svg>
^ Head and tail truncation both feed the agent a needle-free observation, so it reports the service healthy and misses the outage; relevance truncation feeds it the ERROR line, so the same agent reaches the correct verdict.

## Definition of done

The self-test pins the geometry (the needle is in neither end window), both positional failures, and the relevance fix — all under one shared budget.

```python filename=modules/agent-harness/code/truncobs-inter-01/truncobs.py:116-129 COMPLETE
    needle = next(i for i, l in enumerate(lines) if query in l)
    needle_in_middle = budget <= needle < len(lines) - budget
    print("  the needle line is in the middle, outside both end windows = %s (line %d of %d, budget %d)"
          % (needle_in_middle, needle + 1, len(lines), budget))

    head_misses = not contains(truncate_head(lines, budget), query)
    print("  head-truncation drops the needle = %s" % head_misses)

    tail_misses = not contains(truncate_tail(lines, budget), query)
    print("  tail-truncation drops the needle = %s" % tail_misses)

    rel = truncate_relevant(lines, query, budget)
    relevance_keeps = contains(rel, query)
    print("  relevance-truncation keeps the needle = %s (%s)" % (relevance_keeps, [l.split(":")[0] for l in rel]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the needle is in neither the head nor the tail window; head and tail truncation drop it; relevance keeps it
----------------------------------------------------------------------------------------------------------------------
  the needle line is in the middle, outside both end windows = True (line 10 of 20, budget 6)
  head-truncation drops the needle = True
  tail-truncation drops the needle = True
  relevance-truncation keeps the needle = True (['line 07', 'line 08', 'line 09', 'line 10', 'line 11', 'line 12'])
  all strategies obey the same line budget = True (6 lines each)
```

**Done means the failure and the fix are shown on real output at one budget: the ERROR needle sits at line 10 (outside both the head window 1–6 and the tail window 15–20), so head and tail truncation both drop it and the agent reports healthy, while relevance truncation keeps lines 7–12 including the needle — all three strategies keeping exactly six lines, so the difference is allocation, not budget.**

## Boss fight

Predict where relevance truncation is still not enough, because "keep the matching lines" hides assumptions that a real harness has to make explicit.

The first trap is that relevance needs a query, and the agent does not always have a crisp one. A grep with a literal term is easy to score against; "summarize what this service did last night" has no keyword to match, so there is nothing for the line-scorer to rank. In that regime the honest move is not to fake relevance but to change the operation: have the tool itself reduce before it returns (aggregate, count, sample, or summarize server-side), or return a structured result the harness can page through, rather than dumping raw lines for the harness to guess among. And whatever strategy runs, the truncation must be *visible* — the observation should say "showing 6 of 20 lines, filtered by ERROR" — so the agent knows the view is partial and can ask for more, page, or refine, instead of treating a truncated observation as the whole truth. A silent truncation is the actual bug here; a labeled one is a feature the agent can reason about.

The second trap is that relevance can create its own blind spots, in two opposite directions. If it keeps *only* matching lines it can strip the context that makes them meaningful — the ERROR line without the request that triggered it, or the exception without the stack frame above it — which is why the fix expands to neighbors rather than keeping bare matches; the right amount of context is a real parameter, not zero and not the whole file. And relevance scored on the *wrong* query fails exactly like positional truncation: if the agent is chasing "disk full" but scores lines by "ERROR", a different error can crowd out the disk-full line under a tight budget, and the agent again reads a confident partial view. So relevance truncation moves the risk rather than removing it: instead of "did the answer land at an end?", the question becomes "is the query the right one, is there enough context, and does the agent know the view is filtered?" — which is why the durable fixes are reducing at the source and labeling the truncation, with relevance-in-the-harness as the fallback for when a raw dump is all you have.

**Relevance truncation beats head/tail because it spends the budget on the agent's query, but it assumes a scorable query, needs surrounding context (expand to neighbors, don't keep bare matches), and must be labeled as partial so the agent can page or refine — and the more durable fixes push the reduction into the tool itself (aggregate, sample, summarize server-side) so the harness is not guessing which lines to keep at all.**

## External resources

Any agent-framework documentation on observation or context management — how tool results are truncated, summarized, or paged to fit the model's context window, and why raw tool output is reduced before it re-enters the prompt.

Writing on retrieval and "needle in a haystack" evaluations — the same failure in a different setting: an answer present in the source but outside the window the system actually reads, and why what you keep matters more than how much.

The companion per-tool-budget and cost-aware-routing modules in this topic — all three are about spending a scarce agent resource (tool calls, model cost, observation space) deliberately rather than by a default that silently fails.
