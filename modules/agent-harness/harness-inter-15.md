---
id: harness-inter-15
title: Return partial results when one parallel tool call fails — or you throw away all the work that succeeded
topic: agent-harness
level: intermediate
status: ready
time: 21 min
summary: An agent fires several tool calls at once to save time, and one fails. Fail-fast treats any failure as a whole-batch error, so the model gets nothing and every successful call is discarded — the agent redoes all of them, wasting the work and the latency the parallelism bought. Returning partial results hands back every success plus a labeled error per failure, so the agent keeps the work and retries only what failed. On a batch of 4 with 3 successes and 1 timeout, fail-fast delivers 0 usable results; partial delivers 3 plus 1 surfaced error.
eli5: You send four friends to fetch four books at once. Three come back with books; one got stuck. The silly move is to say "the trip failed" and send everyone out again. The smart move is to keep the three books, note which one is missing, and only send someone back for that one. A failed errand shouldn't cancel the successful ones.
---

## Why this module

Firing tool calls in parallel is a speed win right up to the first failure, and how the harness handles that one failure decides whether the other successes survive.

Agents parallelize tool calls to cut latency: fetch three documents at once instead of one after another, query four services concurrently. That works beautifully when every call succeeds. But calls fail — a timeout, a 500, a rate limit, a bad argument to one of them — and in a batch of several, the odds that at least one fails are not small. When it happens, the harness has to decide what to return to the model, and the easy default is the wrong one.

The easy default is fail-fast: if any call in the batch failed, the batch is an error, and the model gets nothing back. This quietly throws away every call that succeeded. The three documents that came back fine are discarded because the fourth timed out; the model sees only "the batch failed" and has to reissue all four calls. So the one flaky call poisoned the whole batch, wasting the successful work and the latency the parallel call was supposed to save — and if that one call keeps failing, the agent can loop, redoing three good calls every time to chase the one bad one.

Returning partial results is the fix. Hand back every successful call's result and a labeled error for each failed one. Now the model sees the three documents it got plus a clear note that the fourth failed with a timeout, so it can do the sensible thing: proceed with what it has, retry only the one that failed, or adapt its plan. The successes are preserved and the failure is surfaced — surfaced, not swallowed, because the agent must know a call failed to handle it. A parallel batch is a bag of independent results, not an all-or-nothing transaction, and treating it as the latter throws away most of the batch on any single failure.

On the fixture, a batch of 4 parallel calls has 3 succeed and 1 fail. Fail-fast delivers 0 usable results and wastes all 3 successes. Partial-results delivers the 3 successes plus 1 labeled error, so the agent keeps the work and knows exactly what to retry.

**A parallel tool batch is a set of independent results, so fail-fast — aborting the whole batch on any failure — discards every success and forces a full redo; returning partial results (every success plus a labeled error per failure) preserves the work and surfaces the failure so the agent can retry only what failed.**

## Concepts

The core question is whether the calls in a batch are independent or coupled, and parallel tool calls are almost always independent. When an agent issues several calls at once, it does so precisely because they do not depend on each other — that is what makes them parallelizable. Independent results should be delivered independently: the failure of one has no bearing on the validity of the others, so discarding the others is throwing away good data for no reason. Fail-fast is the right model only for a genuine transaction, where the calls must all succeed or all be rolled back together — which is the rare case, not the default, and if it applies the agent should have expressed it, not had it imposed by the harness's error handling.

Fail-fast's waste is worst exactly when parallelism helps most. The more calls you batch, the more time you save when they succeed — and the higher the chance at least one fails, since the batch fails if any single call does. So a large, high-value parallel batch is the most likely to be poisoned by fail-fast and the most expensive to redo. The failure probability of the batch compounds with its size while the cost of discarding it also grows with its size, so fail-fast's penalty scales up precisely where you were trying to gain the most. Partial results break that coupling: a failure costs you one call's worth of retry, not the whole batch.

<svg role="img" aria-label="As batch size grows, the chance the batch contains a failure rises and the work discarded by fail-fast rises with it" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">bigger batch → more likely to fail AND more to discard</text>
  <line x1="45" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="45" y1="40" x2="45" y2="150" stroke="var(--line)"/>
  <polyline points="70,135 160,110 250,85 340,65 430,52" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="250" y="78" font-family="var(--mono)" font-size="8" fill="var(--s2)">P(batch has a failure)</text>
  <polyline points="70,140 160,120 250,95 340,72 430,50" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="150" y="132" font-family="var(--mono)" font-size="8" fill="var(--s1)">successes discarded by fail-fast</text>
  <text x="60" y="166" font-family="var(--mono)" font-size="7" fill="var(--muted)">small batch</text>
  <text x="400" y="166" font-family="var(--mono)" font-size="7" fill="var(--muted)">large batch</text>
