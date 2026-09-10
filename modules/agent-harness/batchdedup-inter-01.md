---
id: batchdedup-inter-01
title: Collapse the model's duplicate parallel tool calls in one turn — executing each twice wastes budget and doubles effects
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A tool-calling model can emit several tool calls at once, to run in parallel, and it is not always tidy: in a single batch it sometimes asks for the same call more than once — the identical tool with identical arguments — because it listed the call under two lines of reasoning or lost track. A naive harness dispatches every call as written, so those duplicates each execute. For a read-only tool that is merely wasteful: twice the latency and twice the budget to fetch the same answer. For a tool with side effects it is worse — running send_email or create_ticket twice because the model listed it twice sends two emails, files two tickets. Deduplication fixes this within the batch: compute a signature for each call (the tool name plus its arguments, canonicalized so argument order does not matter), group by signature, execute each unique signature exactly once, and fan the single result back to every call position that shares it. The model still receives one result per call it emitted (the shapes line up) while the number of executions drops to the number of distinct calls. This is distinct from caching across turns and from retry dedup: it collapses the redundancy within one parallel batch, before anything runs. On a fixture where the model emits 5 calls of which 2 are duplicates (a repeated search and a repeated get-time), a naive harness runs all 5, while dedup runs the 3 unique calls once each and fans the results to all 5 slots — 3 executions, 5 results, 2 saved.
eli5: Imagine you send a runner to fetch things and hand them a list, but you accidentally wrote "get milk" twice and "get bread" once and "get eggs" once — five lines, but only three different things. A careless runner makes the trip and buys milk twice, paying double and coming back with two cartons. A smart runner reads the list, notices "get milk" is on there twice, buys one milk, and when they get back they can tick off both "get milk" lines with the same carton. You still get every line on your list checked off — you just didn't pay for the same thing twice. And if the errand were "mail this letter," doing it twice would actually send two letters, which is a real mistake, not just wasted money.
---

## Why this module

Parallel tool calls are a performance win, but they hand the harness a list the model wrote in a hurry, and that list can contain the same call twice. The model does not have a guarantee against repeating itself — it might mention the same lookup under two separate thoughts, or emit a call, reconsider, and emit it again — so a batch of five calls can contain only three distinct actions. A harness that treats the batch as a literal to-do list executes all five, which for a read is paying twice for one answer and for a write is performing an action the user asked for once, twice. The redundancy is right there in the batch, visible before anything runs, and the naive harness runs it anyway.

A naive harness dispatches every call in the batch as written, so those duplicate calls each execute. For a read-only tool that is merely wasteful — twice the latency and twice the token/compute budget to fetch the same answer. For a tool with side effects it is worse than wasteful: running send_email or create_ticket twice because the model listed it twice sends two emails, files two tickets.

Deduplication fixes this within the batch. Compute a signature for each call — the tool name plus its arguments, canonicalized so argument order does not matter — group the calls by signature, execute each unique signature exactly once, and fan the single result back to every position that shares it. Five emitted calls with two duplicates become three executions and five results. This module runs both.

**Within a single turn's batch of parallel tool calls, deduplicate by signature (tool + canonicalized arguments) — execute each unique call once and fan its result back to every slot that shares the signature — because dispatching a duplicate call the batch already contains wastes latency and budget and, for a tool with side effects, performs the action twice.**

## Concepts

**A call's signature is its tool plus canonicalized arguments**, and the naive harness simply executes every call's signature — duplicates included.

```python filename=modules/agent-harness/code/batchdedup-inter-01/batchdedup.py:53-61 COMPLETE
def signature(call):
    """A canonical signature: tool name plus arguments serialized with sorted keys (order-independent)."""
    return call["tool"] + "(" + json.dumps(call["args"], sort_keys=True) + ")"


def run_naive(calls):
    """Execute every call in the batch as written -- duplicates included."""
    executed = [signature(c) for c in calls]
    return executed
```

