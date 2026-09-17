---
id: toolmatch-inter-01
title: Match each parallel tool result to its call by id, not arrival order — out-of-order completion pairs the wrong result with the wrong call
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: When a model emits several tool calls in one turn, a good harness runs them in parallel for speed — but parallel calls finish in an order set by how long each takes, which has nothing to do with the order they were issued: a fast lookup returns before a slow one requested earlier. The harness then has to hand the results back to the model, and here is the fork. It can pair them by arrival — take the results in completion order and drop them onto the calls in issue order, slot by slot — or by identity, matching each result to the specific call it answers. Pairing by arrival is the bug, and a quiet one: because completion order differs from issue order, the results land on the wrong calls, so the weather call is told it returned a stock price and the stock call is told it returned the time, and nothing errors — every call has a result, the shapes are fine — but each result is attributed to the wrong question, and the model reasons from 'get_weather returned stock:150', producing confidently wrong conclusions built on correctly-fetched data pinned to the wrong calls. The fix is identity, not order: every tool call carries a unique id (the tool_call_id in modern tool-calling APIs) and every result carries the id of the call it answers, so the harness matches by id and completion order — which is noise — becomes irrelevant. On a fixture of three calls issued t0, t1, t2 but finishing t1, t2, t0, position pairing mismatches all three while id pairing gives every call its own result regardless of completion order.
eli5: Imagine you send three friends to fetch three different things and tell them to text you when they're done. They finish at different times, so the texts arrive in a jumbled order. If you assume "the first text is about the first errand," you'll think your friend who went for milk actually brought back batteries, just because the battery friend happened to text first. Nothing looks broken — you got three replies — but each reply is pinned to the wrong errand, and you'll act on totally wrong information. The fix is to have each friend say which errand they're reporting on ("this is about the milk"), so it doesn't matter who texts first. In an agent, that label is the tool call's id.
---

## Why this module

Running tool calls in parallel is one of the biggest speedups a harness offers — instead of paying the sum of the durations, you pay the longest one. But parallelism introduces a fact the serial case hid: results come back in an order you do not control and cannot predict, because it depends on each tool's latency, which varies with network, load, and cache state. A harness that was written serially, where result order trivially matched call order, carries an assumption that silently becomes false the moment the calls run concurrently.

The assumption is "the i-th result belongs to the i-th call." Serially it is true. In parallel it is true only by luck, when the calls happen to finish in issue order. When a later call finishes first — which is common, since it is just the fastest one — the assumption pairs its result with an earlier call, and every subsequent result shifts onto the wrong call too. The model then receives a context that says each tool returned something it did not, and there is no error to catch: the data is real, the pairing is wrong.

The correctness fix is to carry identity through the fan-out, which every serious tool-calling API supports via a call id. This module issues three calls, completes them out of order, and compares position-based pairing with id-based pairing.

**Parallel tool calls finish out of issue order, so pairing results to calls by arrival position attributes each result to the wrong call and the model reasons on scrambled data — results must be matched to calls by id, which makes completion order irrelevant.**

## Concepts

The fixture is three tool calls, each with an id, the result it returns, and a duration — issued in the order t0, t1, t2.

```json filename=modules/agent-harness/code/toolmatch-inter-01/toolmatch.json:3-7 COMPLETE
  "calls": [
    {"id": "t0", "tool": "get_weather", "result": "weather:sunny", "dur": 30},
    {"id": "t1", "tool": "get_stock", "result": "stock:150", "dur": 10},
    {"id": "t2", "tool": "get_time", "result": "time:noon", "dur": 20}
  ]
```

Completion order sorts the calls by duration — the order results actually arrive. Naive pairing zips the arrival-order results onto the issue-order call slots by position; id pairing matches each result to its call by id, independent of arrival.

