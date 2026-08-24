---
id: harness-inter-03
title: Did the skill help? Ratchet on the measurement, not the anecdote
topic: agent-harness
level: intermediate
status: ready
eli5: An agent taught itself a new trick. Before you keep it, run the same tasks with and without it — one trick clearly helps, the other changed a lot but helped none, and only the second gets thrown out.
time: 8-10h
summary: An agent compiles two candidate skills; run the same 20 tasks with and without each, and skill_A improves the pass rate +0.40 (interval clears zero, kept) while skill_B changes 11 tasks yet nets +0.05 with an interval from -0.25 to +0.35 — so the ratchet rejects it, because a self-improvement loop that keeps a skill it can't measure is just hoarding.
---

## Why this module

The agent-harness topic has built a loop, its seams, and a governed tool surface. This module closes the loop's most-skipped promise: self-improvement. The labs' harness can reflect on a finished transcript and compile a new skill — a `SKILL.md` procedure — and ratchet it into the library. The scan flagged the hole in one line: "nothing measures whether learned skills improve task outcomes." A loop that adds every skill it invents does not get better; it gets bigger. `CURRICULUM.md`'s Track 2.4 is the fix, and it is a bridge straight back to the evals track: "measure whether a learned skill improves task outcomes — one before/after eval with Track-1 statistics."

This module builds that gate at `intermediate`. Two candidate skills, a suite of 20 tasks, and a paired before/after eval — the same tasks run with and without each skill — that keeps a skill only when the improvement clears the noise, using inter-01's paired bootstrap and sign test verbatim. What it omits: no reflection step, no real agent runs, no live model — the before/after outcomes are a fixture. You need evals-inter-01. Stdlib Python 3, offline, $0.00, about two seconds a run, one sitting. The hard part is one temptation: a skill that visibly changed the agent's behavior *feels* like an improvement, and feeling is not measuring.

By the end, one command keeps one skill and throws the other out. Skipping ahead:

```
# modules/agent-harness/code/harness-inter-03/ — COMPLETE, run from that directory
$ python3 ratchet.py --ratchet

THE RATCHET — keep a skill only if it measurably helps
------------------------------------------------------------------
  skill_A  diff +0.40  CI [+0.15, +0.65]  sign p=0.0107  ->  KEEP
  skill_B  diff +0.05  CI [-0.25, +0.35]  sign p=0.5000  ->  REJECT
------------------------------------------------------------------
  KEEP needs the CI to clear zero. skill_B changed 11 tasks and still
  cannot: its gain is inside the noise, so the ratchet does not click.
```

run: 2026-08-22 · outcomes are a fixture; bootstrap seed=0, B=10000 · n=20 tasks · `python3 ratchet.py --ratchet`

Two skills the agent taught itself. One lifts the pass rate by 40 points with an interval nowhere near zero — kept. The other moved eleven of twenty tasks around and nets five points with an interval running from minus 0.25 to plus 0.35 — a coin flip dressed as progress, and thrown out. This module is about the gate that tells them apart, and why a self-improvement loop without it is a hoarder, not a learner.

## Concepts

Named here so you can find them again; each is built, and one is broken, below.

- **Learned skill** — a procedure the agent compiled from a transcript; the candidate to keep or reject.
- **Before/after eval** — the same tasks run with and without the skill. Paired.
- **The ratchet** — the rule that decides whether a skill enters the library.
- **Paired difference + interval** — inter-01's bootstrap and sign test, the measurement the gate reads.
- **The measured ratchet** — keep only if the interval clears zero. #3.
- **Point-estimate ratchet** — keep if the raw gain is positive. The planted bug.

## Worked example

Source: faisalmahdy/agent — `agent/skills/reflect.py` (compiles a SKILL.md from a finished transcript) and `agent/skills/ratchet.py` (gates skills), with the caveat the skills-matrix records: nothing yet measures whether a learned skill improves outcomes. And faisalmahdy/AI-Learning-Hub — `code/evals-inter-01/`, whose paired bootstrap and sign test this module reuses unchanged.

Script and fixtures: `modules/agent-harness/code/harness-inter-03/` — `ratchet.py`, 201 lines, `skills.json`, 20 tasks with a baseline and two candidate outcomes. Every command runs from there.