**Dedup executes each unseen signature once and fans the result to every slot** that shares it, preserving one result per emitted call.

```python filename=modules/agent-harness/code/batchdedup-inter-01/batchdedup.py:64-75 COMPLETE
def run_dedup(calls):
    """Execute each unique signature once; fan the result back to every slot that shares it."""
    first_seen = {}
    executed = []
    results = [None] * len(calls)
    for i, c in enumerate(calls):
        sig = signature(c)
        if sig not in first_seen:
            first_seen[sig] = "result_of(%s)" % sig
            executed.append(sig)          # actually dispatched
        results[i] = first_seen[sig]      # fan the (possibly reused) result into this slot
    return executed, results
```

<svg role="img" aria-label="Five emitted calls on the left grouped by signature into three unique executions on the right; two pairs of duplicate calls collapse to one execution each" viewBox="0 0 300 122" width="300" height="122">
  <text x="6" y="12" fill="var(--muted)" font-size="8">5 emitted calls → 3 unique signatures executed</text>
  <text x="10" y="28" fill="var(--muted)" font-size="7">emitted</text>
  <rect x="20" y="34" width="80" height="12" fill="var(--s2)"/><text x="24" y="43" fill="var(--panel)" font-size="6">0 search weather</text>
  <rect x="20" y="48" width="80" height="12" fill="var(--s1)"/><text x="24" y="57" fill="var(--panel)" font-size="6">1 time NYC</text>
  <rect x="20" y="62" width="80" height="12" fill="var(--s2)"/><text x="24" y="71" fill="var(--panel)" font-size="6">2 search weather</text>
  <rect x="20" y="76" width="80" height="12" fill="var(--ink)"/><text x="24" y="85" fill="var(--panel)" font-size="6">3 search news</text>
  <rect x="20" y="90" width="80" height="12" fill="var(--s1)"/><text x="24" y="99" fill="var(--panel)" font-size="6">4 time NYC</text>
  <text x="190" y="28" fill="var(--muted)" font-size="7">executed</text>
  <rect x="190" y="40" width="90" height="14" fill="var(--s2)"/><text x="194" y="50" fill="var(--panel)" font-size="6">search weather ×1</text>
  <rect x="190" y="58" width="90" height="14" fill="var(--s1)"/><text x="194" y="68" fill="var(--panel)" font-size="6">time NYC ×1</text>
  <rect x="190" y="76" width="90" height="14" fill="var(--ink)"/><text x="194" y="86" fill="var(--panel)" font-size="6">search news ×1</text>
  <path d="M100 40 L188 46" stroke="var(--s2)" fill="none"/><path d="M100 68 L188 46" stroke="var(--s2)" fill="none"/>
  <path d="M100 54 L188 64" stroke="var(--s1)" fill="none"/><path d="M100 96 L188 64" stroke="var(--s1)" fill="none"/>
  <path d="M100 82 L188 82" stroke="var(--ink)" fill="none"/>
  <text x="14" y="116" fill="var(--muted)" font-size="6">the two weather calls and the two time calls each collapse to one execution</text>
</svg>
^ The five emitted calls group by signature into three unique executions: the two "search weather" calls (0 and 2) collapse to one, the two "time NYC" calls (1 and 4) collapse to one, and "search news" (3) is alone — so three calls run where a naive harness would run five.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/batchdedup-inter-01/batchdedup.py

The fixture is the batch of five parallel calls the model emitted, two of them duplicates.

```json filename=modules/agent-harness/code/batchdedup-inter-01/batchdedup.json:3-9 COMPLETE
  "calls": [
    {"tool": "search", "args": {"q": "weather"}},
    {"tool": "get_time", "args": {"city": "NYC"}},
    {"tool": "search", "args": {"q": "weather"}},
    {"tool": "search", "args": {"q": "news"}},
    {"tool": "get_time", "args": {"city": "NYC"}}
  ]
```

Run `--calls`.

