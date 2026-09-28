---
id: selfconsist-inter-01
title: Majority-vote accuracy is a different number from single-sample accuracy — report the one you deploy
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: For a task with a verifiable answer, sampling the model once returns an answer that is right with some probability, and sampling it k times and keeping the most common answer (self-consistency) changes the score. When the model's probability concentrates on the correct answer while its mistakes scatter across many different wrong answers, the correct answer is the plurality even on questions where a single draw is more often wrong than right, so majority-vote accuracy lands above single-sample accuracy. The two numbers measure different systems — one call versus k calls plus a vote — and both are legitimate but not interchangeable: reporting the majority-vote number for a product that makes one call per request overstates it, and reporting single-sample accuracy for a pipeline that votes understates it. Voting has a hard limit worth stating: it can only surface an answer the samples actually contain as their plurality, so when the model is systematically wrong — most samples give the same incorrect answer — the plurality is that wrong answer and voting confidently returns it. On the fixture four questions each have five samples with gold A: the mean single-sample accuracy is 0.45 and the majority-vote accuracy is 0.75, a gap of 0.30; one question is rescued by voting although only 40% of its individual samples are correct, and one has a wrong majority (three of five samples agree on B) that voting cannot fix. The rule: self-consistency amplifies a model that is right on average and cannot repair one that is wrong on average, and the eval must report the accuracy of whatever inference procedure actually ships.
eli5: Imagine asking a slightly unsure friend the same question five times, and going with whatever answer they gave most. If they mostly know the topic, their right answer comes up more than any single wrong guess, so taking the most-common answer does better than trusting a single reply — even on a question they only got right two times out of five, because their two "correct"s beat any one wrong answer that only came up once. But if they've genuinely got the wrong idea and keep giving the same wrong answer, asking five times just gives you that wrong answer five times — voting can't invent knowledge they don't have. And if you tell people "my friend is 75% accurate" based on the best-of-five game, but then only ask once in real life, you've oversold them.
---

## Why this module

Sampling a model several times and taking the consensus — self-consistency — is one of the cheapest ways to raise accuracy on tasks with a checkable answer, and it is widely used. It also quietly creates two different accuracy numbers for the same model, and mixing them up is a common way benchmark claims and production reality diverge.

The number you report has to be the number you run. A leaderboard entry produced by voting over dozens of samples is not the accuracy a user gets from a single call, and a single-call accuracy understates a system that votes. The gap is not noise; it is real capability that lives in the aggregation step, and attributing it to the wrong configuration misleads everyone downstream.

**Single-sample and majority-vote accuracy measure different inference procedures, so an eval must report the one that ships.**

## Concepts

Consider one question the model answers by sampling. A single sample is correct with some probability — call it the question's single-sample accuracy. Majority vote takes k samples and returns whichever answer appears most often. Whether that helps depends on how the model's probability is distributed over answers.

The favorable case is the common one. A capable-but-noisy model puts more probability on the correct answer than on any single wrong answer, but spreads its errors across many different wrong answers. Then even when a single sample is more often wrong than right — say the correct answer has 40% of the mass and three wrong answers split the other 60% — the correct answer is still the plurality, because no wrong answer individually beats it. Majority vote picks it, and the question that a single sample usually got wrong is now reliably right.

Aggregated over a test set, this makes majority-vote accuracy exceed single-sample accuracy. The two are honest measurements of two different systems: single-sample is one model call; majority vote is k calls and a tally. Report the voted number for a product that calls once and you have overstated it by the gap; report the single number for a pipeline that votes and you have hidden capability you are actually shipping.

The limit is as important as the lift. Voting can only return an answer that is present as the plurality of the samples. When the model is systematically wrong about a question — most of its samples land on the same incorrect answer — the plurality is that wrong answer, and voting returns it with more confidence, not less. Self-consistency amplifies a model that is right on average and cannot repair one that is wrong on average; more samples of a confident error just confirm the error.

**Majority vote lifts accuracy where the correct answer is the plurality, even below 50% single-sample; it cannot help where the model's plurality is itself wrong.**

<svg role="img" aria-label="Two questions. Noisy-but-right: the correct answer has the tallest bar and wrong answers are short and scattered, so voting picks correct. Systematically wrong: a wrong answer has the tallest bar, so voting picks it." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="11">when voting helps, and when it can't</text>
<text x="20" y="40" fill="var(--s2)" font-size="9">noisy but right: correct is the plurality</text>
<rect x="30" y="46" width="20" height="24" fill="var(--s2)"></rect>
<rect x="52" y="58" width="20" height="12" fill="var(--s1)"></rect>
<rect x="74" y="58" width="20" height="12" fill="var(--s1)"></rect>
<rect x="96" y="62" width="20" height="8" fill="var(--s1)"></rect>
<text x="118" y="66" fill="var(--s2)" font-size="8">&#8594; vote = correct</text>
<text x="20" y="102" fill="var(--s1)" font-size="9">systematically wrong: a wrong answer is the plurality</text>
<rect x="30" y="108" width="20" height="12" fill="var(--s2)"></rect>
<rect x="52" y="96" width="20" height="24" fill="var(--s1)"></rect>
<rect x="74" y="112" width="20" height="8" fill="var(--s1)"></rect>
<text x="118" y="116" fill="var(--s1)" font-size="8">&#8594; vote = wrong</text>
</svg>
^ Voting returns the tallest bar; it wins when the correct answer's mass beats every single wrong answer, and loses when the model has piled its mass on one wrong answer.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/evals-and-statistics/code/selfconsist-inter-01/selfconsist.py

