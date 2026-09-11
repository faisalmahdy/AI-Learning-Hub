#!/usr/bin/env python3
"""Compact the context by evicting the oldest UNPINNED turns -- never the pinned ones.

An agent's context window is finite, so when the conversation grows past the token budget
the harness must drop something. What it drops decides whether the agent keeps working or
loses its mind. Two items are pinned: the system prompt (who the agent is) and the task
(what it is doing). Those must survive every compaction. Everything else -- the back-and-
forth of the conversation -- is evictable, oldest first, because the recent turns carry the
live state and the old ones are stale.

The correct policy keeps all pinned items and fills the remaining budget with the most
recent unpinned turns. The bug is plain FIFO: evict the oldest item until it fits, pinned
or not. And the oldest items are exactly the system prompt and the task, so FIFO drops
them first -- the context now fits the budget and the agent has forgotten its instructions
and its goal. It looks like it worked (it fits!) and the agent quietly goes off the rails.
This measures both policies against the budget and the must-keep set.

  --window      the current context, its total, and how far over budget it is
  --compact     the correct compaction (keep pinned, recent unpinned) and what it drops
  --fifo        the FIFO compaction -- fits the budget, but see what it evicted
  --check       correct fits and keeps all pinned; FIFO fits but drops a pinned item

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "context.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- helpers

def total_tokens(items):
    return sum(it["tokens"] for it in items)


def pinned_ids(items):
    return {it["id"] for it in items if it["pinned"]}


# ------------------------------------------------------------- the two policies

def compact_correct(items, budget):
    """Keep every pinned item; fill the rest of the budget with the most RECENT unpinned."""
    pinned = [it for it in items if it["pinned"]]
    unpinned = [it for it in items if not it["pinned"]]
    kept = list(pinned)
    used = total_tokens(pinned)
    for it in reversed(unpinned):          # most recent first
        if used + it["tokens"] <= budget:
            kept.append(it)
            used += it["tokens"]
    # restore chronological order
    order = {it["id"]: i for i, it in enumerate(items)}
    return sorted(kept, key=lambda it: order[it["id"]])


def compact_fifo(items, budget):
    """The bug: drop the oldest item until it fits, pinned or not."""
    kept = list(items)
    while total_tokens(kept) > budget and kept:
        kept.pop(0)                        # evict the oldest -- which is a pinned item first
    return kept


# ----------------------------------------------------------------- printing

def window_view(data):
    items, budget = data["items"], data["budget"]
    print("WINDOW — the context (oldest first), budget = %d tokens" % budget)
    print("-" * 66)
    for it in items:
        print("  %-6s %3d tok  %-8s %s" % (it["id"], it["tokens"], "PINNED" if it["pinned"] else "", it["role"]))
    print("-" * 66)
    print("  total = %d tokens, over budget by %d." % (total_tokens(items), total_tokens(items) - budget))


def compact_view(data):
    items, budget = data["items"], data["budget"]
    kept = compact_correct(items, budget)
    kept_ids = {it["id"] for it in kept}
    dropped = [it["id"] for it in items if it["id"] not in kept_ids]
    print("COMPACT — correct: keep pinned, fill with most-recent unpinned")
    print("-" * 66)
    print("  kept:    %s  (%d tokens)" % ([it["id"] for it in kept], total_tokens(kept)))
    print("  dropped: %s" % dropped)
    print("  all pinned retained? %s" % pinned_ids(items).issubset(kept_ids))
    print("-" * 66)
    print("  the system prompt and task survive; the oldest chatter is what goes.")


def fifo_view(data):
    items, budget = data["items"], data["budget"]
    kept = compact_fifo(items, budget)
    kept_ids = {it["id"] for it in kept}
    dropped = [it["id"] for it in items if it["id"] not in kept_ids]
    print("FIFO — the bug: evict oldest until it fits, pinned or not")
    print("-" * 66)
    print("  kept:    %s  (%d tokens, fits budget %d)" % ([it["id"] for it in kept], total_tokens(kept), budget))
    print("  dropped: %s" % dropped)
    print("  all pinned retained? %s  <- dropped the system prompt and task!" % pinned_ids(items).issubset(kept_ids))
    print("-" * 66)
    print("  it fits the budget and the agent has forgotten who it is and what it is doing.")


def check(data):
    print("SELF-TEST — correct fits and keeps all pinned; FIFO fits but drops a pinned item")
    print("-" * 66)
    items, budget = data["items"], data["budget"]
    pins = pinned_ids(items)

    good = compact_correct(items, budget)
    good_ids = {it["id"] for it in good}
    good_fits = total_tokens(good) <= budget
    print("  correct compaction fits the budget = %s (%d <= %d)" % (good_fits, total_tokens(good), budget))

    good_keeps_pinned = pins.issubset(good_ids)
    print("  correct compaction retains every pinned item = %s (%s)" % (good_keeps_pinned, sorted(pins)))

    keeps_recent = "turn4" in good_ids
    print("  correct compaction keeps the most recent turn = %s (turn4)" % keeps_recent)

    fifo = compact_fifo(items, budget)
    fifo_ids = {it["id"] for it in fifo}
    fifo_fits = total_tokens(fifo) <= budget
    print("  FIFO also fits the budget = %s (%d <= %d)" % (fifo_fits, total_tokens(fifo), budget))

    fifo_drops_pinned = not pins.issubset(fifo_ids)
    print("  ...but FIFO drops a pinned item = %s (missing %s)"
          % (fifo_drops_pinned, sorted(pins - fifo_ids)))

    ok = good_fits and good_keeps_pinned and keeps_recent and fifo_fits and fifo_drops_pinned
    print("-" * 66)
    print("SELF-TEST %s  good_fits=%s  good_keeps_pinned=%s  keeps_recent=%s  fifo_fits=%s  fifo_drops_pinned=%s"
          % ("PASS" if ok else "FAIL", good_fits, good_keeps_pinned, keeps_recent, fifo_fits, fifo_drops_pinned))
    return ok


def main():
    p = argparse.ArgumentParser(description="Context compaction: keep pinned, evict oldest unpinned.")
    p.add_argument("--window", action="store_true")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--fifo", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("items=%d  budget=%d  file=%s  (context is a fixture)"
          % (len(data["items"]), data["budget"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.window:
        window_view(data)
    elif args.compact:
        compact_view(data)
    elif args.fifo:
        fifo_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