```python filename=modules/agent-harness/code/toolmatch-inter-01/toolmatch.py:32-50 COMPLETE
def issue_order(calls):
    return [c["id"] for c in calls]


def completion_order(calls):
    """Results arrive in order of how long each call takes."""
    return sorted(calls, key=lambda c: c["dur"])


def naive_pairing(calls):
    """Pair arrival-order results to issue-order call slots by position."""
    arrived = completion_order(calls)
    slots = issue_order(calls)
    return {slots[i]: arrived[i]["result"] for i in range(len(calls))}


def id_pairing(calls):
    """Match each result to its call by id -- completion order is irrelevant."""
    return {c["id"]: c["result"] for c in calls}
```

Naive pairing reads two orderings and assumes they align; id pairing reads only the id attached to each result. That difference is whether completion order can corrupt the mapping.

<svg role="img" aria-label="Three calls issued t0 t1 t2 complete in order t1 t2 t0; position pairing draws crossing lines mapping each result to the wrong call, id pairing draws straight lines to the right call" viewBox="0 0 320 130">
  <text x="10" y="12" font-size="8" fill="var(--muted)">issued t0,t1,t2 · completed t1,t2,t0</text>
  <text x="20" y="34" font-size="7.5" fill="var(--s2)">position pairing (by arrival)</text>
  <g font-size="6.5">
  <text x="24" y="52" fill="var(--ink)">t0</text><text x="24" y="66" fill="var(--ink)">t1</text><text x="24" y="80" fill="var(--ink)">t2</text>
  <text x="120" y="52" fill="var(--muted)">stock:150</text><text x="120" y="66" fill="var(--muted)">time:noon</text><text x="120" y="80" fill="var(--muted)">weather:sunny</text>
  <line x1="34" y1="49" x2="116" y2="49" stroke="var(--s2)"/><line x1="34" y1="63" x2="116" y2="63" stroke="var(--s2)"/><line x1="34" y1="77" x2="116" y2="77" stroke="var(--s2)"/>
  <text x="180" y="66" fill="var(--s2)">all 3 wrong</text>
  </g>
  <text x="20" y="102" font-size="7.5" fill="var(--s1)">id pairing (t0→weather, t1→stock, t2→time): all correct</text>
</svg>
^ Position pairing maps t0 to the first-arrived result (stock:150), t1 to the second (time:noon), t2 to the third (weather:sunny) — every call wrong, because the arrival order t1,t2,t0 was zipped onto the issue order t0,t1,t2. Id pairing sends each result to the call whose id it carries, correct regardless of arrival.

**Naive pairing assumes result order equals call order and breaks when they differ; id pairing carries the call's identity on the result, so the arrival order cannot scramble the mapping.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the parallel-tool-dispatch step of an agent loop, reduced to three calls so every pairing is checkable by hand.

Run `--order` to see the two orderings.

```text filename=toolmatch.py --order
  issued (in order)      : ['t0', 't1', 't2']
  completed (by duration): ['t1', 't2', 't0']
```

The calls were issued t0, t1, t2, but t1 is fastest (duration 10) so it returns first, then t2 (20), then t0 (30). The completion order t1, t2, t0 is a rotation of the issue order — no result arrives in the slot its call occupies. This is not a pathological case; it is the ordinary consequence of the calls having different latencies, which they almost always do.

Now `--pair` computes both pairings and compares them per call.

```python filename=modules/agent-harness/code/toolmatch-inter-01/toolmatch.py:67-67 COMPLETE
    naive, correct = naive_pairing(calls), id_pairing(calls)
```

Every row of the comparison disagrees.

```text filename=toolmatch.py --pair
  call   true result       position pairing    ok?
  t0     weather:sunny     stock:150         NO  <- wrong result
  t1     stock:150         time:noon         NO  <- wrong result
  t2     time:noon         weather:sunny     NO  <- wrong result
```

Position pairing gets all three wrong. Call t0 (get_weather) is recorded as having returned stock:150; t1 (get_stock) as time:noon; t2 (get_time) as weather:sunny. Every result is real — the tools all worked — but every one is attributed to the wrong call. The model now believes the weather is a stock price and the stock is a time, and it will reason from those attributions with full confidence, because from its point of view the tools simply returned strange answers. Id pairing (the "true result" column) gives each call exactly what it fetched.