</svg>
^ Both the chance a batch contains a failure and the amount of successful work fail-fast throws away grow with batch size, so fail-fast penalizes exactly the large fan-outs parallelism most rewards.

Surfacing the failure, rather than silently dropping it, is the other half of the fix. It is not enough to return the successes and quietly omit the failed call — the agent would then reason over an incomplete set as if it were complete, which is its own bug (it might conclude a document does not exist when the fetch merely timed out). The failed call must come back as an explicit, labeled error: which call failed and why. That lets the agent distinguish "this data is absent" from "this data could not be retrieved," and choose accordingly — retry, fall back, or proceed with a caveat. The delivery is successes plus errors, both visible, so the model has the full picture of what happened.

This is the same principle as partial success in any batch or fan-out API, and it generalizes. Distributed systems return per-item status for a batch write (which items committed, which failed) rather than one blanket result; a good multi-fetch returns per-URL results; parallel map operations collect both results and exceptions. The agent-harness version is to make a parallel tool batch return a per-call outcome list. The caveats are the usual ones: if the calls really are a transaction, fail-fast (or rollback) is correct; if a failure indicates a systemic problem (the whole downstream is down), a circuit breaker should cut the batch rather than retry pieces; and the agent's prompt should make clear that partial results are possible so it handles the error field. But the default for independent parallel calls is partial results, because the alternative discards work you already paid for.

**Parallel tool calls are independent by construction, so their results should be delivered independently; fail-fast couples them and wastes the most when the batch is largest, while partial results (successes plus explicit per-failure errors, both surfaced) let the agent keep the work and retry only what failed — with fail-fast reserved for genuine transactions.**

## Worked example

The fixture is a batch of parallel calls with their outcomes.

```json filename=modules/agent-harness/code/harness-inter-15/batch.json:3-8 COMPLETE
  "batch": [
    {"id": "fetch_doc_a", "ok": true},
    {"id": "fetch_doc_b", "ok": true},
    {"id": "fetch_doc_c", "ok": false, "error": "timeout after 30s"},
    {"id": "fetch_doc_d", "ok": true}
  ]
```

Four parallel document fetches; three succeeded and one (doc_c) timed out. The fail-fast delivery returns nothing if any call failed; the partial delivery returns the successes and a labeled error per failure.

```python filename=modules/agent-harness/code/harness-inter-15/partial.py:48-58 COMPLETE
def deliver_failfast(batch):
    """Any failure aborts the batch: the model gets no results and no per-call detail."""
    if failures(batch):
        return {"results": [], "errors": ["batch failed"]}
    return {"results": [c["id"] for c in batch], "errors": []}


def deliver_partial(batch):
    """Return every success and a labeled error per failure -- the model keeps the work and sees the gaps."""
    return {"results": [c["id"] for c in successes(batch)],
            "errors": ["%s: %s" % (c["id"], c["error"]) for c in failures(batch)]}
```

Both deliveries are built from the same split of the batch into successes and failures.

```python filename=modules/agent-harness/code/harness-inter-15/partial.py:40-45 COMPLETE
def successes(batch):
    return [c for c in batch if c["ok"]]


def failures(batch):
    return [c for c in batch if not c["ok"]]
```

Predict: fail-fast returns an empty result list and a generic "batch failed"; partial returns the three successful ids and one labeled timeout error. Look at the batch, then the deliveries.

```text filename=modules/agent-harness/code/harness-inter-15/partial.py --batch
BATCH — outcome of each parallel call
------------------------------------------------
  fetch_doc_a ok
  fetch_doc_b ok
  fetch_doc_c FAILED  (timeout after 30s)
  fetch_doc_d ok
------------------------------------------------
  3 of 4 succeeded.
```

Three of four calls succeeded — most of the work is done and sitting there, ready to use. Only doc_c failed, and it failed for a specific, actionable reason (a timeout). Now what each policy hands the model.

```text filename=modules/agent-harness/code/harness-inter-15/partial.py --deliver
DELIVER — what each policy hands the model
----------------------------------------------------------
  fail-fast:  results []   errors ['batch failed']
  partial:    results ['fetch_doc_a', 'fetch_doc_b', 'fetch_doc_d']   errors ['fetch_doc_c: timeout after 30s']
----------------------------------------------------------
  fail-fast delivers nothing usable; partial delivers the successes.
```

