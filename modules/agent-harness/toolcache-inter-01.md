---
id: toolcache-inter-01
title: Cache read-only tool results in a session — an agent re-reads the same things constantly, but never cache a mutating or time-sensitive tool
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: Agents are repetitive: over a single task a model re-reads a file it read three steps ago, re-fetches a document it already fetched, re-queries the same record — because its working memory is the conversation, and rebuilding context often means asking for the same information again. Each repeated call, if executed, pays the full cost again: the network round-trip, the tool's latency, the tokens to shuttle the result back. For a read-only tool whose answer has not changed, that is pure waste, because the harness already has the answer. Caching removes it: key each result by (tool, arguments) and serve a repeat from the store instead of re-executing; the model asked the identical question, so the identical answer is correct and arrives instantly, transparently — a cached read-only result is indistinguishable from a fresh one. The hard rule is what you may cache: only tools that are read-only and deterministic within the session, whose result depends solely on the arguments and does not change between calls. A mutating tool (write a file, send a message, charge a card) must execute every time because its point is the side effect; serving it from cache would silently skip the real action. A time-sensitive or non-deterministic tool (current time, a random value, a live price) must also execute every time, because a cached answer would be stale. So each tool is declared cacheable or not, and the harness caches only the cacheable ones. On a fixture of 7 calls including get_file(a) three times, no caching runs all 7 while caching serves the 2 repeated get_file(a) calls from the cache (2 hits) for 5 executions, and current_time and write_file — not cacheable — still execute every time.
eli5: Imagine you have an assistant who keeps asking the librarian for the same book you already borrowed an hour ago. Every trip to the librarian takes time. A smart assistant keeps a little shelf: the first time they fetch a book, they put a copy on the shelf, and next time you ask for that same book they just hand it over instantly instead of walking back to the library. That works great for books, which don't change. But it would be a terrible idea for "what time is it?" (the answer keeps changing) or for "mail this letter" (you actually have to walk to the mailbox each time, or the letter never gets sent). So the assistant only shelves the things that stay the same, and always makes the trip for the things that change or that have to actually happen.
---

## Why this module

Latency and token cost are the two budgets an agent harness spends fastest, and agents spend them wastefully in a specific, predictable way: they ask for the same thing repeatedly. This is not a bug in any one model; it is structural. The model's only memory is the context window, so as a task unfolds it re-derives what it needs, and re-deriving frequently means re-issuing a tool call it already made — re-reading the config, re-listing the directory, re-fetching the record. Every one of those, executed again, is a round-trip and a block of tokens for information the harness is already holding.

Caching is the standard fix, and it is nearly free when it applies, because the correctness argument is trivial: for a pure read-only tool, the answer to the same question is the same answer, so returning the stored one is not an approximation, it is exact. The savings scale with how repetitive the agent is, which is to say substantially.

The entire difficulty is knowing which tools qualify, and getting it wrong is not a performance regression but a correctness bug. This module runs a session with a mix of cacheable and non-cacheable calls and shows caching serving the safe repeats while the unsafe ones always execute.

**Cache the results of read-only, deterministic tool calls keyed by (tool, arguments) and serve repeats from the cache, while executing mutating and time-sensitive tools every time, because agents frequently re-request identical information — so caching read-only results removes redundant round-trips at no correctness cost, whereas caching a mutating tool would skip its side effect and caching a time-sensitive one would return a stale result.**

## Concepts

The fixture is a session of seven calls. get_file is read-only (cacheable) and is called for `a` three times and `b` once; current_time (time-sensitive) and write_file (mutating) are not cacheable.

```json filename=modules/agent-harness/code/toolcache-inter-01/toolcache.json:3-6 COMPLETE
  "calls": [
    {"tool": "get_file", "args": "a", "cacheable": true},
    {"tool": "get_file", "args": "b", "cacheable": true},
    {"tool": "get_file", "args": "a", "cacheable": true},
```

The cache is keyed by (tool, arguments). The classify step decides each call's fate: a non-cacheable call always executes; a cacheable call executes on its first occurrence (cache miss) and is served from the cache on repeats (cache hit).

```python filename=modules/agent-harness/code/toolcache-inter-01/toolcache.py:32-48 COMPLETE
def key(call):
    return (call["tool"], call["args"])


def classify(calls):
    """For each call decide: execute fresh, serve from cache, or execute (non-cacheable). Returns per-call actions."""
    seen = set()
    actions = []
    for c in calls:
        if not c["cacheable"]:
            actions.append("execute (not cacheable)")
        elif key(c) in seen:
            actions.append("cache hit")
        else:
            seen.add(key(c))
            actions.append("execute (cache miss)")
    return actions
```

