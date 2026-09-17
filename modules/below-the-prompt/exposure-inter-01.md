---
id: exposure-inter-01
title: Teacher forcing hides a model's real error rate — feeding its own predictions at inference lets one mistake cascade
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: An autoregressive model predicts the next token from the tokens before it, and it is trained by teacher forcing: at every position it is shown the ground-truth previous tokens and asked only to predict the next one, scored against the true next token. Teacher forcing is efficient and stable — every position gets a correct context, all positions train in parallel, and each step's gradient is clean — but it trains the model in a world it never inhabits at inference. At generation time there is no ground truth to feed: the model must consume its own previous predictions, so a wrong token becomes the context for the next step, and the next. This mismatch is exposure bias: during training the model is only ever exposed to correct prefixes, so it never learns to recover from its own mistakes, and a single early error at inference puts it into a state it was never trained on, from which the error compounds. The measured teacher-forced error rate therefore understates the generation error rate, because teacher forcing resets the context to the truth after every step and never lets an error propagate. On a fixture where the true rule is next=current+1 and the model errs only at token 3 (predicts 5, not 4), teacher forcing makes exactly 1 error out of 7 predictions, while free-running generation produces 0,1,2,3,5,6,7,8 — wrong at 4 of the 7 positions after the start, all cascading from that one mistake.
eli5: Imagine practicing a song where, every time you hit a wrong note, a teacher instantly plays the correct note so you can keep going from the right place. You'd sound almost perfect in practice — one slip, immediately fixed. But at the real concert there's no teacher: when you hit that same wrong note, you keep playing from where your fingers actually are, and now every note after it is off, because you built the rest of the song on top of the mistake. That's the trap — practicing with a helpful teacher who always corrects you hides how badly one small error snowballs when you're finally on your own.
---

## Why this module

The way we train a sequence model and the way we run it are two different worlds, and the model only ever lives in one of them until inference day. In training, teacher forcing hands the model a perfect history at every step and asks for just the next token — so it learns to continue correct text, and its loss looks at how often it gets that single next token right given a flawless past. In generation, there is no flawless past to hand it; the model must build on whatever it produced a moment ago, mistakes included. A model that has only ever seen correct prefixes has never practiced the one thing generation demands: continuing from its own error.

An autoregressive model is trained by teacher forcing — at every position it is shown the ground-truth previous tokens and asked only to predict the next, scored against the true next token. This is efficient and stable, but it trains the model in a world it never inhabits at inference, where the model must consume its own previous predictions, so a wrong token becomes the context for the next step, and the next.

This mismatch is called exposure bias. During training the model is only ever exposed to correct prefixes, so it never learns to recover after a mistake, and at inference a single early error puts it into a state it was never trained on, from which the error can compound. The measured teacher-forced error rate systematically understates the generation error rate, because teacher forcing resets the context to the truth after every step and never lets an error propagate. This module runs the same model both ways.

**The teacher-forced (training) error rate understates generation error, because teacher forcing always feeds the true previous token while inference feeds the model's own prediction — so a single early mistake, kept local by teacher forcing resetting the context to the truth, cascades under free-running generation; evaluate a sequence model by generating, not only by teacher-forced loss.**

## Concepts

**Teacher forcing feeds the true previous token at every step** and scores each prediction against the true next — so an error at one step cannot affect the context of the next.

```python filename=modules/below-the-prompt/code/exposure-inter-01/exposure.py:55-66 COMPLETE
def predict(model, token):
    """The model's learned next-token prediction given the current token."""
    return model[str(token)]


def teacher_forced(true_seq, model):
    """Feed the TRUE previous token at every step; compare each prediction to the true next token."""
    preds = []
    for i in range(len(true_seq) - 1):
        p = predict(model, true_seq[i])          # context is always the ground truth
        preds.append((true_seq[i], p, true_seq[i + 1], p == true_seq[i + 1]))
    return preds
```

**Free-running generation feeds the model's own last output** back in as the next context — the loop the model actually runs at inference, where an error becomes the next step's input.

```python filename=modules/below-the-prompt/code/exposure-inter-01/exposure.py:69-74 COMPLETE
def free_run(true_seq, model):
    """Feed the model's OWN previous prediction at every step, starting from the true first token."""
    out = [true_seq[0]]
    for _ in range(len(true_seq) - 1):
        out.append(predict(model, out[-1]))      # context is the model's own last output
    return out
```

