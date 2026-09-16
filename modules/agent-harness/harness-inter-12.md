---
id: harness-inter-12
title: Memoize tool results by call signature — but only pure tools, or a cached effectful call returns a stale lie
topic: agent-harness
level: intermediate
status: ready
time: 21 min
summary: An agent re-issues the same tool call constantly, so caching by call signature saves executions and gives a consistent view — but only for pure tools whose result is a function of their arguments. Caching an effectful tool freezes it: a run of 7 calls with an interleaved counter returns 1,2,3 with no cache, a frozen 1,1,1 when everything is cached (fast and wrong), and a correct 1,2,3 in just 5 executions when only the pure read is cached.
eli5: If someone asks you the same fixed fact twice, it's fine to remember your answer and repeat it. But if they ask "what number am I on now?" you can't repeat your old answer — the number changed. A shortcut that remembers answers is safe only for questions whose answer never changes.
---

## Why this module

Caching an agent's tool calls is nearly free money, right up until you cache the one tool whose answer was supposed to change.

An agent loop re-issues the same tool call over and over. It reads the same config file at the start of every step, looks up the same record after each action, checks the same setting three times in one run. Each call is a round-trip and a chunk of tokens, and many of them are byte-for-byte identical. The obvious optimization is a cache keyed by the call signature — the tool name plus its arguments: the first call executes and stores its result, every identical call after that returns the stored result without executing. For the config read, this is pure win — fewer executions, lower cost, and a bonus of consistency, since the same read now returns the same answer every time within the run.

The trap is that not every tool is safe to cache. A pure tool's result depends only on its arguments and does not change within a run — read the same file, get the same bytes. But an effectful tool changes the world when you call it (increment a counter, append to a log, charge a card), and a volatile tool returns something new each time by nature (read the clock, sample randomness). These tools are supposed to return a different result on each call. Cache one, and every call after the first returns the first call's stale result: the counter appears frozen, the clock stops ticking, the agent reasons on a value that stopped being true after the first call.

The failure is silent, which is what makes it dangerous. Cache everything and your executions drop, your run gets faster, your cost falls — every dashboard says the optimization worked. Meanwhile the agent is quietly reading a frozen counter and drawing wrong conclusions from it. Nothing errors; the numbers are just wrong. So a memoizer cannot cache blindly. It must know which tools are pure and cache only those, always executing the effectful and volatile ones.

On the fixture a run issues 7 tool calls — a pure read_file and an effectful increment, interleaved. No caching executes all 7 and is correct: increment returns 1, 2, 3. Caching everything executes only 3 but freezes increment at 1, 1, 1 — fast and wrong. Caching only pure tools executes 5, deduping the reads while always running increment, so it is both cheaper than no-cache and correct.

**Memoizing tool calls by signature saves executions and gives a consistent view, but only pure tools — whose result is a function of their arguments — are safe to cache; caching an effectful or volatile tool silently freezes it, so the memoizer must gate on a purity flag.**

## Concepts

Purity is the property that decides whether a call is safe to memoize. A tool is pure if its result is a function of its arguments alone — same arguments, same result, every time, with no observable effect on the world. `read_file("a")` returns the same bytes whether you call it once or a hundred times, so its result can be computed once and reused. That is exactly the precondition a cache needs: a cache assumes the second call would have returned what the first did, and for a pure tool that assumption is guaranteed. Memoization is not a heuristic here; it is exact, because purity makes the cached value provably equal to the value a real call would produce.

An effectful or volatile tool violates that precondition by design. `increment()` returns a different value each call because each call changes the counter; `now()` returns a different time because time moves. The cache's assumption — "the next call returns the same thing" — is false for these tools, so serving a cached value returns something the real tool would never have returned at that point in the run. The cache does not just miss an optimization; it fabricates a result. And because the fabricated result is a plausible-looking value the tool really did return earlier, nothing downstream can tell it apart from a fresh one.

