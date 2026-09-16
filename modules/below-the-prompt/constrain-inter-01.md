---
id: constrain-inter-01
title: Mask illegal next-tokens to −inf before the softmax — an unconstrained decoder emits the most probable token even when the grammar forbids it
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: A language model's head assigns a logit to every token in the vocabulary, softmax turns those into a distribution, and the decoder picks from it — and nothing in that distribution encodes the output format the caller needs. The model was trained to predict likely text, not to guarantee valid JSON or a well-formed field, so at any position the most probable token can be one the grammar forbids, and an unconstrained decoder emits it. On the fixture the output must match digit-colon-digit, but the model's raw argmax is illegal at every position — a letter where a digit is required, a digit where the colon goes, a colon where the last digit goes — so the unconstrained decode is "x2:", not a valid string. Constrained (grammar-guided) decoding fixes it at the same place the causal mask lives: at each position the grammar names the legal tokens, and the decoder sets every illegal token's logit to negative infinity before the softmax, so after the exponential they become exactly zero probability and the choice is renormalized over the legal tokens alone. The result, "1:0", is valid by construction — not checked after the fact and repaired, but made impossible to violate — and the token chosen is the most probable legal one, so the model's preference is honored within the grammar (at the colon position, where only the colon is legal, its probability is 1.000). The rule: enforce a required output format by masking illegal tokens in the logits before the softmax, so generation can only produce valid output.
eli5: Imagine a spelling game where the next letter has to keep the word valid, but your friend just shouts whatever letter feels most likely — sometimes a letter that can't possibly come next, so the word turns into nonsense. A better way is to cover up all the letters that aren't allowed right now, and let your friend pick only from the ones still showing. They still get to choose their favorite, but only among the legal options, so the word always stays valid. Constrained decoding does that to a language model: before it chooses the next token, it hides every token the format doesn't allow, so the model can only pick a legal one — and it still picks the legal one it likes best.
---

## Why this module

When a model has to produce structured output — JSON, a date, an enum value, a line of code — "usually valid" is not good enough, because the one time it emits a stray token, the parser downstream rejects the whole thing. The tempting fixes come after generation: validate the output and retry, or repair the malformed text. Both spend a model round-trip or a fragile patcher on a problem that did not have to happen.

The reason it happens is that the model's probability distribution has no idea what format you need. It ranks tokens by how likely they are to continue the text it saw in training, and the format is a constraint you are imposing from outside. So the highest-probability token at a position can be one the grammar forbids, and a decoder that samples the full vocabulary has nothing stopping it from picking that token.

This module builds a three-position output that must match digit-colon-digit and hands the decoder logits whose raw argmax is illegal at every position. The unconstrained decode comes out "x2:" — invalid. Constrained decoding masks the illegal tokens to negative infinity before the softmax and comes out "1:0" — valid, and still the model's most-preferred legal token at each step. Then it shows why masking, not repair, is the right place to intervene.

**A model's logits rank tokens by likelihood, not by legality, so a valid-output requirement has to be enforced by the decoder — and the cheapest, surest place to enforce it is on the logits, before a token is ever chosen.**

## Concepts

Decoding a token is two steps: turn the logits into a distribution with softmax, then pick from it. The softmax is where a mask can act. Softmax exponentiates each logit and normalizes, so a logit of negative infinity exponentiates to exactly zero — the token gets zero probability and cannot be chosen, while the remaining tokens' probabilities renormalize to sum to one among themselves. This is the identical mechanism the causal mask uses to forbid attending to future positions; here it forbids emitting illegal tokens.

The grammar supplies which tokens are legal. At each position a grammar or state machine — a regex, a JSON schema, a formal grammar — knows the set of tokens that can legally come next given what has been emitted so far. Constrained decoding asks the grammar for that legal set, masks every token outside it to negative infinity, and only then runs the softmax. The decoder's choice is now confined to the legal tokens by construction; there is no path by which an illegal token can be produced.

