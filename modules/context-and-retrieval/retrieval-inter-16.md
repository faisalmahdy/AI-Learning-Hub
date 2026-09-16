---
id: retrieval-inter-16
title: Set the semantic cache threshold high — or a superficially similar query gets served the wrong answer
topic: context-and-retrieval
level: intermediate
status: ready
time: 21 min
summary: A semantic cache reuses a past answer when a new question is close enough to a cached one, keyed by embedding similarity — a big win for paraphrases, but the "close enough" threshold is a trade-off. Set it too low and a query that merely shares words with a cached one gets served a confidently wrong cached answer. On a cache of a password-reset and a cancel-subscription answer, "reset my subscription" sits at similarity 0.667 to both; a loose threshold of 0.60 serves it a wrong answer, while a tight 0.80 rejects it yet still serves the true paraphrase (similarity 0.866) from cache.
eli5: A helper who remembers past answers can save time by reusing one when a new question sounds like an old one. But "sounds like" can fool it: "reset my subscription" sounds a bit like both "reset my password" and "cancel my subscription," so a careless helper hands over one of those wrong answers. Only reuse when the match is really close — close enough for a true reword, not just some shared words.
---

## Why this module

Reusing a cached answer is only safe when the new question truly means the same thing, and a loose similarity threshold cannot tell "same meaning" from "shares some words."

A semantic cache is a speed and cost optimization for a retrieval or generation system: it remembers past questions and their answers, keyed by the question's embedding, and when a new question comes in close enough to a cached one, it returns the stored answer instead of doing the expensive work again. For genuine paraphrases this is a huge win — "how do I reset my password" and "reset my password please" are the same request and should share one answer, computed once. The entire mechanism rests on the phrase "close enough," which in practice is a similarity threshold: reuse the cached answer if the nearest cached question's similarity clears some bar.

That bar is a trade-off, and setting it too low is how the cache starts lying. A low threshold fires the cache on questions that merely overlap in words with a cached one but ask about something different. The victim is a query that shares vocabulary with a cached entry while having a different intent — it lands at moderate similarity, high enough to trip a loose threshold, and gets handed a cached answer that does not actually answer it. The user asked one thing and confidently received the answer to another, with no indication anything went wrong, because a cache hit looks identical to a correct answer.

The structure that makes a good threshold possible is that true paraphrases sit at high similarity to their match, while lexical-overlap impostors sit at moderate similarity — so there is a band between them. Set the threshold above the impostor band and below the paraphrase band and the cache reuses answers only for genuine rephrasings, rejecting the lookalikes (which then get computed fresh, correctly). Set it too low and you pull impostors in; set it absurdly high and you lose real paraphrases and the cache stops helping. The threshold is the whole safety mechanism.

On the fixture, the cache holds a password-reset answer and a cancel-subscription answer. The different-intent query "reset my subscription" sits at similarity 0.667 to both. A loose threshold of 0.60 makes it hit a cached answer — a wrong reuse — while a tight threshold of 0.80 rejects it (so it is computed fresh) yet still serves the true paraphrase "reset my password please" (similarity 0.866) from cache.

**A semantic cache reuses an answer when a new question clears a similarity threshold; too low a threshold serves a cached answer to a different-intent query that merely shares words, because true paraphrases sit high and lexical-overlap impostors sit moderate — so the threshold must be set in the band between them.**

## Concepts

The cache trades correctness risk for speed, and the threshold is the dial that sets the exchange rate. Every cache hit skips the real work, so a higher hit rate is more savings — which pushes toward a low threshold — but every hit also asserts "the cached answer is right for this question," and a wrong assertion is a wrong answer served to a user, which pushes toward a high threshold. There is no free lunch: the threshold picks a point on the curve between hit rate and wrong-answer rate, and the right point depends on how costly a wrong reuse is. For a low-stakes suggestion a looser threshold is fine; for anything a user acts on, wrong reuse is expensive and the threshold should be strict.