<svg role="img" aria-label="Two loops: teacher forcing feeds the true token back into the model at each step, so a wrong prediction is discarded; free-running feeds the model's own prediction back, so a wrong prediction becomes the next input" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">what gets fed back decides whether an error survives</text>
  <text x="10" y="30" fill="var(--s1)" font-size="7">teacher forcing</text>
  <rect x="20" y="36" width="40" height="18" fill="none" stroke="var(--ink)"/><text x="28" y="48" fill="var(--ink)" font-size="7">model</text>
  <text x="70" y="42" fill="var(--muted)" font-size="6">predicts → (scored, discarded)</text>
  <path d="M40 54 L40 66 L14 66 L14 45 L20 45" fill="none" stroke="var(--s1)"/><text x="44" y="70" fill="var(--s1)" font-size="6">feed TRUE token back</text>
  <line x1="14" y1="80" x2="286" y2="80" stroke="var(--grid)"/>
  <text x="10" y="96" fill="var(--s2)" font-size="7">free-running</text>
  <rect x="20" y="100" width="40" height="16" fill="none" stroke="var(--ink)"/><text x="28" y="111" fill="var(--ink)" font-size="7">model</text>
  <path d="M60 108 L80 108 L80 92 L36 92 L36 100" fill="none" stroke="var(--s2)"/><text x="84" y="98" fill="var(--s2)" font-size="6">feed OWN prediction back (error and all)</text>
</svg>
^ Under teacher forcing the true token is fed back regardless of what the model predicted, so a wrong prediction is scored and thrown away; under free-running generation the model's own prediction is fed back, so a wrong prediction becomes the next step's context — the feedback source is the whole difference.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/exposure-inter-01/exposure.py

The fixture is the true sequence (rule next=current+1) and the model's learned map, which is correct everywhere except at token 3.

```json filename=modules/below-the-prompt/code/exposure-inter-01/exposure.json:3-4 COMPLETE
  "true_sequence": [0, 1, 2, 3, 4, 5, 6, 7],
  "model_transition": {"0": 1, "1": 2, "2": 3, "3": 5, "4": 5, "5": 6, "6": 7, "7": 8}
```

Run `--teacher`.

```text filename=--teacher
TEACHER FORCING — fed the true previous token at every step
--------------------------------------------------------------
  step  context(true)  predicts  true next  ok?
  0     0              1         1          ok
  1     1              2         2          ok
  2     2              3         3          ok
  3     3              5         4          WRONG
  4     4              5         5          ok
  5     5              6         6          ok
  6     6              7         7          ok
--------------------------------------------------------------
  errors: 1 of 7 predictions -- the mistake at token 3 stays local.
```

Read down the teacher-forced run. At every step the context is the true token, so the model predicts correctly at steps 0, 1, 2, and then at step 3 it makes its one learned mistake: given the true token 3 it predicts 5 instead of 4. That is scored WRONG — but look at step 4: the context is the *true* 4, not the model's erroneous 5, because teacher forcing feeds ground truth regardless of what the model just said. So step 4 continues correctly, and so do 5 and 6. The single error is quarantined; it never touches another step. The teacher-forced error count is 1 out of 7, an error rate of about 14%, and that is the number a training or validation loss would report — a model that looks 86% correct, quite good.

## Build

Now run the model the way inference actually runs it, feeding its own output back.

```text filename=--generate
GENERATE — fed the model's own previous prediction at every step
------------------------------------------------------------
  position  generated  true   ok?
  0         0          0      ok
  1         1          1      ok
  2         2          2      ok
  3         3          3      ok
  4         5          4      WRONG
  5         6          5      WRONG
  6         7          6      WRONG
  7         8          7      WRONG
------------------------------------------------------------
  generated [0, 1, 2, 3, 5, 6, 7, 8] vs true [0, 1, 2, 3, 4, 5, 6, 7]
  errors: 4 of 8 positions -- one mistake at token 3 shifted every token after it.
```

