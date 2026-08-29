---
id: beam-inter-01
title: Greedy decoding is myopic — the highest-probability token can lead to the worst sequence
topic: below-the-prompt
level: intermediate
status: ready
time: 5-8h
summary: Decoding a sequence means choosing tokens one at a time, and greedy decoding takes the single highest-probability token at each step — fast, locally optimal, and exactly the trap, because the best first token can open onto poor continuations while a slightly-worse first token opens onto excellent ones. On a two-step tree where token A (probability 0.55) is the local favorite but its continuations are mediocre (0.5, 0.5) while token B (0.45) has a lopsided 0.95 continuation, greedy commits to A and returns A-A1 at total probability 0.275, while the actually most-probable sequence is B-B1 at 0.4275 — a sequence greedy walked right past. Beam search keeps the top-k partial sequences (the beam width) instead of one, so the worse-looking first token B survives long enough to reveal its strong continuation, and beam width 2 finds B-B1 while beam width 1 reproduces greedy exactly. Same model, same probabilities; the only difference is whether the decoder can hold more than one hypothesis at once, and greedy's inability to is why the single most probable token per step does not build the most probable sequence.
eli5: Imagine choosing a path through a maze where at each fork you always take the wider opening. That works until a wide opening leads to a dead end while a narrow one just past it opens into the fastest route. Always grabbing the widest next step is greedy, and it gets fooled by exactly this. A smarter explorer keeps a few promising paths alive at once and only commits at the end — so the narrow-then-open route wins, because the best whole path isn't always made of the best single steps.
---

## Why this module

A language model gives you, at each position, a probability distribution over the next token. To produce a sequence you have to turn that stream of distributions into a series of committed choices, and how you make those choices is decoding. The simplest decoder is greedy: at every step, take the token with the highest probability. It is one `argmax` per step, it is deterministic, and it is locally optimal — at each individual step it makes the single best choice available. The problem is that a sequence is not a sum of independent steps, and locally optimal choices do not compose into a globally optimal sequence.

Here is why they don't. The probability of a whole sequence is the product of its step probabilities, so the best sequence is the one that maximizes that product over all steps together. Greedy maximizes the first factor, then the second, and so on, each in isolation — but a large first factor can be attached to small later factors, and a smaller first factor to large ones. So the token that looks best right now can be the doorway to a region of low-probability continuations, while a token that looks slightly worse leads into high-probability ones. Greedy, having committed to the local winner and thrown everything else away, never discovers this. It returns a sequence that is optimal step-by-step and suboptimal overall.

Beam search is the standard fix. Instead of carrying one running sequence, it carries the top-k partial sequences — k is the beam width — expands all of them by one token each step, scores the resulting candidates by their running total probability, and keeps the best k. A first token that looked worse is not discarded immediately; it stays on the beam long enough for its strong continuations to lift it back to the top. This module builds greedy and beam on a small two-step tree, enumerates the true probability of every full sequence so the right answer is known, and shows greedy returning a sequence that is measurably not the most probable one. Everything runs offline against a probability-tree fixture, stdlib Python 3, `$0.00`. The instinct to unlearn is that taking the most probable token at each step yields the most probable sequence. It does not — the most probable sequence is a property of whole paths, and a decoder that only ever holds one path cannot find it.

## Concepts

Named here so you can find them again; each is built below.

- **Decoding** — turning per-step token distributions into a committed sequence.
- **Greedy decoding** — take the single highest-probability token each step; one hypothesis.
- **Sequence probability** — the product of the step probabilities along a path.
- **Local vs global optimum** — best-per-step is not best-overall; the two can diverge.
- **Beam search** — keep the top-k partial sequences, expand and prune each step.
- **Beam width** — how many hypotheses to carry; width 1 is exactly greedy.

## Worked example

Source: the decoding step that sits at the very end of generation, after the model has produced its logits — the choice of how to commit to tokens. The probability tree stands in for a real model's short-horizon next-token distributions, kept tiny so every full-sequence probability is exact and the greedy trap is visible in the numbers.

Script and fixture: `modules/below-the-prompt/code/beam-inter-01/` — `beam.py`, and `tree.json`, a two-step tree. Every command runs from there.

