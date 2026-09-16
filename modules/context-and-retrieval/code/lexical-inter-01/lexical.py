"""Retrieve with lexical (keyword / BM25) scoring, not dense embeddings alone -- otherwise a query with a rare exact token (an error code, an ID, a function name) ranks the wrong document first.

Dense retrieval embeds the query and every document into a vector space and ranks by semantic similarity. That is powerful for meaning: it finds documents that are ABOUT the same thing even when they share no words. But it has a blind spot. A rare exact token -- an error code like E4501, a product SKU, a specific function name -- contributes almost nothing to a document's embedding, because the embedding is a smear of the document's overall meaning and one rare token barely moves it. So a document that contains the exact token the user typed can rank BELOW a document that is merely semantically similar and does not contain it. The user asked for E4501 and got a page about resetting passwords, because 'reset' was in the query and dense similarity rewarded the topical overlap.

Lexical retrieval scores differently. It counts which query terms each document actually contains, weighted by how rare each term is: a term appearing in only 1 of N documents (high inverse document frequency, IDF) is worth far more than a term appearing in all of them. This is the core of BM25. The rare exact token, precisely because it is rare, gets a high IDF weight, so the one document that contains it shoots to the top. Lexical matching cannot understand meaning -- it has no idea 'reset' and 'restore' are related -- but it never fumbles an exact token, which is exactly where dense retrieval is weakest.

The two systems fail on opposite inputs, so production retrieval hybridizes them: run both, combine the scores, and you get semantic recall AND exact-match precision. But the lesson to internalize first is the failure mode of dense-alone: on a query with a rare exact token, dense retrieval can rank a document without the token above the document with it, and you need lexical scoring (or hybrid) to fix that.

The rule: for queries carrying a rare exact token, score documents by IDF-weighted lexical match (BM25) or a dense+lexical hybrid, not dense embeddings alone -- because a rare token barely moves an embedding, so dense similarity can rank a semantically-close document without the token above the document that actually contains it.

On this fixture the query is 'reset error E4501'. Dense retrieval ranks d1 ('reset password', similarity 0.8) first -- it has no E4501. Lexical retrieval, weighting the rare E4501 by its high IDF, ranks d2 ('error E4501 login') first -- the document the user actually wanted. This computes both.

  --idf       the document frequency and IDF weight of each query term
  --rank      the lexical and dense scores and the ranking each produces
  --check     dense retrieval ranks a document without the rare token first; lexical retrieval ranks the exact-match document first

query_terms, rare_term, and the documents (their terms and dense similarities) are the fixture; every document frequency, IDF weight, and lexical score is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lexical.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def document_frequency(term, documents):
    return sum(1 for d in documents if term in d["terms"])


def idf(term, documents):
    n = len(documents)
    df = document_frequency(term, documents)
    return math.log(n / df) if df else 0.0


def lexical_score(doc, query_terms, documents):
    return sum(idf(t, documents) for t in query_terms if t in doc["terms"])


def rank_by(pairs):
    return sorted(pairs, key=lambda kv: kv[1], reverse=True)


# ----------------------------------------------------------------- printing

def idf_view(data):
    documents, query_terms = data["documents"], data["query_terms"]
    n = len(documents)
    print("IDF — how rare each query term is across the %d documents" % n)
    print("-" * 60)
    for t in query_terms:
        df = document_frequency(t, documents)
        mark = "  <- rare exact token" if t == data["rare_term"] else ""
        print("  %-8s df=%d/%d   idf=%.3f%s" % (t, df, n, idf(t, documents), mark))
    print("-" * 60)
    print("  the rare token has the highest idf, so matching it counts most")


def rank_view(data):
    documents, query_terms = data["documents"], data["query_terms"]
    lex = [(d["id"], lexical_score(d, query_terms, documents)) for d in documents]
    dense = [(d["id"], d["dense_sim"]) for d in documents]
    lex_ranked, dense_ranked = rank_by(lex), rank_by(dense)
    has = {d["id"]: (data["rare_term"] in d["terms"]) for d in documents}
    print("RANK — lexical (IDF-weighted) vs dense (embedding) scores")
    print("-" * 64)
    print("  doc  lexical  dense  has %s" % data["rare_term"])
    for d in documents:
        i = d["id"]
        print("  %-4s %6.3f  %5.2f  %s" % (i, dict(lex)[i], dict(dense)[i], "yes" if has[i] else "no"))
    print("-" * 64)
    print("  lexical top = %s (has token: %s)   dense top = %s (has token: %s)"
          % (lex_ranked[0][0], "yes" if has[lex_ranked[0][0]] else "no",
             dense_ranked[0][0], "yes" if has[dense_ranked[0][0]] else "no"))
    print("  dense ranks a document without the exact token first; lexical fixes it")


def check(data):
    print("SELF-TEST — dense retrieval ranks a document without the rare token first; lexical retrieval ranks the exact-match document first")
    print("-" * 122)
    documents, query_terms, rare = data["documents"], data["query_terms"], data["rare_term"]
    lex_ranked = rank_by([(d["id"], lexical_score(d, query_terms, documents)) for d in documents])
    dense_ranked = rank_by([(d["id"], d["dense_sim"]) for d in documents])
    has = {d["id"]: (rare in d["terms"]) for d in documents}
    n = len(documents)

    query_has_rare_term = rare in query_terms
    print("  the query carries the rare exact token '%s' = %s" % (rare, query_has_rare_term))

    rare_term_high_idf = idf(rare, documents) == max(idf(t, documents) for t in query_terms)
    print("  the rare token has the highest idf of any query term = %s (idf=%.3f, df=%d/%d)"
          % (rare_term_high_idf, idf(rare, documents), document_frequency(rare, documents), n))

    dense_top, lex_top = dense_ranked[0][0], lex_ranked[0][0]
    dense_misses_exact = not has[dense_top]
    print("  dense retrieval's top doc %s does NOT contain the token = %s" % (dense_top, dense_misses_exact))

    lexical_finds_exact = has[lex_top]
    print("  lexical retrieval's top doc %s DOES contain the token = %s" % (lex_top, lexical_finds_exact))

    rankings_disagree = dense_top != lex_top
    print("  dense and lexical disagree on the top document = %s (dense %s, lexical %s)" % (rankings_disagree, dense_top, lex_top))

    ok = (query_has_rare_term and rare_term_high_idf and dense_misses_exact and lexical_finds_exact and rankings_disagree)
    print("-" * 122)
    print("SELF-TEST %s  query_has_rare_term=%s  rare_term_high_idf=%s  dense_misses_exact=%s  lexical_finds_exact=%s  rankings_disagree=%s"
          % ("PASS" if ok else "FAIL", query_has_rare_term, rare_term_high_idf, dense_misses_exact, lexical_finds_exact, rankings_disagree))
    return ok


def main():
    p = argparse.ArgumentParser(description="Lexical vs dense retrieval: for queries carrying a rare exact token, score documents by IDF-weighted lexical match (BM25) or a dense+lexical hybrid, not dense embeddings alone -- because a rare token barely moves an embedding, so dense similarity can rank a semantically-close document without the token above the document that actually contains it.")
    p.add_argument("--idf", action="store_true")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  rare_term=%s  documents=%d  file=%s  (the query and documents are a fixture)"
          % (data["query_terms"], data["rare_term"], len(data["documents"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.idf:
        idf_view(data)
    elif args.rank:
        rank_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
