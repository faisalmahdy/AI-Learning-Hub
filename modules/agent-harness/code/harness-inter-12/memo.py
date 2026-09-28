"""Memoize tool results by call signature -- but only pure tools, or a cached effectful call returns a stale lie.

An agent loop re-issues the same tool call constantly: it reads the same config three times across a run,
looks up the same file after every step. Each call costs a round-trip and tokens, and many are identical.
The obvious optimization is a cache keyed by the call signature (tool name plus arguments): the first call
executes, the rest return the stored result. For a pure read -- one whose answer depends only on its
arguments and never changes within the run -- this is free money: fewer executions, lower cost, and a
consistent view (the same read gives the same answer every time).

The trap is caching a tool that is not pure. An effectful tool (increment a counter, append to a log,
charge a card) or a volatile one (read the clock, sample randomness) returns a DIFFERENT result each call
by design. Cache it and every call after the first returns the first call's stale result -- the counter
appears frozen, the clock stops, the agent reasons on a value that is no longer true. The bug is silent:
executions drop and everything looks faster, but the answers are wrong. So the memoizer cannot cache
blindly; it must consult a purity flag and only cache the tools whose results are a function of their
arguments.

On this fixture a run issues 7 tool calls -- a pure read_file and an effectful increment, interleaved.
No caching executes all 7 and is correct. Caching everything executes only 3 but freezes the counter at
1,1,1 instead of 1,2,3 -- fast and wrong. Caching only pure tools executes 5, deduping the reads while
always running increment, so it is both cheaper than no-cache and correct. This computes all three.

  --run        replay the call sequence under each policy, showing what executed and what each returned
  --cost       executions and the increment results under each policy
  --check      caching everything freezes the effectful tool; caching only pure tools saves and stays correct

The call sequence and purity flags are the fixture; every result is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "tools.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


class World:
    """The tools' backing state -- read_file is a fixed lookup (pure); increment mutates a counter."""
    def __init__(self, files):
        self.files = files
        self.counter = 0
        self.executed = 0

    def call(self, tool, arg):
        self.executed += 1
        if tool == "read_file":
            return self.files[arg]
        if tool == "increment":
            self.counter += 1
            return self.counter
        raise KeyError(tool)


def sig(call):
    return (call["tool"], call.get("arg"))


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


def increments(results):
    """The sequence of values the increment tool returned across the run."""
    return [r["value"] for r in results if r["call"][0] == "increment"]


# ----------------------------------------------------------------- printing

def run_view(data):
    calls, files, purity = data["calls"], data["files"], data["purity"]
    for mode, label in (("none", "NO CACHE"), ("all", "CACHE EVERYTHING (buggy)"), ("pure", "CACHE PURE ONLY")):
        execs, results = replay(calls, files, purity, mode)
        print("%s   (%d calls)" % (label, len(calls)))
        print("-" * 56)
        for r in results:
            tag = "cache hit" if r["hit"] else "executed "
            name = r["call"][0] + (("(%s)" % r["call"][1]) if r["call"][1] else "()")
            print("  %-16s %s -> %s" % (name, tag, r["value"]))
        print("  executions %d   increment returned %s" % (execs, increments(results)))
        print("")


def cost_view(data):
    calls, files, purity = data["calls"], data["files"], data["purity"]
    print("COST — executions and the effectful tool's results per policy")
    print("-" * 60)
    print("  policy               executions   increment returned")
    for mode, label in (("none", "no cache"), ("all", "cache everything"), ("pure", "cache pure only")):
        execs, results = replay(calls, files, purity, mode)
        print("  %-18s   %8d   %s" % (label, execs, increments(results)))
    print("-" * 60)
    print("  cache-everything is cheapest but freezes increment; cache-pure is cheaper than none and correct.")


def check(data):
    print("SELF-TEST — caching everything freezes the effectful tool; caching only pure tools saves and stays correct")
    print("-" * 104)
    calls, files, purity = data["calls"], data["files"], data["purity"]
    e_none, r_none = replay(calls, files, purity, "none")
    e_all, r_all = replay(calls, files, purity, "all")
    e_pure, r_pure = replay(calls, files, purity, "pure")

    cache_all_breaks = increments(r_all) != increments(r_none)
    print("  cache-everything returns wrong increment results = %s (%s vs truth %s)"
          % (cache_all_breaks, increments(r_all), increments(r_none)))

    cache_pure_correct = increments(r_pure) == increments(r_none)
    print("  cache-pure returns the same results as no cache = %s (%s)" % (cache_pure_correct, increments(r_pure)))

    cache_pure_saves = e_pure < e_none
    print("  cache-pure executes fewer calls than no cache = %s (%d < %d)" % (cache_pure_saves, e_pure, e_none))

    effectful_always_runs = increments(r_pure) == sorted(set(increments(r_pure))) == increments(r_none)
    print("  cache-pure never caches increment, so it keeps counting = %s (%s)" % (effectful_always_runs, increments(r_pure)))

    ok = cache_all_breaks and cache_pure_correct and cache_pure_saves and effectful_always_runs
    print("-" * 104)
    print("SELF-TEST %s  cache_all_breaks=%s  cache_pure_correct=%s  cache_pure_saves=%s  effectful_always_runs=%s"
          % ("PASS" if ok else "FAIL", cache_all_breaks, cache_pure_correct, cache_pure_saves, effectful_always_runs))
    return ok


def main():
    p = argparse.ArgumentParser(description="Memoize tool results by signature, but only pure tools.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--cost", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%d  tools=%s  file=%s  (the call sequence and purity flags are a fixture)"
          % (len(data["calls"]), sorted(data["purity"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.cost:
        cost_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
