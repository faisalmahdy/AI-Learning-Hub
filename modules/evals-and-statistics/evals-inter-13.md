---
id: evals-inter-13
title: The winner's curse — pick the best of many models on one noisy eval and its score is inflated
topic: evals-and-statistics
level: intermediate
status: ready
time: 21 min
summary: Every eval score is true skill plus noise, and crowning the highest scorer takes the maximum over many noisy draws, which is biased upward — so the winner's measured score overstates its true skill. On five models with identical true skill of 0.70, the selection eval crowns one at 0.78 (an 0.08 inflation and an apparent lead built entirely from noise); a fresh held-out eval regresses it to 0.69 and moves the crown to another model. Report the leaderboard score as performance and you overstate it.
eli5: If a hundred people each flip ten coins, someone will get nine heads and look amazing — but they're not a better flipper, just lucky. If you crown the top scorer from a big group and there's any luck involved, you've probably picked a lucky one, so their score is too good to be true. Test them again on something fresh to see their real level.
---

## Why this module

The model at the top of your leaderboard is there partly because it got lucky, so its score is too high — and the more models you compare, the worse the overstatement.

Every eval score is the model's true skill plus noise. The noise comes from a finite test set, from sampling temperature, from the luck of which items happened to be asked. Evaluate a single model and that noise roughly averages out — the score wobbles around the truth but is honest in expectation. The trouble starts when you evaluate many models and crown the highest scorer. Now you are not observing the noise once; you are taking the maximum over many noisy draws, and the maximum of noisy values is systematically larger than the truth. The model you select is disproportionately one that caught a favorable draw, so its measured score overstates its true skill. This is the winner's curse, and it is a property of selection itself, not of any particular model.

It is worse than a harmless upward bias, because selection can manufacture a gap where none exists. Suppose several models are genuinely equal. One of them will still top the leaderboard by luck, and its lead over the pack will look exactly like a real difference — a clear winner, a number to put in the announcement. But the lead is noise. The ranking below it is noise too. Read the leaderboard as if the ordering meant something and you crown a false winner; quote the top score as its performance and you have published an overestimate.

The fix is a fresh held-out eval that the selection never touched. The noise that inflated the winner on the selection eval is independent of the noise on a new eval, so re-scoring the winner on held-out data gives an unbiased estimate of its true skill. That estimate regresses back down toward the truth, and the fake gap collapses. The rule is that the eval you use to choose is not the eval you may use to report — choosing on a score spends its honesty, and only an untouched set can give the number back clean.

On the fixture five models have identical true skill of 0.70, so every difference between them is pure noise. The selection eval crowns model_c at 0.78 — an 0.08 inflation over its true 0.70, and an apparent lead over the field. Re-scored on held-out data, model_c drops to 0.69, right at the truth, and it is no longer even the top scorer.

**Selecting the highest scorer takes the maximum over many noisy eval draws, which is biased upward, so the winner's score overstates its true skill and can be a gap built entirely from noise; only a fresh held-out eval, whose noise is independent, gives the winner an honest score.**

## Concepts

The bias comes from the operation of taking a maximum, and it is easiest to see when every model is truly equal. Give five models the same true skill and add independent noise to each measurement. Each individual score is unbiased — as likely to land above the truth as below. But the one you keep is the largest of the five, and the largest of several draws is above the average draw by construction. So the kept score is biased high even though every underlying score was fair. Selection, not measurement, introduces the bias: the act of choosing the maximum is what breaks the honesty of the number you chose.

The size of the inflation grows with two things: the amount of noise and the number of candidates. More noise gives luck more room to move a score, so the luckiest draw sits further above the truth. More candidates give more chances for one to get lucky, so the maximum reaches higher. A leaderboard of two similar models is only mildly cursed; a leaderboard of fifty checkpoints, hyperparameter sweeps, or prompt variants — each a candidate — is severely cursed, and the winner there can be almost entirely luck. This is why sweeping over many configurations and reporting the best one is one of the most reliable ways to fool yourself in ML.

<svg role="img" aria-label="Five noisy scores scattered around the true-skill line, with the maximum marked well above the average of the draws" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">five unbiased draws — but their maximum is biased high</text>
  <line x1="40" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="100" x2="450" y2="100" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="96" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">true skill</text>
  <g fill="var(--s1)"><circle cx="90" cy="86" r="4"/><circle cx="170" cy="118" r="4"/><circle cx="250" cy="52" r="5"/><circle cx="330" cy="112" r="4"/><circle cx="410" cy="92" r="4"/></g>
  <line x1="40" y1="92" x2="450" y2="92" stroke="var(--s2)" stroke-dasharray="2 2"/>
  <text x="46" y="88" font-family="var(--mono)" font-size="8" fill="var(--s2)">avg of draws ≈ true</text>
  <line x1="250" y1="52" x2="250" y2="100" stroke="var(--s1)"/>
  <text x="256" y="48" font-family="var(--mono)" font-size="8" fill="var(--s1)">the max you keep — sits above the truth</text>
