---
id: promptsens-inter-01
title: Average a model comparison over a set of prompt templates — a single fair template can crown either model
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A companion rule says both models in a head-to-head must run under the same prompt template, or you measure the setup instead of the model. That is necessary and not the end of the story: the single template you chose, fair as it is, is one arbitrary draw from the space of ways to phrase the task, and models do not score the same across that space. Option ordering, the exact instruction wording, whitespace, whether the answer is asked for as "Answer:" or "The answer is" — these formatting choices move scores by several points, and they move different models by different amounts. So a fair single-template comparison can still be an artifact of the template: under one wording model A looks better, under another equally reasonable wording model B looks better, both comparisons fair and opposite in conclusion. The fix is to treat the template as a nuisance variable and average over it — run the head-to-head under a set of templates and compare the models on their mean scores, so the template-to-template swing shows up as spread and you can see whether the average gap exceeds the noise template choice alone injects. On a fixture of four templates over 20 items, t1 favors A, t2 and t4 favor B, and t3 ties; the A-minus-B gap swings 7 items across templates while the true average gap is only 1 item in B's favor, so any single template can crown either model but the average ranks B first.
eli5: Imagine judging which of two chefs is better by having each cook the same dish — that part is fair. But if you only test one dish, you might pick the one dish that happens to suit chef A's style, and conclude A is better, when a different, equally fair dish would have shown B ahead. One dish tells you as much about your menu choice as about the chefs. The fix is to have them both cook several dishes and compare their averages, and to notice how much the result bounces around from dish to dish: if switching dishes swings the outcome more than the average difference between the chefs, then "who won" was really "which dish you picked," and only the average over many dishes tells you who is actually better.
---

## Why this module

A fair model comparison starts by holding the setup fixed: same items, same decoding settings, same prompt template for both models, so the only thing that differs is the model. A companion module makes that case — config parity — and it is right. Change the template between the two models and the score difference is contaminated by the setup difference.

This module is about the trap that remains after you have done that correctly. You picked one template, applied it fairly to both models, and got a result. But the template you picked is one of many equally reasonable ways to phrase the same task, and language models are notoriously sensitive to that phrasing. The same question with the options in a different order, or "Answer:" instead of "The answer is", or an extra blank line, can shift a model's score by several points — for reasons that have nothing to do with the capability you meant to measure.

The part that turns sensitivity into a wrong conclusion is that two models are sensitive differently. A formatting quirk that helps model A a little might hurt model B, so the gap between them depends on the template. Under one fair template A wins; under another fair template B wins. Report the one you happened to run and you have reported which template you picked as much as which model is better.

<svg role="img" aria-label="A funnel showing the space of equally-fair prompt templates as many small icons feeding into a choice, from which a single template is drawn. Two branches lead out: one template leads to A winning, another to B winning, showing the outcome depends on the draw." viewBox="0 0 440 140">
<text x="90" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">many equally-fair templates</text>
<rect x="30" y="30" width="18" height="12" fill="var(--panel)" stroke="var(--line)"/>
<rect x="52" y="30" width="18" height="12" fill="var(--panel)" stroke="var(--line)"/>
<rect x="74" y="30" width="18" height="12" fill="var(--panel)" stroke="var(--line)"/>
<rect x="96" y="30" width="18" height="12" fill="var(--panel)" stroke="var(--line)"/>
<rect x="41" y="46" width="18" height="12" fill="var(--panel)" stroke="var(--line)"/>
<rect x="63" y="46" width="18" height="12" fill="var(--panel)" stroke="var(--line)"/>
<rect x="85" y="46" width="18" height="12" fill="var(--panel)" stroke="var(--line)"/>
<text x="150" y="70" fill="var(--muted)" font-size="8">pick one</text>
<path d="M115 48 L 200 70" fill="none" stroke="var(--line)"/>
<rect x="200" y="60" width="40" height="16" fill="var(--panel)" stroke="var(--ink)"/>
<text x="220" y="72" fill="var(--ink)" font-size="8" text-anchor="middle">chosen</text>
<path d="M240 66 L 320 40" fill="none" stroke="var(--s1)"/>
<text x="360" y="40" fill="var(--s1)" font-size="8" text-anchor="middle">A wins</text>
<path d="M240 70 L 320 100" fill="none" stroke="var(--s2)"/>
<text x="360" y="104" fill="var(--s2)" font-size="8" text-anchor="middle">B wins</text>
</svg>
^ The winner depends on which fair template you happen to draw — the single-template report measures the draw as much as the models.