The counts follow directly: without caching every call executes; with caching only the misses and the non-cacheable calls execute, and the difference is the cache hits.

```python filename=modules/agent-harness/code/toolcache-inter-01/toolcache.py:51-60 COMPLETE
def no_cache_executions(calls):
    return len(calls)


def cached_executions(calls):
    return sum(1 for a in classify(calls) if a.startswith("execute"))


def cache_hits(calls):
    return sum(1 for a in classify(calls) if a == "cache hit")
```

<svg role="img" aria-label="A stream of seven calls flowing through a cache: cacheable repeats diverted to a cache store as hits, non-cacheable calls passing straight through to execute" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">calls → cache gate</text>
  <g font-size="7">
  <rect x="14" y="24" width="70" height="13" fill="var(--s1)"/><text x="18" y="34" fill="var(--panel)">get_file a (miss)</text>
  <rect x="14" y="39" width="70" height="13" fill="var(--s1)"/><text x="18" y="49" fill="var(--panel)">get_file b (miss)</text>
  <rect x="14" y="54" width="70" height="13" fill="var(--s2)"/><text x="18" y="64" fill="var(--panel)">get_file a (HIT)</text>
  <rect x="14" y="69" width="70" height="13" fill="var(--muted)"/><text x="18" y="79" fill="var(--panel)">current_time</text>
  <rect x="14" y="84" width="70" height="13" fill="var(--s2)"/><text x="18" y="94" fill="var(--panel)">get_file a (HIT)</text>
  <rect x="14" y="99" width="70" height="13" fill="var(--muted)"/><text x="18" y="109" fill="var(--panel)">write_file a</text>
  </g>
  <rect x="150" y="30" width="40" height="70" fill="none" stroke="var(--ink)" stroke-width="1.5"/><text x="156" y="68" font-size="8" fill="var(--ink)">cache</text>
  <rect x="250" y="40" width="60" height="18" fill="var(--s1)"/><text x="258" y="53" font-size="7.5" fill="var(--panel)">execute (5)</text>
  <rect x="250" y="72" width="60" height="18" fill="var(--s2)"/><text x="258" y="85" font-size="7.5" fill="var(--panel)">served (2)</text>
</svg>
^ Cacheable first-calls execute and populate the cache; repeats (the two get_file a) are served from it; non-cacheable calls (current_time, write_file) pass straight through and always execute. Seven calls, five executions, two hits.

**The cache turns repeated read-only questions into instant answers the harness already holds — the only judgment is which tools may answer from memory and which must always do the work.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the tool-dispatch step of an agent harness, reduced to a seven-call session so every cache decision is checkable by hand.

Run `--calls` to see each call and the caching harness's action.

```text filename=toolcache.py --calls
  #  tool          args  cacheable  action
  0  get_file      a     True       execute (cache miss)
  1  get_file      b     True       execute (cache miss)
  2  get_file      a     True       cache hit
  3  current_time        False      execute (not cacheable)
  4  get_file      a     True       cache hit
  5  current_time        False      execute (not cacheable)
  6  write_file    a     False      execute (not cacheable)
```

The first get_file(a) and get_file(b) are misses — they execute and populate the cache. The second and third get_file(a) calls (rows 2 and 4) are cache hits — served instantly, no round-trip. The two current_time calls and the write_file both execute every time, because they are not cacheable: current_time would go stale, and write_file has a side effect that must actually happen. Note row 4 is a hit even though a current_time call happened in between — the cache persists across the session, so unrelated calls do not invalidate it.

Now `--savings` totals it up.

```text filename=toolcache.py --savings
  no caching:  7 executions (every call runs)
  with cache:  5 executions (2 cache hits saved)
  non-cacheable calls that still run every time: 3 (mutating / time-sensitive)
```

Without caching, all seven calls execute. With caching, five execute and two are served from the cache — the two repeated get_file(a) calls, saved. The three non-cacheable calls (two current_time, one write_file) still run every time, correctly. The saving is exactly the repeated read-only work; the correctness-critical calls are untouched.

**Caching cut executions from 7 to 5 by serving the two repeated get_file(a) reads from the cache, while every mutating and time-sensitive call still ran — the savings came entirely from safe repeats.**

