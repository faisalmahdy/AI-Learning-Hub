---
id: evals-inter-15
title: Rank models by a strength that accounts for opponents — raw win-rate rewards an easy schedule
topic: evals-and-statistics
level: intermediate
status: ready
time: 21 min
summary: With pairwise results, raw win-rate (wins over games) is wrong whenever the schedule is unbalanced, because a win over a weak opponent counts the same as a win over a strong one. Bradley-Terry — the model behind Elo and the Chatbot Arena — fits each model a strength so the results are explained at once, weighting each win by opponent difficulty. On four models with true order A > B > C > D but a rigged schedule (C farmed weak D, B was ground down by strong A), raw win-rate ranks C above B (wrong); Bradley-Terry recovers A > B > C > D.
eli5: In a tournament, someone who only played beginners can win most of their games without being good. Someone who kept getting matched against the champion loses a lot but is actually strong. Counting wins ignores who you played. A rating that knows how hard each opponent was — like chess ratings — gives credit for beating strong players and forgives losing to them.
---

## Why this module

Counting a model's wins without asking who it played hands the top spot to whoever had the easiest schedule.

When you evaluate models by pitting them against each other — pairwise comparisons, an LLM judge picking a winner, human preference votes — you get a pile of "A beat B" results and need to turn them into one ranking. The obvious summary is win-rate: total wins over total games. It reads like a fair score, and it is fair only when everyone played the same schedule. The moment the schedule is unbalanced — some models faced tougher opponents than others — win-rate stops measuring strength and starts measuring luck of the draw.

The reason is that win-rate treats every win as worth the same, regardless of whom it was against. Beating the strongest model and beating the weakest model both add exactly one to your win count. So a mediocre model that mostly played weak opponents accumulates a gaudy win-rate on cheap victories, while a strong model that mostly faced tough opponents posts a low win-rate despite its losses being to the very best. Rank by win-rate and you can easily crown the model with the softest schedule over a genuinely stronger one whose schedule was brutal. The number is real; it just answers "did this model win often?" instead of "is this model good?"

Bradley-Terry — the statistical model underneath the Elo rating system and the LLM Chatbot Arena leaderboard — fixes this by fitting each model a single strength number, chosen so that the predicted probability of model i beating model j is strength_i / (strength_i + strength_j), and so that these predictions best explain all the observed results together. Because the fit explains every match jointly, beating a strong opponent (a low-probability event) pushes your strength up a lot, and losing to a strong opponent barely dents it. The schedule is absorbed into the model rather than ignored, so the fitted strengths rank models by ability regardless of who played whom.

On the fixture, four models have a genuine strength order A > B > C > D, but the schedule is rigged: C farmed the weak D while B was ground down by the strong A. Raw win-rate ranks C above B — the wrong order — because C's wins were cheap and B's losses were to the best model. Bradley-Terry, accounting for opponents, ranks B above C, recovering the true order.

**Raw win-rate weights every win equally regardless of opponent, so an unbalanced schedule lets an easy-schedule model outrank a stronger one; Bradley-Terry fits each model a strength that explains all pairwise results jointly, crediting wins by opponent difficulty, and recovers the true ranking whatever the schedule.**

## Concepts

The flaw in win-rate is that it is a marginal statistic — it collapses each model's record to one fraction, discarding the information about which opponents produced those wins and losses. Two models with the same win-rate can have completely different résumés: one built on beating weak opponents, one on splitting with strong ones. Marginalizing over the opponent throws away exactly the variable that determines how impressive a record is. This is the same failure shape as any average that ignores a confounder: the summary is a blend of ability and schedule, and when schedules differ, you cannot read ability off it.

Bradley-Terry keeps the opponent information by modeling every match rather than aggregating first. It posits that each model has a latent strength and that a match is a probabilistic event whose odds are the ratio of strengths, then it finds the strengths that make the observed pile of results most likely. Fitting jointly is what lets it weight correctly: a win over an opponent the model estimates to be strong is surprising under the model, so accommodating it requires a big upward adjustment to your strength; a loss to a strong opponent is expected, so it requires almost no adjustment. The estimator does automatically what a fair human judge does by hand — discount easy wins, forgive hard losses.

