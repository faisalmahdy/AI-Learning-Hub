---
id: retrieval-basic-01
title: Did the retriever find the right note? Measure rank, not vibes
topic: context-and-retrieval
level: basic
status: ready
time: 6-8h
summary: Build a bag-of-words retriever over eleven notes and score it against a gold answer per query — a raw dot-product scorer lands the right note first only 1 of 6 times while length-normalised cosine gets 6 of 6, yet at hit@3 both read a perfect 6/6, so the lenient metric hides a retriever that buries the answer under one long junk-drawer page.
eli5: Ask for the note about your gym day and a naive search hands you the fat everything-page because it says "gym" a lot. Divide by length and you get the short right note — and you only catch the difference by checking which one comes first, not whether it showed up at all.
---

## Why this module

This is the first module of the context-and-retrieval track, and it starts where the track has to: measurement. The labs already run retrieval — a hybrid wiki ranker in the agent, a 2,227-line tiered ranker with a 150-case benchmark in the memory service — and hold a strong opinion that a compiled wiki beats vector RAG. The scan's verdict on that opinion is blunt: it is "currently unearned because it was never tested." Every later module here — chunking ablations, the wiki-versus-RAG head-to-head — is a comparison, and a comparison is only as honest as the number you compare with. So before we retrieve better, we learn to tell whether one retriever is actually better than another.

The trap this module exists to kill is the most natural instinct in retrieval: judging it by whether the right thing showed up at all. A retriever that returns the correct note somewhere in its top five *feels* like it works. But "somewhere in the top five" is a metric that cannot see rank, and rank is the whole game — the model reads the top result first and often only. A retriever that reliably ranks the answer third is a retriever that fails, and the lenient metric will call it perfect.

You need nothing but Python 3 and the standard library. Everything runs offline against an eleven-note fixture, in well under a second, `$0.00`, one sitting. By the end you can build a real retriever and, more importantly, catch it lying.

Here is where we land, both scorers measured against the same six queries:

```
# modules/context-and-retrieval/code/retrieval-basic-01/ — COMPLETE, run from that directory
$ python3 retrieve.py --measure

RETRIEVAL QUALITY — raw dot-product vs length-normalised cosine
------------------------------------------------------------------
  scorer                 hit@1   hit@3   MRR
  raw dot-product        1/6     6/6    0.583
  cosine (length-fair)   6/6     6/6    1.000
```

run: 2026-08-25 · retriever is deterministic; corpus is a fixture · n=6 queries, 11 docs · `python3 retrieve.py --measure`

Look at the `hit@3` column: both scorers score a flat 6 of 6. By that metric they are identical, both perfect. Now look at `hit@1`: the raw scorer puts the right note first exactly once in six tries; cosine does it every time. The two retrievers are worlds apart, and the lenient metric erased the difference. This module is about that gap — where it comes from, and the metric that refuses to hide it.

## Concepts

Named here so you can find them again; each is built below.

- **Retriever** — given a query, score every document and return the top few. The first half of RAG.
- **Bag-of-words vector** — a document as `{term: count}`, order thrown away.
- **Raw dot product** — score by shared-term counts. Rewards length. The bug.
- **Cosine similarity** — the dot product divided by both vector lengths; score by direction, not magnitude.
- **hit@k** — did the gold note land in the top k? Lenient as k grows.
- **MRR** — mean reciprocal rank: `1/rank` of the gold note, averaged. Rank-aware.

## Worked example

Source: faisalmahdy/agent — `agent/memory/retrieval.py`, the hybrid wiki ranker. Its `hash_embed` builds a bag-of-words vector and then L2-normalises it (`norm = sqrt(sum(v*v))`, then divide), and its `cosine` assumes unit vectors. That one normalising line is the subject of this whole module: we remove it, watch retrieval break, and measure exactly what it was buying.

Script and fixture: `modules/context-and-retrieval/code/retrieval-basic-01/` — `retrieve.py`, and `corpus.json`, eleven notes from a personal assistant's memory. Every command runs from there.

### The corpus: ten honest notes and one junk drawer

The notes are short and on-topic — a note about the gym schedule, one about the dentist, one about coffee — except for `d00`, a long "weekly log" that mentions a little of everything: coffee most mornings, the gym most days, a flight, a bill, mom.