</svg>
^ Each of the five draws is equally likely to fall above or below the true skill, so their average is honest; but the single value you keep is the maximum, which lies above the truth by construction.

Regression to the mean is the same phenomenon viewed from the other side, and it is why the held-out re-score works. The winner was selected for an extreme score, and extreme scores are extreme partly because of noise that will not repeat. Measure the winner again with fresh, independent noise and it regresses toward its true skill — down, if it was inflated. The held-out eval is unbiased for the winner precisely because its noise is independent of the selection: nothing about how the winner was chosen is correlated with how it does on data it was not chosen on. That independence is the whole mechanism, which is why the held-out set must be genuinely untouched — reuse it to select again and it is cursed too.

This is the same discipline as a train/validation/test split, applied to model comparison rather than model fitting. You select on validation and you report on test, and the reason is identical: any dataset you optimize against — by fitting parameters or by picking a winner — gives an optimistic score, and only a set you did not optimize against gives an honest one. In eval terms: the leaderboard you rank on is validation, and a claim of performance needs a test set the ranking never saw. Skipping that step does not just risk a slightly high number; it risks announcing a winner whose entire advantage evaporates on contact with new data.

**Taking the maximum over noisy scores is biased upward, and the bias grows with noise and with the number of candidates; the winner's extreme score is partly non-repeating luck, so a fresh independent eval regresses it toward the truth — which is why selection and reporting must use different sets.**

## Worked example

The fixture is five models with identical true skill and two independent eval runs.

```json filename=modules/evals-and-statistics/code/evals-inter-13/models.json:3-5 COMPLETE
  "true_skill": {"model_a": 0.70, "model_b": 0.70, "model_c": 0.70, "model_d": 0.70, "model_e": 0.70},
  "selection_eval": {"model_a": 0.72, "model_b": 0.68, "model_c": 0.78, "model_d": 0.69, "model_e": 0.71},
  "holdout_eval": {"model_a": 0.71, "model_b": 0.70, "model_c": 0.69, "model_d": 0.72, "model_e": 0.70}
```

Every true skill is 0.70, so there is no real difference to find — every gap in the eval columns is noise. The selection eval is the run you would rank on; the held-out eval is a fresh independent run. The winner of a run is just its top scorer.

```python filename=modules/evals-and-statistics/code/evals-inter-13/curse.py:44-46 COMPLETE
def winner_on(scores):
    """The model with the highest score on a given eval."""
    return max(scores, key=scores.get)
```

Predict: `winner_on(selection_eval)` picks the model with the luckiest selection draw — model_c at 0.78 — and since its true skill is 0.70, that 0.78 is an overstatement. On the held-out eval, with independent noise, model_c should fall back near 0.70 and lose the crown to whichever model got lucky there instead. Run it.

```text filename=modules/evals-and-statistics/code/evals-inter-13/curse.py --scores
SCORES — true skill vs selection eval vs held-out eval
----------------------------------------------------------
  model      true    selection   held-out
  model_a    0.70      0.72        0.71
  model_b    0.70      0.68        0.70
  model_c    0.70      0.78        0.69
  model_d    0.70      0.69        0.72
  model_e    0.70      0.71        0.70
----------------------------------------------------------
  every true skill is equal, so all gaps are noise.
```

Read down the selection column: 0.72, 0.68, 0.78, 0.69, 0.71 — model_c stands out at 0.78, a clear leader. Read the true column: all 0.70. The leaderboard's ordering is meaningless, but nothing in the selection column tells you that — model_c looks like a real winner. Now the winner view, which spells out what selecting model_c actually bought you.

```text filename=modules/evals-and-statistics/code/evals-inter-13/curse.py --winner
WINNER — the model crowned by the selection eval
----------------------------------------------------------
  selection winner:      model_c at 0.78
  its true skill:        0.70  (inflation +0.08)
  its lead over field:   +0.080 on selection eval
  its held-out score:    0.69  (regressed to the truth)
  held-out top scorer:   model_d   (the crown moved)
----------------------------------------------------------
  the winner was lucky, not better; held-out reveals it.
```

The lead over the field is the winner's selection score minus the mean of the others — a one-line comparison against the rest of the pack.

```python filename=modules/evals-and-statistics/code/evals-inter-13/curse.py:49-50 COMPLETE
def mean(xs):
    return sum(xs) / len(xs)
```