### The tree, and the sequence that should win

Every full sequence's probability is the product of its step probabilities; enumerating them shows what a perfect decoder would return.

```
# beam.py:42-64 — COMPLETE (enumerate every root-to-leaf path and its probability; find the best)
def all_sequences(tree):
    """Every root-to-leaf path with its total probability (product of step probabilities)."""
    out = []

    def walk(node, prefix, prob):
        nxt = node.get("next")
        if not nxt:
            out.append((prefix, prob))
            return
        for tok, child in nxt.items():
            walk(child, prefix + [tok], prob * child["p"])

    for tok, child in tree.items():
        walk(child, [tok], child["p"])
    return out


def best_sequence(tree):
    """The globally most-probable full sequence -- what a perfect decoder would return."""
    return max(all_sequences(tree), key=lambda s: s[1])
```

Look at the four possible sequences:

```
# $ python3 beam.py --tree
#   B-B1         0.4275
#   A-A1         0.2750
#   A-A2         0.2750
#   B-B2         0.0225
#   most probable sequence: B-B1 (0.4275)
```

run: 2026-08-27 · deterministic; the probability tree is a fixture · 2 steps · `python3 beam.py --tree`

The most probable sequence is B-B1 at 0.4275 — but its first token, B, has probability 0.45, which is *not* the highest first-token probability; A has 0.55. That is the whole setup: the best sequence starts with the worse-looking first token. B is only 0.45 up front, but its continuation B1 is 0.95, so the product 0.45 × 0.95 = 0.4275 beats anything starting with A, whose best continuation is only 0.5 (product 0.55 × 0.5 = 0.275). A greedy decoder, looking only at the first step, will never choose B.

<svg viewBox="0 0 700 220" role="img" aria-label="A probability tree. Root splits to A (0.55) and B (0.45). A splits to A1 (0.5) and A2 (0.5). B splits to B1 (0.95) and B2 (0.05). Leaf totals: A-A1 0.275, A-A2 0.275, B-B1 0.4275, B-B2 0.0225. The A branch is highlighted as greedy's choice; the B-B1 leaf is highlighted as the true best.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the tree: greedy takes A (0.55); the best sequence starts with B (0.45)</text>
    <circle cx="90" cy="110" r="5" fill="var(--ink)"></circle><text x="70" y="114" fill="var(--muted)" font-size="7">start</text>
    <line x1="95" y1="105" x2="240" y2="60" stroke="var(--s2)"></line><text x="150" y="72" fill="var(--s2)" font-size="8">A .55</text>
    <line x1="95" y1="115" x2="240" y2="160" stroke="var(--s1)"></line><text x="150" y="150" fill="var(--s1)" font-size="8">B .45</text>
    <circle cx="250" cy="60" r="5" fill="var(--s2)"></circle>
    <circle cx="250" cy="160" r="5" fill="var(--s1)"></circle>
    <line x1="255" y1="55" x2="420" y2="35" stroke="var(--muted)"></line><text x="330" y="34" fill="var(--muted)" font-size="8">A1 .5</text>
    <line x1="255" y1="65" x2="420" y2="85" stroke="var(--muted)"></line><text x="330" y="86" fill="var(--muted)" font-size="8">A2 .5</text>
    <line x1="255" y1="155" x2="420" y2="135" stroke="var(--s1)"></line><text x="330" y="132" fill="var(--s1)" font-size="8">B1 .95</text>
    <line x1="255" y1="165" x2="420" y2="185" stroke="var(--muted)"></line><text x="330" y="188" fill="var(--muted)" font-size="8">B2 .05</text>
    <text x="440" y="39" fill="var(--muted)" font-size="8">A-A1 = 0.275</text>
    <text x="440" y="89" fill="var(--muted)" font-size="8">A-A2 = 0.275</text>
    <rect x="435" y="126" width="120" height="16" fill="var(--acc-soft)"></rect><text x="440" y="138" fill="var(--acc-ink)" font-size="8">B-B1 = 0.4275 ★</text>
    <text x="440" y="189" fill="var(--muted)" font-size="8">B-B2 = 0.0225</text>
    <text x="70" y="210" fill="var(--muted)" font-size="8">greedy walks the fat first edge (A) into a thin continuation; the star is the real best</text>
  </g>
