---
id: teach-basic-01
title: Learned means a dated recall pass, not a checkmark
topic: teaching-and-portability
level: basic
status: ready
time: 6-8h
summary: Count a curriculum's progress by modules authored and six of six look nearly done at 5 of 6 — but authoring is the teacher's work, not the learner's, and only 3 of 6 have a dated closed-book recall pass that is still within the 60-day retention window. One module was never recall-tested and one passed only ninety days ago and has decayed, so the honest retained count is 3, and the two-module gap is progress that looks earned and is not.
eli5: Signing up for the gym is not the same as being able to lift the weight today. A module you wrote, or read once, or passed months ago is not one you can still do from memory now — only a recent, closed-book pass counts, and even that fades.
---

## Why this module

This opens the teaching-and-portability track, which is about turning a personal learning system into something a stranger could run — and it starts with the measurement that the whole hub is built on: what counts as having *learned* a module. Every module in this hub ends with a boss fight whose passing earns a dated entry in a recall ledger, and that design is deliberate. The scan is blunt about why it matters: the labs built "a mechanically enforced spaced-recall gate," but its ledger "has zero dated passes, so assessment is designed but never run." A gate nobody passes is not a gate; it is decoration.

The tempting progress metric is "modules authored" or "modules read." Both overcount, and in opposite-looking but identical ways: authoring a module is the *teacher's* labor, and reading one is exposure, not retention — neither is evidence the *learner* can reproduce the material. The honest signal is a dated, closed-book recall pass. And even that is not permanent: memory decays, so a pass from four months ago is not current mastery. Retention is a recent pass, and progress is how many modules you could pass *today*, not how many you once could.

You need nothing but Python 3 and the standard library. Everything runs offline against a six-module ledger fixture, `$0.00`, one sitting. The instinct to unlearn is that a checkmark is achievement. A checkmark is a claim; a dated recall pass is evidence; and evidence expires.

Here is the same curriculum counted two ways:

```
# modules/teaching-and-portability/code/teach-basic-01/ — COMPLETE, run from that directory
$ python3 progress.py --progress

PROGRESS — what looks done vs what is retained
------------------------------------------------------------------
  authored (looks done)   5/6
  retained (really done)  3/6
```

run: 2026-08-25 · deterministic; the clock is fixed · now=day 200, window 60 days, 6 modules · `python3 progress.py --progress`

By authoring, the curriculum is nearly complete: five of six. By retention — a recall pass still inside the window — it is half. The gap of two is progress that looks earned: one module never recall-tested, one passed so long ago it has faded. This module is that gap and why only the second column is honest.

## Concepts

Named here so you can find them again; each is built below.

- **Authored** — the module exists and is marked ready. The teacher's checkmark.
- **Recall pass** — a dated, closed-book reproduction of the material. The learner's evidence.
- **Retention window** — how long a pass stays valid before memory is assumed to have decayed.
- **Retained** — has a recall pass within the window; the honest "learned" status.
- **Decay** — a pass aging past the window, so the module needs re-testing.
- **Unearned progress** — the gap between authored and retained: what looks done but cannot be reproduced now.

## Worked example

Source: the hub's own recall ledger (`ledger/recall-ledger.json`) and the recall gate the scan describes — `recall_gate.py` over a spaced-recall ledger, whose caveat is zero dated passes. This module builds the metric that gate should drive.

Script and fixture: `modules/teaching-and-portability/code/teach-basic-01/` — `progress.py`, and `ledger.json`, six modules with authoring status and dated recall passes. Every command runs from there.

### The frame: a gym membership is not a deadlift

Signing up for the gym is a checkmark. It is not the same as walking in today and lifting the weight. And lifting it once, three months ago, is not the same as lifting it now — strength you do not maintain fades. A curriculum's "modules done" is the membership: it records that the material was prepared and maybe seen, not that the learner can perform it on demand. The only measurement that means "can perform it" is a recent, unaided reproduction — a recall pass with a date on it — and the date matters because the ability behind it decays.

That is the whole module. Authoring and reading are memberships; a dated recall pass is a lift; and a lift from long ago has to be redone. Progress is the count of lifts you can do today, which is smaller and more honest than the count of memberships you hold.

### Two statuses: the checkmark and the evidence

Authored is trivial — the module is marked ready.

```
# progress.py:38-40 — COMPLETE (the teacher's checkmark)
def authored(m):
    """The teacher's checkmark: the module exists and is marked ready."""
    return m["status"] == "ready"
```

Retained is the honest one: a recall pass exists *and* is recent enough to still count.

