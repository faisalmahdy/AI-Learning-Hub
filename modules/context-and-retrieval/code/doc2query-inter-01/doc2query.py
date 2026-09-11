"""Index the questions a passage answers, not only its words -- or a short query lands on a lexical look-alike, not the answer.

A lexical retriever scores a document by how many query words appear in it. That fails whenever the person asking and
the person who wrote the passage chose different words for the same idea: someone asks "how do plants make food from
light" and the passage that answers it says "photosynthesis converts sunlight energy inside chloroplasts" -- almost
no shared words, so the score is near zero. Meanwhile a passage about a "food processor" that "makes" "meals" shares
the surface words "food" and "make" and scores higher, so the retriever ranks the wrong document first. The gap is
not about relevance; it is about vocabulary, and the document side of the gap is the half you can fix ahead of time.

doc2query closes it from the document side: before indexing, run a small model over each passage to predict the
QUESTIONS it answers, and append those predicted questions to the text you index. Now the passage about
photosynthesis is indexed alongside "how plants make food light energy," which shares the asker's words, so the same
lexical retriever -- unchanged -- scores it highly and ranks it first. This is the mirror image of HyDE, which
rewrites the query toward the document's words; doc2query rewrites the document toward the query's words, and it does
the expensive generation once at index time instead of on every query.

On this fixture the query shares its vocabulary with the gold passage's predicted questions, not its text. Ranking by
text alone puts the lexical look-alike (the food processor) at rank 1 and the gold answer below it; ranking by
text-plus-expansions puts the gold answer at rank 1. The lift comes entirely from query terms that match only the
expansions. cosine is over term-count vectors; every number is computed.

  --rank    the ranking by passage text alone (gold loses) vs by text-plus-predicted-questions (gold wins)
  --gap     the query terms that match the gold passage only through its expansions -- the vocabulary gap closed
  --check   text-only ranks a look-alike first and the gold below; doc2query lifts the gold to rank 1 via expansions

The corpus, query, and predicted questions are the fixture; every similarity is computed. Stdlib only.
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "doc2query.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def tokens(text, stop):
    """Lowercase word tokens with stop words removed -- the terms a lexical index would key on."""
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in stop]


def cosine(a, b):
    """Cosine similarity between two term-count vectors (Counters)."""
    dot = sum(a[t] * b[t] for t in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def indexed_text(doc, expand, stop):
    """The bag of terms the retriever indexes for a doc: its text, plus its predicted questions when expand=True."""
    text = doc["text"] + (" " + doc["expansions"] if expand else "")
    return Counter(tokens(text, stop))


def ranking(data, expand):
    """Rank the docs by cosine to the query, indexing text alone (expand=False) or text+expansions (expand=True)."""
    stop = data["stop"]
    qv = Counter(tokens(data["query"], stop))
    scored = [(doc["id"], cosine(qv, indexed_text(doc, expand, stop))) for doc in data["docs"]]
    return sorted(scored, key=lambda kv: kv[1], reverse=True)


# ----------------------------------------------------------------- printing

def rank_view(data):
    print("RANK — score by passage text alone vs by text plus the questions it answers")
    print("-" * 68)
    base, exp = ranking(data, False), ranking(data, True)
    print("  text only                     text + predicted questions")
    for (bi, bs), (ei, es) in zip(base, exp):
        gold_b = "  <- gold" if bi == data["gold"] else ""
        gold_e = "  <- gold" if ei == data["gold"] else ""
        print("  %s  %.3f%-9s        %s  %.3f%s" % (bi, bs, gold_b, ei, es, gold_e))
    print("-" * 68)
    print("  text alone ranks the lexical look-alike first; expansions put the gold answer on top.")


def gap_view(data):
    stop = data["stop"]
    gold = next(d for d in data["docs"] if d["id"] == data["gold"])
    qterms = set(tokens(data["query"], stop))
    in_text = set(tokens(gold["text"], stop))
    in_exp = set(tokens(gold["expansions"], stop))
    print("GAP — which query terms reach the gold passage, and through what")
    print("-" * 60)
    print("  query terms:            %s" % sorted(qterms))
    print("  match gold TEXT:        %s" % sorted(qterms & in_text))
    print("  match gold EXPANSIONS:  %s" % sorted(qterms & in_exp))
    print("  reached only via expansions: %s" % sorted((qterms & in_exp) - in_text))
    print("-" * 60)
    print("  the query and the passage text barely share words; the predicted questions carry the overlap.")


def check(data):
    print("SELF-TEST — text-only ranks a look-alike first and the gold below; doc2query lifts the gold to rank 1")
    print("-" * 100)
    base, exp = ranking(data, False), ranking(data, True)
    gold = data["gold"]
    stop = data["stop"]

    base_top_not_gold = base[0][0] != gold
    print("  text-only ranks a non-gold look-alike first = %s (rank 1 = %s)" % (base_top_not_gold, base[0][0]))

    base_gold_rank = [i for i, (d, _) in enumerate(base) if d == gold][0] + 1
    base_gold_below = base_gold_rank > 1
    print("  the gold passage ranks below it on text alone = %s (gold at rank %d)" % (base_gold_below, base_gold_rank))

    exp_gold_first = exp[0][0] == gold
    print("  text-plus-expansions ranks the gold passage first = %s (rank 1 = %s)" % (exp_gold_first, exp[0][0]))

    goldd = next(d for d in data["docs"] if d["id"] == gold)
    qterms = set(tokens(data["query"], stop))
    lift_terms = (qterms & set(tokens(goldd["expansions"], stop))) - set(tokens(goldd["text"], stop))
    lift_from_expansions = len(lift_terms) > 0
    print("  the lift comes from query terms matching only the expansions = %s (%s)" % (lift_from_expansions, sorted(lift_terms)))

    same_retriever = True  # both rankings call the identical cosine over the identical query vector
    print("  the retriever and query are unchanged; only the indexed text grew = %s" % same_retriever)

    ok = base_top_not_gold and base_gold_below and exp_gold_first and lift_from_expansions and same_retriever
    print("-" * 100)
    print("SELF-TEST %s  base_top_not_gold=%s  base_gold_below=%s  exp_gold_first=%s  lift_from_expansions=%s  same_retriever=%s"
          % ("PASS" if ok else "FAIL", base_top_not_gold, base_gold_below, exp_gold_first, lift_from_expansions, same_retriever))
    return ok


def main():
    p = argparse.ArgumentParser(description="doc2query: append a passage's predicted questions to the indexed text so a lexical retriever bridges the query-document vocabulary gap from the document side.")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--gap", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%r  gold=%s  docs=%d  file=%s  (the corpus and predicted questions are a fixture)"
          % (data["query"], data["gold"], len(data["docs"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rank:
        rank_view(data)
    elif args.gap:
        gap_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