```
# $ python3 retrieve.py --corpus
#   d00   76 tokens  weekly log monday coffee then gym legs d  <-- long junk-drawer page
#   d01   20 tokens  coffee: I take it black, no sugar. a lig
#   d02   15 tokens  gym schedule: monday is leg day, wednesd
#   ...
#   6 queries, each with one gold note it should return at rank 1.
```

run: 2026-08-25 · fixture · 11 docs · `python3 retrieve.py --corpus`

Each query has one **gold** note that truly answers it — "when is my gym leg day" wants `d02`, the gym schedule, not the log that happens to say "gym" five times. That gold label is what makes measurement possible: without a known right answer, you are back to vibes.

### Two ways to score, and why one has a bias

A retriever turns query and document into bag-of-words vectors and scores each pair. The simplest score is the raw dot product — sum, over the query's terms, of how many times each appears in the document.

```
# retrieve.py:52-55 — COMPLETE (score by shared-term counts)
def score_raw(q_vec, d_vec):
    """Raw dot product of term-frequency vectors. No length normalisation, so a
    long document with many words scores high just for being long."""
    return sum(w * d_vec.get(t, 0) for t, w in q_vec.items())
```

This has a bias baked in, and it is worth predicting before you see it. The weekly log says "gym" five times because the owner goes to the gym five days a week — not because it is the gym *schedule*. A raw count rewards that repetition. So ask yourself: for "when is my gym leg day", will the raw scorer return the fifteen-token schedule, or the seventy-six-token log? Write it down.

```
# $ python3 retrieve.py --search "when is my gym leg day"
#   raw dot-product        d00=8.000  d02=8.000  d03=1.000  d05=1.000
#   cosine (length-fair)   d02=0.596  d00=0.242  d10=0.102  d03=0.099
```

run: 2026-08-25 · fixture · `python3 retrieve.py --search "..."`

The raw scorer ties the log and the schedule at 8.000 and breaks the tie toward `d00`, the log — the wrong note, first, because length let it accumulate matches. The fix is to divide the dot product by both vectors' lengths, which turns "how many words match" into "how aligned are the two in direction" — cosine similarity.

```
# retrieve.py:58-64 — COMPLETE (divide out length: direction, not magnitude)
def score_cosine(q_vec, d_vec):
    """Cosine similarity: the dot product divided by both vector lengths, so score
    is direction (what the doc is about), not magnitude (how long it is)."""
    dot = sum(w * d_vec.get(t, 0) for t, w in q_vec.items())
    nq = sqrt(sum(w * w for w in q_vec.values()))
    nd = sqrt(sum(w * w for w in d_vec.values()))
    return dot / (nq * nd) if nq and nd else 0.0
```

Under cosine the schedule wins, 0.596 to the log's 0.242: `d02` is *about* the gym leg day, the log merely mentions it. That division is the exact line the labs' `hash_embed` runs on every vector, and now you can see what it defends against.

<svg viewBox="0 0 700 210" role="img" aria-label="Two panels. Left, raw dot product: a long junk-drawer document vector and a short on-topic vector, with the long one scoring higher because length inflates its shared-term count. Right, cosine: both vectors divided by their length, so the short on-topic document now scores higher by direction.">
  <g font-family="var(--mono)" font-size="10">
    <text x="40" y="24" fill="var(--s2)">raw dot product — length wins</text>
    <text x="400" y="24" fill="var(--s1)">cosine — direction wins</text>
    <line x1="360" y1="36" x2="360" y2="200" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"></line>
    <rect x="40" y="50" width="230" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect>
    <rect x="40" y="50" width="180" height="26" rx="4" fill="var(--s2)"></rect>
    <text x="278" y="68" fill="var(--muted)">d00 log = 8.0</text>
    <rect x="40" y="92" width="230" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect>
    <rect x="40" y="92" width="180" height="26" rx="4" fill="var(--muted)"></rect>
    <text x="278" y="110" fill="var(--muted)">d02 note = 8.0</text>
    <text x="40" y="150" fill="var(--muted)" font-size="9">the long log ties on raw count — and wins the tie</text>
    <rect x="400" y="50" width="230" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect>
    <rect x="400" y="50" width="66" height="26" rx="4" fill="var(--muted)"></rect>
    <text x="474" y="68" fill="var(--muted)">d00 log = 0.24</text>
    <rect x="400" y="92" width="230" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect>
    <rect x="400" y="92" width="162" height="26" rx="4" fill="var(--s1)"></rect>
    <text x="570" y="110" fill="var(--muted)">d02 note = 0.60</text>
    <text x="400" y="150" fill="var(--muted)" font-size="9">divide by length: the on-topic note pulls ahead</text>
  </g>
