---
id: govern-inter-02
title: Do councils help? Only when the voters fail independently
topic: orchestration-and-governance
level: intermediate
status: ready
time: 8-10h
summary: Run a three-model council on two eval sets and the majority vote beats the best single model by +0.10 on one and loses to it by 0.10 on the other — same council, opposite verdicts. The difference is error independence: when the models fail on different items the majority cancels their mistakes, but when they share a blind spot the two weaker models outvote the strong one into the shared error, and a single error-overlap number (0.12 vs 0.54) predicts which regime you are in before you score a thing.
eli5: Ask three friends and take the majority — great if they think for themselves, useless if they all read the same wrong newspaper, because then three votes is just one wrong answer repeated. Check how often they're wrong about the same things before you trust the vote.
---

## Why this module

The labs use councils — several models deliberate, the majority or a synthesizer decides — across multiple systems: a 25-pole council in one, a cross-vendor four-round protocol in another. And the scan's verdict is that the method is "used but never validated against outcomes." Council is an intuition — three heads beat one — deployed on faith. This module puts it on a scale, and the answer is not the reassuring one. A council sometimes beats a single strong pass and sometimes loses to it, and whether it helps is not about how many models you add; it is about whether their mistakes are independent.

The intuition has a name and a proof — Condorcet's jury theorem — and it has fine print that the intuition drops: the voters must err *independently*. Language models are the worst case for that assumption. They share training data, architectures, and the internet's biases, so they tend to be wrong about the *same* things — and when voters share a blind spot, a majority vote does not cancel the error, it ratifies it. Worse, a council of one strong model and two correlated weak ones lets the weak pair outvote the strong one exactly where they share a mistake, so the council scores *below* the strong model you already had.

You need the evals track's habit of measuring instead of assuming. Everything runs offline against two vote fixtures, stdlib Python 3, `$0.00`. The one instinct to unlearn is that more voters is more accuracy. It is only more accuracy under a condition you have to check, and this module builds the check.

Here is the same council on two eval sets:

```
# modules/orchestration-and-governance/code/govern-inter-02/ — COMPLETE, run from that directory
$ python3 council.py --compare

COUNCIL vs BEST SINGLE — does the vote help?
------------------------------------------------------------------
  scenario      best single       council   delta    error-overlap
  independent   m1    0.70       0.80    +0.10    0.12  (helps)
  correlated    m1    0.80       0.70    -0.10    0.54  (hurts)
```

run: 2026-08-25 · deterministic; votes are a fixture · n=10 items, 3 models per scenario · `python3 council.py --compare`

Same voting rule, opposite verdicts. On the independent set the council lifts accuracy 10 points over the best single model; on the correlated set it *drops* 10 points below it. The last column is the tell — error overlap 0.12 versus 0.54 — and it predicts the verdict before you score the council at all. This module is those two rows and the statistic that separates them.

## Concepts

Named here so you can find them again; each is built below.

- **Council** — several models vote on each item; the majority is the answer.
- **Best single** — the strongest individual model; the baseline a council must beat to be worth its cost.
- **Independent errors** — the models are wrong on different items; the regime where voting helps.
- **Correlated errors** — the models share a blind spot and fail the same items; the regime where voting fails.
- **Error overlap** — the fraction of shared wrong answers across model pairs; the statistic that predicts the verdict.
- **Condorcet's theorem** — majority voting improves accuracy, *if* voters err independently. The fine print.

## Worked example

Source: faisalmahdy/operator (a 25-pole council) and faisalmahdy/fm-llm-wikipedia (`council/`, a cross-vendor four-round deliberation); the scan records the council method as used but "never validated against outcomes." This module is the validation, on a controlled fixture where the answer is knowable.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-02/` — `council.py`, and `votes.json`, two scenarios of ten decisions voted by three models. Every command runs from there.

### The frame: a jury only helps if the jurors think for themselves

A jury of twelve is wiser than one juror only if the twelve reason independently. If all twelve read the same slanted newspaper and walked in with the same wrong impression, the jury is not twelve opinions — it is one opinion with eleven echoes, and its confident unanimous verdict is exactly as wrong as the newspaper. The size of the jury bought nothing, because the votes were not independent draws; they were copies.

That is the whole risk with a model council. When you add a second and third model that were trained on overlapping data, you are often not adding independent judges — you are adding jurors who read the same newspaper. On the items where the shared bias bites, all three vote the same wrong way, and the majority makes the shared error *official*. The question a council must answer before you trust it is not "how many models voted" but "how often are these models wrong about the same things", and that is a number you can measure.

### The council, and the baseline it must beat

The council's answer for an item is the majority vote; its accuracy is how often that majority matches the truth.

```
# council.py:39-46 — COMPLETE (the majority vote, with a fixed blind tie-break)
def majority(row):
    """The council's answer for one item: the label with the most votes (ties ->
    the alphabetically first, a fixed, blind tie-break)."""
    counts = {}
    for v in row:
        counts[v] = counts.get(v, 0) + 1
    top = max(counts.values())
    return sorted(k for k, c in counts.items() if c == top)[0]