<svg role="img" aria-label="Two sequences on parallel tracks: the true sequence 0 through 7, and the generated sequence 0,1,2,3,5,6,7,8 which matches until position 4 then runs one step ahead, wrong at every position after the divergence" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">one error at token 3 shifts the whole trajectory</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">true</text>
  <g font-size="8" fill="var(--ink)"><text x="44" y="34">0</text><text x="74" y="34">1</text><text x="104" y="34">2</text><text x="134" y="34">3</text><text x="164" y="34">4</text><text x="194" y="34">5</text><text x="224" y="34">6</text><text x="254" y="34">7</text></g>
  <text x="10" y="60" fill="var(--muted)" font-size="7">generated</text>
  <g font-size="8"><text x="44" y="60" fill="var(--s1)">0</text><text x="74" y="60" fill="var(--s1)">1</text><text x="104" y="60" fill="var(--s1)">2</text><text x="134" y="60" fill="var(--s1)">3</text><text x="164" y="60" fill="var(--s2)">5</text><text x="194" y="60" fill="var(--s2)">6</text><text x="224" y="60" fill="var(--s2)">7</text><text x="254" y="60" fill="var(--s2)">8</text></g>
  <line x1="158" y1="24" x2="158" y2="68" stroke="var(--s2)" stroke-dasharray="2 2"/><text x="150" y="82" fill="var(--s2)" font-size="6">error here (5 not 4)</text>
  <text x="164" y="96" fill="var(--muted)" font-size="6">from here on, generated runs one ahead — every token wrong</text>
</svg>
^ The generated sequence matches the truth through token 3, then the one error (5 instead of 4) makes it run a step ahead of the truth for the rest of the sequence — positions 4–7 are all wrong, not from new mistakes but from the trajectory shift the single error caused.

