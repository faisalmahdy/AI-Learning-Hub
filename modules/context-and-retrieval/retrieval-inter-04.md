---
id: retrieval-inter-04
title: The three-signal memory ranker — relevance alone serves last year's answer
topic: context-and-retrieval
level: intermediate
status: ready
time: 8-10h
summary: A memory where facts change cannot rank on relevance alone — an old note and the note that superseded it match a query equally, so pure relevance serves the stale one 0 of 3 times. Add an exponential recency decay and the fresh note wins 3 of 3; add an importance signal on a raw backlink count and a hub page with 20 links drowns every query back to 0 of 3; normalise importance by the busiest page, exactly as the labs' ranker does, and the blend holds at 3 of 3 — because three signals only compose when they share a scale.
eli5: Ask your desk for the note about your phone number and the biggest, wordiest old note answers, because it looks most like the question. Weight fresh notes higher and the new one wins — until you also count how many notes link to each, on a raw tally, and the index page that links to everything buries the answer. Divide that tally by the busiest page and the balance comes back.
---

## Why this module

This is the track's synthesis module, and it composes every module before it. You built a retriever and learned to measure it; you chunked; you fused a wiki and a dense retriever; you budgeted the result into a window. All of that assumed the corpus holds still. Real memory does not. Facts change — a phone number, an address, a plan — and the old note and the note that replaced it both sit in the store, both matching the query. Rank on relevance alone and you serve whichever is *wordier*, which is often the old one, so your agent confidently answers with a fact that was true last year. The labs' wiki ranker names the fix in its own docstring: the score blends "three signals the research keeps returning to" — relevance, recency, and importance — and this module builds that blend from scratch and breaks it on purpose.

The gap the scan records is exact: the labs' retrieval "blends relevance + recency + centrality," but the track had never shown *why each term is load-bearing* or how they fail. This module does. You will watch relevance serve stale answers, recency rescue them, and then a third signal — importance — destroy the whole ranker when it is added on the wrong scale, before one normalising division mirrored from the real code puts it right. The deepest lesson is the same one the wiki-vs-RAG module taught about fusion, now sharper: signals only compose when they share a scale, and a signal ten times larger than its neighbours is not a stronger vote, it is a dictator.

You need every prior module in this track, especially `retrieval-basic-01`'s cosine. Everything runs offline against a seven-note fixture with hand-set ages and backlink counts standing in for file timestamps and a real link graph, stdlib Python 3, `$0.00`. Here is the whole arc in one table — four rankers, each adding one signal to the last:

```
# modules/context-and-retrieval/code/retrieval-inter-04/ — COMPLETE, run from that directory
$ python3 hybrid.py --measure

FRESH-ANSWER ACCURACY — top result is the current, correct note
----------------------------------------------------------------------
  relevance only             0/3
  + recency                  3/3
  + raw importance (bug)     0/3
  + norm importance (fix)    3/3
```

run: 2026-08-25 · deterministic; ages and backlinks are a fixture · half-life 30d, weights 0.6/0.2/0.2, n=3 queries · `python3 hybrid.py --measure`

Read it as a staircase that falls twice. Relevance alone never surfaces the current note. Recency fixes it completely. Adding importance the obvious way knocks it back to zero. Normalising importance restores it. This module is those four rows and the single division that separates the third from the fourth.

## Concepts

Named here so you can find them again; each is built below.

- **Relevance** — cosine of query and note; how much the note is *about* the query. Built in `retrieval-basic-01`.
- **Recency** — an exponential decay on the note's age; fresh memory outweighs stale, smoothly.
- **Importance** — how central a note is, measured by backlinks; a proxy for "canonical".
- **Half-life** — the age at which recency halves. The dial on how fast memory goes stale.
- **The blend** — a weighted sum of the three signals, weights 0.6 / 0.2 / 0.2.
- **Normalisation** — dividing a signal so it lands in [0,1] like its neighbours; the line that makes importance safe. #4.

## Worked example

Source: faisalmahdy/agent — `agent/memory/retrieval.py`, the hybrid wiki ranker. Its scoring loop is the target this module rebuilds: `recency = 0.5 ** (age_days / half_life_days)`, `importance = backlinks[stem] / max_back` — "normalised by the busiest page" — and `score = w_relevance * relevance + w_recency * recency + w_importance * importance`, with defaults 0.6 / 0.2 / 0.2. Every formula below is that file's, and the planted bug is the one line — `/ max_back` — removed.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-04/` — `hybrid.py`, and `memory.json`, seven notes: an old and a new version of three facts, plus one hub index page. Every command runs from there.

