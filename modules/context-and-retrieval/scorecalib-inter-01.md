---
id: scorecalib-inter-01
title: A fixed similarity threshold doesn't transfer across queries — calibrate the cutoff per query
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: A retriever scores each candidate by similarity to the query, and to decide which candidates are relevant — or whether to abstain — a system compares the score to a threshold, and the tempting choice is a single absolute number like keep everything with cosine at least 0.70. The flaw is that similarity scores are not calibrated between queries: a query whose topic is richly represented in the corpus produces high scores, while a query about a rare or narrow topic produces lower scores across the board, so even its single genuinely-best match sits well below the easy query's matches. One constant cutoff is therefore simultaneously too loose for the high-scoring query (admitting marginal candidates) and too strict for the low-scoring one (rejecting the correct answer because its absolute score is low). The fix is to make the threshold relative to the query — keep candidates whose score is at least a fraction of that query's own top score (or use the gap between the top scores) — so the cutoff scales with each query's range. On the fixture the easy query scores 0.90, 0.82, 0.45, 0.30 with 2 truly relevant and the hard query scores 0.58, 0.40, 0.35, 0.30 with 1 truly relevant: an absolute threshold of 0.70 keeps the right 2 for the easy query but keeps 0 for the hard query, missing its relevant answer at 0.58, while a relative threshold of 0.85 times the query's top score keeps 2 and 1, both correct. This is distinct from whether to have an abstention threshold at all — the point is that the threshold's value cannot be one global constant. The rule: a similarity score is meaningful within a query's own ranking but not comparable across queries, so any cutoff on it must be calibrated per query.
eli5: Imagine grading tests from two classes, where one test was easy (top scores in the 90s) and the other was brutally hard (top score 58). If you set one pass mark at 70 for both, everyone in the easy class who did fine passes, but the best student in the hard class — who genuinely aced the hardest test — fails, just because the numbers were lower. The scores from the two tests aren't on the same scale, so one pass mark can't fit both. The fix is to grade relative to each test: pass the students who scored near the top of their own test. Retrieval scores are the same — a 0.58 can be the best possible match for one question and a mediocre one for another — so the cutoff has to bend to each query.
---

## Why this module

Retrieval systems constantly need a yes/no line on a continuous score: is this chunk relevant enough to include, is any chunk good enough to answer at all, should we fall back to "I don't know." The obvious implementation is a constant — pick a cosine threshold, apply it everywhere.

That constant quietly assumes similarity scores are comparable across queries, and they are not. The same cosine value can be an excellent match for a hard query and a weak one for an easy query, so a single line drawn across all queries is miscalibrated for every query but the ones it happened to be tuned on. The failure is worst where it is least visible: a hard query's genuinely-correct answer gets scored below the line and the system abstains or drops it, reporting nothing wrong.

**A similarity score ranks candidates within one query but is not comparable across queries, so a single global threshold is miscalibrated for all but the queries it was tuned on.**

## Concepts

Similarity scores come from the geometry of the query and the documents in the embedding space, and that geometry differs per query. A query near a dense, well-covered region of the corpus has many documents close to it, so its top scores are high. A query in a sparse region — a rare topic, an unusual phrasing — has its nearest documents farther away, so even its best, genuinely-relevant match scores lower. The scores are calibrated within a query: higher means more relevant to that query. They are not calibrated across queries: a 0.58 for one query and a 0.58 for another do not mean the same degree of relevance.

An absolute threshold treats them as if they were comparable. Set it at 0.70 and it works for whatever queries you tuned it on, then fails in both directions elsewhere. For a high-scoring query it sits low in the query's range, so it admits marginal candidates the query happens to score above 0.70. For a low-scoring query it sits above the entire range, so it rejects everything — including the one candidate that is the correct answer, whose only crime is that its absolute score is modest.

The rejection case is the dangerous one, because it is silent. The retriever had the right document; the threshold discarded it, and the system either abstains ("no relevant results") or answers from worse material, with no error to signal that a correct answer was thrown away for scoring 0.58 instead of 0.70.