The important property is that masking filters the model without overriding it. Among the legal tokens, the logits are untouched, so their relative order and the softmax over them are exactly what the model intended — the chosen token is the most probable legal token. If the model most wanted an illegal token and a particular legal token second, constrained decoding returns that legal token, which is precisely the desired behavior: honor the model's preference, but only within what the format allows.

The figure shows one position's logits before and after masking: the illegal tokens are pushed to negative infinity, and the softmax redistributes all the probability over the legal ones.

<svg role="img" aria-label="At one position, a row of seven logit bars. The illegal tokens (four digits are legal, colon and letter x illegal here) are struck through and labeled minus infinity. After the softmax, the probability bars show zero for the illegal tokens and a renormalized distribution over the four legal digits" viewBox="0 0 640 250">
<text x="60" y="30" fill="var(--ink)" font-size="11">logits at pos 0 (legal: digits; illegal: ':' , 'x')</text>
<rect x="60" y="60" width="30" height="40" fill="var(--s1)" opacity="0.7"/>
<rect x="100" y="45" width="30" height="55" fill="var(--s1)" opacity="0.7"/>
<rect x="140" y="72" width="30" height="28" fill="var(--s1)" opacity="0.7"/>
<rect x="180" y="78" width="30" height="22" fill="var(--s1)" opacity="0.7"/>
<rect x="220" y="82" width="30" height="18" fill="var(--s1)" opacity="0.7"/>
<rect x="260" y="90" width="30" height="10" fill="var(--s2)" opacity="0.5"/>
<line x1="258" y1="88" x2="292" y2="100" stroke="var(--s2)" stroke-width="1.5"/>
<rect x="300" y="40" width="30" height="60" fill="var(--s2)" opacity="0.5"/>
<line x1="298" y1="42" x2="332" y2="100" stroke="var(--s2)" stroke-width="1.5"/>
<text x="275" y="118" fill="var(--s2)" font-size="9" text-anchor="middle">': '→ −inf</text>
<text x="315" y="118" fill="var(--s2)" font-size="9" text-anchor="middle">'x'→ −inf</text>
<text x="130" y="118" fill="var(--muted)" font-size="9" text-anchor="middle">legal digits</text>
<text x="480" y="30" fill="var(--ink)" font-size="11">masked softmax → probabilities</text>
<line x1="380" y1="200" x2="600" y2="200" stroke="var(--line)" stroke-width="1"/>
<rect x="390" y="150" width="26" height="50" fill="var(--ink)"/>
<rect x="420" y="135" width="26" height="65" fill="var(--ink)"/>
<rect x="450" y="170" width="26" height="30" fill="var(--ink)"/>
<rect x="480" y="178" width="26" height="22" fill="var(--ink)"/>
<rect x="510" y="184" width="26" height="16" fill="var(--ink)"/>
<rect x="540" y="199" width="26" height="1" fill="var(--s2)"/>
<rect x="570" y="199" width="26" height="1" fill="var(--s2)"/>
<text x="553" y="214" fill="var(--s2)" font-size="9" text-anchor="middle">0</text>
<text x="583" y="214" fill="var(--s2)" font-size="9" text-anchor="middle">0</text>
</svg>
^ Masking the illegal tokens to negative infinity makes their softmax probability exactly zero, and the distribution renormalizes over the legal tokens the model still ranks by its own logits.

**Setting an illegal logit to negative infinity is not a soft penalty but an exact zero after the softmax, so constrained decoding cannot emit an illegal token — the guarantee is structural, not statistical.**

## Worked example

The fixture is a three-position format — digit, colon, digit — with the model's raw logits at each position.

