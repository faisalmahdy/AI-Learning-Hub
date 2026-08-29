---
id: distill-inter-01
title: Distill from soft targets, not hard labels — the teacher's wrong-class probabilities are the lesson
topic: below-the-prompt
level: intermediate
status: ready
time: 5-8h
summary: A teacher model shown a cat does not output "cat" — it outputs a whole distribution, cat 0.70, dog 0.25, car 0.03, ship 0.02, and the hard label (the argmax) throws away everything but the winner, yet the rest is information: it says a cat looks a lot like a dog and nothing like a ship, and that this image was a somewhat uncertain cat. That is the teacher's dark knowledge, and distillation trains the student on the full soft distribution rather than the one-hot hard label because the soft target teaches the similarity structure the hard label deletes. The loss is exact: hard labels collapse every example sharing an argmax into the same one-hot target, so a confident cat and a barely-a-cat become identical signals and the second-choice class — what the image is confusable with — is erased. On the fixture three examples all hard-label "cat" but carry distinct soft distributions and different runner-up classes; hard labels collapse the three to one signal and drop 0.30, 0.10, and 0.50 of non-top probability mass, while soft targets preserve each example's uncertainty (entropy 1.12, 0.62, 1.46 bits) and its confusable class (dog, dog, car). Soft targets carry the teacher's whole read of the input; hard labels carry one bit of it.
eli5: When a smart teacher looks at a fuzzy photo, they don't just say "it's a cat." They say "it's probably a cat, could be a dog, definitely not a ship." That extra information — what it might be confused with, and how sure they are — is gold for a student learning from them. If you erase all that and only keep "cat," you've thrown away most of the lesson, and two very different photos that both got called "cat" now look identical to the student. Teaching from the full opinion, not just the final answer, is what distillation does.
---

## Why this module

Training a model to classify usually uses hard labels: this image is a cat, so the target is the one-hot vector [1, 0, 0, 0]. That is what the ground-truth dataset gives you, and it is correct — the image really is a cat. But when you already have a good model (a teacher) and want to train a smaller one (a student), you have access to something far richer than the hard label: the teacher's full output distribution over all the classes. For a particular cat photo the teacher might say cat 0.70, dog 0.25, car 0.03, ship 0.02, and that distribution contains information the hard label does not.

Look at what those numbers say. The teacher put a quarter of its probability on dog — it thinks this image looks quite a lot like a dog — and almost nothing on ship. That is real knowledge about the structure of the problem: it encodes that cats and dogs are visually similar and cats and ships are not, information the model learned from all its training that is now sitting right there in the wrong-class probabilities. Geoffrey Hinton named this the teacher's "dark knowledge," and the insight of distillation is that the student learns more, and faster, from these soft targets than from the hard labels, because the soft targets hand it the teacher's whole similarity map for free.

<svg viewBox="0 0 700 160" role="img" aria-label="A soft distribution being projected to a hard label. On the left, a four-bar distribution: cat 0.70, dog 0.25, car 0.03, ship 0.02. An arrow labeled argmax points to the right, where only a single one-hot bar for cat remains at 1.0 and the other three are zero. The discarded bars are marked as dark knowledge thrown away.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the hard label is a lossy projection: argmax keeps one bar, deletes the rest</text>
    <text x="40" y="44" fill="var(--muted)" font-size="8">soft target</text>
    <rect x="40" y="60" width="40" height="72" fill="var(--s1)"></rect><text x="60" y="146" text-anchor="middle" fill="var(--muted)" font-size="7">cat .70</text>
    <rect x="90" y="96" width="40" height="36" fill="var(--s2)"></rect><text x="110" y="146" text-anchor="middle" fill="var(--s2)" font-size="7">dog .25</text>
    <rect x="140" y="128" width="40" height="4" fill="var(--acc-line)"></rect><text x="160" y="146" text-anchor="middle" fill="var(--muted)" font-size="7">car .03</text>
    <rect x="190" y="129" width="40" height="3" fill="var(--muted)"></rect><text x="210" y="146" text-anchor="middle" fill="var(--muted)" font-size="7">ship</text>
    <text x="300" y="96" fill="var(--muted)" font-size="8">argmax →</text><text x="290" y="110" fill="var(--s2)" font-size="7">drops 0.30 mass</text>
    <text x="440" y="44" fill="var(--muted)" font-size="8">hard label</text>
    <rect x="440" y="30" width="40" height="102" fill="var(--muted)"></rect><text x="460" y="146" text-anchor="middle" fill="var(--muted)" font-size="7">cat 1.0</text>
    <rect x="490" y="129" width="40" height="3" fill="var(--panel)" stroke="var(--line)"></rect><rect x="540" y="129" width="40" height="3" fill="var(--panel)" stroke="var(--line)"></rect><rect x="590" y="129" width="40" height="3" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="560" y="120" text-anchor="middle" fill="var(--s2)" font-size="7">all zeroed</text>
  </g>