```text filename=--calls
CALLS — the batch the model emitted, with each call's signature
--------------------------------------------------------------------------
  call 0: search({"q": "weather"})
  call 1: get_time({"city": "NYC"})
  call 2: search({"q": "weather"})  <- duplicate of an earlier call
  call 3: search({"q": "news"})
  call 4: get_time({"city": "NYC"})  <- duplicate of an earlier call
--------------------------------------------------------------------------
  5 calls emitted; 3 distinct signatures.
```

Read the signatures. Call 0 and call 2 both reduce to `search({"q": "weather"})` — they are byte-for-byte the same request, so call 2 is flagged a duplicate of call 0. Call 1 and call 4 both reduce to `get_time({"city": "NYC"})`, so call 4 is a duplicate of call 1. Call 3, `search({"q": "news"})`, is unique. Five calls, three distinct signatures. The signature is what makes this detectable: it canonicalizes each call to a comparable string, serializing the arguments with sorted keys so that `{"q": "weather"}` and a differently-ordered but identical argument dict would still match — and, crucially, so that genuinely different arguments (`weather` vs `news`) do not collide. The duplicates are not a subtle semantic overlap; they are literally the same call, which is exactly the case dedup should and safely can collapse.

## Build

Now dispatch the batch both ways and watch the execution count.

```text filename=--execute
EXECUTE — naive dispatch vs dedup
----------------------------------------------------------------------
  NAIVE:  executes 5 calls: ['search({"q": "weather"})', 'get_time({"city": "NYC"})', 'search({"q": "weather"})', 'search({"q": "news"})', 'get_time({"city": "NYC"})']
  DEDUP:  executes 3 calls: ['search({"q": "weather"})', 'get_time({"city": "NYC"})', 'search({"q": "news"})']
          results fanned to all 5 slots:
            slot 0 <- result_of(search({"q": "weather"}))
            slot 1 <- result_of(get_time({"city": "NYC"}))
            slot 2 <- result_of(search({"q": "weather"}))
            slot 3 <- result_of(search({"q": "news"}))
            slot 4 <- result_of(get_time({"city": "NYC"}))
```

<svg role="img" aria-label="Three executed results fanning out to five result slots: the search-weather result goes to slots 0 and 2, the time-NYC result to slots 1 and 4, and search-news to slot 3" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">3 results fan out to 5 slots — every emitted call is answered</text>
  <text x="10" y="28" fill="var(--muted)" font-size="7">executed (3)</text>
  <rect x="20" y="34" width="70" height="14" fill="var(--s2)"/><text x="24" y="44" fill="var(--panel)" font-size="6">weather</text>
  <rect x="20" y="56" width="70" height="14" fill="var(--s1)"/><text x="24" y="66" fill="var(--panel)" font-size="6">time NYC</text>
  <rect x="20" y="78" width="70" height="14" fill="var(--ink)"/><text x="24" y="88" fill="var(--panel)" font-size="6">news</text>
  <text x="220" y="28" fill="var(--muted)" font-size="7">slots (5)</text>
  <g font-size="6" fill="var(--muted)"><text x="220" y="40">slot 0</text><text x="220" y="54">slot 1</text><text x="220" y="68">slot 2</text><text x="220" y="82">slot 3</text><text x="220" y="96">slot 4</text></g>
  <path d="M90 41 L216 37" stroke="var(--s2)" fill="none"/><path d="M90 41 L216 65" stroke="var(--s2)" fill="none"/>
  <path d="M90 63 L216 51" stroke="var(--s1)" fill="none"/><path d="M90 63 L216 93" stroke="var(--s1)" fill="none"/>
  <path d="M90 85 L216 79" stroke="var(--ink)" fill="none"/>
</svg>
^ The three executed results fan back out to the five original slots — the weather result to slots 0 and 2, the time-NYC result to slots 1 and 4, the news result to slot 3 — so the model receives one result per call it emitted, with the deduplication invisible downstream.

