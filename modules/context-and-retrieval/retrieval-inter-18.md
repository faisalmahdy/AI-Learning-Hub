---
id: retrieval-inter-18
title: Saturate the term frequency — or a keyword-stuffed document buries the relevant one
topic: context-and-retrieval
level: intermediate
status: ready
time: 19 min
summary: A lexical scorer weights a document by how often the query term appears — its term frequency. The naive rule uses that count directly, so twice the occurrences is twice the score, unbounded. That rewards repetition without limit: a page repeating "mortgage" fifty times scores fifty times a page that uses it once, even when the second page is the one that answers the question. Keyword stuffing is exactly this weakness. BM25 saturates instead — score = tf × (k1+1) / (tf+k1) — so the first occurrence is worth the most, each additional one adds less, and the score approaches a ceiling of k1+1 no matter how high tf climbs. On k1 = 1.2 (ceiling 2.2), linear scoring gives tf 3 and tf 50 the scores 3 and 50, a 16.7× gap; BM25 gives 1.57 and 2.15, a 1.37× gap — stuffing neutralized.
eli5: The first time a page mentions your word, that is real news — the page is about it. The tenth time tells you a little more, the fiftieth almost nothing. A naive search engine keeps rewarding every repeat equally, so a page that spams a word wins. A smarter one gives big credit for the first mention and less and less for each repeat, so spamming stops helping.
---

## Why this module

The most obvious way to score a document for a keyword — count the keyword — is the one that lets spam win.

Lexical retrieval rests on term frequency: a document that uses the query term more is, all else equal, more about it. The naive scorer takes that literally and uses the raw count, so the score grows linearly and without bound. That is a gift to keyword stuffing, the oldest search-spam trick there is: repeat the term fifty times and you outscore a genuinely relevant page fifty to one, regardless of whether your page answers anything. The signal the scorer trusts — more is better — has no idea that the tenth occurrence of a word tells you far less than the first.

**Raw term frequency is unbounded, so it rewards repetition without limit — and repetition is the cheapest thing to fake.**

BM25 fixes this by saturating the term frequency: the first occurrence counts the most, each additional one adds less, and the score approaches a ceiling it can never exceed. Establishing that a document uses a term is worth a lot; hammering it is worth almost nothing. This module scores a range of term frequencies both ways and shows a stuffed document's runaway advantage collapse.

## Concepts

The **term frequency** (tf) is how many times the query term appears in a document. The **linear scorer** uses tf directly — score equals tf — so it is a straight line with no ceiling.

**BM25's saturation** replaces tf with `tf × (k1 + 1) / (tf + k1)`. As tf grows, the ratio approaches `k1 + 1`, a hard **ceiling** the score never crosses. The curve rises steeply at first and flattens: the marginal value of each extra occurrence shrinks toward zero.

The parameter **k1** controls how fast the curve saturates. A small k1 flattens almost immediately (presence matters, count barely does); a large k1 keeps the curve closer to linear for longer. Typical values are around 1.2 to 2.0.

The mechanism is diminishing returns. The jump from zero occurrences to one is the largest — it establishes the term is present at all. From one to three is a real but smaller gain; from ten to fifty is nearly flat, because by then the term's presence is thoroughly established and more repetition is noise. Linear scoring treats all these jumps as equal; BM25 does not.

**Saturation encodes a truth linear tf ignores: the information in a term's presence is mostly in the first few occurrences, not the fiftieth.**

The value of each successive occurrence is a shrinking staircase — tall first step, then shorter and shorter treads toward the ceiling.

