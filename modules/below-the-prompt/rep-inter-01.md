---
id: rep-inter-01
title: Add a repetition penalty — or greedy decoding loops forever on the model's favorite token
topic: below-the-prompt
level: intermediate
status: ready
time: 20 min
summary: Greedy decoding picks the highest-logit token every step. If the context barely changes, the token that is best once is best every step, so the decoder emits it over and over — the classic "the the the" loop. A repetition penalty gives the decoder a memory: before each pick it divides the logit of every already-emitted token by a penalty factor raised to how many times it was used, so a token's appeal shrinks the more it is repeated. On a 3-token fixture, greedy emits X eight times (one unique token, a run of 8); a penalty of 2.0 produces "X Y X Y Z X Y Z" — max run 1, three unique tokens. Same model, same logits; the penalty broke the loop.
eli5: If you always say your favorite word because it feels best, you will just say it forever. A repetition penalty makes a word feel a little less good each time you have already said it, so after a couple of repeats a different word wins and you finally move on. Nothing about what you know changed — only how tempting it is to repeat yourself.
---

## Why this module

Greedy decoding has no memory of what it already said, so a model with a clear favorite token will say it forever.

The decoder's job is small: at each step the model produces a logit for every vocabulary token, and the decoder picks one. Greedy picks the highest. That is fine for one step. The trap is that the logits at the next step come from a context that has barely changed — you appended one token — so the same token is still highest, and greedy picks it again. Nothing in plain greedy remembers the emission, so a token that is best once is best every step. The output is a degenerate loop: "the the the the", or a sentence repeated verbatim without end.

**The model is not broken; greedy is memoryless, so a token that wins once wins every time.**

A repetition penalty fixes it without touching the model. Before each pick, lower the logit of every token you have already emitted — divide it by a penalty factor for each prior occurrence — so a token's appeal shrinks the more it has been used. The favorite still wins the first time; by the time it would repeat, its penalized logit has fallen below the runner-up, and a different token is chosen. The loop cannot form, because repeating makes a token progressively less attractive. This module builds both decoders on one fixture and measures the difference.

## Concepts

A **logit** is the model's raw score for a token before it is turned into a probability. Higher logit, more favored. On this fixture the model's static logits are X = 3.0, Y = 2.5, Z = 1.0 — X is the favorite, then Y, then Z.

**Greedy decoding** picks the argmax logit at every step. It is deterministic and cheap, and with unchanging logits it is a fixed point: it lands on the top token and stays there.

The **repetition penalty** is a single number, here 2.0. At each step, a token that has been emitted `k` times already has its logit divided by penalty raised to the power `k`. Emitted zero times, it is untouched (`penalty**0 = 1`). Emitted once, it is halved. Emitted twice, quartered. The penalty is applied to a copy of the logits used only for this pick — the base logits never change.

The mechanism is a race between the favorite's shrinking penalized logit and the runner-up's steady one. X starts at 3.0. After X is emitted once, its penalized logit is 3.0 / 2.0 = 1.5, which is now below Y's untouched 2.5 — so Y wins the next step. That single crossover is the whole trick.

**A repetition penalty is memory bolted onto a memoryless decoder: it reads back what was emitted and taxes it.**

The tax compounds: each additional emission divides by the penalty again, so a token's logit decays geometrically the more it is used.

<svg role="img" aria-label="X's logit falls from 3.0 to 1.5 to 0.75 to 0.375 as it is emitted more times under penalty 2.0" viewBox="0 0 300 120" width="300" height="120">
  <line x1="30" y1="15" x2="30" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <rect x="45" y="15" width="30" height="80" fill="var(--s1)"/>
  <rect x="110" y="55" width="30" height="40" fill="var(--s1)"/>
  <rect x="175" y="75" width="30" height="20" fill="var(--s1)"/>
  <rect x="240" y="85" width="30" height="10" fill="var(--s1)"/>
  <text x="48" y="12" fill="var(--muted)" font-size="8">3.0</text>
  <text x="113" y="52" fill="var(--muted)" font-size="8">1.5</text>
  <text x="176" y="72" fill="var(--muted)" font-size="8">0.75</text>
  <text x="238" y="82" fill="var(--muted)" font-size="8">0.375</text>
  <text x="52" y="108" fill="var(--muted)" font-size="8">0×</text>
  <text x="117" y="108" fill="var(--muted)" font-size="8">1×</text>
  <text x="182" y="108" fill="var(--muted)" font-size="8">2×</text>
  <text x="247" y="108" fill="var(--muted)" font-size="8">3×</text>
</svg>
^ X's penalized logit under penalty 2.0 as a function of how many times it has already been emitted — a geometric decay, not a one-time subtraction.