Fail-fast hands back an empty result list and a single opaque "batch failed" — the model learns nothing about what succeeded or why anything failed, and has to reissue all four calls, redoing three that were already done. Partial hands back the three successful document ids and one labeled error, "fetch_doc_c: timeout after 30s." The model keeps doc_a, doc_b, and doc_d, and knows precisely that doc_c timed out, so it can retry just doc_c (perhaps with a longer timeout) or proceed with three of four. Same batch, same single failure; fail-fast lost three results and the diagnosis, partial kept both.

<svg role="img" aria-label="A batch of four calls with three green successes and one red failure; fail-fast delivers an empty box, partial delivers the three successes plus a labeled error" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">4 parallel calls: 3 ok, 1 failed → what the model gets</text>
  <g font-family="var(--mono)" font-size="7">
    <rect x="30" y="34" width="60" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="38" y="48" fill="var(--acc-ink)">doc_a ok</text>
    <rect x="96" y="34" width="60" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="104" y="48" fill="var(--acc-ink)">doc_b ok</text>
    <rect x="162" y="34" width="60" height="20" fill="var(--panel)" stroke="var(--s2)"/><text x="168" y="48" fill="var(--s2)">doc_c FAIL</text>
    <rect x="228" y="34" width="60" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="236" y="48" fill="var(--acc-ink)">doc_d ok</text>
  </g>
  <text x="30" y="86" font-family="var(--mono)" font-size="8" fill="var(--s2)">fail-fast →</text>
  <rect x="110" y="74" width="120" height="22" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="118" y="89" font-family="var(--mono)" font-size="7" fill="var(--s2)">[]  "batch failed"</text>
  <text x="240" y="89" font-family="var(--mono)" font-size="7" fill="var(--s2)">3 successes discarded</text>
  <text x="30" y="132" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">partial →</text>
  <rect x="110" y="120" width="230" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="118" y="135" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">[a, b, d] + err(doc_c: timeout)</text>
  <text x="30" y="170" font-family="var(--mono)" font-size="8" fill="var(--muted)">partial keeps the 3 results and says exactly what to retry</text>
</svg>
^ Fail-fast reduces three successes and a failure to an empty result and a generic error; partial keeps the three successes and surfaces the one failure with its reason.

## Build

Reproduce the deliveries. Pure standard library, deterministic, so the empty fail-fast result and the three-plus-one partial result come out exactly.

Run `--batch` for the outcomes, `--deliver` for the two policies, `--check` for the gate. The remaining flags confirm the failure is surfaced (not dropped) and that partial simply delivers more.

```python filename=modules/agent-harness/code/harness-inter-15/partial.py:101-105 COMPLETE
    partial_surfaces_failures = len(pr["errors"]) == n_fail and n_fail > 0
    print("  partial surfaces each failure as a labeled error = %s (%s)" % (partial_surfaces_failures, pr["errors"]))

    partial_beats_failfast = len(pr["results"]) > len(ff["results"])
    print("  partial delivers more usable results than fail-fast = %s (%d vs %d)" % (partial_beats_failfast, len(pr["results"]), len(ff["results"])))
```

<svg role="img" aria-label="Bar chart of usable results delivered to the model: fail-fast 0, partial 3" viewBox="0 0 470 150" width="470" height="150">
  <rect x="0" y="0" width="470" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">usable results delivered (of 3 successes)</text>
  <line x1="60" y1="120" x2="450" y2="120" stroke="var(--line)"/>
  <rect x="90" y="117" width="90" height="3" fill="var(--s2)"/>
  <text x="95" y="111" font-family="var(--mono)" font-size="9" fill="var(--s2)">fail-fast: 0</text>
  <rect x="290" y="45" width="90" height="75" fill="var(--acc-line)"/>
  <text x="295" y="39" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">partial: 3</text>
  <text x="150" y="140" font-family="var(--mono)" font-size="8" fill="var(--muted)">same batch, same one failure — fail-fast keeps none, partial keeps three</text>
</svg>
^ Fail-fast delivers zero usable results from a batch where three of four calls succeeded; partial delivers all three, from the identical outcomes.

The self-test pins that fail-fast delivers nothing and wastes the successes, while partial delivers them and surfaces the failure.

```python filename=modules/agent-harness/code/harness-inter-15/partial.py:92-98 COMPLETE
    failfast_delivers_nothing = len(ff["results"]) == 0 and n_fail > 0
    print("  fail-fast delivers nothing usable when any call fails = %s (results %s)" % (failfast_delivers_nothing, ff["results"]))

    failfast_wastes_successes = n_success - len(ff["results"]) == n_success
    print("  fail-fast wastes all %d successful calls = %s" % (n_success, failfast_wastes_successes))

    partial_delivers_successes = len(pr["results"]) == n_success
    print("  partial delivers every successful result = %s (%d)" % (partial_delivers_successes, len(pr["results"])))
```