<svg role="img" aria-label="A staircase where the first step is tall and each next step is shorter, approaching a ceiling" viewBox="0 0 300 120" width="300" height="120">
  <line x1="30" y1="15" x2="285" y2="15" stroke="var(--grid)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="240" y="12" fill="var(--muted)" font-size="8">ceiling k1+1</text>
  <line x1="30" y1="100" x2="285" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <polyline points="30,100 70,100 70,55 120,55 120,35 180,35 180,25 250,25 250,20 285,20" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="40" y="95" fill="var(--muted)" font-size="8">1st: big</text>
  <text x="128" y="48" fill="var(--muted)" font-size="8">3rd: smaller</text>
  <text x="200" y="38" fill="var(--muted)" font-size="8">10th+: tiny</text>
  <text x="60" y="115" fill="var(--muted)" font-size="8">each extra occurrence of the term →</text>
</svg>
^ Each occurrence adds a shorter step than the last, so the score climbs fast at first and then presses flat against the ceiling — the geometry of diminishing returns.

The payoff is spam resistance. Once the stuffed document's tf advantage is capped, its score edge over a relevant document shrinks to almost nothing, and the ranking is decided by other signals — additional query terms, length normalization, real relevance — instead of by who repeated the word most.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/retrieval-inter-18/bm25.py

The fixture is a k1 and a set of term frequencies to score.

```json filename=modules/context-and-retrieval/code/retrieval-inter-18/bm25.json:1-8 COMPLETE
{
  "_meta": "A single query term and how a lexical scorer weights a document by how many times that term appears (its term frequency, tf). A naive scorer uses tf directly -- linear, unbounded. BM25 saturates tf with tf*(k1+1)/(tf+k1), so the score approaches a ceiling of k1+1 as tf grows. k1 controls how fast it saturates. tf_values are the counts to score; relevant_tf and stuffed_tf are a genuinely-relevant doc vs a keyword-stuffed one.",
  "k1": 1.2,
  "tf_values": [0, 1, 3, 10, 50],
  "relevant_tf": 3,
  "stuffed_tf": 50
}
```

The two scorers are two lines. Linear returns tf; BM25 saturates it toward the ceiling k1 + 1.

```python filename=modules/context-and-retrieval/code/retrieval-inter-18/bm25.py:41-52 COMPLETE
def linear(tf):
    """The naive scorer: term frequency used directly, unbounded."""
    return float(tf)


def bm25(tf, k1):
    """BM25's saturating term frequency: approaches the ceiling k1+1 as tf grows."""
    return tf * (k1 + 1) / (tf + k1)


def ceiling(k1):
    return k1 + 1.0
```

The scores view walks the term frequencies, printing both scorers and the marginal BM25 gain of each step.

```python filename=modules/context-and-retrieval/code/retrieval-inter-18/bm25.py:58-69 COMPLETE
    k1 = data["k1"]
    print("SCORES — linear vs BM25 term-frequency weight (k1 %.1f, ceiling %.1f)" % (k1, ceiling(k1)))
    print("-" * 64)
    print("  tf     linear    BM25    marginal BM25 gain")
    prev = None
    for tf in data["tf_values"]:
        b = bm25(tf, k1)
        marg = "" if prev is None else "+%.3f" % (b - prev)
        print("  %-5d  %6.1f   %5.3f   %s" % (tf, linear(tf), b, marg))
        prev = b
    print("-" * 64)
    print("  linear keeps climbing; BM25 flattens toward %.1f as tf grows." % ceiling(k1))
```

Run `--scores` and read the two columns and the marginal gain.

```text filename=--scores
SCORES — linear vs BM25 term-frequency weight (k1 1.2, ceiling 2.2)
----------------------------------------------------------------
  tf     linear    BM25    marginal BM25 gain
  0         0.0   0.000   
  1         1.0   1.000   +1.000
  3         3.0   1.571   +0.571
  10       10.0   1.964   +0.393
  50       50.0   2.148   +0.184
----------------------------------------------------------------
  linear keeps climbing; BM25 flattens toward 2.2 as tf grows.
```

