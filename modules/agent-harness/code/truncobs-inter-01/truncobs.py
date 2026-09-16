"""Truncate an oversized tool observation by relevance, not by position -- head/tail truncation can delete the answer.

An agent works by calling a tool and reading the observation the tool returns. But observations do not fit a fixed
budget: a log search, a file read, a database query can each return far more text than the harness can paste back into
the model's limited context. So the harness truncates -- and HOW it truncates decides what the agent can still know. The
easy truncations are positional: keep the first N lines (head) or the last N lines (tail). They are trivial to
implement and they are a trap, because the line that actually answers the agent's question has no reason to sit at the
top or the bottom of the output. A grep hit, an error, the one row you asked for -- these land wherever the data puts
them, often in the middle, and a positional truncation that keeps the ends deletes exactly the middle. The agent then
reads a plausible-looking observation with the answer removed, concludes 'not found', and either gives up or
hallucinates -- and nothing in the transcript shows that the harness, not the tool, hid the answer.

The fix is to truncate by relevance to the query the agent is pursuing: keep the lines that match (plus a little
surrounding context for readability), and drop the non-matching filler, all within the same budget. A matching line is
worth more than a filler line, so under a tight budget you spend the budget on the match. This does not need a model --
the agent already has a query (the term it searched for, the id it asked about), and the harness scores lines by that
query and keeps the highest-scoring ones. The principle generalizes: an observation budget is a scarce resource, and
spending it on whatever happened to be printed first is the one allocation guaranteed to sometimes spend it all on
filler.

On this fixture a log-search tool returned 20 lines and the budget is 6. The one ERROR line -- 'write failed: disk full'
-- is line 10, in the middle. Head-truncation keeps lines 1-6 and drops it; tail-truncation keeps lines 15-20 and drops
it; both leave the agent with no error in view, so it reports the service healthy. Relevance-truncation keeps the ERROR
line plus its neighbors and the agent finds the disk-full failure -- same 6-line budget, opposite answer. This computes
all three.

  --truncate  each strategy's kept lines under the budget, and whether the ERROR needle survived
  --answer    the conclusion the agent reaches from each truncated observation -- head/tail miss the outage, relevance finds it
  --check     the needle is in neither the head nor the tail window; head and tail truncation drop it; relevance keeps it

The lines, query, and budget are the fixture; which lines each strategy keeps is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "truncobs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def truncate_head(lines, budget):
    """Keep the first `budget` lines -- positional, ignores what the agent asked for."""
    return lines[:budget]


def truncate_tail(lines, budget):
    """Keep the last `budget` lines -- positional, ignores what the agent asked for."""
    return lines[-budget:]


def truncate_relevant(lines, query, budget):
    """Keep the lines matching `query`, then expand outward for context until the budget is full."""
    matched = [i for i, line in enumerate(lines) if query in line]
    if not matched:
        return lines[:budget]
    selected = set(matched)
    radius = 1
    while len(selected) < budget:
        grew = False
        for m in matched:
            for j in (m - radius, m + radius):
                if 0 <= j < len(lines) and j not in selected and len(selected) < budget:
                    selected.add(j)
                    grew = True
        if not grew:
            break
        radius += 1
    return [lines[i] for i in sorted(selected)]


def contains(view, query):
    return any(query in line for line in view)


# ----------------------------------------------------------------- printing

def truncate_view(data):
    lines, query, budget = data["lines"], data["query"], data["budget"]
    print("TRUNCATE — %d lines into a %d-line budget; needle = the %r line" % (len(lines), budget, query))
    print("-" * 66)
    for name, view in (("head", truncate_head(lines, budget)),
                       ("tail", truncate_tail(lines, budget)),
                       ("relevant", truncate_relevant(lines, query, budget))):
        kept = contains(view, query)
        print("  %-9s keeps: %s" % (name, [l.split(":")[0] for l in view]))
        print("  %-9s needle present = %s" % ("", kept))
    print("-" * 66)


def answer_view(data):
    lines, query, budget = data["lines"], data["query"], data["budget"]
    print("ANSWER — what the agent concludes from each truncated observation")
    print("-" * 66)
    for name, view in (("head", truncate_head(lines, budget)),
                       ("tail", truncate_tail(lines, budget)),
                       ("relevant", truncate_relevant(lines, query, budget))):
        hit = [l for l in view if query in l]
        if hit:
            print("  %-9s -> found: %s" % (name, hit[0]))
        else:
            print("  %-9s -> no %r in view: agent reports the service healthy (WRONG)" % (name, query))
    print("-" * 66)
    print("  same 6-line budget, opposite conclusions -- the truncation strategy decided the answer.")


def check(data):
    print("SELF-TEST — the needle is in neither the head nor the tail window; head and tail truncation drop it; relevance keeps it")
    print("-" * 118)
    lines, query, budget = data["lines"], data["query"], data["budget"]

    needle = next(i for i, l in enumerate(lines) if query in l)
    needle_in_middle = budget <= needle < len(lines) - budget
    print("  the needle line is in the middle, outside both end windows = %s (line %d of %d, budget %d)"
          % (needle_in_middle, needle + 1, len(lines), budget))

    head_misses = not contains(truncate_head(lines, budget), query)
    print("  head-truncation drops the needle = %s" % head_misses)

    tail_misses = not contains(truncate_tail(lines, budget), query)
    print("  tail-truncation drops the needle = %s" % tail_misses)

    rel = truncate_relevant(lines, query, budget)
    relevance_keeps = contains(rel, query)
    print("  relevance-truncation keeps the needle = %s (%s)" % (relevance_keeps, [l.split(":")[0] for l in rel]))

    same_budget = len(truncate_head(lines, budget)) == len(rel) == budget
    print("  all strategies obey the same line budget = %s (%d lines each)" % (same_budget, budget))

    ok = needle_in_middle and head_misses and tail_misses and relevance_keeps and same_budget
    print("-" * 118)
    print("SELF-TEST %s  needle_in_middle=%s  head_misses=%s  tail_misses=%s  relevance_keeps=%s  same_budget=%s"
          % ("PASS" if ok else "FAIL", needle_in_middle, head_misses, tail_misses, relevance_keeps, same_budget))
    return ok


def main():
    p = argparse.ArgumentParser(description="Observation truncation by relevance: an oversized tool result must be truncated to fit the observation budget, and positional (head/tail) truncation can delete the one line that answers the agent's query, so the agent reports 'not found'; scoring lines by the agent's query and keeping the matches preserves the answer under the same budget.")
    p.add_argument("--truncate", action="store_true")
    p.add_argument("--answer", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("lines=%d  query=%r  budget=%d  file=%s  (the lines, query, and budget are a fixture)"
          % (len(data["lines"]), data["query"], data["budget"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.truncate:
        truncate_view(data)
    elif args.answer:
        answer_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
