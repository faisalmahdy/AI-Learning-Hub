#!/usr/bin/env python3
"""MMR: rank retrieved chunks for relevance AND novelty -- pure top-k returns duplicates.

Retrieval scores each chunk for relevance and you keep the top k. The trouble is that
the most relevant chunks are often near-duplicates of each other: three passages all
about the same sub-topic, all scoring high, crowd out everything else. A query that needs
several things answered -- a drug's dosage AND side effects AND interactions -- gets three
dosage chunks and nothing else, and the answer built from that context is confidently
incomplete. Relevance alone optimizes for the single best sub-topic, repeated.

Maximal marginal relevance (MMR) fixes this by scoring each candidate for relevance MINUS
its similarity to what is already selected, so once a dosage chunk is picked, the next
dosage chunk is penalized and a side-effects chunk wins the slot. The result covers the
distinct sub-topics the answer needs, trading a little relevance for a lot of coverage.
This measures top-k coverage against MMR coverage.

  --topk        the pure-relevance top-k selection, and how many sub-topics it covers
  --mmr         the MMR selection, balancing relevance and novelty
  --check       top-k returns near-duplicates and covers fewer topics; MMR covers the needed ones

Stdlib only. Deterministic. Similarity is 1.0 within a topic, low across topics.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chunks.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- similarity

def similarity(a, b):
    """A stand-in for chunk-chunk similarity: high within a topic, low across topics."""
    return 1.0 if a["topic"] == b["topic"] else 0.15


def topics_covered(selected):
    return {c["topic"] for c in selected}


# ------------------------------------------------------------- the two selectors

def select_topk(chunks, k):
    """Pure relevance: the k highest-scoring chunks."""
    return sorted(chunks, key=lambda c: (-c["relevance"], c["id"]))[:k]


def select_mmr(chunks, k, lam):
    """Greedily pick the chunk maximizing lam*relevance - (1-lam)*max_sim_to_selected."""
    selected, remaining = [], list(chunks)
    while remaining and len(selected) < k:
        best, best_score = None, None
        for c in remaining:
            novelty_penalty = max((similarity(c, s) for s in selected), default=0.0)
            score = lam * c["relevance"] - (1 - lam) * novelty_penalty
            if best_score is None or score > best_score or (score == best_score and c["id"] < best["id"]):
                best, best_score = c, score
        selected.append(best)
        remaining.remove(best)
    return selected


# ----------------------------------------------------------------- printing

def topk_view(data):
    sel = select_topk(data["chunks"], data["k"])
    cov = topics_covered(sel)
    print("TOPK — pure relevance, top %d" % data["k"])
    print("-" * 66)
    for c in sel:
        print("  %-4s rel=%.2f  topic=%s" % (c["id"], c["relevance"], c["topic"]))
    print("-" * 66)
    print("  topics covered: %s (%d of %d needed)" % (sorted(cov), len(cov & set(data["needed_topics"])), len(data["needed_topics"])))
    print("  the highest-relevance chunks are near-duplicates on one sub-topic.")


def mmr_view(data):
    sel = select_mmr(data["chunks"], data["k"], data["lambda"])
    cov = topics_covered(sel)
    print("MMR — relevance minus redundancy (lambda=%.1f), top %d" % (data["lambda"], data["k"]))
    print("-" * 66)
    for c in sel:
        print("  %-4s rel=%.2f  topic=%s" % (c["id"], c["relevance"], c["topic"]))
    print("-" * 66)
    print("  topics covered: %s (%d of %d needed)" % (sorted(cov), len(cov & set(data["needed_topics"])), len(data["needed_topics"])))
    print("  once a topic is selected, its near-duplicates are penalized -- coverage rises.")


def check(data):
    print("SELF-TEST — top-k returns duplicates and covers fewer topics; MMR covers the needed ones")
    print("-" * 66)
    chunks, k, lam = data["chunks"], data["k"], data["lambda"]
    needed = set(data["needed_topics"])

    topk = select_topk(chunks, k)
    mmr = select_mmr(chunks, k, lam)
    topk_cov = topics_covered(topk)
    mmr_cov = topics_covered(mmr)

    topk_redundant = len(topk_cov) < k          # k chunks but fewer than k distinct topics
    print("  top-k selects near-duplicates (fewer topics than chunks) = %s (%d topics in %d chunks)"
          % (topk_redundant, len(topk_cov), k))

    mmr_more = len(mmr_cov) > len(topk_cov)
    print("  MMR covers more distinct topics than top-k = %s (%d vs %d)" % (mmr_more, len(mmr_cov), len(topk_cov)))

    mmr_covers_needed = needed.issubset(mmr_cov)
    print("  MMR covers every needed sub-topic = %s (%s)" % (mmr_covers_needed, sorted(needed)))
    topk_misses = not needed.issubset(topk_cov)
    print("  top-k misses a needed sub-topic = %s (missing %s)" % (topk_misses, sorted(needed - topk_cov)))

    # MMR still keeps the single most relevant chunk.
    top1 = max(chunks, key=lambda c: c["relevance"])["id"]
    mmr_keeps_top1 = any(c["id"] == top1 for c in mmr)
    print("  MMR still includes the most relevant chunk = %s (%s)" % (mmr_keeps_top1, top1))

    ok = topk_redundant and mmr_more and mmr_covers_needed and topk_misses and mmr_keeps_top1
    print("-" * 66)
    print("SELF-TEST %s  topk_redundant=%s  mmr_more=%s  mmr_covers_needed=%s  topk_misses=%s  mmr_keeps_top1=%s"
          % ("PASS" if ok else "FAIL", topk_redundant, mmr_more, mmr_covers_needed, topk_misses, mmr_keeps_top1))
    return ok


def main():
    p = argparse.ArgumentParser(description="Maximal marginal relevance vs pure top-k retrieval.")
    p.add_argument("--topk", action="store_true")
    p.add_argument("--mmr", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("chunks=%d  k=%d  lambda=%.1f  file=%s  (relevance and topics are a fixture)"
          % (len(data["chunks"]), data["k"], data["lambda"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.topk:
        topk_view(data)
    elif args.mmr:
        mmr_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
