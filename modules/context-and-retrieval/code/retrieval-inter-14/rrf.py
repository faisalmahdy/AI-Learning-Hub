"""Fuse retrievers by rank, not by raw score, or one retriever's score scale outvotes the other.

Hybrid retrieval runs two retrievers -- a lexical one (BM25, scores maybe 0 to 30) and a dense one (cosine,
scores 0 to 1) -- and has to combine their rankings into one. The obvious way is to add the scores and
sort. It is broken, because the two score scales are not comparable. BM25's numbers are ten to a hundred
times larger than cosine's, so summing them lets the lexical score dominate every fusion: the combined
ranking is essentially the lexical ranking with a rounding error, and the dense retriever's opinion barely
counts. Worse, the winner depends on the arbitrary units each retriever happens to use -- rescale one and
the fused order changes -- so 'add the scores' does not even give a stable answer.

Reciprocal rank fusion (RRF) throws away the scores and keeps only the ranks. Each retriever contributes
1 / (k + rank) for a document, summed across retrievers, where k is a small constant (60 is standard). A
document ranked near the top of both lists scores high; a document ranked first in one list but buried in
the other cannot win. Because only the rank order is used, RRF is immune to the score-scale problem -- the
units cancel out entirely -- and it rewards consensus, which is exactly what you want from a fusion: the
document both retrievers agree is relevant, even if neither ranked it first.

On this fixture the true answer ranks second in both retrievers -- strong agreement, first in neither. A
lexical distractor ranks first on BM25 (score 28) but fourth on cosine; a dense distractor is the mirror
image. Raw-score fusion crowns the lexical distractor, because its BM25 score of 28 swamps everything, and
rescaling the dense scores flips the winner to the dense distractor -- proof the method depends on units.
RRF crowns the true answer and does not budge when the scores are rescaled. This computes both.

  --rank       each document's rank and score in each retriever
  --fuse       the fused ranking under raw-score sum vs RRF, and how each changes when dense is rescaled
  --check      raw-score fusion picks a distractor and is scale-dependent; RRF picks the answer and is invariant

The retriever scores and the answer id are the fixture; every rank and fusion is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "retrievers.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def ranks(scores):
    """Map each document to its 1-based rank (highest score = rank 1)."""
    order = sorted(scores, key=lambda d: scores[d], reverse=True)
    return {doc: i + 1 for i, doc in enumerate(order)}


def fuse_rawscore(retrievers):
    """Fuse by summing raw scores across retrievers -- sensitive to each retriever's scale."""
    docs = next(iter(retrievers.values())).keys()
    total = {d: sum(r[d] for r in retrievers.values()) for d in docs}
    return sorted(total, key=lambda d: total[d], reverse=True), total


def fuse_rrf(retrievers, k):
    """Fuse by reciprocal rank: sum 1/(k+rank) across retrievers -- uses only rank order."""
    rank_maps = {name: ranks(scores) for name, scores in retrievers.items()}
    docs = next(iter(retrievers.values())).keys()
    total = {d: sum(1.0 / (k + rm[d]) for rm in rank_maps.values()) for d in docs}
    return sorted(total, key=lambda d: total[d], reverse=True), total


def scaled(retrievers, name, factor):
    """Return a copy with one retriever's scores multiplied by factor (same ranking, different scale)."""
    out = {n: dict(s) for n, s in retrievers.items()}
    out[name] = {d: v * factor for d, v in out[name].items()}
    return out


# ----------------------------------------------------------------- printing

def rank_view(data):
    retr, ans = data["retrievers"], data["answer"]
    print("RANK — each document's rank and score per retriever (answer = %s)" % ans)
    print("-" * 60)
    rank_maps = {name: ranks(scores) for name, scores in retr.items()}
    print("  doc     " + "   ".join("%-14s" % n for n in retr))
    for d in next(iter(retr.values())):
        tag = "  <- answer" if d == ans else ""
        cells = "   ".join("rank %d (%.2f)  " % (rank_maps[n][d], retr[n][d]) for n in retr)
        print("  %-6s  %s%s" % (d, cells, tag))
    print("-" * 60)
    print("  the answer is rank 2 in both — strong agreement, first in neither.")


def fuse_view(data):
    retr, ans, k = data["retrievers"], data["answer"], data["k"]
    dense = list(retr)[1]
    scaled_retr = scaled(retr, dense, 1000)
    print("FUSE — top document under each method (k=%d), original vs dense rescaled x1000" % k)
    print("-" * 60)
    print("  raw-score:  top %s   (rescaled: top %s)" % (fuse_rawscore(retr)[0][0], fuse_rawscore(scaled_retr)[0][0]))
    print("  RRF:        top %s   (rescaled: top %s)" % (fuse_rrf(retr, k)[0][0], fuse_rrf(scaled_retr, k)[0][0]))
    print("-" * 60)
    print("  answer is %s; raw-score misses it and moves when rescaled, RRF holds." % ans)


def check(data):
    print("SELF-TEST — raw-score fusion picks a distractor and is scale-dependent; RRF picks the answer and is invariant")
    print("-" * 108)
    retr, ans, k = data["retrievers"], data["answer"], data["k"]
    dense = list(retr)[1]
    scaled_retr = scaled(retr, dense, 1000)

    rank_maps = {name: ranks(scores) for name, scores in retr.items()}
    answer_top_neither = all(rm[ans] != 1 for rm in rank_maps.values())
    print("  the answer is first in neither retriever = %s (ranks %s)"
          % (answer_top_neither, [rank_maps[n][ans] for n in retr]))

    raw_top = fuse_rawscore(retr)[0][0]
    rawscore_wrong = raw_top != ans
    print("  raw-score fusion's top is not the answer = %s (top %s)" % (rawscore_wrong, raw_top))

    rrf_top = fuse_rrf(retr, k)[0][0]
    rrf_correct = rrf_top == ans
    print("  RRF's top is the answer = %s (top %s)" % (rrf_correct, rrf_top))

    rrf_invariant = fuse_rrf(scaled_retr, k)[0][0] == rrf_top
    print("  RRF's top is unchanged when dense is rescaled = %s (%s)" % (rrf_invariant, fuse_rrf(scaled_retr, k)[0][0]))

    rawscore_scale_dependent = fuse_rawscore(scaled_retr)[0][0] != raw_top
    print("  raw-score fusion's top changes when dense is rescaled = %s (%s -> %s)"
          % (rawscore_scale_dependent, raw_top, fuse_rawscore(scaled_retr)[0][0]))

    ok = answer_top_neither and rawscore_wrong and rrf_correct and rrf_invariant and rawscore_scale_dependent
    print("-" * 108)
    print("SELF-TEST %s  answer_top_neither=%s  rawscore_wrong=%s  rrf_correct=%s  rrf_invariant=%s  rawscore_scale_dependent=%s"
          % ("PASS" if ok else "FAIL", answer_top_neither, rawscore_wrong, rrf_correct, rrf_invariant, rawscore_scale_dependent))
    return ok


def main():
    p = argparse.ArgumentParser(description="Fuse retrievers by reciprocal rank, not raw score.")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--fuse", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("retrievers=%s  answer=%s  k=%d  file=%s  (the scores and answer are a fixture)"
          % (list(data["retrievers"]), data["answer"], data["k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rank:
        rank_view(data)
    elif args.fuse:
        fuse_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