The fix is to calibrate the threshold to each query. A relative rule keeps candidates whose score is at least a fraction of that query's own top score, so the cutoff rises for a high-scoring query and falls for a low-scoring one, always sitting at the same relative position within whatever range the query produced. A related signal is the gap between the top scores — a confident retrieval has a clear leader, a diffuse one does not. Either way, the decision is made within the query's own distribution, where the scores actually mean something, rather than against a constant they cannot be compared to.

**Scores are calibrated within a query, not across queries, so the cutoff must be set relative to each query's own scores, not as one absolute constant.**

<svg role="img" aria-label="Two queries' score ranges shown as vertical bars: the easy query spans high (0.30 to 0.90), the hard query spans low (0.30 to 0.58). A single absolute line at 0.70 cuts the easy range in a sensible place but sits entirely above the hard range." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="12">score ranges differ per query; one line can't fit both</text>
<line x1="30" y1="60" x2="290" y2="60" stroke="var(--s1)" stroke-dasharray="4 3"></line>
<text x="292" y="63" fill="var(--s1)" font-size="8">0.70</text>
<rect x="90" y="34" width="16" height="90" fill="var(--s2)"></rect>
<text x="78" y="138" fill="var(--muted)" font-size="9">easy 0.30-0.90</text>
<text x="112" y="46" fill="var(--muted)" font-size="8">line splits it well</text>
<rect x="210" y="80" width="16" height="44" fill="var(--s2)"></rect>
<text x="196" y="138" fill="var(--muted)" font-size="9">hard 0.30-0.58</text>
<text x="150" y="92" fill="var(--s1)" font-size="8">line above the whole range</text>
</svg>
^ The easy query's scores span up to 0.90 and the hard query's top out at 0.58, so a line at 0.70 lands inside one range and above the other — no single height fits both.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/context-and-retrieval/code/scorecalib-inter-01/scorecalib.py

The fixture is two queries with different score scales.

```json filename=modules/context-and-retrieval/code/scorecalib-inter-01/scorecalib.json:3-7 COMPLETE
  "absolute_threshold": 0.70,
  "relative_ratio": 0.85,
  "queries": [
    {"name": "easy", "scores": [0.90, 0.82, 0.45, 0.30], "relevant": 2},
    {"name": "hard", "scores": [0.58, 0.40, 0.35, 0.30], "relevant": 1}
  ]
```

The absolute rule applies one constant; the relative rule scales to each query's top score.

```python filename=modules/context-and-retrieval/code/scorecalib-inter-01/scorecalib.py:30-32 COMPLETE
def keep_absolute(scores, threshold):
    """Keep candidates whose score meets a fixed absolute threshold."""
    return [s for s in scores if s >= threshold]
```

```python filename=modules/context-and-retrieval/code/scorecalib-inter-01/scorecalib.py:35-38 COMPLETE
def keep_relative(scores, ratio):
    """Keep candidates whose score is at least a fraction of this query's own top score."""
    cutoff = ratio * max(scores)
    return [s for s in scores if s >= cutoff]
```

```python filename=modules/context-and-retrieval/code/scorecalib-inter-01/scorecalib.py:41-43 COMPLETE
def correct(kept, relevant):
    """Whether the number kept equals the number of truly relevant candidates."""
    return len(kept) == relevant
```

```text filename=scorecalib.py --absolute
ABSOLUTE — one fixed cutoff of 0.70 for every query
----------------------------------------------------------------
  easy  scores [0.9, 0.82, 0.45, 0.3]  kept 2  (truth 2)  ok
  hard  scores [0.58, 0.4, 0.35, 0.3]  kept 0  (truth 1)  WRONG
----------------------------------------------------------------
  the cutoff that fits the high-scoring query rejects the low-scoring query's real answer
```

The 0.70 cutoff is right for the easy query — its two relevant docs (0.90, 0.82) clear it and the two irrelevant ones (0.45, 0.30) do not. On the hard query the same 0.70 sits above every score, so it keeps nothing, discarding the correct answer at 0.58. One threshold, correct for one query and silently wrong for the other.

