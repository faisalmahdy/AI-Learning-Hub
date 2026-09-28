---
id: configparity-inter-01
title: Hold the harness config fixed when comparing two models — a stingy output cap on one side truncates correct answers and erases a real winner
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A model comparison is supposed to isolate one variable — the model. Everything else in the harness (the prompt template, the decoding temperature, and above all the maximum output length) has to be identical for both, or the comparison stops measuring the model and starts measuring the difference in setup. This is the eval version of a controlled experiment: change one thing at a time or you cannot attribute the result. The output-length cap is the sneakiest of these to get wrong, because it does not corrupt an answer visibly — it truncates it, and a model that knew the answer but was cut off mid-response scores exactly like a model that did not know it. So if model B runs with a smaller max_tokens than model A, every item whose correct answer is longer than B's cap is scored against B as a failure, even on items B would have aced under A's cap; those lost points are a property of the config, not the model. Run the comparison that way and the reported gap is the true model gap plus the config penalty, and a genuinely better model can be dragged down to a tie. On a fixture where model B is truly better than A (it solves one harder item by skill), a matched config shows B winning by that item, while an unfair config that throttles B's max_tokens truncates that same item and reports a tie.
eli5: Imagine a spelling bee where two kids compete, but one kid is only allowed to say the first three letters of every word before the bell cuts them off. If a word is short, they're fine. But on the long words they get cut off mid-spelling and marked wrong — not because they didn't know the word, but because the rule stopped them from finishing. If that kid was actually the better speller, the unfair bell can drag them down to a tie with the other kid, and the judges announce "it was even" when it wasn't. To find out who is really the better speller, you have to give both kids the same amount of time to answer. Comparing two AI models is the same: if one is allowed to write a long answer and the other gets cut off early, you're testing the cutoff, not the models. Give both the same limits, change only the model, and then the winner is real.
---

## Why this module

The whole point of a head-to-head is to attribute a difference in score to a difference in model. That attribution is only valid if the model is the only thing that differed. The moment anything else about the harness changes between the two runs — the system prompt, the temperature, the retrieval context, the output-length cap — the score gap absorbs that change too, and you can no longer say the better-scoring model is the better model.

Most of these confounds are easy to spot because they corrupt the answer in a visible way. A wrong prompt produces obviously off-topic responses; a high temperature produces obviously erratic ones. The output-length cap is different: when it is too small, the model produces a correct answer and then gets cut off, and a truncated-correct answer is scored identically to a wrong one. The failure is silent, so it is easy to leave the caps mismatched and never notice.

That silence is what makes it dangerous in a comparison. If the two models happen to run with different caps — because they came from different vendors with different defaults, or because one was configured by a different person — the model with the smaller cap loses points on every long-answer item, and those losses are pure config. This module scores two models under a matched config and an unfair one and shows the winner flipping to a tie.

**A comparison is only about the model if the model is the only thing that changed — and a mismatched output cap silently truncates correct answers, folding a config penalty into the score gap.**

## Concepts

The controlled-experiment discipline is the frame: to measure the effect of one factor, hold all others fixed. An eval harness has many factors — prompt, temperature, tools, context, output cap — and a fair comparison pins every one of them and varies only the model. This is not pedantry; it is the only thing that licenses the sentence "B beat A because B is better."

The output cap earns special attention because its failure mode is invisible in the score. A truncated answer and a wrong answer both count as zero, so the score alone cannot tell you whether a model failed on skill or on config. You only recover the distinction by asking, item by item, whether the model had the skill and whether the cap fit the answer — which is exactly what a fair harness makes unnecessary by giving both models a generous, equal cap.

The arithmetic of the confound is worth stating plainly. The observed gap equals the true model gap plus the config penalty. When the throttled model is the weaker one, the penalty piles on and exaggerates the gap; when the throttled model is the stronger one, the penalty subtracts and shrinks or reverses it. The second case is the trap this module builds: the better model, throttled, is reported as no better at all.

