---
id: evals-inter-14
title: Macro-average an imbalanced eval — or a micro score hides a total failure on the rare class
topic: evals-and-statistics
level: intermediate
status: ready
time: 21 min
summary: When an eval set is imbalanced, how you average per-class performance decides what the number means. A micro average pools every example, so the majority class dominates and a model that fails the rare class still posts a high score. A macro average weights each class equally, so failing the rare class costs half the score. On 90 common and 10 rare examples, model X aces the common class (0.978) and fails the rare one (0.300): micro says 0.910, macro says 0.639. Against a balanced model Y, micro prefers X and macro prefers Y — the averaging flips the winner.
eli5: A restaurant gets rave reviews for its popular dish and terrible reviews for a rare one. If you average all the reviews together, the popular dish drowns out the rare one and the place looks great. If you first average each dish's reviews and then average those, the bad dish counts as much as the good one. Which average you pick changes who looks best.
---

## Why this module

One accuracy number from an imbalanced eval can mean two completely different things, and the common way of computing it hides exactly the failure you most need to see.

Eval sets are rarely balanced. Most examples are the common case and a handful are the rare one — a rare intent, an edge-case category, an underrepresented group. To report a single accuracy, you have to average across classes, and there are two ways to do it that give different answers. A micro average pools every example into one bucket and divides total correct by total examples, so each example counts equally. Because the common class contributes most of the examples, it contributes most of the score — the micro number is essentially the common-class accuracy with a small correction.

That is the trap. A model can ace the common class and completely botch the rare one, and its micro score barely moves, because the rare class is a rounding error in the pool. The single number looks excellent while the model fails the cases that were the whole reason you included a rare class in the eval. The metric is not lying — micro accuracy really is the fraction of examples classified correctly — but that fraction answers "how often is the model right on a random example," which on imbalanced data is dominated by the majority and says nothing about the minority.

A macro average fixes this by computing each class's accuracy separately and then averaging those per-class numbers, so each class counts equally regardless of how many examples it has. Now the rare class is worth exactly as much as the common one, and failing it costs half the score. The macro number answers a different and often more useful question: "how well does the model do on a typical class," which credits breadth across classes rather than volume within the majority. On imbalanced data, macro and micro can disagree sharply, and the disagreement is the signal that the model's performance is uneven.

The choice is not cosmetic, because the two averages can rank models in opposite orders. On the fixture, two models are scored on 90 common-class and 10 rare-class examples. Model X aces the common class (0.978) and fails the rare one (0.300); model Y is balanced (0.889 and 0.900). Micro scores them 0.910 and 0.890, so micro prefers X — the model that fails the rare class. Macro scores them 0.639 and 0.894, so macro prefers Y. Same data; the averaging flips the winner.

**Micro averaging pools examples so the majority class dominates and a rare-class failure is hidden; macro averaging weights each class equally so the failure shows — and on imbalanced data the two can crown different models, so reporting the wrong average selects the wrong model.**

## Concepts

The two averages answer different questions, and naming them precisely is most of the lesson. Micro accuracy is the probability that a uniformly random example is classified correctly — it weights each example equally, so classes contribute in proportion to their size. Macro accuracy is the average of the per-class accuracies — it weights each class equally, so a class contributes the same whether it has ten examples or ten thousand. Neither is universally right; they encode different values. If you genuinely care about aggregate example-level correctness (say, total user requests served), micro is appropriate. If you care that the model works across all classes including rare ones (fairness, coverage, safety on edge cases), macro is what you want. The error is not choosing one — it is reporting one while thinking it means the other.

On imbalanced data the gap between them is a direct read-out of how uneven the model is. Micro tracks the majority-class accuracy; macro pulls the minority-class accuracy up to equal weight. So micro-minus-macro grows exactly as the model's performance diverges across classes. A model with a large micro-macro gap is telling you it is carried by the majority class; a model with micro and macro close together performs evenly. This is why reporting both is good practice: their agreement or disagreement is itself informative, in a way that either number alone conceals. A single high micro number on imbalanced data should always prompt the question "and what is the macro?"

