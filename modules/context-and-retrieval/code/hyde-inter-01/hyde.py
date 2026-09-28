"""Embed a hypothetical answer, not the question, or the query's words match the wrong document.

A question and its answer are written in different languages. The question "how long until a refund" is made of
question words -- how, long, until -- and a topic word; the answer "refunds are processed within thirty days of
receipt" is made of answer words -- processed, within, days, receipt. They barely overlap. So when you embed the
raw question and search for the nearest passage, the question's words pull it toward text that looks like a
question -- an FAQ heading, another user's post -- rather than toward the passage that actually answers it. The
retriever is matching surface vocabulary, and the vocabulary of a question is not the vocabulary of its answer.

HyDE -- Hypothetical Document Embeddings -- closes the gap by searching with an answer instead of a question.
Before retrieving anything, ask the model to WRITE a hypothetical answer to the query. It will be in the style
and vocabulary of a real answer, and -- this is the surprising part -- it does not need to be factually correct.
Even a made-up answer that says "processed within business days" is written like the target passage, so its
embedding lands near the real answer's embedding. You then retrieve with the hypothetical document's vector, not
the question's, and the nearest passage is the one that answers the question. The model's guess is a decoy shaped
like the target; you throw it at the index and keep whatever real passage it sticks to.

On this fixture the query's nearest passage is the FAQ (cosine 0.447) -- itself a question, sharing 'how' and
'refund' -- while the correct answer passage scores only 0.204: the query retrieves the WRONG document. The
hypothetical answer's nearest passage is the correct one (0.730), because it shares 'refund', 'processed',
'within', and 'days' with it. Same index, same correct passage; searching with the answer finds it. This computes
both.

  --score      each passage's cosine similarity to the query and to the hypothetical answer
  --retrieve   which passage the query retrieves vs which the hypothetical answer retrieves
  --check      the query retrieves the wrong passage; the hypothetical answer retrieves the right one

The query, hypothetical, and passages are the fixture; every score is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "hyde.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cosine(a, b):
    """Cosine similarity over token presence: shared tokens / sqrt(|a| * |b|)."""
    sa, sb = set(a), set(b)
    return len(sa & sb) / math.sqrt(len(sa) * len(sb))


def best_passage(text, passages):
    """The passage id with the highest cosine similarity to the given text."""
    return max(passages, key=lambda pid: cosine(text, passages[pid]))


# ----------------------------------------------------------------- printing

def score_view(data):
    q, h, passages = data["query"], data["hypothetical"], data["passages"]
    print("SCORE — cosine similarity of each passage to the query and to the hypothetical answer")
    print("-" * 66)
    print("  passage       to query   to hypothetical")
    for pid in passages:
        print("  %-12s  %.3f      %.3f" % (pid, cosine(q, passages[pid]), cosine(h, passages[pid])))
    print("-" * 66)
    print("  the query scores highest on the FAQ; the hypothetical answer scores highest on the correct passage.")


def retrieve_view(data):
    q, h, passages = data["query"], data["hypothetical"], data["passages"]
    bq, bh = best_passage(q, passages), best_passage(h, passages)
    print("RETRIEVE — top passage by query vs by hypothetical answer")
    print("-" * 66)
    print("  search with the QUERY:               retrieves %-11s (cosine %.3f)" % (bq, cosine(q, passages[bq])))
    print("  search with the HYPOTHETICAL answer: retrieves %-11s (cosine %.3f)" % (bh, cosine(h, passages[bh])))
    print("-" * 66)
    print("  the query lands on a question-shaped doc; the hypothetical answer lands on the answer.")


def check(data):
    print("SELF-TEST — the query retrieves the wrong passage; the hypothetical answer retrieves the right one")
    print("-" * 100)
    q, h, passages = data["query"], data["hypothetical"], data["passages"]
    correct = "p_correct"

    query_retrieves_wrong = best_passage(q, passages) != correct
    print("  searching with the query retrieves the wrong passage = %s (got %s)" % (query_retrieves_wrong, best_passage(q, passages)))

    hyde_retrieves_right = best_passage(h, passages) == correct
    print("  searching with the hypothetical answer retrieves the correct passage = %s (got %s)" % (hyde_retrieves_right, best_passage(h, passages)))

    hyde_scores_correct_higher = cosine(h, passages[correct]) > cosine(q, passages[correct])
    print("  the hypothetical answer matches the correct passage far better than the query does = %s (%.3f > %.3f)" % (hyde_scores_correct_higher, cosine(h, passages[correct]), cosine(q, passages[correct])))

    question_answer_asymmetry = cosine(q, passages[correct]) < cosine(q, passages["p_faq"])
    print("  the query matches a question-shaped doc better than its own answer = %s (%.3f < %.3f)" % (question_answer_asymmetry, cosine(q, passages[correct]), cosine(q, passages["p_faq"])))

    hyde_not_a_copy = "business" in h and "business" not in passages[correct]
    print("  the hypothetical answer is not a copy of the passage (it can be factually wrong) = %s" % hyde_not_a_copy)

    ok = query_retrieves_wrong and hyde_retrieves_right and hyde_scores_correct_higher and question_answer_asymmetry and hyde_not_a_copy
    print("-" * 100)
    print("SELF-TEST %s  query_retrieves_wrong=%s  hyde_retrieves_right=%s  hyde_scores_correct_higher=%s  question_answer_asymmetry=%s  hyde_not_a_copy=%s"
          % ("PASS" if ok else "FAIL", query_retrieves_wrong, hyde_retrieves_right, hyde_scores_correct_higher, question_answer_asymmetry, hyde_not_a_copy))
    return ok


def main():
    p = argparse.ArgumentParser(description="HyDE: retrieve with a hypothetical answer instead of the question, so the search vector matches the answer's vocabulary.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  hypothetical=%s  passages=%d  file=%s  (the texts are a fixture)"
          % (data["query"], data["hypothetical"], len(data["passages"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.retrieve:
        retrieve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