```
# progress.py:48-52 — COMPLETE (a dated pass, still within the window)
def retained(now, m):
    """The honest status: a recall pass exists AND is within the retention window,
    so the learner can still reproduce it today -- not just once, long ago."""
    lp = last_pass(m)
    return lp is not None and (now - lp) <= WINDOW
```

The two conditions rule out the two ways a checkmark lies. `lp is not None` rules out a module that was authored but never recall-tested — done on paper, never assessed. `(now - lp) <= WINDOW` rules out a module whose only pass has decayed. Both must hold, and the ledger shows exactly who fails which.

```
# $ python3 progress.py --ledger
#   module         authored  last-pass  age   retained
#   evals-basic    yes       190        10    yes
#   evals-inter    yes       110        90    no
#   harness-basic  yes       never      -     no
#   retr-basic     yes       196        4     yes
#   retr-inter     DRAFT     never      -     no
#   govern-basic   yes       160        40    yes
```

run: 2026-08-25 · fixture · `python3 progress.py --ledger`

Five modules are authored, but `evals-inter`'s only pass is 90 days old — past the 60-day window, so it has decayed — and `harness-basic` was never recall-tested at all. Both carry the teacher's checkmark and neither is retained. `govern-basic` shows the other side: two passes, the most recent 40 days ago, still inside the window — retained.

<svg viewBox="0 0 700 180" role="img" aria-label="Two columns of six modules. The authored column marks five as done (all but the draft). The retained column marks only three: evals-basic, retr-basic, govern-basic. evals-inter and harness-basic are authored but not retained.">
  <g font-family="var(--mono)" font-size="9">
    <text x="120" y="18" fill="var(--muted)">authored (checkmark)</text><text x="380" y="18" fill="var(--muted)">retained (recall pass, fresh)</text>
    <g fill="var(--ink)">
      <text x="20" y="40">evals-basic</text><text x="150" y="40" fill="var(--s1)">done</text><text x="410" y="40" fill="var(--s1)">retained</text>
      <text x="20" y="60">evals-inter</text><text x="150" y="60" fill="var(--s1)">done</text><text x="410" y="60" fill="var(--s2)">DECAYED (90d)</text>
      <text x="20" y="80">harness-basic</text><text x="150" y="80" fill="var(--s1)">done</text><text x="410" y="80" fill="var(--s2)">NEVER TESTED</text>
      <text x="20" y="100">retr-basic</text><text x="150" y="100" fill="var(--s1)">done</text><text x="410" y="100" fill="var(--s1)">retained</text>
      <text x="20" y="120">retr-inter</text><text x="150" y="120" fill="var(--muted)">draft</text><text x="410" y="120" fill="var(--muted)">-</text>
      <text x="20" y="140">govern-basic</text><text x="150" y="140" fill="var(--s1)">done</text><text x="410" y="140" fill="var(--s1)">retained</text>
    </g>
    <line x1="360" y1="26" x2="360" y2="150" stroke="var(--grid)" stroke-dasharray="3 3"></line>
    <text x="20" y="168" fill="var(--muted)">5 authored, 3 retained — the two-module gap is a decayed pass and an untested module.</text>
  </g>
</svg>
^ The two columns rarely match. Authoring marks five done; retention keeps only the three with a fresh recall pass, dropping the decayed one and the never-tested one. The gap is the unearned progress.

### The measurement, and the decay

Progress is the two counts side by side.

```
# progress.py:57-60 — COMPLETE (authored count vs retained count)
def counts(now, modules):
    a = sum(1 for m in modules if authored(m))
    r = sum(1 for m in modules if retained(now, m))
    return a, r
```

Five authored, three retained. The decay half is worth seeing on its own — a module that was genuinely learned once and has aged out:

```
# $ python3 progress.py --stale
#   harness-basic  never passed a recall check
#   evals-inter    last pass day 110, 90 days ago -> decayed
```

run: 2026-08-25 · fixture · `python3 progress.py --stale`

These are not failures of authoring; they are the honest maintenance list. `evals-inter` was learned and needs a refresh; `harness-basic` was never assessed and needs a first pass. A retention-based tracker turns "we're at five of six" into "three are current, two need a recall pass," which is the difference between a progress bar and a study plan.

