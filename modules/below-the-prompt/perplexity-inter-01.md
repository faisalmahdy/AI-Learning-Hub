---
id: perplexity-inter-01
title: Perplexity is exp of the token-weighted mean loss — averaging per-sentence perplexities gives a different, wrong number
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Perplexity is the standard language-model metric, defined from the model's loss: the cross-entropy on a token is the negative log-likelihood (NLL) the model gave the true next token, and perplexity is exp(average NLL per token) — the effective number of equally-likely choices the model was deciding among at each step. The key is "per token" and "exp once": for a corpus, perplexity is exp(total NLL / total tokens), one token-weighted average exponentiated at the very end. Two aggregation mistakes give confidently wrong numbers. Averaging per-sentence perplexities — compute each sentence's perplexity, then take the arithmetic mean — is wrong because exp is convex, so the mean of exponentials is not the exponential of the mean, and one high-loss sentence's enormous perplexity dominates the average. Averaging the per-sentence per-token losses without weighting by token count, then exponentiating, is wrong because it treats a 5-token sentence as equal to a 20-token one. The correct recipe sums the NLL over all tokens, sums the tokens, divides, and exponentiates once — the same "aggregate in the right space" discipline as combining percentiles or gamma-encoded pixels. On a fixture of three sentences with total NLL 10, 6, 20 over 5, 10, 5 tokens, the corpus perplexity is exp(36/20) = exp(1.8) = 6.05, while averaging the per-sentence perplexities (7.39, 1.82, 54.60) gives 21.27 (3.5× too high, dominated by the third) and the unweighted mean gives 9.03.
eli5: Perplexity measures how "surprised" a language model is by text — lower is better, like a smaller number of options it was guessing between. To score a whole book you can't just score each sentence and average the scores, because the scoring involves an exponent that blows up for one really surprising sentence, and because long sentences should count more than short ones. The right way is to add up all the surprise across every word, divide by the total number of words, and take the exponent once at the end. Do it any other way and one weird sentence, or a bunch of short ones, throws the number off.
---

## Why this module

Perplexity looks like a simple average you can compute per sentence and mean over the dataset, and that intuition is wrong twice over. The metric lives in log space and is exponential, so both "average the perplexities" and "average without weighting by length" produce numbers that are not the corpus perplexity — and since they look like reasonable aggregation code, the wrong number gets reported and compared across models as if it were right.

Perplexity is the standard way to report how well a language model predicts text. It is defined from the model's loss: the cross-entropy loss on a token is the negative log-likelihood (NLL) the model assigned to the true next token, and perplexity is exp(average NLL per token). Intuitively it is the effective number of equally-likely choices the model was deciding among at each step — a perplexity of 6 means the model was about as uncertain as if it were guessing uniformly among 6 options. The key is "per token" and "exp once": for a whole corpus, perplexity is exp(total NLL / total tokens), a single token-weighted average exponentiated at the very end.

Two aggregation mistakes give confidently wrong numbers. The first is averaging per-sentence perplexities — compute each sentence's perplexity, then take their arithmetic mean. Because exp is convex, the mean of the exponentials is not the exponential of the mean: one sentence with a high loss has an enormous perplexity that dominates the average, so the mean-of-perplexities is inflated and does not equal the corpus perplexity. The second is averaging the per-sentence per-token losses without weighting by token count, then exponentiating — this treats a 5-token sentence as equal in weight to a 20-token one, so short sentences are over-counted. Both mistakes look like reasonable "average the metric over the dataset" code. The correct recipe sums the NLL over all tokens, sums the token counts, divides, and exponentiates once — the same "aggregate in the right space" discipline as combining percentiles or gamma-encoded pixels. This module computes the corpus perplexity and both wrong aggregates.

**Perplexity is exp of the token-weighted mean negative log-likelihood — exp(total NLL / total tokens), exponentiated once — so averaging per-sentence perplexities (the mean of exponentials, which a high-loss sentence dominates) or averaging per-token losses without token weighting both give different, wrong numbers.**

## Concepts

**Corpus perplexity** is the correct recipe: total NLL over total tokens, exponentiated once — a single token-weighted average.

```python filename=modules/below-the-prompt/code/perplexity-inter-01/perplexity.py:48-52 COMPLETE
def corpus_perplexity(sentences):
    """The correct perplexity: exp(total NLL / total tokens) -- one token-weighted average, exponentiated once."""
    total_nll = sum(s["total_nll"] for s in sentences)
    total_tokens = sum(s["tokens"] for s in sentences)
    return math.exp(total_nll / total_tokens)
```

**Mean of perplexities** is the first wrong way: exponentiate each sentence, then average. The mean of exponentials is not the exponential of the mean, so a high-loss sentence's huge perplexity dominates.