<svg role="img" aria-label="Two score scales side by side with a single horizontal threshold line at 0.70. The easy query's top two scores are above the line and its bottom two below. The hard query's scores are all below the line, including its relevant top score at 0.58." viewBox="0 0 320 160">
<rect x="0" y="0" width="320" height="160" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="12">one cutoff (0.70) across two score scales</text>
<line x1="30" y1="58" x2="290" y2="58" stroke="var(--s1)" stroke-dasharray="4 3"></line>
<text x="292" y="61" fill="var(--s1)" font-size="8">0.70</text>
<text x="60" y="150" fill="var(--muted)" font-size="9">easy</text>
<circle cx="70" cy="34" r="4" fill="var(--s2)"></circle>
<circle cx="70" cy="46" r="4" fill="var(--s2)"></circle>
<circle cx="70" cy="98" r="4" fill="var(--muted)"></circle>
<circle cx="70" cy="118" r="4" fill="var(--muted)"></circle>
<text x="90" y="42" fill="var(--s2)" font-size="8">2 relevant, above line</text>
<text x="220" y="150" fill="var(--muted)" font-size="9">hard</text>
<circle cx="230" cy="80" r="4" fill="var(--s2)"></circle>
<circle cx="230" cy="104" r="4" fill="var(--muted)"></circle>
<circle cx="230" cy="112" r="4" fill="var(--muted)"></circle>
<circle cx="230" cy="120" r="4" fill="var(--muted)"></circle>
<text x="150" y="84" fill="var(--s1)" font-size="8">relevant 0.58, below line &#8594; rejected</text>
</svg>
^ The line at 0.70 splits the easy query correctly but falls above the entire hard query, so the hard query's relevant answer at 0.58 is below it and thrown away.

## Build

The relative rule sets the cutoff from each query's own top score.

```text filename=scorecalib.py --relative
RELATIVE — cutoff = 0.85 x each query's own top score
----------------------------------------------------------------
  easy  top 0.90  cutoff 0.765  kept 2  (truth 2)  ok
  hard  top 0.58  cutoff 0.493  kept 1  (truth 1)  ok
----------------------------------------------------------------
  the cutoff scales to each query's range, so each keeps what stands out for it
```

For the easy query the cutoff is 0.85 × 0.90 = 0.765, keeping the two high scores. For the hard query it is 0.85 × 0.58 = 0.493, keeping just the 0.58 answer and rejecting the 0.40 and below. The same rule, expressed relative to each query, gets both right — because it judges each candidate against its own query's scale.

<svg role="img" aria-label="The relative cutoff drawn at a different height for each query: high for the easy query (0.765) just below its top two scores, low for the hard query (0.493) just below its single relevant score." viewBox="0 0 320 160">
<rect x="0" y="0" width="320" height="160" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="12">per-query cutoff = 0.85 x that query's top</text>
<text x="60" y="150" fill="var(--muted)" font-size="9">easy</text>
<line x1="40" y1="52" x2="110" y2="52" stroke="var(--s2)" stroke-dasharray="4 3"></line>
<text x="40" y="48" fill="var(--s2)" font-size="8">0.765</text>
<circle cx="75" cy="34" r="4" fill="var(--s2)"></circle>
<circle cx="75" cy="46" r="4" fill="var(--s2)"></circle>
<circle cx="75" cy="98" r="4" fill="var(--muted)"></circle>
<circle cx="75" cy="118" r="4" fill="var(--muted)"></circle>
<text x="220" y="150" fill="var(--muted)" font-size="9">hard</text>
<line x1="200" y1="92" x2="270" y2="92" stroke="var(--s2)" stroke-dasharray="4 3"></line>
<text x="200" y="88" fill="var(--s2)" font-size="8">0.493</text>
<circle cx="235" cy="80" r="4" fill="var(--s2)"></circle>
<circle cx="235" cy="104" r="4" fill="var(--muted)"></circle>
<circle cx="235" cy="112" r="4" fill="var(--muted)"></circle>
<circle cx="235" cy="120" r="4" fill="var(--muted)"></circle>
<text x="150" y="78" fill="var(--s2)" font-size="8">0.58 kept</text>
</svg>
^ The cutoff sits at the same relative height within each query — just under the easy query's top pair and just under the hard query's lone relevant score — so both are judged correctly.

