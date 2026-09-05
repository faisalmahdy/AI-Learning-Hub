#!/usr/bin/env python3
"""A bag-of-words retriever, scored two ways, and measured honestly.

Retrieval is the first half of RAG: given a query, rank a corpus and return the
top few. This builds the smallest real retriever -- term-frequency vectors, one
score per document -- and then asks the question the whole track is about: did it
actually find the right note? It scores every query against a gold answer with
hit@k and MRR, and shows that the lenient metric (hit@3) calls a length-biased
retriever perfect while the honest one (hit@1, MRR) shows it burying the answer.

  --corpus     the notes and their lengths (the long junk-drawer page is the trap)
  --search Q   rank the corpus for one query, both scorers side by side
  --measure    hit@1, hit@3, MRR for raw dot-product vs length-normalised cosine
  --check      cosine self-similarity is 1, normalisation kills the length bias, seeds

Mirrors faisalmahdy/agent memory/retrieval.py, whose hash_embed L2-normalises and
whose cosine assumes unit vectors -- this shows what that normalisation buys.
Stdlib only (math.sqrt). No network, no model. The corpus is a fixture.
"""
import argparse
import json
import re
import sys
from math import sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus.json"

TOP_MEASURE = 3      # the lenient cutoff the naive metric reports


def load():
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    return data["docs"], data["queries"]


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def tf(text):
    """Term-frequency vector: {term: count}."""
    v = {}
    for t in tokens(text):
        v[t] = v.get(t, 0) + 1
    return v


# --------------------------------------------------------------- the two scores

def score_raw(q_vec, d_vec):
    """Raw dot product of term-frequency vectors. No length normalisation, so a
    long document with many words scores high just for being long."""
    return sum(w * d_vec.get(t, 0) for t, w in q_vec.items())


def score_cosine(q_vec, d_vec):
    """Cosine similarity: the dot product divided by both vector lengths, so score
    is direction (what the doc is about), not magnitude (how long it is)."""
    dot = sum(w * d_vec.get(t, 0) for t, w in q_vec.items())
    nq = sqrt(sum(w * w for w in q_vec.values()))
    nd = sqrt(sum(w * w for w in d_vec.values()))
    return dot / (nq * nd) if nq and nd else 0.0


def rank(docs, query, score):
    q_vec = tf(query)
    scored = [(did, score(q_vec, tf(text))) for did, text in docs.items()]
    # sort by score desc, then doc id for a deterministic tie-break.
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


# ---------------------------------------------------------------- the metrics

def rank_of_gold(ranked, gold):
    """1-based position of the gold doc in the ranking (len+1 if never returned)."""
    for i, (did, _) in enumerate(ranked, 1):
        if did == gold:
            return i
    return len(ranked) + 1


def measure(docs, queries, score):
    hit1 = hitk = 0
    rr_sum = 0.0
    for item in queries:
        r = rank_of_gold(rank(docs, item["q"], score), item["gold"])
        hit1 += 1 if r == 1 else 0
        hitk += 1 if r <= TOP_MEASURE else 0
        rr_sum += 1.0 / r
    n = len(queries)
    return hit1, hitk, rr_sum / n


# ------------------------------------------------------------------- printing

def show_corpus(docs, queries):
    print("CORPUS — ten short notes and one long junk-drawer page")
    print("-" * 66)
    for did, text in docs.items():
        n = len(tokens(text))
        flag = "  <-- long junk-drawer page" if n >= 60 else ""
        print("  %s  %3d tokens  %s%s" % (did, n, text[:40].replace("\n", " "), flag))
    print("-" * 66)
    print("  %d queries, each with one gold note it should return at rank 1." % len(queries))


def search(docs, query):
    print("SEARCH — %r, both scorers, top 4" % query)
    print("-" * 66)
    for label, score in (("raw dot-product", score_raw), ("cosine (length-fair)", score_cosine)):
        ranked = rank(docs, query, score)[:4]
        shown = "  ".join("%s=%.3f" % (d, s) for d, s in ranked)
        print("  %-22s %s" % (label, shown))
    print("-" * 66)
    print("  raw puts the long page on top; cosine puts the on-topic note on top.")


def do_measure(docs, queries):
    print("RETRIEVAL QUALITY — raw dot-product vs length-normalised cosine")
    print("-" * 66)
    print("  scorer                 hit@1   hit@%d   MRR" % TOP_MEASURE)
    for label, score in (("raw dot-product", score_raw), ("cosine (length-fair)", score_cosine)):
        h1, hk, mrr = measure(docs, queries, score)
        n = len(queries)
        print("  %-20s   %d/%d     %d/%d    %.3f" % (label, h1, n, hk, n, mrr))
    print("-" * 66)
    print("  at hit@%d the two look identical -- 'both perfect'. hit@1 and MRR show" % TOP_MEASURE)
    print("  the raw scorer buries the right note under the long page. Rank is the metric.")


def check(docs, queries):
    print("SELF-TEST — cosine bounds, normalisation kills length bias, determinism")
    print("-" * 66)

    # cosine of a document with itself is 1; with a disjoint query, 0.
    v = tf("coffee gym coffee")
    self_sim = score_cosine(v, v)
    disjoint = score_cosine(tf("dentist"), tf("flight jakarta"))
    print("  cosine(x,x) = %.6f (==1), cosine(disjoint) = %.6f (==0)" % (self_sim, disjoint))
    bounds_ok = abs(self_sim - 1.0) < 1e-9 and disjoint == 0.0

    # the bug: on "gym leg day" the raw scorer ranks the long page above the note.
    q = "when is my gym leg day"
    raw_top = rank(docs, q, score_raw)[0][0]
    cos_top = rank(docs, q, score_cosine)[0][0]
    print("  query %r: raw top = %s, cosine top = %s" % (q, raw_top, cos_top))
    bias_shows = raw_top == "d00" and cos_top == "d02"

    # measured: cosine's hit@1 strictly beats raw's, but hit@3 hides it.
    r1, rk, _ = measure(docs, queries, score_raw)
    c1, ck, _ = measure(docs, queries, score_cosine)
    print("  hit@1  raw=%d cosine=%d (cosine wins)   hit@%d raw=%d cosine=%d (tie hides it)"
          % (r1, c1, TOP_MEASURE, rk, ck))
    metric_hides = c1 > r1 and rk == ck

    # determinism.
    det = rank(docs, q, score_cosine) == rank(docs, q, score_cosine)

    ok = bounds_ok and bias_shows and metric_hides and det
    print("-" * 66)
    print("SELF-TEST %s  bounds=%s  bias_shows=%s  lenient_hides=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", bounds_ok, bias_shows, metric_hides, det))
    return ok


def main():
    p = argparse.ArgumentParser(description="A bag-of-words retriever, measured honestly.")
    p.add_argument("--corpus", action="store_true")
    p.add_argument("--search", metavar="Q")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    docs, queries = load()
    print("docs=%d  queries=%d  file=%s  (corpus is a fixture)" % (len(docs), len(queries), CORPUS.name))
    print("")

    if args.check:
        return 0 if check(docs, queries) else 1
    if args.corpus:
        show_corpus(docs, queries)
    elif args.search:
        search(docs, args.search)
    elif args.measure:
        do_measure(docs, queries)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