<svg role="img" aria-label="Two models with identical win-rate: one beat only weak opponents, the other split with strong ones; win-rate cannot tell them apart" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">same win-rate, opposite résumés — win-rate discards the difference</text>
  <text x="20" y="46" font-family="var(--mono)" font-size="8" fill="var(--ink)">model P: 6 wins / 10</text>
  <g fill="var(--muted)"><rect x="30" y="54" width="18" height="14"/><rect x="52" y="54" width="18" height="14"/><rect x="74" y="54" width="18" height="14"/><rect x="96" y="54" width="18" height="14"/><rect x="118" y="54" width="18" height="14"/><rect x="140" y="54" width="18" height="14"/></g>
  <text x="170" y="65" font-family="var(--mono)" font-size="7" fill="var(--muted)">all vs weak opponents (cheap)</text>
  <text x="20" y="102" font-family="var(--mono)" font-size="8" fill="var(--ink)">model Q: 6 wins / 10</text>
  <g fill="var(--acc-line)"><rect x="30" y="110" width="18" height="14"/><rect x="52" y="110" width="18" height="14"/><rect x="74" y="110" width="18" height="14"/><rect x="96" y="110" width="18" height="14"/><rect x="118" y="110" width="18" height="14"/><rect x="140" y="110" width="18" height="14"/></g>
  <text x="170" y="121" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">all vs strong opponents (hard)</text>
  <text x="30" y="148" font-family="var(--mono)" font-size="8" fill="var(--s2)">win-rate 0.60 for both — but Q is clearly the stronger model</text>
</svg>
^ Two records with the same win-rate can mean very different abilities; collapsing to a fraction marginalizes over the opponent, the one variable that says how much each win was worth.

Transitivity is the extra leverage a strength model has and win-rate lacks. If A beats B and B beats C, Bradley-Terry can infer something about A versus C even if they never played, because all three share the same strength scale. Win-rate has no such scale — it can only report what each model directly did — so it is blind to the indirect evidence that connects a schedule together. This is why strength models work on sparse, unbalanced tournaments (like the Arena, where most model pairs never meet head-to-head): they propagate strength through the graph of who-beat-whom, filling in comparisons that were never directly run.

This is the standard method for ranking from comparisons, and its relatives are worth knowing. Elo is Bradley-Terry updated online (one match at a time, so ratings drift as play continues); the Chatbot Arena publishes Bradley-Terry (and Elo) ratings from millions of human preference votes for exactly this reason — the schedule of which models get compared is wildly unbalanced. The cautions: strength models assume a single dimension of ability (they can be fooled by non-transitive, rock-paper-scissors match-ups where A beats B beats C beats A), and their ratings have uncertainty that grows when a model has few games or a disconnected schedule — a model that only ever played one cluster of opponents has a poorly-pinned strength. But for turning unbalanced pairwise results into an honest ranking, fitting strengths is the right move and raw win-rate is the trap.

**Win-rate is a marginal statistic that blends ability with schedule; Bradley-Terry models each match by a strength ratio and fits jointly, so it credits wins by opponent difficulty and uses transitivity to rank even models that never met — at the cost of assuming one ability dimension and needing enough connected games.**

## Worked example

The fixture is a set of pairwise results and the true strength order.

```json filename=modules/evals-and-statistics/code/evals-inter-15/matches.json:6-11 COMPLETE
  "wins": {
    "A": {"B": 7, "C": 2, "D": 0},
    "B": {"A": 3, "C": 0, "D": 2},
    "C": {"A": 0, "B": 0, "D": 7},
    "D": {"A": 0, "B": 0, "C": 3}
  }
```

The true order is A > B > C > D. But look at the schedule: B mostly played A (the strongest, losing 7 of 10), while C mostly played D (the weakest, winning 7 of 10). Win-rate is each model's total wins over its total games.

```python filename=modules/evals-and-statistics/code/evals-inter-15/rank.py:48-55 COMPLETE
def win_rate(wins, m, players):
    g = games_of(wins, m, players)
    return round(wins_of(wins, m) / g, 3) if g else 0.0


def ranking(scores):
    """Player ids ordered from highest score to lowest."""
    return sorted(scores, key=lambda m: scores[m], reverse=True)
```