### Install the frame: the ratchet clicks only on a real tooth

In my opinion, the best way to think of keeping a skill is as a ratchet and pawl, not a growing list.

A ratchet advances one tooth and cannot slip back — but it only clicks forward when a tooth is actually there for the pawl to catch. Press it against a smooth spot and nothing engages; force it and you strip the gear. Keeping a learned skill is the same click: the skill advances the library only when its measured improvement is a real tooth, big enough for the pawl to catch. The pawl is the confidence interval. A gain that sits inside the noise is a smooth spot — no tooth — and ratcheting the skill in anyway strips the thing you were trying to build.

Three jobs, one line each: the before/after eval says "how much did the skill change outcomes?", the interval says "how much of that could be noise?", and the ratchet says "click forward only if the change clears the noise."

The loop is a ring with one gate on it. The agent reflects on a transcript, compiles a candidate skill, and runs the before/after eval — and the only thing standing between the candidate and the library is the pawl:

<svg viewBox="0 0 680 150" role="img" aria-label="A self-improvement loop: a finished transcript feeds a reflect step, which compiles a candidate skill, which goes to a before/after eval, which feeds the ratchet gate. The gate keeps the skill into the library only if its interval clears zero, otherwise discards it. The library feeds the next run's transcript, closing the loop.">
  <g font-family="var(--mono)" font-size="10">
    <rect x="24" y="52" width="96" height="34" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="72" y="73" text-anchor="middle" fill="var(--ink)">transcript</text>
    <rect x="150" y="52" width="96" height="34" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="198" y="67" text-anchor="middle" fill="var(--ink)">reflect →</text>
    <text x="198" y="80" text-anchor="middle" fill="var(--muted)">candidate</text>
    <rect x="276" y="52" width="112" height="34" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="332" y="67" text-anchor="middle" fill="var(--ink)">before/after</text>
    <text x="332" y="80" text-anchor="middle" fill="var(--muted)">eval + interval</text>
    <rect x="418" y="48" width="92" height="42" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="464" y="65" text-anchor="middle" fill="var(--acc-ink)">ratchet</text>
    <text x="464" y="79" text-anchor="middle" fill="var(--acc-ink)">(the pawl)</text>
    <line x1="120" y1="69" x2="148" y2="69" stroke="var(--muted)" stroke-width="1.4"></line>
    <line x1="246" y1="69" x2="274" y2="69" stroke="var(--muted)" stroke-width="1.4"></line>
    <line x1="388" y1="69" x2="416" y2="69" stroke="var(--muted)" stroke-width="1.4"></line>
    <rect x="548" y="24" width="108" height="30" rx="6" fill="var(--panel)" stroke="var(--s1)"></rect>
    <text x="602" y="43" text-anchor="middle" fill="var(--s1)">KEEP → library</text>
    <rect x="548" y="86" width="108" height="30" rx="6" fill="var(--panel)" stroke="var(--s2)"></rect>
    <text x="602" y="105" text-anchor="middle" fill="var(--s2)">REJECT → drop</text>
    <line x1="510" y1="60" x2="546" y2="42" stroke="var(--s1)" stroke-width="1.4"></line>
    <text x="524" y="46" font-size="8.5" fill="var(--muted)">CI clears 0</text>
    <line x1="510" y1="78" x2="546" y2="98" stroke="var(--s2)" stroke-width="1.4"></line>
    <text x="522" y="96" font-size="8.5" fill="var(--muted)">CI spans 0</text>
    <path d="M 602 24 L 602 14 L 72 14 L 72 50" fill="none" stroke="var(--grid)" stroke-width="1.2" stroke-dasharray="3 3"></path>
    <text x="330" y="10" text-anchor="middle" font-size="8.5" fill="var(--muted)">kept skills feed the next transcript</text>
  </g>
</svg>
^ The loop with one gate. Every candidate reaches the pawl; only an interval clear of zero clicks it into the library, and the naive loops in the next section are this same ring with the gate removed.

### Look at the data: two skills, twenty tasks, run both ways

Each skill was run against the same 20 tasks the baseline was, so every comparison is paired. skill_A is a grounding hint; skill_B is a verbose-format nudge. The `--evaluate` view is the whole before/after picture:

