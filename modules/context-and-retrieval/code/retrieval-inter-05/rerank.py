#!/usr/bin/env python3
"""Rerank for precision -- but a reranker can only reorder what the first stage returned.

Retrieval is usually two stages: a cheap, recall-oriented retriever (approximate
nearest-neighbour over quantized vectors) pulls a pool of k candidates, then an
expensive, precise reranker (a cross-encoder) reorders that pool so the best one
lands on top. The reranker is only as good as the pool it is handed: if the first
stage's top-k misses the answer, no reranker can promote a document it never
received. So the first-stage k is a recall dial, and setting it too small silently
caps the whole pipeline below the reranker's real accuracy -- the reranker looks
broken when the retriever starved it. This measures the ceiling.

  --stage1 K     the cheap retriever's top-K per query, and whether the gold is in it
  --pipeline K   retrieve K, then rerank; the final hit@1 at that pool size
  --sweep        first-stage recall@K and pipeline hit@1 as K grows -- the ceiling
  --check        pipeline hit@1 is bounded by recall@K; widen K and it rises

Each candidate carries a cheap score (the first stage's) and a precise score (the
reranker's), a fixture standing in for real ANN and cross-encoder outputs. Stdlib
only. No model, no network. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "candidates.json"


def load():
    return json.loads(CORPUS.read_text(encoding="utf-8"))["queries"]


# --------------------------------------------------------- stage 1 and the reranker

def stage1_ranked(query):
    """The cheap first stage orders candidates by their cheap (approximate) score."""
    return sorted(query["candidates"], key=lambda c: (-c["cheap"], c["id"]))


def stage1_topk(query, k):
    return [c["id"] for c in stage1_ranked(query)[:k]]


def pipeline_top1(query, k):
    """Take the first stage's top-k, then rerank that pool by the precise score."""
    pool = stage1_ranked(query)[:k]
    best = max(pool, key=lambda c: (c["precise"], -ord(c["id"][0])))
    return best["id"]


# ---------------------------------------------------------------- the metrics

def recall_at_k(queries, k):
    return sum(1 for q in queries if q["gold"] in stage1_topk(q, k))


def pipeline_hit1(queries, k):
    return sum(1 for q in queries if pipeline_top1(q, k) == q["gold"])


def stage1_hit1(queries):
    return sum(1 for q in queries if stage1_topk(q, 1)[0] == q["gold"])


# ------------------------------------------------------------------- printing

def stage1_view(queries, k):
    print("STAGE 1 — cheap retriever's top-%d, and whether the gold is inside" % k)
    print("-" * 66)
    for q in queries:
        pool = stage1_topk(q, k)
        print("  %-22s pool=%s gold=%s %s" % (q["q"][:22], pool, q["gold"], "IN" if q["gold"] in pool else "MISSED"))
    print("-" * 66)
    print("  recall@%d = %d/%d -- the ceiling on what any reranker can achieve." % (k, recall_at_k(queries, k), len(queries)))


def pipeline_view(queries, k):
    print("PIPELINE — retrieve %d, then rerank the pool, take the top" % k)
    print("-" * 66)
    for q in queries:
        top = pipeline_top1(q, k)
        print("  %-22s rerank top=%s  %s" % (q["q"][:22], top, "ok" if top == q["gold"] else "<-- wrong"))
    print("-" * 66)
    print("  pipeline hit@1 = %d/%d at k=%d." % (pipeline_hit1(queries, k), len(queries), k))


def sweep_view(queries):
    n = len(queries)
    print("SWEEP — first-stage recall@K vs pipeline hit@1 as the pool grows")
    print("-" * 66)
    print("  K    stage1 recall@K   pipeline hit@1")
    for k in (1, 2, 3, 5):
        print("  %-4d %d/%-14d %d/%d" % (k, recall_at_k(queries, k), n, pipeline_hit1(queries, k), n))
    print("-" * 66)
    print("  hit@1 never exceeds recall@K: the reranker cannot promote a document the")
    print("  retriever did not return. Widen K for recall, then rerank for precision.")


def check(queries):
    print("SELF-TEST — the reranker is capped by first-stage recall; widening K lifts it")
    print("-" * 66)
    n = len(queries)

    capped = all(pipeline_hit1(queries, k) <= recall_at_k(queries, k) for k in (1, 2, 3, 5))
    print("  pipeline hit@1 <= recall@K at every K = %s" % capped)

    h1, h3 = pipeline_hit1(queries, 1), pipeline_hit1(queries, 3)
    widen_helps = h3 > h1
    print("  widening K=1 -> K=3 raises pipeline hit@1 = %s (%d -> %d)" % (widen_helps, h1, h3))

    r3 = recall_at_k(queries, 3)
    full_at_3 = r3 == n and h3 == n
    print("  at K=3 recall is full (%d/%d) and rerank hit@1 is full (%d/%d) = %s" % (r3, n, h3, n, full_at_3))

    s1 = stage1_hit1(queries)
    beats_stage1 = h3 > s1
    print("  reranking a wide pool beats the cheap stage's own top-1 = %s (%d vs %d)" % (beats_stage1, h3, s1))

    det = pipeline_top1(queries[0], 3) == pipeline_top1(queries[0], 3)
    ok = capped and widen_helps and full_at_3 and beats_stage1 and det
    print("-" * 66)
    print("SELF-TEST %s  capped=%s  widen_helps=%s  full_at_3=%s  beats_stage1=%s"
          % ("PASS" if ok else "FAIL", capped, widen_helps, full_at_3, beats_stage1))
    return ok


def main():
    p = argparse.ArgumentParser(description="Two-stage retrieve-then-rerank, and the recall ceiling.")
    p.add_argument("--stage1", type=int, metavar="K")
    p.add_argument("--pipeline", type=int, metavar="K")
    p.add_argument("--sweep", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    queries = load()
    print("queries=%d  file=%s  (candidate scores are a fixture)" % (len(queries), CORPUS.name))
    print("")

    if args.check:
        return 0 if check(queries) else 1
    if args.stage1 is not None:
        stage1_view(queries, args.stage1)
    elif args.pipeline is not None:
        pipeline_view(queries, args.pipeline)
    elif args.sweep:
        sweep_view(queries)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