</svg>
^ The best full sequence B-B1 (0.4275, starred) begins with the worse first token B (0.45), because B's 0.95 continuation more than makes up for it. Greedy takes the fatter first edge A and can only reach 0.275.

### Greedy walks into the trap

Greedy takes the argmax token each step and never reconsiders.

```
# beam.py:66-76 — COMPLETE (take the highest-probability token at each step; one hypothesis)
def greedy(tree):
    """Take the single highest-probability token at each step; never reconsider."""
    seq, prob, level = [], 1.0, tree
    while level:
        tok = min(level, key=lambda t: (-level[t]["p"], t))   # max prob, ties by smallest token
        seq.append(tok)
        prob *= level[tok]["p"]
        level = level[tok].get("next")
    return seq, prob
```

At the first step greedy sees A (0.55) and B (0.45) and takes A. That single choice has already doomed it — every sequence starting with A tops out at 0.275, and it cannot see that, because it threw B away. At the second step it takes the best A-continuation (0.5) and returns A-A1 at 0.275. It made the locally best choice twice and ended up with a sequence worth 65% of the best one.

<svg viewBox="0 0 700 170" role="img" aria-label="Two rankings side by side. Ordered by first-token probability, A is on top (0.55) and B below (0.45) — greedy's view. Ordered by total sequence probability, B-B1 is on top (0.4275) and the A sequences below (0.275). The top item differs between the two orderings.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">greedy sorts by the first column; the answer sorts by the last — they disagree at the top</text>
    <text x="60" y="44" fill="var(--s2)">by first-token p (greedy's view)</text>
    <rect x="60" y="52" width="200" height="22" fill="var(--s2)"></rect><text x="160" y="67" text-anchor="middle" fill="var(--panel)" font-size="8">A — 0.55  ← greedy picks</text>
    <rect x="60" y="78" width="200" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="160" y="93" text-anchor="middle" fill="var(--muted)" font-size="8">B — 0.45</text>
    <text x="410" y="44" fill="var(--s1)">by total sequence probability</text>
    <rect x="410" y="52" width="200" height="22" fill="var(--s1)"></rect><text x="510" y="67" text-anchor="middle" fill="var(--panel)" font-size="8">B-B1 — 0.4275  ★ best</text>
    <rect x="410" y="78" width="200" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="510" y="93" text-anchor="middle" fill="var(--muted)" font-size="8">A-A1 — 0.2750</text>
    <text x="160" y="126" text-anchor="middle" fill="var(--s2)" font-size="8">A on top</text><text x="510" y="126" text-anchor="middle" fill="var(--s1)" font-size="8">B on top</text>
    <text x="60" y="152" fill="var(--muted)" font-size="8">the highest first token and the highest full sequence are different rows — the whole trap</text>
  </g>
</svg>
^ Ranked by first-token probability, A wins and greedy commits to it; ranked by whole-sequence probability, B-B1 wins. The two orderings put different items on top, and greedy only ever sees the left one.

### Beam search keeps the loser alive

Beam search carries the top-k partial sequences, so B is not discarded at step one.

```
# beam.py:79-97 — COMPLETE (keep the top-k partials, expand all, prune to k each round)
def beam_search(tree, width):
    """Keep the top-`width` partial sequences at every step; expand and prune each round."""
    beams = [([tok], child["p"], child) for tok, child in tree.items()]
    beams = top(beams, width)
    while any(b[2].get("next") for b in beams):
        expanded = []
        for seq, prob, node in beams:
            nxt = node.get("next")
            if not nxt:
                expanded.append((seq, prob, node))          # a finished sequence rides along
            else:
                for tok, child in nxt.items():
                    expanded.append((seq + [tok], prob * child["p"], child))
        beams = top(expanded, width)
    return max(beams, key=lambda b: b[1])[:2]


def top(beams, width):
    return sorted(beams, key=lambda b: (-b[1], b[0]))[:width]
```

With width 2, after step one the beam holds both A (0.55) and B (0.45) — B survived. Step two expands both: A-A1 and A-A2 at 0.275, B-B1 at 0.4275, B-B2 at 0.0225. The top 2 are B-B1 and one of the A sequences, and the winner is B-B1. Run both decoders head to head:

```
# $ python3 beam.py --decode
#   greedy: A-A1         total 0.2750
#   beam:   B-B1         total 0.4275
```

run: 2026-08-27 · deterministic · `python3 beam.py --decode`

Greedy returns A-A1 at 0.275; beam returns B-B1 at 0.4275, the true maximum. Beam found a sequence 55% more probable than greedy's, purely by refusing to commit to the first token before seeing where it led. The extra cost is holding two hypotheses instead of one — width 2 instead of width 1.

**A sequence's probability is the product over all its steps, so the most probable sequence is not built from the most probable token at each step — greedy takes the local argmax and returns A-A1 at 0.275 while the true best B-B1 (0.4275) starts with a worse first token; beam search keeps the top-k partial hypotheses so the worse-looking token survives to reveal its strong continuation, and width 1 collapses back to greedy exactly.**

### The self-test

The `--check` mode plants the bug — greedy's single hypothesis — and proves it: greedy takes the local argmax first token, beam finds a more probable sequence, greedy's result is not the global best, beam's is, and beam width 1 reproduces greedy.

```
# $ python3 beam.py --check
#   greedy's first token is the local argmax = True (A, p=0.55)
#   beam's sequence is more probable than greedy's = True (0.4275 vs 0.2750)
#   greedy did NOT find the globally best sequence = True (greedy A-A1, best B-B1)
#   beam found the globally best sequence here = True
#   beam width 1 reproduces greedy = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 beam.py --check`

The `width1_is_greedy` line is the one that places the two decoders on a single spectrum: greedy is not a different algorithm from beam, it is beam with a width of one, the degenerate case that keeps a single hypothesis. Widening the beam is buying more hypotheses, and the greedy trap is what you pay for keeping only one. That framing matters because it tells you the fix has a dial, not a switch.

<svg viewBox="0 0 700 150" role="img" aria-label="A dial from beam width 1 to width 2. At width 1 the returned sequence is A-A1 with total 0.275, labeled greedy. At width 2 it is B-B1 with total 0.4275, labeled optimal here. Widening the beam by one recovers the best sequence.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">beam width is a dial, not a switch — width 1 is greedy</text>
    <rect x="110" y="50" width="150" height="46" fill="var(--panel)" stroke="var(--s2)"></rect><text x="185" y="70" text-anchor="middle" fill="var(--s2)" font-size="9">width 1</text><text x="185" y="86" text-anchor="middle" fill="var(--s2)" font-size="8">A-A1 · 0.275 (greedy)</text>
    <line x1="260" y1="73" x2="430" y2="73" stroke="var(--ink)"></line><text x="345" y="66" text-anchor="middle" fill="var(--muted)" font-size="8">+1 hypothesis</text>
    <rect x="430" y="50" width="160" height="46" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="510" y="70" text-anchor="middle" fill="var(--acc-ink)" font-size="9">width 2</text><text x="510" y="86" text-anchor="middle" fill="var(--acc-ink)" font-size="8">B-B1 · 0.4275 ★</text>
    <text x="110" y="126" fill="var(--muted)" font-size="8">one more hypothesis on the beam recovers the true best; keeping only one is the myopia</text>
  </g>
</svg>
^ Width 1 returns greedy's A-A1 (0.275); widening to width 2 returns the optimal B-B1 (0.4275). The fix is a continuous dial — how many hypotheses to carry — and greedy is just its narrowest setting.

```
# beam.py:140-145 — COMPLETE (beam beats greedy, and greedy misses the global best)
    beam_better = b_prob > g_prob
    print("  beam's sequence is more probable than greedy's = %s (%.4f vs %.4f)"
          % (beam_better, b_prob, g_prob))

    greedy_suboptimal = g_seq != best_seq
    print("  greedy did NOT find the globally best sequence = %s (greedy %s, best %s)"
          % (greedy_suboptimal, "-".join(g_seq), "-".join(best_seq)))
```

### The running tally

| sequence | first token p | total prob | greedy? | beam (w2)? | best? |
|---|---|---|---|---|---|
| B-B1 | 0.45 | 0.4275 | no | yes | yes |
| A-A1 | 0.55 | 0.2750 | yes | no | no |
| A-A2 | 0.55 | 0.2750 | no | no | no |
| B-B2 | 0.45 | 0.0225 | no | no | no |

Read the first-token-p column against the total-prob column: they disagree at the top. The sequence with the highest first-token probability (A, 0.55) is not the sequence with the highest total probability (B-B1, 0.4275). Greedy sorts by the first column one step at a time; the right answer sorts by the last column over whole sequences, and those two orderings put different sequences on top. Beam width 2 was just enough to keep the eventual winner in contention past the step where greedy dropped it — which is the general rule: you need a beam at least as wide as the number of deceptively-weak prefixes you must carry to reach the true best.

### What we did not settle

This is the greedy trap and beam's basic fix; decoding has more. Beam search maximizes total probability, and the most probable sequence is not always what you want — it tends toward short, generic, repetitive text, which is why open-ended generation usually prefers sampling (temperature and top-p, `sampling-inter-01`) over either greedy or beam. Longer sequences need length normalization, because raw probability products shrink with every step and unfairly favor short sequences. A wider beam is not monotonically better in practice — very wide beams can degrade output quality, a well-documented surprise. And beam still is not guaranteed optimal: a width-k beam can drop the true best if more than k weak prefixes must be carried, exactly as this tally hints. The invariant: the best token per step is not the best sequence, so any decoder that keeps a single hypothesis is myopic by construction.

## Build

The build in one paragraph: decode by keeping the top-k partial sequences, not one — expand every beam by a token each step, score candidates by their running total probability (a product of step probabilities, or a sum of log-probabilities), and prune back to k — so a strong sequence whose prefix looked weak is not discarded before its continuation redeems it; width 1 is greedy, and the trap is what one hypothesis costs. Add length normalization for long sequences, prefer sampling for open-ended generation where the most-probable sequence is bland, and remember a finite beam is still not guaranteed to find the global optimum.

We opened on the tree. The number that proves the trap is greedy's total against beam's:

```
# modules/below-the-prompt/code/beam-inter-01/ — COMPLETE, run from that directory
$ python3 beam.py --decode
  greedy: A-A1         total 0.2750
  beam:   B-B1         total 0.4275
```

Now build your own. Take a real short-horizon distribution (a model's top few tokens over two or three steps, or a synthetic tree) engineered so the best first token leads to weak continuations. Your number to beat is not speed; it is **the total probability of the greedy sequence versus the beam sequence** — beam should find a strictly more probable sequence, and beam width 1 should reproduce greedy exactly. Confirm greedy's pick is the local argmax that is not the global best. Bring back both decoders' totals. Good luck.

## Definition of done

- [ ] An enumeration of every full sequence's total probability
- [ ] A greedy decoder taking the argmax token each step
- [ ] A beam search keeping the top-k partial sequences
- [ ] A tree where the best first token leads to a worse full sequence
- [ ] Confirmation greedy takes the local argmax and misses the global best
- [ ] Confirmation beam finds a more probable sequence, and width 1 reproduces greedy
- [ ] `python3 beam.py --check` printing SELF-TEST PASS: greedy_local, beam_better, greedy_suboptimal, beam_optimal, w1=greedy
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why doesn't taking the highest-probability token at each step yield the highest-probability sequence?
2. On the tree, why does greedy choose A when the best sequence starts with B?
3. How does beam search keep the eventual winner alive past the step greedy drops it?
4. What is beam width 1, and why does it equal greedy?
5. Your own tree was decoded both ways. What total probability did greedy and beam return, and did beam win?

## External resources

- Any sequence-to-sequence or neural-machine-translation reference on beam search — my summary: the standard decoder, length normalization, and why beam width has diminishing and even negative returns; read it for the length-penalty and width tradeoffs this module leaves out.
- The "beam search curse" / neural text degeneration discussion (Holtzman et al.) — my summary: why maximizing probability produces bland, repetitive text and why sampling is preferred for open-ended generation; read it for when NOT to use beam or greedy.
- This hub, *sampling-inter-01* (temperature and top-p shape the softmax) — read it for the sampling decoders that trade maximum probability for diversity, the usual choice for open-ended generation.