```
# $ python3 ratchet.py --evaluate
#   skill_A  baseline 0.40 -> with-skill 0.80   diff +0.40  CI [+0.15, +0.65]
#            helps 9, hurts 1, ties 10   sign p=0.0107
#   skill_B  baseline 0.40 -> with-skill 0.45   diff +0.05  CI [-0.25, +0.35]
#            helps 6, hurts 5, ties 9   sign p=0.5000
```

run: 2026-08-22 · fixture; bootstrap seed=0, B=10000 · n=20 tasks · `python3 ratchet.py --evaluate`

Carry skill_B, the interesting one. It is *busy*: it flipped 6 baseline failures to passes and 5 baseline passes to failures — eleven of twenty tasks changed. A skill that changes eleven tasks obviously does something. Now the prediction — commit before the next section. skill_B helped 6 and hurt 5, a net of one task. Do you keep it? Write it down. Most people say yes — it helped more than it hurt, net positive, keep it. The answer is at the top of the next section.

<svg viewBox="0 0 680 118" role="img" aria-label="skill_B's per-task effect across 20 tasks: five losses, then three ties, then six wins, then six ties. Eleven tasks changed, netting one.">
  <g font-family="var(--mono)">
    <text x="44" y="24" font-size="10.5" fill="var(--muted)">skill_B, per task: win = helped, loss = hurt, tie = unchanged</text>
    <g>
      <rect x="44" y="36" width="22" height="22" rx="3" fill="var(--s2)"></rect><rect x="74" y="36" width="22" height="22" rx="3" fill="var(--s2)"></rect><rect x="104" y="36" width="22" height="22" rx="3" fill="var(--s2)"></rect><rect x="134" y="36" width="22" height="22" rx="3" fill="var(--s2)"></rect><rect x="164" y="36" width="22" height="22" rx="3" fill="var(--s2)"></rect>
      <rect x="194" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect><rect x="224" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect><rect x="254" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect>
      <rect x="284" y="36" width="22" height="22" rx="3" fill="var(--s1)"></rect><rect x="314" y="36" width="22" height="22" rx="3" fill="var(--s1)"></rect><rect x="344" y="36" width="22" height="22" rx="3" fill="var(--s1)"></rect><rect x="374" y="36" width="22" height="22" rx="3" fill="var(--s1)"></rect><rect x="404" y="36" width="22" height="22" rx="3" fill="var(--s1)"></rect><rect x="434" y="36" width="22" height="22" rx="3" fill="var(--s1)"></rect>
      <rect x="464" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect><rect x="494" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect><rect x="524" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect><rect x="554" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect><rect x="584" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect><rect x="614" y="36" width="22" height="22" rx="3" fill="var(--grid)"></rect>
    </g>
    <g font-size="9.5" fill="var(--muted)"><rect x="44" y="74" width="14" height="14" rx="3" fill="var(--s1)"></rect><text x="64" y="85">6 helped</text><rect x="150" y="74" width="14" height="14" rx="3" fill="var(--s2)"></rect><text x="170" y="85">5 hurt</text><rect x="250" y="74" width="14" height="14" rx="3" fill="var(--grid)"></rect><text x="270" y="85">9 unchanged</text></g>
    <rect x="420" y="72" width="216" height="22" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="528" y="87" font-size="10" text-anchor="middle" fill="var(--acc-ink)">11 changed · net +1 of 20</text>
  </g>
</svg>
^ skill_B's effect, task by task: it changed eleven of twenty, and the wins and losses very nearly cancel.

How to read this: the eye sees eleven colored cells and reads "active". The ratchet counts wins minus losses and sees +1, then asks whether +1 of 20 is more than noise. The failure signature is a strip busy with color whose greens and reds roughly balance.

### Strategy #1 — keep it if it ever helped. The library fills with cruft.

The simplest ratchet keeps any skill that helped on any task. Run it and both skills stay:

```
# ratchet.py:89-92 — COMPLETE (the trap: keep on any win)
def keep_naive(base, skill):
    """The trap: keep the skill if it helped on ANY task."""
    wins, _, _, _ = sign_test(base, skill)
    return wins > 0

# $ python3 ratchet.py --naive
#   skill_A  helped  9 tasks -> KEEP
#   skill_B  helped  6 tasks -> KEEP
#   both kept.
```

