"""Perplexity is exp of the token-weighted mean loss -- averaging per-sentence perplexities gives a different, wrong number.

Perplexity is the standard way to report how well a language model predicts text. It is defined from the model's loss:
the cross-entropy loss on a token is the negative log-likelihood (NLL) the model assigned to the true next token, and
perplexity is exp(average NLL per token). Intuitively it is the effective number of equally-likely choices the model was
deciding among at each step -- a perplexity of 6 means the model was about as uncertain as if it were guessing uniformly
among 6 options. The key is 'per token' and 'exp once': for a whole corpus, perplexity is exp(total NLL / total tokens),
a single token-weighted average exponentiated at the very end.

Two aggregation mistakes give confidently wrong numbers. The first is averaging per-sentence perplexities -- compute each
sentence's perplexity, then take their arithmetic mean. Because exp is convex, the mean of the exponentials is not the
exponential of the mean: one sentence with a high loss has an enormous perplexity that dominates the average, so the
mean-of-perplexities is inflated and does not equal the corpus perplexity. The second is averaging the per-sentence
per-token losses WITHOUT weighting by token count, then exponentiating -- this treats a 5-token sentence as equal in
weight to a 20-token one, so short sentences are over-counted, and the result is wrong whenever the sentences differ in
length. Both mistakes are easy to make because they look like reasonable 'average the metric over the dataset' code.

The correct recipe is: sum the NLL over all tokens in the corpus, sum the token counts, divide, and exponentiate once.
Equivalently, take a token-weighted average of the per-sentence average losses. This is the same 'aggregate in the right
space' discipline as combining percentiles or gamma-encoded pixels: perplexity lives in log space (the NLL is additive
per token), so you average in log space and exponentiate last, never average the already-exponentiated perplexities.

On this fixture three sentences have total NLL 10, 6, 20 over 5, 10, 5 tokens. The corpus perplexity is exp((10+6+20) /
(5+10+5)) = exp(1.8) = 6.05. Averaging the three per-sentence perplexities (7.39, 1.82, 54.60) gives 21.27 -- 3.5x too
high, dominated by the third sentence. Averaging the per-token losses unweighted and exponentiating gives 9.03. This
computes all three.

  --perplexity  the corpus perplexity, the per-sentence perplexities, and the two wrong aggregates -- 6.05 vs 21.27 vs 9.03
  --weight      why token-weighting matters: the corpus average weights each sentence by its token count, not by 1
  --check       corpus PPL = exp(total NLL / total tokens); the mean-of-perplexities and the unweighted mean both differ

The per-sentence NLL and token counts are the fixture; every perplexity is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "perplexity.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def corpus_perplexity(sentences):
    """The correct perplexity: exp(total NLL / total tokens) -- one token-weighted average, exponentiated once."""
    total_nll = sum(s["total_nll"] for s in sentences)
    total_tokens = sum(s["tokens"] for s in sentences)
    return math.exp(total_nll / total_tokens)


def sentence_perplexity(s):
    """One sentence's perplexity: exp(its average per-token NLL)."""
    return math.exp(s["total_nll"] / s["tokens"])


def mean_of_perplexities(sentences):
    """WRONG: average each sentence's perplexity (mean of exponentials -- a high-loss sentence dominates)."""
    return sum(sentence_perplexity(s) for s in sentences) / len(sentences)


def unweighted_perplexity(sentences):
    """WRONG: average the per-token losses without weighting by token count, then exponentiate."""
    mean_avg_nll = sum(s["total_nll"] / s["tokens"] for s in sentences) / len(sentences)
    return math.exp(mean_avg_nll)


# ----------------------------------------------------------------- printing

def perplexity_view(data):
    sents = data["sentences"]
    print("PERPLEXITY — corpus vs two wrong aggregations")
    print("-" * 60)
    print("  sentence   total_nll   tokens   per-sentence PPL")
    for s in sents:
        print("  %-9s  %-10.1f  %-7d  %.2f" % (s["id"], s["total_nll"], s["tokens"], sentence_perplexity(s)))
    print("-" * 60)
    print("  corpus PPL = exp(%d/%d) = exp(%.1f)        = %.2f   <- correct"
          % (sum(s["total_nll"] for s in sents), sum(s["tokens"] for s in sents),
             sum(s["total_nll"] for s in sents) / sum(s["tokens"] for s in sents), corpus_perplexity(sents)))
    print("  mean of the per-sentence perplexities        = %.2f   <- wrong (exp is nonlinear)" % mean_of_perplexities(sents))
    print("  unweighted mean of per-token losses, exp'd   = %.2f   <- wrong (ignores token counts)" % unweighted_perplexity(sents))