<svg role="img" aria-label="A cache assumes the next call equals the last; this holds for a pure tool and is false for an effectful one, so caching an effectful tool fabricates a result" viewBox="0 0 470 170" width="470" height="170">
  <rect x="0" y="0" width="470" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">a cache serves: "next call == last call's result"</text>
  <text x="30" y="52" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">pure read_file(a)</text>
  <rect x="30" y="60" width="80" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="46" y="77" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">config-v1</text>
  <text x="120" y="77" font-family="var(--mono)" font-size="14" fill="var(--muted)">=</text>
  <rect x="140" y="60" width="80" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="156" y="77" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">config-v1</text>
  <text x="235" y="77" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">assumption holds → safe to cache</text>
  <text x="30" y="122" font-family="var(--mono)" font-size="9" fill="var(--s2)">effectful increment()</text>
  <rect x="30" y="130" width="40" height="26" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="46" y="147" font-family="var(--mono)" font-size="9" fill="var(--s2)">1</text>
  <text x="80" y="147" font-family="var(--mono)" font-size="14" fill="var(--s2)">≠</text>
  <rect x="100" y="130" width="40" height="26" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="116" y="147" font-family="var(--mono)" font-size="9" fill="var(--s2)">2</text>
  <text x="155" y="147" font-family="var(--mono)" font-size="8" fill="var(--s2)">assumption false → cache fabricates a stale result</text>
</svg>
^ For a pure tool the next call equals the last, so the cache's assumption is exact; for an effectful tool the next call differs, so serving the cached value returns something the tool would never have produced.

This is why the purity flag has to be part of the tool's declaration, not inferred. You cannot look at a call signature and tell whether the tool is pure — `read_file("a")` and `increment()` are both just a name and arguments. Purity is a fact about the tool's implementation that only the tool's author knows, so it must be declared alongside the tool (pure/read-only versus effectful/write), and the memoizer must consult that declaration before caching. A cache that ignores the flag and keys purely on the signature is the bug: it treats every tool as if it were pure.

The payoff of getting this right is two things at once, and they are worth separating. The obvious one is cost: deduping repeated pure reads cuts executions and tokens. The subtler one is consistency: within a single run, a cached pure read is guaranteed to return the same value every time, so the agent cannot see a config as one value early and a different value late and reason incoherently across the gap. Both benefits apply only to pure tools; for effectful tools, executing every time is not a cost to optimize away — it is the correct behavior, because each execution is a distinct action with a distinct result.

**A cache assumes the next call returns what the last one did, which is guaranteed for a pure tool and false for an effectful one; purity is a declared fact about the tool, not something inferable from the signature, so the memoizer must gate on the flag or it fabricates results.**

## Worked example

The fixture is one run's tool calls plus a purity flag per tool.

```json filename=modules/agent-harness/code/harness-inter-12/tools.json:4-5 COMPLETE
  "files": {"a": "config-v1", "b": "config-w1"},
  "purity": {"read_file": true, "increment": false}
```

`read_file` is a pure lookup — pure true. `increment` mutates a counter and returns its new value — pure false. The run interleaves them: read a, increment, read a again, increment, read b, increment, read a. The replay executes each call unless the policy allows a cache hit for its signature.

```python filename=modules/agent-harness/code/harness-inter-12/memo.py:63-78 COMPLETE
def replay(calls, files, purity, cache_mode):
    """Replay the run. cache_mode: 'none', 'all' (cache every tool), 'pure' (cache only pure tools)."""
    world = World(dict(files))
    cache = {}
    results = []
    for call in calls:
        key = sig(call)
        cacheable = cache_mode == "all" or (cache_mode == "pure" and purity[call["tool"]])
        if cacheable and key in cache:
            results.append({"call": key, "value": cache[key], "hit": True})
            continue
        value = world.call(call["tool"], call.get("arg"))
        if cacheable:
            cache[key] = value
        results.append({"call": key, "value": value, "hit": False})
    return world.executed, results
```

