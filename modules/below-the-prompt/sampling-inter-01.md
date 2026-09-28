---
id: sampling-inter-01
title: Temperature and top-p shape the softmax — and truncation must renormalize
topic: below-the-prompt
level: intermediate
status: ready
time: 8-10h
summary: Temperature divides the logits before the softmax, so the same distribution goes from 0.60 bits of entropy and 0.89 mass on the top token at T=0.5 to 2.23 bits and 0.41 at T=2.0 — cold sharpens toward greedy, hot flattens toward uniform. Top-p nucleus sampling then keeps the smallest set of tokens whose probability reaches p (three of six at p=0.9) and cuts the unreliable tail, but truncation removes mass, so the survivors sum to 0.9278 and must be renormalized back to 1 or you are sampling from an invalid distribution that under-weights every kept token. The bug is one missing division, and it is silent: the token probabilities still look reasonable, they just no longer sum to one.
eli5: A model does not pick the next word outright; it makes a weighted spinner. Temperature is how greedy the spinner is: cold means it almost always lands on the favourite, hot means even long shots come up. Top-p throws away the least likely slices before spinning so nonsense words cannot win. But once you cut slices off a spinner, the remaining slices no longer cover the whole circle — you have to resize them to fill it again, or the spin is rigged.
---

## Why this module

A model does not output words; it outputs logits — one raw score per vocabulary token — at every position. Everything between those scores and the token that actually gets emitted is sampling, and sampling has two knobs almost every deployment touches: temperature and top-p. Getting them right is the difference between output that is crisp but repetitive and output that is varied but occasionally unhinged, and getting the arithmetic under them right is the difference between sampling from the distribution you think you have and sampling from a subtly broken one. This module builds both knobs from the logits up and plants the one bug that makes top-p quietly wrong.

Temperature is a division. Divide every logit by T before the softmax: with T below 1 the gaps between logits grow, the softmax sharpens, and mass piles onto the top token — at the limit T→0 it is greedy argmax. With T above 1 the gaps shrink, the softmax flattens toward uniform, and unlikely tokens get real probability — more diversity, more errors. Top-p, or nucleus sampling, is a truncation: sort tokens by probability, keep the smallest prefix whose cumulative probability reaches p, and sample only from those, so the long unreliable tail is cut while the head stays as wide as the distribution needs. The trap is that truncation deletes probability mass, so the kept tokens no longer sum to 1, and you must renormalize — divide by the surviving mass — or every downstream sample is drawn from an invalid distribution. That missing division is the module's planted bug, and it is silent because the numbers still look like probabilities.

You need the softmax from anywhere it has appeared and no more. Everything runs offline against a logits fixture — six tokens, one decoding step — stdlib Python 3, `$0.00`. The instinct to unlearn is that temperature and top-p are opaque dials you turn by feel. They are two short, exact operations on a probability vector, and once you have built them you know precisely what each does to the distribution and where each can go wrong.

Here is the same distribution at three temperatures:

```
# modules/below-the-prompt/code/sampling-inter-01/ — COMPLETE, run from that directory
$ python3 sampling.py --temperature

TEMPERATURE — the same logits, three temperatures
------------------------------------------------------------------
  T=0.5  entropy=0.60 bits  top=the
        the=0.89  a=0.10  cat=0.01  dog=0.00  quantum=0.00  zebra=0.00
  T=1.0  entropy=1.53 bits  top=the
        the=0.64  a=0.21  cat=0.07  dog=0.04  quantum=0.02  zebra=0.01
  T=2.0  entropy=2.23 bits  top=the
        the=0.41  a=0.23  cat=0.14  dog=0.11  quantum=0.07  zebra=0.05
```

run: 2026-08-26 · deterministic; logits are a fixture · 6 tokens · `python3 sampling.py --temperature`

One set of logits, three shapes. At T=0.5 the top token holds 0.89 and the distribution is nearly a spike; at T=2.0 it holds 0.41 and the tail tokens `quantum` and `zebra` have gone from rounding-to-zero to a real 0.07 and 0.05. This module is what those knobs do and the arithmetic they demand.

## Concepts

Named here so you can find them again; each is built below.