<svg role="img" aria-label="Micro pools 100 examples so the 90 common ones dominate; macro puts the two classes on an equal footing regardless of size" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">how each average weights the two classes</text>
  <text x="30" y="46" font-family="var(--mono)" font-size="9" fill="var(--s2)">micro: weight by examples</text>
  <rect x="30" y="52" width="324" height="24" fill="var(--acc-line)"/>
  <text x="120" y="68" font-family="var(--mono)" font-size="8" fill="var(--panel)">common (90%)</text>
  <rect x="354" y="52" width="36" height="24" fill="var(--s2)"/>
  <text x="356" y="68" font-family="var(--mono)" font-size="7" fill="var(--panel)">rare 10%</text>
  <text x="30" y="118" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">macro: weight by class</text>
  <rect x="30" y="124" width="180" height="24" fill="var(--acc-line)"/>
  <text x="90" y="140" font-family="var(--mono)" font-size="8" fill="var(--panel)">common 50%</text>
  <rect x="210" y="124" width="180" height="24" fill="var(--s1)"/>
  <text x="270" y="140" font-family="var(--mono)" font-size="8" fill="var(--panel)">rare 50%</text>
</svg>
^ Micro gives the rare class only its 10% share of the vote, so a rare-class failure barely dents the score; macro splits the vote 50/50, so the rare class can move the number as much as the common one.

The ranking flip follows from the same mechanics. A model that specializes in the majority class maximizes micro (most examples are majority) but tanks macro (it fails a whole class). A model that spreads its competence maximizes macro but may give up a little micro (it trades some majority accuracy for minority accuracy). So optimizing or selecting on micro pushes you toward majority-class specialists, and optimizing on macro pushes you toward balanced models. When those point at different models — as they do whenever the trade-off is real — the metric you report is the model you ship. Choosing the average is choosing the objective.

This generalizes beyond accuracy to any per-class metric — precision, recall, F1 all have micro and macro forms, and the same logic applies (micro-F1 is dominated by the frequent classes, macro-F1 gives voice to rare ones). There is also a weighted average in between (weight classes by size, which recovers something micro-like) and per-class reporting (skip the single number entirely and show every class), which is the most honest option when classes matter differently. The discipline is: on any imbalanced evaluation, never report a single pooled number without also reporting the macro or the per-class breakdown, because the pooled number structurally cannot show a minority-class failure.

**Micro answers "right on a random example" (majority-weighted) and macro answers "right on a typical class" (class-weighted); their gap measures how uneven the model is, and because a majority specialist wins micro while a balanced model wins macro, the average you report is the objective you select on.**

## Worked example

The fixture is two models' per-class correct-out-of-total on an imbalanced set.

```json filename=modules/evals-and-statistics/code/evals-inter-14/results.json:4-11 COMPLETE
    "model_X": {
      "common": {"correct": 88, "total": 90},
      "rare":   {"correct": 3,  "total": 10}
    },
    "model_Y": {
      "common": {"correct": 80, "total": 90},
      "rare":   {"correct": 9,  "total": 10}
    }
```

Ninety common-class examples, ten rare. Model X gets 88 of 90 common and 3 of 10 rare; model Y gets 80 of 90 common and 9 of 10 rare. Micro pools all examples; macro averages the two per-class accuracies.

```python filename=modules/evals-and-statistics/code/evals-inter-14/averaging.py:45-55 COMPLETE
def micro(model):
    """Pool all examples: total correct / total examples -- the majority class dominates."""
    correct = sum(model[c]["correct"] for c in model)
    total = sum(model[c]["total"] for c in model)
    return round(correct / total, 3)


def macro(model):
    """Average the per-class accuracies -- each class counts equally."""
    accs = class_acc(model)
    return round(sum(accs.values()) / len(accs), 3)
```