## Build

The self-test asserts the savings and the safety: the session repeats a cacheable call, caching reduces executions, and the saved count equals the cache hits (nothing is dropped, only deduplicated).

```python filename=modules/agent-harness/code/toolcache-inter-01/toolcache.py:94-104 COMPLETE
    has_repeated_cacheable = cache_hits(calls) > 0
    print("  the session repeats a cacheable call = %s (%d cache hit(s))" % (has_repeated_cacheable, cache_hits(calls)))

    cache_reduces_executions = cached_executions(calls) < no_cache_executions(calls)
    print("  caching reduces total executions = %s (%d < %d)" % (cache_reduces_executions, cached_executions(calls), no_cache_executions(calls)))

    savings_equals_hits = no_cache_executions(calls) - cached_executions(calls) == cache_hits(calls)
    print("  the executions saved equal the cache hits = %s (%d saved)" % (savings_equals_hits, no_cache_executions(calls) - cached_executions(calls)))

    noncacheable_always_runs = all(actions[i].startswith("execute") for i, c in enumerate(calls) if not c["cacheable"])
    print("  every non-cacheable call executes (never cached) = %s" % noncacheable_always_runs)
```

<svg role="img" aria-label="Two execution bars: no caching 7, with caching 5, with the 2-execution gap labeled as cache hits and a note that non-cacheable calls always run" viewBox="0 0 320 100">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">tool executions</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s2)">no caching</text>
  <rect x="90" y="30" width="210" height="16" fill="var(--s2)"/><text x="278" y="43" font-size="8" fill="var(--panel)">7</text>
  <text x="10" y="68" font-size="8.5" fill="var(--s1)">with cache</text>
  <rect x="90" y="58" width="150" height="16" fill="var(--s1)"/><text x="218" y="71" font-size="8" fill="var(--panel)">5</text>
  <rect x="240" y="58" width="60" height="16" fill="none" stroke="var(--s2)" stroke-dasharray="2 2"/><text x="248" y="71" font-size="7" fill="var(--muted)">2 hits</text>
  <text x="10" y="92" font-size="7.5" fill="var(--muted)">the 2 saved are repeated reads; the 3 non-cacheable calls always run</text>
</svg>
^ Caching shrinks executions from 7 to 5; the two-execution gap is exactly the cache hits (repeated reads). The non-cacheable calls are inside the 5 — they always run.

Running the check confirms every clause, including that the first call of each key still executes and the time-sensitive tool is never served stale.

```text filename=toolcache.py --check
  the session repeats a cacheable call = True (2 cache hit(s))
  caching reduces total executions = True (5 < 7)
  the executions saved equal the cache hits = True (2 saved)
  every non-cacheable call executes (never cached) = True
  the first call of each cacheable key still executes (cache miss) = True
  the time-sensitive tool is never served stale from cache = True
```

**The check ties the saving to the cache hits (safe repeats only) and pins that non-cacheable calls always execute — so caching removes redundant reads without ever skipping a side effect or serving a stale time.**

## Definition of done

Two properties close it. The first call of each cacheable key must still execute (the cache is populated by real work, not invented), and the time-sensitive tool must never be served from the cache. The second is the correctness boundary: caching only reads, never a tool whose answer changes or whose purpose is a side effect.

```python filename=modules/agent-harness/code/toolcache-inter-01/toolcache.py:106-111 COMPLETE
    only_repeats_cached = all(actions[i] == "cache hit" for i, c in enumerate(calls) if actions[i] == "cache hit" and c["cacheable"])
    first_of_each_executes = actions[0] == "execute (cache miss)"
    print("  the first call of each cacheable key still executes (cache miss) = %s" % first_of_each_executes)

    time_tool_not_cached = all(actions[i].startswith("execute") for i, c in enumerate(calls) if c["tool"] == "current_time")
    print("  the time-sensitive tool is never served stale from cache = %s" % time_tool_not_cached)
```