The linear column runs away — 1, 3, 10, 50 — while the BM25 column crawls toward 2.2 and stops: 1.000, 1.571, 1.964, 2.148. The marginal-gain column is the story. The first occurrence is worth a full 1.000; the jump from 10 to 50 — forty more occurrences — buys only 0.184. Under linear scoring those forty occurrences were worth 40 points.

<svg role="img" aria-label="Linear tf rises as a straight line while BM25 saturates and flattens toward a ceiling of 2.2" viewBox="0 0 300 150" width="300" height="150">
  <line x1="35" y1="15" x2="35" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <line x1="35" y1="120" x2="285" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <line x1="35" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="240" y="92" fill="var(--muted)" font-size="8">ceiling 2.2</text>
  <polyline points="40,118 90,113 150,98 285,18" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="250" y="30" fill="var(--s1)" font-size="8">linear</text>
  <polyline points="40,120 50,102 90,103 150,100 285,96" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="150" y="90" fill="var(--s2)" font-size="8">BM25 (saturates)</text>
  <text x="120" y="138" fill="var(--muted)" font-size="8">term frequency →</text>
</svg>
^ Linear tf is a straight line to the sky; BM25 rises fast then flattens against the ceiling k1 + 1 — the two agree at the first occurrence and diverge forever after.

## Build

What does that saturation do to a stuffing attack? Run `--stuffing`.

```text filename=--stuffing
STUFFING — a relevant doc (tf 3) vs a keyword-stuffed doc (tf 50)
----------------------------------------------------------------
  linear:  relevant 3.0   stuffed 50.0   stuffed/relevant 16.7x
  BM25:    relevant 1.571  stuffed 2.148  stuffed/relevant 1.37x
----------------------------------------------------------------
  linear lets the stuffed doc dominate; BM25 shrinks its edge to almost nothing.
```

Under linear scoring, the stuffed document beats the relevant one 16.7 to 1 — it wins on repetition alone, no contest. Under BM25 the same two documents are 1.37 to 1: the stuffed doc still edges ahead on tf, but by a margin small enough that any other signal — a second query term the relevant doc matches, a length penalty on the padded doc — flips the ranking. Stuffing went from decisive to negligible.

<svg role="img" aria-label="Stuffed over relevant ratio: 16.7x under linear scoring, 1.37x under BM25" viewBox="0 0 300 110" width="300" height="110">
  <line x1="70" y1="12" x2="70" y2="85" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="85" x2="285" y2="85" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="25" width="200" height="16" fill="var(--s1)"/>
  <text x="10" y="37" fill="var(--muted)" font-size="9">linear</text>
  <text x="200" y="37" fill="var(--panel)" font-size="9">16.7x</text>
  <rect x="70" y="55" width="26" height="16" fill="var(--s2)"/>
  <text x="10" y="67" fill="var(--muted)" font-size="9">BM25</text>
  <text x="100" y="67" fill="var(--muted)" font-size="9">1.37x</text>
  <text x="70" y="102" fill="var(--muted)" font-size="8">stuffed-doc advantage: decisive under linear, negligible under BM25</text>
</svg>
^ The stuffed document's advantage over the relevant one: a commanding 16.7× under raw tf, shrunk to a decidable 1.37× once tf is saturated.

## Definition of done

The self-test pins the saturation: linear is unbounded, every BM25 score stays under the ceiling, each extra occurrence adds less, the first occurrence is the biggest jump, and the stuffing advantage is shrunk from over 10× to under 2×.

