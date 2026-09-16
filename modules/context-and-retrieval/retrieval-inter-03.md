---
id: retrieval-inter-03
title: Retrieved isn't injected — the duplicate that eats your context budget
topic: context-and-retrieval
level: intermediate
status: ready
time: 8-10h
summary: Retrieval returns more chunks than fit the context window, so a budget step chooses what to inject — and the obvious choice, fill by rank until full, answers only 4 of 6 facts because on two queries it packs a chunk and its near-duplicate, spending 40 tokens to say one thing and dropping the chunk with the second fact. Skip a chunk that duplicates one already taken and the same 40-token budget covers 6 of 6 facts at fewer tokens, because a budget rewards new information per token, not rank.
eli5: You pulled every useful note off the shelf, but your bag only holds so much. Grab them in order and you pack two copies of the same note, so the one fact you still needed gets left behind. Don't pack a copy of what's already in the bag and everything fits.
---

## Why this module

The last two modules found the right chunks. This one faces what happens next: they do not all fit. Retrieval returns a ranked list of candidates, but the model's context window is a fixed budget, so something between "retrieved" and "injected" has to drop the overflow. The anatomy notes flag this exact seam — "retrieved ≠ injected" — and it is where a retrieval system that scored perfectly on the last two modules can still feed the model an answer that is missing half its facts. The chunks were found; they just did not make it into the prompt.

The obvious budgeting rule is to walk the ranking and take chunks until the budget is full. It is one loop, it always respects the budget, and it quietly fails in a way the earlier metrics cannot see: when the top two chunks say the *same thing*, it spends the whole budget saying that one thing twice and drops the lower-ranked chunk that held the only other fact the query needed. Rank order optimizes for relevance per chunk; a budget has to optimize for *information per token*, and those are not the same objective.

You need `retrieval-inter-01` and `-02` — chunks that are already scored and sized. Everything runs offline against a fixture of pre-retrieved candidates, stdlib Python 3, `$0.00`, one sitting. The instinct to unlearn is that a higher-ranked chunk is always worth injecting: a chunk that repeats information already in the context is worth nothing and costs tokens, and spotting that is the whole job.

Here is the budget step done two ways, on the same candidates:

```
# modules/context-and-retrieval/code/retrieval-inter-03/ — COMPLETE, run from that directory
$ python3 budget.py --measure

CONTEXT BUDGET — answer coverage and injected tokens (budget = 40)
------------------------------------------------------------------
  selector                coverage    avg tokens injected
  rank-fill (bug)         4/6         36.7
  dedup-coverage (fix)    6/6         31.3
```

run: 2026-08-25 · deterministic; candidates are a fixture · n=3 queries needing 2 facts each, budget 40 tokens · `python3 budget.py --measure`

Same budget, same candidates, same retrieval. Filling by rank answers four of six needed facts and spends 36.7 tokens doing it. Dropping duplicates answers all six and spends *fewer* tokens. This module is why the obvious selector leaves facts on the floor, and why the fix is cheaper, not just better.

## Concepts

Named here so you can find them again; each is built below.

- **Candidate chunks** — what retrieval returned: each with a score, a token cost, and the facts it carries.
- **Context budget** — the token ceiling on what you can inject. Smaller than the candidates.
- **Retrieved ≠ injected** — the gap this module lives in: found is not the same as fed to the model.
- **Rank-fill** — take chunks in score order until the budget is full. The obvious selector, and the bug.
- **Near-duplicate** — two chunks whose cosine is high: same information, twice the tokens.
- **Coverage** — the fraction of a query's needed facts present in the injected set. The metric a budget should maximize.

## Worked example