```python filename=modules/below-the-prompt/code/perplexity-inter-01/perplexity.py:60-62 COMPLETE
def mean_of_perplexities(sentences):
    """WRONG: average each sentence's perplexity (mean of exponentials -- a high-loss sentence dominates)."""
    return sum(sentence_perplexity(s) for s in sentences) / len(sentences)
```

**Unweighted perplexity** is the second wrong way: average the per-token losses without weighting by token count, then exponentiate — counting every sentence equally regardless of length.

```python filename=modules/below-the-prompt/code/perplexity-inter-01/perplexity.py:65-68 COMPLETE
def unweighted_perplexity(sentences):
    """WRONG: average the per-token losses without weighting by token count, then exponentiate."""
    mean_avg_nll = sum(s["total_nll"] / s["tokens"] for s in sentences) / len(sentences)
    return math.exp(mean_avg_nll)
```

<svg role="img" aria-label="A pipeline: per-token NLL adds in log space, then exp once gives the corpus perplexity; the wrong way exponentiates each sentence first and then averages" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">average in log space, exp once — not exp then average</text>
  <text x="10" y="34" fill="var(--s1)" font-size="7">correct</text>
  <g transform="translate(50,24)" font-size="6" fill="var(--muted)">
  <rect x="0" y="0" width="70" height="16" fill="none" stroke="var(--s1)"/><text x="6" y="10">sum NLL / tokens</text>
  <rect x="90" y="0" width="44" height="16" fill="none" stroke="var(--s1)"/><text x="98" y="10">exp once</text>
  <rect x="150" y="0" width="60" height="16" fill="var(--s1)"/><text x="158" y="10" fill="var(--panel)">PPL 6.05</text>
  <text x="76" y="11">→</text><text x="138" y="11">→</text>
  </g>
  <text x="10" y="72" fill="var(--s2)" font-size="7">wrong</text>
  <g transform="translate(50,62)" font-size="6" fill="var(--muted)">
  <rect x="0" y="0" width="70" height="16" fill="none" stroke="var(--s2)"/><text x="6" y="10">exp EACH sentence</text>
  <rect x="90" y="0" width="44" height="16" fill="none" stroke="var(--s2)"/><text x="96" y="10">average</text>
  <rect x="150" y="0" width="60" height="16" fill="var(--s2)"/><text x="158" y="10" fill="var(--panel)">21.27</text>
  <text x="76" y="11">→</text><text x="138" y="11">→</text>
  </g>
  <text x="10" y="100" fill="var(--muted)" font-size="7">exp is nonlinear, so the order (average-then-exp vs exp-then-average) changes the answer</text>
</svg>
^ The correct path averages the additive per-token loss in log space and exponentiates once (6.05); the wrong path exponentiates each sentence first and then averages (21.27), and because exp is nonlinear the two orders disagree.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/perplexity-inter-01/perplexity.py

The fixture is three sentences with their summed NLL and token counts.

```json filename=modules/below-the-prompt/code/perplexity-inter-01/perplexity.json:3-7 COMPLETE
  "sentences": [
    {"id": "s1", "total_nll": 10.0, "tokens": 5},
    {"id": "s2", "total_nll": 6.0,  "tokens": 10},
    {"id": "s3", "total_nll": 20.0, "tokens": 5}
  ]
```

Run `--perplexity`.

```text filename=--perplexity
PERPLEXITY — corpus vs two wrong aggregations
------------------------------------------------------------
  sentence   total_nll   tokens   per-sentence PPL
  s1         10.0        5        7.39
  s2         6.0         10       1.82
  s3         20.0        5        54.60
------------------------------------------------------------
  corpus PPL = exp(36/20) = exp(1.8)        = 6.05   <- correct
  mean of the per-sentence perplexities        = 21.27   <- wrong (exp is nonlinear)
  unweighted mean of per-token losses, exp'd   = 9.03   <- wrong (ignores token counts)
```

The corpus perplexity is exp(total NLL / total tokens) = exp(36/20) = exp(1.8) = 6.05 — the honest number. The mean of the per-sentence perplexities is 21.27, more than three times too high. Look at the per-sentence column to see why: sentence s3 has average loss 4.0, so its perplexity is exp(4) = 54.60, and averaging that with 7.39 and 1.82 lets that one exponentially-large value dominate — the arithmetic mean of perplexities is pulled toward the worst sentence far more than the token counts justify. The unweighted mean gives 9.03: it averages the per-token losses (2.0, 0.6, 4.0) as if each sentence counted once, getting mean 2.2, then exponentiates — but s2 has twice as many tokens as s1 or s3 and should count twice as much, and ignoring that over-weights the two short, high-loss sentences. Both wrong numbers would make the model look worse than it is, and reporting either — or comparing a model scored one way against a model scored another — is a silent evaluation error.