```json filename=modules/below-the-prompt/code/constrain-inter-01/constrain.json:3-9 COMPLETE
  "vocab": ["0", "1", "2", "3", "4", ":", "x"],
  "legal_per_pos": [["0", "1", "2", "3", "4"], [":"], ["0", "1", "2", "3", "4"]],
  "logits_per_pos": [
    [1.0, 2.0, 0.5, 0.3, 0.2, 0.1, 3.0],
    [0.2, 0.3, 4.0, 0.1, 0.1, 2.0, 0.5],
    [0.5, 0.4, 0.3, 0.2, 0.1, 3.5, 0.6]
  ]
```

The masked softmax sets illegal tokens to negative infinity and renormalizes over the rest.

```python filename=modules/below-the-prompt/code/constrain-inter-01/constrain.py:31-37 COMPLETE
def masked_softmax(logits, allowed_idx):
    """Softmax after setting illegal logits to -inf: legal tokens get a renormalized distribution, illegal ones 0."""
    masked = [(lg if i in allowed_idx else float("-inf")) for i, lg in enumerate(logits)]
    hi = max(masked)
    exps = [math.exp(lg - hi) if lg != float("-inf") else 0.0 for lg in masked]
    total = sum(exps)
    return [e / total for e in exps]
```

The pick at a position is the argmax over whichever token indices are allowed.

```python filename=modules/below-the-prompt/code/constrain-inter-01/constrain.py:40-42 COMPLETE
def best_token(logits, allowed_idx):
    """The argmax over the allowed tokens -- the most probable legal next token at this position."""
    return max(allowed_idx, key=lambda i: logits[i])
```

Decoding runs that pick at every position — over the whole vocabulary when unconstrained, over the legal set when constrained.

```python filename=modules/below-the-prompt/code/constrain-inter-01/constrain.py:45-55 COMPLETE
def decode(data, constrained):
    """Decode all positions: constrained restricts each choice to the position's legal tokens; naive uses all."""
    vocab = data["vocab"]
    out = []
    for pos, logits in enumerate(data["logits_per_pos"]):
        if constrained:
            allowed = {vocab.index(t) for t in data["legal_per_pos"][pos]}
        else:
            allowed = set(range(len(vocab)))
        out.append(best_token(logits, allowed))
    return out
```

Unconstrained, the argmax is illegal at every position, and the output does not match the format.

```text filename=constrain.py --naive
NAIVE — argmax over the whole vocabulary at each position
----------------------------------------------------------------
  pos 0: picked 'x'  legal here? False  (legal set ['0', '1', '2', '3', '4'])
  pos 1: picked '2'  legal here? False  (legal set [':'])
  pos 2: picked ':'  legal here? False  (legal set ['0', '1', '2', '3', '4'])
  output = 'x2:'   valid digit:digit? False
----------------------------------------------------------------
  nothing stopped an illegal token, so the output does not match the required format
```

Constrained, each position picks the best legal token, and the output is valid.

```text filename=constrain.py --constrained
CONSTRAINED — mask illegal tokens to -inf before the softmax
----------------------------------------------------------------
  pos 0: picked '1'  p(legal)=0.516  (illegal tokens have p=0)
  pos 1: picked ':'  p(legal)=1.000  (illegal tokens have p=0)
  pos 2: picked '0'  p(legal)=0.242  (illegal tokens have p=0)
  output = '1:0'   valid digit:digit? True
----------------------------------------------------------------
  the choice is the most probable LEGAL token, so the output is valid by construction
```

At position 1 only the colon is legal, so its probability is 1.000 — the grammar forced it, and the model's raw preference for the digit "2" there is simply gone from the distribution. At positions 0 and 2 the model still chose among the digits it ranked highest. The figure shows the two decodes side by side.

