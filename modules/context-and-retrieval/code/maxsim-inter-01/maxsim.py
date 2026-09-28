"""Score retrieval token by token (MaxSim), not by one mean-pooled vector -- or a blurry doc outranks a real match.

A single-vector retriever compresses a query and a document each into ONE embedding -- usually the mean of their token
vectors -- and scores by the cosine between those two means. That is fast and it works when a document is about one
thing, but the mean throws away which specific tokens matched which. Two very different documents can share a mean: a
document that genuinely contains an exact match for each query term, buried among other tokens, ends up with a blended
mean; and a document full of vague tokens that half-match everything can have a mean that lands right on the query's
mean. The mean cannot tell "distinct tokens that each fully match a query term" from "one fuzzy token that partially
matches all of them," so it can rank the vague document above the real answer.

Late interaction keeps the token vectors and compares them directly. ColBERT's MaxSim scores a document by summing, over
each query token, the maximum cosine similarity between that query token and ANY document token: every query term goes
looking for its best match in the document, and the score is how well each term is individually satisfied. A query term
that finds an exact match contributes 1; a term with no real match contributes little, no matter how the rest of the
document blurs together. This recovers the term-level precision the mean destroys, while still precomputing every
document's token vectors offline -- the middle ground between a single-vector bi-encoder (fast, coarse) and a full
cross-encoder (accurate, slow).

On this fixture the query has two orthogonal token vectors. The gold document contains an exact match for each (plus
extra tokens), so its MaxSim is the perfect 2.0; the distractor has only blurry [0.5, 0.5] tokens matching each query
term at 0.707, for a MaxSim of 1.414. But mean-pooling gives the distractor a cosine of 1.00 to the query mean and the
gold document only 0.89, so the single-vector retriever ranks the distractor first while MaxSim ranks the gold first.
This computes both.

  --score     the single-vector (mean-pool cosine) ranking vs the MaxSim ranking -- they disagree on the top result
  --tokens    for each query token, its best match in each document -- the gold has exact matches, the distractor none
  --check     mean-pooling ranks the distractor first; MaxSim ranks the gold first with a perfect per-token match

The query and document token vectors are the fixture; every cosine and score is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "maxsim.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cosine(u, v):
    """Cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    return dot / (nu * nv) if nu and nv else 0.0


def mean_vec(tokens):
    """Mean-pool a bag of token vectors into a single vector -- what a bi-encoder indexes."""
    dim = len(tokens[0])
    return [sum(t[i] for t in tokens) / len(tokens) for i in range(dim)]


def single_vector_score(query_tokens, doc_tokens):
    """Bi-encoder score: cosine between the mean-pooled query and the mean-pooled document."""
    return cosine(mean_vec(query_tokens), mean_vec(doc_tokens))


def maxsim_score(query_tokens, doc_tokens):
    """Late-interaction score: for each query token, its best cosine to any doc token, summed."""
    return sum(max(cosine(q, d) for d in doc_tokens) for q in query_tokens)


def ranking(query, documents, scorer):
    """Rank the documents by a scorer, highest first."""
    return sorted(((name, scorer(query, toks)) for name, toks in documents.items()), key=lambda kv: kv[1], reverse=True)


# ----------------------------------------------------------------- printing

def score_view(data):
    q, docs = data["query"], data["documents"]
    print("SCORE — single-vector (mean-pool) ranking vs MaxSim (late interaction)")
    print("-" * 66)
    sv = ranking(q, docs, single_vector_score)
    ms = ranking(q, docs, maxsim_score)
    print("  single-vector (bi-encoder):")
    for name, s in sv:
        print("    %-14s %.3f%s" % (name, s, "  <- gold" if name == data["gold"] else ""))
    print("  MaxSim (late interaction):")
    for name, s in ms:
        print("    %-14s %.3f%s" % (name, s, "  <- gold" if name == data["gold"] else ""))
    print("-" * 66)
    print("  mean-pooling ranks the blurry distractor first; MaxSim ranks the gold, which really matches both terms.")


def tokens_view(data):
    q, docs = data["query"], data["documents"]
    print("TOKENS — each query token's best match (max cosine) in each document")
    print("-" * 60)
    for qi, qt in enumerate(q):
        print("  query token %d = %s:" % (qi, qt))
        for name, toks in docs.items():
            best = max(cosine(qt, d) for d in toks)
            print("    best match in %-14s = %.3f" % (name, best))
    print("-" * 60)
    print("  the gold has an exact (1.000) match for each query token; the distractor only ever half-matches.")


def check(data):
    print("SELF-TEST — mean-pooling ranks the distractor first; MaxSim ranks the gold first with a perfect per-token match")
    print("-" * 110)
    q, docs, gold = data["query"], data["documents"], data["gold"]

    sv = ranking(q, docs, single_vector_score)
    ms = ranking(q, docs, maxsim_score)

    single_vector_wrong = sv[0][0] != gold
    print("  the single-vector retriever ranks a non-gold doc first = %s (top = %s)" % (single_vector_wrong, sv[0][0]))

    maxsim_right = ms[0][0] == gold
    print("  MaxSim ranks the gold doc first = %s (top = %s)" % (maxsim_right, ms[0][0]))

    gold_maxsim_perfect = abs(maxsim_score(q, docs[gold]) - len(q)) < 1e-9
    print("  the gold's MaxSim is the perfect %d (an exact match per query token) = %s (%.3f)" % (len(q), gold_maxsim_perfect, maxsim_score(q, docs[gold])))

    maxsim_gold_beats_distractor = maxsim_score(q, docs[gold]) > max(maxsim_score(q, t) for n, t in docs.items() if n != gold)
    print("  the gold's MaxSim beats every distractor's = %s" % maxsim_gold_beats_distractor)

    per_token_exact = all(max(cosine(qt, d) for d in docs[gold]) > 0.999 for qt in q)
    print("  every query token finds an exact match in the gold = %s" % per_token_exact)

    ok = single_vector_wrong and maxsim_right and gold_maxsim_perfect and maxsim_gold_beats_distractor and per_token_exact
    print("-" * 110)
    print("SELF-TEST %s  single_vector_wrong=%s  maxsim_right=%s  gold_maxsim_perfect=%s  maxsim_gold_beats_distractor=%s  per_token_exact=%s"
          % ("PASS" if ok else "FAIL", single_vector_wrong, maxsim_right, gold_maxsim_perfect, maxsim_gold_beats_distractor, per_token_exact))
    return ok


def main():
    p = argparse.ArgumentParser(description="Late interaction (ColBERT MaxSim): score retrieval by summing each query token's best match to any document token, recovering term-level precision that a single mean-pooled vector blurs away.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--tokens", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%d tokens  docs=%s  gold=%s  file=%s  (the token vectors are a fixture)"
          % (len(data["query"]), list(data["documents"]), data["gold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.tokens:
        tokens_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