The naive harness executes five calls, including the two duplicates — so `search weather` runs twice and `get_time NYC` runs twice. The dedup harness executes three, one per distinct signature, and then fans the results out: slot 0 and slot 2 both receive the single `search weather` result, slot 1 and slot 4 both receive the single `get_time NYC` result, slot 3 gets its own. The model asked for five results and got five results, in the right positions — the fan-out is invisible to it — but only three executions actually happened. This is the whole design: the deduplication is transparent downstream (the number and order of results the model sees are unchanged) and the saving is real upstream (two fewer executions, two fewer latencies, two fewer units of budget). And note the side-effect angle: if `search` were instead `send_notification`, the naive harness would have sent the same notification twice from one turn, while dedup sends it once — dedup is not merely an optimization there, it is a correctness guard against the model double-firing an effect. Preserving the slot positions in the fan-out is what makes it safe to apply as a default: nothing downstream can tell dedup happened.

```python filename=modules/agent-harness/code/batchdedup-inter-01/batchdedup.py:117-124 COMPLETE
    naive_executes_all = len(naive) == len(calls)
    print("  naive executes every call in the batch = %s (%d executions for %d calls)" % (naive_executes_all, len(naive), len(calls)))

    dedup_executes_unique = len(executed) == unique
    print("  dedup executes exactly the unique calls = %s (%d executions for %d distinct)" % (dedup_executes_unique, len(executed), unique))

    dedup_saves = len(executed) < len(naive)
    print("  dedup runs fewer executions than naive = %s (%d < %d)" % (dedup_saves, len(executed), len(naive)))
```

## Definition of done

The self-test pins the full naive execution, the unique-only dedup execution, the answered slots, and the shared duplicate results.

```python filename=modules/agent-harness/code/batchdedup-inter-01/batchdedup.py:126-130 COMPLETE
    all_slots_answered = all(r is not None for r in results) and len(results) == len(calls)
    print("  every emitted call slot still gets a result = %s (%d of %d)" % (all_slots_answered, sum(1 for r in results if r is not None), len(calls)))

    dups_share_result = results[0] == results[2] and results[1] == results[4]
    print("  duplicate slots share the single result = %s (slot0==slot2, slot1==slot4)" % dups_share_result)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive harness executes every call including duplicates; dedup executes each unique call once for all slots
----------------------------------------------------------------------------------------------------------------------------
  naive executes every call in the batch = True (5 executions for 5 calls)
  dedup executes exactly the unique calls = True (3 executions for 3 distinct)
  dedup runs fewer executions than naive = True (3 < 5)
  every emitted call slot still gets a result = True (5 of 5)
  duplicate slots share the single result = True (slot0==slot2, slot1==slot4)
```

<svg role="img" aria-label="Executions: naive runs 5, dedup runs 3, both answering all 5 slots" viewBox="0 0 300 88" width="300" height="88">
  <text x="6" y="12" fill="var(--muted)" font-size="8">executions for the same 5-call batch, both answering all 5 slots</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">naive</text>
  <g fill="var(--s2)"><rect x="70" y="26" width="16" height="14"/><rect x="90" y="26" width="16" height="14"/><rect x="110" y="26" width="16" height="14"/><rect x="130" y="26" width="16" height="14"/><rect x="150" y="26" width="16" height="14"/></g>
  <text x="172" y="37" fill="var(--muted)" font-size="7">5 executions</text>
  <text x="10" y="60" fill="var(--muted)" font-size="7">dedup</text>
  <g fill="var(--s1)"><rect x="70" y="52" width="16" height="14"/><rect x="90" y="52" width="16" height="14"/><rect x="110" y="52" width="16" height="14"/></g>
  <text x="132" y="63" fill="var(--muted)" font-size="7">3 executions (2 saved)</text>
  <text x="10" y="82" fill="var(--muted)" font-size="6">both deliver 5 results; dedup just doesn't run the same call twice</text>