- **Logits** — the model's raw per-token scores before any normalization.
- **Softmax** — exponentiate and normalize logits into a probability distribution.
- **Temperature** — a divisor on the logits: below 1 sharpens, above 1 flattens, →0 is greedy.
- **Entropy** — bits of uncertainty in the distribution; low when peaked, high when flat.
- **Top-p / nucleus** — keep the smallest set of tokens whose probability reaches p; cut the tail.
- **Renormalization** — after truncation, divide by the surviving mass so the kept probabilities sum to 1.

## Worked example

Source: the decoding stack every text model ships (temperature scaling and Holtzman et al.'s nucleus sampling), reduced to its arithmetic; the logits here stand in for a real model's output at one position so the distributions, entropy, and truncation are exact and checkable.

Script and fixture: `modules/below-the-prompt/code/sampling-inter-01/` — `sampling.py`, and `logits.json`, six tokens and their logits for one decoding step. Every command runs from there.

### Temperature: one division reshapes everything

The softmax exponentiates and normalizes; temperature divides the logits first.

```
# sampling.py:40-47 — COMPLETE (softmax with temperature; max-subtraction for stability)
def softmax(logits, temperature=1.0):
    """exp(logit / T) normalized. Lower T sharpens toward the top; higher T flattens."""
    scaled = [l / temperature for l in logits]
    m = max(scaled)  # subtract max for numerical stability
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]
```

Dividing by a small T magnifies the differences between logits before exponentiation, so the largest logit's exponential dominates even harder — the distribution sharpens. Dividing by a large T compresses the differences, so the exponentials come out closer together — the distribution flattens. The max-subtraction is a numerical-stability trick that does not change the result: it keeps the exponentials from overflowing by shifting the largest to `exp(0)=1`. Temperature is the whole of "how random is the model" in one divisor.

<svg viewBox="0 0 700 200" role="img" aria-label="Three side-by-side bar charts of the same six-token distribution at T=0.5, T=1.0, T=2.0. At T=0.5 one tall bar for 'the' and the rest near zero. At T=1.0 a tall 'the' bar and a descending tail. At T=2.0 the bars are much more even across all six tokens.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">same logits, three temperatures — mass spreads as T rises</text>
    <text x="70" y="34" fill="var(--ink)">T=0.5</text>
    <g fill="var(--s1)"><rect x="40" y="50" width="12" height="120"></rect><rect x="54" y="156" width="12" height="14"></rect><rect x="68" y="169" width="12" height="1"></rect><rect x="82" y="170" width="12" height="0.5"></rect><rect x="96" y="170" width="12" height="0.5"></rect><rect x="110" y="170" width="12" height="0.5"></rect></g>
    <text x="300" y="34" fill="var(--ink)">T=1.0</text>
    <g fill="var(--s1)"><rect x="270" y="84" width="12" height="86"></rect><rect x="284" y="142" width="12" height="28"></rect><rect x="298" y="161" width="12" height="9"></rect><rect x="312" y="165" width="12" height="5"></rect><rect x="326" y="167" width="12" height="3"></rect><rect x="340" y="169" width="12" height="1"></rect></g>
    <text x="530" y="34" fill="var(--ink)">T=2.0</text>
    <g fill="var(--s1)"><rect x="500" y="115" width="12" height="55"></rect><rect x="514" y="139" width="12" height="31"></rect><rect x="528" y="151" width="12" height="19"></rect><rect x="542" y="155" width="12" height="15"></rect><rect x="556" y="161" width="12" height="9"></rect><rect x="570" y="163" width="12" height="7"></rect></g>
    <line x1="30" y1="170" x2="600" y2="170" stroke="var(--grid)"></line>
    <text x="70" y="188" fill="var(--muted)">0.60 bits</text><text x="300" y="188" fill="var(--muted)">1.53 bits</text><text x="530" y="188" fill="var(--muted)">2.23 bits</text>
  </g>
</svg>
^ The leftmost token is `the` in every panel; only the shape changes. Cold, it is a spike (0.60 bits of entropy); hot, the mass spreads across all six tokens (2.23 bits). Entropy is the one-number summary of that spread.

### Entropy: the uncertainty in one number

Entropy measures how spread the distribution is — low when one token dominates, high when all are equal.

```
# sampling.py:49-51 — COMPLETE (Shannon entropy in bits)
def entropy(probs):
    """Shannon entropy in bits -- low when peaked, high when flat."""
    return -sum(p * math.log2(p) for p in probs if p > 0)
```

<svg viewBox="0 0 700 180" role="img" aria-label="A rising curve of entropy in bits against temperature. At T=0.5 entropy is 0.60 bits, at T=1.0 it is 1.53, at T=2.0 it is 2.23. A dashed horizontal ceiling line sits at log2(6)=2.58 bits, the uniform maximum, which the curve approaches but does not reach.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">entropy rises with temperature, toward the uniform ceiling</text>
    <line x1="60" y1="150" x2="640" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="42" x2="640" y2="42" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="500" y="38" fill="var(--acc-ink)" font-size="8">ceiling log2(6) = 2.58</text>
    <polyline points="140,128 360,66 580,50" fill="none" stroke="var(--s1)" stroke-width="2.5"></polyline>
    <circle cx="140" cy="128" r="3" fill="var(--s1)"></circle><circle cx="360" cy="66" r="3" fill="var(--s1)"></circle><circle cx="580" cy="50" r="3" fill="var(--s1)"></circle>
    <g fill="var(--muted)" text-anchor="middle"><text x="140" y="165">T=0.5</text><text x="360" y="165">T=1.0</text><text x="580" y="165">T=2.0</text></g>
    <g fill="var(--muted)"><text x="150" y="125">0.60</text><text x="370" y="63">1.53</text><text x="590" y="47">2.23</text></g>
  </g>
</svg>
^ Each temperature is one point on a curve that climbs toward the uniform ceiling of 2.58 bits. Sweeping temperature and logging entropy turns "how random should it be" into a single readable dial.

The three temperatures gave 0.60, 1.53, and 2.23 bits — monotonically rising with T, exactly as the picture shows. Entropy is a cleaner diagnostic than eyeballing bars: if you sweep temperature and log the entropy, you get a single curve that tells you how much diversity each setting buys, and its ceiling is `log2(vocab)` bits, reached only at uniform. Here the ceiling is `log2(6) ≈ 2.58`, and T=2.0 has climbed most of the way to it.

### Top-p: keep the head, cut the tail

Nucleus sampling sorts by probability and keeps the smallest prefix that reaches p.

```
# sampling.py:56-72 — COMPLETE (top-p truncation, then renormalize the survivors)
def nucleus(probs, p, renormalize=True):
    """Keep the smallest set of tokens whose mass reaches p; renormalize to a valid dist."""
    ranked = sorted(range(len(probs)), key=lambda i: (-probs[i], i))
    kept, cum = [], 0.0
    for i in ranked:
        kept.append(i)
        cum += probs[i]
        if cum >= p:
            break  # smallest prefix that reaches p, INCLUDING the token that crosses it
    mass = sum(probs[i] for i in kept)
    if renormalize:
        return [(i, probs[i] / mass) for i in kept]
    return [(i, probs[i]) for i in kept]
```

At p=0.9 on the T=1.0 distribution, it keeps `the` (0.64), `a` (0.85 cumulative), and `cat` (0.92, crossing 0.9), then stops — three tokens of six, the head, dropping `dog`, `quantum`, `zebra`.

```
# $ python3 sampling.py --nucleus
#   full distribution: the=0.64  a=0.21  cat=0.07  dog=0.04  quantum=0.02  zebra=0.01
#   kept (3 of 6 tokens), renormalized to sum 1:
#      the    0.693
#      a      0.231
#      cat    0.077
#   dropped tail: ['dog', 'quantum', 'zebra']
```

run: 2026-08-26 · deterministic · `python3 sampling.py --nucleus`

<svg viewBox="0 0 700 175" role="img" aria-label="Six probability bars in descending order: the 0.64, a 0.21, cat 0.07, dog 0.04, quantum 0.02, zebra 0.01. A vertical cut line falls after cat, where the cumulative probability reaches 0.92, crossing p=0.9. The three bars left of the cut are kept and highlighted; dog, quantum, zebra to the right are greyed as dropped.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">top-p=0.9: keep the smallest head whose cumulative mass reaches 0.9</text>
    <line x1="40" y1="140" x2="660" y2="140" stroke="var(--grid)"></line>
    <g fill="var(--s1)"><rect x="60" y="44" width="60" height="96"></rect><rect x="150" y="108" width="60" height="32"></rect><rect x="240" y="130" width="60" height="10"></rect></g>
    <g fill="var(--muted)"><rect x="330" y="134" width="60" height="6"></rect><rect x="420" y="137" width="60" height="3"></rect><rect x="510" y="138" width="60" height="2"></rect></g>
    <line x1="312" y1="30" x2="312" y2="150" stroke="var(--s2)" stroke-dasharray="4 3"></line>
    <text x="318" y="40" fill="var(--s2)" font-size="8">cut: cumulative 0.92 >= 0.9</text>
    <g fill="var(--ink)" text-anchor="middle" font-size="8"><text x="90" y="155">the .64</text><text x="180" y="155">a .21</text><text x="270" y="155">cat .07</text></g>
    <g fill="var(--muted)" text-anchor="middle" font-size="8"><text x="360" y="155">dog</text><text x="450" y="155">quantum</text><text x="540" y="155">zebra</text></g>
    <text x="180" y="176" fill="var(--s1)" font-size="8">kept (renormalize these to sum 1)</text><text x="450" y="176" fill="var(--muted)" font-size="8">dropped tail</text>
  </g>
</svg>
^ The cut falls after `cat`, where the cumulative mass first reaches p; the three bars left of it are the nucleus, the three right of it are discarded. The kept bars sum to 0.92, not 1 — which is exactly why they must be renormalized before sampling.

Unlike top-k, which always keeps a fixed number, top-p adapts: on a peaked distribution it might keep one token, on a flat one a dozen, always exactly enough to cover probability p. That is why it is the default in most deployments — it cuts the tail without capping the head.

### The bug: forgetting to renormalize

Look at the kept probabilities before renormalization: `the=0.64, a=0.21, cat=0.07`, summing to 0.92, not 1. That is the mass that survived the cut, and it is less than one because you deleted the tail. If you sample from those raw numbers you are drawing from an invalid distribution — every kept token is under-weighted by the same factor, and any sampler that relies on the probabilities summing to 1 (cumulative-draw, rejection) drifts.

```
# $ python3 sampling.py --check
#   softmax sums to 1 = True (1.000000)
#   entropy rises with temperature = True (0.60 < 1.53 < 2.23 bits)
#   lower T concentrates mass on the top token = True (0.89 > 0.64)
#   renormalized nucleus sums to 1 = True (1.000000)
#   BUG: un-renormalized nucleus sums to < 1 = True (0.9278)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 sampling.py --check`

The self-test pins both sides of the division — the correct nucleus sums to 1, the buggy one does not:

```
# sampling.py:126-133 — COMPLETE (the renormalized nucleus vs the un-renormalized bug)
    kept = nucleus(probs, 0.9, renormalize=True)
    renorm_valid = abs(sum(pr for _, pr in kept) - 1.0) < 1e-9

    buggy = nucleus(probs, 0.9, renormalize=False)
    bug_undercounts = sum(pr for _, pr in buggy) < 1.0 - 1e-9
```

The renormalization is one division — `probs[i] / mass` — turning `0.64, 0.21, 0.07` into `0.693, 0.231, 0.077`, which sum to 1. The `bug_seen` line makes the failure explicit: the un-renormalized nucleus sums to 0.9278, and a test that only checked "does the output look like probabilities" would pass it, because 0.64 and 0.21 are perfectly plausible probabilities. Only summing them catches it.

**Temperature is a divisor on the logits that trades entropy for reliability, and top-p keeps the smallest head that reaches p — but truncation deletes mass, so the survivors must be renormalized to sum to 1, or every sample is drawn from a distribution that is quietly, plausibly wrong.**

### The running tally

| setting | top token mass | entropy (bits) | kept-mass sums to |
|---|---|---|---|
| T=0.5 | 0.89 | 0.60 | 1.00 (full softmax) |
| T=2.0 | 0.41 | 2.23 | 1.00 (full softmax) |
| top-p 0.9, renormalized | 0.69 | — | 1.00 |
| top-p 0.9, bug | 0.64 | — | 0.93 |

The last two rows are the same truncation, one division apart. The renormalized version is a valid distribution centred on `the` at 0.69; the buggy version under-weights every token and sums to 0.93. Everything above the last row is correct; the last row is the trap, and it is invisible unless you check the sum. When you truncate a distribution, the very next thing you do is make it sum to one again.

### What we did not settle

This is two knobs of several. Top-k keeps a fixed count rather than a mass, and is often combined with top-p (apply k, then p). Repetition and presence penalties adjust logits for tokens already emitted, before temperature, to fight loops. Min-p and typical sampling are newer nucleus variants that adapt the cut differently. And we scored distributions rather than drawing samples — the actual draw needs a random source and a seed, and reproducible generation pins that seed, which is its own discipline. The arithmetic here — softmax, temperature, an adaptive cut, and the renormalization it forces — is the floor every one of those builds on.

## Build

The practice in one paragraph: turn logits into a distribution with a temperature-scaled softmax, using max-subtraction for stability; pick temperature by the entropy you want, remembering T→0 is greedy and high T approaches uniform; truncate the tail with top-p by keeping the smallest prefix that reaches p; and always renormalize the survivors to sum to 1 before sampling, then assert that sum in a test, because an un-renormalized nucleus is a silent bug that looks like valid probabilities. Score the distribution before you ever draw from it.

We opened on temperature. The number that proves the cut is done right is the kept mass:

```
# modules/below-the-prompt/code/sampling-inter-01/ — COMPLETE, run from that directory
$ python3 sampling.py --nucleus
  kept (3 of 6 tokens), renormalized to sum 1:
     the    0.693
```

Now build it on your own logits. Take a real distribution — export logits from a small model, or hand-make a vector — sweep temperature and plot entropy, then apply top-p and check the survivors sum to 1. Your number to beat is not the top token's probability; it is **the kept-mass sum after truncation, which must be exactly 1 once renormalized and strictly less than 1 before** — reproduce both, so you have seen the bug. Bring back the entropy-versus-temperature curve and the two kept-mass sums. Good luck.

## Definition of done

- [ ] A temperature-scaled softmax with max-subtraction for numerical stability
- [ ] Entropy of the distribution computed, and shown rising with temperature
- [ ] Confirmation that low temperature concentrates mass on the top token
- [ ] Top-p nucleus truncation keeping the smallest prefix that reaches p
- [ ] The survivors renormalized to sum to 1, and the sum asserted
- [ ] The un-renormalized version reproduced, summing to less than 1, so the bug is seen
- [ ] `python3 sampling.py --check` printing SELF-TEST PASS: softmax-ok, temp-orders, colder-sharper, renorm-valid, bug-seen
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Temperature is a single arithmetic operation on the logits. Which one, and what does T→0 versus large T do to the distribution and why?
2. What does entropy measure here, what is its maximum for this vocabulary, and why does it rise with temperature?
3. How does top-p decide how many tokens to keep, and how does that differ from top-k?
4. After truncating to the nucleus, why must you renormalize, and what exactly is wrong with the distribution if you do not?
5. Your own logits were swept and truncated. What was the entropy at your lowest and highest temperature, and what were the kept-mass sums before and after renormalization?

## External resources

- Holtzman et al., *The Curious Case of Neural Text Degeneration* (2019) — https://arxiv.org/abs/1904.09751 — my summary: the paper that introduced nucleus (top-p) sampling and showed why cutting the unreliable tail beats both greedy and pure temperature sampling; read it for why the adaptive cut this module implements is the default.
- Anthropic / OpenAI API docs on temperature and top_p — my summary: the operator-facing description of the two knobs and the common advice to tune one, not both; read it for how these parameters are exposed and the ranges practitioners actually use.
- This hub, *tokens-basic-01* — modules/below-the-prompt/tokens-basic-01.md — my summary: what the vocabulary these logits range over actually is, and why token boundaries are not word boundaries; read it for the layer below this one — the tokens whose logits temperature and top-p reshape.
