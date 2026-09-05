---
id: retrieval-inter-08
title: Place the best retrieved chunks at the context edges — models lose the middle
topic: context-and-retrieval
level: intermediate
status: ready
time: 5-8h
summary: Retrieval hands the model a set of chunks and there is a real choice in what order to put them, but long-context models do not read uniformly — they attend to the very start and very end of the input far more than the middle, the U-shaped "lost in the middle" effect — so a chunk's usefulness is its relevance times the attention of the slot it lands in, and the order that matters is best-at-the-edges, not best-first. The naive placement sorts chunks by relevance and fills slots in that order, sending the second- and third-best chunks straight into the dead middle; the edge-aware placement pairs the most relevant chunks with the highest-attention slots (both edges first, then inward), so the strongest evidence sits where the model reads and the weakest chunk is the one left in the middle. On the fixture, edge-aware carries 2.12 units of effective information to naive's 1.80 — an 18% gain with no change to which chunks were retrieved, only where they sit — because pairing the largest relevances with the largest attention weights is exactly the rearrangement inequality, and the gold chunk belongs at an edge while the worst belongs in the middle.
eli5: Imagine reading a stack of notes but only really remembering the first one and the last one, while the ones in the middle blur together. If someone hands you the notes, the smart thing is to put the two most important on top and bottom, and bury the least important in the middle. Sorting them strictly by importance, top to bottom, wastes your second-most-important note by sticking it where you barely look. Same notes, better order — you come away knowing more.
---

## Why this module

Once retrieval has chosen the chunks to show the model, it still has to decide the order to place them in the context window, and the tempting rule is "most relevant first." That rule quietly assumes the model reads its whole input evenly — that a fact in the middle of the context counts the same as a fact at the top. Long-context models do not work that way. They exhibit a strong positional bias: information at the very beginning and the very end of the input is used reliably, while information in the middle is often effectively ignored, even when it is exactly what the question needs. Plotted against position, accuracy is a U — high at both edges, sagging in the middle. This is the "lost in the middle" effect, and it means position is not a cosmetic detail of retrieval; it is a multiplier on every chunk's value.

Once you accept that, the placement problem changes shape. A chunk's contribution is not its relevance alone; it is its relevance weighted by how much attention the slot it occupies receives. The most relevant chunk in the dead middle may deliver less than a moderately relevant chunk at the edge. So the goal is to match the strongest chunks to the highest-attention positions — and the naive "sort by relevance and fill top to bottom" does the opposite for the runners-up, dropping your second- and third-best evidence into precisely the slots the model reads least.

This module makes the effect a number. It models the context slots with a U-shaped attention profile and scores a placement by its effective information: the sum over slots of chunk relevance times slot attention. The naive relevance-order placement scores 1.80; an edge-aware placement that pairs the best chunks with the edges scores 2.12 — an 18% lift from reordering alone, retrieving nothing new. Everything runs offline against a chunks fixture, stdlib Python 3, `$0.00`, with every placement and score computed. The instinct to unlearn is that ranking retrieved chunks by relevance is the end of the job. Ranking decides which chunks; placement decides how much of each one the model actually reads, and the best order is best-at-the-edges, not best-first.

## Concepts

Named here so you can find them again; each is built below.

- **Lost in the middle** — models attend to the input's edges far more than its middle; a U-shaped profile.
- **Slot attention** — how much the model uses information at a given context position.
- **Placement** — the assignment of retrieved chunks to context slots; distinct from ranking.
- **Effective information** — sum over slots of chunk relevance times slot attention.
- **Naive placement** — sort by relevance, fill slots in order; buries the runners-up in the middle.
- **Edge-aware placement** — pair the most relevant chunks with the highest-attention slots.

## Worked example

Source: the assembly step of a retrieval pipeline — after chunks are ranked, the order they are written into the prompt. The slot-attention profile stands in for a real long-context model's measured positional bias; the chunks stand in for a retrieved set, kept small so every placement and score is exact.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-08/` — `middle.py`, and `chunks.json`, five chunks and five slots. Every command runs from there.

### The two placements

Both placements start from the same relevance-sorted chunks; they differ in which slots they target.