<svg viewBox="0 0 700 140" role="img" aria-label="A timeline to now at day 200 with a 60-day retention window starting at day 140. A pass at day 190 falls inside the window (retained). A pass at day 110 falls before the window (decayed). A pass at day 196 is fresh.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">retention window: a pass must land after day 140 (now 200 minus 60)</text>
    <line x1="40" y1="70" x2="660" y2="70" stroke="var(--grid)"></line>
    <rect x="470" y="55" width="170" height="30" fill="var(--acc-soft)"></rect>
    <text x="480" y="100" fill="var(--acc-ink)" font-size="8">window: retained</text>
    <line x1="470" y1="48" x2="470" y2="92" stroke="var(--acc-line)" stroke-dasharray="3 2"></line><text x="440" y="44" fill="var(--muted)">day 140</text>
    <circle cx="290" cy="70" r="5" fill="var(--s2)"></circle><text x="255" y="58" fill="var(--s2)">pass day 110</text><text x="255" y="122" fill="var(--s2)" font-size="8">decayed</text>
    <circle cx="590" cy="70" r="5" fill="var(--s1)"></circle><text x="560" y="58" fill="var(--s1)">pass day 190</text><text x="565" y="122" fill="var(--s1)" font-size="8">retained</text>
    <circle cx="640" cy="70" r="4" fill="var(--s1)"></circle>
    <text x="648" y="73" fill="var(--ink)" font-size="8">now</text>
  </g>
</svg>
^ Two passes, one window. The day-190 pass is inside the 60-day window and counts; the day-110 pass fell out the back of the window as time moved the window forward, so a module that was genuinely learned is no longer retained. The window slides; retention is not permanent.

**A checkmark records that a module was made; only a dated, unexpired recall pass records that it was learned — count the second, and treat the gap as the work that remains.**

The self-test pins down both overcounts and the decay rule:

```
# $ python3 progress.py --check
#   authored=5  retained=3
#   authored count overstates retained learning = True (5 > 3)
#   authored-but-never-tested modules = ['harness-basic']
#   authored-but-stale modules = ['evals-inter']
#   never-tested modules are not retained = True
#   stale modules are not retained = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 progress.py --check`

## Build

The pipeline in one paragraph: record a dated, closed-book recall pass every time a learner reproduces a module from memory; define a retention window past which a pass no longer counts; and report progress as the number of modules with a within-window pass, never as the number authored or read. Never let a checkmark stand in for a recall pass, and never count a decayed pass as current.

We opened on the two counts. The one that is honest:

```
# modules/teaching-and-portability/code/teach-basic-01/ — COMPLETE, run from that directory
$ python3 progress.py --progress
  retained (really done)  3/6
```

Now track your own learning. Keep a recall ledger with a dated entry per closed-book pass, pick a retention window honest to how fast you forget, and compute retained-versus-authored. Your number to beat is the **retained count**, and your maintenance list is the stale-and-untested set — those are the modules to schedule next. Let a pass age past your window and confirm it drops out of retained. Bring back the two counts and your stale list. Good luck.

## Definition of done

- [ ] A recall ledger with a dated, closed-book pass per module reproduction
- [ ] A retention window past which a pass no longer counts
- [ ] A retained status requiring a within-window pass, not just authoring
- [ ] Your own `ledger.json` including a never-tested module and a decayed one
- [ ] Authored count kept alongside retained, so the overcount is measured
- [ ] `python3 progress.py --check` printing SELF-TEST PASS: authored overcounts, never-tested and stale excluded, drafts excluded
- [ ] The retained count and the stale-and-untested maintenance list recorded
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A curriculum is "5 of 6 done" by authoring and "3 of 6" by retention. Explain the two different reasons a module can be authored but not retained.
2. Why is "modules authored" the teacher's metric and not the learner's? Give the metric that is the learner's.
3. State the two conditions the retained check requires, and which kind of lying checkmark each one rules out.
4. A module passed a recall check 90 days ago with a 60-day window. Is it retained? What does it need?
5. Your own ledger produced a retained count and a stale list. What were they, and which module will you refresh first?

## External resources

- The hub's own recall ledger (`ledger/recall-ledger.json`) and `recall_gate.py` pattern — my summary: the mechanically-enforced spaced-recall gate this module measures; read it for the schema a boss-fight pass writes, and note the scan's caveat that its ledger has zero dated passes — assessment designed but never run.
- Ebbinghaus / the spacing effect, modern review — https://www.gwern.net/Spaced-repetition — my summary: the empirical forgetting curve and why spaced review beats massed study; read it for where the retention window comes from and how to set one honestly for your own memory.
- Bjork, *desirable difficulties* and testing effect — https://bjorklab.psych.ucla.edu/research/ — my summary: the finding that retrieval practice (a recall test) produces more durable learning than re-reading; read it for why a closed-book pass, not exposure, is the right unit of "learned" this whole hub is built on.