Source: faisalmahdy/agent — the compaction and context-assembly path that trims retrieved material to fit a turn; anatomy episode 007 names the principle this module measures, "retrieved ≠ injected." The chunks here are the scored, sized output of the retrievers built in the previous two modules.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-03/` — `budget.py`, and `candidates.json`, three queries' worth of pre-retrieved chunks and a 40-token budget. Every command runs from there.

### The frame: packing a bag with a weight limit

Think of injection as packing a bag with a strict weight limit before a trip. Retrieval is you pulling every useful item off the shelf — more than the bag holds — and the budget step is the packing. The obvious way to pack is by priority: put in the most important item, then the next, until the bag is full. That works right up until your two highest-priority items are two copies of the same charger. Priority says pack both; the bag now holds one charger's worth of information at two chargers' weight, and the toothbrush you also needed — lower priority, but the only one of its kind — gets left on the bed.

That is the entire bug. A budget is not a priority queue; it is a packing problem, and the thing you are packing is *information*, not *rank*. A second copy of a fact you already packed adds weight and no information, so the correct move is to refuse it and spend that weight on something new. The fix is one check — is this a duplicate of something already in the bag? — and the numbers below are it earning its place.

### Look at the candidates: more tokens than the budget holds

```
# $ python3 budget.py --candidates "what gate and seat is my flight"
#   (budget = 40 tokens, needs facts ['gate22', 'seat14c'])
#   c1     score 0.90  20 tok  facts=['gate22']
#   c2     score 0.85  20 tok  facts=['gate22']
#   c3     score 0.60  11 tok  facts=['seat14c']
```

run: 2026-08-25 · fixture · `python3 budget.py --candidates "..."`

The query needs two facts: the gate and the seat. Three chunks came back totalling 51 tokens against a 40-token budget, so one chunk must be dropped. Notice the shape of the trap: `c1` and `c2` both carry the gate and are nearly identical text, ranked one and two; `c3` carries the seat, ranked last and cheapest. Whichever chunk you drop decides whether the model can answer the whole question. Drop `c3` and the model never sees the seat.

<svg viewBox="0 0 700 170" role="img" aria-label="A funnel: retrieved candidates totalling 51 tokens (c1 20, c2 20, c3 11) pass through a 40-token budget gate. Only a subset is injected. Retrieved is not the same as injected.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">retrieved (51 tok)  ->  budget gate (40 tok)  ->  injected</text>
    <rect x="20" y="40" width="120" height="22" rx="3" fill="var(--muted)"></rect><text x="26" y="55" fill="var(--panel)" font-size="9">c1 gate  20</text>
    <rect x="20" y="66" width="120" height="22" rx="3" fill="var(--muted)"></rect><text x="26" y="81" fill="var(--panel)" font-size="9">c2 gate  20 (dup)</text>
    <rect x="20" y="92" width="70" height="22" rx="3" fill="var(--s1)"></rect><text x="26" y="107" fill="var(--panel)" font-size="9">c3 seat 11</text>
    <path d="M 170 40 L 300 70 L 300 100 L 170 114 Z" fill="none" stroke="var(--line)"></path>
    <text x="205" y="88" fill="var(--muted)" font-size="9">40 tok</text>
    <line x1="150" y1="51" x2="360" y2="51" stroke="var(--muted)" stroke-dasharray="2 2"></line>
    <line x1="150" y1="77" x2="360" y2="77" stroke="var(--muted)" stroke-dasharray="2 2"></line>
    <line x1="100" y1="103" x2="360" y2="103" stroke="var(--s1)" stroke-dasharray="2 2"></line>
    <text x="380" y="60" fill="var(--muted)">what you inject here is</text>
    <text x="380" y="76" fill="var(--muted)">a CHOICE, and the choice</text>
    <text x="380" y="92" fill="var(--muted)">decides which facts the</text>
    <text x="380" y="108" fill="var(--muted)">model ever gets to see.</text>
  </g>
</svg>
^ Retrieval returns 51 tokens; the window holds 40. The budget gate is a choice, not a formality — and which chunk it drops decides whether the seat fact reaches the model at all.

### Strategy #1 — fill by rank until full. This is the bug.

The obvious selector walks the ranking and takes each chunk that still fits.

```
# budget.py:63-71 — COMPLETE (take chunks in score order until the budget is full)
def rank_fill(chunks, budget):
    """THE BUG: walk the ranking, take each chunk if it still fits. Redundancy is
    invisible to it, so a chunk and its near-duplicate can both be taken."""
    picked, used = [], 0
    for ch in sorted(chunks, key=lambda c: (-c["score"], c["id"])):
        if used + cost(ch) <= budget:
            picked.append(ch)
            used += cost(ch)
    return picked
