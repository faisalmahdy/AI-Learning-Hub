---
id: labelshift-inter-01
title: Shift the labels one position ahead for next-token training — the target at position i is token i+1, or the model just learns to copy what it sees
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: A language model is trained by teacher forcing — it reads a prefix of tokens and predicts the token that comes next — so turning a sequence into training pairs needs a one-token shift between what the model reads and what it must produce: the target for the output at position i is tokens[i+1]. Concretely, inputs are tokens[:-1] and targets are tokens[1:], so position i means "given tokens 0..i, predict tokens[i+1]". The classic bug is to line the target up with the input at the same position, so the target at i is tokens[i] — the token the model, under a correct causal mask, can already see there. That objective is solved by the identity function: a model that does nothing but copy its input to its output gets every prediction right and drives the loss to zero, having learned nothing about which token follows which, and at generation time it can only echo what it was just given. The failure is easy to miss because it looks like success — the loss plummets, accuracy hits 100% — but the tell is that a trivial copy baseline achieves the same perfect score, which means the objective carries no signal. This is separate from the causal mask, which controls what the model may attend to; the shift controls what it is asked to predict, and a model with a correct mask but unshifted labels still learns the wrong task. On a fixture sequence, a copy model scores 100% under the same-position alignment and only 25% under the shifted one.
eli5: Imagine you're teaching someone to guess the next word in a sentence. The right game is: you show them "the cat sat on the" and they have to guess "mat" — a word you haven't shown them yet. That's a real challenge. But suppose you set up the game wrong, so that you show them the word "mat" and then ask them to guess... "mat". They'd get every single one right instantly, not because they understand sentences, but because you're asking them to name a word you just put in front of them. They could win by just repeating whatever you say. It would look like they aced the test, but they learned nothing. Training a language model has exactly this trap. The model must be asked to predict the NEXT token, one step ahead of what it can see — not the token it's already looking at. Line them up wrong by even one position and the model wins by copying, and learns nothing worth knowing.
---

## Why this module

Next-token prediction has a subtle bookkeeping requirement that is easy to get wrong and painful to detect. The model is a function from a prefix to a prediction, and what makes the prediction meaningful is that the answer lies just beyond the prefix — the model must produce a token it has not been shown. That "just beyond" is a one-position offset between the inputs it reads and the targets it is scored against, and getting the offset right is the whole game.

The offset is implemented as a shift: pair each position's output with the token one step ahead. Read tokens 0 through i, predict token i+1. In code this is usually inputs = tokens[:-1] and targets = tokens[1:] — the same sequence, sliced one apart. Do that and every training pair asks a genuine question, because the target is never a token the model was given.

Line the target up with the input at the same position instead, and the question stops being a question. Now the model is asked to predict the token sitting at its own position — a token it can see. The task collapses to copying, the loss goes to zero, and the metrics look wonderful while the model learns nothing about sequence structure. This module builds both alignments and scores a copy model on each to expose the collapse.

**Next-token prediction is meaningful only because the target lies one position beyond the input; shift the labels by one so the model predicts a token it has not seen, or the objective collapses into copying.**

## Concepts

The key property of a good training objective is that a trivial baseline cannot solve it. Prediction should be hard for a model that has learned nothing; if a do-nothing baseline scores perfectly, the objective is not measuring what you think. The same-position alignment fails exactly this test — the identity function, output equals input, is a do-nothing baseline that scores 100%, which is proof the objective carries no learning signal.

It helps to see why the causal mask does not save you. The mask controls attention: it forbids position i from attending to positions after i, so the model cannot peek at future tokens through the attention mechanism. But the mask says nothing about which token you score the output against. If you score position i's output against tokens[i], the model does not need to peek forward — the answer is the very token being fed in at that position, fully visible to it. The mask and the shift are orthogonal safeguards, and you need both: the mask stops attention-based cheating, the shift stops target-based cheating.