Two numbers summarize any output. The **longest run** is the most times a single token appears in a row — 8 means the whole output is one token repeated. The **unique count** is how many distinct tokens the output uses — 1 means total collapse, higher means the decoder is using more of its vocabulary.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/rep-inter-01/repetition.py

The fixture is three logits, a penalty, and a length. Everything else is computed.

```json filename=modules/below-the-prompt/code/rep-inter-01/logits.json:1-6 COMPLETE
{
  "_meta": "A model's next-token logits over a tiny vocabulary, held static across steps (the context barely changes). X is most favored, then Y, then Z. penalty divides an already-emitted token's logit by penalty**(times emitted); length is how many tokens to decode.",
  "penalty": 2.0,
  "length": 8,
  "logits": {"X": 3.0, "Y": 2.5, "Z": 1.0}
}
```

The decoder is one loop. For each step it builds `adjusted` — a copy of the base logits with each token divided by `penalty ** (times already emitted)` — picks the argmax, and records the emission. Passing `penalty = 1.0` makes the division a no-op, so the identical function is plain greedy.

```python filename=modules/below-the-prompt/code/rep-inter-01/repetition.py:40-48 COMPLETE
def generate(base, penalty, n):
    """Greedy decode n tokens, dividing an already-emitted token's logit by penalty**(times emitted)."""
    counts, out = {}, []
    for _ in range(n):
        adjusted = {t: base[t] / (penalty ** counts.get(t, 0)) for t in base}
        pick = max(adjusted, key=lambda t: adjusted[t])
        out.append(pick)
        counts[pick] = counts.get(pick, 0) + 1
    return out
```

Two small helpers summarize a sequence: the longest run of one token, and the count of distinct tokens.

```python filename=modules/below-the-prompt/code/rep-inter-01/repetition.py:51-61 COMPLETE
def max_run(seq):
    """Longest run of the same token in a row."""
    best = run = 1
    for i in range(1, len(seq)):
        run = run + 1 if seq[i] == seq[i - 1] else 1
        best = max(best, run)
    return best if seq else 0


def unique(seq):
    return len(set(seq))
```

Run `--generate` and the two decoders sit side by side on the same base logits.

```text filename=--generate
GENERATE — 8 tokens, greedy vs penalty 2.0 (base logits {'X': 3.0, 'Y': 2.5, 'Z': 1.0})
----------------------------------------------------------
  greedy:     X X X X X X X X
  penalized:  X Y X Y Z X Y Z
----------------------------------------------------------
  greedy sticks on the top token; the penalty moves off it.
```

Here is the crossover from the concepts, drawn as the penalized logit of X falling past Y's steady line the moment X is emitted once.

<svg role="img" aria-label="X's penalized logit drops from 3.0 to 1.5 after one emission, crossing below Y's steady 2.5" viewBox="0 0 300 150" width="300" height="150">
  <line x1="40" y1="20" x2="40" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <line x1="40" y1="120" x2="270" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <text x="20" y="35" fill="var(--muted)" font-size="9">3.0</text>
  <text x="20" y="72" fill="var(--muted)" font-size="9">2.5</text>
  <text x="20" y="105" fill="var(--muted)" font-size="9">1.5</text>
  <line x1="40" y1="65" x2="270" y2="65" stroke="var(--s2)" stroke-width="2"/>
  <text x="230" y="60" fill="var(--s2)" font-size="9">Y 2.5</text>
  <polyline points="40,30 150,30 150,100 270,100" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="55" y="25" fill="var(--s1)" font-size="9">X 3.0</text>
  <text x="185" y="95" fill="var(--s1)" font-size="9">X 1.5</text>
  <text x="120" y="138" fill="var(--muted)" font-size="9">X emitted once →</text>
</svg>
^ Before any emission X (3.0) beats Y (2.5); after X is emitted once its penalized logit halves to 1.5 and Y wins the next step.

## Build

Run `--stats` and the collapse is two numbers versus two numbers.

```text filename=--stats
STATS — longest repeated run and unique tokens
----------------------------------------------------------
  greedy:     max run 8   unique 1
  penalized:  max run 1   unique 3
----------------------------------------------------------
  the penalty caps the run and widens the vocabulary used.
```

Greedy: longest run 8, one unique token — the entire output is X. Penalized: longest run 1 (no token ever repeats immediately) and all three tokens appear. Same model, same base logits; only the penalty changed.

<svg role="img" aria-label="Greedy output is eight X's in one run; penalized output alternates X Y X Y Z X Y Z" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="30" fill="var(--muted)" font-size="9">greedy</text>
  <text x="60" y="30" fill="var(--s1)" font-size="12" font-family="var(--mono)">X X X X X X X X</text>
  <text x="60" y="48" fill="var(--muted)" font-size="8">run 8 · unique 1</text>
  <line x1="10" y1="65" x2="290" y2="65" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="90" fill="var(--muted)" font-size="9">penalized</text>
  <text x="60" y="90" fill="var(--s2)" font-size="12" font-family="var(--mono)">X Y X Y Z X Y Z</text>
  <text x="60" y="108" fill="var(--muted)" font-size="8">run 1 · unique 3</text>