run: 2026-08-22 · fixture · n=20 tasks · `python3 ratchet.py --naive`

Both kept, because both helped *somewhere* — everything helps somewhere. This is exactly how a skill library rots: every reflection produces a skill that beat the baseline on at least one task, so every skill is kept forever, each one adding prompt length, latency, and a chance of firing on the wrong task, for a benefit no one measured. Strategy #1 is not a filter, it is a funnel.

### Strategy #2 — keep it if the net gain is positive. This is the bug.

So do not keep on a single win; keep on the net. skill_B nets +0.05 — positive — so keep it. That rule is one line, and it is wrong:

```
# ratchet.py:95-97 — COMPLETE (the planted bug: keep on the raw gain, ignore the interval)
def keep_point_estimate(base, skill):
    """THE BUG: keep the skill if its raw gain is positive, ignoring the interval."""
    return mean(skill) - mean(base) > 0
```

Stop here. This keeps skill_B, and skill_B nets a genuine +0.05 — so why is keeping it wrong? Because +0.05 on 20 tasks has an interval of `[-0.25, +0.35]`, and a sign test of `p=0.5000` — the skill is statistically a coin flip. The gain is real as an arithmetic fact about these 20 tasks and meaningless as a claim about the next 20. The bug hides because on a *good* skill it agrees: skill_A also has a positive gain, so the point-estimate ratchet keeps it too, and only diverges on the marginal skill — which is the only place the decision was ever hard. Named: the **point-estimate ratchet**, inter-01's lesson wearing a keep/reject hat. The one-line assertion: a skill whose interval includes zero must be rejected. `--check` runs it:

```
# $ python3 ratchet.py --check
#   skill_B CI = [-0.25, +0.35], sign p=0.5000
#   measured ratchet keeps skill_B = False  (CI includes zero -> reject)
#   point-estimate ratchet keeps   = True  (the bug: +0.05 > 0 -> keep)
# SELF-TEST PASS  routes_agree=True  bug_detectable=True  deterministic=True
```

run: 2026-08-22 · seed=0, B=10000 · n=20 tasks · `python3 ratchet.py --check`

The measured ratchet rejects skill_B; the point-estimate one keeps it; the paired difference agrees to six places by two routes, and two seeded runs are identical.

**"It changed the output" is not "it improved the output" — the difference is an interval, and the interval is the ratchet's pawl.**

### Strategy #3 — keep it only if the interval clears zero

The fix is inter-01's exact machinery, gating a decision instead of printing a leaderboard. Resample the tasks, recompute the paired difference, and keep the skill only if the interval sits above zero and the sign test agrees.

```
# ratchet.py:53-68, 82-86 — COMPLETE (the paired bootstrap from inter-01, and the gate)
def paired_diffs(base, skill):
    """skill outcome minus baseline outcome, per task. Paired: same task both."""
    return [skill[i] - base[i] for i in range(len(base))]


def bootstrap_diff_ci(base, skill, rng):
    n = len(base)
    d = paired_diffs(base, skill)
    boots = []
    for _ in range(BOOT):
        s = 0
        for _ in range(n):
            s += d[rng.randrange(n)]
        boots.append(s / n)
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)


def keep_measured(base, skill, rng):
    """KEEP only if the paired improvement clears zero AND the sign test agrees."""
    lo, hi = bootstrap_diff_ci(base, skill, rng)
    _, _, _, p = sign_test(base, skill)
    return (lo > 0) and (p < 0.05), (lo, hi, p)
```

run: 2026-08-22 · seed=0, B=10000 · n=20 tasks · this is the rule behind `--ratchet`

This is the **measured ratchet**. On skill_A the interval is `[+0.15, +0.65]`, entirely above zero, and the sign test is `p=0.0107` — kept. On skill_B the interval is `[-0.25, +0.35]`, straddling zero, `p=0.5000` — rejected. The good skill clicks the ratchet forward; the busy one is a smooth spot and the ratchet holds.

