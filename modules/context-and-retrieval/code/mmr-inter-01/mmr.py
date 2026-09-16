"""Select by marginal relevance, not raw relevance -- the top-k most relevant chunks are often near-duplicates.

Retrieval ranks chunks by relevance to the query, and the obvious way to fill a context window is to take the top k. But
relevance ranks each chunk in isolation, and the top of that ranking tends to CLUSTER: if three chunks all say the same
highly-relevant thing, all three sit at the top, and taking the top k spends the whole budget on one point while other
relevant aspects of the answer -- ranked just below the cluster -- never make the cut. The retrieved set is highly
relevant and highly redundant, which is the worst combination for a context window, because the model sees the same fact
three times and never sees the second fact it needed. The failure is not that the top chunks are irrelevant; it is that
they are relevant in the same way.

Maximal Marginal Relevance fixes this by ranking each candidate not on its relevance alone but on its MARGINAL relevance:
how relevant it is MINUS how similar it is to what you have already selected. It builds the result greedily. The first
pick is just the most relevant chunk. Each subsequent pick maximizes lambda * relevance(d) - (1-lambda) * max_similarity(
d, already_selected): a chunk earns its place by being relevant AND by being different from the chunks already chosen.
lambda tunes the trade-off -- lambda=1 is pure relevance (back to top-k), lambda=0 is pure diversity (ignore the query),
and a middle value keeps the best chunk while pushing near-duplicates down in favor of chunks that add something new. The
result covers more of the answer for the same k.

On this fixture chunks a1, a2, a3 are near-duplicates covering aspect A (relevance 0.90, 0.88, 0.86) and b1, b2 cover a
different aspect B (0.80, 0.78). Top-3 by relevance returns a1, a2, a3 -- three restatements of aspect A, with aspect B
missing entirely. MMR returns a1, b1, a2: it keeps the most relevant chunk a1, then at step 2 prefers b1 (marginal score
0.35) over the near-duplicate a2 (marginal score -0.01) because a2 is 0.9 similar to a1 and b1 is only 0.1 similar, so
the set now covers BOTH aspects. This computes both.

  --select   the top-k-by-relevance selection vs the MMR selection, with the aspect each set ends up covering
  --score    the MMR marginal scores at the second pick -- b1 beats the near-duplicate a2 despite lower raw relevance
  --check    top-k returns one redundant aspect and drops the other; MMR keeps the top chunk yet covers both aspects

The relevance, similarity, and lambda are the fixture; every selection and marginal score is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "mmr.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def sim(data, i, j):
    """Pairwise chunk similarity, looked up from the matrix by id position."""
    ids = data["ids"]
    return data["similarity"][ids.index(i)][ids.index(j)]


def top_k(data, k):
    """The k chunks with the highest raw relevance -- what a naive retriever returns."""
    return sorted(data["ids"], key=lambda d: data["relevance"][d], reverse=True)[:k]


def marginal_score(data, d, selected, lam):
    """MMR score for candidate d: lambda*relevance - (1-lambda)*max similarity to the already-selected set."""
    redundancy = max((sim(data, d, s) for s in selected), default=0.0)
    return lam * data["relevance"][d] - (1 - lam) * redundancy


def mmr(data, k, lam):
    """Greedy Maximal Marginal Relevance: repeatedly add the candidate with the highest marginal score."""
    selected = []
    candidates = list(data["ids"])
    while len(selected) < k and candidates:
        best = max(candidates, key=lambda d: marginal_score(data, d, selected, lam))
        selected.append(best)
        candidates.remove(best)
    return selected


def aspects(data, ids):
    """The set of distinct aspects covered by a selection."""
    return sorted({data["aspect"][d] for d in ids})


# ----------------------------------------------------------------- printing

def select_view(data):
    k, lam = data["k"], data["lambda"]
    tk = top_k(data, k)
    mm = mmr(data, k, lam)
    print("SELECT — top-k by relevance vs MMR (k=%d, lambda=%.1f)" % (k, lam))
    print("-" * 62)
    print("  chunk relevance and aspect:")
    for d in data["ids"]:
        print("    %-4s relevance %.2f  aspect %s" % (d, data["relevance"][d], data["aspect"][d]))
    print("-" * 62)
    print("  top-%d by relevance : %s   aspects covered: %s" % (k, tk, aspects(data, tk)))
    print("  MMR                : %s   aspects covered: %s" % (mm, aspects(data, mm)))
    print("  top-k returns 3 restatements of aspect A; MMR covers A and B.")


def score_view(data):
    lam = data["lambda"]
    print("SCORE — the second MMR pick, after a1 is selected (lambda=%.1f)" % lam)
    print("-" * 66)
    print("  candidate  relevance   sim to a1   marginal = %.1f*rel - %.1f*sim" % (lam, 1 - lam))
    for d in ("a2", "a3", "b1", "b2"):
        print("    %-4s     %.2f        %.1f         %.3f"
              % (d, data["relevance"][d], sim(data, d, "a1"), marginal_score(data, d, ["a1"], lam)))
    print("-" * 66)
    best = max(("a2", "a3", "b1", "b2"), key=lambda d: marginal_score(data, d, ["a1"], lam))
    print("  highest marginal score: %s -- a diverse chunk beats the near-duplicate a2." % best)


def check(data):
    print("SELF-TEST — top-k returns one redundant aspect and drops the other; MMR keeps the top chunk yet covers both aspects")
    print("-" * 120)
    k, lam = data["k"], data["lambda"]
    tk = top_k(data, k)
    mm = mmr(data, k, lam)

    topk_one_aspect = len(aspects(data, tk)) == 1
    print("  top-k covers only one aspect (redundant) = %s (%s)" % (topk_one_aspect, aspects(data, tk)))

    topk_drops_b = not any(data["aspect"][d] == "B" for d in tk)
    print("  top-k drops aspect B entirely = %s (%s)" % (topk_drops_b, tk))

    mmr_covers_both = len(aspects(data, mm)) == 2
    print("  MMR covers both aspects = %s (%s)" % (mmr_covers_both, aspects(data, mm)))

    mmr_keeps_best = mm[0] == tk[0]
    print("  MMR still picks the most relevant chunk first = %s (%s)" % (mmr_keeps_best, mm[0]))

    b1_beats_a2 = marginal_score(data, "b1", ["a1"], lam) > marginal_score(data, "a2", ["a1"], lam)
    print("  at step 2 the diverse b1 outscores the near-duplicate a2 = %s (%.3f > %.3f)"
          % (b1_beats_a2, marginal_score(data, "b1", ["a1"], lam), marginal_score(data, "a2", ["a1"], lam)))

    ok = topk_one_aspect and topk_drops_b and mmr_covers_both and mmr_keeps_best and b1_beats_a2
    print("-" * 120)
    print("SELF-TEST %s  topk_one_aspect=%s  topk_drops_b=%s  mmr_covers_both=%s  mmr_keeps_best=%s  b1_beats_a2=%s"
          % ("PASS" if ok else "FAIL", topk_one_aspect, topk_drops_b, mmr_covers_both, mmr_keeps_best, b1_beats_a2))
    return ok


def main():
    p = argparse.ArgumentParser(description="Maximal Marginal Relevance: top-k by relevance clusters near-duplicate chunks and wastes the context budget while dropping other relevant aspects; MMR selects greedily by marginal relevance (lambda*relevance - (1-lambda)*max similarity to the already-selected set), keeping the best chunk while favoring diversity so the returned set covers more of the answer.")
    p.add_argument("--select", action="store_true")
    p.add_argument("--score", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("ids=%s  lambda=%.1f  k=%d  file=%s  (the relevance and similarity are a fixture)"
          % (data["ids"], data["lambda"], data["k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.select:
        select_view(data)
    elif args.score:
        score_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