The one line that matters is the `cacheable` predicate. Mode `all` caches every tool — the bug. Mode `pure` caches a call only when `purity[tool]` is true. The counter mutates in `World.call`, so each real execution of increment returns the next integer.

```python filename=modules/agent-harness/code/harness-inter-12/memo.py:49-55 COMPLETE
    def call(self, tool, arg):
        self.executed += 1
        if tool == "read_file":
            return self.files[arg]
        if tool == "increment":
            self.counter += 1
            return self.counter
```

Predict: no cache executes all 7 and increment returns 1, 2, 3. Cache-everything serves increment from cache after the first call, freezing it at 1, 1, 1. Cache-pure dedups the reads but runs increment every time, so it stays 1, 2, 3 while executing fewer than 7. Run it.

```text filename=modules/agent-harness/code/harness-inter-12/memo.py --run
CACHE EVERYTHING (buggy)   (7 calls)
--------------------------------------------------------
  read_file(a)     executed  -> config-v1
  increment()      executed  -> 1
  read_file(a)     cache hit -> config-v1
  increment()      cache hit -> 1
  read_file(b)     executed  -> config-w1
  increment()      cache hit -> 1
  read_file(a)     cache hit -> config-v1
  executions 3   increment returned [1, 1, 1]

CACHE PURE ONLY   (7 calls)
--------------------------------------------------------
  read_file(a)     executed  -> config-v1
  increment()      executed  -> 1
  read_file(a)     cache hit -> config-v1
  increment()      executed  -> 2
  read_file(b)     executed  -> config-w1
  increment()      executed  -> 3
  read_file(a)     cache hit -> config-v1
  executions 5   increment returned [1, 2, 3]
```

Cache-everything looks great — 3 executions, less than half — but increment returned 1, 1, 1: after the first call it was served from cache, so the counter froze. The agent now believes it incremented three times and the value never moved. Cache-pure returned increment as 1, 2, 3, identical to no cache, because increment is never cached; it still deduped read_file(a)'s three calls down to one execution, landing at 5 executions — cheaper than no-cache's 7 and correct. Same run, same signatures; the only difference is whether the cache consulted the purity flag.

<svg role="img" aria-label="Timeline of increment calls returning 1,2,3 with no cache and cache-pure, but a frozen 1,1,1 with cache-everything" viewBox="0 0 470 180" width="470" height="180">
  <rect x="0" y="0" width="470" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">what increment() returns on its three calls</text>
  <text x="30" y="52" font-family="var(--mono)" font-size="9" fill="var(--ink)">no cache</text>
  <g fill="var(--acc-line)"><circle cx="180" cy="48" r="12"/><circle cx="280" cy="48" r="12"/><circle cx="380" cy="48" r="12"/></g>
  <text x="176" y="52" font-family="var(--mono)" font-size="10" fill="var(--panel)">1</text>
  <text x="276" y="52" font-family="var(--mono)" font-size="10" fill="var(--panel)">2</text>
  <text x="376" y="52" font-family="var(--mono)" font-size="10" fill="var(--panel)">3</text>
  <text x="30" y="102" font-family="var(--mono)" font-size="9" fill="var(--ink)">cache all</text>
  <g fill="var(--s2)"><circle cx="180" cy="98" r="12"/><circle cx="280" cy="98" r="12"/><circle cx="380" cy="98" r="12"/></g>
  <text x="176" y="102" font-family="var(--mono)" font-size="10" fill="var(--panel)">1</text>
  <text x="276" y="102" font-family="var(--mono)" font-size="10" fill="var(--panel)">1</text>
  <text x="376" y="102" font-family="var(--mono)" font-size="10" fill="var(--panel)">1</text>
  <text x="60" y="122" font-family="var(--mono)" font-size="8" fill="var(--s2)">frozen — the counter never advances</text>
  <text x="30" y="152" font-family="var(--mono)" font-size="9" fill="var(--ink)">cache pure</text>
  <g fill="var(--acc-line)"><circle cx="180" cy="148" r="12"/><circle cx="280" cy="148" r="12"/><circle cx="380" cy="148" r="12"/></g>
  <text x="176" y="152" font-family="var(--mono)" font-size="10" fill="var(--panel)">1</text>
  <text x="276" y="152" font-family="var(--mono)" font-size="10" fill="var(--panel)">2</text>
  <text x="376" y="152" font-family="var(--mono)" font-size="10" fill="var(--panel)">3</text>