```

Accuracy itself is just the fraction of items a set of votes gets right — the same measurement the evals track built, reused for every model and for the council.

```
# council.py:35-36 — COMPLETE (fraction of items a vote series gets right)
def accuracy(votes, truth):
    return sum(1 for v, t in zip(votes, truth) if v == t) / len(truth)
```

A council is only worth its extra cost if it beats the best single model — running three models and voting is three times the spend, so the bar is the strongest one alone.

```
# council.py:53-55 — COMPLETE (the baseline: the strongest single model)
def best_single(models, truth):
    """The strongest individual model -- the one-good-pass baseline a council must beat."""
    return max(((m, accuracy(v, truth)) for m, v in models.items()), key=lambda x: x[1])
```

### The independent regime: the vote cancels the errors

In the first scenario the three models are each 70% accurate and fail on mostly *different* items. Watch what the majority does: an item is only wrong if at least two models are wrong on it, and if their errors are spread out, almost no item collects two. The council reaches 0.80, a clean 10 points over any single model — Condorcet working as advertised.

<svg viewBox="0 0 700 170" role="img" aria-label="Independent errors: three models each fail on different items, shown as non-overlapping red spans across ten items. The majority is wrong only where two spans overlap, which is rare, so the council beats each model.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">independent: each model's errors (red) fall on different items</text>
    <g>
      <text x="20" y="45" fill="var(--ink)">m1</text>
      <rect x="60" y="34" width="174" height="14" fill="var(--s2)"></rect><rect x="234" y="34" width="406" height="14" fill="var(--s1)" opacity="0.3"></rect>
      <text x="20" y="70" fill="var(--ink)">m2</text>
      <rect x="60" y="59" width="116" height="14" fill="var(--s1)" opacity="0.3"></rect><rect x="176" y="59" width="174" height="14" fill="var(--s2)"></rect><rect x="350" y="59" width="290" height="14" fill="var(--s1)" opacity="0.3"></rect>
      <text x="20" y="95" fill="var(--ink)">m3</text>
      <rect x="60" y="84" width="232" height="14" fill="var(--s1)" opacity="0.3"></rect><rect x="292" y="84" width="174" height="14" fill="var(--s2)"></rect><rect x="466" y="84" width="174" height="14" fill="var(--s1)" opacity="0.3"></rect>
      <text x="20" y="125" fill="var(--s1)">council</text>
      <rect x="60" y="114" width="116" height="14" fill="var(--s1)" opacity="0.3"></rect><rect x="176" y="114" width="58" height="14" fill="var(--s2)"></rect><rect x="234" y="114" width="58" height="14" fill="var(--s1)" opacity="0.3"></rect><rect x="292" y="114" width="58" height="14" fill="var(--s2)"></rect><rect x="350" y="114" width="290" height="14" fill="var(--s1)" opacity="0.3"></rect>
    </g>
    <text x="20" y="150" fill="var(--muted)">each model 0.70; council 0.80 — the majority erases the isolated errors</text>
  </g>
</svg>
^ Independent errors barely overlap, so almost no item has a majority wrong, and the council clears each model. This is the case the "three heads beat one" intuition assumes — and it is the case that does not describe correlated language models.

### The correlated regime: the vote ratifies the shared error

The second scenario is the realistic one. Now `m1` is the strong model at 0.80, and the two weaker models at 0.60 share `m1`'s early blind spot *and add their own*. Look at the per-item votes:

```
# $ python3 council.py --scenario correlated
#   item     truth   m1    m2    m3     council
#   1        A       B     B     B      B
#   2        A       B     B     B      B
#   3        A       A     B     B      B
#   ...
#   m1       accuracy 0.80
#   council  accuracy 0.70
```

run: 2026-08-25 · fixture · `python3 council.py --scenario correlated`

Item 3 is the whole lesson in one row. The strong model `m1` gets it right — votes `A` — and the two weaker models, sharing a blind spot, both vote `B`. The majority is `B`. The council took the strong model's correct answer and *overruled it* with two correlated wrong ones. Across the set that happens enough that the council lands at 0.70, a full 10 points *below* the strong model you would have if you had never convened the council. Adding voters did not add wisdom; it added two echoes of a mistake, and the echoes won.

<svg viewBox="0 0 700 150" role="img" aria-label="Item 3 in the correlated scenario: the strong model m1 votes A (correct), the two weaker models m2 and m3 vote B (wrong, sharing a blind spot), and the majority is B, overriding the correct answer.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">item 3, correlated scenario — the majority overrides the strong model</text>
    <text x="60" y="55" fill="var(--ink)">m1 (strong)</text><rect x="200" y="42" width="60" height="18" rx="3" fill="var(--s1)"></rect><text x="210" y="55" fill="var(--panel)">A ok</text>
    <text x="60" y="82" fill="var(--ink)">m2 (weak)</text><rect x="200" y="69" width="60" height="18" rx="3" fill="var(--s2)"></rect><text x="210" y="82" fill="var(--panel)">B x</text>
    <text x="60" y="109" fill="var(--ink)">m3 (weak)</text><rect x="200" y="96" width="60" height="18" rx="3" fill="var(--s2)"></rect><text x="210" y="109" fill="var(--panel)">B x</text>
    <text x="320" y="82" fill="var(--muted)">2 vs 1 -></text>
    <rect x="420" y="69" width="200" height="24" rx="4" fill="var(--panel)" stroke="var(--s2)"></rect><text x="430" y="86" fill="var(--s2)">council = B (WRONG)</text>
    <text x="20" y="140" fill="var(--muted)">two correlated errors outvote one correct answer: the council is worse than m1 alone.</text>
  </g>
</svg>
^ The correlated failure in one item: the strong model is right, the two weak models share a wrong answer, and the majority ratifies it. This is why a council of unequal, correlated models can score below its best member.

### The statistic that predicts the verdict

You do not need to wait for the outcome to know which regime you are in — you can measure how often the models err together. Error overlap is the fraction of shared wrong answers across all model pairs.

```
# council.py:58-67 — COMPLETE (how often model pairs are wrong on the same item)
def error_overlap(models, truth):
    """Fraction of item-pairs of models that are wrong on the SAME item -- a proxy
    for error correlation. High overlap is the regime where councils fail."""
    names = list(models)
    wrong = {m: {i for i, (v, t) in enumerate(zip(models[m], truth)) if v != t} for m in names}
    shared = total = 0
    for a, b in combinations(names, 2):
        shared += len(wrong[a] & wrong[b])
        total += len(wrong[a] | wrong[b])
    return shared / total if total else 0.0