</svg>
^ The argmax keeps the cat bar and zeroes the other three, discarding the 0.30 of mass that said "somewhat dog, not at all ship." That discarded mass is the dark knowledge distillation trains on.

The hard label deletes all of it. Take the argmax and you keep only "cat" and zero out the 0.30 of probability the teacher spread across the other classes — including which class it was, the confusable one. Worse, hard labels are lossy in a way that collapses distinct examples: a confident cat (0.90 on cat) and a barely-a-cat (0.50 on cat, 0.40 on car) both have argmax cat, so both become the identical one-hot target, and the student can never learn that the second image was near a decision boundary. This module makes that loss exact — it computes the dark knowledge hard labels discard and the distinctions they collapse. Everything runs offline against a soft-targets fixture, stdlib Python 3, `$0.00`, with every quantity computed. The instinct to unlearn is that a label is the answer. For distillation, the answer is the whole distribution, and the wrong-class probabilities are where most of the teaching is.

## Concepts

Named here so you can find them again; each is built below.

- **Soft target** — the teacher's full probability distribution over classes for an example.
- **Hard label** — the one-hot argmax; all a soft target keeps if you collapse it.
- **Dark knowledge** — the probability mass on non-top classes; the similarity structure hard labels erase.
- **Runner-up** — the teacher's second choice; the class this input is confusable with.
- **Collapse** — distinct examples sharing an argmax reduced to one identical hard target.
- **Entropy** — the uncertainty in a soft target (bits); a hard label always reports zero.

## Worked example

Source: the target-construction step of distillation — turning a teacher's outputs into the signal a student trains on. The soft distributions stand in for a real teacher's per-example outputs; the classes are a small toy set so every quantity is exact.

Script and fixture: `modules/below-the-prompt/code/distill-inter-01/` — `distill.py`, and `targets.json`, four examples over four classes. Every command runs from there.

### Reading a soft target

Four small functions read the information a soft target carries and the hard label throws away.

```
# distill.py:43-63 — COMPLETE (hard label, runner-up, dark knowledge, entropy)
def hard_label(dist, classes):
    """The one-hot target: the single most probable class (all a hard label keeps)."""
    return classes[max(range(len(dist)), key=lambda i: dist[i])]


def runner_up(dist, classes):
    """The teacher's second choice -- the confusable class, dark knowledge a hard label erases."""
    order = sorted(range(len(dist)), key=lambda i: -dist[i])
    return classes[order[1]]


def dark_knowledge(dist):
    """Probability mass on the NON-top classes -- exactly what the hard label zeros out."""
    return round(1 - max(dist), 4)


def entropy(dist):
    """Uncertainty in the soft target (bits); a hard label always reports 0."""
    return round(-sum(p * math.log2(p) for p in dist if p > 0), 4)
```

`hard_label` keeps the argmax; the other three read what it discards — the second-choice class, the total non-top mass, and the uncertainty. Look at the four examples:

```
# $ python3 distill.py --targets
#   id    soft distribution              hard    runner-up  dark   entropy
#   e1    [0.7, 0.25, 0.03, 0.02]        cat     dog        0.3    1.1248
#   e2    [0.9, 0.05, 0.03, 0.02]        cat     dog        0.1    0.6175
#   e3    [0.5, 0.05, 0.4, 0.05]         cat     car        0.5    1.461
#   e4    [0.1, 0.1, 0.75, 0.05]         car     cat        0.25   1.1918
```

run: 2026-08-27 · deterministic; the teacher's soft distributions are a fixture · 4 examples · `python3 distill.py --targets`

