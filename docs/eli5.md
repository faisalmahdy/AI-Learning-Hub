# ELI5 — the Evals & Statistics track, explained simply

Plain-language companions to the five modules in [`modules/evals-and-statistics/`](../modules/evals-and-statistics/). The modules themselves stay rigorous — real code, real numbers, honest intervals. These are the "explain it like I'm five" versions: one everyday picture per module, so the idea sticks before the math does.

Each links to the real thing. If a blurb makes you curious, open the module.

## 1. Three graders, thirty answers → [`evals-basic-01`](../modules/evals-and-statistics/evals-basic-01.md)

Imagine three robots grading the same 30 homework answers.

- **Robot 1** only says "correct" if your answer matches the answer key *letter for letter*. It fails almost everything — even right answers written in different words.
- **Robot 2** counts *how many words* you share with the answer key. It hands a big score to an answer that copied everything but swapped one number (137 where the truth is 37).
- **Robot 3** asks six real yes/no questions: did you name a real source? did you say anything false? did you refuse when you should have?

The big idea: a grader that agrees with you can still be **broken**, and the way you catch it is when two graders **disagree** about the same answer. Nine times out of thirty here, they do.

## 2. Did B really beat A? → [`evals-inter-01`](../modules/evals-and-statistics/evals-inter-01.md)

Two kids, A and B, do the same 30 puzzles. B gets more right. But some puzzles are just *hard for everybody*, so scores bounce around.

Weigh each kid on a wobbly bathroom scale and their ranges overlap — you'd shrug and say "same." The trick: because they did the **same** puzzles, compare them *puzzle by puzzle*, like a see-saw weighing the two directly against each other. The wobble that hits both sides cancels out, and now you can actually prove B is ahead instead of just lucky.

The big idea: **overlapping error bars fool you. The real question lives on the *difference*, and the difference has its own, much tighter bar.**

## 3. Can you trust the robot judge? → [`evals-inter-02`](../modules/evals-and-statistics/evals-inter-02.md)

You hire a robot to grade essays, and it agrees with the teacher 80% of the time. Sounds great!

But a lazy robot that stamps "PASS" on *everything* already agrees 63% of the time — because most essays pass anyway. So the robot's *real* skill is only the sliver above what a rubber stamp gets for free. And worse: this judge waves through **half the bad essays**, which are the whole reason you built a grader.

The big idea: **measure a judge against a real answer key before you trust it**, and use a fair score (called kappa) that subtracts the free agreement a lazy stamp would collect.

## 4. One try is a lie → [`evals-inter-03`](../modules/evals-and-statistics/evals-inter-03.md)

A basketball player sinks one free throw. Can they shoot? You have no idea — it was *one shot*.

Watch five: four in, one clank. Now three different questions have three different answers:

- "Will at least one go in?" → almost always yes.
- "What's their make rate?" → four in five.
- "Will *all five* go in?" → nope, one clanked.

Rank players by a single shot and you crown the flashy streaky one. But the player you actually want is the steady one who quietly sinks all five, every time.

The big idea: **"it worked once" is not "it works."** Reliability is a different question from average, and it has a different answer.

## 5. Does the upgrade really help? → [`evals-adv-01`](../modules/evals-and-statistics/evals-adv-01.md) (the capstone)

Two robot coders — plain and upgraded — fix the same 15 broken programs. A program counts as "fixed" only when its own tests pass, so nobody argues about grades: the tests decide.

The upgraded one fixes 60% vs 40% — a real win. **But**:

- If you'd stopped at 5 programs, it looked like an *even bigger* win that you actually couldn't prove yet.
- It only *reliably* fixes about a quarter of them.
- If you'd cheated by keeping each robot's best-of-three try, you'd have bragged "87%!"

The big idea: **a benchmark number is only a real claim when it comes with an honest "maybe this much" range — and you say it no more strongly than your data allows.**

---

*These blurbs are companions, not replacements. Every number above is real and comes from the module's own runnable script; the modules show the working.*