</svg>
^ For the identical five-call batch, the naive harness runs five executions and the dedup harness runs three, saving two — and both deliver all five results, so dedup pays nothing downstream while cutting the redundant executions.

**Done means the batch dedup is proven on real calls: the model emitted 5 calls with 2 duplicates, and the naive harness executes all 5 while dedup executes the 3 unique signatures once each and fans them to all 5 slots (slot 0 = slot 2, slot 1 = slot 4), delivering 5 results from 3 executions — so a turn's parallel tool-call batch must be deduplicated by signature before dispatch.**

## Boss fight

Predict two ways batch dedup needs care, because "same signature" is a judgment and not every duplicate is safe to collapse the same way.

The first trap is that the signature must be canonical AND semantically correct — too loose and you merge calls that are not the same, too tight and you miss real duplicates. Canonicalization has to normalize things that do not change the call's meaning: argument key order (sorted keys, done here), and ideally value normalization where it is safe (whitespace, equivalent numeric forms), because two calls that differ only in JSON key order are the same call and should merge. But it must NOT normalize away things that do matter, and this is where it gets subtle: if a tool's behavior depends on something outside its arguments — the current time, a random seed, a per-call idempotency key the harness injects, ambient state — then two calls with identical argument signatures are NOT guaranteed to produce the same result, and merging them is wrong. So dedup-by-signature is safe exactly when the tool is a pure function of its arguments (a deterministic read), and for tools whose result depends on hidden state, the signature is an incomplete key and dedup can return a stale or wrong shared result. The correct scope is: deduplicate identical calls to deterministic tools within a batch, and be conservative about what "identical" includes.

The second trap is that side-effecting duplicates need a decision, not just a merge, because collapsing them changes behavior in a way that might or might not be what the user wanted. When the model emits `send_email(...)` twice in one batch, collapsing to one send is almost certainly right — the user asked to send one email and the model double-listed it — but "almost certainly" is not "always": there are rare cases where two identical-looking effectful calls are both intended (append the same line twice, increment a counter twice), and a blind signature-merge silently drops the second. So for effectful tools the safe posture is stronger than dedup: pair it with idempotency (each intended effect carries an idempotency key, so a genuine duplicate is a no-op at the tool and a genuinely-distinct repeat carries a distinct key), and where the model's intent is ambiguous, surface it rather than guess. Batch dedup is an unambiguous win for pure reads and a good default for effects, but for effects it is really a special case of the broader idempotency discipline — the harness should not perform an action twice from one turn, and the robust way to guarantee that is idempotency keys, with signature-dedup as the cheap first line of defense. Dedup collapses the obvious redundancy; idempotency handles the cases dedup cannot safely judge.

**Signature-dedup is only safe when "same signature" means "same result": canonicalize what doesn't change meaning (argument key order) but never merge calls to a tool whose output depends on hidden state (time, randomness, ambient state) — there the argument signature is an incomplete key. And side-effecting duplicates need a decision, not a blind merge: collapsing a double send_email is usually right but occasionally two identical effects are both intended, so pair batch dedup with idempotency keys (a genuine duplicate becomes a no-op, a genuinely-distinct repeat carries a distinct key) and surface ambiguous intent rather than silently dropping the second call.**

## External resources

Documentation for parallel/batch tool calling in agent frameworks and model APIs — how a model emits multiple tool calls in one turn, how results are returned per call id, and the position/id matching the fan-out must preserve.

Writing on request coalescing, memoization, and idempotency keys — the related patterns dedup borrows from (collapse identical work, cache pure results, make effects safe to repeat) and how they differ in scope (within-batch, across-time, across-retries).

The companion memoize-tool-results, idempotent-retry, and parallel-tool-call modules in this topic — batch dedup collapses redundancy within one turn's parallel batch, memoization caches pure results across turns, and idempotency makes effectful duplicates safe, together covering the same call requested twice in every timeframe.