The hard-label column is identical for e1, e2, and e3 — all "cat" — but the soft distributions could hardly be more different. e2 is a confident cat (0.90, dark knowledge only 0.10, low entropy 0.62). e1 is a softer cat that looks somewhat like a dog (0.70/0.25, dark 0.30). e3 is barely a cat at all — 0.50 cat but 0.40 car, dark knowledge 0.50, the highest entropy — an image on the edge between cat and car. The hard label calls all three "cat" and stops; the soft target tells you which one the teacher was sure about, and what each was confusable with.

<svg viewBox="0 0 700 210" role="img" aria-label="Three stacked bars for e1, e2, e3, all hard-labeled cat. Each bar is split into cat, dog, car, ship probability. e2 is almost all cat (confident). e1 is mostly cat with a quarter dog. e3 is half cat and 40% car. A single hard label cat sits beside all three, identical, ignoring the differences.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">three examples, all hard-labeled 'cat', very different soft targets</text>
    <text x="30" y="52" fill="var(--muted)" font-size="8">e2 (0.90)</text>
    <rect x="110" y="40" width="450" height="18" fill="var(--s1)"></rect><rect x="560" y="40" width="25" height="18" fill="var(--muted)"></rect><text x="600" y="53" fill="var(--muted)" font-size="7">confident</text>
    <text x="30" y="90" fill="var(--muted)" font-size="8">e1 (0.70)</text>
    <rect x="110" y="78" width="350" height="18" fill="var(--s1)"></rect><rect x="460" y="78" width="125" height="18" fill="var(--s2)"></rect><text x="600" y="91" fill="var(--s2)" font-size="7">~dog</text>
    <text x="30" y="128" fill="var(--muted)" font-size="8">e3 (0.50)</text>
    <rect x="110" y="116" width="250" height="18" fill="var(--s1)"></rect><rect x="360" y="116" width="200" height="18" fill="var(--acc-line)"></rect><text x="600" y="129" fill="var(--acc-ink)" font-size="7">~car</text>
    <text x="110" y="160" fill="var(--muted)" font-size="7">cat = filled · dog = grey · car = accent — the non-cat mass is the dark knowledge</text>
    <rect x="110" y="176" width="120" height="20" fill="var(--panel)" stroke="var(--line)"></rect><text x="170" y="190" text-anchor="middle" fill="var(--muted)" font-size="8">hard label: "cat"</text>
    <text x="245" y="190" fill="var(--s2)" font-size="8">← identical for all three, ignores every difference above</text>
  </g>
</svg>
^ e2, e1, and e3 all reduce to the one-hot "cat" target, yet their soft distributions range from a confident cat to a cat-or-car coin flip. The hard label is the same bar for all three; the soft target is the whole colored distribution.

### What the hard label collapses

The collapse is not a metaphor — it is a set of distinct examples mapped to one target.

```
# distill.py:66-72 — COMPLETE (examples sharing a hard label but differing in soft target)
def collapsed_groups(examples, classes):
    """Groups of examples that share a hard label but have DIFFERENT soft targets -- collapsed to one signal."""
    groups = {}
    for e in examples:
        groups.setdefault(hard_label(e["soft"], classes), []).append(e)
    return {label: es for label, es in groups.items()
            if len(es) > 1 and len({tuple(e["soft"]) for e in es}) > 1}
```

Run it:

```
# $ python3 distill.py --loss
#   hard label cat    collapses ['e1', 'e2', 'e3'] into ONE identical target
#      e1    soft [0.7, 0.25, 0.03, 0.02]  (dark knowledge 0.30, runner-up dog)
#      e2    soft [0.9, 0.05, 0.03, 0.02]  (dark knowledge 0.10, runner-up dog)
#      e3    soft [0.5, 0.05, 0.4, 0.05]  (dark knowledge 0.50, runner-up car)
```

run: 2026-08-27 · deterministic · `python3 distill.py --loss`

Three distinct training signals become one. A student trained on hard labels sees the same target [1, 0, 0, 0] for the confident cat, the doggish cat, and the cat-or-car — it has no way to learn that e3 was ambiguous or that e3's confusion was with car while e1's was with dog. A student trained on soft targets sees three different distributions and learns exactly those distinctions: the shape of the teacher's uncertainty and the geometry of the classes. That extra structure is why a distilled student can match a teacher far larger than the hard labels alone would allow.

**A teacher's soft distribution carries dark knowledge — the probability mass on non-top classes, encoding which classes an input is confusable with and how uncertain the teacher was — that the hard-label argmax deletes; three examples all argmax "cat" collapse to one identical one-hot target under hard labels while their soft targets keep 0.30, 0.10, and 0.50 of non-top mass and distinct runner-ups (dog, dog, car), so distillation trains on the soft distribution to teach the similarity structure the label erases.**

