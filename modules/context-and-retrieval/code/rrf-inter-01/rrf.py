"""Fuse two retrievers by RANK, not by raw score -- adding a lexical and a dense score lets the bigger scale win alone.

Hybrid search combines a lexical retriever (BM25, keyword overlap) with a dense retriever (cosine similarity of
embeddings), because each finds documents the other misses: BM25 nails exact terms and rare tokens, dense finds
paraphrases and synonyms with no shared words. To return one ranked list you have to FUSE the two, and the obvious way
-- add each document's two scores and sort -- is broken, because the two scores are not on the same scale. BM25 is
unbounded: a strong keyword match can score 40 while a weak one scores 5. Cosine is bounded in [0,1]. Add them and the
BM25 term dominates every sum; the cosine term, never larger than 1, is a rounding error next to a BM25 of 40. So the
'fused' ranking is just the BM25 ranking with imperceptible jitter, and the dense retriever -- the whole reason you
added semantic search -- contributes nothing. The documents dense retrieval exists to surface, strong semantic matches
with few shared keywords, are exactly the ones buried.

Reciprocal Rank Fusion fixes this by throwing away the raw scores and fusing the RANKS. Each retriever contributes
1/(k+rank) for a document, where rank is its position in that retriever's list (1 for the top) and k is a small constant,
and the document's fused score is the sum of these across retrievers. Rank is scale-free: being #1 by BM25 is worth the
same as being #1 by cosine, no matter that one raw score is 40 and the other is 0.95. So both retrievers get an equal
vote, a document ranked highly by EITHER is rewarded, and a document ranked highly by BOTH rises to the top. RRF needs no
score normalization, no tuning of per-retriever weights, and no assumption that the scores are comparable -- it only
needs each retriever to produce an ordering, which is why it is the default fusion in many hybrid search systems.

On this fixture d1 has the biggest BM25 (40) but weak cosine (0.20), while d3 is the top semantic match (cosine 0.95)
with modest BM25 (10). Raw-score fusion ranks d1, d2, d3, d4, d5 -- identical to the BM25 order, with d3 stuck at 3rd
because its 0.95 cosine cannot move a sum dominated by BM25. RRF ranks d3 first: d3 is #1 by cosine and #3 by BM25, and
its rank votes beat d1's #1-BM25/#4-cosine split. Multiplying every BM25 score by 1000 leaves the RRF result identical,
because RRF never looks at the magnitudes. This computes all of it.

  --fuse    each retriever's ranks, the naive raw-score fusion (echoes BM25), and the RRF fusion (surfaces the semantic match)
  --scale   put cosine on a 0-100 scale instead of 0-1; the naive order flips to the cosine order, the RRF order is unchanged
  --check   naive fusion reproduces the BM25 order and buries the dense-top doc; RRF surfaces it and ignores score scale

The scores and rrf_k are the fixture; every rank and fused order is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "rrf.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def order_by(scores):
    """Document ids sorted by score, highest first."""
    return sorted(scores, key=lambda d: scores[d], reverse=True)


def ranks(scores):
    """Map each document to its 1-based rank under a retriever's scores (1 = top)."""
    return {d: i + 1 for i, d in enumerate(order_by(scores))}


def naive_fuse(docs):
    """Add the raw bm25 and cosine scores -- broken: the unbounded bm25 scale dominates the [0,1] cosine."""
    return {d: docs[d]["bm25"] + docs[d]["cosine"] for d in docs}


def rrf_fuse(docs, k):
    """Reciprocal Rank Fusion: sum 1/(k+rank) across retrievers, using ranks not raw scores."""
    bm = ranks({d: docs[d]["bm25"] for d in docs})
    co = ranks({d: docs[d]["cosine"] for d in docs})
    return {d: 1 / (k + bm[d]) + 1 / (k + co[d]) for d in docs}


# ----------------------------------------------------------------- printing