```
# middle.py:41-55 — COMPLETE (naive fills slots in relevance order; edge-aware targets the edges)
def naive_placement(relevances):
    """Sort chunks by relevance and drop them into slots 0,1,2,... in that order."""
    order = sorted(range(len(relevances)), key=lambda i: (-relevances[i], i))
    # slot s holds the s-th most relevant chunk
    return {s: chunk for s, chunk in enumerate(order)}


def edge_aware_placement(relevances, weights):
    """Pair the most relevant chunks with the highest-attention slots (edges first)."""
    chunks_by_rel = sorted(range(len(relevances)), key=lambda i: (-relevances[i], i))
    slots_by_attn = sorted(range(len(weights)), key=lambda s: (-weights[s], s))
    return {slot: chunk for slot, chunk in zip(slots_by_attn, chunks_by_rel)}
```

The naive placement zips relevance-sorted chunks with slots `0, 1, 2, …` — so the top chunk goes to slot 0 and the order marches down the positions. The edge-aware placement zips relevance-sorted chunks with *attention*-sorted slots — so the top chunk goes to the highest-attention slot, the next to the next-highest, and so on. That one change — sorting the slots by attention before pairing — is the whole method. See where each chunk lands:

```
# $ python3 middle.py --slots
#   slot   attention   naive chunk (rel)     edge-aware chunk (rel)
#   0      1.00        c0 (0.90)             c0 (0.90)
#   1      0.60        c1 (0.70)             c2 (0.50)
#   2      0.40        c2 (0.50)             c4 (0.10)
#   3      0.60        c3 (0.30)             c3 (0.30)
#   4      1.00        c4 (0.10)             c1 (0.70)
```

run: 2026-08-27 · deterministic; relevances and slot attention are a fixture · 5 chunks · `python3 middle.py --slots`

The attention column is the U: slots 0 and 4 (the edges) get 1.00, slot 2 (the middle) gets 0.40. Now read the two placement columns. Naive puts c1 (relevance 0.70, the second-best chunk) in slot 1 and c2 (0.50) in the dead-middle slot 2 — the runner-up evidence is landing where the model barely reads. Edge-aware puts c1 (0.70) at slot 4, the other edge, and leaves c4 (0.10, the worst chunk) in the middle. Same five chunks; the difference is that edge-aware wastes the low-attention middle on the chunk that matters least.

<svg viewBox="0 0 700 210" role="img" aria-label="Two placements over five slots whose attention forms a U: edges 1.0, then 0.6, middle 0.4. Naive places chunks by relevance in order: c0 0.9 at edge, c1 0.7 and c2 0.5 in the middle region, c4 0.1 at the far edge. Edge-aware places c0 0.9 and c1 0.7 at the two edges, and the worst chunk c4 0.1 in the middle.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">U-shaped attention: edges read most, middle least</text>
    <polyline points="90,40 230,80 370,100 510,80 650,40" fill="none" stroke="var(--muted)" stroke-dasharray="4 3"></polyline>
    <text x="90" y="34" text-anchor="middle" fill="var(--muted)" font-size="7">1.0</text><text x="370" y="114" text-anchor="middle" fill="var(--muted)" font-size="7">0.4</text><text x="650" y="34" text-anchor="middle" fill="var(--muted)" font-size="7">1.0</text>
    <text x="30" y="140" fill="var(--s2)" font-size="8">naive</text>
    <rect x="70" y="128" width="60" height="20" fill="var(--s1)"></rect><text x="100" y="142" text-anchor="middle" fill="var(--panel)" font-size="7">c0 .9</text>
    <rect x="210" y="128" width="60" height="20" fill="var(--muted)"></rect><text x="240" y="142" text-anchor="middle" fill="var(--panel)" font-size="7">c1 .7</text>
    <rect x="350" y="128" width="60" height="20" fill="var(--muted)"></rect><text x="380" y="142" text-anchor="middle" fill="var(--panel)" font-size="7">c2 .5</text>
    <rect x="490" y="128" width="60" height="20" fill="var(--panel)" stroke="var(--line)"></rect><text x="520" y="142" text-anchor="middle" fill="var(--muted)" font-size="7">c3 .3</text>
    <rect x="630" y="128" width="60" height="20" fill="var(--panel)" stroke="var(--line)"></rect><text x="660" y="142" text-anchor="middle" fill="var(--muted)" font-size="7">c4 .1</text>
    <text x="220" y="164" fill="var(--s2)" font-size="7">↑ 2nd/3rd-best buried in the low-attention middle</text>
    <text x="30" y="196" fill="var(--s1)" font-size="8">edge</text>
    <rect x="70" y="184" width="60" height="20" fill="var(--s1)"></rect><text x="100" y="198" text-anchor="middle" fill="var(--panel)" font-size="7">c0 .9</text>
    <rect x="210" y="184" width="60" height="20" fill="var(--panel)" stroke="var(--line)"></rect><text x="240" y="198" text-anchor="middle" fill="var(--muted)" font-size="7">c2 .5</text>
    <rect x="350" y="184" width="60" height="20" fill="var(--panel)" stroke="var(--s2)"></rect><text x="380" y="198" text-anchor="middle" fill="var(--s2)" font-size="7">c4 .1</text>
    <rect x="490" y="184" width="60" height="20" fill="var(--panel)" stroke="var(--line)"></rect><text x="520" y="198" text-anchor="middle" fill="var(--muted)" font-size="7">c3 .3</text>
    <rect x="630" y="184" width="60" height="20" fill="var(--s1)"></rect><text x="660" y="198" text-anchor="middle" fill="var(--panel)" font-size="7">c1 .7</text>
  </g>