</svg>
^ No cache and cache-pure both let increment count 1, 2, 3; cache-everything freezes it at 1, 1, 1 because it served the effectful tool from cache.

## Build

Reproduce the run. Pure standard library, deterministic, so the frozen 1,1,1 and the correct 5-execution 1,2,3 come out exactly.

Run `--run` for the per-policy trace, `--cost` for the summary, `--check` for the gate. The cost view is the temptation and the trap in one table: cache-everything is cheapest and wrong; cache-pure is cheaper than none and right.

```text filename=modules/agent-harness/code/harness-inter-12/memo.py --cost
COST — executions and the effectful tool's results per policy
------------------------------------------------------------
  policy               executions   increment returned
  no cache                    7   [1, 2, 3]
  cache everything            3   [1, 1, 1]
  cache pure only             5   [1, 2, 3]
------------------------------------------------------------
  cache-everything is cheapest but freezes increment; cache-pure is cheaper than none and correct.
```

The increment results are extracted with a one-line helper — the sequence of values the effectful tool returned across the run, which is what every correctness flag compares.

```python filename=modules/agent-harness/code/harness-inter-12/memo.py:81-83 COMPLETE
def increments(results):
    """The sequence of values the increment tool returned across the run."""
    return [r["value"] for r in results if r["call"][0] == "increment"]
```

<svg role="img" aria-label="Bar chart of executions per policy: no cache 7, cache-everything 3 marked wrong, cache-pure 5 marked correct" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">executions per policy (fewer = cheaper), with correctness</text>
  <line x1="40" y1="140" x2="450" y2="140" stroke="var(--line)"/>
  <rect x="70" y="42" width="70" height="98" fill="var(--s2)"/>
  <text x="86" y="156" font-family="var(--mono)" font-size="8" fill="var(--ink)">no cache 7</text>
  <text x="80" y="36" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">correct</text>
  <rect x="200" y="98" width="70" height="42" fill="var(--s1)"/>
  <text x="210" y="156" font-family="var(--mono)" font-size="8" fill="var(--ink)">cache all 3</text>
  <text x="210" y="92" font-family="var(--mono)" font-size="8" fill="var(--s1)">WRONG (1,1,1)</text>
  <rect x="330" y="70" width="70" height="70" fill="var(--acc-line)"/>
  <text x="340" y="156" font-family="var(--mono)" font-size="8" fill="var(--ink)">cache pure 5</text>
  <text x="338" y="64" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">correct</text>
</svg>
^ Cache-everything is the shortest bar but produces the wrong counter; cache-pure sits between the two on cost and is the only cheaper policy that is also correct.

The self-test pins the trade: caching everything returns wrong increment results, caching only pure tools returns the same results as no cache while executing fewer calls, and the effectful tool keeps counting under cache-pure.

```python filename=modules/agent-harness/code/harness-inter-12/memo.py:122-126 COMPLETE
    cache_all_breaks = increments(r_all) != increments(r_none)
    print("  cache-everything returns wrong increment results = %s (%s vs truth %s)"
          % (cache_all_breaks, increments(r_all), increments(r_none)))

    cache_pure_correct = increments(r_pure) == increments(r_none)
    print("  cache-pure returns the same results as no cache = %s (%s)" % (cache_pure_correct, increments(r_pure)))
```

