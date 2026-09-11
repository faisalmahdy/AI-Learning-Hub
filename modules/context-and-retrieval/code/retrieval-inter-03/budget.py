#!/usr/bin/env python3
"""Retrieved is not injected: a token budget, and the redundant chunk that eats it.

Retrieval returns more chunks than fit in the model's context window, so a budget
step chooses which retrieved chunks are actually injected. The naive choice --
walk the ranking and take chunks until the budget is full -- looks obviously
right and quietly fails: a high-scoring chunk and its near-duplicate both get
taken, spend the whole budget saying the same thing, and crowd out the lower-
ranked chunk that holds the one other fact the query needs. Dedup first, select
for coverage, and the same budget answers the question.

  --candidates Q   the retrieved chunks for one query: score, tokens, facts carried
  --select Q       rank-fill vs dedup-coverage for one query, what each injects
  --measure        answer coverage and injected tokens, both selectors, all queries
  --check          rank-fill busts coverage under budget; dedup-coverage restores it

Builds on retrieval-inter-01/02: chunks already scored and sized. Stdlib only
(math.sqrt for the duplicate check). No network, no model. The corpus is a fixture.
"""
import argparse
import json
import re
import sys
from math import sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "candidates.json"

DUP_SIM = 0.8      # cosine at or above this counts two chunks as near-duplicates


def load():
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    return data["budget"], data["queries"]


