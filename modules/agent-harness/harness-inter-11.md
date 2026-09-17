---
id: harness-inter-11
title: Run independent tool calls in parallel — a serial harness pays the sum of durations, not the critical path
topic: agent-harness
level: intermediate
status: ready
time: 21 min
summary: When a turn issues several tool calls, independent ones can overlap; a serial harness runs them one after another and pays the sum of all durations. A parallel harness pays only the critical path — the longest chain of dependent calls. On four calls (3s, 2s, 4s, and 1s depending on the first), serial takes 10s and parallel takes 4s, a 2.5× speedup, with the dependency still respected.
eli5: If you have to boil water, chop vegetables, and preheat the oven, you don't do them one at a time — you start all three at once, because none needs the others. Only the step that needs a finished step waits. A slow assistant does everything in a line; a fast one overlaps everything that can overlap.
---

## Why this module

An agent turn that makes several tool calls often makes most of them for no reason in sequence, and the user waits through every one added end to end.

Within a single turn, an agent frequently needs several things from the outside world: search the web, query a database, read a file, call an API. Many of these are independent — the web search does not need the database result, the file read does not need the API call. They could all happen at the same time. But the simplest harness runs them one after another: issue the first, wait for it, issue the second, wait for it, and so on. The turn's latency is then the sum of every call's duration, and if you have four calls of a few seconds each, the user waits ten or fifteen seconds for work that could have finished in the time of the single slowest call.

The waste is invisible in the code because serial execution looks correct — each call runs, each returns, the answer is right. It is only slow, and slowness is easy to attribute to "the tools are slow" or "the model is slow" rather than to the harness running independent work in sequence. But the tools were not the problem; the scheduling was. The same calls, overlapped, finish far sooner.

A parallel harness runs independent calls concurrently and serializes only where one call genuinely depends on another's output — a summarize that needs the fetched document, a lookup that needs the id from a prior search. The turn's latency becomes the critical path: the longest chain of calls that truly must run in order, not the total of all calls. Everything off the critical path overlaps and is free.

We will run four calls in a turn — three independent, one that depends on the first. Serially they take 10 seconds. In parallel, the three independent calls overlap and the dependent one waits only for its single prerequisite, so the turn finishes in 4 seconds — the critical path — a 2.5× speedup with the dependency still correctly respected.

**A serial harness pays the sum of every call's duration even when the calls are independent; a parallel harness pays only the critical path, overlapping everything that does not depend on something else.**

## Concepts

<svg role="img" aria-label="Dependency graph: A, B, C are independent nodes; D has an edge from A; the critical path is C alone at 4 and A to D at 4" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">dependency graph (edge = must run after)</text>
  <g font-family="var(--mono)" font-size="10">
    <circle cx="80" cy="60" r="24" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="66" y="58" fill="var(--acc-ink)">A</text><text x="70" y="72" fill="var(--acc-ink)">3s</text>
    <circle cx="80" cy="120" r="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="66" y="118" fill="var(--acc-ink)">B</text><text x="70" y="130" fill="var(--acc-ink)">2s</text>
    <circle cx="220" cy="120" r="24" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="206" y="118" fill="var(--acc-ink)">C</text><text x="210" y="132" fill="var(--acc-ink)">4s</text>
    <circle cx="220" cy="60" r="20" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="206" y="58" fill="var(--acc-ink)">D</text><text x="210" y="72" fill="var(--acc-ink)">1s</text>
  </g>
  <line x1="104" y1="60" x2="200" y2="60" stroke="var(--ink)"/><text x="130" y="52" font-family="var(--mono)" font-size="8" fill="var(--muted)">A→D</text>
  <text x="290" y="55" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">critical path (4s):</text>
  <text x="290" y="72" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">A→D = 3+1, and C = 4</text>
  <text x="290" y="100" font-family="var(--mono)" font-size="9" fill="var(--muted)">B (2s) is free — it</text>
  <text x="290" y="114" font-family="var(--mono)" font-size="9" fill="var(--muted)">finishes inside the path</text>
</svg>
^ Three nodes with no incoming edges (A, B, C) start at once; only D waits, on its single edge from A — so the turn's floor is the longest path, not the node count.