<svg role="img" aria-label="Two rows. The naive row shows positions picking x, 2, colon, each marked illegal, forming the invalid string x2 colon. The constrained row shows positions picking 1, colon, 0, each marked legal, forming the valid string 1 colon 0" viewBox="0 0 640 200">
<text x="60" y="40" fill="var(--ink)" font-size="12">naive</text>
<rect x="120" y="24" width="44" height="30" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="4"/>
<text x="142" y="44" fill="var(--ink)" font-size="12" text-anchor="middle">x</text>
<rect x="174" y="24" width="44" height="30" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="4"/>
<text x="196" y="44" fill="var(--ink)" font-size="12" text-anchor="middle">2</text>
<rect x="228" y="24" width="44" height="30" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="4"/>
<text x="250" y="44" fill="var(--ink)" font-size="12" text-anchor="middle">:</text>
<text x="330" y="44" fill="var(--s2)" font-size="12">"x2:"  invalid (illegal every position)</text>
<text x="60" y="120" fill="var(--ink)" font-size="12">constrained</text>
<rect x="120" y="104" width="44" height="30" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="4"/>
<text x="142" y="124" fill="var(--ink)" font-size="12" text-anchor="middle">1</text>
<rect x="174" y="104" width="44" height="30" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="4"/>
<text x="196" y="124" fill="var(--ink)" font-size="12" text-anchor="middle">:</text>
<rect x="228" y="104" width="44" height="30" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="4"/>
<text x="250" y="124" fill="var(--ink)" font-size="12" text-anchor="middle">0</text>
<text x="330" y="124" fill="var(--s1)" font-size="12">"1:0"  valid (best legal each position)</text>
</svg>
^ The same model, same logits: unconstrained it emits an illegal token at every position; constrained it emits the best legal token at every position.

**Constrained decoding did not make the model smarter — it removed the illegal tokens from the choice, so the same underlying preferences now land only on valid output.**

## Build

The self-test pins both sides: the unconstrained decode is invalid (illegal at every position), the constrained decode is valid, and — the property that keeps masking honest — the illegal tokens get exactly zero probability.

```python filename=modules/below-the-prompt/code/constrain-inter-01/constrain.py:99-106 COMPLETE
    naive_invalid = not _valid(data, naive)
    print("  the unconstrained decode is invalid = %s (%r)" % (naive_invalid, _text(data, naive)))

    naive_illegal_every_pos = all(data["vocab"][i] not in data["legal_per_pos"][pos] for pos, i in enumerate(naive))
    print("  the unconstrained argmax is illegal at every position = %s" % naive_illegal_every_pos)

    constrained_valid = _valid(data, constrained)
    print("  the constrained decode is valid = %s (%r)" % (constrained_valid, _text(data, constrained)))
```

Running the check confirms all five flags.

```text filename=constrain.py --check
SELF-TEST — the unconstrained decode is invalid while the constrained decode is valid and picks the best legal token at each position
----------------------------------------------------------------------------------------------------------------
  the unconstrained decode is invalid = True ('x2:')
  the unconstrained argmax is illegal at every position = True
  the constrained decode is valid = True ('1:0')
  each constrained token is the most probable legal one = True
  masking gives the illegal tokens exactly zero probability = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_invalid=True  naive_illegal_every_pos=True  constrained_valid=True  constrained_is_best_legal=True  illegal_prob_is_zero=True
```

**"Illegal tokens have exactly zero probability" is the whole guarantee: because the mask acts before the softmax, no amount of sampling temperature or bad luck can produce an illegal token, which is what "valid by construction" means.**

## Definition of done

You are done when a required output format is enforced by masking illegal tokens in the logits at each decoding step, so the generated output is always valid without a post-hoc validate-and-retry loop.

The machinery has two parts that work together. A grammar or state machine tracks what has been generated and, at each step, produces the set of legal next tokens — this is where a JSON schema, a regex, or a context-free grammar is compiled into per-step token masks. The decoder applies that mask to the logits (set illegal tokens to negative infinity), runs the softmax, and samples or takes the argmax, then advances the grammar state with the chosen token so the next step's legal set is correct. Two cautions keep it honest: the mask must be computed over the model's actual token vocabulary, since a grammar written over characters has to be translated into which tokens are legal (a token may span several characters), and the mask should never empty the legal set — a grammar that can reach a state with no legal token is a grammar bug that will crash or force an illegal emission, so the grammar must always allow at least one continuation (including a way to end).