```

Predict what it packs for the flight query before you run it. It takes `c1` (20 tokens, the gate) and then `c2` (20 tokens, the gate again) for exactly 40 tokens — full — and never reaches `c3`. Here is the selection:

```
# $ python3 budget.py --select "what gate and seat is my flight"
#   rank-fill (bug)        inject ['c1', 'c2'] = 40 tok, facts ['gate22']  <-- MISSING ['seat14c']
#   dedup-coverage (fix)   inject ['c1', 'c3'] = 31 tok, facts ['gate22', 'seat14c']  (complete)
```

run: 2026-08-25 · fixture · `python3 budget.py --select "..."`

Rank-fill spent its entire budget on the gate, twice, and left the seat on the shelf. The failure is invisible to every metric from the earlier modules: retrieval ranked the right chunks, `c3` was *retrieved*, the pipeline "found" the seat — it just never injected it. This is why "retrieved ≠ injected" is its own measurement. The chunk with the answer being in the candidate list is worth nothing if the budget step drops it.

### Strategy #2 — skip a chunk that duplicates one already taken

The fix adds one check before packing a chunk: is it a near-duplicate of something already injected? If so, it carries no new information, so skip it and keep the budget for a chunk that does.

```
# budget.py:74-84 — COMPLETE (drop a redundant chunk, then fill by score under budget)
def dedup_coverage(chunks, budget):
    """Drop a chunk that near-duplicates one already taken (it adds tokens, no new
    information), then fill by score under the budget."""
    picked, used = [], 0
    for ch in sorted(chunks, key=lambda c: (-c["score"], c["id"])):
        if any(cosine(ch["text"], p["text"]) >= DUP_SIM for p in picked):
            continue                                   # redundant: skip, keep the budget
        if used + cost(ch) <= budget:
            picked.append(ch)
            used += cost(ch)
    return picked
```

The `cosine(...) >= DUP_SIM` line is the whole fix: `c2` is 0.88 cosine to `c1`, above the 0.8 threshold, so it is skipped as redundant, and the budget it would have eaten goes to `c3` instead. Now the injected set is `c1` and `c3` — the gate and the seat — at 31 tokens, under budget with room to spare. Coverage is measured by which needed facts survived into the injected set:

```
# budget.py:92-108 — COMPLETE (coverage = needed facts present in the injected set)
def facts_present(picked, needed):
    """Which required facts appear in the injected set."""
    have = set()
    for ch in picked:
        have |= set(ch["facts"])
    return have & set(needed)


def evaluate(budget, queries, selector):
    covered = total = injected = 0
    for item in queries:
        picked = selector(item["chunks"], budget)
        got = facts_present(picked, item["needs"])
        covered += len(got)
        total += len(item["needs"])
        injected += sum(cost(c) for c in picked)
    return covered, total, injected / len(queries)