The quantity that governs a parallel turn is the critical path. Model the calls as a graph: each call is a node with a duration, and an edge from A to D means D depends on A's output and cannot start until A finishes. The earliest a call can finish is its own duration plus the earliest finish of whatever it depends on. The turn is done when the last call finishes, so the turn's parallel latency is the maximum over all calls of that earliest-finish time — which is exactly the longest weighted path through the dependency graph, the critical path. Calls not on the critical path finish earlier and cost nothing extra; they were running while the critical path ran.

Serial latency, by contrast, is the sum of all durations, because serial execution puts every call on one long path whether or not the dependencies require it. Serial execution is equivalent to adding a false dependency between every pair of calls — "B waits for A" even though B never needed A — which is why it pays for edges that do not exist. The gap between the sum and the critical path is the latency the harness wastes by inventing those false dependencies, and the speedup is the sum divided by the critical path.

The dependencies are what make some serialization unavoidable and legitimate. If D needs the document that A fetches, D genuinely cannot start until A is done, and no scheduler can make that pair overlap. The art is to serialize exactly the real dependencies and nothing more. A harness that runs everything serially over-serializes (invents dependencies); a harness that tried to run a dependent call before its prerequisite would under-serialize (violate a real dependency and get a wrong or empty input). Correct parallel execution respects every real edge and adds no false ones.

This is why agent frameworks that support parallel tool calls — issuing a batch of independent calls in one step and awaiting them together — can be dramatically faster than those that issue one call per step. The model can often name several independent calls at once, and the harness's job is to run them concurrently rather than marching through them. The speedup grows with the number of independent calls and shrinks only where a genuine dependency chain forces order, so the practical lesson is to structure tool use so that as much as possible is independent, and to run the independent part in parallel.

**Parallel latency is the critical path — the longest chain of real dependencies — while serial latency is the sum, because serial execution invents a dependency between every pair; the speedup is the sum over the critical path.**

## Worked example

The fixture is four tool calls with durations and one real dependency.

```json filename=modules/agent-harness/code/harness-inter-11/calls.json:7-24 COMPLETE
  "calls": {
    "A": {
      "seconds": 3,
      "depends_on": null
    },
    "B": {
      "seconds": 2,
      "depends_on": null
    },
    "C": {
      "seconds": 4,
      "depends_on": null
    },
    "D": {
      "seconds": 1,
      "depends_on": "A"
    }
  }
```

A, B, and C are independent; D depends on A.

```text filename=modules/agent-harness/code/harness-inter-11/parallel.py --calls
CALLS — 4 tool calls in one turn
----------------------------------------------
  A  3s   independent
  B  2s   independent
  C  4s   independent
  D  1s   depends on A
----------------------------------------------
  A, B, C need nothing from each other; only D waits for A.
```

Serial latency just adds every duration.

```python filename=modules/agent-harness/code/harness-inter-11/parallel.py:39-41 COMPLETE
def serial_latency(calls):
    """One after another: the turn takes the sum of every call's duration."""
    return sum(c["seconds"] for c in calls.values())
```

The earliest a call can finish is its duration plus its dependency's finish time, and the parallel turn finishes when the last call does.

```python filename=modules/agent-harness/code/harness-inter-11/parallel.py:44-48 COMPLETE
def finish_time(cid, calls):
    """Earliest time this call can finish: its duration plus the finish time of what it depends on."""
    call = calls[cid]
    dep = call["depends_on"]
    return call["seconds"] + (finish_time(dep, calls) if dep else 0)
```

```python filename=modules/agent-harness/code/harness-inter-11/parallel.py:51-53 COMPLETE
def parallel_latency(calls):
    """Independent calls overlap; the turn finishes when the last call does -- the critical path."""
    return max(finish_time(cid, calls) for cid in calls)
```

Predict: serial is 3 + 2 + 4 + 1 = 10. Parallel — A, B, C start at time 0 and finish at 3, 2, 4; D waits for A (finishes at 3) then runs 1 second, finishing at 4. The last finish is 4 (C at 4 and D at 4 tie), so parallel is 4. Run it.

```text filename=modules/agent-harness/code/harness-inter-11/parallel.py --latency
LATENCY — serial (sum) vs parallel (critical path)
--------------------------------------------------
  serial:   10s  (3+2+4+1, one after another)
  parallel:  4s  (A,B,C at once; D after A)
  speedup:  2.5x
--------------------------------------------------
  the parallel turn finishes when the longest dependency chain does.
```