<svg role="img" aria-label="Bars: position pairing gets 0 of 3 calls right, id pairing gets 3 of 3, with the note that all results are real but misattributed" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">calls given the correct result (of 3)</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">position pairing</text>
  <rect x="110" y="32" width="4" height="16" fill="var(--s2)"/><text x="120" y="44" font-size="8" fill="var(--ink)">0 of 3 (all misattributed)</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">id pairing</text>
  <rect x="110" y="62" width="180" height="16" fill="var(--s1)"/><text x="150" y="74" font-size="8" fill="var(--panel)">3 of 3</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">the results are all real — position pairing just pins them to the wrong calls</text>
</svg>
^ Position pairing gets zero of three calls right; id pairing gets all three. The failure is total here because the completion order is a full rotation, and it produces no error — just three real results attached to the wrong three calls.

**Position pairing attributes all three real results to the wrong calls, so the model reasons on scrambled data; id pairing gives every call its own result — the difference is whether the harness trusts arrival order or the call id.**

## Build

The self-test establishes the setup and the failure: the calls complete in a different order than issued, position pairing mismatches some call, and the first-issued call specifically gets the wrong result.

```python filename=modules/agent-harness/code/toolmatch-inter-01/toolmatch.py:85-95 COMPLETE
    completion_differs = [c["id"] for c in completion_order(calls)] != issue_order(calls)
    print("  the calls complete in a different order than issued = %s (%s vs %s)"
          % (completion_differs, [c["id"] for c in completion_order(calls)], issue_order(calls)))

    mismatches = [cid for cid in correct if naive[cid] != correct[cid]]
    position_mispairs = len(mismatches) > 0
    print("  position pairing assigns some result to the wrong call = %s (%s)" % (position_mispairs, mismatches))

    first_call = calls[0]["id"]
    first_call_wrong = naive[first_call] != correct[first_call]
    print("  the first-issued call %s gets the wrong result = %s (%r, should be %r)"
          % (first_call, first_call_wrong, naive[first_call], correct[first_call]))
```

Then the fix: id pairing gives every call its own result, and it is unchanged if the results are reordered — the property position pairing lacks.

```python filename=modules/agent-harness/code/toolmatch-inter-01/toolmatch.py:98-101 COMPLETE
    id_pairing_correct = all(id_pairing(calls)[c["id"]] == c["result"] for c in calls)
    print("  id pairing gives every call its own result = %s" % id_pairing_correct)

    id_pairing_order_independent = id_pairing(calls) == id_pairing(list(reversed(calls)))
    print("  id pairing is the same regardless of result order = %s" % id_pairing_order_independent)
```

Running the check confirms every clause.

```text filename=toolmatch.py --check
  the calls complete in a different order than issued = True (['t1', 't2', 't0'] vs ['t0', 't1', 't2'])
  position pairing assigns some result to the wrong call = True (['t0', 't1', 't2'])
  the first-issued call t0 gets the wrong result = True ('stock:150', should be 'weather:sunny')
  id pairing gives every call its own result = True
  id pairing is the same regardless of result order = True
```

**The check ties the misattribution to the completion order differing from issue order, and shows id pairing correct and order-independent — the mapping made immune to the arrival order that broke position pairing.**

## Definition of done

Done means position pairing misattributes results when completion order differs from issue order, and id pairing is both correct and independent of result order. The order-independence clause is the real specification: correctness under one particular arrival order is luck, but correctness under any arrival order — which id pairing has and position pairing does not — is the property a parallel harness actually needs, because it does not control which result arrives first.

