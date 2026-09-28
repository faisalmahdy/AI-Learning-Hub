"""Enforce a negated constraint as a hard filter, not through the dense score -- a dense retriever ignores the word 'not', so the negated term stays in the query and pulls retrieval toward the exact documents it was meant to exclude.

A dense retriever turns text into a vector that encodes which content words are present. That is what makes it powerful, and it is also why it cannot represent negation: 'not' and 'without' are short, low-content function words that barely move the vector, while the content word they negate -- 'ibuprofen' in 'relief without ibuprofen' -- lands in the representation at full weight, the same as if the user had asked for ibuprofen. The retriever encodes the topics you mentioned; it does not encode that you wanted one of them kept out.

So a query with a negated constraint scores a document that contains the excluded term as a near-perfect match, because that document shares every content token including the one you were trying to avoid. The negated term does not merely fail to exclude the wrong document -- it actively promotes it, adding one more matching token that lifts the unwanted document above the one you actually wanted.

This module models documents and the query as sets of content tokens and dense similarity as their cosine. It is a stylized embedder, but the mechanism is the real one: presence of content tokens drives the score, and the negation word is invisible. On the fixture the query is 'muscle pain relief without ibuprofen'; the ibuprofen document matches all four content tokens and tops the dense ranking, while the acetaminophen document -- the intended answer, which relieves the pain without ibuprofen -- matches three and ranks below it.

The fix is not a better score function; a dense score cannot see a NOT. Parse the negation out of the query and enforce it as a hard structured filter -- remove any document containing the excluded term -- then rank the survivors by the positive terms. The excluded document is gone before ranking, and the intended answer rises to the top.

  --dense    the dense cosine ranking: the excluded (ibuprofen) document on top
  --filter   parse the negation into a hard NOT filter, then rank: the intended (acetaminophen) document on top
  --check    the dense ranking returns the excluded document, the negated term is what promotes it, and the hard filter fixes it

query_positive, query_negated, and documents are the fixture; the cosine scores and both rankings are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "negretr.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cosine(query_terms, doc_terms):
    """Set cosine: shared tokens over the geometric mean of the two sizes -- the stylized dense score."""
    q, d = set(query_terms), set(doc_terms)
    if not q or not d:
        return 0.0
    return len(q & d) / (len(q) * len(d)) ** 0.5


def dense_query(data):
    """What the dense retriever actually embeds: every content token, the negated one included."""
    return data["query_positive"] + data["query_negated"]   # 'without' is invisible; 'ibuprofen' stays in


def rank(data, query_terms, docs):
    """Rank the given documents by cosine against the query, highest first."""
    scored = [(doc_id, cosine(query_terms, docs[doc_id])) for doc_id in docs]
    return sorted(scored, key=lambda pair: pair[1], reverse=True)


def negation_filter(data, docs):
    """Enforce the negation as a hard NOT: drop any document that contains an excluded term."""
    excluded = set(data["query_negated"])
    return {doc_id: terms for doc_id, terms in docs.items() if not (set(terms) & excluded)}


# ----------------------------------------------------------------- printing

def dense_view(data):
    docs = data["documents"]
    q = dense_query(data)
    print("DENSE — cosine ranking with the negated term left in the query (as the embedder sees it)")
    print("-" * 72)
    print("  query embeds: %s   ('without' is invisible to the embedder)" % q)
    for doc_id, score in rank(data, q, docs):
        note = "  <- EXCLUDED term is here" if set(data["query_negated"]) & set(docs[doc_id]) else ""
        print("    %-20s cosine %.4f%s" % (doc_id, score, note))
    print("-" * 72)
    print("  the top hit is the document the user asked to exclude")


def filter_view(data):
    docs = data["documents"]
    kept = negation_filter(data, docs)
    print("FILTER — parse the negation into a hard NOT filter, then rank by the positive terms")
    print("-" * 72)
    print("  positive query: %s   NOT: %s" % (data["query_positive"], data["query_negated"]))
    print("  removed by filter: %s" % [d for d in docs if d not in kept])
    for doc_id, score in rank(data, data["query_positive"], kept):
        print("    %-20s cosine %.4f" % (doc_id, score))
    print("-" * 72)
    print("  the excluded document is gone before ranking; the intended answer is on top")


def check(data):
    print("SELF-TEST — the dense ranking returns the excluded document, the negated term is what promotes it, and the hard filter fixes it")
    print("-" * 112)
    docs = data["documents"]
    excluded_terms = set(data["query_negated"])

    dense_ranking = rank(data, dense_query(data), docs)
    dense_top = dense_ranking[0][0]
    dense_top_is_excluded = bool(set(docs[dense_top]) & excluded_terms)
    print("  dense top hit contains the excluded term = %s (%s)" % (dense_top_is_excluded, dense_top))

    excluded_id = next(d for d in docs if set(docs[d]) & excluded_terms)
    intended_id = next(d for d in docs if not (set(docs[d]) & excluded_terms) and set(docs[d]) & set(data["query_positive"]))
    with_neg = {d: cosine(dense_query(data), docs[d]) for d in (excluded_id, intended_id)}
    without_neg = {d: cosine(data["query_positive"], docs[d]) for d in (excluded_id, intended_id)}
    negated_term_promotes_excluded = (with_neg[excluded_id] > with_neg[intended_id]) and (without_neg[excluded_id] == without_neg[intended_id])
    print("  the negated term is what lifts the excluded doc above the intended one = %s (with %.4f>%.4f, without %.4f==%.4f)"
          % (negated_term_promotes_excluded, with_neg[excluded_id], with_neg[intended_id], without_neg[excluded_id], without_neg[intended_id]))

    kept = negation_filter(data, docs)
    filter_removes_excluded = excluded_id not in kept
    print("  the hard NOT filter removes the excluded document = %s" % filter_removes_excluded)

    filtered_top = rank(data, data["query_positive"], kept)[0][0]
    filtered_top_is_intended = filtered_top == intended_id
    print("  after filtering, the top hit is the intended document = %s (%s)" % (filtered_top_is_intended, filtered_top))

    dense_alone_is_wrong = dense_top != intended_id
    print("  dense alone does NOT return the intended document = %s (returned %s)" % (dense_alone_is_wrong, dense_top))

    ok = (dense_top_is_excluded and negated_term_promotes_excluded and filter_removes_excluded
          and filtered_top_is_intended and dense_alone_is_wrong)
    print("-" * 112)
    print("SELF-TEST %s  dense_top_is_excluded=%s  negated_term_promotes_excluded=%s  filter_removes_excluded=%s  filtered_top_is_intended=%s  dense_alone_is_wrong=%s"
          % ("PASS" if ok else "FAIL", dense_top_is_excluded, negated_term_promotes_excluded, filter_removes_excluded,
             filtered_top_is_intended, dense_alone_is_wrong))
    return ok


def main():
    p = argparse.ArgumentParser(description="Negation in retrieval: enforce a negated query constraint as a hard structured filter, not through the dense score, because a dense retriever ignores 'not'/'without' and keeps the negated content term in the query, promoting the very documents the user meant to exclude.")
    p.add_argument("--dense", action="store_true")
    p.add_argument("--filter", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query_positive=%s  query_negated=%s  file=%s  (these are a fixture)"
          % (data["query_positive"], data["query_negated"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.dense:
        dense_view(data)
    elif args.filter:
        filter_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