The fixture is four questions, each answered five times, all with gold answer A.

```json filename=modules/evals-and-statistics/code/selfconsist-inter-01/selfconsist.json:3-8 COMPLETE
  "questions": [
    {"gold": "A", "samples": ["A", "B", "A", "A", "C"]},
    {"gold": "A", "samples": ["B", "A", "A", "C", "A"]},
    {"gold": "A", "samples": ["C", "A", "B", "A", "D"]},
    {"gold": "A", "samples": ["B", "B", "B", "A", "C"]}
  ]
```

Single-sample accuracy is the fraction of a question's samples that are correct; majority vote takes the most common sample.

```python filename=modules/evals-and-statistics/code/selfconsist-inter-01/selfconsist.py:31-33 COMPLETE
def single_accuracy(q):
    """The chance one random sample is correct: the fraction of this question's samples that match the gold."""
    return sum(1 for s in q["samples"] if s == q["gold"]) / len(q["samples"])
```

```python filename=modules/evals-and-statistics/code/selfconsist-inter-01/selfconsist.py:36-38 COMPLETE
def majority_answer(q):
    """The answer that appears most often among the samples -- what self-consistency returns."""
    return Counter(q["samples"]).most_common(1)[0][0]
```

```text filename=selfconsist.py --single
SINGLE — one sample per question (gold in parentheses)
----------------------------------------------------------------
  q1 (A): ['A', 'B', 'A', 'A', 'C']  single-sample acc 0.6
  q2 (A): ['B', 'A', 'A', 'C', 'A']  single-sample acc 0.6
  q3 (A): ['C', 'A', 'B', 'A', 'D']  single-sample acc 0.4
  q4 (A): ['B', 'B', 'B', 'A', 'C']  single-sample acc 0.2
  mean single-sample accuracy = 0.45
----------------------------------------------------------------
  this is what one call per question scores on average
```

One call per question averages 0.45 accuracy. Q3 is right only 40% of the time per sample, and Q4 only 20% — a single call fails both more often than not.

<svg role="img" aria-label="For question 3, the five samples: A appears twice, and C, B, D once each. The correct answer A is the plurality even though it is only 40% of the samples, because the wrong answers are split." viewBox="0 0 320 130">
<rect x="0" y="0" width="320" height="130" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">q3 samples: A is the plurality at only 40%</text>
<line x1="40" y1="100" x2="300" y2="100" stroke="var(--line)"></line>
<rect x="60" y="50" width="40" height="50" fill="var(--s2)"></rect>
<text x="72" y="114" fill="var(--muted)" font-size="9">A: 2</text>
<rect x="120" y="75" width="40" height="25" fill="var(--s1)"></rect>
<text x="132" y="114" fill="var(--muted)" font-size="9">C: 1</text>
<rect x="180" y="75" width="40" height="25" fill="var(--s1)"></rect>
<text x="192" y="114" fill="var(--muted)" font-size="9">B: 1</text>
<rect x="240" y="75" width="40" height="25" fill="var(--s1)"></rect>
<text x="252" y="114" fill="var(--muted)" font-size="9">D: 1</text>
<text x="60" y="42" fill="var(--s2)" font-size="9">correct A wins the vote though it is a minority of samples</text>
</svg>
^ The correct answer A has more samples than any single wrong answer, so it is the plurality and wins the vote — even though it is only two of five, because the errors are scattered.

## Build

Majority vote tallies the plurality per question and scores the fraction that are correct.

```python filename=modules/evals-and-statistics/code/selfconsist-inter-01/selfconsist.py:51-53 COMPLETE
def majority_accuracy(questions):
    """Majority-vote accuracy across questions: the fraction whose plurality answer is correct."""
    return sum(1 for q in questions if majority_correct(q)) / len(questions)
```

```text filename=selfconsist.py --majority
MAJORITY — take the most common of the 5 samples per question
----------------------------------------------------------------
  q1 (A): majority A  correct? True
  q2 (A): majority A  correct? True
  q3 (A): majority A  correct? True
  q4 (A): majority B  correct? False   <- wrong majority (systematic error)
  majority-vote accuracy = 0.75
----------------------------------------------------------------
  voting lifts the score where the correct answer is the plurality
```