def toks(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def tf(text):
    v = {}
    for t in toks(text):
        v[t] = v.get(t, 0) + 1
    return v


def cosine(a, b):
    va, vb = tf(a), tf(b)
    dot = sum(w * vb.get(t, 0) for t, w in va.items())
    na = sqrt(sum(w * w for w in va.values()))
    nb = sqrt(sum(w * w for w in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


def cost(chunk):
    return len(toks(chunk["text"]))


# --------------------------------------------------------------- the selectors

def rank_fill(chunks, budget):
    """THE BUG: walk the ranking, take each chunk if it still fits. Redundancy is
    invisible to it, so a chunk and its near-duplicate can both be taken."""
    picked, used = [], 0
    for ch in sorted(chunks, key=lambda c: (-c["score"], c["id"])):
        if used + cost(ch) <= budget:
            picked.append(ch)
            used += cost(ch)
    return picked


def dedup_coverage(chunks, budget):
    """Drop a chunk that near-duplicates one already taken (it adds tokens, no new
    information), then fill by score under the budget."""
    picked, used = [], 0
    for ch in sorted(chunks, key=lambda c: (-c["score"], c["id"])):
        if any(cosine(ch["text"], p["text"]) >= DUP_SIM for p in picked):
            continue                                   # redundant: skip, keep the budget
        if used + cost(ch) <= budget:
            picked.append(ch)
            used += cost(ch)
    return picked


SELECTORS = [("rank-fill (bug)", rank_fill), ("dedup-coverage (fix)", dedup_coverage)]


# ---------------------------------------------------------------- the metric

def facts_present(picked, needed):
    """Which required facts appear in the injected set."""
    have = set()
    for ch in picked:
        have |= set(ch["facts"])
    return have & set(needed)


def evaluate(budget, queries, selector):
    covered = total = injected = 0
    for item in queries:
        picked = selector(item["chunks"], budget)
        got = facts_present(picked, item["needs"])
        covered += len(got)
        total += len(item["needs"])
        injected += sum(cost(c) for c in picked)
    return covered, total, injected / len(queries)


# ------------------------------------------------------------------- printing

def candidates_view(budget, queries, q):
    item = next(i for i in queries if i["q"] == q)
    print("CANDIDATES — %r   (budget = %d tokens, needs facts %s)" % (q, budget, item["needs"]))
    print("-" * 66)
    for ch in sorted(item["chunks"], key=lambda c: (-c["score"], c["id"])):
        print("  %-6s score %.2f  %2d tok  facts=%s" % (ch["id"], ch["score"], cost(ch), ch["facts"]))
    print("-" * 66)
    print("  more tokens here than the budget holds; something must be dropped.")


def select_view(budget, queries, q):
    item = next(i for i in queries if i["q"] == q)
    print("SELECTION — %r   (budget = %d tokens, needs %s)" % (q, budget, item["needs"]))
    print("-" * 66)
    for label, selector in SELECTORS:
        picked = selector(item["chunks"], budget)
        ids = [c["id"] for c in picked]
        got = facts_present(picked, item["needs"])
        used = sum(cost(c) for c in picked)
        print("  %-22s inject %s = %d tok, facts %s%s"
              % (label, ids, used, sorted(got),
                 "  <-- MISSING %s" % sorted(set(item["needs"]) - got) if got != set(item["needs"]) else "  (complete)"))
    print("-" * 66)


def measure(budget, queries):
    print("CONTEXT BUDGET — answer coverage and injected tokens (budget = %d)" % budget)
    print("-" * 66)
    print("  selector                coverage    avg tokens injected")
    for label, selector in SELECTORS:
        cov, tot, avg = evaluate(budget, queries, selector)
        print("  %-22s  %d/%d        %5.1f" % (label, cov, tot, avg))
    print("-" * 66)
    print("  same budget, same candidates: rank-fill spends tokens on duplicates and")
    print("  drops facts; dedup-coverage spends them on new information and keeps them.")


def check(budget, queries):
    print("SELF-TEST — rank-fill busts coverage under budget; dedup restores it")
    print("-" * 66)
    rf_cov, tot, rf_tok = evaluate(budget, queries, rank_fill)
    dc_cov, _, dc_tok = evaluate(budget, queries, dedup_coverage)
    print("  rank-fill coverage=%d/%d  dedup-coverage coverage=%d/%d" % (rf_cov, tot, dc_cov, tot))

    dedup_better = dc_cov > rf_cov
    print("  dedup-coverage answers more facts than rank-fill = %s (%d > %d)" % (dedup_better, dc_cov, rf_cov))

    within = all(sum(cost(c) for c in dedup_coverage(i["chunks"], budget)) <= budget for i in queries)
    print("  dedup-coverage never exceeds the budget = %s" % within)

    # the mechanism: rank-fill injects a near-duplicate pair somewhere.
    took_dup = False
    for i in queries:
        picked = rank_fill(i["chunks"], budget)
        for a in range(len(picked)):
            for b in range(a + 1, len(picked)):
                if cosine(picked[a]["text"], picked[b]["text"]) >= DUP_SIM:
                    took_dup = True
    print("  rank-fill injects a near-duplicate pair somewhere = %s" % took_dup)

    dc_cheaper = dc_tok <= rf_tok
    print("  dedup-coverage injects no more tokens than rank-fill = %s (%.1f <= %.1f)" % (dc_cheaper, dc_tok, rf_tok))

    det = [c["id"] for c in dedup_coverage(queries[0]["chunks"], budget)] == \
        [c["id"] for c in dedup_coverage(queries[0]["chunks"], budget)]

    ok = dedup_better and within and took_dup and dc_cheaper and det
    print("-" * 66)
    print("SELF-TEST %s  dedup_better=%s  within_budget=%s  dup_taken=%s  cheaper=%s  det=%s"
          % ("PASS" if ok else "FAIL", dedup_better, within, took_dup, dc_cheaper, det))
    return ok


def main():
    p = argparse.ArgumentParser(description="Budget retrieved chunks into a context window.")
    p.add_argument("--candidates", metavar="Q")
    p.add_argument("--select", metavar="Q")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    budget, queries = load()
    print("budget=%d tok  queries=%d  file=%s  (candidates are a fixture)"
          % (budget, len(queries), CORPUS.name))
    print("")

    if args.check:
        return 0 if check(budget, queries) else 1
    if args.candidates:
        candidates_view(budget, queries, args.candidates)
    elif args.select:
        select_view(budget, queries, args.select)
    elif args.measure:
        measure(budget, queries)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