<svg role="img" aria-label="A loop: the grammar produces a legal token set, the decoder masks illegal logits to minus infinity, softmax and pick a token, then the chosen token advances the grammar state, feeding back to produce the next legal set" viewBox="0 0 640 190">
<rect x="30" y="75" width="120" height="44" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="90" y="93" fill="var(--ink)" font-size="10" text-anchor="middle">grammar state →</text>
<text x="90" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">legal token set</text>
<line x1="150" y1="97" x2="200" y2="97" stroke="var(--line)" stroke-width="1"/>
<polygon points="200,97 192,92 192,102" fill="var(--line)"/>
<rect x="200" y="75" width="130" height="44" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="265" y="93" fill="var(--ink)" font-size="10" text-anchor="middle">mask illegal → −inf</text>
<text x="265" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">softmax, pick token</text>
<line x1="330" y1="97" x2="380" y2="97" stroke="var(--line)" stroke-width="1"/>
<polygon points="380,97 372,92 372,102" fill="var(--line)"/>
<rect x="380" y="75" width="120" height="44" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="440" y="93" fill="var(--ink)" font-size="10" text-anchor="middle">emit token,</text>
<text x="440" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">advance grammar</text>
<path d="M 440 119 L 440 155 L 90 155 L 90 119" fill="none" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 3"/>
<polygon points="90,119 85,127 95,127" fill="var(--line)"/>
<text x="265" y="150" fill="var(--muted)" font-size="9" text-anchor="middle">next step's legal set depends on what was emitted</text>
</svg>
^ The grammar and the mask form a loop: each emitted token advances the grammar, which narrows the next step's legal set, so the whole sequence stays valid.

**Validate-and-retry treats invalid output as an error to catch after the fact; constrained decoding treats it as a state the decoder is never allowed to enter — the same reason you mask the future rather than checking for cheating after training.**

## Boss fight

Your turn: make a position's legal set a singleton and watch the model's opinion vanish entirely. At position 1 only the colon is legal, so its masked probability is 1.000 no matter what the model's logits said — the model wanted the digit "2" most there, and constrained decoding overrides it completely. Now imagine a JSON schema where after a key the next token must be a colon: constrained decoding will emit that colon with certainty, which is exactly right, but it means the model's logits at forced positions carry no information and you are spending a forward pass to produce a token the grammar already knew. Efficient implementations skip the model entirely at forced positions and only run it where the legal set has more than one option — a real speedup, and a reminder that constraint and generation are separate concerns.

Then break the grammar on purpose to see the failure mode you must prevent. Change position 2's legal set to a token that has an extremely negative logit, or to the empty list. With an empty legal set the mask sends every logit to negative infinity, the softmax denominator is zero, and the decode is undefined — a crash or a NaN. This is the one way constrained decoding fails, and it is always a grammar bug: a well-formed grammar guarantees at least one legal continuation at every reachable state, including a legal way to terminate. So the discipline is not only "mask the illegal tokens" but "ensure the grammar can never paint itself into a corner with nothing legal left," because a mask over an empty set is worse than no mask at all.

**A singleton legal set shows constraint fully overriding the model, and an empty one shows the grammar's obligation: constrained decoding is only as sound as the grammar's guarantee that some legal token always remains.**

## External resources

The guidance/outlines/llguidance family of libraries implement grammar-constrained decoding by compiling a regex or context-free grammar into per-step token masks — the production form of this module's `legal_per_pos` plus masking.

OpenAI's structured-outputs and function-calling documentation, and the JSON-mode features of other providers, describe constrained decoding against a JSON schema as a first-class feature, and are the practical place most people meet it.

Willard and Louf's "Efficient Guided Generation for Large Language Models" (the outlines paper) gives the algorithm for turning a finite-state or context-free grammar into token-level masks efficiently, including the token-versus-character translation this module flags.