```python filename=modules/context-and-retrieval/code/retrieval-inter-18/bm25.py:88-101 COMPLETE
    linear_unbounded = linear(50) == 50.0 and linear(50) > linear(10) * 4
    print("  linear scoring grows without limit = %s (tf 50 -> %.1f)" % (linear_unbounded, linear(50)))

    bm25_below_ceiling = all(bm25(tf, k1) < cap for tf in [1, 3, 10, 50])
    print("  every BM25 score stays under the ceiling %.1f = %s (tf 50 -> %.3f)" % (cap, bm25_below_ceiling, bm25(50, k1)))

    marginal_diminishes = (bm25(3, k1) - bm25(1, k1)) > (bm25(50, k1) - bm25(10, k1))
    print("  each extra occurrence adds less = %s (1->3 gains %.3f, 10->50 gains %.3f)"
          % (marginal_diminishes, bm25(3, k1) - bm25(1, k1), bm25(50, k1) - bm25(10, k1)))

    first_occurrence_worth_most = (bm25(1, k1) - bm25(0, k1)) > (bm25(2, k1) - bm25(1, k1))
    print("  the first occurrence is the biggest jump = %s (0->1 gains %.3f)" % (first_occurrence_worth_most, bm25(1, k1) - bm25(0, k1)))

    stuffing_neutralized = (linear(50) / linear(3)) > 10 and (bm25(50, k1) / bm25(3, k1)) < 2
    print("  BM25 shrinks the stuffing advantage = %s (linear %.1fx -> BM25 %.2fx)"
          % (stuffing_neutralized, linear(50) / linear(3), bm25(50, k1) / bm25(3, k1)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — linear tf is unbounded; BM25 saturates toward a ceiling and diminishes each extra occurrence
--------------------------------------------------------------------------------------------------------
  linear scoring grows without limit = True (tf 50 -> 50.0)
  every BM25 score stays under the ceiling 2.2 = True (tf 50 -> 2.148)
  each extra occurrence adds less = True (1->3 gains 0.571, 10->50 gains 0.184)
  the first occurrence is the biggest jump = True (0->1 gains 1.000)
  BM25 shrinks the stuffing advantage = True (linear 16.7x -> BM25 1.37x)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  linear_unbounded=True  bm25_below_ceiling=True  marginal_diminishes=True  first_occurrence_worth_most=True  stuffing_neutralized=True
```

**Done means the diminishing returns are provable: the 0→1 jump is worth 1.000 while forty more occurrences (10→50) add only 0.184, and the stuffing edge falls from 16.7× to 1.37×.**

## Boss fight

BM25 saturated the stuffing here. Predict what still lets a long spam document win, even with saturation. It is tempting to think saturation alone solves keyword stuffing.

Saturation caps repetition, but a long document has more room to match many different query terms and to accumulate tf across them, so length is the remaining lever — which is why full BM25 adds a length normalization term, not just saturation. The complete denominator is `tf + k1 × (1 − b + b × dl/avgdl)`, where `b` scales a penalty for documents longer than average. Without it, a document can dodge the tf ceiling by being enormous. Saturation and length normalization are two halves of the same defense: one stops repeating a term, the other stops padding the document.

The mirror-image mistake is setting k1 too low in pursuit of spam resistance. Push k1 toward zero and the curve saturates almost instantly — one occurrence scores nearly the same as twenty — and now you have thrown away real signal, treating a document that genuinely discusses the term at length the same as one that mentions it once. The parameter is a balance, and the standard 1.2–2.0 range is where it sits.

```python filename=modules/context-and-retrieval/code/retrieval-inter-18/bm25.py:46-48 COMPLETE
def bm25(tf, k1):
    """BM25's saturating term frequency: approaches the ceiling k1+1 as tf grows."""
    return tf * (k1 + 1) / (tf + k1)
```

**Saturate the term frequency and normalize by length together: the first stops a term from being repeated into dominance, the second stops a document from being padded into it.**

## External resources

Robertson and Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond" (2009) — the definitive treatment of the saturation function, the k1 and b parameters, and the length normalization in the boss fight.

The Elasticsearch and Lucene "Practical BM25" documentation — how the formula is implemented in a production search engine, with the default k1 and b and worked scoring examples.

Manning, Raghavan, and Schütze, "Introduction to Information Retrieval", the term-weighting chapter — why raw tf is a poor weight and the log/saturation alternatives that predate and motivate BM25.