The spread — the gap between a model's best and worst class — is the balance measure the ranking hinges on.

```python filename=modules/evals-and-statistics/code/evals-inter-14/averaging.py:58-61 COMPLETE
def spread(model):
    """Gap between best and worst class accuracy -- how balanced the model is."""
    accs = list(class_acc(model).values())
    return round(max(accs) - min(accs), 3)
```

Predict: X's micro will sit near its common-class 0.978 (the pool is 90% common), so about 0.91, while its macro averages 0.978 and 0.300 to about 0.64. Y, being balanced, will have micro and macro close. Look at the scores.

```text filename=modules/evals-and-statistics/code/evals-inter-14/averaging.py --scores
SCORES — per-class accuracy, micro, and macro for each model
--------------------------------------------------------------
  model_X:  common 0.978   rare 0.300
      micro 0.910   macro 0.639
  model_Y:  common 0.889   rare 0.900
      micro 0.890   macro 0.894
--------------------------------------------------------------
  class sizes: {'common': 90, 'rare': 10}  (imbalanced)
```

Model X's micro is 0.910 — it looks like a strong model — but its rare-class accuracy is 0.300, a near-total failure that the micro number completely hides, because the 7 extra rare-class errors are swamped by 88 common-class correct. Its macro is 0.639, and the gap between 0.910 and 0.639 is the imbalance made visible. Model Y's micro (0.890) and macro (0.894) are nearly equal, the signature of a balanced model. Now rank them.

```text filename=modules/evals-and-statistics/code/evals-inter-14/averaging.py --rank
RANK — which model each averaging method prefers
--------------------------------------------------------------
  by micro:  model_X   (0.910 vs 0.890)
  by macro:  model_Y   (0.639 vs 0.894)
--------------------------------------------------------------
  micro and macro crown different models on the same data.
```

Micro prefers X, 0.910 to 0.890 — pick by micro and you ship the model that gets 30% of the rare class right. Macro prefers Y, 0.894 to 0.639 — pick by macro and you ship the balanced model. The same two models, the same eval data, and the ranking depends entirely on which average you report. If the rare class matters at all — and a rare class in an eval usually matters more per example, not less — micro is selecting the wrong model and hiding why.

<svg role="img" aria-label="Model X has a tall common-class bar and a short rare-class bar with micro near the top and macro pulled down; model Y has two equal bars with micro and macro together" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">per-class accuracy with micro (majority-weighted) and macro lines</text>
  <line x1="40" y1="170" x2="450" y2="170" stroke="var(--line)"/>
  <text x="90" y="34" font-family="var(--mono)" font-size="9" fill="var(--ink)">model X</text>
  <rect x="60" y="42" width="45" height="128" fill="var(--acc-line)"/>
  <text x="62" y="182" font-family="var(--mono)" font-size="7" fill="var(--muted)">common .98</text>
  <rect x="115" y="131" width="45" height="39" fill="var(--s2)"/>
  <text x="120" y="182" font-family="var(--mono)" font-size="7" fill="var(--muted)">rare .30</text>
  <line x1="55" y1="52" x2="165" y2="52" stroke="var(--ink)" stroke-dasharray="4 2"/>
  <text x="165" y="52" font-family="var(--mono)" font-size="7" fill="var(--ink)">micro .91</text>
  <line x1="55" y1="88" x2="165" y2="88" stroke="var(--s2)" stroke-width="2"/>
  <text x="165" y="90" font-family="var(--mono)" font-size="7" fill="var(--s2)">macro .64</text>
  <text x="320" y="34" font-family="var(--mono)" font-size="9" fill="var(--ink)">model Y</text>
  <rect x="290" y="55" width="45" height="115" fill="var(--acc-line)"/>
  <text x="292" y="182" font-family="var(--mono)" font-size="7" fill="var(--muted)">common .89</text>
  <rect x="345" y="53" width="45" height="117" fill="var(--s1)"/>
  <text x="350" y="182" font-family="var(--mono)" font-size="7" fill="var(--muted)">rare .90</text>
  <line x1="285" y1="56" x2="395" y2="56" stroke="var(--ink)" stroke-dasharray="4 2"/>
  <text x="396" y="58" font-family="var(--mono)" font-size="7" fill="var(--ink)">micro/macro .89</text>