```

Across all three queries the difference is 4 of 6 facts against 6 of 6 — and the fix injects *fewer* tokens on average, 31.3 against 36.7, because skipping the duplicate frees budget it never needed to spend. That is the rare case where the correct thing is also the cheaper thing.

<svg viewBox="0 0 700 190" role="img" aria-label="Two packed bags for the flight query under a 40-token budget. Rank-fill packs c1 gate and c2 gate, 40 tokens, one fact, missing the seat. Dedup-coverage packs c1 gate and c3 seat, 31 tokens, both facts complete.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--s2)">rank-fill: 40 tok, one fact</text>
    <text x="360" y="20" fill="var(--s1)">dedup-coverage: 31 tok, both facts</text>
    <rect x="20" y="34" width="300" height="70" rx="6" fill="none" stroke="var(--s2)"></rect>
    <rect x="30" y="44" width="180" height="22" rx="3" fill="var(--muted)"></rect><text x="36" y="59" fill="var(--panel)" font-size="9">c1 gate  20</text>
    <rect x="30" y="70" width="180" height="22" rx="3" fill="var(--muted)"></rect><text x="36" y="85" fill="var(--panel)" font-size="9">c2 gate  20 (duplicate)</text>
    <text x="30" y="102" fill="var(--s2)" font-size="9">seat: never packed</text>
    <rect x="360" y="34" width="300" height="70" rx="6" fill="none" stroke="var(--s1)"></rect>
    <rect x="370" y="44" width="180" height="22" rx="3" fill="var(--muted)"></rect><text x="376" y="59" fill="var(--panel)" font-size="9">c1 gate  20</text>
    <rect x="370" y="70" width="99" height="22" rx="3" fill="var(--s1)"></rect><text x="376" y="85" fill="var(--panel)" font-size="9">c3 seat 11</text>
    <text x="370" y="102" fill="var(--s1)" font-size="9">9 tokens still free</text>
    <text x="20" y="140" fill="var(--muted)">the duplicate weighs the same as the answer — and buys nothing.</text>
    <text x="20" y="162" fill="var(--muted)">a budget rewards information per token, which rank order never checks.</text>
  </g>
</svg>
^ The same budget packed two ways. Rank-fill fills 40 tokens with the gate stated twice; dedup-coverage packs the gate once and the seat, complete, with room left over. The duplicate cost a fact.

### Prove it in one run

The self-test checks the mechanism, not just the score: that rank-fill actually injects a near-duplicate pair, that dropping it raises coverage, and that it never overruns the budget.

```
# $ python3 budget.py --check
#   rank-fill coverage=4/6  dedup-coverage coverage=6/6
#   dedup-coverage answers more facts than rank-fill = True (6 > 4)
#   dedup-coverage never exceeds the budget = True
#   rank-fill injects a near-duplicate pair somewhere = True
#   dedup-coverage injects no more tokens than rank-fill = True (31.3 <= 36.7)
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · n=3 queries · `python3 budget.py --check`

The `dup_taken` line is the diagnosis: it confirms rank-fill's failure is redundancy, not bad luck — there really is a near-duplicate pair sitting in the injected set, spending tokens on nothing.

<svg viewBox="0 0 700 160" role="img" aria-label="Two selectors on two axes. Rank-fill: coverage 4 of 6, injected 36.7 tokens. Dedup-coverage: coverage 6 of 6, injected 31.3 tokens. Dedup-coverage is both more complete and cheaper.">
  <g font-family="var(--mono)" font-size="10">
    <text x="30" y="22" fill="var(--muted)">coverage (higher better) and injected tokens (lower better), one budget</text>
    <text x="20" y="60" fill="var(--ink)">rank-fill</text>
    <rect x="150" y="50" width="260" height="16" rx="3" fill="var(--s2)"></rect><text x="418" y="63" fill="var(--s2)">coverage 4/6</text>
    <rect x="150" y="72" width="294" height="12" rx="3" fill="var(--muted)"></rect><text x="452" y="82" fill="var(--muted)" font-size="9">36.7 tok</text>
    <text x="20" y="118" fill="var(--ink)">dedup-cover</text>
    <rect x="150" y="108" width="390" height="16" rx="3" fill="var(--s1)"></rect><text x="548" y="121" fill="var(--s1)">coverage 6/6</text>
    <rect x="150" y="130" width="251" height="12" rx="3" fill="var(--muted)"></rect><text x="409" y="140" fill="var(--muted)" font-size="9">31.3 tok</text>
  </g>
</svg>
^ Both axes favor the fix: dedup-coverage answers all six facts (against four) while injecting fewer tokens (31.3 against 36.7). Dropping the duplicate is the rare move that is more complete and cheaper at once.

**A context budget is a packing problem, not a priority queue: reward information per token, and a chunk that repeats what you already injected is pure weight — drop it.**

### The running tally

| selector | coverage | avg tokens injected | what happened |
|---|---|---|---|
| rank-fill | 4/6 | 36.7 | two queries packed a duplicate, dropped a fact |
| dedup-coverage | 6/6 | 31.3 | skipped the duplicate, packed the second fact |