</svg>
^ The attention curve peaks at the edges and sags in the middle. Naive fills left-to-right by relevance, so the second- and third-best chunks land in the sag; edge-aware puts the top two at the two edges and leaves the weakest chunk (c4, 0.1) in the middle.

### Effective information

Score a placement by summing chunk relevance times slot attention across all slots.

```
# middle.py:57-60 — COMPLETE (effective information: relevance weighted by where it sits)
def effective_information(placement, relevances, weights):
    """Sum over slots of (chunk relevance) x (slot attention) -- what the model actually gets."""
    return sum(relevances[chunk] * weights[slot] for slot, chunk in placement.items())
```

This is the model's realized access to the retrieved evidence: a chunk contributes its relevance scaled down by how little the model reads its slot. Compute it for both placements:

```
# $ python3 middle.py --effective
#   naive placement:      1.8000
#   edge-aware placement: 2.1200
#   gain from reordering: 0.3200 (18%), same chunks, different slots
```

run: 2026-08-27 · deterministic · `python3 middle.py --effective`

<svg viewBox="0 0 700 160" role="img" aria-label="Two bars of effective information. Naive placement 1.80, edge-aware placement 2.12, a taller bar. A bracket marks the 0.32 gain, labeled reordering only.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">effective information delivered — same chunks, different order</text>
    <line x1="60" y1="130" x2="660" y2="130" stroke="var(--line)"></line>
    <rect x="120" y="58" width="120" height="72" fill="var(--muted)"></rect><text x="180" y="52" text-anchor="middle" fill="var(--muted)" font-size="9">1.80</text><text x="180" y="146" text-anchor="middle" fill="var(--muted)" font-size="8">naive</text>
    <rect x="360" y="45" width="120" height="85" fill="var(--s1)"></rect><text x="420" y="39" text-anchor="middle" fill="var(--s1)" font-size="9">2.12</text><text x="420" y="146" text-anchor="middle" fill="var(--s1)" font-size="8">edge-aware</text>
    <line x1="500" y1="45" x2="500" y2="58" stroke="var(--acc-line)"></line><text x="560" y="54" fill="var(--acc-ink)" font-size="8">+0.32 (18%)</text><text x="560" y="68" fill="var(--muted)" font-size="7">reordering only</text>
  </g>
</svg>
^ Reordering alone lifts effective information from 1.80 to 2.12 — a free 18% with no new retrieval, no better chunks, and no larger context.

Edge-aware delivers 2.12 against naive's 1.80 — 18% more usable information, from nothing but reordering the same chunks. No extra retrieval, no better chunks, no larger context; the gain is entirely in matching the strong evidence to the positions the model actually reads. That this is optimal is not a coincidence: pairing the largest relevances with the largest attention weights maximizes the sum of products, which is the rearrangement inequality — sorted-with-sorted beats any other pairing. Naive pairs relevance-order with position-order, which is not sorted-with-sorted whenever the attention profile is not monotonic, and a U is about as non-monotonic as it gets.