### The frame: a desk where the newest correction is buried

Picture memory as a desk piled with notes. You ask for your phone number. Three things could decide which note surfaces: which note *looks* most like "phone number" (relevance), which was written *most recently* (recency), and which is referenced by the most other notes (importance). A pure-relevance desk hands you the note whose words match best — and the old note that says only "phone number" matches the bare query more tightly than the new one that says "phone number now a new cell line ending 4231", because the update *diluted* the exact phrase with the very information that makes it correct. So the tidiest, most on-topic note is the wrong one, and relevance cannot tell.

Recency is the signal that breaks that tie: the new note is days old, the stale one is a year old, and a decay curve turns that age gap into a score gap. But a third signal is waiting to cause trouble. Importance — how many notes link to a page — is a real signal (a canonical page everyone references should rank up), but it lives on a different scale from the others, and if you add it raw, the one page that everything links to swamps the vote. The whole back half of this module is that scale collision.

### Relevance can't tell the fresh note from the stale one

Look at the raw signals for one query. The old and new notes are close on relevance; everything else separates them.

```
# $ python3 hybrid.py --signals "what is my gym membership plan"
#   doc            relevance  recency  imp(norm)  age(d)  backlinks
#   gym_old        0.707      0.000    0.100       420    2
#   gym_new        0.548      0.831    0.100         8    2
#   index_hub      0.236      0.062    1.000       120    20
```

run: 2026-08-25 · fixture · `python3 hybrid.py --signals "..."`

The stale `gym_old` out-relevances the correct `gym_new`, 0.707 to 0.548, purely because it is the terser match. On relevance alone it wins, and the ranker serves a membership plan the owner cancelled. Across all three facts, relevance-only scores 0 of 3 — it is *systematically* stale, because an updated note is almost always a longer, more diluted match than the original it replaced.

```
# hybrid.py:61-62 — COMPLETE (relevance is just the cosine from the first module)
def relevance(query, doc):
    return cosine(query, doc["text"])
```

<svg viewBox="0 0 700 170" role="img" aria-label="For the gym query, gym_old scores relevance 0.707 and gym_new 0.548, so relevance ranks the stale note first. But gym_old is 420 days old and gym_new is 8 days old, a gap relevance cannot see.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">relevance ranks the STALE note first — it is the tighter match</text>
    <text x="20" y="52" fill="var(--ink)">gym_old (420d)</text>
    <rect x="150" y="42" width="283" height="16" rx="3" fill="var(--s2)"></rect><text x="440" y="55" fill="var(--s2)">rel 0.707  <- wins</text>
    <text x="20" y="82" fill="var(--ink)">gym_new (8d)</text>
    <rect x="150" y="72" width="219" height="16" rx="3" fill="var(--s1)"></rect><text x="376" y="85" fill="var(--s1)">rel 0.548  (correct, loses)</text>
    <text x="20" y="120" fill="var(--muted)">age tells them apart cleanly — but relevance never looks at age:</text>
    <text x="150" y="145" fill="var(--s2)">stale: 420 days</text><text x="360" y="145" fill="var(--s1)">fresh: 8 days</text>
  </g>
</svg>
^ On the gym query the stale note is the tighter lexical match, so relevance ranks it first and serves a cancelled plan. The signal that separates them — a 420-day versus 8-day age — is one relevance cannot see.

### Recency turns age into a score

Recency is an exponential decay: a note edited today scores 1, one a half-life old scores 0.5, and it approaches zero as a note ages. It is the real ranker's formula, unchanged.

```
# hybrid.py:65-68 — COMPLETE (fresh scores 1, a half-life old scores 0.5)
def recency(doc):
    """Exponential decay on age: a doc edited today scores 1, one a half-life old
    scores 0.5. Fresh memory outweighs stale, smoothly."""
    return 0.5 ** (doc["age_days"] / HALF_LIFE)
```