<svg role="img" aria-label="The observed score gap decomposed into a true model gap plus a config penalty, with the penalty subtracting when the stronger model is throttled" viewBox="0 0 440 130">
<text x="70" y="30" fill="var(--ink)" font-size="10" text-anchor="middle">observed gap</text>
<rect x="30" y="40" width="80" height="24" fill="var(--s2)"/>
<text x="70" y="56" fill="var(--ink)" font-size="10" text-anchor="middle">0 (tie)</text>
<text x="130" y="56" fill="var(--muted)" font-size="12" text-anchor="middle">=</text>
<text x="200" y="30" fill="var(--ink)" font-size="10" text-anchor="middle">true model gap</text>
<rect x="160" y="40" width="80" height="24" fill="var(--s1)"/>
<text x="200" y="56" fill="var(--ink)" font-size="10" text-anchor="middle">+1 (B better)</text>
<text x="260" y="56" fill="var(--muted)" font-size="12" text-anchor="middle">+</text>
<text x="340" y="30" fill="var(--ink)" font-size="10" text-anchor="middle">config penalty</text>
<rect x="290" y="40" width="100" height="24" fill="var(--panel)" stroke="var(--s2)"/>
<text x="340" y="56" fill="var(--ink)" font-size="10" text-anchor="middle">-1 (B throttled)</text>
<text x="220" y="100" fill="var(--muted)" font-size="9" text-anchor="middle">throttle the stronger model and the penalty cancels its true edge to a tie</text>
</svg>
^ The observed gap is the true model gap plus a config penalty; throttling the stronger model makes the penalty subtract, cancelling a real win.

**Hold every harness factor fixed but the model; the output cap deserves the most care because its damage is invisible in the score — a truncated correct answer looks exactly like a wrong one.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/configparity-inter-01. Each item has a difficulty (a model solves it only if its skill meets it) and a tokens_needed (the answer needs that many output tokens, or it truncates). Model B is the stronger model.

```json filename=modules/evals-and-statistics/code/configparity-inter-01/configparity.json:11-14 COMPLETE
  "skill_a": 7,
  "skill_b": 8,
  "matched_config": {"max_tokens_a": 1000, "max_tokens_b": 1000},
  "unfair_config": {"max_tokens_a": 1000, "max_tokens_b": 100}
```

An item is scored correct only when both conditions hold — the skill meets the difficulty and the cap fits the answer.

```python filename=modules/evals-and-statistics/code/configparity-inter-01/configparity.py:32-34 COMPLETE
def solved(item, skill, max_tokens):
    """An item is scored correct only if skill meets the difficulty AND the cap fits the answer."""
    return skill >= item["difficulty"] and max_tokens >= item["tokens_needed"]
```

A model's score is just how many items it solved under its config.

```python filename=modules/evals-and-statistics/code/configparity-inter-01/configparity.py:37-38 COMPLETE
def score(items, skill, max_tokens):
    return sum(solved(it, skill, max_tokens) for it in items)
```

The confounded points are the items a model would solve by skill but loses only because the cap truncates the answer.

```python filename=modules/evals-and-statistics/code/configparity-inter-01/configparity.py:41-44 COMPLETE
def truncated_wins(items, skill, max_tokens):
    """Items the model would solve by skill but loses only because the cap truncates the answer."""
    return [it["id"] for it in items
            if skill >= it["difficulty"] and max_tokens < it["tokens_needed"]]
```

Before running it, predict: under the matched config B should win (it is the stronger model); under the unfair config, throttling B's cap should erase that win. Run `--scores`:

```text filename=configparity.py --scores
SCORES — each model under the matched config vs the unfair config
--------------------------------------------------------------
  config     max_a  max_b   score_a  score_b   winner
  matched    1000   1000    4        5         B
  unfair     1000   100     4        4         tie
```