```

The independent scenario scores 0.12; the correlated one scores 0.54 — and those numbers rank the two scenarios exactly as the outcome does. Low overlap, the council helps; high overlap, it hurts. The self-test confirms the mechanism end to end:

```
# $ python3 council.py --check
#   council - best_single:  independent = +0.10   correlated = -0.10
#   council beats the best single when errors are independent = True
#   council loses to the best single when errors are correlated = True
#   error-overlap is higher in the correlated scenario = True (0.54 > 0.12)
#   the council overrode the strong model into a shared error = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · n=10 items · `python3 council.py --check`

**A council is not more voters, it is more *independent* voters — and when models share a blind spot, a majority vote makes the shared mistake official, so measure error overlap before you trust the vote over one strong pass.**

### The running tally

| scenario | best single | council | verdict | error overlap |
|---|---|---|---|---|
| independent | 0.70 | 0.80 | council helps (+0.10) | 0.12 |
| correlated | 0.80 | 0.70 | council hurts (−0.10) | 0.54 |

<svg viewBox="0 0 700 170" role="img" aria-label="Council minus best-single accuracy plotted against error overlap. At overlap 0.12 the council is +0.10 (helps); at overlap 0.54 the council is -0.10 (hurts). The council's benefit falls as error overlap rises, crossing zero in between.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">council benefit vs error overlap — the higher the overlap, the worse the vote</text>
    <line x1="70" y1="100" x2="640" y2="100" stroke="var(--grid)"></line>
    <text x="70" y="150" fill="var(--muted)">overlap 0.0</text><text x="580" y="150" fill="var(--muted)">overlap 0.6</text>
    <text x="20" y="55" fill="var(--muted)">+0.1</text><text x="20" y="150" fill="var(--muted)">-0.1</text>
    <text x="18" y="104" fill="var(--muted)">0</text>
    <circle cx="180" cy="55" r="5" fill="var(--s1)"></circle><text x="150" y="45" fill="var(--s1)">independent +0.10</text>
    <circle cx="580" cy="145" r="5" fill="var(--s2)"></circle><text x="470" y="140" fill="var(--s2)">correlated -0.10</text>
    <line x1="180" y1="55" x2="580" y2="145" stroke="var(--muted)" stroke-width="1.4" stroke-dasharray="4 3"></line>
    <circle cx="380" cy="100" r="3" fill="var(--muted)"></circle><text x="330" y="92" fill="var(--muted)" font-size="8">break-even</text>
  </g>