### The self-test

The `--check` mode confirms the loss: hard labels collapse same-argmax examples, every soft target carries dark knowledge, the confusable runner-up is recoverable from soft but not hard, and soft targets preserve uncertainty.

```
# $ python3 distill.py --check
#   hard labels collapse distinct examples sharing an argmax = True (3 examples into 1 labels)
#   every soft target carries dark knowledge (non-top mass > 0) = True
#   the confusable runner-up class is recoverable from soft, not hard = True
#   soft targets preserve uncertainty (entropy > 0) where hard labels report 0 = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 distill.py --check`

The collapse is counted directly — how many distinct examples got mapped onto how few labels:

```
# distill.py:112-116 — COMPLETE (count the distinct examples hard labels collapse onto shared argmaxes)
    groups = collapsed_groups(examples, classes)
    collapses = len(groups) > 0 and any(len(es) >= 2 for es in groups.values())
    total_collapsed = sum(len(es) for es in groups.values())
    print("  hard labels collapse distinct examples sharing an argmax = %s (%d examples into %d labels)"
          % (collapses, total_collapsed, len(groups)))
```

<svg viewBox="0 0 700 160" role="img" aria-label="Dark-knowledge mass discarded per example as bars. e1 0.30, e2 0.10, e3 0.50, e4 0.25. Every bar is above zero, showing hard labels always throw something away, most for e3 the ambiguous cat-or-car.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">dark-knowledge mass the hard label discards, per example (never zero)</text>
    <line x1="60" y1="130" x2="660" y2="130" stroke="var(--line)"></line>
    <rect x="110" y="70" width="70" height="60" fill="var(--s2)"></rect><text x="145" y="64" text-anchor="middle" fill="var(--s2)" font-size="8">0.30</text><text x="145" y="146" text-anchor="middle" fill="var(--muted)" font-size="7">e1 cat~dog</text>
    <rect x="250" y="110" width="70" height="20" fill="var(--s2)"></rect><text x="285" y="104" text-anchor="middle" fill="var(--s2)" font-size="8">0.10</text><text x="285" y="146" text-anchor="middle" fill="var(--muted)" font-size="7">e2 sure cat</text>
    <rect x="390" y="30" width="70" height="100" fill="var(--s2)"></rect><text x="425" y="24" text-anchor="middle" fill="var(--s2)" font-size="8">0.50</text><text x="425" y="146" text-anchor="middle" fill="var(--muted)" font-size="7">e3 cat~car</text>
    <rect x="530" y="80" width="70" height="50" fill="var(--muted)"></rect><text x="565" y="74" text-anchor="middle" fill="var(--muted)" font-size="8">0.25</text><text x="565" y="146" text-anchor="middle" fill="var(--muted)" font-size="7">e4 car</text>
  </g>
</svg>
^ Every example has a nonzero bar — the hard label always discards something — and the discard is largest for the ambiguous e3 (0.50), exactly the example whose uncertainty was most worth teaching.

The `collapses` line quantifies the information loss (three examples into one label) and the `has_dark` and `soft_recovers_runnerup` lines name what is lost (the mass, the confusable class). Together they are the argument for distillation in four assertions: the hard label is not just a coarser version of the soft target, it is a lossy projection that erases exactly the structure — similarity and uncertainty — that a student most needs to learn efficiently.

```
# distill.py:118-122 — COMPLETE (dark knowledge is nonzero; the runner-up differs from the argmax)
    has_dark = all(dark_knowledge(e["soft"]) > 0 for e in examples)
    print("  every soft target carries dark knowledge (non-top mass > 0) = %s" % has_dark)

    # the runner-up (confusable class) is recoverable from soft, but a hard label gives only the argmax
    soft_recovers_runnerup = all(runner_up(e["soft"], classes) != hard_label(e["soft"], classes) for e in examples)
```

### The running tally

| example | soft (cat,dog,car,ship) | hard | runner-up | dark knowledge | entropy |
|---|---|---|---|---|---|
| e1 | 0.70, 0.25, 0.03, 0.02 | cat | dog | 0.30 | 1.12 |
| e2 | 0.90, 0.05, 0.03, 0.02 | cat | dog | 0.10 | 0.62 |
| e3 | 0.50, 0.05, 0.40, 0.05 | cat | car | 0.50 | 1.46 |
| e4 | 0.10, 0.10, 0.75, 0.05 | car | cat | 0.25 | 1.19 |