def fuse_view(data):
    docs, k = data["docs"], data["rrf_k"]
    bm = ranks({d: docs[d]["bm25"] for d in docs})
    co = ranks({d: docs[d]["cosine"] for d in docs})
    print("FUSE — per-retriever ranks, then naive raw-sum vs RRF")
    print("-" * 66)
    print("  doc   bm25    (rank)   cosine   (rank)")
    for d in sorted(docs):
        print("  %-4s  %-6.1f  (%d)      %-5.2f    (%d)" % (d, docs[d]["bm25"], bm[d], docs[d]["cosine"], co[d]))
    print("-" * 66)
    print("  bm25 order        : %s" % order_by({d: docs[d]["bm25"] for d in docs}))
    print("  naive raw-sum     : %s   <- identical to bm25; cosine ignored" % order_by(naive_fuse(docs)))
    print("  RRF (k=%d)        : %s   <- d3 (top cosine) surfaces to #1" % (k, order_by(rrf_fuse(docs, k))))


def scale_view(data):
    docs, k = data["docs"], data["rrf_k"]
    scaled = {d: {"bm25": docs[d]["bm25"], "cosine": docs[d]["cosine"] * 100} for d in docs}
    print("SCALE — put cosine on a 0-100 scale (x100) instead of 0-1, then re-fuse")
    print("-" * 62)
    print("  naive raw-sum, cosine in [0,1]   : %s" % order_by(naive_fuse(docs)))
    print("  naive raw-sum, cosine x100       : %s   <- flipped to the cosine order" % order_by(naive_fuse(scaled)))
    print("  RRF, cosine in [0,1]             : %s" % order_by(rrf_fuse(docs, k)))
    print("  RRF, cosine x100                 : %s   <- unchanged" % order_by(rrf_fuse(scaled, k)))
    print("-" * 62)
    print("  naive fusion depends on an arbitrary scale choice; RRF depends only on ranks, so its order is fixed.")


def check(data):
    print("SELF-TEST — naive fusion reproduces the BM25 order and buries the dense-top doc; RRF surfaces it and ignores score scale")
    print("-" * 122)
    docs, k = data["docs"], data["rrf_k"]
    bm_order = order_by({d: docs[d]["bm25"] for d in docs})
    co_order = order_by({d: docs[d]["cosine"] for d in docs})

    naive_order = order_by(naive_fuse(docs))
    naive_is_bm25 = naive_order == bm_order
    print("  naive raw-sum fusion reproduces the BM25 order = %s (%s)" % (naive_is_bm25, naive_order))

    dense_top = co_order[0]
    dense_top_buried = naive_order.index(dense_top) > 0
    print("  the top dense match (%s) is NOT first under naive fusion = %s (rank %d)"
          % (dense_top, dense_top_buried, naive_order.index(dense_top) + 1))

    rrf_order = order_by(rrf_fuse(docs, k))
    rrf_surfaces_dense = rrf_order[0] == dense_top
    print("  RRF ranks the top dense match first = %s (%s)" % (rrf_surfaces_dense, rrf_order))

    rrf_differs = rrf_order != bm_order
    print("  the RRF order differs from the BM25 order = %s" % rrf_differs)

    scaled = {d: {"bm25": docs[d]["bm25"], "cosine": docs[d]["cosine"] * 100} for d in docs}
    rrf_scale_free = order_by(rrf_fuse(scaled, k)) == rrf_order
    print("  putting cosine on a 0-100 scale leaves the RRF order unchanged = %s" % rrf_scale_free)

    ok = naive_is_bm25 and dense_top_buried and rrf_surfaces_dense and rrf_differs and rrf_scale_free
    print("-" * 122)
    print("SELF-TEST %s  naive_is_bm25=%s  dense_top_buried=%s  rrf_surfaces_dense=%s  rrf_differs=%s  rrf_scale_free=%s"
          % ("PASS" if ok else "FAIL", naive_is_bm25, dense_top_buried, rrf_surfaces_dense, rrf_differs, rrf_scale_free))
    return ok


def main():
    p = argparse.ArgumentParser(description="Reciprocal Rank Fusion: hybrid search must fuse a lexical (BM25, unbounded) and dense (cosine, [0,1]) retriever, and adding the raw scores lets the larger scale dominate so the fused ranking just echoes BM25; RRF fuses the ranks (sum of 1/(k+rank)), which is scale-free, gives each retriever an equal vote, and surfaces documents ranked highly by either or both.")
    p.add_argument("--fuse", action="store_true")
    p.add_argument("--scale", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("docs=%d  rrf_k=%d  file=%s  (the bm25/cosine scores are a fixture)"
          % (len(data["docs"]), data["rrf_k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.fuse:
        fuse_view(data)
    elif args.scale:
        scale_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