<svg viewBox="0 0 700 170" role="img" aria-label="The rearrangement inequality. On the left, sorted relevances 0.9, 0.7, 0.5, 0.3, 0.1 paired with sorted attention 1.0, 1.0, 0.6, 0.6, 0.4 gives the maximum sum of products 2.12. On the right, relevances paired with the naive position order 1.0, 0.6, 0.4, 0.6, 1.0 gives a smaller sum 1.80.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">rearrangement inequality: sorted×sorted maximizes the sum of products</text>
    <text x="60" y="44" fill="var(--s1)" font-size="8">edge-aware (sorted × sorted)</text>
    <text x="60" y="62" fill="var(--muted)" font-size="8">rel:  .9  .7  .5  .3  .1</text>
    <text x="60" y="78" fill="var(--muted)" font-size="8">attn: 1.0 1.0 .6  .6  .4</text>
    <text x="60" y="98" fill="var(--s1)" font-size="8">Σ = 2.12  (max)</text>
    <line x1="55" y1="106" x2="330" y2="106" stroke="var(--line)"></line>
    <text x="400" y="44" fill="var(--s2)" font-size="8">naive (rel-order × position-order)</text>
    <text x="400" y="62" fill="var(--muted)" font-size="8">rel:  .9  .7  .5  .3  .1</text>
    <text x="400" y="78" fill="var(--muted)" font-size="8">attn: 1.0 .6  .4  .6  1.0</text>
    <text x="400" y="98" fill="var(--s2)" font-size="8">Σ = 1.80  (mismatched)</text>
    <text x="60" y="140" fill="var(--muted)" font-size="8">the U attention profile is non-monotonic, so filling positions in order mis-pairs the sorts</text>
  </g>
</svg>
^ Edge-aware sorts both relevances and attention weights and pairs them, giving the maximum sum 2.12; naive pairs relevances with the U-shaped positions in place, mis-matching the sorts and giving 1.80.

**Long-context models attend to the edges of the input and lose the middle, so a retrieved chunk's value is its relevance times its slot's attention — place the most relevant chunks at the two edges and the weakest in the middle, and effective information rises from 1.80 to 2.12 (18%) with no change to what was retrieved, because pairing the largest relevances with the largest attention weights is the rearrangement inequality and best-first is not best-at-the-edges.**

### The self-test

The `--check` mode plants the bug — relevance-order placement — and proves it: the middle is the lowest-attention slot, edge-aware carries more effective information, the gold chunk sits at an edge, and the worst chunk is the one left in the middle.

```
# $ python3 middle.py --check
#   the middle slot has the least attention, the edges the most = True (mid 0.40, edge 1.00)
#   edge-aware carries more effective information than naive = True (2.1200 vs 1.8000)
#   the most relevant chunk sits in a max-attention (edge) slot = True (chunk c0 at slot 0)
#   the least relevant chunk is the one left in the dead middle = True (chunk c4 at slot 2)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 middle.py --check`

The `gold_at_edge` and `worst_in_middle` lines together are the placement rule stated as an outcome: the best chunk ends up where the model reads most, and the middle — the slot you cannot avoid having — is spent on the chunk you can most afford to lose. That is the correct allocation of a scarce resource (edge attention) to the chunks that most deserve it, and it falls straight out of pairing sorted relevances with sorted attention.

```
# middle.py:117-123 — COMPLETE (edge-aware beats naive; the gold lands at a max-attention slot)
    edge_better = ee > en
    print("  edge-aware carries more effective information than naive = %s (%.4f vs %.4f)"
          % (edge_better, ee, en))

    gold = max(range(len(rel)), key=lambda i: rel[i])
    gold_slot = slot_of(edge, gold)
    gold_at_edge = w[gold_slot] == max(w)
```

And the mirror-image assertion confirms the middle is spent on the chunk that matters least:

```
# middle.py:127-130 — COMPLETE (the worst chunk is the one left in the dead middle)
    worst = min(range(len(rel)), key=lambda i: rel[i])
    worst_slot = slot_of(edge, worst)
    worst_in_middle = w[worst_slot] == min(w)
```

### The running tally

| slot | attention | naive: chunk (rel) | edge-aware: chunk (rel) |
|---|---|---|---|
| 0 (edge) | 1.00 | c0 (0.90) | c0 (0.90) |
| 1 | 0.60 | c1 (0.70) | c2 (0.50) |
| 2 (middle) | 0.40 | c2 (0.50) | c4 (0.10) |
| 3 | 0.60 | c3 (0.30) | c3 (0.30) |
| 4 (edge) | 1.00 | c4 (0.10) | c1 (0.70) |