Bradley-Terry fits strengths by the MM algorithm — iterate each model's strength as its wins divided by a sum over opponents that weighs each matchup by the current strengths, until it converges.

```python filename=modules/evals-and-statistics/code/evals-inter-15/rank.py:58-69 COMPLETE
def bradley_terry(wins, players, iters=200):
    """Fit each player's strength by the MM algorithm; strengths explain all pairwise results at once."""
    p = {m: 1.0 for m in players}
    for _ in range(iters):
        new = {}
        for m in players:
            w = wins_of(wins, m)
            denom = sum((wins[m].get(o, 0) + wins[o].get(m, 0)) / (p[m] + p[o]) for o in players if o != m)
            new[m] = w / denom if denom else p[m]
        s = sum(new.values())
        p = {m: v / s * len(players) for m, v in new.items()}   # normalize to keep scale stable
    return {m: round(p[m], 3) for m in players}
```

A model's total games count every match it played on either side of the ledger — the denominator win-rate divides by.

```python filename=modules/evals-and-statistics/code/evals-inter-15/rank.py:44-45 COMPLETE
def games_of(wins, m, players):
    return sum(wins[m].get(o, 0) + wins[o].get(m, 0) for o in players if o != m)
```

Predict: C's win-rate will beat B's (C farmed weak D, B lost to strong A), so win-rate mis-orders them; Bradley-Terry will put B back above C. Look at win-rate first.

```text filename=modules/evals-and-statistics/code/evals-inter-15/rank.py --winrate
WINRATE — raw wins / games and the ranking it gives
----------------------------------------------------
  A  wins  9  games 12  win-rate 0.750
  B  wins  5  games 12  win-rate 0.417
  C  wins  7  games 12  win-rate 0.583
  D  wins  3  games 12  win-rate 0.250
----------------------------------------------------
  raw ranking: A > C > B > D   (true: A > B > C > D)
```

C has a win-rate of 0.583 and B only 0.417, so win-rate ranks A > C > B > D — it put C ahead of B. But C earned its 7 wins against the weakest model D, and B earned its low rate by losing 7 of 10 to the strongest model A. Win-rate saw only the fractions and rewarded C's soft schedule. Now the strengths.

```text filename=modules/evals-and-statistics/code/evals-inter-15/rank.py --strength
STRENGTH — fitted Bradley-Terry strengths and the ranking they give
----------------------------------------------------
  A  strength 2.778
  B  strength 1.193
  C  strength 0.021
  D  strength 0.009
----------------------------------------------------
  BT ranking: A > B > C > D   (true: A > B > C > D)
```

Bradley-Terry ranks A > B > C > D — the true order. It rated B (1.193) well above C (0.021) despite C's higher win-rate, because B's record is losses to the strongest model plus wins over D, while C's record is wins over only the weakest model and zero wins against anyone strong. The strengths absorbed the schedule: B got credit for the difficulty of its opponents, and C's cheap wins were discounted. Same results, read two ways; only the strength model saw who played whom.

<svg role="img" aria-label="Win-rate bars rank C above B, but each win is shaded by opponent strength; the Bradley-Terry strengths rank B above C" viewBox="0 0 470 205" width="470" height="205">
  <rect x="0" y="0" width="470" height="205" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">win-rate (top) vs Bradley-Terry strength (bottom)</text>
  <text x="20" y="42" font-family="var(--mono)" font-size="8" fill="var(--s2)">win-rate ranks C over B</text>
  <text x="40" y="66" font-family="var(--mono)" font-size="8" fill="var(--ink)">B</text>
  <rect x="60" y="58" width="100" height="12" fill="var(--s2)"/>
  <text x="166" y="68" font-family="var(--mono)" font-size="7" fill="var(--muted)">0.417 (lost to strong A)</text>
  <text x="40" y="86" font-family="var(--mono)" font-size="8" fill="var(--ink)">C</text>
  <rect x="60" y="78" width="140" height="12" fill="var(--s2)"/>
  <text x="206" y="88" font-family="var(--mono)" font-size="7" fill="var(--muted)">0.583 (beat weak D)</text>
  <text x="20" y="126" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">Bradley-Terry ranks B over C</text>
  <text x="40" y="150" font-family="var(--mono)" font-size="8" fill="var(--ink)">B</text>
  <rect x="60" y="142" width="150" height="12" fill="var(--acc-line)"/>
  <text x="216" y="152" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">1.193</text>
  <text x="40" y="170" font-family="var(--mono)" font-size="8" fill="var(--ink)">C</text>
  <rect x="60" y="162" width="6" height="12" fill="var(--acc-line)"/>
  <text x="72" y="172" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">0.021</text>
  <text x="30" y="196" font-family="var(--mono)" font-size="8" fill="var(--muted)">accounting for opponents flips C and B back to the true order</text>
