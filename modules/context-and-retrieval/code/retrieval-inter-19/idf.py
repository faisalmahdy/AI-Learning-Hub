"""Weight matched terms by IDF, or a document matching only common words beats the one that answers the query.

A lexical scorer decides how well a document matches a query. The naive rule is to count matched query terms:
more terms hit, higher score. That treats every word as equally informative, which is false. In the query
"how does backpropagation work", the words 'how', 'does', and 'work' appear in most documents -- matching them
says almost nothing about relevance. 'backpropagation' appears in a handful -- matching it says almost
everything. A document that happens to contain 'how', 'does', and 'work' but never mentions backpropagation
scores three matched terms; the document actually about backpropagation scores one. Count the terms and the
off-topic document wins.

The fix is inverse document frequency: weight each matched term by IDF = log(n_docs / df), where df is how many
documents contain the term. A term in almost every document has df near n_docs, so log(n_docs/df) is near zero
-- matching it barely counts. A rare term has small df, so its IDF is large -- matching it counts a lot. Now
the single rare-term match outweighs the three common-term matches, and the document that answers the query
ranks first. IDF encodes the intuition that a word is informative in proportion to how surprising it is to see.

On this fixture the corpus has 1000 documents. The common terms have df 600-850 (IDF around 0.2-0.5); rare
'backpropagation' has df 5 (IDF 5.3). Counting terms ranks the common-word document first (3 vs 1). IDF-
weighting ranks the rare-term document first (5.3 vs 0.9). This computes both.

  --idf       each query term's document frequency and its IDF weight
  --score     the two documents scored by term count vs IDF sum, and who ranks first
  --check     term-count ranks the off-topic document first; IDF ranks the on-topic one first

The corpus size and document frequencies are the fixture; every score is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "idf.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def idf(term, df, n_docs):
    """Inverse document frequency: log(n_docs / df). Near 0 for common terms, large for rare ones."""
    return math.log(n_docs / df[term])


def count_score(matched):
    """Naive score: how many query terms the document matched."""
    return float(len(matched))


def idf_score(matched, df, n_docs):
    """IDF-weighted score: sum of the matched terms' IDF weights."""
    return sum(idf(t, df, n_docs) for t in matched)


# ----------------------------------------------------------------- printing

def idf_view(data):
    n, df = data["n_docs"], data["df"]
    print("IDF — document frequency and weight per query term (corpus %d docs)" % n)
    print("-" * 60)
    print("  term             df     IDF=log(n/df)")
    for t in data["query"]:
        print("  %-15s %4d     %.3f" % (t, df[t], idf(t, df, n)))
    print("-" * 60)
    print("  common terms weigh near zero; the rare term weighs an order more.")


def score_view(data):
    n, df = data["n_docs"], data["df"]
    a, b = data["doc_common"], data["doc_rare"]
    print("SCORE — term-count vs IDF-sum for each document")
    print("-" * 60)
    print("  doc            matched                     count   IDF-sum")
    print("  common-word    %-26s %5.0f   %6.3f" % (",".join(a), count_score(a), idf_score(a, df, n)))
    print("  rare-word      %-26s %5.0f   %6.3f" % (",".join(b), count_score(b), idf_score(b, df, n)))
    print("-" * 60)
    print("  count ranks the common-word doc first; IDF ranks the rare-word doc first.")


def check(data):
    print("SELF-TEST — term-count ranks the off-topic document first; IDF ranks the on-topic one first")
    print("-" * 100)
    n, df = data["n_docs"], data["df"]
    a, b = data["doc_common"], data["doc_rare"]

    count_ranks_common_first = count_score(a) > count_score(b)
    print("  term-count ranks the common-word doc first = %s (%.0f > %.0f)" % (count_ranks_common_first, count_score(a), count_score(b)))

    idf_ranks_rare_first = idf_score(b, df, n) > idf_score(a, df, n)
    print("  IDF ranks the rare-word doc first = %s (%.3f > %.3f)" % (idf_ranks_rare_first, idf_score(b, df, n), idf_score(a, df, n)))

    ranking_reverses = count_ranks_common_first and idf_ranks_rare_first
    print("  the two rules pick opposite winners = %s" % ranking_reverses)

    rare_outweighs_all_common = idf("backpropagation", df, n) > idf_score(a, df, n)
    print("  one rare match outweighs all three common matches = %s (%.3f > %.3f)" % (rare_outweighs_all_common, idf("backpropagation", df, n), idf_score(a, df, n)))

    idf_is_log_n_over_df = all(abs(idf(t, df, n) - math.log(n / df[t])) < 1e-12 for t in data["query"])
    print("  IDF equals log(n_docs/df) for every term = %s" % idf_is_log_n_over_df)

    ok = count_ranks_common_first and idf_ranks_rare_first and ranking_reverses and rare_outweighs_all_common and idf_is_log_n_over_df
    print("-" * 100)
    print("SELF-TEST %s  count_ranks_common_first=%s  idf_ranks_rare_first=%s  ranking_reverses=%s  rare_outweighs_all_common=%s  idf_is_log_n_over_df=%s"
          % ("PASS" if ok else "FAIL", count_ranks_common_first, idf_ranks_rare_first, ranking_reverses, rare_outweighs_all_common, idf_is_log_n_over_df))
    return ok


def main():
    p = argparse.ArgumentParser(description="Weight matched query terms by IDF so a common-word match cannot outrank a rare-word match.")
    p.add_argument("--idf", action="store_true")
    p.add_argument("--score", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_docs=%d  query=%s  file=%s  (the corpus stats are a fixture)"
          % (data["n_docs"], " ".join(data["query"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.idf:
        idf_view(data)
    elif args.score:
        score_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