</svg>
^ Model X's micro line rides up near the tall common bar while its macro line drops toward the short rare bar; model Y's two bars are equal, so its micro and macro coincide — the gap is the imbalance.

## Build

Reproduce the averages. Pure standard library, deterministic, so the 0.910/0.639 and 0.890/0.894 come out exactly.

Run `--scores` for the per-class and averaged numbers, `--rank` for the preference of each method, `--check` for the gate. The ranking-flip check compares the winner under each metric directly.

```python filename=modules/evals-and-statistics/code/evals-inter-14/averaging.py:110-112 COMPLETE
    ranking_flips = prefer(models, micro) != prefer(models, macro)
    print("  micro and macro prefer different models = %s (micro->%s, macro->%s)"
          % (ranking_flips, prefer(models, micro), prefer(models, macro)))
```

<svg role="img" aria-label="Under micro model X wins, under macro model Y wins: two crossing lines showing the ranking reversal" viewBox="0 0 470 160" width="470" height="160">
  <rect x="0" y="0" width="470" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">which model wins under each average (higher = preferred)</text>
  <text x="120" y="40" font-family="var(--mono)" font-size="9" fill="var(--muted)">by micro</text>
  <text x="320" y="40" font-family="var(--mono)" font-size="9" fill="var(--muted)">by macro</text>
  <line x1="140" y1="60" x2="340" y2="130" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="140" cy="60" r="5" fill="var(--s2)"/><circle cx="340" cy="130" r="5" fill="var(--s2)"/>
  <text x="96" y="58" font-family="var(--mono)" font-size="8" fill="var(--s2)">X .910</text>
  <text x="346" y="132" font-family="var(--mono)" font-size="8" fill="var(--s2)">X .639</text>
  <line x1="140" y1="72" x2="340" y2="66" stroke="var(--acc-line)" stroke-width="2"/>
  <circle cx="140" cy="72" r="5" fill="var(--acc-line)"/><circle cx="340" cy="66" r="5" fill="var(--acc-line)"/>
  <text x="96" y="86" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">Y .890</text>
  <text x="346" y="64" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">Y .894</text>
  <text x="150" y="150" font-family="var(--mono)" font-size="8" fill="var(--muted)">X on top by micro; Y on top by macro — the lines cross</text>
</svg>
^ X sits above Y under micro and Y sits above X under macro, so the lines cross — the winner is decided by the averaging choice, not by the data.

The self-test pins the hidden failure, the exposing gap, and the ranking flip.

```python filename=modules/evals-and-statistics/code/evals-inter-14/averaging.py:102-106 COMPLETE
    micro_hides_failure = micro(x) > 0.9 and class_acc(x)[rare] < 0.4
    print("  X's micro is high while it fails the rare class = %s (micro %.3f, rare acc %.3f)"
          % (micro_hides_failure, micro(x), class_acc(x)[rare]))

    macro_reveals = micro(x) - macro(x) > 0.2
    print("  X's macro is far below its micro, exposing the imbalance = %s (%.3f vs %.3f)"
          % (macro_reveals, macro(x), micro(x)))
```

```text filename=modules/evals-and-statistics/code/evals-inter-14/averaging.py --check
SELF-TEST — micro hides X's rare-class failure and prefers X; macro reveals it and prefers the balanced Y
----------------------------------------------------------------------------------------------------------
  X's micro is high while it fails the rare class = True (micro 0.910, rare acc 0.300)
  X's macro is far below its micro, exposing the imbalance = True (0.639 vs 0.910)
  micro and macro prefer different models = True (micro->model_X, macro->model_Y)
  the macro-preferred model is the more balanced one = True (spread 0.011 vs 0.678)
  X's micro tracks its best (majority) class, not its worst = True
----------------------------------------------------------------------------------------------------------
SELF-TEST PASS  micro_hides_failure=True  macro_reveals=True  ranking_flips=True  macro_prefers_balanced=True  micro_tracks_majority=True
```