Model_c's selection score of 0.78 is 0.08 above its true skill, and 0.08 above the field average — a lead that looks real and is entirely noise. Re-scored on held-out data, model_c comes in at 0.69, essentially its true 0.70, and the top held-out scorer is now model_d. If you had reported model_c's 0.78 as its performance, you would have overstated it by eight points; if you had believed the leaderboard, you would have crowned a model that is no better than the rest and does not even win the next round.

<svg role="img" aria-label="Selection eval shows model_c spiking to 0.78 above a flat true-skill line at 0.70; on held-out, model_c drops back to 0.69 and the spike moves to model_d" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">scores vs true skill (dashed = true 0.70, all models)</text>
  <line x1="40" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="95" x2="450" y2="95" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="380" y="91" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">true 0.70</text>
  <polyline points="70,85 150,117 230,50 310,112 390,90" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <g fill="var(--s2)"><circle cx="70" cy="85" r="3"/><circle cx="150" cy="117" r="3"/><circle cx="230" cy="50" r="4"/><circle cx="310" cy="112" r="3"/><circle cx="390" cy="90" r="3"/></g>
  <text x="180" y="44" font-family="var(--mono)" font-size="8" fill="var(--s2)">selection: model_c spikes to 0.78</text>
  <polyline points="70,90 150,95 230,101 310,84 390,95" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <g fill="var(--s1)"><circle cx="70" cy="90" r="3"/><circle cx="150" cy="95" r="3"/><circle cx="230" cy="101" r="4"/><circle cx="310" cy="84" r="3"/><circle cx="390" cy="95" r="3"/></g>
  <text x="150" y="130" font-family="var(--mono)" font-size="8" fill="var(--s1)">held-out: model_c back at 0.69, crown moves to model_d</text>
  <text x="60" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">a</text>
  <text x="140" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">b</text>
  <text x="222" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">c</text>
  <text x="302" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">d</text>
  <text x="382" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">e</text>
</svg>
^ The selection eval's spike at model_c sits well above the flat true-skill line; on the held-out eval model_c is back at the line and the spike has jumped to model_d — the lead was noise that did not repeat.

## Build

Reproduce the curse. Pure standard library, deterministic, so the 0.78 winner, the 0.08 inflation, and the 0.69 held-out regression come out exactly.

Run `--scores` for the full table, `--winner` for the verdict on the crowned model, `--check` for the gate. The self-test pins that the true skills are all equal (so the gap is noise), that selecting the max inflates the winner over its truth, that the held-out re-score drops back down and lands closer to the truth, and that the crown moves.

```python filename=modules/evals-and-statistics/code/evals-inter-13/curse.py:87-93 COMPLETE
    true_all_equal = max(true.values()) - min(true.values()) < 1e-9
    print("  all models have equal true skill, so any gap is noise = %s (%.2f)" % (true_all_equal, true[w]))

    selection_inflates = sel[w] > true[w]
    print("  the selection winner's score exceeds its true skill = %s (%.2f > %.2f)" % (selection_inflates, sel[w], true[w]))

    holdout_regresses = hold[w] < sel[w]
    print("  the winner's held-out score drops back down = %s (%.2f < %.2f)" % (holdout_regresses, hold[w], sel[w]))
```

The winner view computes the inflation directly as the selection score minus the true skill, and prints the held-out score beside it.

```python filename=modules/evals-and-statistics/code/evals-inter-13/curse.py:72-75 COMPLETE
    print("  selection winner:      %s at %.2f" % (w, sel[w]))
    print("  its true skill:        %.2f  (inflation +%.2f)" % (true[w], sel[w] - true[w]))
    print("  its lead over field:   +%.3f on selection eval" % (sel[w] - mean(field)))
    print("  its held-out score:    %.2f  (regressed to the truth)" % hold[w])
```

<svg role="img" aria-label="Two error bars: selection eval overstates the winner by plus 0.08; held-out eval errs by only minus 0.01" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">winner's estimate error vs the true 0.70</text>
  <line x1="60" y1="40" x2="60" y2="140" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="66" y="36" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">truth (error 0)</text>
  <text x="200" y="66" font-family="var(--mono)" font-size="9" fill="var(--s2)">selection eval</text>
  <rect x="60" y="72" width="320" height="18" fill="var(--s2)"/>
  <text x="200" y="86" font-family="var(--mono)" font-size="9" fill="var(--panel)">+0.08 overstated</text>
  <text x="90" y="118" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">held-out eval</text>
  <rect x="20" y="120" width="40" height="18" fill="var(--acc-line)"/>
  <text x="66" y="134" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">-0.01 (≈ truth)</text>