def weight_view(data):
    sents = data["sentences"]
    total_tokens = sum(s["tokens"] for s in sents)
    print("WEIGHT — the corpus average weights each sentence by its token count")
    print("-" * 62)
    print("  sentence   avg NLL/token   tokens   weight (tokens/total)")
    for s in sents:
        print("  %-9s  %-13.2f  %-7d  %.2f" % (s["id"], s["total_nll"] / s["tokens"], s["tokens"], s["tokens"] / total_tokens))
    print("-" * 62)
    weighted = sum((s["total_nll"] / s["tokens"]) * (s["tokens"] / total_tokens) for s in sents)
    print("  token-weighted mean NLL = %.2f  ->  exp = %.2f (the corpus PPL)" % (weighted, math.exp(weighted)))
    print("  a 10-token sentence counts twice as much as a 5-token one, as it should.")


def check(data):
    print("SELF-TEST — corpus PPL = exp(total NLL / total tokens); the mean-of-perplexities and the unweighted mean both differ")
    print("-" * 118)
    sents = data["sentences"]
    total_nll = sum(s["total_nll"] for s in sents)
    total_tokens = sum(s["tokens"] for s in sents)
    corpus = corpus_perplexity(sents)

    corpus_is_exp_weighted = abs(corpus - math.exp(total_nll / total_tokens)) < 1e-9
    print("  corpus PPL is exp(total NLL / total tokens) = %s (%.2f, mean NLL %.1f)" % (corpus_is_exp_weighted, corpus, total_nll / total_tokens))

    mean_ppls = mean_of_perplexities(sents)
    mean_of_ppls_wrong = abs(mean_ppls - corpus) > 1.0
    print("  averaging per-sentence perplexities differs = %s (%.2f vs %.2f)" % (mean_of_ppls_wrong, mean_ppls, corpus))

    unweighted = unweighted_perplexity(sents)
    unweighted_wrong = abs(unweighted - corpus) > 1.0
    print("  unweighted (per-sentence) mean differs = %s (%.2f vs %.2f)" % (unweighted_wrong, unweighted, corpus))

    mean_ppls_inflated = mean_ppls > corpus
    print("  the mean-of-perplexities is inflated by the high-loss sentence = %s (%.2f > %.2f)" % (mean_ppls_inflated, mean_ppls, corpus))

    weighted_equals_corpus = abs(math.exp(sum((s["total_nll"] / s["tokens"]) * (s["tokens"] / total_tokens) for s in sents)) - corpus) < 1e-9
    print("  the token-weighted mean loss reproduces the corpus PPL = %s" % weighted_equals_corpus)

    ok = corpus_is_exp_weighted and mean_of_ppls_wrong and unweighted_wrong and mean_ppls_inflated and weighted_equals_corpus
    print("-" * 118)
    print("SELF-TEST %s  corpus_is_exp_weighted=%s  mean_of_ppls_wrong=%s  unweighted_wrong=%s  mean_ppls_inflated=%s  weighted_equals_corpus=%s"
          % ("PASS" if ok else "FAIL", corpus_is_exp_weighted, mean_of_ppls_wrong, unweighted_wrong, mean_ppls_inflated, weighted_equals_corpus))
    return ok


def main():
    p = argparse.ArgumentParser(description="Perplexity: the language-model metric is exp of the token-weighted mean negative log-likelihood, i.e. exp(total NLL / total tokens) exponentiated once; averaging per-sentence perplexities (mean of exponentials) or averaging per-token losses without token weighting both give different, wrong numbers.")
    p.add_argument("--perplexity", action="store_true")
    p.add_argument("--weight", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("sentences=%s  file=%s  (the per-sentence NLL and token counts are a fixture)"
          % ([(s["id"], s["total_nll"], s["tokens"]) for s in data["sentences"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.perplexity:
        perplexity_view(data)
    elif args.weight:
        weight_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