</svg>
^ The same eight decoding steps: greedy stays on X, the penalty forces a new token whenever the last one's logit has been taxed below a rival's.

Notice the penalized output is not random — it is still fully deterministic greedy. X wins, is halved to 1.5, so Y (2.5) wins; Y is halved to 1.25, so X (back to 1.5 after its penalty, still above Z's 1.0) wins again; the pattern settles into using Z once both X and Y have been taxed enough. Every pick is the argmax of the penalized logits at that step.

## Definition of done

The self-test asserts the loop-versus-variety split with named boolean flags, and exits non-zero if any fails — so this is CI-checkable, not eyeballed.

```python filename=modules/below-the-prompt/code/rep-inter-01/repetition.py:93-104 COMPLETE
    greedy_loops = max_run(g) == n and unique(g) == 1
    print("  greedy emits one token for the whole output = %s (run %d, unique %d)" % (greedy_loops, max_run(g), unique(g)))

    penalized_no_immediate_repeat = max_run(p) == 1
    print("  the penalty never repeats a token immediately = %s (max run %d)" % (penalized_no_immediate_repeat, max_run(p)))

    penalized_more_variety = unique(p) > unique(g)
    print("  the penalty uses more of the vocabulary = %s (%d vs %d)" % (penalized_more_variety, unique(p), unique(g)))

    top = max(base, key=lambda t: base[t])
    penalty_lowers_emitted = base[top] / (pen ** 1) < base[top]
    print("  emitting a token lowers its next logit = %s (%s: %.2f -> %.2f)" % (penalty_lowers_emitted, top, base[top], base[top] / pen))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — greedy loops on one token; the penalty stops immediate repetition and adds variety
--------------------------------------------------------------------------------------------
  greedy emits one token for the whole output = True (run 8, unique 1)
  the penalty never repeats a token immediately = True (max run 1)
  the penalty uses more of the vocabulary = True (3 vs 1)
  emitting a token lowers its next logit = True (X: 3.00 -> 1.50)
  both start from the identical base logits (first pick same) = True
--------------------------------------------------------------------------------------------
SELF-TEST PASS  greedy_loops=True  penalized_no_immediate_repeat=True  penalized_more_variety=True  penalty_lowers_emitted=True  same_base=True
```

The last flag, `same_base`, is the honesty check: the first pick is identical under both decoders (X either way), proving the penalty did not change the model — only what happens once a token has been used.

**Done means the loop is provable, not merely absent: greedy collapses to run 8 / unique 1, and the penalty forces run 1 / unique 3 from the same logits.**

## Boss fight

The penalty of 2.0 was chosen so X's halved logit (1.5) drops below Y (2.5). Predict what happens if you weaken the penalty to 1.1 instead. It is tempting to say "a little less repetition" — the penalty is still there, so surely it still helps.

It does not help here at all. With penalty 1.1, X emitted once becomes 3.0 / 1.1 ≈ 2.73, still above Y's 2.5 — so X wins again. Emitted twice, 3.0 / 1.21 ≈ 2.48, now just below Y, but by then you already have a run. The penalty must be strong enough to push the favorite past the runner-up in one emission, or the loop survives with a slightly longer period. Change `penalty` in `logits.json` to 1.1 and rerun `--stats` to watch the run length climb back up.

The mirror-image failure is a penalty that is too strong. Set it very high and every emitted token is crushed so far that the decoder is forced onto never-used tokens even when repetition would have been correct — real text does repeat words ("the", "is"), and a brutal penalty produces stilted output that avoids any word twice. The `--stats` unique count would hit the vocabulary ceiling and stay there.

```python filename=modules/below-the-prompt/code/rep-inter-01/repetition.py:106-107 COMPLETE
    same_base = generate(base, 1.0, 1) == generate(base, pen, 1)
    print("  both start from the identical base logits (first pick same) = %s" % same_base)
```

**The penalty is a dial, not a switch: too weak and the loop survives, too strong and it forbids legitimate repetition — the fixture's 2.0 is tuned to cross X past Y in exactly one emission.**

## External resources

Holtzman et al., "The Curious Case of Neural Text Degeneration" (2019) — the paper that named the repetition-and-blandness failure of likelihood-maximizing decoding and motivated sampling alternatives.

Keskar et al., "CTRL" (2019), Section 4.1 — introduces the repetition penalty applied to logits, the exact divide-by-penalty mechanism this module builds.

The Hugging Face `transformers` docs on `generation` — `repetition_penalty`, `no_repeat_ngram_size`, and the related knobs, showing how the toy here maps onto a production decoder.