</svg>
^ Same query, same two documents, two scores. Raw dot product ties them on shared-term count and hands the tie to the longer page; cosine divides out length and the short on-topic note wins. The only difference is the division.

### Measuring it: rank is the metric

One search is an anecdote. To judge a retriever you run every query, find where the gold note landed, and summarise. `hit@k` asks a yes/no question — did the gold note make the top k — and `MRR` asks a sharper one: how high, averaging `1/rank` so rank 1 scores 1.0, rank 2 scores 0.5, rank 3 scores 0.33.

```
# retrieve.py:77-94 — COMPLETE (find the gold's rank, then hit@k and MRR)
def rank_of_gold(ranked, gold):
    """1-based position of the gold doc in the ranking (len+1 if never returned)."""
    for i, (did, _) in enumerate(ranked, 1):
        if did == gold:
            return i
    return len(ranked) + 1


def measure(docs, queries, score):
    hit1 = hitk = 0
    rr_sum = 0.0
    for item in queries:
        r = rank_of_gold(rank(docs, item["q"], score), item["gold"])
        hit1 += 1 if r == 1 else 0
        hitk += 1 if r <= TOP_MEASURE else 0
        rr_sum += 1.0 / r
    n = len(queries)
    return hit1, hitk, rr_sum / n
```

Run it against both scorers and the cold-open table is what comes back: raw at `hit@1` 1/6, cosine at 6/6, and MRR 0.583 versus 1.000. But the row that teaches the lesson is `hit@3`, where both read 6/6. The raw scorer does get the gold note into the top three every time — it just buries it below the junk drawer. Pick `k` generously and you certify a broken retriever as perfect.

<svg viewBox="0 0 700 190" role="img" aria-label="Two metrics compared. At hit@3 both the raw and cosine scorers show 6 of 6, a tie. At hit@1 the raw scorer shows 1 of 6 and cosine shows 6 of 6, a wide gap the hit@3 view hid.">
  <g font-family="var(--mono)" font-size="10">
    <text x="150" y="24" fill="var(--muted)">the same two retrievers under a lenient vs a rank-aware metric</text>
    <text x="20" y="70" fill="var(--ink)">hit@3</text>
    <rect x="120" y="58" width="230" height="18" rx="3" fill="var(--s2)"></rect><text x="356" y="72" fill="var(--muted)">raw 6/6</text>
    <rect x="120" y="82" width="230" height="18" rx="3" fill="var(--s1)"></rect><text x="356" y="96" fill="var(--muted)">cosine 6/6</text>
    <text x="470" y="82" fill="var(--muted)" font-size="9">"both perfect"</text>
    <text x="20" y="140" fill="var(--ink)">hit@1</text>
    <rect x="120" y="128" width="38" height="18" rx="3" fill="var(--s2)"></rect><text x="164" y="142" fill="var(--muted)">raw 1/6</text>
    <rect x="120" y="152" width="230" height="18" rx="3" fill="var(--s1)"></rect><text x="356" y="166" fill="var(--muted)">cosine 6/6</text>
    <text x="470" y="152" fill="var(--muted)" font-size="9">the truth: raw buries the answer</text>
    <line x1="118" y1="50" x2="118" y2="176" stroke="var(--grid)" stroke-width="1"></line>
  </g>
</svg>
^ One pair of retrievers, two metrics. `hit@3` calls them equal; `hit@1` shows one finds the answer first every time and the other almost never. The metric you pick decides whether you can see the bug.

**A retriever's job is not to include the answer, it is to rank it first — so measure rank, and a metric that cannot see rank cannot see failure.**

### Prove it in one run