<svg viewBox="0 0 680 168" role="img" aria-label="A number line for the paired difference from -0.35 to +0.7, zero marked. skill_A's interval runs from +0.15 to +0.65, entirely right of zero, kept. skill_B's interval runs from -0.25 to +0.35, straddling zero, rejected.">
  <g font-family="var(--mono)">
    <text x="60" y="24" font-size="10.5" fill="var(--muted)">paired difference (with-skill minus baseline), per skill</text>
    <line x1="60" y1="118" x2="640" y2="118" stroke="var(--grid)" stroke-width="1.5"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="182" y="134">0.0</text><text x="314" y="134">+0.25</text><text x="446" y="134">+0.50</text><text x="578" y="134">+0.75</text></g>
    <line x1="182" y1="40" x2="182" y2="126" stroke="var(--acc)" stroke-width="1.4" stroke-dasharray="3 3"></line>
    <text x="182" y="36" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">zero</text>
    <text x="60" y="63" font-size="10" fill="var(--ink)">skill_A</text>
    <line x1="261" y1="66" x2="525" y2="66" stroke="var(--s1)" stroke-width="2.5"></line>
    <circle cx="393" cy="66" r="4" fill="var(--s1)"></circle>
    <text x="537" y="69" font-size="9" fill="var(--s1)">KEEP</text>
    <text x="60" y="97" font-size="10" fill="var(--ink)">skill_B</text>
    <line x1="50" y1="90" x2="367" y2="90" stroke="var(--s2)" stroke-width="2.5"></line>
    <circle cx="208" cy="90" r="4" fill="var(--s2)"></circle>
    <text x="379" y="93" font-size="9" fill="var(--s2)">REJECT</text>
    <rect x="430" y="146" width="210" height="20" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="535" y="160" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">only the interval clear of zero is kept</text>
  </g>
</svg>
^ The two skills' paired-difference intervals. skill_A clears zero and is kept; skill_B straddles it and is rejected, whatever its positive point estimate says.

How to read this: the diagnostic is the left end of each bar against the zero line. skill_A's clears it; skill_B's crosses it, so its +0.05 midpoint is a number you cannot defend on 20 tasks.

### The running tally

| ratchet rule | skill_A | skill_B |
|---|---|---|
| keep if it ever helped | KEEP | KEEP |
| keep if net gain > 0 (the bug) | KEEP | KEEP |
| keep if the interval clears zero | KEEP | REJECT |

The skills never changed; only the rule did. The first two keep the coin-flip skill by different mistakes — a single anecdote, a noisy net — and only the third, the one that reads the interval, throws it out. And yet — 20 tasks gave skill_B an interval 0.60 wide, so "reject" here means "not shown to help on this little evidence", not "shown to be useless"; more tasks could still promote it.

**A self-improvement loop that does not measure improvement is not learning — it is hoarding.**

### Bridge to the standard names

Nobody outside this module calls it a pawl. The reflection step is what the labs' `reflect.py` does — compile a `SKILL.md` from a transcript — and the gate is `ratchet.py`; the eval is a **paired A/B test**, the bootstrap and sign test are inter-01's, and the keep-only-if-better rule is a **hill-climbing accept criterion** with a significance gate. In reinforcement-learning terms, accepting a change on a positive point estimate is **noise-chasing**; the fix is the same held-out, interval-gated discipline the evals track is built on. "Ratchet" is the labs' own word for it, and the mechanism is exactly why the word fits: forward-only, and only on a real tooth.

### What we did not settle

The 20 outcomes are a fixture, so this measures the ratchet honestly and the skills only as authored. Three real complications we skipped: the skill should be measured on *held-out* tasks, not the ones it was reflected from, or a skill that memorizes its own transcript looks great and generalizes to nothing; multiple candidate skills tested at once need a multiple-comparison correction, or one of them clears p=0.05 by luck; and the ratchet here is pass/fail per task, where a real one might gate on a graded rubric (evals-inter-04) and weigh a regression more than a gain. If the pull to keep skill_B "because it helped six tasks" is still there, that is the honest tension — and it is answered by getting more tasks, not by lowering the bar.

## Build

The pipeline in one paragraph: take a candidate skill; run your task suite with and without it, the same tasks both ways; compute the paired difference with a bootstrap interval and a sign test; keep the skill only if the interval clears zero; and re-run the whole gate every time the agent proposes a new skill.