Serial is 10 seconds; parallel is 4; the speedup is 2.5×. The 4 seconds is the critical path: two chains tie for longest — C alone (4s) and A→D (3 + 1 = 4s) — and everything else finishes inside that window. B's 2 seconds and the first 3 of A's are entirely free, overlapped with C. The serial harness paid for all of it because it never let anything overlap; the parallel harness paid only for the longest unavoidable chain.

<svg role="img" aria-label="Turn latency: serial 10 seconds, parallel 4 seconds" viewBox="0 0 460 130" width="460" height="130">
  <rect x="0" y="0" width="460" height="130" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">turn latency (seconds, lower is better)</text>
  <line x1="60" y1="100" x2="440" y2="100" stroke="var(--line)"/>
  <rect x="100" y="35" width="150" height="65" fill="var(--s2)" stroke="var(--line)"/><text x="150" y="29" font-family="var(--mono)" font-size="11" fill="var(--s2)">10s</text><text x="120" y="116" font-family="var(--mono)" font-size="9" fill="var(--muted)">serial</text>
  <rect x="300" y="74" width="60" height="26" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="322" y="68" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">4s</text><text x="300" y="116" font-family="var(--mono)" font-size="9" fill="var(--muted)">parallel (2.5×)</text>
</svg>
^ Overlapping the independent calls cuts the turn from 10 seconds to 4 — the same work, scheduled to pay only the critical path.

<svg role="img" aria-label="Timelines: serial runs A,B,C,D end to end over 10 seconds; parallel runs A,B,C at once with D after A, finishing at 4 seconds" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">serial: one after another (10s)</text>
  <g font-family="var(--mono)" font-size="9">
    <rect x="40" y="26" width="90" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="72" y="39" fill="var(--ink)">A 3</text>
    <rect x="130" y="26" width="60" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="150" y="39" fill="var(--ink)">B 2</text>
    <rect x="190" y="26" width="120" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="240" y="39" fill="var(--ink)">C 4</text>
    <rect x="310" y="26" width="30" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="318" y="39" fill="var(--ink)">D</text>
  </g>
  <text x="345" y="39" font-family="var(--mono)" font-size="9" fill="var(--s2)">= 10s</text>
  <text x="16" y="78" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">parallel: overlap independent (4s)</text>
  <g font-family="var(--mono)" font-size="9">
    <rect x="40" y="86" width="90" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><text x="72" y="98" fill="var(--ink)">A 3</text>
    <rect x="40" y="106" width="60" height="16" fill="var(--acc-soft)" stroke="var(--line)"/><text x="60" y="118" fill="var(--ink)">B 2</text>
    <rect x="40" y="126" width="120" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="90" y="138" fill="var(--acc-ink)">C 4 (critical)</text>
    <rect x="130" y="146" width="30" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="132" y="158" fill="var(--acc-ink)">D (after A)</text>
  </g>
  <line x1="160" y1="82" x2="160" y2="170" stroke="var(--acc-ink)" stroke-dasharray="3 2"/><text x="166" y="176" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">4s = critical path</text>
  <text x="40" y="192" font-family="var(--mono)" font-size="8" fill="var(--muted)">A,B,C start at 0; D starts when A ends at 3; C and D both finish at 4</text>
</svg>
^ Serial lays every call end to end for 10s; parallel stacks the independent calls and finishes at the longest chain — 4s — with D correctly starting only after A.

## Build

Reproduce the two latencies. Pure arithmetic over the dependency graph, so 10s, 4s, and the 2.5× speedup come out exactly.

Run `--calls` for the graph, `--latency` for the numbers, `--check` for the gate. The self-test pins the whole model: parallel beats serial, parallel equals the critical path, the dependency is respected, and serial pays the full sum.

```python filename=modules/agent-harness/code/harness-inter-11/parallel.py:90-96 COMPLETE
    parallel_faster = p < s
    print("  the parallel turn is faster than serial = %s (%ds vs %ds)" % (parallel_faster, p, s))

    # the critical path is the longest single chain of dependent durations
    critical = max(finish_time(cid, calls) for cid in calls)
    parallel_is_critical_path = p == critical
    print("  parallel latency equals the critical path = %s (%ds)" % (parallel_is_critical_path, critical))
```