```text filename=modules/agent-harness/code/harness-inter-12/memo.py --check
SELF-TEST — caching everything freezes the effectful tool; caching only pure tools saves and stays correct
--------------------------------------------------------------------------------------------------------
  cache-everything returns wrong increment results = True ([1, 1, 1] vs truth [1, 2, 3])
  cache-pure returns the same results as no cache = True ([1, 2, 3])
  cache-pure executes fewer calls than no cache = True (5 < 7)
  cache-pure never caches increment, so it keeps counting = True ([1, 2, 3])
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  cache_all_breaks=True  cache_pure_correct=True  cache_pure_saves=True  effectful_always_runs=True
```

Four True flags. Cache_all_breaks: caching everything returns 1,1,1 instead of the true 1,2,3 — the silent freeze. Cache_pure_correct: caching only pure tools matches no cache exactly. Cache_pure_saves: and it does so in 5 executions, fewer than 7. Effectful_always_runs: increment's results are strictly increasing under cache-pure, proving it was executed every time. The correctness flags matter more than the cost flag, because cache-everything wins on cost and still loses.

**Cache-everything is cheaper than cache-pure and still the wrong answer, which is the whole point — the metric that catches the bug is correctness of the effectful tool's results, not the execution count the optimization was chasing.**

## Definition of done

You are done when you reproduce the frozen counter and can explain which tools are safe to cache.

Concretely: `--run` shows cache-everything freezing increment at 1,1,1 while cache-pure keeps it at 1,2,3; `--cost` shows executions 7 / 3 / 5 with increment results 1,2,3 / 1,1,1 / 1,2,3; `--check` prints PASS with four True flags. You can define purity — result is a function of arguments with no observable effect — and explain why a cache's core assumption holds for pure tools and is false for effectful or volatile ones. You can explain that purity is a declared fact about the tool, not inferable from a call signature, so the memoizer must gate on the flag. And you can name both payoffs of caching pure reads: lower cost and a consistent within-run view.

The habit to carry: declare every tool as read-only/pure or effectful/write, and let the harness memoize only the pure ones, keyed by their arguments. Never cache a write, a counter, a clock, or a randomness source. When an agent seems to ignore that a value changed — insisting a counter is still 1, a file still has the old contents, the time is still what it was — suspect an over-eager cache serving a stale result, not a reasoning failure.

## Boss fight

The instructive failure is an agent that keeps acting on a balance that stopped updating.

A team adds a tool-result cache to cut cost and keys it on the call signature — tool name plus JSON arguments — for every tool uniformly. Read-heavy tools get big hit rates and the bill drops, so it ships. Then reports come in: an agent that transfers money keeps reading the same account balance after each transfer, because `get_balance(account)` has an identical signature every call and is served from cache after the first. The agent believes the balance never changed, so it approves transfers that overdraw the account. Nothing errored; the cache just froze a value that was supposed to move. The fix is to mark `get_balance` (and every effectful or volatile tool) as non-cacheable and cache only the declared-pure reads.

Your turn, two moves. First, add a volatile-but-effect-free tool — `now()` that returns a step counter — and mark it pure by mistake; predict that cache-pure will now also freeze it, showing that "no side effects" is not the same as "pure": a tool that returns something new each call is unsafe to cache even if it changes nothing, so volatility, not just effects, must set the flag to false. Second, add a cache-invalidation event: after an increment, drop the cached read of any file that increment could have changed, and confirm that with correct invalidation you can safely cache a read whose backing state is mutated by another tool — which is the real, hard version of this problem and why most harnesses simply refuse to cache anything but provably pure tools.

## External resources

The literature on referential transparency and memoization (any functional-programming text) is the formal backing here — memoization is sound exactly when a function is referentially transparent, which is the precise version of the purity flag this module gates on.

HTTP caching semantics (RFC 9111) are the same problem at web scale: which responses are cacheable, for how long, and how invalidation works — GET is cacheable, POST is not, which is the read-versus-write distinction applied to tools.

Any agent-framework tool-specification format (OpenAI function calling, MCP tool annotations such as readOnlyHint) shows where purity and read-only hints are declared in practice, so a harness can decide safely what to memoize.