Read slot 4, the second edge: naive wastes its 1.00 attention on c4 (relevance 0.10) while edge-aware spends it on c1 (0.70), and read slot 2, the middle: naive spends its 0.40 on c2 (0.50) while edge-aware spends it on c4 (0.10). The two swaps — the second-best chunk to the second edge, the worst chunk to the middle — are the entire 0.32 gain. Naive's fatal move is treating the two edges asymmetrically: it fills slot 0 with the best (correct) but leaves the equally-strong slot 4 for last, handing it the dregs. Edge-aware treats the two high-attention slots as the pair they are.

### What we did not settle

This is the reordering fix; a fuller treatment adds a few things. The attention profile here is a fixed, known U; a real model's profile depends on the model and the context length, and you would measure it (a needle-in-a-haystack sweep) rather than assume it. The scoring treats chunks as independent, but order also affects coherence — a chunk that sets up another should precede it — so pure attention-weighting can fight readability, and a real assembler balances both. Reordering is cheaper than the alternatives but complements them: retrieving fewer, better chunks (`retrieval-inter-05` rerank) shrinks the middle problem, and a shorter context has a shallower U. And the gain is largest when relevance varies a lot across the retrieved set; if every chunk is equally relevant, placement matters less. The invariant: after ranking, place — put the strongest evidence where the model reads most, the edges, and never bury a runner-up in the middle.

## Build

The build in one paragraph: after ranking retrieved chunks, place them by pairing the most relevant with the highest-attention context positions — the two edges first, then working inward — rather than filling positions in relevance order, because long-context models lose the middle and a chunk's value is its relevance times its slot's attention; the best chunk belongs at an edge and the weakest in the middle. Measure your model's positional profile rather than assuming the U, balance attention-weighting against narrative coherence, pair reordering with reranking to fewer chunks, and expect the largest gain when relevance varies most across the set.

We opened on the slots. The number that proves the fix is the effective information of each placement:

```
# modules/context-and-retrieval/code/retrieval-inter-08/ — COMPLETE, run from that directory
$ python3 middle.py --effective
  naive placement:      1.8000
  edge-aware placement: 2.1200
```

Now build your own. Take a real retrieved set with varied relevance and a model whose positional bias you have measured, and score the relevance-order placement against an edge-aware one. Your number to beat is not retrieval recall; it is **the effective information (relevance times slot attention) of naive versus edge-aware placement** — edge-aware should win by reordering alone, with the gold chunk at an edge and the weakest in the middle. Bring back both placements' scores. Good luck.

## Definition of done

- [ ] A U-shaped slot-attention profile (edges high, middle low)
- [ ] A naive placement filling slots in relevance order
- [ ] An edge-aware placement pairing the most relevant chunks with the highest-attention slots
- [ ] An effective-information score (sum of relevance times slot attention)
- [ ] Confirmation edge-aware carries more effective information than naive
- [ ] Confirmation the gold chunk sits at an edge and the worst chunk in the middle
- [ ] `python3 middle.py --check` printing SELF-TEST PASS: middle_lowest, edge_better, gold_at_edge, worst_in_middle
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What is the "lost in the middle" effect, and what shape does accuracy-versus-position take?
2. Why is a chunk's value its relevance times its slot's attention, not its relevance alone?
3. How does the edge-aware placement differ from the naive one in one line of code?
4. Why is pairing the strongest chunks with the edges optimal? Name the inequality.
5. Your own retrieved set was placed both ways. What effective information did each score, and where did the gold and worst chunks end up?

## External resources

- Liu et al., *Lost in the Middle: How Language Models Use Long Contexts* — my summary: the paper documenting the U-shaped positional accuracy and that the middle is underused; read it for the empirical profile this module models.
- Any RAG-assembly guidance on reordering retrieved passages by position — my summary: the practical recipe of placing the top passages at the head and tail of the context; read it for how this reordering is applied in production pipelines.
- This hub, *retrieval-inter-05* (rerank for precision) and *retrieval-inter-07* (cosine, not raw dot) — read them for the ranking that decides which chunks you place and why fewer, better chunks shrink the middle problem.