The failure is specifically about the difference between lexical overlap and semantic identity. Two questions can share many words and mean different things ("reset my password" versus "reset my subscription"), and two questions can share few surface words and mean the same thing ("how do I change my password" versus "password reset steps"). A similarity score — especially a lexical one, but even an embedding one — is an imperfect proxy for "same intent," and the imperfection is worst exactly in the moderate-similarity band, where a question shares enough words to score middling but not enough meaning to deserve the same answer. A loose threshold lives in that band, which is why it is dangerous.

<svg role="img" aria-label="As the threshold rises, hit rate falls and wrong-answer rate falls; the safe zone is the threshold band above the impostors and below the paraphrases" viewBox="0 0 470 180" width="470" height="180">
  <rect x="0" y="0" width="470" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">threshold (low → high) vs hit rate and wrong-answer rate</text>
  <line x1="40" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="40" x2="40" y2="150" stroke="var(--line)"/>
  <polyline points="55,55 150,70 245,95 340,120 430,145" fill="none" stroke="var(--acc-line)" stroke-width="2"/>
  <text x="300" y="118" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">hit rate falls</text>
  <polyline points="55,60 150,85 245,140 340,148 430,149" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="60" y="72" font-family="var(--mono)" font-size="8" fill="var(--s2)">wrong-answer rate</text>
  <rect x="230" y="40" width="70" height="110" fill="var(--acc-soft)" opacity="0.4"/>
  <text x="222" y="168" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">safe band: wrong≈0, hits kept</text>
</svg>
^ Raising the threshold lowers both the hit rate and the wrong-answer rate, but the wrong-answer rate drops faster; the safe band is where wrong reuse has vanished but real paraphrases still hit.

Asymmetry of cost is the reason the threshold should err high. A cache miss is cheap: you do the work you would have done anyway, so a false miss (rejecting a real paraphrase) costs one recomputation. A false hit is expensive: you serve a wrong answer, which the user may act on, and you have no signal that it happened. Because a wrong hit is far worse than a needless miss, the threshold should be set conservatively — high enough that only near-certain paraphrases reuse. This is the same logic as any precision/recall trade-off where a false positive is costlier than a false negative: bias toward precision (few, confident hits) over recall (many hits, some wrong).

This is a real pattern in production LLM systems, and its cautions generalize. Semantic caches (and their cousins, prompt caches keyed by semantic similarity) do cut latency and cost meaningfully, but they need a well-calibrated threshold, and often more: normalizing queries, scoping the cache per user or per context so a different user's answer is not reused, and sometimes a cheap verification that the cached answer still fits before serving it. The deeper point is that similarity is not identity — a threshold turns a continuous similarity into a binary reuse decision, and where you put it decides whether the cache is a safe optimization or a source of silent wrong answers. Measure the impostor and paraphrase bands on real traffic and set the threshold between them, leaning high.

**The threshold trades hit rate against wrong-answer rate; the danger band is moderate similarity where lexical overlap outruns semantic identity, and because a false hit (wrong answer served) is far costlier than a false miss (a recomputation), the threshold should be set conservatively high, between the impostor and paraphrase bands.**

## Worked example

The fixture is a small cache, incoming queries with their expected match, and two candidate thresholds.

```json filename=modules/context-and-retrieval/code/retrieval-inter-16/queries.json:5-14 COMPLETE
  "cache": [
    {"id": "ans_reset_pw", "query": "reset my password"},
    {"id": "ans_cancel_sub", "query": "cancel my subscription"}
  ],
  "queries": [
    {"text": "reset my password please", "expected": "ans_reset_pw"},
    {"text": "reset my subscription", "expected": null}
  ]
```

The first incoming query is a true paraphrase of the password-reset entry (expected: reuse it); the second is a novel intent that shares words with both cached entries but matches neither (expected: null, should miss). Similarity is bag-of-words cosine, a stand-in for an embedding so the matching is visible; the cache serves the nearest entry's answer only if the similarity clears the threshold.