The `dependency_respected` check, below these, is what keeps the speedup honest. It would be easy to make parallel latency small by ignoring dependencies and running everything at time zero — but then D would run before A finished and get an empty or wrong input. The check asserts D finishes only after A plus D's own duration, proving the parallel scheduler respected the one real edge. Fast is worthless if it is wrong; the check insists the parallelization preserved correctness. Here is the full gate.

```text filename=modules/agent-harness/code/harness-inter-11/parallel.py --check
SELF-TEST — parallel equals the critical path and beats serial, while dependencies are respected
--------------------------------------------------------------------------------------------
  the parallel turn is faster than serial = True (4s vs 10s)
  parallel latency equals the critical path = True (4s)
  the dependent call D still waits for A = True (D finishes at 4, after A at 3)
  serial pays the full sum incl. 3 independent calls = True (10s)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  parallel_faster=True  parallel_is_critical_path=True  dependency_respected=True  serial_pays_sum=True
```

Four True flags. Parallel_faster: overlapping beats sequencing. Parallel_is_critical_path: parallel latency is exactly the longest dependency chain. Dependency_respected: D still waits for A, so the speedup did not break correctness. Serial_pays_sum: serial pays for all four durations including the three that could have overlapped. The third flag is the guardrail — a parallel scheduler is only correct if it respects every real dependency while overlapping everything else.

**The dependency-respected check proves the speedup did not come from running D before A — fast is worthless if the dependent call gets its input too early.**

## Definition of done

You are done when you reproduce 10s and 4s and can explain the critical path.

Concretely: `--latency` shows serial 10s and parallel 4s (2.5×); `--check` prints PASS with four True flags. You can model tool calls as a dependency graph and define parallel latency as the critical path — the longest chain of real dependencies — and serial latency as the sum. You can explain why serial execution is equivalent to inventing a dependency between every pair of calls, and why the speedup is the sum over the critical path. And you can state the correctness constraint: parallelization must respect every real dependency (never run a dependent call early) while overlapping everything independent.

The habit to carry: when a turn makes multiple tool calls, run the independent ones in parallel and serialize only the real dependencies. When an agent feels slow, check whether the harness is issuing tool calls one at a time when it could batch them, and structure tools so that as much of the work as possible is independent and can overlap.

## Boss fight

The instructive failure is an agent that feels sluggish and gets "optimized" everywhere except where the time actually goes.

An agent answers each query by making five API calls — none of which depend on each other — but the harness issues them one per step, waiting for each before the next. Each call takes about two seconds, so every answer takes ten seconds, and users complain it is slow. The team profiles the model, shortens prompts, switches to a faster model — shaving milliseconds — while the ten seconds of serialized, independent tool calls sits untouched, because it does not show up as "model time." Batching the five independent calls to run at once would cut the tool latency from ten seconds to two, a far bigger win than any prompt tweak. The slowness was never the model; it was the harness running parallelizable work in series.

Your turn, two moves. First, find the speedup ceiling. With all four calls independent (remove D's dependency on A), predict the parallel latency: it becomes just the single longest call, max(3, 2, 4, 1) = 4s — same 4 here because C already dominated, but now nothing is on a chain, so the speedup is purely sum-over-max. Then make the calls all equal, say four 3-second independent calls: serial 12s, parallel 3s, a 4× speedup equal to the number of calls. The more independent calls, the larger the speedup, up to N×. Second, add a dependency chain and watch the critical path grow. Make D depend on C and add E depending on D (E: 2s). Now the chain C→D→E is 4 + 1 + 2 = 7s, which exceeds any single call, so parallel latency rises to 7s. That shows the limit of parallelism: you can overlap everything off the critical path, but the critical path itself is a floor you cannot beat without removing a real dependency — which is why reducing dependency chains, not just adding concurrency, is the deeper optimization.

## External resources

The agent frameworks that support parallel tool calls document the pattern directly — the Anthropic and OpenAI tool-use guides describe returning multiple tool calls in one turn and executing them concurrently, and the LangChain and LlamaIndex docs cover parallel tool execution and its latency benefit.

For the scheduling theory, the critical-path method from project scheduling is exactly this computation — the longest weighted path through a dependency graph sets the minimum completion time — and any operations-research or project-management reference derives it.

For the broader principle, Amdahl's law formalizes the ceiling: the speedup from parallelization is bounded by the fraction of work that must remain serial, which in this setting is the critical path — the part no amount of concurrency can overlap away.