</svg>
^ The council's benefit over the best single model falls as error overlap rises, from +0.10 at low overlap to −0.10 at high overlap. The overlap number, measurable before you score the council, is what tells you which side of break-even you are on.

The voting rule never changed; only whether the voters shared their errors. The independent case is the one the intuition imagines and the correlated case is the one language models actually live in, which is why "we use a council" is a claim that needs a measurement attached, not a design you can trust by construction. And the fix when overlap is high is not "add more models" — more correlated models deepen the problem — it is to either diversify the voters until their errors decorrelate or drop the council and ship the one strong pass.

### What we did not settle

The fixture uses a clean binary decision and a hard majority, so the mechanism is stark. Real complications we skipped: a weighted or confidence-aware vote can partly rescue the correlated case by letting a confident strong model outweigh two hesitant weak ones — but only if the confidence is calibrated, which is its own eval; error overlap here is measured against ground truth you have on a labelled set, whereas in production you estimate it from agreement patterns without labels, which is noisier; and cross-*vendor* councils (a Claude, a Gemini, a GPT) decorrelate errors far more than three prompts of one model, which is exactly why the labs' four-round cross-vendor protocol is the more defensible council design — the diversity is the point, and this module is the argument for why. The dial here is who votes; the real lever is how independent they are.

## Build

The pipeline in one paragraph: score several models on the same labelled decisions; compute each model's accuracy, the majority-vote council's accuracy, and the error overlap across model pairs; deploy the council only when it beats the best single model, which happens only when error overlap is low; and when overlap is high, diversify the voters or ship the single strong pass. Never adopt a council on the three-heads intuition without the overlap number.

We opened on the two-scenario comparison. The verdict that matters:

```
# modules/orchestration-and-governance/code/govern-inter-02/ — COMPLETE, run from that directory
$ python3 council.py --compare
  correlated    best 0.80   council 0.70   -0.10  (hurts)
```

Now measure your own council. Score two or three real models on one labelled eval set, compute the council accuracy against the best single, and compute the error overlap. Your number to beat is the **best single model's accuracy** — a council that does not clear it is paying multiples for a downgrade. Build a correlated case (three prompts of the *same* model) and an independent one (three different vendors) and confirm the overlap number and the verdict move together. Bring back both accuracies and the overlap for each. Good luck.

## Definition of done

- [ ] Several models scored on the same labelled decisions, with per-model accuracy
- [ ] A majority-vote council and the best-single baseline it must beat
- [ ] Error overlap computed across model pairs as a correlation proxy
- [ ] Your own `votes.json` with an independent scenario and a correlated one
- [ ] The council-minus-best-single delta reported for each, so the verdict is measured
- [ ] `python3 council.py --check` printing SELF-TEST PASS: council helps independent, hurts correlated, overlap predicts, strong model overridden
- [ ] The two verdicts and the two overlap numbers recorded, with the deploy/skip decision
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. The same council beat the best model on one set and lost on another. Name the property of the voters that flips the verdict, and why more voters does not fix the losing case.
2. State Condorcet's fine print in one sentence, and why language models are the worst case for it.
3. In the correlated scenario, item 3 had the strong model right and the council wrong. Walk through the votes and explain the override.
4. What does error overlap measure, and how does its value predict whether a council will help before you score the council?
5. Your own run produced two overlap numbers and two verdicts. What were they, and did you deploy the council?

## External resources

- faisalmahdy/fm-llm-wikipedia — `council/` — my summary: a cross-vendor, four-round deliberation protocol with an explicit when-NOT-to-use section; read it for a council designed to decorrelate errors by construction, which is the defensible answer to this module's warning, and note it never measured the payoff — the gap this module fills.
- Condorcet / the jury theorem, modern treatment — https://plato.stanford.edu/entries/jury-theorems/ — my summary: the theorem that majority accuracy rises with voters, and the independence assumption it rests on; read it for the exact condition this module shows language models violate.
- This hub, *evals-inter-02* (calibrated judge) — modules/evals-and-statistics/evals-inter-02.md — my summary: measuring a judge's agreement before trusting it; read it for the same "validate the method against outcomes before deploying it" discipline, applied there to an LLM judge and here to a council.