**Config parity makes each comparison fair by holding the template fixed for both models; it does not make the comparison robust, because the single template is one arbitrary draw and models are sensitive to phrasing differently, so a fair template can still decide the winner.**

## Concepts

Think of the prompt template as a nuisance variable — something that affects the measurement but is not what you are trying to measure, like the particular thermometer you grabbed. With one thermometer you get one reading and no idea how much it depends on the instrument. The fix in measurement is the same everywhere: vary the nuisance variable deliberately and average over it, so its effect becomes visible as spread instead of hiding inside a single number.

For evals that means running the head-to-head under a set of templates, not one. Each template is still a fair comparison — both models on the identical wording — but now you have several fair comparisons, and you compare the models on their mean score across the set. Two things become visible that a single template hides: the average gap, which is your best estimate of the real difference, and the swing across templates, which tells you how much template choice alone moves the result.

<svg role="img" aria-label="Four templates t1 to t4, each with a pair of bars for model A and model B. In t1 A's bar is taller; in t2 B's is taller; in t3 they are equal; in t4 B's is clearly taller. The winner changes across the panels." viewBox="0 0 440 150">
<text x="20" y="14" fill="var(--muted)" font-size="9">each template: a fair A-vs-B pair; the winner changes</text>
<text x="50" y="130" fill="var(--muted)" font-size="8" text-anchor="middle">t1</text>
<rect x="34" y="60" width="12" height="55" fill="var(--s1)"/>
<rect x="50" y="72" width="12" height="43" fill="var(--s2)"/>
<text x="48" y="52" fill="var(--s1)" font-size="7" text-anchor="middle">A</text>
<text x="150" y="130" fill="var(--muted)" font-size="8" text-anchor="middle">t2</text>
<rect x="134" y="80" width="12" height="35" fill="var(--s1)"/>
<rect x="150" y="65" width="12" height="50" fill="var(--s2)"/>
<text x="162" y="57" fill="var(--s2)" font-size="7" text-anchor="middle">B</text>
<text x="250" y="130" fill="var(--muted)" font-size="8" text-anchor="middle">t3</text>
<rect x="234" y="68" width="12" height="47" fill="var(--s1)"/>
<rect x="250" y="68" width="12" height="47" fill="var(--s2)"/>
<text x="248" y="60" fill="var(--muted)" font-size="7" text-anchor="middle">tie</text>
<text x="350" y="130" fill="var(--muted)" font-size="8" text-anchor="middle">t4</text>
<rect x="334" y="75" width="12" height="40" fill="var(--s1)"/>
<rect x="350" y="55" width="12" height="60" fill="var(--s2)"/>
<text x="362" y="47" fill="var(--s2)" font-size="7" text-anchor="middle">B</text>
</svg>
^ The same two models under four equally-fair templates: A wins t1, B wins t2 and t4, t3 ties — the winner is a property of the template, not just the models.

The decisive comparison is between the average gap and the swing. If the average gap is large relative to the swing, the ranking is about the models and a single template would have been roughly right. If the swing is as large as or larger than the average gap, the ranking is not stable — template choice moves the result more than the model difference does — and any single-template claim is a coin flip dressed as a measurement.

This is the same logic as reporting a mean with its variability, and the same logic as the module on seed variance, which averages over decoding seeds. The nuisance variable is different — prompt phrasing rather than the sampling seed — but the discipline is identical: a number you would quote as a result must be averaged over the incidental choices it should not depend on, and the spread over those choices is part of the result, not something to hide.

**Treat the template as a nuisance variable: run the head-to-head over a set of templates, compare the mean scores, and read the swing across templates as the noise template choice injects — a ranking is trustworthy only when the average gap clears that swing.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/promptsens-inter-01. The fixture is two models' scores on the same 20-item eval under four different but equally-fair prompt templates.

```json filename=modules/evals-and-statistics/code/promptsens-inter-01/promptsens.json:3-9 COMPLETE
  "n_items": 20,
  "templates": {
    "t1": {"a": 15, "b": 12},
    "t2": {"a": 11, "b": 14},
    "t3": {"a": 13, "b": 13},
    "t4": {"a": 12, "b": 16}
  }
```

Each template's result is the A-minus-B gap.

```python filename=modules/evals-and-statistics/code/promptsens-inter-01/promptsens.py:30-32 COMPLETE
def gaps(templates):
    """Per-template A-minus-B score gap (in items)."""
    return {name: t["a"] - t["b"] for name, t in templates.items()}
```