```python filename=modules/context-and-retrieval/code/retrieval-inter-16/cache.py:64-67 COMPLETE
def serve(query, cache, threshold):
    """Return the cached answer id if the nearest is within threshold, else None (a cache miss)."""
    best, sim = nearest(query, cache)
    return best["id"] if sim >= threshold else None
```

A wrong reuse is a hit that returns an id other than the query's expected match — including any hit at all when the expected match is null.

```python filename=modules/context-and-retrieval/code/retrieval-inter-16/cache.py:70-73 COMPLETE
def is_wrong_reuse(q, cache, threshold):
    """A hit that returns an id other than the query's expected match (None expected = should have missed)."""
    served = serve(q["text"], cache, threshold)
    return served is not None and served != q["expected"]
```

The nearest cached entry is just the highest-cosine one, returned with its similarity for the threshold test.

```python filename=modules/context-and-retrieval/code/retrieval-inter-16/cache.py:58-61 COMPLETE
def nearest(query, cache):
    """The cached entry most similar to the query, and that similarity."""
    best = max(cache, key=lambda e: cosine(vec(query), vec(e["query"])))
    return best, cosine(vec(query), vec(best["query"]))
```

Predict: the paraphrase sits at high similarity to its match; the different-intent query sits at moderate similarity to both. Look at the similarities.

```text filename=modules/context-and-retrieval/code/retrieval-inter-16/cache.py --sim
SIM — each incoming query's nearest cached entry
--------------------------------------------------------------
  'reset my password please' -> ans_reset_pw  sim 0.866   (want ans_reset_pw)
  'reset my subscription'    -> ans_reset_pw  sim 0.667   (want none (novel))
--------------------------------------------------------------
  the paraphrase sits high; the different-intent query sits moderate.
```

The paraphrase scores 0.866 against the password-reset entry — clearly its match. The different-intent "reset my subscription" scores 0.667, its nearest being the password-reset entry (it shares "reset" and "my"), even though it is not about passwords at all. That 0.667 is the danger band: high enough to look like a match, low enough that it is not one. Now serve at both thresholds.

```text filename=modules/context-and-retrieval/code/retrieval-inter-16/cache.py --serve
SERVE — what each threshold serves (loose 0.60 vs tight 0.80)
------------------------------------------------------------------
  query                        loose         tight
  'reset my password please'   ans_reset_pw          ans_reset_pw
  'reset my subscription'      ans_reset_pw (WRONG)  miss
------------------------------------------------------------------
  loose serves a wrong answer to the different-intent query; tight does not.
```

At the loose threshold of 0.60, both queries clear the bar. The paraphrase correctly gets the password-reset answer — but so does "reset my subscription," which is flagged WRONG: it was served the password-reset answer for a question about subscriptions, a confidently wrong cache hit. At the tight threshold of 0.80, the paraphrase (0.866) still clears the bar and is served from cache, but the impostor (0.667) does not, so it misses and gets computed fresh — correctly. The tight threshold kept the good reuse and rejected the bad one, because it sits in the band between 0.667 and 0.866.

<svg role="img" aria-label="A similarity axis with the impostor at 0.667 and the paraphrase at 0.866; the loose threshold 0.60 admits both, the tight threshold 0.80 falls between them and admits only the paraphrase" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">similarity axis (0 → 1): where each query and threshold sits</text>
  <line x1="40" y1="90" x2="450" y2="90" stroke="var(--line)"/>
  <text x="36" y="108" font-family="var(--mono)" font-size="7" fill="var(--muted)">0</text>
  <text x="440" y="108" font-family="var(--mono)" font-size="7" fill="var(--muted)">1</text>
  <line x1="286" y1="70" x2="286" y2="110" stroke="var(--s2)" stroke-dasharray="3 2"/>
  <text x="250" y="128" font-family="var(--mono)" font-size="7" fill="var(--s2)">impostor 0.667</text>
  <circle cx="286" cy="90" r="5" fill="var(--s2)"/>
  <line x1="394" y1="70" x2="394" y2="110" stroke="var(--acc-line)" stroke-dasharray="3 2"/>
  <text x="360" y="60" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">paraphrase 0.866</text>
  <circle cx="394" cy="90" r="5" fill="var(--acc-line)"/>
  <line x1="286" y1="40" x2="286" y2="140" stroke="var(--s2)"/>
  <text x="180" y="44" font-family="var(--mono)" font-size="7" fill="var(--s2)">loose 0.60 → admits both (impostor slips in)</text>
  <line x1="246" y1="40" x2="246" y2="140" stroke="var(--s2)" stroke-width="0"/>
  <text x="60" y="150" font-family="var(--mono)" font-size="7" fill="var(--muted)">loose bar left of impostor</text>
  <line x1="340" y1="40" x2="340" y2="140" stroke="var(--acc-line)" stroke-width="2"/>
  <text x="300" y="30" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">tight 0.80 → between them</text>