```text filename=modules/agent-harness/code/harness-inter-15/partial.py --check
SELF-TEST — fail-fast discards the successes; partial-results keeps them and surfaces the failure
------------------------------------------------------------------------------------------------
  fail-fast delivers nothing usable when any call fails = True (results [])
  fail-fast wastes all 3 successful calls = True
  partial delivers every successful result = True (3)
  partial surfaces each failure as a labeled error = True (['fetch_doc_c: timeout after 30s'])
  partial delivers more usable results than fail-fast = True (3 vs 0)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  failfast_delivers_nothing=True  failfast_wastes_successes=True  partial_delivers_successes=True  partial_surfaces_failures=True  partial_beats_failfast=True
```

Five True flags. Failfast_delivers_nothing: with one failure, fail-fast returns an empty result list. Failfast_wastes_successes: all 3 successful calls are discarded. Partial_delivers_successes: partial returns all 3. Partial_surfaces_failures: the failure comes back as a labeled error, not silently dropped. Partial_beats_failfast: 3 usable results versus 0. The surfaced-failure flag matters because it distinguishes partial results from silently ignoring the failure — the agent gets the successes and the specific diagnosis, which is what lets it act correctly rather than reason over an incomplete set.

**The surfaced-failure flag is the safeguard — partial results return the successes and an explicit labeled error, so the agent knows a call failed rather than mistaking missing data for absent data, which is why partial results must surface failures, not just drop them.**

## Definition of done

You are done when you reproduce the discarded successes and the partial delivery, and can explain when each policy is right.

Concretely: `--deliver` shows fail-fast returning an empty result and "batch failed" while partial returns the three ids and the labeled timeout error; `--check` prints PASS with five True flags. You can explain that parallel tool calls are independent by construction so their results should be delivered independently, that fail-fast wastes the most exactly when the batch is largest (highest failure odds and highest redo cost), and that partial results must surface each failure as an explicit error so the agent distinguishes "absent" from "could not retrieve." You can name when fail-fast is correct (a genuine transaction) and the companions (circuit breaker for systemic failure, a prompt that tells the agent partial results are possible).

The habit to carry: make a parallel tool batch return per-call outcomes — every success plus a labeled error for every failure — rather than aborting the whole batch on one failure, and reserve fail-fast for calls that truly must all-or-nothing together. When an agent redoes a whole set of tool calls because one keeps failing, or reasons as if a timed-out fetch returned "nothing found," suspect a fail-fast batch that discarded the successes or swallowed the failure. Deliver the parts.

## Boss fight

The instructive failure is an agent that loops forever because one of its parallel fetches keeps timing out.

A research agent fetches ten sources in parallel for each step, and the harness fails the whole batch if any fetch errors. One flaky source times out intermittently, so on many steps the batch "fails," the agent gets nothing, and it reissues all ten fetches — nine of which succeeded moments ago — burning latency and budget, and sometimes looping on the same step because the flaky source keeps failing. Nothing is actually broken except the error handling. The fix is partial results: return the nine successful fetches and a labeled error for the flaky one, so the agent proceeds with nine sources (or retries just the one), and add a circuit breaker so a persistently-failing source is dropped rather than retried forever. The tell is an agent redoing large batches of tool calls repeatedly with only one call actually failing.

Your turn, two moves. First, scale the waste: make the batch 10 calls with 1 failure and confirm fail-fast discards 9 successes while partial keeps them — the larger the batch, the more fail-fast throws away, which is why big parallel fan-outs are the most damaged by it. Second, add the transaction exception: mark the calls as a coupled transaction (all must succeed to be meaningful) and confirm fail-fast is now the correct policy — showing that partial results is the default for independent calls, not a universal rule, and that the harness needs to know which kind of batch it is handling.

## External resources

Batch and fan-out API designs that return per-item status (Google's and AWS's batch-operation responses, GraphQL partial results with an errors array) are the general pattern this module applies to tool calls — deliver each item's outcome rather than one blanket success or failure.

Agent-framework documentation on parallel tool execution (LangGraph, the OpenAI and Anthropic tool-use guides) discusses returning individual tool results and errors so the model can handle partial failure, which is the harness-level form of this pattern.

Writing on error handling in concurrent and distributed systems (partial failure, the "return results and errors together" idiom in Go's errgroup, Promise.allSettled versus Promise.all in JavaScript) frames the general choice between all-or-nothing and per-item outcomes that this module makes concrete for an agent.