The one-token shift restores the difficulty by making the target a token the model has not been shown. Predicting tokens[i+1] from tokens[0..i] cannot be done by copying the input, so the copy baseline drops from perfect to chance, and only a model that actually learns which tokens follow which can score well. The shift is the single line that converts "repeat what you see" into "predict what comes next".

<svg role="img" aria-label="Two orthogonal safeguards: the causal mask controls what the model attends to, the label shift controls what token it is scored against; both are needed" viewBox="0 0 440 130">
<rect x="20" y="30" width="180" height="70" fill="var(--panel)" stroke="var(--line)"/>
<text x="110" y="52" fill="var(--ink)" font-size="10" text-anchor="middle">causal mask</text>
<text x="110" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">what it may attend to</text>
<text x="110" y="86" fill="var(--s1)" font-size="9" text-anchor="middle">stops attention peeking</text>
<rect x="240" y="30" width="180" height="70" fill="var(--panel)" stroke="var(--line)"/>
<text x="330" y="52" fill="var(--ink)" font-size="10" text-anchor="middle">label shift</text>
<text x="330" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">what it is scored against</text>
<text x="330" y="86" fill="var(--s1)" font-size="9" text-anchor="middle">stops target copying</text>
<text x="220" y="118" fill="var(--muted)" font-size="9" text-anchor="middle">orthogonal — a correct mask with unshifted labels still learns copying</text>
</svg>
^ The mask and the shift guard different doors — attention and target — so a correct mask does not rescue an unshifted label.

**A sound objective defeats the do-nothing baseline; the same-position target is aced by the identity function, and only the one-token shift — orthogonal to the causal mask — restores a target the model cannot simply copy.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/labelshift-inter-01. The fixture is a short token sequence; everything else is computed.

```json filename=modules/below-the-prompt/code/labelshift-inter-01/labelshift.json:3-3 COMPLETE
  "tokens": [5, 2, 8, 8, 1]
```

The buggy alignment pairs each position's target with the token already at that position.

```python filename=modules/below-the-prompt/code/labelshift-inter-01/labelshift.py:34-36 COMPLETE
def same_position(tokens):
    """The buggy alignment: the target at position i is tokens[i] -- the token already visible there."""
    return list(zip(tokens, tokens))
```

The correct alignment shifts the target one step ahead — the next token.

```python filename=modules/below-the-prompt/code/labelshift-inter-01/labelshift.py:39-41 COMPLETE
def shifted(tokens):
    """The correct alignment: the target at position i is tokens[i+1] -- the next token."""
    return list(zip(tokens[:-1], tokens[1:]))
```

A copy model just outputs whatever token it was given; its accuracy is how often the input already equals the target.

```python filename=modules/below-the-prompt/code/labelshift-inter-01/labelshift.py:44-49 COMPLETE
def copy_accuracy(pairs):
    """A copy model outputs its input token; how often does that equal the target?"""
    if not pairs:
        return 0.0
    correct = sum(1 for inp, tgt in pairs if inp == tgt)
    return correct / len(pairs)
```

Run `--align` to see the two sets of input-to-target pairs:

```text filename=labelshift.py --align
ALIGN — input -> target pairs under each alignment
--------------------------------------------------------
  same-position (target = tokens[i], the visible token):
    [(5, 5), (2, 2), (8, 8), (8, 8), (1, 1)]
  shifted-by-one (target = tokens[i+1], the next token):
    [(5, 2), (2, 8), (8, 8), (8, 1)]
```

The same-position pairs are all `(x, x)` — every target equals its own input. The shifted pairs are `(x, next)` — each target is the following token, and only one of them, `(8, 8)`, happens to repeat.