<svg role="img" aria-label="Sentences sized by token count: the corpus average weights s2 (10 tokens) twice as much as s1 and s3 (5 tokens each), while the unweighted mistake gives all three equal weight" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">perplexity averages over TOKENS, not sentences</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">correct (by tokens):</text>
  <g transform="translate(120,24)" font-size="6" fill="var(--panel)">
  <rect x="0" y="0" width="40" height="12" fill="var(--s1)"/><text x="4" y="9">s1: 5</text>
  <rect x="42" y="0" width="80" height="12" fill="var(--s1)"/><text x="46" y="9">s2: 10 (double)</text>
  <rect x="124" y="0" width="40" height="12" fill="var(--s1)"/><text x="128" y="9">s3: 5</text>
  </g>
  <text x="10" y="64" fill="var(--muted)" font-size="7">unweighted (wrong):</text>
  <g transform="translate(120,54)" font-size="6" fill="var(--panel)">
  <rect x="0" y="0" width="54" height="12" fill="var(--s2)"/><text x="14" y="9">s1</text>
  <rect x="56" y="0" width="54" height="12" fill="var(--s2)"/><text x="70" y="9">s2</text>
  <rect x="112" y="0" width="54" height="12" fill="var(--s2)"/><text x="126" y="9">s3</text>
  </g>
  <text x="10" y="92" fill="var(--muted)" font-size="7">giving each sentence equal weight over-counts the two short, high-loss ones</text>
</svg>
^ The corpus perplexity weights each sentence by its token count, so the 10-token s2 counts twice as much as the 5-token s1 and s3; the unweighted mistake gives all three equal weight, over-counting the short high-loss sentences and inflating the result.

## Build

The correct number is exactly a token-weighted average, and seeing the weights makes that concrete. Run `--weight`.

```text filename=--weight
WEIGHT — the corpus average weights each sentence by its token count
--------------------------------------------------------------
  sentence   avg NLL/token   tokens   weight (tokens/total)
  s1         2.00           5        0.25
  s2         0.60           10       0.50
  s3         4.00           5        0.25
--------------------------------------------------------------
  token-weighted mean NLL = 1.80  ->  exp = 6.05 (the corpus PPL)
  a 10-token sentence counts twice as much as a 5-token one, as it should.
```

Each sentence's average per-token loss is weighted by its share of the total tokens: s2 with 10 of the 20 tokens gets weight 0.50, and s1 and s3 with 5 each get 0.25. The token-weighted mean loss is 2.00×0.25 + 0.60×0.50 + 4.00×0.25 = 1.80, and exp(1.80) = 6.05 — identical to the corpus perplexity, because "total NLL / total tokens" *is* the token-weighted mean of the per-sentence average losses. That equivalence is the whole point: perplexity is an average over tokens, not over sentences, so a long sentence contributes more of the average than a short one, exactly in proportion to how many token-predictions it contains. The unweighted mistake replaces those token weights with equal 1/3 weights, and the mean-of-perplexities mistake applies the exp before averaging so the weights stop being weights at all. Getting perplexity right is getting the averaging level (tokens) and the averaging space (log) both correct.

```python filename=modules/below-the-prompt/code/perplexity-inter-01/perplexity.py:110-119 COMPLETE
    corpus_is_exp_weighted = abs(corpus - math.exp(total_nll / total_tokens)) < 1e-9
    print("  corpus PPL is exp(total NLL / total tokens) = %s (%.2f, mean NLL %.1f)" % (corpus_is_exp_weighted, corpus, total_nll / total_tokens))

    mean_ppls = mean_of_perplexities(sents)
    mean_of_ppls_wrong = abs(mean_ppls - corpus) > 1.0
    print("  averaging per-sentence perplexities differs = %s (%.2f vs %.2f)" % (mean_of_ppls_wrong, mean_ppls, corpus))

    unweighted = unweighted_perplexity(sents)
    unweighted_wrong = abs(unweighted - corpus) > 1.0
    print("  unweighted (per-sentence) mean differs = %s (%.2f vs %.2f)" % (unweighted_wrong, unweighted, corpus))
```

<svg role="img" aria-label="Three perplexity numbers: the correct corpus 6.05, the inflated mean-of-perplexities 21.27, and the unweighted 9.03" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">one dataset, three numbers — only exp(total/total) is right</text>
  <line x1="40" y1="90" x2="290" y2="90" stroke="var(--line)"/>
  <g transform="translate(60,0)">
  <rect x="0" y="66" width="40" height="24" fill="var(--s1)"/><text x="2" y="102" fill="var(--muted)" font-size="7">corpus</text><text x="10" y="62" fill="var(--muted)" font-size="7">6.05</text>
  </g>
  <g transform="translate(140,0)">
  <rect x="0" y="24" width="40" height="66" fill="var(--s2)"/><text x="0" y="102" fill="var(--muted)" font-size="7">mean-of-ppl</text><text x="6" y="20" fill="var(--muted)" font-size="7">21.27</text>
  </g>
  <g transform="translate(220,0)">
  <rect x="0" y="54" width="40" height="36" fill="var(--muted)"/><text x="0" y="102" fill="var(--muted)" font-size="7">unweighted</text><text x="10" y="50" fill="var(--muted)" font-size="7">9.03</text>
  </g>