</svg>
^ The selection eval overstates the winner by +0.08; the held-out eval misses by only −0.01 — the fresh set is a correction, nearly eight times closer to the truth.

The `holdout_closer` flag is the one that proves the fix works, not just that the score moved: it checks the held-out estimate is nearer the truth than the selection estimate, so re-scoring is a correction, not just more noise.

```text filename=modules/evals-and-statistics/code/evals-inter-13/curse.py --check
SELF-TEST — selecting the max inflates the winner; a held-out re-score regresses it to the truth
------------------------------------------------------------------------------------------------
  all models have equal true skill, so any gap is noise = True (0.70)
  the selection winner's score exceeds its true skill = True (0.78 > 0.70)
  the winner's held-out score drops back down = True (0.69 < 0.78)
  held-out is closer to the truth than selection = True (|-0.01| < |0.08|)
  the selection winner is not the held-out winner = True (model_c vs model_d)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  true_all_equal=True  selection_inflates=True  holdout_regresses=True  holdout_closer=True  crown_moves=True
```

Five True flags. True_all_equal: the models are genuinely identical, so the whole ranking is noise. Selection_inflates: the crowned model scores 0.78 against a true 0.70. Holdout_regresses and holdout_closer: on fresh data it falls to 0.69, an error of −0.01 versus selection's +0.08 — the held-out estimate is nearly eight times closer to the truth. Crown_moves: model_c is not even the held-out winner, so the ranking did not survive contact with new data. The crown moving is the blunt proof that the leaderboard order was luck.

**The held-out re-score is a correction, not just a re-roll — its error of −0.01 versus selection's +0.08 shows the fresh set recovers the truth, which is why the eval you rank on can never be the eval you report.**

## Definition of done

You are done when you reproduce the inflation and its correction, and can explain why selecting the max causes it.

Concretely: `--scores` shows all true skills equal while the selection column has model_c spiking to 0.78; `--winner` shows the 0.08 inflation, the fake +0.080 lead, the held-out drop to 0.69, and the crown moving to model_d; `--check` prints PASS with five True flags. You can explain that taking the maximum over many noisy scores is biased upward, that the bias grows with noise and with the number of candidates, and that regression to the mean is why an independent held-out re-score is unbiased for the winner. You can state the rule: select on one set, report on another, because optimizing against a set — by fitting or by choosing — spends its honesty.

The habit to carry: whenever you pick the best of several models, checkpoints, prompts, or hyperparameter settings on an eval, treat the winner's score on that eval as an overestimate and re-score the chosen one on a held-out set before quoting a number or claiming a lead. The more candidates you compared, the more you must distrust the top score. A leaderboard ranks; it does not measure — measurement needs a set the ranking never touched.

## Boss fight

The instructive failure is a prompt sweep that finds a "10% better" prompt which does nothing in production.

An engineer tries 40 prompt variants against a 200-item eval and reports the best one as a 10-point accuracy improvement, and it ships. In production the metric does not move. With 40 candidates and the noise of a 200-item eval, the best-of-40 was heavily cursed — its 10-point lead was mostly the luckiest draw among 40, not a real gain. The fix is to hold out a fresh eval set the sweep never saw, re-run only the chosen prompt on it, and report that number; almost always it regresses toward the pack, and the honest improvement is a fraction of the swept one. The team learns to budget candidates and to reserve a test set, so the number they ship is the number they get.

Your turn, two moves. First, dial the curse up and down. Widen the selection-eval spread (more noise) and confirm the winner's inflation grows; then add more models with the same true skill and confirm the maximum climbs higher — the curse scales with both noise and candidate count, which is why big sweeps are the most dangerous. Second, make one model genuinely better (raise its true skill to 0.80 and lift both its eval scores accordingly) and confirm that now the selection winner and the held-out winner agree and the held-out score stays high — a real effect survives the held-out re-score, which is exactly how you tell a true winner from a lucky one.

## External resources

The winner's curse originates in auction theory (Capen, Clapp, and Campbell, 1971) — the highest bidder for an uncertain-value asset systematically overpays — and the statistical version, the bias of the maximum of noisy estimates, appears throughout model selection and genome-wide association studies under the same name.

Any treatment of the train/validation/test split (e.g. Hastie, Tibshirani, and Friedman's "Elements of Statistical Learning") makes the same point this module makes for model comparison: the set you select on gives an optimistically biased score, and an honest estimate needs a set held out from selection.

The literature on regression to the mean (Galton onward, and Kahneman's popular treatment) is the mechanism behind the held-out correction — an extreme measurement is extreme partly by luck, so a fresh independent measurement regresses toward the truth.