With a 30-day half-life, the 8-day-old `gym_new` scores 0.831 and the 420-day-old `gym_old` scores essentially zero. Add recency to the blend at weight 0.2 and the fresh note's `0.6·0.548 + 0.2·0.831 = 0.495` clears the stale note's `0.6·0.707 + 0.2·0.0 = 0.424`. The correct note surfaces — on every query, 3 of 3. The exponential shape matters: a decay that is linear or a hard cutoff either never quite overtakes a strong relevance lead or throws away a note the moment it ages past a threshold; the smooth halving lets a slightly-older, slightly-more-relevant note still win, and a much-older one always lose.

<svg viewBox="0 0 700 180" role="img" aria-label="An exponential recency decay curve: score 1.0 at age 0, 0.5 at 30 days (one half-life), 0.25 at 60 days, approaching 0 by 420 days. gym_new at 8 days sits near 0.83; gym_old at 420 days sits near 0.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">recency = 0.5 ^ (age / 30d)</text>
    <line x1="60" y1="150" x2="660" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="150" stroke="var(--grid)"></line>
    <text x="30" y="45" fill="var(--muted)">1.0</text><text x="30" y="153" fill="var(--muted)">0</text>
    <path d="M 60 40 Q 130 95 200 118 T 400 145 T 660 149" fill="none" stroke="var(--s1)" stroke-width="2"></path>
    <circle cx="76" cy="55" r="4" fill="var(--s1)"></circle><text x="84" y="52" fill="var(--s1)">gym_new (8d) ~0.83</text>
    <circle cx="140" cy="95" r="3" fill="var(--muted)"></circle><text x="120" y="112" fill="var(--muted)">30d = 0.5</text>
    <circle cx="640" cy="149" r="4" fill="var(--s2)"></circle><text x="470" y="145" fill="var(--s2)">gym_old (420d) ~0</text>
    <text x="360" y="170" fill="var(--muted)">age (days) -></text>
  </g>
</svg>
^ The recency decay. A fresh note sits near the top of the curve, a year-old note near the floor; the smooth halving is what lets recency overtake a modest relevance lead without discarding a note the instant it ages.

### Strategy #3 — add importance raw. The hub eats every query.

Importance rewards a note that many others link to — a canonical page should rank up. The obvious implementation is the raw backlink count.

```
# hybrid.py:77-80 — COMPLETE (the planted bug: raw, unnormalised backlink count)
def importance_raw(doc, _max_back):
    """THE BUG: raw backlink count, unnormalised. A hub with 20 links contributes
    20 to a sum whose other terms are at most 1."""
    return float(doc["backlinks"])
```

Stop and predict. Relevance and recency both live in [0,1]. The hub index page has 20 backlinks; a real note has 2. Added at weight 0.2, the hub contributes `0.2 · 20 = 4.0` to its score, while every other term in every note's score is at most `0.2 · 1 = 0.2`. What ranks first now — for *every* query?

```
# $ python3 hybrid.py --rank "what is my gym membership plan"
#   relevance only             top = gym_old        <-- wrong
#   + recency                  top = gym_new        ok
#   + raw importance (bug)     top = index_hub      <-- wrong
#   + norm importance (fix)    top = gym_new        ok
```

run: 2026-08-25 · fixture · `python3 hybrid.py --rank "..."`

The index page — a table of contents that answers no question — wins every single query, because a raw count of 20 on a scale where everything else maxes out at 1 is not a signal, it is a veto. Accuracy collapses from 3 of 3 back to 0 of 3. This is the wiki-vs-RAG fusion bug in a new costume: there, a silent retriever's tie-break outvoted a real signal; here, a signal measured in the wrong units outvotes two good ones. Adding a third opinion made the ranker worse than it was with two, exactly as naive fusion did.