The self-test states the non-transfer and the fix.

```python filename=modules/context-and-retrieval/code/scorecalib-inter-01/scorecalib.py:79-83 COMPLETE
    abs_ok_easy = correct(keep_absolute(easy["scores"], t), easy["relevant"])
    print("  absolute threshold is correct for the high-scoring query = %s (kept %d, truth %d)" % (abs_ok_easy, len(keep_absolute(easy["scores"], t)), easy["relevant"]))

    abs_fails_hard = not correct(keep_absolute(hard["scores"], t), hard["relevant"])
    print("  absolute threshold is WRONG for the low-scoring query = %s (kept %d, truth %d)" % (abs_fails_hard, len(keep_absolute(hard["scores"], t)), hard["relevant"]))
```

```text filename=scorecalib.py --check
SELF-TEST — the absolute threshold matches the truth for the high-scoring query but not the low-scoring one, while the relative threshold matches both
----------------------------------------------------------------------------------------------------------------
  absolute threshold is correct for the high-scoring query = True (kept 2, truth 2)
  absolute threshold is WRONG for the low-scoring query = True (kept 0, truth 1)
  relative threshold is correct for both queries = True (easy True, hard True)
  the same absolute cutoff works for one query and not the other (not transferable) = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  abs_ok_easy=True  abs_fails_hard=True  rel_ok_easy=True  rel_ok_hard=True  not_transferable=True
```

**not_transferable is the whole claim: one cutoff correct for one query and wrong for another proves the score is not comparable across queries, so the threshold cannot be a global constant.**

## Definition of done

You can explain why similarity scores are calibrated within a query but not across queries — the embedding geometry differs per query, so a high-scoring query and a low-scoring query put their relevant matches at different absolute levels.

You can describe both failure directions of an absolute threshold: admitting marginal candidates for a high-scoring query and rejecting the correct answer for a low-scoring one.

You can state the fix — a per-query relative cutoff (a fraction of the top score, or the gap between top scores) — and why it judges each candidate against the right scale.

You can distinguish this from simply adding an abstention threshold: the companion idea is whether to have a cutoff, and this module is that its value cannot be one global constant.

## Boss fight

Your RAG system uses "include chunks with cosine ≥ 0.75, else answer 'I don't know'." It works well in testing, but in production it says "I don't know" to many answerable questions — disproportionately the more specialized, technical ones — while giving confident answers full of marginal chunks to broad, common questions.

First: explain the pattern from this module. Why do the specialized questions get "I don't know" and the broad ones get padded with marginal chunks, from the same 0.75 cutoff? What is different about the score distributions of the two kinds of query?

Then: switch to a per-query rule. Contrast two options — keep chunks above a fraction of the query's top score, versus keep chunks whose score is within a small gap of the top — and say what each does well and badly (hint: consider a query with one clearly-best chunk versus one with several near-tied good chunks).

Finally: even a per-query cutoff cannot tell a genuinely unanswerable query (nothing relevant exists) from an answerable one, because the top score is always "the top" relative to itself. Explain why you still need some absolute signal to decide abstention, and how you would combine it with the relative cutoff — a relative rule for how many chunks to keep, and an absolute floor for whether to answer at all.

## External resources

Writing on calibrating retrieval scores and thresholds (for example discussions of score normalization and abstention in RAG pipelines) makes the same point: raw similarity scores are not comparable across queries, so relevance and abstention decisions need per-query calibration.

The literature on query performance prediction studies exactly which signals of a query's score distribution — the top score, the gap to the next, the variance — indicate a confident versus a diffuse retrieval, which is the machinery behind the relative cutoffs this module uses.