</svg>
^ The impostor (0.667) and the paraphrase (0.866) leave a band between them; the loose bar (0.60) sits left of both and admits the impostor, while the tight bar (0.80) sits in the band and admits only the paraphrase.

## Build

Reproduce the serves. Pure standard library, deterministic, so the 0.866 paraphrase and 0.667 impostor similarities and the two thresholds' decisions come out exactly.

Run `--sim` for the similarities, `--serve` for what each threshold serves, `--check` for the gate. <svg role="img" aria-label="A two-by-two of the two queries under the two thresholds: loose serves both (one wrong), tight serves the paraphrase and misses the impostor" viewBox="0 0 470 160" width="470" height="160">
  <rect x="0" y="0" width="470" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">what each threshold serves</text>
  <text x="170" y="42" font-family="var(--mono)" font-size="9" fill="var(--s2)">loose 0.60</text>
  <text x="320" y="42" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">tight 0.80</text>
  <text x="20" y="80" font-family="var(--mono)" font-size="8" fill="var(--ink)">paraphrase</text>
  <text x="170" y="80" font-family="var(--mono)" font-size="9" fill="var(--acc-line)">serve ✓</text>
  <text x="320" y="80" font-family="var(--mono)" font-size="9" fill="var(--acc-line)">serve ✓</text>
  <text x="20" y="118" font-family="var(--mono)" font-size="8" fill="var(--ink)">reset subscription</text>
  <text x="170" y="118" font-family="var(--mono)" font-size="9" fill="var(--s2)">serve WRONG</text>
  <text x="320" y="118" font-family="var(--mono)" font-size="9" fill="var(--acc-line)">miss (fresh) ✓</text>
  <line x1="150" y1="52" x2="150" y2="130" stroke="var(--line)"/>
  <line x1="15" y1="92" x2="440" y2="92" stroke="var(--line)" stroke-dasharray="2 2"/>
</svg>
^ Both thresholds serve the true paraphrase; only the loose one also serves the impostor a wrong answer, while the tight one correctly sends it to a fresh computation.

The self-test pins the loose threshold's wrong reuse and the tight threshold's clean, still-useful behavior.

```python filename=modules/context-and-retrieval/code/retrieval-inter-16/cache.py:114-118 COMPLETE
    loose_wrong_reuse = any(is_wrong_reuse(q, cache, lo) for q in queries)
    print("  the loose threshold produces a wrong reuse = %s (%s)"
          % (loose_wrong_reuse, [q["text"] for q in queries if is_wrong_reuse(q, cache, lo)]))

    tight_no_wrong_reuse = not any(is_wrong_reuse(q, cache, hi) for q in queries)
    print("  the tight threshold produces no wrong reuse = %s" % tight_no_wrong_reuse)
```

```text filename=modules/context-and-retrieval/code/retrieval-inter-16/cache.py --check
SELF-TEST — a loose threshold serves a wrong cached answer; a tight one rejects it and keeps the good hit
--------------------------------------------------------------------------------------------------------
  the loose threshold produces a wrong reuse = True (['reset my subscription'])
  the tight threshold produces no wrong reuse = True
  the tight threshold still serves the true paraphrase from cache = True (ans_reset_pw)
  the tight threshold makes the different-intent query miss = True
  the paraphrase is more similar than the impostor, so a threshold separates them = True (0.866 > 0.667)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  loose_wrong_reuse=True  tight_no_wrong_reuse=True  tight_keeps_good_hit=True  tight_rejects_novel=True  separable=True
```