The prediction holds. Matched, B wins 5 to 4 — its true advantage. Unfair, B's cap drops to 100, its score falls to 4, and the comparison reports a tie. Nothing about either model changed; only B's token cap did, and the winner changed with it.

<svg role="img" aria-label="Two bar pairs: under the matched config A scores 4 and B scores 5 with B taller; under the unfair config A scores 4 and B scores 4, equal" viewBox="0 0 440 190">
<line x1="30" y1="150" x2="200" y2="150" stroke="var(--line)"/>
<rect x="55" y="70" width="30" height="80" fill="var(--s1)"/>
<text x="70" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">A 4</text>
<rect x="120" y="50" width="30" height="100" fill="var(--s2)"/>
<text x="135" y="44" fill="var(--ink)" font-size="10" text-anchor="middle">B 5</text>
<text x="115" y="172" fill="var(--ink)" font-size="10" text-anchor="middle">matched: B wins</text>
<line x1="250" y1="150" x2="420" y2="150" stroke="var(--line)"/>
<rect x="275" y="70" width="30" height="80" fill="var(--s1)"/>
<text x="290" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">A 4</text>
<rect x="340" y="70" width="30" height="80" fill="var(--s2)"/>
<text x="355" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">B 4</text>
<text x="335" y="172" fill="var(--ink)" font-size="10" text-anchor="middle">unfair: tie</text>
</svg>
^ Same models, same items — throttling only B's output cap drops it from a win to a tie.

Now the attribution the score alone hides — why does B lose each item under the unfair cap? Run `--attribute`:

```text filename=configparity.py --attribute
ATTRIBUTE — why model B loses each item under the unfair config (cap 100)
------------------------------------------------------------
  id    difficulty  tokens_needed  skill_ok  cap_ok  lost_to
  i1    3           50             True      True    -
  i2    5           50             True      True    -
  i3    6           80             True      True    -
  i4    7           80             True      True    -
  i5    8           150            True      False   truncation
  i6    9           150            False     False   skill
------------------------------------------------------------
  lost to truncation (config): ['i5']   lost to skill (model): ['i6']
```

Item i5 is the whole story. B has the skill for it (difficulty 8, B's skill 8) but its 150-token answer does not fit the 100-token cap, so it is lost to truncation — a config failure. Item i6 is a genuine skill failure (difficulty 9 exceeds B's skill). The score of 4 mixes these two together; only the attribution separates the config loss from the real one.

<svg role="img" aria-label="Model B's true win of one item is shown split into two causes when throttled: the item is lost to truncation from the config, not to skill" viewBox="0 0 440 150">
<rect x="20" y="30" width="150" height="40" fill="var(--panel)" stroke="var(--s2)"/>
<text x="95" y="47" fill="var(--ink)" font-size="10" text-anchor="middle">B's real edge: i5</text>
<text x="95" y="62" fill="var(--muted)" font-size="9" text-anchor="middle">skill solves it</text>
<line x1="170" y1="50" x2="250" y2="50" stroke="var(--muted)"/>
<text x="210" y="42" fill="var(--muted)" font-size="9" text-anchor="middle">stingy cap</text>
<rect x="250" y="20" width="170" height="40" fill="var(--panel)" stroke="var(--s2)"/>
<text x="335" y="37" fill="var(--ink)" font-size="10" text-anchor="middle">truncated: scored wrong</text>
<text x="335" y="52" fill="var(--s2)" font-size="9" text-anchor="middle">lost to config, not model</text>
<rect x="250" y="80" width="170" height="40" fill="var(--panel)" stroke="var(--line)"/>
<text x="335" y="97" fill="var(--ink)" font-size="10" text-anchor="middle">i6: difficulty 9 &gt; skill 8</text>
<text x="335" y="112" fill="var(--muted)" font-size="9" text-anchor="middle">lost to skill (legitimate)</text>
</svg>
^ The score buries i5 (lost to the cap) alongside i6 (lost to skill); only attribution shows one loss is the config's fault, not the model's.