The free-running sequence is correct through position 3, then diverges and never comes back: 0, 1, 2, 3, and then 5 (the model's error at token 3), and from 5 it predicts 6, from 6 predicts 7, from 7 predicts 8. Positions 4 through 7 are all wrong. But notice *why* they are wrong: the model made only one actual mistake — the 5-instead-of-4 at token 3, the exact same mistake teacher forcing recorded. Every subsequent error is not a new failure of the model; it is the model faithfully applying its correct rule (add one) to a context that is off by one because of that first error. The mistake did not multiply the model's errors; it shifted the trajectory into a region where every correct prediction is nonetheless wrong relative to the truth. This is the essence of exposure bias: teacher forcing measured one error because it kept resetting the context to the truth, and generation reveals four because it lets the one error persist in the context. The training number was not wrong about the model's per-step accuracy; it was silent about what happens when the model must stand on its own output.

```python filename=modules/below-the-prompt/code/exposure-inter-01/exposure.py:114-124 COMPLETE
    tf_errors = sum(1 for _, _, _, ok in preds if not ok)
    teacher_one_error = tf_errors == 1
    print("  teacher-forced errors = %d -> exactly one = %s" % (tf_errors, teacher_one_error))

    gen_errors = sum(1 for i in range(len(true_seq)) if gen[i] != true_seq[i])
    generation_cascades = gen_errors > tf_errors
    print("  free-running generation errors = %d -> more than teacher forcing = %s" % (gen_errors, generation_cascades))

    first_div = next(i for i in range(len(true_seq)) if gen[i] != true_seq[i])
    cascade_from_one_root = all(gen[i] != true_seq[i] for i in range(first_div, len(true_seq)))
    print("  every position from the first divergence (pos %d) onward is wrong = %s" % (first_div, cascade_from_one_root))
```

## Definition of done

The self-test pins the single learned error, the one teacher-forced mistake, the four cascaded generation errors, and the rate the training number hides.

```python filename=modules/below-the-prompt/code/exposure-inter-01/exposure.py:126-132 COMPLETE
    single_learned_error = sum(1 for k, v in model.items() if v != int(k) + 1) == 1
    print("  the model has exactly one learned error (at token 3) = %s" % single_learned_error)

    tf_rate = tf_errors / len(preds)
    gen_rate = gen_errors / len(true_seq)
    training_understates = tf_rate < gen_rate
    print("  teacher-forced error RATE understates generation error rate = %s (%.3f vs %.3f)" % (training_understates, tf_rate, gen_rate))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — teacher forcing makes one local error; free-running generation cascades it into many (exposure bias)
----------------------------------------------------------------------------------------------------------------
  teacher-forced errors = 1 -> exactly one = True
  free-running generation errors = 4 -> more than teacher forcing = True
  every position from the first divergence (pos 4) onward is wrong = True
  the model has exactly one learned error (at token 3) = True
  teacher-forced error RATE understates generation error rate = True (0.143 vs 0.500)
```

<svg role="img" aria-label="Error rate: teacher forcing 1 of 7 (0.143), free-running generation 4 of 8 (0.500); the generation bar is more than three times the teacher-forced bar" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">error rate: teacher-forced 0.143 vs generation 0.500</text>
  <text x="10" y="38" fill="var(--muted)" font-size="7">teacher forcing</text>
  <rect x="110" y="28" width="46" height="14" fill="var(--s1)"/><text x="160" y="39" fill="var(--muted)" font-size="7">1/7 = 0.143</text>
  <text x="10" y="66" fill="var(--muted)" font-size="7">generation</text>
  <rect x="110" y="56" width="160" height="14" fill="var(--s2)"/><text x="150" y="66" fill="var(--panel)" font-size="7">4/8 = 0.500</text>
  <text x="10" y="86" fill="var(--muted)" font-size="6">same model, same one mistake — the training number hides the cascade</text>
</svg>
^ The teacher-forced error rate (1 of 7 = 0.143) is the number training reports; the free-running generation error rate (4 of 8 = 0.500) is what the model actually produces — more than triple, from the identical single mistake, because generation lets the error persist while teacher forcing erases it each step.

**Done means exposure bias is proven on one model: it has exactly one learned error (5 instead of 4 at token 3), teacher forcing records that as 1 error in 7 (rate 0.143) because it feeds the true token next, while free-running generation cascades it into 4 wrong positions out of 8 (rate 0.500) because it feeds the model's own output next — so a sequence model must be evaluated by generation, not only by teacher-forced loss.**

## Boss fight

Predict two things about exposure bias that the toy makes look simpler than it is, because the real phenomenon is a matter of degree and its fixes have their own costs.

The first trap is over-reading the toy's perfect cascade: real exposure bias is a tendency, not a guarantee, and its severity depends on whether the model can recover. In this fixture the model applies a deterministic "+1" to whatever it is given, so an off-by-one context produces an off-by-one output forever — the error is permanent because nothing pulls the trajectory back. A real language model is not so brittle: after a wrong token it often *can* recover, because natural language is redundant and the model has (accidentally, from noisy training data and the sheer variety of contexts) seen enough imperfect prefixes to right itself, and because sampling and the model's uncertainty give it room to move back toward plausible text. So exposure bias in practice ranges from negligible (the model shrugs off a slip) to catastrophic (a degenerate loop, a hallucinated fact that the model then "explains" and builds on) depending on the task, the decoding method, and how far off the error took it. The lesson is not "generation always cascades" but "teacher-forced loss cannot tell you which case you are in," so you must actually generate to find out — greedy loops, repetition, and drift are exactly the failures that a per-step teacher-forced metric is blind to.

The second trap is that the obvious fixes trade one problem for another and are not free. The classic remedy is to train on the model's own predictions sometimes — scheduled sampling: with some probability feed the model's generated token instead of the truth, annealing toward more self-feeding as training proceeds, so the model practices recovering from its own errors. But this breaks the clean, parallelizable teacher-forced objective (you now have a partly sequential, higher-variance training signal), and naive scheduled sampling can bias the learning objective in ways that hurt as much as they help. Sequence-level training objectives (optimizing a whole-sequence reward with reinforcement learning, or minimum-risk / beam-search training) attack exposure bias more directly by scoring generated sequences, but they are expensive, high-variance, and easy to get wrong. And RLHF-style fine-tuning, which trains on model-generated responses judged by a reward model, incidentally exposes the model to its own distribution and so mitigates exposure bias as a side effect — but introduces reward-hacking and distribution-shift concerns of its own. There is no free lunch: the reason teacher forcing dominates despite exposure bias is that it is stable, parallel, and cheap, and every fix that closes the train/inference gap reopens some of the instability that teacher forcing was chosen to avoid. The practical stance is to keep teacher forcing for the bulk of training, evaluate on real generation, and add targeted self-conditioning (scheduled sampling, or generation-based fine-tuning) only where the generation gap actually bites.

**Read exposure bias as a tendency, not a law: a robust model often recovers from a slip while a brittle one loops or drifts, and only real generation — not teacher-forced loss — reveals which, so evaluate by generating. And treat the fixes as trade-offs: scheduled sampling and sequence-level or generation-based objectives let the model practice recovering from its own errors but sacrifice the stable, parallel, cheap training that made teacher forcing the default, so close the train/inference gap deliberately where it hurts, not everywhere.**

## External resources

The scheduled-sampling paper (Bengio et al., 2015) and the exposure-bias / sequence-level training literature (MIXER, minimum-risk training, and critiques of scheduled sampling) — the formal statement of exposure bias and the objectives designed to reduce it.

Discussions of teacher forcing in seq2seq and language-model training (the deep-learning textbooks and framework tutorials) — why teacher forcing is the standard training regime, its parallelism and stability advantages, and its train/inference mismatch.

The companion sampling, repetition-penalty, and beam-search modules in this topic — degenerate generation (loops, drift) is exposure bias meeting a decoding strategy, and those modules address the inference-time symptoms that a teacher-forced training metric cannot see.