</svg>
^ Win-rate's longer bar for C (soft schedule) puts it above B; the Bradley-Terry strengths reverse them, because B's losses were to the strongest model and C's wins were over the weakest.

## Build

Reproduce the rankings. Pure standard library, deterministic, so the win-rate order A > C > B > D and the Bradley-Terry order A > B > C > D come out exactly.

Run `--winrate` for the raw ranking, `--strength` for the fitted strengths, `--check` for the gate. <svg role="img" aria-label="Two ranking lists side by side: win-rate reads A C B D, Bradley-Terry reads A B C D, with the B and C lines crossing between them" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">ranking by win-rate vs by Bradley-Terry</text>
  <text x="90" y="42" font-family="var(--mono)" font-size="9" fill="var(--s2)">win-rate</text>
  <text x="330" y="42" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">Bradley-Terry</text>
  <text x="120" y="66" font-family="var(--mono)" font-size="9" fill="var(--ink)">A</text>
  <text x="120" y="92" font-family="var(--mono)" font-size="9" fill="var(--s2)">C</text>
  <text x="120" y="118" font-family="var(--mono)" font-size="9" fill="var(--s2)">B</text>
  <text x="120" y="144" font-family="var(--mono)" font-size="9" fill="var(--ink)">D</text>
  <text x="360" y="66" font-family="var(--mono)" font-size="9" fill="var(--ink)">A</text>
  <text x="360" y="92" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">B</text>
  <text x="360" y="118" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">C</text>
  <text x="360" y="144" font-family="var(--mono)" font-size="9" fill="var(--ink)">D</text>
  <line x1="140" y1="62" x2="350" y2="62" stroke="var(--muted)"/>
  <line x1="140" y1="88" x2="350" y2="114" stroke="var(--s2)" stroke-width="2"/>
  <line x1="140" y1="114" x2="350" y2="88" stroke="var(--acc-line)" stroke-width="2"/>
  <line x1="140" y1="140" x2="350" y2="140" stroke="var(--muted)"/>
  <text x="180" y="168" font-family="var(--mono)" font-size="8" fill="var(--muted)">only B and C swap — the two with the most lopsided schedules</text>
</svg>
^ A and D keep their places, but B and C cross between the two rankings — win-rate demoted B (hard schedule) and promoted C (easy schedule), and Bradley-Terry swaps them back.

The self-test pins that win-rate is wrong, Bradley-Terry is right, and locates the exact inversion.

```python filename=modules/evals-and-statistics/code/evals-inter-15/rank.py:105-108 COMPLETE
    winrate_wrong = wr_rank != true
    print("  raw win-rate's ranking is not the true order = %s (%s)" % (winrate_wrong, " > ".join(wr_rank)))

    bt_correct = bt_rank == true
    print("  Bradley-Terry's ranking is the true order = %s (%s)" % (bt_correct, " > ".join(bt_rank)))
```

```text filename=modules/evals-and-statistics/code/evals-inter-15/rank.py --check
SELF-TEST — raw win-rate misranks the easy-schedule model; Bradley-Terry recovers the true order
------------------------------------------------------------------------------------------------
  raw win-rate's ranking is not the true order = True (A > C > B > D)
  Bradley-Terry's ranking is the true order = True (A > B > C > D)
  win-rate puts the easy-schedule C above the hard-schedule B = True
  Bradley-Terry puts B back above C = True
  the easy-schedule model really did have the higher win-rate = True (0.583 > 0.417)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  winrate_wrong=True  bt_correct=True  winrate_inverts=True  bt_fixes=True  easy_higher_winrate=True
```