The winner of one template is just the sign of its gap.

```python filename=modules/evals-and-statistics/code/promptsens-inter-01/promptsens.py:35-41 COMPLETE
def winner(gap):
    """Who wins one template's fair head-to-head."""
    if gap > 0:
        return "A"
    if gap < 0:
        return "B"
    return "tie"
```

The swing is the spread of the per-template gap — how much the result moves on template choice alone.

```python filename=modules/evals-and-statistics/code/promptsens-inter-01/promptsens.py:52-55 COMPLETE
def swing(templates):
    """The spread of the per-template gap -- how much template choice alone moves the result."""
    gs = list(gaps(templates).values())
    return max(gs) - min(gs)
```

Before running it, predict: if the templates disagree, you will see A win some and B win others, and no single template can be trusted to name the better model. Run `--templates`:

```text filename=promptsens.py --templates
TEMPLATES — each a fair head-to-head (both models, same template)
----------------------------------------------------
  template   A    B    gap(A-B)   winner
  t1         15   12   +3         A
  t2         11   14   -3         B
  t3         13   13   +0         tie
  t4         12   16   -4         B
----------------------------------------------------
  the winner is not the same template to template; swing in the gap = 7 points
```

The prediction holds, and it is stark. Template t1 hands A a 3-item win; t2 hands B a 3-item win; t3 ties; t4 hands B a 4-item win. Four fair comparisons of the same two models, three different verdicts. The gap swings from +3 (A ahead) to −4 (B ahead) — a 7-item spread — purely from which fair wording you chose. Anyone who ran only t1 would report "A is better"; anyone who ran only t4 would report "B is better by a mile."

Now average over the templates. Run `--aggregate`:

```text filename=promptsens.py --aggregate
AGGREGATE — mean score across the 4 templates
----------------------------------------------------
  model A mean = 12.75 / 20
  model B mean = 13.75 / 20
  mean gap (A-B) = -1.00  ->  B is better on average
----------------------------------------------------
  averaging over templates gives one stable ranking; a single template does not
```

Averaged over the four templates, A scores 12.75 and B scores 13.75 — B is ahead by 1 item. That is the stable answer, and it exposes the real problem with the single-template reports: the swing (7 items) is seven times the average gap (1 item). Template choice moves the result far more than the models actually differ, so a single template's verdict is mostly noise, and even the sign of t1's result (+3 for A) is opposite the truth (B ahead). The average is small but consistent; the single templates are large and contradictory.

<svg role="img" aria-label="A number line of the A-minus-B gap from minus 5 to plus 5. Four template markers sit at plus 3, minus 3, 0, and minus 4, spread widely. A marker for the mean gap sits at minus 1, near the center. The wide spread of template markers is contrasted with the small mean." viewBox="0 0 440 130">
<line x1="40" y1="60" x2="410" y2="60" stroke="var(--line)"/>
<text x="40" y="78" fill="var(--muted)" font-size="8" text-anchor="middle">-5</text>
<text x="225" y="78" fill="var(--muted)" font-size="8" text-anchor="middle">0 (tie)</text>
<text x="410" y="78" fill="var(--muted)" font-size="8" text-anchor="middle">+5 (A)</text>
<circle cx="336" cy="60" r="4" fill="var(--s1)"/>
<text x="336" y="48" fill="var(--s1)" font-size="7" text-anchor="middle">t1 +3</text>
<circle cx="114" cy="60" r="4" fill="var(--s2)"/>
<text x="114" y="48" fill="var(--s2)" font-size="7" text-anchor="middle">t2 -3</text>
<circle cx="225" cy="60" r="4" fill="var(--muted)"/>
<text x="225" y="94" fill="var(--muted)" font-size="7" text-anchor="middle">t3 0</text>
<circle cx="77" cy="60" r="4" fill="var(--s2)"/>
<text x="77" y="48" fill="var(--s2)" font-size="7" text-anchor="middle">t4 -4</text>
<circle cx="188" cy="60" r="5" fill="var(--ink)"/>
<text x="188" y="94" fill="var(--ink)" font-size="7" text-anchor="middle">mean -1</text>
</svg>
^ The per-template gaps sprawl from +3 to −4 while the mean sits at just −1: the swing from template choice dwarfs the real difference, so a single template lands almost anywhere.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that both models win at least one template, that the template swing dwarfs the mean gap, that the average gives a definite ranking, that at least one template names the opposite winner from the average, and that a single-template comparison is therefore unreliable here.