Read the hard column against everything to its right: three "cat" rows, but the runner-up, dark-knowledge, and entropy columns are all different across them. Every one of those differences is information the teacher computed and the hard label throws in the bin. The dark-knowledge column is the size of what is thrown away per example — 0.30, 0.10, 0.50 — and it is never zero, so there is always something the soft target carries that the label does not. Distillation is, in one sentence, training on the columns to the right instead of the one column on the left.

### What we did not settle

This is why soft targets carry more than hard labels; the full distillation recipe adds mechanics. Temperature is the key one: the teacher's raw distribution is often very peaked (0.99 on the top class), so distillation divides the logits by a temperature T > 1 before softmax, which flattens the distribution and amplifies the small non-top probabilities — turning up the volume on the dark knowledge so the student can hear it. The student's loss is typically a blend of the soft-target (KL to the teacher) and the hard-label cross-entropy, so it learns from both the teacher and the ground truth. Distillation extends beyond classification to matching a teacher's token distributions in language models, which is how many small deployable models are trained from large ones. And the teacher can be wrong, so its dark knowledge is only as good as the teacher. The invariant: the argmax is a lossy projection of the teacher's output, and distillation trains on the projection's source.

## Build

The build in one paragraph: to distill a student from a teacher, train it on the teacher's full soft output distribution rather than the hard argmax label, because the non-top probabilities (the dark knowledge) encode the class-similarity structure and per-example uncertainty that the argmax erases and that a student learns from efficiently. Soften the teacher's distribution with a temperature above 1 to amplify the small probabilities, blend the soft-target loss with the ordinary hard-label loss so the student also uses the ground truth, extend the same idea to matching token distributions for language models, and remember the dark knowledge is only as trustworthy as the teacher.

We opened on the soft targets. The number that proves the loss is the dark knowledge hard labels discard:

```
# modules/below-the-prompt/code/distill-inter-01/ — COMPLETE, run from that directory
$ python3 distill.py --loss
  hard label cat    collapses ['e1', 'e2', 'e3'] into ONE identical target
```

Now build your own. Take a teacher's soft outputs on a batch (any classifier's probabilities), and for each example compute the hard label, the runner-up, the dark-knowledge mass, and the entropy. Your number to beat is not accuracy; it is **how many distinct examples your hard labels collapse and how much dark-knowledge mass they discard** — soft targets should keep distinctions and mass the argmax deletes. Confirm same-argmax examples carry different soft targets. Bring back the collapsed groups and the discarded mass. Good luck.

## Definition of done

- [ ] Functions for hard label, runner-up, dark-knowledge mass, and entropy of a soft target
- [ ] A detector for examples sharing a hard label but differing in soft target
- [ ] Confirmation hard labels collapse distinct same-argmax examples into one target
- [ ] Confirmation every soft target carries nonzero dark knowledge
- [ ] Confirmation the confusable runner-up is recoverable from soft but not hard
- [ ] Confirmation soft targets preserve uncertainty (entropy) that hard labels report as zero
- [ ] `python3 distill.py --check` printing SELF-TEST PASS: collapses, has_dark, soft_recovers_runnerup, soft_has_entropy
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What is "dark knowledge," and where in a teacher's output does it live?
2. Why do a confident cat and a barely-a-cat become identical training signals under hard labels?
3. What does the runner-up class tell you that the hard label cannot?
4. Why does distillation use a temperature above 1 on the teacher's logits?
5. Your own teacher's outputs were analyzed. How many examples did the hard labels collapse, and how much dark-knowledge mass was discarded?

## External resources

- Hinton, Vinyals & Dean, *Distilling the Knowledge in a Neural Network* — my summary: the paper that named dark knowledge and introduced temperature-scaled soft-target distillation; read it for the temperature and combined-loss mechanics this module leaves out.
- Any tutorial on knowledge distillation loss (KL to teacher plus cross-entropy to labels) — my summary: how the student's objective blends the soft and hard targets; read it for the exact loss you would train with.
- This hub, *softmax-inter-01* (subtract the max before exp) and *sampling-inter-01* (temperature shapes the softmax) — read them for the softmax the teacher's distribution comes from and the temperature that amplifies its dark knowledge.
