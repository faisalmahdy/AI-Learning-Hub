"""Prefix the query the way the embedding model was trained ('query:' for queries, 'passage:' for documents) -- an asymmetric retriever embedded without the query prefix lands in the wrong part of the space and returns look-alikes, not answers.

Many modern retrieval embedding models are asymmetric: they are trained with a short instruction prefix on every input that says whether the text is a search query or a document being searched -- 'query: ...' versus 'passage: ...' (the exact tokens vary by model). This is not decoration. Queries and documents have systematically different shapes -- a short question versus a long passage -- and the prefix lets one model handle both by learning to map a correctly-prefixed query near the passages that ANSWER it, rather than near the passages that merely resemble it in wording or length.

The prefix feels like a cosmetic detail, so it is one of the most commonly dropped steps when wiring up such a model, and dropping it fails silently. Embed a query with no prefix and the model treats it as a passage: it places the query vector where a document of that text would go, which is a different region of the space than where the trained query encoder would have put it. Nearest-neighbor search then finds the documents nearest to a passage-like version of the query -- documents that look like the query -- instead of the documents the query encoder would have pointed at, which answer it. Retrieval quality drops, and because everything still returns plausible-looking results, nothing flags the mistake.

The fix is to embed each text with the prefix the model documents for its role: the query prefix for queries, the passage prefix for documents, on every call, matching training. It is a one-line formatting step, and getting it wrong quietly degrades every retrieval.

The rule: prefix queries and documents with the model's trained instruction ('query:' / 'passage:'), because asymmetric retrievers learn the query-to-answer mapping only for correctly-prefixed inputs -- so a query embedded without its prefix lands in passage space and retrieves look-alikes instead of answers.

On this fixture the query embedded with its prefix ranks the answering document d1 first (cosine 0.80 vs 0.60); the same query embedded without the prefix lands elsewhere and ranks the distractor d2 first (0.99 vs 0.92). This computes both.

  --embed    the cosine of each query variant (prefixed vs unprefixed) to each document
  --rank     the ranking each query variant produces, and which document is retrieved first
  --check    the unprefixed query retrieves the wrong document; the correctly-prefixed query retrieves the answer

the embeddings are the fixture; the cosines and rankings are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "qprefix.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cosine(a, b):
    """Vectors are unit-length, so cosine is the dot product."""
    return sum(x * y for x, y in zip(a, b))


def rank(query, documents):
    scored = [(d["id"], cosine(query, d["emb"])) for d in documents]
    return sorted(scored, key=lambda kv: kv[1], reverse=True)


def answer_id(documents):
    return next(d["id"] for d in documents if d["answer"])


# ----------------------------------------------------------------- printing

def embed_view(data):
    docs = data["documents"]
    print("EMBED — cosine of each query variant to each document")
    print("-" * 58)
    print("  document   answer?   query: prefix   no prefix")
    for d in docs:
        print("  %-8s   %-7s   %.2f            %.2f"
              % (d["id"], d["answer"], cosine(data["q_correct"], d["emb"]), cosine(data["q_no_prefix"], d["emb"])))
    print("-" * 58)
    print("  the prefix moves the query vector, changing which document is closest")


def rank_view(data):
    docs = data["documents"]
    rc = rank(data["q_correct"], docs)
    rn = rank(data["q_no_prefix"], docs)
    ans = answer_id(docs)
    print("RANK — retrieval order under each query embedding (answer = %s)" % ans)
    print("-" * 60)
    print("  with 'query:' prefix : %s  -> top %s" % (rc, rc[0][0]))
    print("  without prefix       : %s  -> top %s" % (rn, rn[0][0]))
    print("-" * 60)
    print("  the correctly-prefixed query retrieves the answer; the unprefixed one does not")


def check(data):
    print("SELF-TEST — the unprefixed query retrieves the wrong document; the correctly-prefixed query retrieves the answer")
    print("-" * 116)
    docs = data["documents"]
    ans = answer_id(docs)
    rc = rank(data["q_correct"], docs)
    rn = rank(data["q_no_prefix"], docs)

    prefix_changes_embedding = data["q_correct"] != data["q_no_prefix"]
    print("  the prefix changes the query's embedding = %s (%s vs %s)" % (prefix_changes_embedding, data["q_correct"], data["q_no_prefix"]))

    prefixed_retrieves_answer = rc[0][0] == ans
    print("  the correctly-prefixed query retrieves the answer first = %s (top %s)" % (prefixed_retrieves_answer, rc[0][0]))

    unprefixed_retrieves_wrong = rn[0][0] != ans
    print("  the unprefixed query retrieves the wrong document first = %s (top %s)" % (unprefixed_retrieves_wrong, rn[0][0]))

    rankings_differ = [i for i, _ in rc] != [i for i, _ in rn]
    print("  the two query embeddings produce different rankings = %s" % rankings_differ)

    unprefixed_prefers_lookalike = cosine(data["q_no_prefix"], next(d["emb"] for d in docs if not d["answer"])) > cosine(data["q_no_prefix"], next(d["emb"] for d in docs if d["answer"]))
    print("  the unprefixed query is closest to the distractor, not the answer = %s" % unprefixed_prefers_lookalike)

    ok = (prefix_changes_embedding and prefixed_retrieves_answer and unprefixed_retrieves_wrong
          and rankings_differ and unprefixed_prefers_lookalike)
    print("-" * 116)
    print("SELF-TEST %s  prefix_changes_embedding=%s  prefixed_retrieves_answer=%s  unprefixed_retrieves_wrong=%s  rankings_differ=%s  unprefixed_prefers_lookalike=%s"
          % ("PASS" if ok else "FAIL", prefix_changes_embedding, prefixed_retrieves_answer, unprefixed_retrieves_wrong, rankings_differ, unprefixed_prefers_lookalike))
    return ok


def main():
    p = argparse.ArgumentParser(description="Query/passage prefixes: prefix queries and documents with the model's trained instruction ('query:' / 'passage:'), because asymmetric retrievers learn the query-to-answer mapping only for correctly-prefixed inputs -- so a query embedded without its prefix lands in passage space and retrieves look-alikes instead of answers.")
    p.add_argument("--embed", action="store_true")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("q_correct=%s  q_no_prefix=%s  documents=%d  file=%s  (the embeddings are a fixture)"
          % (data["q_correct"], data["q_no_prefix"], len(data["documents"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.embed:
        embed_view(data)
    elif args.rank:
        rank_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