```python filename=modules/evals-and-statistics/code/promptsens-inter-01/promptsens.py:96-108 COMPLETE
    both_models_win_some = "A" in winners and "B" in winners
    print("  both models win at least one template = %s (winners %s)" % (both_models_win_some, winners))

    swing_pts = swing(templates)
    swing_exceeds_mean_gap = swing_pts > abs(mean_gap)
    print("  the template swing dwarfs the mean gap = %s (%d vs %.2f)" % (swing_exceeds_mean_gap, swing_pts, abs(mean_gap)))

    average_favors_one = mean_gap != 0
    print("  the average gives a definite ranking = %s (mean gap %+.2f, %s ahead)" % (average_favors_one, mean_gap, "A" if mean_gap > 0 else "B"))

    avg_winner = "A" if mean_gap > 0 else "B"
    a_template_flips_sign = any(winner(v) not in ("tie", avg_winner) for v in g.values())
    print("  at least one template names the opposite winner from the average = %s" % a_template_flips_sign)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the templates ever stopped disagreeing or the swing ever shrank below the mean gap:

```text filename=promptsens.py --check
SELF-TEST — the per-template winner flips with the template and the swing dwarfs the mean gap; only the average gives a stable ranking
----------------------------------------------------------------------------------------------------------------
  both models win at least one template = True (winners ['A', 'B', 'tie', 'B'])
  the template swing dwarfs the mean gap = True (7 vs 1.00)
  the average gives a definite ranking = True (mean gap -1.00, B ahead)
  at least one template names the opposite winner from the average = True
  a single-template comparison is unreliable here = True
```

**The self-test does not merely check that the templates disagree; it checks that the swing exceeds the mean gap and that a template's winner contradicts the average — so a pass certifies template choice moves the result more than the models differ, which is exactly what makes a single-template report unreliable.**

## Definition of done

You can explain why config parity (same template for both models) is necessary but not sufficient for a robust comparison.
You can explain why prompt-format sensitivity plus differing sensitivity between models lets a fair single template decide the winner.
You can describe treating the template as a nuisance variable and averaging over a set of templates.
You can compare the average gap to the template swing and say when a ranking is trustworthy.
You can connect this to seed variance as the same discipline applied to a different incidental choice.

## Boss fight

Suppose you average over four templates and the mean gap is 1 item while the swing is 7. Reason about whether you should report "B is better." The honest answer is that you cannot yet, because the swing tells you the measurement is dominated by template noise: a mean of −1 with individual templates ranging from +3 to −4 is consistent with the two models being essentially tied, and four templates is far too few to pin a 1-item difference. The right move is to quantify it — treat the per-template gaps as your sample, compute a confidence interval for the mean gap across templates (a paired analysis, since each template scores both models), and report the interval, which here would comfortably straddle zero. The lesson generalizes the module: averaging over templates is step one; step two is putting an error bar on that average using the template-to-template variability, exactly as you would put an error bar on a metric using case-to-case variability.

Now the trap that makes prompt sensitivity worse than seed noise: it is not always mean-zero. Decoding-seed noise is symmetric — it does not systematically favor one model — so averaging over seeds mostly reduces variance. But prompt-format effects can be biased: if one model was trained or tuned on a particular answer format ("The answer is (B)") and your template set happens to over-represent that format, the average itself is skewed toward that model, not just noisier. So you cannot fix format sensitivity purely by adding more templates if the templates are drawn from a biased distribution; you must choose a template set that is representative of how the model will actually be prompted in deployment, and be suspicious when one model's advantage rides on formats that match its training. Representativeness of the template set, not just its size, is what makes the average meaningful.

**Averaging over templates is step one; step two is a confidence interval on the mean gap from the template-to-template spread, which here straddles zero — and because format effects can be biased toward a model's trained format, the template set must be representative of deployment, not merely large.**

## External resources

Sclar et al., "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" (2023), measures how much benchmark scores swing across trivial formatting changes and how the ranking of models depends on the template.
The HELM methodology and the lm-evaluation-harness documentation discuss prompt-template choice as a source of score variance and the case for reporting across formats.
The topic's own modules on config parity and on seed variance cover the neighboring disciplines — holding the template fixed for a fair comparison, and averaging over decoding seeds — that this one extends to averaging over the templates themselves.
