"""Retrieve with the bi-encoder, rerank with the cross-encoder, or you pay accuracy for scale or scale for accuracy.

Two encoder architectures score a query against a document, and they trade off exactly opposite things. A
BI-ENCODER embeds the query and each document SEPARATELY into vectors, then scores by their dot product. Because
the document vectors do not depend on the query, you precompute them once and, at query time, a similarity search
over millions of them is cheap. The price is that the bi-encoder never sees the query and document together: it
scores each in isolation, so it cannot judge INTERACTIONS -- whether the document actually addresses the query as
a whole, rather than just containing its words. A document that repeats one query term many times can score high
without covering the rest of the query, and the bi-encoder, scoring term by term, is fooled.

A CROSS-ENCODER reads the query and document TOGETHER, in one pass, so it sees every interaction and judges
whether the document covers the whole query. It is far more accurate. The price is the mirror image of the
bi-encoder's: because the score depends on the pair, there is nothing to precompute -- you must run the model on
each (query, document) pair -- so it cannot be scaled to millions. The resolution is to use each for what it is
good at: retrieve a shortlist with the cheap bi-encoder, then RERANK just that shortlist with the accurate
cross-encoder. The bi-encoder's scale gets the answer into the top-k; the cross-encoder's accuracy pulls it to the
top; and you only pay the cross-encoder's per-pair cost on k documents, not on the whole corpus.

On this fixture the bi-encoder ranks d_pad first (it repeats 'python' five times, term-count 5) over the true
answer d_answer (term-count 2) -- wrong. The cross-encoder scores by query-aspect coverage: d_answer covers both
'async' and 'python' (2) while d_pad covers only one (1), so it ranks d_answer first -- right. Reranking the
bi-encoder's top 2 recovers d_answer while scoring 2 pairs, not all 3. This computes both.

  --score      each document's bi-encoder (term-count) and cross-encoder (aspect-coverage) score, and each top pick
  --rerank     retrieve top-k with the bi-encoder, rerank with the cross-encoder, and the pairs scored vs a full pass
  --check      the bi-encoder misranks on the interaction; the cross-encoder fixes it; reranking top-k recovers it cheaply

The query and documents are the fixture; every score is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "crossenc.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def bi_score(doc, query):
    """Bi-encoder stand-in: total query-term occurrences (separable, precomputable, no interaction)."""
    return sum(count for term, count in doc.items() if term in query)


def cross_score(doc, query):
    """Cross-encoder stand-in: how many DISTINCT query aspects the doc covers (joint, sees the interaction)."""
    return sum(1 for term in query if term in doc)


def top_by(docs, query, scorer):
    """The document id ranked first by the given scorer."""
    return max(docs, key=lambda d: scorer(docs[d], query))


def bi_ranking(docs, query):
    return sorted(docs, key=lambda d: bi_score(docs[d], query), reverse=True)


# ----------------------------------------------------------------- printing

def score_view(data):
    docs, q = data["documents"], data["query"]
    print("SCORE — bi-encoder (term count) vs cross-encoder (aspect coverage)")
    print("-" * 62)
    print("  document    bi (term count)   cross (aspects covered)")
    for d in docs:
        print("  %-10s  %d                 %d" % (d, bi_score(docs[d], q), cross_score(docs[d], q)))
    print("-" * 62)
    print("  bi top: %s (repeats a term)   cross top: %s (covers the query)" % (top_by(docs, q, bi_score), top_by(docs, q, cross_score)))


def rerank_view(data):
    docs, q, k = data["documents"], data["query"], data["top_k"]
    shortlist = bi_ranking(docs, q)[:k]
    reranked = max(shortlist, key=lambda d: cross_score(docs[d], q))
    print("RERANK — bi-encoder retrieves top %d, cross-encoder reranks them" % k)
    print("-" * 62)
    print("  bi-encoder shortlist (cheap, all %d docs):  %s" % (len(docs), shortlist))
    print("  cross-encoder rerank (scores %d pairs):      top = %s" % (k, reranked))
    print("  a FULL cross-encoder pass would score all %d pairs" % len(docs))
    print("-" * 62)
    print("  the answer rode into the shortlist on scale, then the cross-encoder pulled it to the top.")


def check(data):
    print("SELF-TEST — the bi-encoder misranks on the interaction; the cross-encoder fixes it; reranking recovers it cheaply")
    print("-" * 112)
    docs, q, answer, k = data["documents"], data["query"], data["answer"], data["top_k"]

    bi_misranks = top_by(docs, q, bi_score) != answer
    print("  the bi-encoder ranks the wrong document first = %s (got %s, answer %s)" % (bi_misranks, top_by(docs, q, bi_score), answer))

    cross_correct = top_by(docs, q, cross_score) == answer
    print("  the cross-encoder ranks the answer first = %s (%s)" % (cross_correct, top_by(docs, q, cross_score)))

    bi_rewards_repetition = bi_score(docs["d_pad"], q) > bi_score(docs[answer], q)
    print("  the bi-encoder scores a term-padded doc above the answer = %s (%d > %d)" % (bi_rewards_repetition, bi_score(docs["d_pad"], q), bi_score(docs[answer], q)))

    cross_rewards_coverage = cross_score(docs[answer], q) > cross_score(docs["d_pad"], q)
    print("  the cross-encoder scores the answer above the padded doc = %s (%d > %d)" % (cross_rewards_coverage, cross_score(docs[answer], q), cross_score(docs["d_pad"], q)))

    shortlist = bi_ranking(docs, q)[:k]
    reranked = max(shortlist, key=lambda d: cross_score(docs[d], q))
    rerank_recovers_cheaply = answer in shortlist and reranked == answer and k < len(docs)
    print("  reranking the top %d recovers the answer while scoring fewer pairs = %s (%d < %d pairs)" % (k, rerank_recovers_cheaply, k, len(docs)))

    ok = bi_misranks and cross_correct and bi_rewards_repetition and cross_rewards_coverage and rerank_recovers_cheaply
    print("-" * 112)
    print("SELF-TEST %s  bi_misranks=%s  cross_correct=%s  bi_rewards_repetition=%s  cross_rewards_coverage=%s  rerank_recovers_cheaply=%s"
          % ("PASS" if ok else "FAIL", bi_misranks, cross_correct, bi_rewards_repetition, cross_rewards_coverage, rerank_recovers_cheaply))
    return ok


def main():
    p = argparse.ArgumentParser(description="Bi-encoders scale but miss interactions; cross-encoders are accurate but cannot scale; retrieve with one and rerank the top-k with the other.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--rerank", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  documents=%d  answer=%s  top_k=%d  file=%s  (the corpus is a fixture)"
          % (data["query"], len(data["documents"]), data["answer"], data["top_k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.rerank:
        rerank_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