## Build

The self-test plants the failure and names each claim as a boolean flag. It scores both models under each config, checks that the matched config is equal and shows B winning, that the unfair config is unequal and erases the win, and that the erased points are exactly the correct answers truncated by the cap.

```python filename=modules/evals-and-statistics/code/configparity-inter-01/configparity.py:95-105 COMPLETE
    b_truly_better = mb > ma
    print("  under the matched config B beats A = %s (%d vs %d)" % (b_truly_better, mb, ma))

    unfair_config_unequal = u["max_tokens_a"] != u["max_tokens_b"]
    print("  unfair config gives the two models different caps = %s" % unfair_config_unequal)

    unfair_erases_win = ub <= ua
    print("  under the unfair config B no longer beats A = %s (%d vs %d)" % (unfair_erases_win, ub, ua))

    lost_to_truncation = truncated_wins(items, sb, u["max_tokens_b"])
    erased_by_truncation = len(lost_to_truncation) > 0 and (mb - ub) == len(lost_to_truncation)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the erased points ever stop being truncation losses:

```text filename=configparity.py --check
SELF-TEST — a matched config shows B's true win; an unfair token cap truncates a correct answer and erases it
--------------------------------------------------------------------------------------------------------------------
  matched config gives both models the same cap = True
  under the matched config B beats A = True (5 vs 4)
  unfair config gives the two models different caps = True
  under the unfair config B no longer beats A = True (4 vs 4)
  B's lost points are correct answers truncated by the cap = True (['i5'])
--------------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  matched_config_equal=True  b_truly_better=True  unfair_config_unequal=True  unfair_erases_win=True  erased_by_truncation=True
```

**The self-test ties the erased win to the truncated items exactly — the drop in B's score equals the count of correct answers the cap cut off — so it proves the tie came from config, not from any change in the models.**

## Definition of done

You can state the controlled-experiment rule for evals: vary only the model, hold prompt, temperature, and output cap identical across the comparison.
You can explain why the output cap is the sneakiest confound — a truncated correct answer scores identically to a wrong one, so the failure is invisible in the score.
You can write the observed gap as the true model gap plus a config penalty, and say when the penalty exaggerates the gap and when it erases it.
You can separate a skill loss from a truncation loss item by item, and explain why the aggregate score cannot.
You can name the fix — one shared, generous config — and say why a generous cap for both is safer than a tight cap for both.

## Boss fight

Flip which model is throttled: give the unfair config `max_tokens_a: 100, max_tokens_b: 1000` and rerun. Now A is the one truncated. A was already the weaker model, so throttling it widens the gap — B's win grows instead of vanishing. The lesson generalizes: a config difference does not always hide a winner, it distorts the gap in whatever direction the penalty falls, and only a matched config removes it. Either way the reported gap is not the model gap.

Now try the subtler failure. Keep both caps equal but tight — `max_tokens_a: 100, max_tokens_b: 100` — and rerun. The config is matched, so the comparison is fair, but both models now lose the long-answer item i5 to truncation, and the eval reports a tie at 4 to 4. This is fair but wrong about the world: a cap too small for the task understates both models and can hide a real difference from everyone. Config parity makes the comparison valid; a cap sized to the task is what makes it informative.

**Matched-but-tight is fair yet uninformative — parity removes the confound between the models, but only a cap large enough for the task keeps the eval from understating them both and hiding the very difference you are measuring.**

## External resources

The HELM and lm-evaluation-harness projects both stress fixed, documented generation settings and prompt templates as a precondition for comparable scores across models.
Anthropic's and OpenAI's model-comparison guidance note that decoding parameters and max-token limits must be held constant across systems for a comparison to be meaningful.
The topic's own modules on paired comparison and on production-mix weighting cover other ways a comparison's setup, not the model, can drive the result.