Five True flags. Winrate_wrong: raw win-rate's ranking is not the true order. Bt_correct: Bradley-Terry's is. Winrate_inverts: win-rate puts the easy-schedule C above the hard-schedule B. Bt_fixes: Bradley-Terry puts B back above C. Easy_higher_winrate: C genuinely had the higher win-rate (0.583 versus 0.417) — the inversion is real in the data, not a rounding artifact. The last flag matters because it confirms this is not a tie broken arbitrarily: win-rate confidently ranks the wrong model higher, and only the strength model corrects it.

**The easy-higher-winrate flag is the indictment — C's win-rate genuinely exceeds B's, so anyone ranking by win-rate would confidently crown the weaker model; the schedule, not the ability, produced that number.**

## Definition of done

You are done when you reproduce the two rankings and can explain why win-rate inverts B and C.

Concretely: `--winrate` shows C at 0.583 above B at 0.417 giving A > C > B > D; `--strength` shows Bradley-Terry strengths A 2.778, B 1.193, C 0.021, D 0.009 giving A > B > C > D; `--check` prints PASS with five True flags. You can explain that win-rate is a marginal statistic that discards the opponent, that Bradley-Terry models each match by a strength ratio and fits jointly so wins are weighted by opponent difficulty, and that transitivity lets a strength model rank even models that never met. You can name the relatives (Elo, the Chatbot Arena) and the cautions (single ability dimension, uncertainty on sparse or disconnected schedules).

The habit to carry: when ranking from pairwise comparisons on any schedule that is not a perfectly balanced round-robin, fit a strength model (Bradley-Terry or Elo) rather than sorting by win-rate — and be wary of comparing win-rates when the models faced different opponents. When a leaderboard's win-rate ordering surprises you, check the schedule: a high win-rate against weak opponents and a low one against strong opponents are the fingerprints of a ranking that measured the draw, not the ability.

## Boss fight

The instructive failure is a leaderboard that crowns a model everyone can tell is worse.

A team ranks its models by their win-rate in an LLM-judge arena, and a new model shoots to the top of the leaderboard — but in side-by-side use it is clearly not the best. The arena's matchmaking had paired the new model mostly against a couple of weak baselines while the actual best model kept getting matched against strong contenders, so the new model's win-rate was inflated and the best model's was depressed. Shipping decisions made off the win-rate leaderboard would promote the wrong model. The fix is to compute Bradley-Terry (or Elo) ratings from the same match records, which discount the easy wins and forgive the hard losses, and to report those ratings with their uncertainty intervals — exactly what public arenas do for this reason.

Your turn, two moves. First, balance the schedule and watch the disagreement vanish: give every pair the same number of games (a round-robin) and confirm win-rate and Bradley-Terry now agree — showing the problem is unbalanced schedules specifically, and that win-rate is fine only under a balanced one. Second, break Bradley-Terry's assumption: build a non-transitive cycle (A beats B, B beats C, C beats A, all decisively) and confirm the fitted strengths come out nearly equal and cannot express the cycle — the single-dimension limit, and why rock-paper-scissors match-ups need a richer model than one strength per player.

## External resources

The Bradley-Terry model (Bradley and Terry, 1952) is the original; Hunter's "MM algorithms for generalized Bradley-Terry models" (2004) is the iterative fitting method this module implements, and any treatment of paired-comparison ranking derives the strength-ratio likelihood.

The LMSYS Chatbot Arena papers and leaderboard document Bradley-Terry and Elo ratings computed from millions of unbalanced human preference votes, and their notes on confidence intervals and non-transitivity are the practical cautions this module names.

The Elo rating system (Elo's "The Rating of Chessplayers") is the online, incremental cousin of Bradley-Terry, and comparing the two clarifies the batch-versus-streaming trade-off in comparison-based ranking.