Voting gets q1, q2, and q3 right — including q3, whose single-sample accuracy was only 0.4 — for a majority-vote accuracy of 0.75, well above the 0.45 single-sample number. But q4's plurality is B: the model gave B three times out of five, so it is systematically wrong here, and voting returns B confidently. Voting fixed the scattered errors and could not touch the systematic one.

<svg role="img" aria-label="Two bars: single-sample accuracy 0.45 and majority-vote accuracy 0.75, with the gap of 0.30 marked between them." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">single-sample vs majority-vote accuracy</text>
<line x1="50" y1="120" x2="300" y2="120" stroke="var(--line)"></line>
<rect x="90" y="66" width="50" height="54" fill="var(--s1)"></rect>
<text x="92" y="60" fill="var(--s1)" font-size="10">single 0.45</text>
<rect x="200" y="30" width="50" height="90" fill="var(--s2)"></rect>
<text x="202" y="24" fill="var(--s2)" font-size="10">majority 0.75</text>
<line x1="160" y1="66" x2="160" y2="30" stroke="var(--muted)" stroke-dasharray="3 3"></line>
<text x="150" y="52" fill="var(--muted)" font-size="9">gap 0.30</text>
</svg>
^ The gap of 0.30 between the two numbers is real capability from the voting step — reporting the wrong one over- or under-states the shipped system by exactly that.

The self-test states the lift, the rescue, and the limit.

```python filename=modules/evals-and-statistics/code/selfconsist-inter-01/selfconsist.py:86-92 COMPLETE
    ms, mv = mean_single(qs), majority_accuracy(qs)
    majority_beats_single = mv > ms
    print("  majority-vote accuracy beats single-sample = %s (%.2f > %.2f, gap %.2f)" % (majority_beats_single, mv, ms, mv - ms))

    rescued = [i + 1 for i, q in enumerate(qs) if majority_correct(q) and single_accuracy(q) < 0.5]
    majority_rescues = len(rescued) > 0
    print("  voting rescues a question whose single-sample accuracy is below half = %s (questions %s)" % (majority_rescues, rescued))
```

```text filename=selfconsist.py --check
SELF-TEST — majority-vote accuracy exceeds single-sample accuracy, voting rescues a below-half question, and it cannot fix a wrong-majority question
----------------------------------------------------------------------------------------------------------------
  majority-vote accuracy beats single-sample = True (0.75 > 0.45, gap 0.30)
  voting rescues a question whose single-sample accuracy is below half = True (questions [3])
  a wrong-majority question exists that voting cannot fix = True (questions [4])
  the report-vs-deploy gap is 0.30 = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  majority_beats_single=True  majority_rescues=True  cannot_fix_systematic=True  gap_is_real=True
```

**cannot_fix_systematic is the ceiling on the technique: voting concentrates the samples' plurality, so it amplifies a model that is right on average and confirms one that is wrong on average.**

## Definition of done

You can explain why majority vote raises accuracy when the correct answer is the plurality, even on a question a single sample gets right less than half the time.

You can state why single-sample and majority-vote accuracy are numbers for different systems, and why reporting one while deploying the other misstates the product by their gap.

You can describe the limit — voting cannot fix a question whose plurality answer is wrong — and connect it to the model being systematically wrong rather than noisily wrong.

You can distinguish this from pass@k: majority vote returns one consensus answer and needs the correct answer to be the plurality, while pass@k asks only whether any of the k samples is correct.

## Boss fight

A benchmark result reports 78% on a math task, and it turns out the number was produced by sampling 64 times per question and taking the majority. Your product calls the model once per question and users report accuracy nearer 60%.

First: explain why the two numbers differ and why neither is "wrong" — what system does each measure, and why is the 78% not achievable at one call per question?

Then: you want the product to get closer to 78%. Self-consistency costs k times the calls. Explain the accuracy-versus-cost curve — why the first few extra samples help the most and later ones help less — and how you would choose k for a latency- and cost-bounded product rather than a leaderboard.

Finally: some questions in the set are ones the model is systematically wrong about (its plurality is a confident wrong answer). Explain why spending more samples on those questions is pure waste, and what signal in the sample distribution (how concentrated the plurality is) you could use to decide when extra samples are worth it versus when the model has simply made up its mind incorrectly.

## External resources

The self-consistency paper (Wang et al., "Self-Consistency Improves Chain of Thought Reasoning") introduces sampling multiple reasoning paths and taking the majority answer, and reports exactly this lift over single-sample decoding on math and reasoning benchmarks.

Discussions of pass@k versus majority@k (for example in code- and math-eval methodology) draw the distinction this module's boss fight rests on: pass@k credits any correct sample, majority@k credits the consensus, and they reward very different model behaviors.