Three refinements keep the cache safe. First, cacheability is a per-tool declaration, not a guess — the tool author marks a tool read-only-and-deterministic, and the harness caches only those; defaulting to "cache everything" is the dangerous mistake, because it silently breaks mutating and time-sensitive tools. Second, "deterministic within the session" has a scope: a read-only tool whose underlying data can change (read a file that another process might write) is only safely cacheable if nothing in the session mutates it — the conservative rule is to invalidate a read's cache entry when a mutating call touches the same resource (a write_file(a) should evict get_file(a)), or to scope the cache to a single turn where staleness cannot bite. This fixture's write_file(a) coming last means it does not corrupt the earlier reads, but a real harness must handle a write-then-read. Third, the cache key must capture everything the result depends on — the arguments and any relevant context (the user, the permissions); a key that omits a dependency serves one caller another's cached result. Within those bounds, read-only tool caching is one of the cheapest wins available: exact results, fewer round-trips, lower cost.

<svg role="img" aria-label="A decision: read-only and deterministic tools are cacheable, mutating tools and time-sensitive tools are not" viewBox="0 0 320 120">
  <rect x="110" y="12" width="100" height="22" fill="none" stroke="var(--ink)" stroke-width="1"/><text x="118" y="27" font-size="8" fill="var(--ink)">may I cache it?</text>
  <line x1="140" y1="34" x2="70" y2="56" stroke="var(--s1)" stroke-width="1"/>
  <line x1="180" y1="34" x2="250" y2="56" stroke="var(--s2)" stroke-width="1"/>
  <rect x="20" y="58" width="110" height="20" fill="var(--s1)"/><text x="26" y="72" font-size="7.5" fill="var(--panel)">read-only + deterministic</text>
  <text x="40" y="92" font-size="7.5" fill="var(--s1)">→ cache (get_file)</text>
  <rect x="195" y="58" width="110" height="20" fill="var(--s2)"/><text x="200" y="72" font-size="7.5" fill="var(--panel)">mutating / time-sensitive</text>
  <text x="205" y="92" font-size="7.5" fill="var(--s2)">→ always execute</text>
  <text x="20" y="112" font-size="7.5" fill="var(--ink)">default is do-not-cache; cacheable tools opt in — the safe direction to err</text>
</svg>
^ Only read-only, deterministic tools are cacheable; mutating tools (side effects) and time-sensitive tools (changing answers) always execute. The default must be do-not-cache, with cacheable tools opting in — erring toward executing is safe, erring toward caching corrupts.

**Done means caching serves only repeated read-only calls (misses populate it, hits reuse it) while every mutating and time-sensitive call executes — an exact, transparent saving whose safety rests on per-tool cacheability and proper invalidation.**

## Boss fight

An agent framework adds a global result cache to speed things up: every tool call's result is cached by (tool, args) and repeats are served from the cache. Latency improves, but users start reporting bizarre bugs — an agent says a file has content it no longer has after editing it, an agent reports the same "current price" for an hour, and once an agent's "send notification" appeared to succeed but no notification arrived. What went wrong, and how should the cache be fixed?

The framework cached everything, including tools that must never be cached, and each reported bug is one class of that mistake. The stale file content is a read-then-write invalidation failure: the agent read the file (cached), edited it (a mutating call that should have evicted the cached read), and then a later read was served the old cached content — the cache had no invalidation when the underlying resource changed. The frozen "current price" is a time-sensitive tool being cached: its result is only valid at the instant it is called, so serving a cached value returns a stale answer that was true once and is now wrong. The phantom notification is the most dangerous: a mutating tool (send notification) was served from the cache on a repeat, so the harness skipped the actual side effect and reported the cached "success" without anything being sent. The fix is to make cacheability a per-tool property, not a global default: mark only read-only, deterministic tools cacheable, and never cache mutating tools (they must execute every time for their side effect) or time-sensitive/non-deterministic ones (they must execute for a fresh answer). Then add invalidation: when a mutating call touches a resource, evict cached reads of that resource (write_file(x) evicts get_file(x)), or scope read caches narrowly enough (per turn, or with short TTLs) that staleness cannot accumulate. And ensure the cache key includes everything the result depends on — arguments plus user/permission context — so one caller never receives another's cached result. The default must be "do not cache" with cacheable tools opting in, the opposite of the framework's "cache everything."

## External resources

The literature and framework docs on agent tool-result caching (LangChain/LlamaIndex caching layers, and general memoization patterns) — practical guidance on caching read-only tool and LLM calls, cache keys, and TTLs.

HTTP caching semantics (RFC 9111) on cacheability, safe vs unsafe methods, and cache invalidation — the mature model this pattern mirrors: GET (safe, cacheable) versus POST/PUT/DELETE (unsafe, must not be served from cache and invalidate related entries), the same read-only-vs-mutating distinction applied to tools.