Five True flags. Loose_wrong_reuse: the loose threshold serves a wrong answer to the different-intent query. Tight_no_wrong_reuse: the tight threshold serves no wrong answer. Tight_keeps_good_hit: it still serves the true paraphrase from cache, so it did not just turn the cache off. Tight_rejects_novel: it makes the impostor miss (compute fresh). Separable: the paraphrase (0.866) is more similar than the impostor (0.667), so a threshold between them exists. The keeps-good-hit flag matters because it proves the fix is a better threshold, not abandoning caching — the tight setting preserves the real savings while removing the wrong answer.

**The separable flag is the precondition for the whole fix — because the paraphrase scores higher than the impostor, a threshold between them serves the real reuse and rejects the wrong one; when that gap closes, no threshold is safe and you need more than similarity.**

## Definition of done

You are done when you reproduce the wrong reuse and its fix, and can explain why the threshold must sit between the bands.

Concretely: `--sim` shows the paraphrase at 0.866 and the impostor at 0.667; `--serve` shows the loose 0.60 serving a wrong answer to the impostor while the tight 0.80 rejects it and still serves the paraphrase; `--check` prints PASS with five True flags. You can explain that the threshold trades hit rate against wrong-answer rate, that the danger is the moderate-similarity band where lexical overlap outruns semantic identity, and that a false hit (wrong answer) is far costlier than a false miss (a recomputation), so the threshold should lean high. You can name the complements: normalize queries, scope the cache per user, and verify the cached answer fits.

The habit to carry: set a semantic cache's reuse threshold conservatively high, calibrated on real traffic so it sits above the lexical-overlap band and below the paraphrase band, and treat a false hit as a wrong answer, not a minor cache miss. When users occasionally get an answer that is confidently about the wrong thing, suspect an over-loose semantic cache serving a similar-looking neighbor, and raise the threshold (and scope the cache) before blaming the model. Reuse only on near-certain matches.

## Boss fight

The instructive failure is a support bot that answers the wrong question because its cache is too eager.

A team adds a semantic cache to its support assistant to cut latency and API cost, keyed by question embedding with a similarity threshold tuned for a high hit rate. Cost drops, but complaints rise: users asking "how do I cancel my subscription" sometimes get the steps to cancel an *order*, because the two questions are lexically similar and the loose threshold reused the order-cancellation answer. The cache is confidently serving wrong answers, and because a hit looks like a normal response, it is hard to notice in aggregate metrics. The fix is to raise the threshold so only near-paraphrases hit (measured against real query pairs), scope the cache so answers are not reused across clearly different intents, and optionally verify the retrieved answer's topic matches before serving.

Your turn, two moves. First, find the safe threshold by sweeping it from 0.60 upward and locating the value that first stops the wrong reuse while still serving the paraphrase — confirm it lies strictly between 0.667 and 0.866, the two bands, and that any value there works. Second, close the gap to break the cache: add an impostor that is a near-paraphrase in words but a different intent (raising its similarity toward 0.85), and confirm no threshold both admits the real paraphrase and rejects it — showing that when lexical similarity and intent diverge, a similarity threshold alone is insufficient and you need query normalization, per-intent scoping, or answer verification.

## External resources

Writeups of LLM semantic caching (GPTCache's documentation and design notes) describe the embedding-keyed cache and, crucially, the similarity-threshold tuning and eviction concerns this module centers on.

Any treatment of precision/recall trade-offs and threshold selection (ROC analysis, cost-sensitive classification) is the general framework for setting the reuse bar when a false positive costs more than a false negative.

Discussions of prompt and response caching in production LLM systems (from vendors and practitioners) cover the complements — normalizing and scoping cache keys, and verifying a cached response before serving it — that make a semantic cache safe beyond the threshold alone.