We opened on the ratchet keeping one skill and rejecting the other. The payoff block (again):

```
# modules/agent-harness/code/harness-inter-03/ — COMPLETE, run from that directory
$ python3 ratchet.py --ratchet
  skill_A  diff +0.40  CI [+0.15, +0.65]  sign p=0.0107  ->  KEEP
  skill_B  diff +0.05  CI [-0.25, +0.35]  sign p=0.5000  ->  REJECT
```

Now ratchet your own skills. The one dial is `skills.json`: for each candidate skill, run your suite with and without it and store the paired pass/fail per task. Everything in `ratchet.py` derives from that file. Run the skill on held-out tasks, not the ones it was learned from.

Your number to beat is not a pass rate — it is the **fraction of proposed skills your ratchet rejects**. If it keeps every skill, it is the naive funnel and your library is filling with noise; a real ratchet says no most of the time. Add a skill that changes many tasks but nets nothing and confirm your gate rejects it while a point-estimate check would keep it. Bring back the reject rate. Good luck.

### FAQ

**skill_B helped six tasks — isn't rejecting it throwing away a real gain?** It hurt five, and the net is a coin flip, so "real gain" is not established. If those six tasks matter, run more tasks and re-measure; do not keep a skill on six anecdotes.

**Why a sign test *and* an interval — isn't one enough?** They can disagree at small N, exactly as in the SWE-bench capstone: the bootstrap can clear zero while the exact test cannot. Requiring both is the conservative call for a gate that ships skills.

**Doesn't this make self-improvement slow?** Yes, and that is correct — a skill is a permanent addition to every future prompt, so it should cost a real eval to earn a place. Fast accumulation is the disease.

**Why is mine slow?** This isn't — it is a bootstrap over 20 numbers. Yours is slow at the before/after runs, because each task is a real agent run; that cost is why you gate, so you only pay it for skills worth keeping.

### Errata

Version one, dated 2026-08-22. skill_B is authored to net exactly +1 of 20 so its interval straddles zero cleanly; real marginal skills are messier, but the verdict logic is identical. One soft spot left in: the ratchet measures on the same 20 tasks for both skills and says nothing about held-out generalization, which is the larger risk in real self-improvement and is called out in "what we did not settle" rather than solved.

## Definition of done

- [ ] `skills.json` for your own candidate skills: paired pass/fail per task, with and without each skill, on held-out tasks
- [ ] A before/after eval reporting the paired difference, a bootstrap interval, and a sign test per skill
- [ ] A ratchet that keeps a skill only if the interval clears zero (and the sign test agrees)
- [ ] The naive and point-estimate ratchets kept for contrast, so the trap is visible
- [ ] `python3 ratchet.py --check` printing SELF-TEST PASS: paired diff derived twice, the bug detectable, deterministic
- [ ] A run stamp under every published number: date · seed and B · n tasks · the command
- [ ] The gate wired to run on every proposed skill, not once
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A learned skill changed 11 of 20 tasks. Say why that is not evidence it helped, and the one number that decides whether to keep it.
2. Give the three ratchet rules in order, and which of the two candidate skills each keeps or rejects.
3. The point-estimate ratchet keeps a skill on a raw gain of +0.05. State the bug in one sentence and why it agrees with the correct ratchet on a good skill.
4. Explain, in the ratchet-and-pawl frame, what the confidence interval is and what "the ratchet does not click" means for a skill.
5. Your own run printed skill_B's paired interval. What was it, did it clear zero, and what did the naive ratchet do with the same skill?

## External resources

- Anthropic, *Agent Skills* — https://www.anthropic.com/news/skills — my summary: what a compiled skill is and how an agent loads it; read it for the shape of the thing this module decides whether to keep, and note it does not tell you when to keep one.
- This hub, *evals-inter-01* — modules/evals-and-statistics/evals-inter-01.md — my summary: the paired bootstrap and sign test reused here in full; if the interval or the sign test feels like magic, that module builds both from scratch.
- Kohavi, Tang & Xu, *Trustworthy Online Controlled Experiments* (2020) — https://experimentguide.com/ — my summary: the discipline of A/B testing changes before shipping them; a learned skill is a change, and the ratchet is that discipline applied to an agent improving itself.
