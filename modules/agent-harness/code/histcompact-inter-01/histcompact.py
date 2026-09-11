"""Pin the system prompt and task when compacting history -- naive FIFO drops the oldest, which is exactly the goal.

An agent's conversation grows every turn: the system prompt, the user's task, then a lengthening trail of assistant
thoughts and tool observations. The model's context window is fixed, so sooner or later the transcript no longer fits and
the harness must trim it before the next turn. The obvious trim is FIFO -- drop the oldest messages until it fits -- and
it is exactly wrong, because the oldest messages are the system prompt and the original task: the standing instructions
that tell the agent what it is and the goal that tells it what it is doing. Evict those and the agent, on its very next
turn, is a capable model with no instructions and no objective, working only from the recent tool chatter -- so it drifts,
repeats work, or invents a new goal. The bug is silent: the transcript still fits, the model still responds fluently, it
just responds to the wrong (missing) prompt.

The fix is to compact with priorities, not by age. Mark the messages that must survive -- the system prompt and the task
-- as pinned, always keep them, and spend the remaining budget on the most RECENT turns, because recency is what the agent
needs to continue, while the middle of the transcript is the most expendable (and, in a real system, is where you put a
short summary of what happened rather than dropping it outright). So the kept context is: the goal (pinned) plus the
latest state (recent), with the stale middle compacted away. This keeps the agent both on-task and current, within the
same token budget that FIFO used to lose the task.

On this fixture the transcript is 870 tokens against a 500-token budget. FIFO drops from the front: it removes the system
prompt (200), then the task (150), then the oldest turn, leaving the four most recent turns at 420 tokens -- under budget,
but with no system prompt and no task. Pinned compaction keeps system + task (350) and adds only the single most recent
turn (120) for 470 tokens -- under budget, and it still has the goal. This computes both.

  --compact  each strategy's kept messages and token total -- FIFO drops system+task; pinned keeps them plus the latest turn
  --recall   what the agent still knows after each trim: FIFO has lost its instructions and goal; pinned retains them
  --check    FIFO drops the pinned system and task; pinned keeps both plus a recent turn; both stay within budget

The transcript and budget are the fixture; every kept set and token total is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "histcompact.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def total(msgs):
    return sum(m["tokens"] for m in msgs)


def fifo_compact(messages, budget):
    """Drop the oldest messages until the transcript fits -- ignores what each message is."""
    kept = list(messages)
    while total(kept) > budget:
        kept.pop(0)
    return kept


def pinned_compact(messages, budget):
    """Keep pinned messages always, then fill the remaining budget with the most recent unpinned turns."""
    kept = [m for m in messages if m["pin"]]
    used = total(kept)
    for m in reversed([m for m in messages if not m["pin"]]):
        if used + m["tokens"] <= budget:
            kept.append(m)
            used += m["tokens"]
    return [m for m in messages if m in kept]  # restore original order


def ids(msgs):
    return [m["id"] for m in msgs]


# ----------------------------------------------------------------- printing

def compact_view(data):
    msgs, budget = data["messages"], data["budget"]
    print("COMPACT — trim %d tokens to a %d-token budget" % (total(msgs), budget))
    print("-" * 62)
    f = fifo_compact(msgs, budget)
    p = pinned_compact(msgs, budget)
    print("  FIFO (drop oldest) keeps  : %s  = %d tokens" % (ids(f), total(f)))
    print("  pinned compaction keeps   : %s  = %d tokens" % (ids(p), total(p)))
    print("-" * 62)
    print("  FIFO evicted the system prompt and task; pinned kept them plus the latest turn.")


def recall_view(data):
    msgs, budget = data["messages"], data["budget"]
    f = ids(fifo_compact(msgs, budget))
    p = ids(pinned_compact(msgs, budget))
    print("RECALL — what the agent still knows on the next turn")
    print("-" * 58)
    for label, kept in (("FIFO", f), ("pinned", p)):
        print("  %-8s has system prompt = %-5s  has task = %-5s  has latest turn = %s"
              % (label, "system" in kept, "task" in kept, msgs[-1]["id"] in kept))
    print("-" * 58)
    print("  FIFO lost its instructions and goal; pinned retained both.")


def check(data):
    print("SELF-TEST — FIFO drops the pinned system and task; pinned keeps both plus a recent turn; both stay within budget")
    print("-" * 118)
    msgs, budget = data["messages"], data["budget"]
    f = fifo_compact(msgs, budget)
    p = pinned_compact(msgs, budget)
    fids, pids = ids(f), ids(p)
    latest = msgs[-1]["id"]

    fifo_drops_system = "system" not in fids
    print("  FIFO drops the system prompt = %s (kept %s)" % (fifo_drops_system, fids))

    fifo_drops_task = "task" not in fids
    print("  FIFO drops the original task = %s" % fifo_drops_task)

    pinned_keeps_goal = "system" in pids and "task" in pids
    print("  pinned compaction keeps system + task = %s (kept %s)" % (pinned_keeps_goal, pids))

    pinned_keeps_recent = latest in pids
    print("  pinned compaction keeps the most recent turn (%s) = %s" % (latest, pinned_keeps_recent))

    both_under_budget = total(f) <= budget and total(p) <= budget
    print("  both strategies fit the budget = %s (FIFO %d, pinned %d, budget %d)" % (both_under_budget, total(f), total(p), budget))

    ok = fifo_drops_system and fifo_drops_task and pinned_keeps_goal and pinned_keeps_recent and both_under_budget
    print("-" * 118)
    print("SELF-TEST %s  fifo_drops_system=%s  fifo_drops_task=%s  pinned_keeps_goal=%s  pinned_keeps_recent=%s  both_under_budget=%s"
          % ("PASS" if ok else "FAIL", fifo_drops_system, fifo_drops_task, pinned_keeps_goal, pinned_keeps_recent, both_under_budget))
    return ok


def main():
    p = argparse.ArgumentParser(description="Conversation history compaction: when an agent transcript exceeds the context budget, naive FIFO drops the oldest messages -- the system prompt and the task -- so the agent forgets its instructions and goal; pin those and fill the rest of the budget with the most recent turns (summarizing the middle) so the agent stays on-task and current.")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--recall", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("messages=%d  total=%d tokens  budget=%d  file=%s  (the transcript and budget are a fixture)"
          % (len(data["messages"]), total(data["messages"]), data["budget"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.compact:
        compact_view(data)
    elif args.recall:
        recall_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