The candidates never changed; only the packing did. Rank-fill is not wrong because it respects the budget — it always does — it is wrong because it treats a token spent on a duplicate as well spent. The third query, which had no duplicate, both selectors handled identically; the gap appears only where redundancy does, which is exactly where the earlier relevance metrics are blind.

### What we did not settle

The fixture uses obvious near-duplicates and a coverage metric that treats every fact as equally required. Real complications we skipped: deduplication by cosine has a threshold you must tune — set it too low and you drop genuinely distinct chunks that happen to share vocabulary, too high and you keep paraphrased duplicates; true budget selection is a knapsack problem (maximize coverage subject to a token limit), and greedy dedup-then-fill is a cheap approximation that can still be beaten when chunk sizes vary widely; and coverage here assumes you know each chunk's facts, whereas in production you infer relevance from the retrieval score and never really know whether the answer survived — which is why measuring end-to-end answer quality, not just retrieval, is the only honest check. The dial here is dedup and coverage; the next dial is a real optimizer over token cost.

## Build

The pipeline in one paragraph: take the scored, sized chunks retrieval returned; set a token budget equal to your context allowance for retrieved context; select chunks by score but skip any that near-duplicate one already selected; and measure answer coverage — the needed facts present in the injected set — against the tokens you spent. Never fill by rank alone, and never assume a retrieved chunk was injected.

We opened on the two selectors. The row that matters:

```
# modules/context-and-retrieval/code/retrieval-inter-03/ — COMPLETE, run from that directory
$ python3 budget.py --measure
  dedup-coverage (fix)    6/6         31.3
```

Now budget your own retrieved candidates. The dials are the token `budget` and the `DUP_SIM` threshold: sweep the threshold and watch coverage — too high readmits duplicates, too low discards distinct chunks. Your number to beat is **coverage at a fixed budget**: the fraction of needed facts you inject per token you spend. Construct a query whose answer needs two facts where the top chunk has a near-duplicate, and confirm rank-fill drops the second fact while dedup keeps it. Bring back both selectors' coverage and injected-token numbers, and the threshold you chose. Good luck.

## Definition of done

- [ ] A budget selector over scored, sized chunks that respects a token ceiling
- [ ] Your own `candidates.json`: queries needing two-plus facts, at least one with a near-duplicate top chunk
- [ ] A near-duplicate check (cosine over a threshold) that skips redundant chunks
- [ ] Answer coverage measured as needed facts present in the injected set, plus injected tokens
- [ ] The rank-fill selector kept for contrast, so the dropped fact is visible
- [ ] `python3 budget.py --check` printing SELF-TEST PASS: dedup covers more, stays within budget, a duplicate really was taken, no more tokens
- [ ] The coverage-and-cost numbers for both selectors, and the dedup threshold you chose
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. "Retrieved ≠ injected." Explain the gap in one sentence, and why a retrieval metric that scored the chunks perfectly can still feed the model an incomplete answer.
2. Rank-fill injected two chunks for 40 tokens and answered only one fact. Say exactly where the other 20 tokens went and what got dropped.
3. Give the one check that took coverage from 4/6 to 6/6, and explain why the fix also lowered the injected-token count.
4. Why is a context budget a packing problem and not a priority queue? Name the quantity the packer should maximize.
5. Your own run swept the dedup threshold. What happened to coverage at a too-high and a too-low threshold, and where did you set it?

## External resources

- faisalmahdy/agent — the context-assembly / compaction path — my summary: where retrieved material is trimmed to fit a turn; read it for the real budget step this module isolates, and note that deduplication and coverage are exactly the decisions a compaction routine makes under pressure.
- Liu et al., *Lost in the Middle: How Language Models Use Long Contexts* (2023) — https://arxiv.org/abs/2307.03172 — my summary: models attend unevenly across a long context, so *more* injected tokens is not more usable information; read it for why a tight, redundancy-free budget can beat a full window, which is the deeper reason dedup-coverage wins.
- Anthropic, *Introducing Contextual Retrieval* — https://www.anthropic.com/news/contextual-retrieval — my summary: production retrieval that reranks and trims candidates before injection; read it for how reranking and a budget interact, and treat the coverage metric here as the thing a reranker is ultimately trying to protect.