Five True flags. Micro_hides_failure: X's micro is 0.910 while it gets 0.300 on the rare class. Macro_reveals: X's macro of 0.639 is 0.271 below its micro, exposing the imbalance. Ranking_flips: micro prefers X, macro prefers Y. Macro_prefers_balanced: the macro-winner Y has a per-class spread of 0.011 versus X's 0.678 — macro rewards evenness. Micro_tracks_majority: X's micro sits within 0.1 of its best class, confirming the pool follows the majority. The ranking-flip flag is the one with teeth: it means the reported average is not a detail but the deciding vote.

**The ranking-flip flag is the whole stakes — micro and macro name different models as best on identical data, so the averaging choice is not presentation but model selection, and micro's choice is the one that fails the rare class.**

## Definition of done

You are done when you reproduce the flip and can explain what each average measures.

Concretely: `--scores` shows X at micro 0.910 / macro 0.639 with a rare-class 0.300, and Y balanced at 0.890 / 0.894; `--rank` shows micro preferring X and macro preferring Y; `--check` prints PASS with five True flags including spreads 0.678 versus 0.011. You can state that micro weights examples equally (majority-dominated) and macro weights classes equally, that their gap measures class-level unevenness, and that a majority specialist wins micro while a balanced model wins macro so the reported average selects the model. You can name the alternatives — weighted average and per-class reporting — and when each is appropriate.

The habit to carry: on any imbalanced eval, never report a single pooled (micro) number alone — report macro or the full per-class breakdown alongside it, and choose the headline average to match whether you care about example-level volume or class-level coverage. When a model shows a high overall score but users report it failing on a specific category, suspect a micro average hiding a minority-class collapse, and look at the per-class numbers.

## Boss fight

The instructive failure is a classifier that ships at "94% accurate" and fails every request from a rare but important category.

A support-ticket classifier is evaluated at 94% accuracy and shipped. In production, the rare "billing dispute" category — 3% of tickets but high-stakes — is misrouted almost every time, and complaints pile up. The 94% was a micro average dominated by the two huge common categories; the billing class, at 3% of examples, could be 20% accurate without moving the headline number below 94%. The eval never surfaced the failure because it reported only the pooled score. The fix is to report macro accuracy (or per-class recall) so the billing class counts equally, which would have shown a macro in the 60s and flagged the problem before launch; the deeper fix is to select the model on the metric that matches the stakes, weighting rare-but-important classes at least as heavily as common ones.

Your turn, two moves. First, find the breaking imbalance. Hold the per-class accuracies fixed and shrink the rare class from 10 examples toward 1, watching X's micro climb toward its common-class 0.978 while its macro stays at 0.639 — the more imbalanced the set, the more micro hides and the larger the micro-macro gap. Second, add a third, medium-frequency class and compute a size-weighted average alongside micro and macro; confirm the weighted average lands between them and that only macro (or per-class) gives the rare class full voice — so the choice among micro, weighted, and macro is really a choice of how much the rare class is allowed to matter.

## External resources

Any machine-learning evaluation reference (scikit-learn's documentation on the `average` parameter for precision, recall, and F1) lays out micro, macro, and weighted averaging precisely, and its notes on imbalanced data make the same warning this module demonstrates.

Sokolova and Lapalme's "A systematic analysis of performance measures for classification tasks" (2009) formalizes how averaging choices interact with class imbalance and what each measure rewards.

The fairness literature on per-group evaluation (disaggregated metrics, "model cards") is the modern extension — it argues for reporting performance per subgroup rather than a single pooled number, which is macro averaging taken to its logical, most honest conclusion.