Two clarifications ground this in real tool-calling. First, the id is not something you invent; the API provides it. In modern tool-calling formats each tool call the model emits comes with a unique id (OpenAI's and Anthropic's tool-use blocks both carry one), and the protocol requires each tool result to be returned tagged with the id of the call it answers. Honoring that contract is exactly id-based pairing; the bug appears when a harness ignores the id and instead relies on ordering, list position, or a shared mutable variable that the parallel tasks race on. Second, the failure is worse than it looks because it is silent and load-dependent. It may never occur in testing, where a mock returns results instantly in issue order, and then appear in production only under the latency variance that makes completion order diverge — and even then it produces not a crash but subtly wrong answers, which are far harder to trace than an exception. The defense is to make id-matching structural: build the result set as a map keyed by call id, never as a list assembled in completion order, so there is no ordering for the code to get wrong in the first place.

<svg role="img" aria-label="The tool-calling contract: each call has a unique id, each result carries its call's id, and the harness builds a map keyed by id rather than a list in completion order" viewBox="0 0 320 118">
  <rect x="14" y="22" width="292" height="40" fill="none" stroke="var(--s1)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s1)">the contract: id on every call, id on every result</text>
  <text x="22" y="50" font-size="7" fill="var(--ink)">build results as a map {id: result}, never a list in arrival order</text>
  <text x="14" y="82" font-size="7.5" fill="var(--muted)">silent + load-dependent: passes with instant mocks, fails under real latency variance</text>
  <text x="14" y="102" font-size="7.5" fill="var(--ink)">make id-matching structural so there is no ordering to get wrong</text>
</svg>
^ Every tool-calling API tags calls and results with a matching id; the harness's job is to build the result set as a map keyed by that id, not a list assembled in completion order. Doing so structurally removes the ordering the position bug depends on — a bug that hides behind instant test mocks and surfaces only under production latency.

**Done means id pairing is correct and order-independent while position pairing misattributes under out-of-order completion — so results are matched to calls by the API-provided id and assembled as a map, never a list in arrival order, closing a silent load-dependent bug.**

## Boss fight

An agent that makes several parallel API calls per turn works perfectly in development but, in production, occasionally produces answers that mix up which data came from where — citing one city's weather for another, or one user's record under a different user's name. The bug is intermittent and never reproduces locally. The team's harness collects parallel results into a list as each call's future resolves, then appends them to the conversation in that order. What is happening, and how do you fix it?

The harness is pairing tool results to tool calls by completion order instead of by id. It collects results into a list as each future resolves — which is completion order, determined by latency — and then appends them positionally against the calls, so whenever a later-issued call finishes before an earlier one, its result lands on the wrong call. The model then reads results attributed to the wrong calls and produces the observed mix-ups: one city's weather cited for another, one user's record under another's name. It never reproduces locally because in development the calls are fast or mocked and tend to resolve in issue order, so completion order accidentally matches and the pairing is correct by luck; in production, real and variable latencies make completion order diverge from issue order, and the misattribution appears intermittently, exactly correlated with which call happened to be slow. It is silent because every result is a real, well-formed value — nothing errors, the answers are just wrong. The fix is to match results to calls by the tool call's id, which the tool-calling API already provides on every call and expects on every result: build the results as a map keyed by call id (result[call_id] = value) rather than a list in resolution order, and emit each tool-result message tagged with its call's id. Then completion order is irrelevant and each result is always attached to the call it answers. To keep the class of bug from returning, make the id-matching structural — the code should never have a code path that assembles results by position — and add a test that resolves the parallel calls in a deliberately shuffled order to confirm the pairing is still correct, since the default fast-mock test cannot catch it.

## External resources

The tool-use / function-calling specifications for major model APIs (the tool_call_id / tool_use id contract in OpenAI's and Anthropic's tool-calling docs) — how each call is assigned an id and why each result must be returned tagged with it, which is precisely id-based pairing.

Engineering guidance on parallel tool execution in agent frameworks (collecting concurrent results into an id-keyed structure rather than a completion-ordered list, and testing with shuffled resolution orders) — the harness patterns that make result-to-call matching robust against the nondeterministic completion order of parallel calls.