The self-test checks the claims this rests on: cosine of a vector with itself is exactly 1 and of two disjoint texts exactly 0, the raw scorer really does top the gym query with the log while cosine tops it with the schedule, and cosine's `hit@1` beats raw's while `hit@3` hides the gap.

```
# $ python3 retrieve.py --check
#   cosine(x,x) = 1.000000 (==1), cosine(disjoint) = 0.000000 (==0)
#   query 'when is my gym leg day': raw top = d00, cosine top = d02
#   hit@1  raw=1 cosine=6 (cosine wins)   hit@3 raw=6 cosine=6 (tie hides it)
#   SELF-TEST PASS  bounds=True  bias_shows=True  lenient_hides=True  deterministic=True
```

run: 2026-08-25 · deterministic · n=6 queries · `python3 retrieve.py --check`

One honest fence: cosine scoring a perfect 1.000 MRR here is an artifact of a clean eleven-note fixture with well-separated topics. Real corpora do not split so kindly — near-duplicate notes, shared vocabulary, and long documents that are *genuinely* relevant are exactly what the chunking and reranking modules later in this track exist to handle. The lesson that transfers is not "cosine is perfect"; it is "rank-aware measurement is how you would ever know."

## Build

The pipeline in one paragraph: turn each query and document into a bag-of-words vector; score every document with length-normalised cosine, not a raw count; return the top few; and to judge the retriever, label a gold answer per query and report `hit@1` and MRR, never a lenient `hit@k` alone.

Now point it at your own notes. The one dial is `corpus.json`: replace the eleven documents with your own, and write a handful of queries each tagged with the note id that truly answers it. Everything in `retrieve.py` recomputes. Your number to beat is not `hit@5` — that is the metric that flatters. It is **MRR, or `hit@1`**: the fraction of queries whose answer you rank first. Add a long, off-topic note that repeats a common word and confirm your `hit@1` notices while `hit@5` shrugs. Bring back two numbers — your raw scorer's `hit@1` and your cosine scorer's — and the gap between them is the length bias, measured. Good luck.

## Definition of done

- [ ] `corpus.json` of your own notes, each query tagged with the gold note id that answers it
- [ ] A retriever that scores with length-normalised cosine and returns a ranked top-k
- [ ] The raw dot-product scorer kept alongside it, so the length bias is visible, not asserted
- [ ] `hit@1`, `hit@k`, and MRR computed against the gold labels for both scorers
- [ ] `python3 retrieve.py --check` printing SELF-TEST PASS: cosine bounds, the bias shows, the lenient metric hides it, deterministic
- [ ] The two numbers recorded: raw `hit@1` vs cosine `hit@1` — the length bias, measured
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A long note that mentions "gym" five times out-ranks the actual gym schedule under one scorer. Name the scorer, name the bias, and give the one operation that fixes it.
2. Two retrievers both score 6/6 at hit@3, but one is far worse. Give the metric that reveals it and explain why hit@3 could not.
3. Write the cosine score in words as a ratio, and say which part of it — numerator or denominator — is what kills the length bias.
4. The gold note for a query lands at rank 3. State its contribution to hit@1, to hit@3, and to MRR.
5. Your own run printed a raw hit@1 and a cosine hit@1. What were they, and what does the difference between them measure?

## External resources

- faisalmahdy/agent — `agent/memory/retrieval.py` — my summary: the hybrid wiki ranker whose `hash_embed` L2-normalises every vector and whose `cosine` assumes unit vectors; read it to see the normalising line this module removes, and note it blends relevance with recency and centrality — signals a later module will add on top of the retrieval this one measures.
- Manning, Raghavan & Schütze, *Introduction to Information Retrieval*, ch. 6 (scoring, term weighting, the vector space model) — https://nlp.stanford.edu/IR-book/ — my summary: the standard derivation of cosine and length normalisation, and where tf-idf comes from; read it for why raw term counts mislead, and note our bag-of-words score is the un-weighted special case tf-idf improves on.
- Anthropic, *Contextual Retrieval* — https://www.anthropic.com/news/contextual-retrieval — my summary: a practical account of measuring retrieval failure rate and driving it down with better chunk context and reranking; read it for how the `hit@k`-versus-rank distinction here scales to a real RAG system, and as a preview of this track's later modules.