<svg role="img" aria-label="The token row 5 2 8 8 1 with same-position arrows pointing each token to itself, and shifted arrows pointing each token to the next one" viewBox="0 0 440 160">
<text x="30" y="44" fill="var(--muted)" font-size="9">same-pos</text>
<text x="100" y="44" fill="var(--ink)" font-size="13">5</text>
<text x="150" y="44" fill="var(--ink)" font-size="13">2</text>
<text x="200" y="44" fill="var(--ink)" font-size="13">8</text>
<text x="250" y="44" fill="var(--ink)" font-size="13">8</text>
<text x="300" y="44" fill="var(--ink)" font-size="13">1</text>
<path d="M100 30 A 8 8 0 1 1 104 30" fill="none" stroke="var(--s2)"/>
<path d="M150 30 A 8 8 0 1 1 154 30" fill="none" stroke="var(--s2)"/>
<path d="M200 30 A 8 8 0 1 1 204 30" fill="none" stroke="var(--s2)"/>
<path d="M250 30 A 8 8 0 1 1 254 30" fill="none" stroke="var(--s2)"/>
<path d="M300 30 A 8 8 0 1 1 304 30" fill="none" stroke="var(--s2)"/>
<text x="360" y="44" fill="var(--s2)" font-size="9">predict self</text>
<text x="30" y="110" fill="var(--muted)" font-size="9">shifted</text>
<text x="100" y="110" fill="var(--ink)" font-size="13">5</text>
<text x="150" y="110" fill="var(--ink)" font-size="13">2</text>
<text x="200" y="110" fill="var(--ink)" font-size="13">8</text>
<text x="250" y="110" fill="var(--ink)" font-size="13">8</text>
<text x="300" y="110" fill="var(--ink)" font-size="13">1</text>
<line x1="108" y1="105" x2="146" y2="105" stroke="var(--s1)"/>
<line x1="158" y1="105" x2="196" y2="105" stroke="var(--s1)"/>
<line x1="208" y1="105" x2="246" y2="105" stroke="var(--s1)"/>
<line x1="258" y1="105" x2="296" y2="105" stroke="var(--s1)"/>
<text x="360" y="110" fill="var(--s1)" font-size="9">predict next</text>
</svg>
^ Same-position asks each token to predict itself; the shift asks each token to predict the one after it.

Now score a copy model on each alignment. Predict: it should ace the same-position objective and fail the shifted one. Run `--score`:

```text filename=labelshift.py --score
SCORE — a copy model (output = input token) on each alignment
--------------------------------------------------------
  same-position   copy accuracy = 100%  (5/5)
  shifted-by-one  copy accuracy = 25%  (1/4)
```

The prediction holds. Copying scores a perfect 100% on the same-position objective — it is the identity function solving an identity task — and drops to 25% on the shifted one, getting only the lone repeated `(8, 8)` pair. A model that learned nothing looks perfect under the bug and near-useless under the correct objective, which is exactly the signal difference the shift creates.

<svg role="img" aria-label="Two bars of copy-model accuracy: 100 percent under same-position labeled learns nothing, and 25 percent under shifted labeled real task" viewBox="0 0 440 150">
<line x1="40" y1="120" x2="410" y2="120" stroke="var(--line)"/>
<rect x="80" y="30" width="80" height="90" fill="var(--s2)"/>
<text x="120" y="24" fill="var(--ink)" font-size="11" text-anchor="middle">100%</text>
<text x="120" y="138" fill="var(--ink)" font-size="10" text-anchor="middle">same-position</text>
<text x="120" y="150" fill="var(--muted)" font-size="9" text-anchor="middle">(learns nothing)</text>
<rect x="280" y="97" width="80" height="23" fill="var(--s1)"/>
<text x="320" y="90" fill="var(--ink)" font-size="11" text-anchor="middle">25%</text>
<text x="320" y="138" fill="var(--ink)" font-size="10" text-anchor="middle">shifted</text>
<text x="320" y="150" fill="var(--muted)" font-size="9" text-anchor="middle">(real task)</text>
</svg>
^ The copy baseline aces the buggy objective and collapses on the real one — the gap is the learning signal the shift creates.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the same-position objective has every target equal to its input and is aced perfectly by copying, that the shifted objective's targets are the next tokens, and that the copy baseline falls below perfect under the shift — proof the shift carries signal.

