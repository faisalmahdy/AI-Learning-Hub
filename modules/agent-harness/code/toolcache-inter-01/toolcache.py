"""Cache read-only tool results in a session -- an agent re-reads the same things constantly, and never cache a mutating or time-sensitive tool.

Agents are repetitive. Over a single task a model will re-read the same file it read three steps ago, re-fetch a document it already fetched, re-query the same record -- because its working memory is the conversation, and rebuilding context often means asking for the same information again. Each of those repeated calls, if executed, pays the full cost again: the network round-trip, the tool's latency, and the tokens to shuttle the result back into the context. For a read-only tool whose answer has not changed, that is pure waste -- the harness already has the answer from the first call.

Caching removes the waste. Key each tool result by (tool name, arguments) and store it; when the same call comes again, serve the stored result instead of re-executing. Because the model asked the identical question, the identical answer is correct, and it arrives instantly with no round-trip. Over a session with the normal amount of agent repetition, this cuts tool executions and latency substantially, and it does so transparently -- the model cannot tell a cached result from a fresh one, because for a pure read-only tool they are the same.

The hard rule is WHAT you may cache. Caching is only safe for tools that are read-only and deterministic within the session -- their result depends solely on the arguments and does not change between calls. A mutating tool (write a file, send a message, charge a card) must execute every time, because its point is the side effect; serving it from cache would silently skip the real action. A time-sensitive or non-deterministic tool (the current time, a random value, a live price, a queue depth) must also execute every time, because caching it would return a stale answer that was true once and is now wrong. So the cache key is not enough; each tool must be declared cacheable or not, and the harness caches only the cacheable ones while running the rest every time.

The rule: cache the results of read-only, deterministic tool calls keyed by (tool, arguments) and serve repeats from the cache, while executing mutating and time-sensitive tools every time, because agents frequently re-request identical information -- so caching read-only results removes redundant round-trips at no correctness cost, whereas caching a mutating tool would skip its side effect and caching a time-sensitive one would return a stale result.

On this fixture the agent makes 7 calls, including get_file(a) three times. Without caching that is 7 executions; caching serves the 2 repeated get_file(a) calls from the cache (2 hits) for 5 executions, while current_time and write_file -- not cacheable -- still execute every time. This computes both.

  --calls     each call, whether it is cacheable, and whether caching serves it fresh or from the cache
  --savings   executions without caching vs with caching, the cache hits, and the non-cacheable calls that always run
  --check     caching serves repeated read-only calls from the cache and reduces executions, while non-cacheable calls always run

calls are the fixture; the executions with and without caching, the cache hits, and the non-cacheable executions are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "toolcache.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


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


def no_cache_executions(calls):
    return len(calls)


def cached_executions(calls):
    return sum(1 for a in classify(calls) if a.startswith("execute"))


def cache_hits(calls):
    return sum(1 for a in classify(calls) if a == "cache hit")


# ----------------------------------------------------------------- printing

def calls_view(data):
    calls = data["calls"]
    actions = classify(calls)
    print("CALLS — each call, cacheability, and the caching harness's action")
    print("-" * 62)
    print("  #  tool          args  cacheable  action")
    for i, (c, a) in enumerate(zip(calls, actions)):
        print("  %d  %-12s  %-4s  %-9s  %s" % (i, c["tool"], c["args"], c["cacheable"], a))
    print("-" * 62)
    print("  repeated read-only calls become cache hits; others execute")


def savings_view(data):
    calls = data["calls"]
    print("SAVINGS — executions without caching vs with caching")
    print("-" * 58)
    print("  no caching:  %d executions (every call runs)" % no_cache_executions(calls))
    print("  with cache:  %d executions (%d cache hits saved)" % (cached_executions(calls), cache_hits(calls)))
    print("-" * 58)
    noncacheable = sum(1 for c in calls if not c["cacheable"])
    print("  non-cacheable calls that still run every time: %d (mutating / time-sensitive)" % noncacheable)


def check(data):
    print("SELF-TEST — caching serves repeated read-only calls from the cache and reduces executions, while non-cacheable calls always run")
    print("-" * 128)
    calls = data["calls"]
    actions = classify(calls)

    has_repeated_cacheable = cache_hits(calls) > 0
    print("  the session repeats a cacheable call = %s (%d cache hit(s))" % (has_repeated_cacheable, cache_hits(calls)))

    cache_reduces_executions = cached_executions(calls) < no_cache_executions(calls)
    print("  caching reduces total executions = %s (%d < %d)" % (cache_reduces_executions, cached_executions(calls), no_cache_executions(calls)))

    savings_equals_hits = no_cache_executions(calls) - cached_executions(calls) == cache_hits(calls)
    print("  the executions saved equal the cache hits = %s (%d saved)" % (savings_equals_hits, no_cache_executions(calls) - cached_executions(calls)))

    noncacheable_always_runs = all(actions[i].startswith("execute") for i, c in enumerate(calls) if not c["cacheable"])
    print("  every non-cacheable call executes (never cached) = %s" % noncacheable_always_runs)

    only_repeats_cached = all(actions[i] == "cache hit" for i, c in enumerate(calls) if actions[i] == "cache hit" and c["cacheable"])
    first_of_each_executes = actions[0] == "execute (cache miss)"
    print("  the first call of each cacheable key still executes (cache miss) = %s" % first_of_each_executes)

    time_tool_not_cached = all(actions[i].startswith("execute") for i, c in enumerate(calls) if c["tool"] == "current_time")
    print("  the time-sensitive tool is never served stale from cache = %s" % time_tool_not_cached)

    ok = (has_repeated_cacheable and cache_reduces_executions and savings_equals_hits and noncacheable_always_runs
          and first_of_each_executes and time_tool_not_cached and only_repeats_cached)
    print("-" * 128)
    print("SELF-TEST %s  has_repeated_cacheable=%s  cache_reduces_executions=%s  savings_equals_hits=%s  noncacheable_always_runs=%s  first_of_each_executes=%s  time_tool_not_cached=%s"
          % ("PASS" if ok else "FAIL", has_repeated_cacheable, cache_reduces_executions, savings_equals_hits, noncacheable_always_runs, first_of_each_executes, time_tool_not_cached))
    return ok


def main():
    p = argparse.ArgumentParser(description="Tool result caching: cache the results of read-only, deterministic tool calls keyed by (tool, arguments) and serve repeats from the cache, while executing mutating and time-sensitive tools every time, because agents frequently re-request identical information -- so caching read-only results removes redundant round-trips at no correctness cost, whereas caching a mutating tool would skip its side effect and caching a time-sensitive one would return a stale result.")
    p.add_argument("--calls", action="store_true")
    p.add_argument("--savings", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%d  file=%s  (the session's tool calls are a fixture)" % (len(data["calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.calls:
        calls_view(data)
    elif args.savings:
        savings_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
