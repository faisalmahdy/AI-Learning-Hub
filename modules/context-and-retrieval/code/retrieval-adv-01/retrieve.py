#!/usr/bin/env python3
"""A hybrid retrieval pipeline end to end: lexical + dense, fused, then reranked.

No single retriever is enough. Lexical retrieval (BM25-style term overlap) finds documents
that share rare exact terms with the query and misses paraphrases; dense retrieval (embedding
cosine) finds paraphrases and can miss an exact keyword. On a mixed query set each recovers
only its own half. The production answer is a pipeline: run both, FUSE their rankings so the
gold is recovered whichever retriever found it, then RERANK the fused top-k with a precise
cross-encoder to lift the gold to rank 1.

The fusion must be rank-based, not score-based. Lexical scores are term counts (0..20+) and
dense scores are cosines (0..1); adding them lets the larger scale dominate, so a raw-sum
fusion just reproduces the lexical ranking and throws away the dense half. Reciprocal rank
fusion (RRF) combines the RANKS -- 1/(k0 + rank) summed across retrievers -- which is
scale-free, so a document ranked well by either retriever rises. This measures recall@1 and
recall@3 at every stage and the scale bug that raw-sum fusion falls into.

  --stages      recall@1 for lexical, dense, RRF fusion, and rerank -- the pipeline climbing
  --fusion      RRF (rank-based) vs raw-sum (score-based) -- the scale bug
  --check       fusion beats either retriever; rerank lifts recall@1 to full; raw-sum reproduces lexical

Stdlib only. Deterministic. Scores are a fixture.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "queries.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the retrievers

def rank_by(query, key):
    """Rank the docs by a per-doc score (lex, dense, or precise), descending, id-tiebroken."""
    return [d for d, _ in sorted(query["docs"].items(), key=lambda kv: (-kv[1][key], kv[0]))]


# ------------------------------------------------------------- fusion

def rrf_fuse(query, k0):
    """Reciprocal rank fusion: sum 1/(k0 + rank) across the lexical and dense rankings."""
    lex, den = rank_by(query, "lex"), rank_by(query, "dense")
    score = {d: 1.0 / (k0 + lex.index(d) + 1) + 1.0 / (k0 + den.index(d) + 1) for d in query["docs"]}
    return [d for d, _ in sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))]


def rawsum_fuse(query):
    """The bug: add the raw lexical and dense scores. The larger scale (lexical) dominates."""
    score = {d: v["lex"] + v["dense"] for d, v in query["docs"].items()}
    return [d for d, _ in sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))]


# ------------------------------------------------------------- rerank

def rerank(query, k0, k=3):
    """Take the fused top-k, reorder by the precise (cross-encoder) score."""
    pool = rrf_fuse(query, k0)[:k]
    return sorted(pool, key=lambda d: (-query["docs"][d]["precise"], d)) + rrf_fuse(query, k0)[k:]


# ------------------------------------------------------------- metrics

def recall_at(queries, ranker, at):
    return sum(1 for q in queries if q["gold"] in ranker(q)[:at])


# ----------------------------------------------------------------- printing

def stages_view(data):
    qs, k0 = data["queries"], data["rrf_k"]
    n = len(qs)
    print("STAGES — recall@1 through the pipeline (n=%d queries)" % n)
    print("-" * 66)
    print("  lexical only        recall@1 = %d/%d" % (recall_at(qs, lambda q: rank_by(q, "lex"), 1), n))
    print("  dense only          recall@1 = %d/%d" % (recall_at(qs, lambda q: rank_by(q, "dense"), 1), n))
    print("  RRF fusion          recall@1 = %d/%d   recall@3 = %d/%d"
          % (recall_at(qs, lambda q: rrf_fuse(q, k0), 1), n, recall_at(qs, lambda q: rrf_fuse(q, k0), 3), n))
    print("  + rerank top-3      recall@1 = %d/%d" % (recall_at(qs, lambda q: rerank(q, k0), 1), n))
    print("-" * 66)
    print("  each retriever gets half; fusion recovers both; rerank lifts them to rank 1.")


def fusion_view(data):
    qs, k0 = data["queries"], data["rrf_k"]
    n = len(qs)
    print("FUSION — reciprocal rank (scale-free) vs raw-sum (scale-dominated)")
    print("-" * 66)
    print("  lexical scale ~0..14, dense scale 0..1 -- adding them lets lexical dominate")
    print("  RRF fusion    recall@1 = %d/%d" % (recall_at(qs, lambda q: rrf_fuse(q, k0), 1), n))
    print("  raw-sum fusion recall@1 = %d/%d  (same as lexical alone -- dense half discarded)"
          % (recall_at(qs, rawsum_fuse, 1), n))
    print("-" * 66)
    print("  RRF combines ranks, so scale does not matter; raw-sum reproduces the lexical ranking.")


def check(data):
    print("SELF-TEST — fusion beats either retriever; rerank fills recall@1; raw-sum reproduces lexical")
    print("-" * 66)
    qs, k0 = data["queries"], data["rrf_k"]
    n = len(qs)

    lex1 = recall_at(qs, lambda q: rank_by(q, "lex"), 1)
    den1 = recall_at(qs, lambda q: rank_by(q, "dense"), 1)
    complementary = lex1 < n and den1 < n
    print("  neither retriever alone is complete = %s (lex %d, dense %d of %d)" % (complementary, lex1, den1, n))

    rrf1 = recall_at(qs, lambda q: rrf_fuse(q, k0), 1)
    fusion_beats = rrf1 > lex1 and rrf1 > den1
    print("  RRF fusion beats both single retrievers at recall@1 = %s (%d > %d, %d)" % (fusion_beats, rrf1, lex1, den1))

    rrf3 = recall_at(qs, lambda q: rrf_fuse(q, k0), 3)
    fusion_recall = rrf3 == n
    print("  RRF fusion gets every gold into the top-3 = %s (recall@3 = %d/%d)" % (fusion_recall, rrf3, n))

    rr1 = recall_at(qs, lambda q: rerank(q, k0), 1)
    rerank_lifts = rr1 == n and rr1 > rrf1
    print("  rerank lifts recall@1 to full = %s (%d/%d, up from %d)" % (rerank_lifts, rr1, n, rrf1))

    raw1 = recall_at(qs, rawsum_fuse, 1)
    rawsum_bug = raw1 == lex1 and raw1 < rrf1
    print("  raw-sum fusion collapses to lexical (the scale bug) = %s (%d, = lexical, < RRF %d)"
          % (rawsum_bug, raw1, rrf1))

    ok = complementary and fusion_beats and fusion_recall and rerank_lifts and rawsum_bug
    print("-" * 66)
    print("SELF-TEST %s  complementary=%s  fusion_beats=%s  fusion_recall=%s  rerank_lifts=%s  rawsum_bug=%s"
          % ("PASS" if ok else "FAIL", complementary, fusion_beats, fusion_recall, rerank_lifts, rawsum_bug))
    return ok


def main():
    p = argparse.ArgumentParser(description="Hybrid retrieval pipeline: lexical + dense, RRF fusion, rerank.")
    p.add_argument("--stages", action="store_true")
    p.add_argument("--fusion", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("queries=%d  rrf_k=%d  file=%s  (scores are a fixture)" % (len(data["queries"]), data["rrf_k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.stages:
        stages_view(data)
    elif args.fusion:
        fusion_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