```python filename=modules/below-the-prompt/code/labelshift-inter-01/labelshift.py:85-98 COMPLETE
    same_target_equals_input = all(inp == tgt for inp, tgt in sp)
    print("  same-position: every target equals its own input token = %s" % same_target_equals_input)

    copy_aces_same = copy_accuracy(sp) == 1.0
    print("  same-position: a copy model scores a perfect 100%% = %s" % copy_aces_same)

    shifted_target_is_next = all(tgt == tokens[i + 1] for i, (inp, tgt) in enumerate(sh))
    print("  shifted: every target is the next token tokens[i+1] = %s" % shifted_target_is_next)

    copy_fails_shifted = copy_accuracy(sh) < 1.0
    print("  shifted: the copy model no longer scores perfectly = %s (%.0f%%)"
          % (copy_fails_shifted, 100 * copy_accuracy(sh)))

    shift_carries_signal = copy_accuracy(sh) < copy_accuracy(sp)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the shift ever stops separating the copy baseline from a perfect score:

```text filename=labelshift.py --check
SELF-TEST — the same-position objective is aced by copying; the one-token shift makes it a real prediction
----------------------------------------------------------------------------------------------------------------
  same-position: every target equals its own input token = True
  same-position: a copy model scores a perfect 100% = True
  shifted: every target is the next token tokens[i+1] = True
  shifted: the copy model no longer scores perfectly = True (25%)
  the shift lowers the copy baseline (so it carries signal) = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  same_target_equals_input=True  copy_aces_same=True  shifted_target_is_next=True  copy_fails_shifted=True  shift_carries_signal=True
```

**The self-test measures the objective against a copy baseline, not a model — so it proves the same-position task is trivially solvable and the shifted one is not, which is the real distinction the bug hides.**

## Definition of done

You can state the alignment rule: the target for the output at position i is tokens[i+1], implemented as inputs = tokens[:-1] and targets = tokens[1:].
You can explain why the same-position objective collapses to copying and drives the loss to zero while teaching nothing.
You can explain why the causal mask does not prevent this — the mask governs attention, the shift governs the target, and they are orthogonal.
You can describe the tell of the bug: a trivial copy baseline scores as well as the model, so the objective carries no signal.
You can predict that a model trained on the buggy objective can only echo its input at generation time.

## Boss fight

Shift by two instead of one — pair position i with tokens[i+2] — and reason about what breaks. The copy baseline still fails (good), but the task is now "predict the token after next", skipping the immediate next token entirely. A model trained this way learns a stride-2 language and generates by leaping over positions; the loss looks fine but the samples are garbage. The lesson sharpens: the objective must not just defeat the copy baseline, it must ask for the right token, and only the shift of exactly one does that. Wrong-by-one in either direction is a different broken task, not a smaller version of the right one.

Now consider the boundary. Under the shift, the last input token has no next token to predict, so the shifted alignment has one fewer pair than the sequence length — four pairs for five tokens, as the fixture shows. A harness that forgets this and tries to pair all five tokens either indexes past the end or silently reuses a token, quietly corrupting the last example of every sequence. The shift changes the count by one, and the code that builds batches has to account for it.

**Off-by-one in the target is not a milder bug — shifting by zero teaches copying and shifting by two teaches a stride-2 language; only the exact one-token shift asks for the next token, and it shortens the sequence by one pair, which the batching code must respect.**

## External resources

The nanoGPT training loop forms x and y as the same block of tokens offset by one, and its comments are the canonical short statement of this alignment.
Andrej Karpathy's "Let's build GPT" walks through constructing the shifted input/target batches from a token stream and shows the copy-baseline intuition directly.
The topic's own modules on the causal mask and on teacher forcing cover the two adjacent ideas this one is carefully distinguished from — what the model may attend to, and what it is fed at inference.
