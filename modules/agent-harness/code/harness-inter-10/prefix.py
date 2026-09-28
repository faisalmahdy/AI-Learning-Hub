"""Keep the prompt's stable segments first, or a volatile token up front busts the cache and reprocesses everything.

A model prompt cache works on the longest common prefix: when this request's prompt begins with the same
tokens as the last one, those leading tokens are reused from cache and only the tokens after the first
difference are reprocessed. That reprocessing is what you pay for in latency and cost. So where you put a
segment that changes every request -- a timestamp, a per-request id, a random nonce -- decides your whole
cache. Put it first and the very first token differs, the common prefix is zero, and the entire prompt is
reprocessed on every request. Put it last, behind all the stable segments, and the cache covers everything
up to it, leaving only its few tokens to reprocess.

The segments here are the system prompt (500 tokens, stable), the tool definitions (300, stable), the
conversation history (1000, stable across a request pair), and a 20-token timestamp that changes every
request. Ordered volatile-first, the cache reuses 0 tokens and reprocesses all 1820. Ordered
volatile-last, it reuses 1800 and reprocesses just 20 -- the same content, ninety-one times less work,
decided entirely by the position of one small segment.

This computes, for each layout, how many tokens the cache reuses and how many must be reprocessed when a
volatile segment has changed since the previous request.

  --layouts    the two segment orderings and where the volatile segment sits
  --cache      cached vs reprocessed tokens for each layout
  --check      the volatile-first layout caches nothing; volatile-last caches the whole stable prefix

The segment sizes and orderings are the fixture; every cached/reprocessed count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "prompt.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the cache model

def cached_tokens(order, segments):
    """Longest common prefix with the previous request: the leading run of STABLE segments, in tokens.

    The cache breaks at the first segment that changed (a volatile one); everything from there is reprocessed.
    """
    cached = 0
    for name in order:
        if not segments[name]["stable"]:
            break               # first volatile segment: the common prefix ends here
        cached += segments[name]["tokens"]
    return cached


def total_tokens(segments):
    return sum(s["tokens"] for s in segments.values())


def reprocessed(order, segments):
    return total_tokens(segments) - cached_tokens(order, segments)


# ----------------------------------------------------------------- printing

def layouts_view(data):
    segs = data["segments"]
    print("LAYOUTS — the two segment orderings (V marks the volatile segment)")
    print("-" * 60)
    for name, order in data["layouts"].items():
        marked = " ".join(("%s(V)" % s if not segs[s]["stable"] else s) for s in order)
        print("  %-14s %s" % (name, marked))
    print("-" * 60)
    print("  same segments, same tokens (%d total) -- only the order differs." % total_tokens(segs))


def cache_view(data):
    segs = data["segments"]
    total = total_tokens(segs)
    print("CACHE — cached vs reprocessed tokens per layout (total %d)" % total)
    print("-" * 60)
    for name, order in data["layouts"].items():
        c = cached_tokens(order, segs)
        r = reprocessed(order, segs)
        print("  %-14s cached %4d   reprocessed %4d   (%.0f%% cached)" % (name, c, r, 100 * c / total))
    print("-" * 60)
    print("  volatile-first reprocesses everything; volatile-last reprocesses only the timestamp.")


def check(data):
    print("SELF-TEST — the volatile-first layout caches nothing; volatile-last caches the whole stable prefix")
    print("-" * 92)
    segs = data["segments"]
    total = total_tokens(segs)
    first = data["layouts"]["volatile_first"]
    last = data["layouts"]["volatile_last"]
    stable_total = sum(s["tokens"] for s in segs.values() if s["stable"])

    first_caches_nothing = cached_tokens(first, segs) == 0
    print("  volatile-first caches nothing (reprocesses all) = %s (cached %d, reprocessed %d)"
          % (first_caches_nothing, cached_tokens(first, segs), reprocessed(first, segs)))

    last_caches_prefix = cached_tokens(last, segs) == stable_total
    print("  volatile-last caches the whole stable prefix = %s (cached %d of %d stable)"
          % (last_caches_prefix, cached_tokens(last, segs), stable_total))

    last_reprocesses_less = reprocessed(last, segs) < reprocessed(first, segs)
    print("  volatile-last reprocesses far fewer tokens = %s (%d vs %d)"
          % (last_reprocesses_less, reprocessed(last, segs), reprocessed(first, segs)))

    same_content = sorted(first) == sorted(last)
    print("  the two layouts contain the identical segments = %s (order is the only difference)" % same_content)

    ok = first_caches_nothing and last_caches_prefix and last_reprocesses_less and same_content
    print("-" * 92)
    print("SELF-TEST %s  first_caches_nothing=%s  last_caches_prefix=%s  last_reprocesses_less=%s  same_content=%s"
          % ("PASS" if ok else "FAIL", first_caches_nothing, last_caches_prefix, last_reprocesses_less, same_content))
    return ok


def main():
    p = argparse.ArgumentParser(description="Keep the prompt's stable segments first so the cache hits.")
    p.add_argument("--layouts", action="store_true")
    p.add_argument("--cache", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("segments=%d  layouts=%s  total_tokens=%d  file=%s  (the segments and orders are a fixture)"
          % (len(data["segments"]), list(data["layouts"]), total_tokens(data["segments"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.layouts:
        layouts_view(data)
    elif args.cache:
        cache_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