</svg>
^ The correct corpus perplexity (6.05) is far below the mean-of-perplexities (21.27, inflated by the one high-loss sentence's exp) and the unweighted mean (9.03), so the aggregation method alone changes the reported metric by more than 3×.

## Definition of done

The self-test pins the correct recipe and both wrong aggregates.

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — corpus PPL = exp(total NLL / total tokens); the mean-of-perplexities and the unweighted mean both differ
----------------------------------------------------------------------------------------------------------------------
  corpus PPL is exp(total NLL / total tokens) = True (6.05, mean NLL 1.8)
  averaging per-sentence perplexities differs = True (21.27 vs 6.05)
  unweighted (per-sentence) mean differs = True (9.03 vs 6.05)
  the mean-of-perplexities is inflated by the high-loss sentence = True (21.27 > 6.05)
  the token-weighted mean loss reproduces the corpus PPL = True
```

**Done means the correct metric and both mistakes are proven on real numbers: the corpus perplexity is exp(total NLL / total tokens) = exp(1.8) = 6.05, averaging per-sentence perplexities gives 21.27 (inflated by the high-loss sentence, since exp is nonlinear), the unweighted mean gives 9.03, and the token-weighted mean loss reproduces 6.05 exactly — so perplexity must be aggregated over tokens in log space and exponentiated once.**

## Boss fight

Predict two ways perplexity misleads even when computed correctly, because the number depends on things other than model quality.

The first trap is that perplexity is not comparable across models with different tokenizers, and this invalidates many naive comparisons. Perplexity is per *token*, and the token is defined by the tokenizer, so a model that splits text into more, smaller tokens spreads the same information over more predictions and can report a lower per-token perplexity without being a better model — it is predicting easier, more numerous pieces. Two models with different vocabularies or tokenization schemes therefore cannot be compared by raw perplexity at all; you must either normalize to a tokenizer-independent unit (bits per byte or bits per character, which divide the total NLL by the number of bytes/characters rather than tokens) or evaluate both on the same tokenization. This is why leaderboards report bits-per-byte for cross-model comparison, and why "our model has lower perplexity" is meaningless without stating the tokenizer. The metric is only comparable when the denominator — what counts as one prediction — is held fixed.

The second trap is that perplexity measures next-token prediction on the evaluation text, which is related to but not the same as the quality anyone actually cares about, and it is sensitive to the data. A model can have excellent perplexity and still be unhelpful, untruthful, or bad at reasoning, because predicting the next token of fluent text rewards fluency and memorization more than correctness — which is why instruction-tuned and RLHF'd models are evaluated on task benchmarks and human preference, not perplexity alone, and can even show *higher* perplexity than a base model while being far more useful. Perplexity also depends heavily on the evaluation corpus (a model looks great on text like its training data and worse on a domain shift), is contaminated if the eval text leaked into training (memorized text has artificially low perplexity), and is affected by context length (more context lowers per-token loss). So perplexity is a legitimate, cheap, label-free measure of language-modeling ability on a held-out distribution, but it is a proxy: report it with its tokenizer and corpus, prefer bits-per-byte for cross-model comparison, guard against contamination, and never treat it as a standalone measure of how good a model is at the things a user wants.

**Perplexity is per-token so it is not comparable across different tokenizers — use bits-per-byte or a shared tokenization for cross-model comparison — and it measures next-token prediction on a specific, possibly-contaminated corpus rather than usefulness, so report it with its tokenizer and data, guard against eval-set leakage, and treat it as a cheap proxy for language-modeling ability, not a verdict on model quality.**

## External resources

Any language-modeling reference on perplexity and cross-entropy — the exp(mean NLL) definition, why it is the effective vocabulary size, and bits-per-byte / bits-per-character as tokenizer-independent alternatives.

Writing on evaluating language models — why perplexity is not comparable across tokenizers, why it is a proxy rather than a measure of usefulness, and how eval-set contamination and corpus choice affect it.

The companion cross-entropy-gradient and softmax modules in this topic, plus the percentile-aggregation module in ship-and-operate — perplexity is the exponentiated cross-entropy, and aggregating it (like aggregating percentiles) must happen in the right space and at the right level, not by averaging the already-transformed per-item values.