<svg viewBox="0 0 700 180" role="img" aria-label="A stacked score for the gym query. Under raw importance the hub's importance term is 4.0, dwarfing relevance and recency terms that are at most 0.2, so the hub's total towers over gym_new. Under normalised importance the hub's term is 0.2 and gym_new wins.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--s2)">raw importance: the hub's term is 4.0, the rest are &lt;= 0.2</text>
    <text x="20" y="50" fill="var(--ink)">index_hub</text>
    <rect x="110" y="40" width="30" height="14" fill="var(--s1)"></rect><rect x="140" y="40" width="4" height="14" fill="var(--muted)"></rect><rect x="144" y="40" width="400" height="14" fill="var(--s2)"></rect><text x="548" y="51" fill="var(--s2)">imp 4.0 -> wins</text>
    <text x="20" y="76" fill="var(--ink)">gym_new</text>
    <rect x="110" y="66" width="66" height="14" fill="var(--s1)"></rect><rect x="176" y="66" width="33" height="14" fill="var(--muted)"></rect><rect x="209" y="66" width="4" height="14" fill="var(--s2)"></rect><text x="220" y="77" fill="var(--muted)">total ~0.5</text>
    <text x="20" y="120" fill="var(--s1)">normalised importance: the hub's term is 0.2, and gym_new wins</text>
    <text x="20" y="150" fill="var(--ink)">index_hub</text>
    <rect x="110" y="140" width="30" height="14" fill="var(--s1)"></rect><rect x="140" y="140" width="4" height="14" fill="var(--muted)"></rect><rect x="144" y="140" width="40" height="14" fill="var(--s2)"></rect><text x="190" y="151" fill="var(--muted)">total ~0.36</text>
    <text x="360" y="120" fill="var(--muted)" font-size="8">bars: relevance | recency | importance</text>
  </g>
</svg>
^ The gym query's score, broken into its three terms. Raw importance gives the hub a term of 4.0 that dwarfs everything; normalised, the same hub contributes 0.2 and the fresh note's relevance-plus-recency wins. The bug is a units mismatch, not a weighting choice.

### Strategy #4 — normalise importance by the busiest page

The fix is the real ranker's line: divide backlinks by the maximum, so importance lands in [0,1] like its neighbours.

```
# hybrid.py:71-74 — COMPLETE (the fix: normalise by the busiest page, exactly as the labs do)
def importance_norm(doc, max_back):
    """Backlinks normalised by the busiest page -> [0,1]. A hub is important but
    cannot outweigh everything."""
    return doc["backlinks"] / max_back if max_back else 0.0
```

Now the hub's importance is `20/20 = 1.0`, contributing `0.2` — a nudge, not a veto — and the blend is back to 3 of 3. The whole blend, assembled, is the real ranker's weighted sum:

```
# hybrid.py:83-99 — COMPLETE (the weighted blend, and ranking by it)
def score_doc(query, doc, max_back, use_recency, use_importance, imp_fn):
    s = W_REL * relevance(query, doc) if (use_recency or use_importance) else relevance(query, doc)
    if use_recency:
        s += W_REC * recency(doc)
    if use_importance:
        s += W_IMP * imp_fn(doc, max_back)
    return s


def rank(docs, query, use_recency, use_importance, imp_fn=importance_norm):
    max_back = max((d["backlinks"] for d in docs.values()), default=1) or 1
    scored = [(did, score_doc(query, d, max_back, use_recency, use_importance, imp_fn))
              for did, d in docs.items()]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored
```

The self-test walks the whole staircase and asserts each step:

```
# $ python3 hybrid.py --check
#   accuracy  relevance=0/3  +recency=3/3  +raw-imp=0/3  +norm-imp=3/3
#   relevance alone serves at least one stale note = True (0 < 3)
#   adding recency recovers the fresh note = True (3 > 0)
#   raw (unnormalised) importance breaks it = True (0 < 3)
#   normalised importance restores full accuracy = True (3/3)
#   under raw importance the hub 'index_hub' wins query 1 = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · n=3 queries · `python3 hybrid.py --check`

**Three signals only compose when they share a scale. Relevance finds the topic, recency finds the current version, importance finds the canonical page — but a signal measured in the wrong units does not vote louder, it silences the others.**

### The running tally

| ranker | fresh accuracy | what happened |
|---|---|---|
| relevance only | 0/3 | the stale note is the tighter match; memory answers with last year's fact |
| + recency | 3/3 | age decay lifts the fresh note past the stale one |
| + raw importance | 0/3 | the hub's backlink count of 20 vetoes every query |
| + norm importance | 3/3 | importance normalised to [0,1] nudges, does not dominate |

The notes never changed; only which signals the ranker read, and on what scale. The two failures are opposites — relevance is blind to time, raw importance is blind to scale — and the fix for each is a different discipline: add the missing signal, then make sure it speaks the same units as the others. That second discipline is the one that separates a blend that works from a blend that a single loud signal has quietly taken over.

### What we did not settle

The fixture is built to isolate each signal, so a few real complications are deliberately absent. Importance here does not *discriminate* — every real note has the same backlink count, so its only job in this module is to demonstrate the scale bug; in a real graph importance breaks ties toward genuinely canonical pages, which this corpus does not exercise. The weights 0.6 / 0.2 / 0.2 are the labs' defaults, not tuned here, and the right weights depend on how fast your facts actually change — a half-life of 30 days is aggressive for a stable knowledge base and slow for a volatile one, and tuning it against a dated eval set is its own module. And recency assumes edit time tracks correctness, which fails when an old note was right and a new note is a careless edit — recency would then confidently serve the mistake, which is why a real system pairs it with the human-approval gate the earlier tracks built. The dial here is the blend; the next dials are the weights and the half-life, tuned against measured freshness.

## Build

The pipeline in one paragraph: score each note by a weighted blend of relevance (cosine), recency (an exponential decay on age), and importance (backlinks); normalise every signal into [0,1] before you weight it, especially importance, which must be divided by the busiest page; and to validate the blend, label the current note per query and measure how often the top result is fresh, adding each signal one at a time so a regression is attributable. Never rank changing memory on relevance alone, and never add a signal on a scale its neighbours do not share.

We opened on the four-row staircase. The row that matters:

```
# modules/context-and-retrieval/code/retrieval-inter-04/ — COMPLETE, run from that directory
$ python3 hybrid.py --measure
  + norm importance (fix)    3/3
```

Now blend your own memory. The dials are the three weights and the `HALF_LIFE`: point the ranker at notes with real timestamps and backlink counts, label the current note for a set of queries where a fact changed, and add each signal one at a time. Your number to beat is **fresh-answer accuracy** — the fraction of queries whose top result is the current note — and your discipline is attribution: if adding a signal drops accuracy, you have a scale bug, not a weighting preference, so check its units before you touch its weight. Sweep the half-life and watch fresh accuracy trade against stability. Bring back the four-row staircase for your own memory. Good luck.

## Definition of done

- [ ] A ranker blending relevance, recency, and importance as a weighted sum
- [ ] Recency as an exponential decay on age with a configurable half-life
- [ ] Importance normalised into [0,1] by the busiest page before weighting
- [ ] Your own `memory.json`: old and new versions of facts with real ages, plus a labelled current note per query
- [ ] Fresh-answer accuracy measured with each signal added one at a time, so regressions are attributable
- [ ] The raw-importance ranker kept for contrast, so the scale bug is visible
- [ ] `python3 hybrid.py --check` printing SELF-TEST PASS: relevance stale, recency fixes, raw breaks, norm restores
- [ ] The four-row staircase recorded for your own memory, and the half-life you chose
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Relevance-only scored 0/3 on a corpus where the correct note was present. Explain why an *updated* note is usually a worse relevance match than the stale one it replaced.
2. Write the recency formula and compute it for a note 30 days old and one 60 days old at a 30-day half-life. Say why an exponential shape beats a hard age cutoff.
3. Adding importance dropped accuracy from 3/3 to 0/3. State the bug in terms of scale, and name the one operation that fixes it.
4. Connect this module's importance bug to the previous module's fusion bug — what is the single principle both violate?
5. Your own run produced a four-row staircase. Give the accuracy at each row, and say which signal, added on the wrong scale, would break your ranker.

## External resources

- faisalmahdy/agent — `agent/memory/retrieval.py` — my summary: the production ranker this module rebuilds, blending relevance, recency, and importance with the exact `backlinks / max_back` normalisation the bug removes; read the scoring loop and note the weights are configurable and the degraded-embedding path is handled — robustness this teaching version omits.
- Letta / MemGPT, *memory-hierarchy and recency in agent memory* — https://www.letta.com/ — my summary: a memory-OS that pages notes in and out by relevance and recency; read it for how a production personal-agent memory decides what is current, and for the sleep-time consolidation that keeps the "importance" graph honest as facts change.
- Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009) — https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf — my summary: the canonical treatment of length normalisation and term weighting in retrieval scores; read it for why unnormalised signals mislead — the same disease as this module's raw importance, diagnosed for term frequency.
