---
id: specdecode-inter-01
title: Accept the draft token with probability min(1, p/q) and resample the rest — or you sample the small model, not the big one
topic: below-the-prompt
level: intermediate
status: ready
time: 18 min
summary: Speculative decoding runs a small fast draft model to propose the next token and a big slow target model to verify it, so the target can confirm several proposed tokens in one forward pass. The tempting shortcut — propose a draft token and keep it if it looks fine — samples the draft's distribution q, not the target's distribution p, and the whole point of the big model is that q is not p. The correct rule keeps the speedup without the bias: accept the draft token with probability min(1, p/q), and on rejection resample from the residual, the normalized positive part of p − q. That rule emits exactly p for any draft q, so the draft changes only the speed. On a fixture over five tokens, the acceptance rate is sum min(p, q) = 0.80 = 1 − TV(p, q); the speculative output equals the target exactly (total-variation distance 0) while "keep the draft" is 0.20 away; and with a draft block of 4 the target emits 3.36 tokens per forward pass instead of 1.
eli5: A slow expert and a fast intern both guess the next word. The intern guesses first; the expert checks. If you just trust the intern whenever the guess looks okay, you end up with the intern's writing, not the expert's — which defeats hiring the expert. The trick is a checking rule that sometimes rejects the intern and lets the expert pick instead, arranged so the words you keep are exactly the ones the expert would have written alone. You still go faster whenever the intern guesses well, but the final writing is the expert's, every time.
---

## Why this module

Speculative decoding is sold as a free speedup, and it is — but only under one exact acceptance rule; keep the draft's tokens on a looser test and you have quietly swapped the model you sample from.

The idea is simple: a small draft model proposes tokens cheaply, and the big target model verifies a whole block of them in a single forward pass instead of generating them one at a time. The trap is the verification step. It feels natural to accept a proposed token whenever it is "good enough" — the draft's top choice matches the target's, say, or the target assigns it decent probability. But any rule of the form "keep the draft's token when it passes" is sampling the draft's distribution q on the tokens it keeps, and the entire reason you pay for the big model is that q is not p. Keep draft tokens and your output drifts toward the small model by exactly the gap between them; the big model becomes a rubber stamp instead of the thing you sample.

**Speculative decoding only preserves the target model's output if you accept the draft token with probability min(1, p/q) and, on rejection, resample from the residual — any looser "keep it if it looks fine" rule samples the draft distribution, not the target's.**

The correct rule has an exact guarantee that no approximate rule has. Draft a token x from q; accept it with probability min(1, p(x)/q(x)); if rejected, do not fall back to a draft token — resample from the residual distribution, the normalized positive part of p − q. The token you emit is then distributed exactly as p, for any draft q whatsoever. The draft changes the speed and nothing else: the fraction of proposals accepted is sum min(p, q) = 1 − TV(p, q), so a draft that agrees with the target confirms a whole block per pass, and a useless draft degrades gracefully to ordinary one-token decoding. This module computes the exact output distribution of both rules and the speedup, with no sampling.

## Concepts

**The target p and draft q** are two probability distributions over the vocabulary — the big model's next-token distribution and the small model's. We want to sample from p; the draft only proposes.

**Acceptance** is the fraction of draft proposals the target keeps. It equals the overlap of the two distributions, sum min(p, q), which is exactly 1 − TV(p, q): the closer the draft is to the target, the more it gets accepted.

```python filename=modules/below-the-prompt/code/specdecode-inter-01/specdecode.py:43-45 COMPLETE
def acceptance(p, q):
    """Fraction of draft proposals the target accepts = sum min(p, q) = 1 - TV(p, q)."""
    return sum(min(pi, qi) for pi, qi in zip(p, q))
```

**The residual** is where a rejected step resamples from: the normalized positive part of p − q. It carries exactly the probability mass the target wanted but the draft under-proposed, so accepting-or-residual-resampling adds up to p.

**The speculative rule** ties these together: emit x with probability q(x)·min(1, p(x)/q(x)) — the accept branch — plus the reject probability times the residual. That sum equals p(x) for every x.

```python filename=modules/below-the-prompt/code/specdecode-inter-01/specdecode.py:55-63 COMPLETE
def speculative_output(p, q):
    """The exact output distribution of accept-with-prob-min(1,p/q)-else-resample-residual. Equals p."""
    reject = 1.0 - acceptance(p, q)
    res = residual(p, q)
    out = []
    for pi, qi, ri in zip(p, q, res):
        accept_prob = min(1.0, pi / qi) if qi > 0 else 0.0
        out.append(qi * accept_prob + reject * ri)
    return out
```

<svg role="img" aria-label="A draft token is accepted with probability min(1, p/q); on rejection the step resamples from the residual, and either path emits a token distributed as the target p" viewBox="0 0 300 108" width="300" height="108">
  <rect x="6" y="44" width="58" height="20" fill="none" stroke="var(--line)"/><text x="12" y="57" fill="var(--ink)" font-size="8">draft x ~ q</text>
  <line x1="64" y1="54" x2="96" y2="54" stroke="var(--line)"/>
  <text x="70" y="50" fill="var(--muted)" font-size="7">min(1,p/q)</text>
  <rect x="96" y="20" width="70" height="18" fill="var(--s1)"/><text x="100" y="33" fill="var(--panel)" font-size="8">accept x</text>
  <rect x="96" y="70" width="70" height="18" fill="var(--s2)"/><text x="100" y="83" fill="var(--panel)" font-size="8">reject</text>
  <text x="120" y="16" fill="var(--muted)" font-size="7">prob accept</text>
  <line x1="166" y1="79" x2="198" y2="79" stroke="var(--line)"/>
  <rect x="198" y="70" width="94" height="18" fill="none" stroke="var(--line)"/><text x="202" y="83" fill="var(--ink)" font-size="8">resample residual</text>
  <line x1="166" y1="29" x2="292" y2="29" stroke="var(--s1)"/>
  <text x="200" y="26" fill="var(--muted)" font-size="7">emit x</text>
  <text x="6" y="102" fill="var(--muted)" font-size="8">both paths together emit a token distributed exactly as the target p</text>
</svg>
^ The draft token is accepted with probability min(1, p/q); a rejection resamples from the residual (positive part of p − q); the two branches sum to exactly the target distribution.

**Acceptance decides only how fast you go; the accept-min(1,p/q)-else-resample-residual rule decides that what you emit is exactly the target p — swap that rule for any "keep the draft if it passes" test and you are sampling the draft.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/specdecode-inter-01/specdecode.py

The fixture is a target and a draft distribution over five tokens, plus a draft block length.

```json filename=modules/below-the-prompt/code/specdecode-inter-01/specdecode.json:1-7 COMPLETE
{
  "_meta": "One decoding step for speculative sampling. target is the probability distribution of the big model we want to sample from (p). draft is the distribution of the small fast model that proposes tokens (q). Speculative sampling lets the draft propose a token and the target verify it, accepting the proposal with probability min(1, p/q) and otherwise resampling from the normalized positive residual max(0, p-q). The point of the rule is that the resulting output distribution is EXACTLY p -- the draft speeds things up without changing what the big model would have produced. draft_len is how many tokens the draft proposes per target call, used to estimate the speedup. The naive alternative -- just keep the draft's token -- outputs q instead of p, which is biased. All quantities here are exact, not sampled.",
  "vocab": ["the", "a", "cat", "dog", "runs"],
  "target": [0.40, 0.20, 0.20, 0.10, 0.10],
  "draft":  [0.50, 0.30, 0.10, 0.05, 0.05],
  "draft_len": 4
}
```

Run `--verify` to reconstruct the output distribution of both rules exactly.

```text filename=--verify
VERIFY — the speculative rule emits the TARGET's distribution, not the draft's
----------------------------------------------------------------------
  token     target p   draft q    spec-out    keep-draft
  the       0.400      0.500      0.400       0.500
  a         0.200      0.300      0.200       0.300
  cat       0.200      0.100      0.200       0.100
  dog       0.100      0.050      0.100       0.050
  runs      0.100      0.050      0.100       0.050
----------------------------------------------------------------------
  TV(spec-out, target)   = 0.000   (accept-or-resample is exact)
  TV(keep-draft, target) = 0.200   (keeping draft tokens samples q, not p)
```

Read the `spec-out` column against `target p`: they are identical to the digit, so the total-variation distance is 0. The draft over-proposes `the` (0.50 vs 0.40) and `a` (0.30 vs 0.20) and under-proposes `cat` (0.10 vs 0.20) — but the accept probability min(1, p/q) throttles the over-proposed tokens back down, and the residual makes up the under-proposed `cat`, `dog`, and `runs` on the rejection branch. The `keep-draft` column is just q, sitting 0.20 away from the target in total variation. That 0.20 is not a rounding error; it is a systematic bias toward the small model, present on every token the naive rule keeps. The correct rule leans on the draft for speed and never lets it touch the distribution.

<svg role="img" aria-label="For each token the speculative output bar matches the target bar exactly, while the keep-draft bar matches the draft and diverges from the target" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="10" fill="var(--muted)" font-size="8">per token: target (line) vs spec-out (dark) vs keep-draft (light)</text>
  <line x1="30" y1="92" x2="292" y2="92" stroke="var(--grid)"/>
  <text x="4" y="52" fill="var(--muted)" font-size="7">p</text>
  <rect x="34" y="32" width="14" height="60" fill="var(--s1)"/><rect x="50" y="17" width="14" height="75" fill="var(--s2)"/><line x1="32" y1="32" x2="66" y2="32" stroke="var(--ink)"/><text x="36" y="102" fill="var(--muted)" font-size="7">the</text>
  <rect x="86" y="62" width="14" height="30" fill="var(--s1)"/><rect x="102" y="47" width="14" height="45" fill="var(--s2)"/><line x1="84" y1="62" x2="118" y2="62" stroke="var(--ink)"/><text x="90" y="102" fill="var(--muted)" font-size="7">a</text>
  <rect x="138" y="62" width="14" height="30" fill="var(--s1)"/><rect x="154" y="77" width="14" height="15" fill="var(--s2)"/><line x1="136" y1="62" x2="170" y2="62" stroke="var(--ink)"/><text x="140" y="102" fill="var(--muted)" font-size="7">cat</text>
  <rect x="190" y="77" width="14" height="15" fill="var(--s1)"/><rect x="206" y="84" width="14" height="8" fill="var(--s2)"/><line x1="188" y1="77" x2="222" y2="77" stroke="var(--ink)"/><text x="192" y="102" fill="var(--muted)" font-size="7">dog</text>
  <rect x="242" y="77" width="14" height="15" fill="var(--s1)"/><rect x="258" y="84" width="14" height="8" fill="var(--s2)"/><line x1="240" y1="77" x2="274" y2="77" stroke="var(--ink)"/><text x="244" y="102" fill="var(--muted)" font-size="7">runs</text>
  <text x="6" y="113" fill="var(--muted)" font-size="8">dark bars sit on the target line; light bars (keep-draft) miss it every token</text>
</svg>
^ The spec-out bar meets the target line on every token, while the keep-draft bar over- or under-shoots it — the speculative rule reproduces p, the naive rule reproduces q.

## Build

The speedup is the other half. Run `--speed`: acceptance is the overlap of the two distributions, and it multiplies how many tokens the target confirms per forward pass.

```text filename=--speed
SPEED — acceptance is 1 - TV, and it multiplies tokens per target forward pass
------------------------------------------------------------------
  acceptance  alpha = sum min(p,q) = 0.800   ( = 1 - TV = 1 - 0.200 )
  draft block length k               = 4
  expected tokens per target pass    = 3.362   (vs 1.000 for plain decoding)
------------------------------------------------------------------
  a good draft (alpha near 1) confirms a whole block per pass; a bad one falls back to 1.
```

Acceptance is 0.80 — the target keeps four of every five proposals — and that number is exactly the overlap sum min(p, q), which is 1 − TV(p, q). Feed it through the block: with a draft proposing k = 4 tokens, the expected number the target emits in one forward pass is (1 − αᵏ⁺¹)/(1 − α) = (1 − 0.8⁵)/0.2 = 3.362. Plain decoding emits exactly one token per target pass; speculative decoding emits 3.362, so the target runs about a third as often for the same output. The whole speedup lives in α, which is a property of how good the draft is, and none of it touched the output distribution — the earlier `--verify` already proved that stays exactly p. Faster when the draft is good, never wrong when it is bad: the acceptance falls, the expected tokens fall toward 1, and you have simply paid for ordinary decoding.

<svg role="img" aria-label="Acceptance is the overlap area between the target and draft distributions, the sum of the per-token minimum, which equals 0.8" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="10" fill="var(--muted)" font-size="8">acceptance = shaded overlap = sum min(p,q) = 0.80</text>
  <line x1="30" y1="82" x2="292" y2="82" stroke="var(--grid)"/>
  <rect x="34" y="34" width="30" height="48" fill="var(--s1)"/><text x="38" y="94" fill="var(--muted)" font-size="7">the</text>
  <rect x="70" y="58" width="30" height="24" fill="var(--s1)"/><text x="74" y="94" fill="var(--muted)" font-size="7">a</text>
  <rect x="106" y="58" width="30" height="24" fill="var(--s1)"/><text x="110" y="94" fill="var(--muted)" font-size="7">cat</text>
  <rect x="142" y="70" width="30" height="12" fill="var(--s1)"/><text x="146" y="94" fill="var(--muted)" font-size="7">dog</text>
  <rect x="178" y="70" width="30" height="12" fill="var(--s1)"/><text x="182" y="94" fill="var(--muted)" font-size="7">runs</text>
  <text x="224" y="46" fill="var(--muted)" font-size="8">overlap 0.80</text>
  <text x="224" y="60" fill="var(--muted)" font-size="8">→ 3.36 tok/pass</text>
  <text x="6" y="101" fill="var(--muted)" font-size="8">each bar is min(p,q) for that token; their sum is the acceptance rate</text>
</svg>
^ Acceptance is the shaded overlap between target and draft — the sum of the per-token minimum, 0.80 here — and that overlap is what turns a draft block into ~3.36 tokens per target pass.

## Definition of done

The self-test pins both properties: the speculative output equals the target to machine precision, the naive rule is measurably biased, and the acceptance and speedup match their closed forms.

```python filename=modules/below-the-prompt/code/specdecode-inter-01/specdecode.py:110-123 COMPLETE
    spec_exact = tv(out, p) < 1e-12
    print("  the speculative output equals the target distribution = %s (TV = %.2e)" % (spec_exact, tv(out, p)))

    naive_biased = tv(q, p) > 0.01
    print("  'keep the draft token' is biased away from the target = %s (TV = %.3f)" % (naive_biased, tv(q, p)))

    spec_is_distribution = abs(sum(out) - 1.0) < 1e-12 and all(o >= -1e-12 for o in out)
    print("  the speculative output is a valid probability distribution = %s (sum = %.6f)" % (spec_is_distribution, sum(out)))

    accept_is_one_minus_tv = abs(a - (1 - tv(p, q))) < 1e-12
    print("  acceptance equals 1 - TV(target, draft) = %s (%.3f)" % (accept_is_one_minus_tv, a))

    net_speedup = expected_tokens(a, k) > 1.0 + 1e-9
    print("  the target emits more than one token per pass (net speedup) = %s (%.3f)" % (net_speedup, expected_tokens(a, k)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the correct rule is exact; 'keep the draft' is biased; acceptance and speedup match theory
------------------------------------------------------------------------------------------------------
  the speculative output equals the target distribution = True (TV = 8.33e-17)
  'keep the draft token' is biased away from the target = True (TV = 0.200)
  the speculative output is a valid probability distribution = True (sum = 1.000000)
  acceptance equals 1 - TV(target, draft) = True (0.800)
  the target emits more than one token per pass (net speedup) = True (3.362)
```

**Done means both halves are proven: the accept-min(1,p/q)-else-resample-residual rule emits the target distribution to a TV of 8e-17 while "keep the draft" sits 0.20 away, and the acceptance equals 1 − TV(target, draft) = 0.80, which turns a 4-token draft block into 3.36 emitted tokens per target pass.**

## Boss fight

The rule is exact, so predict the two places its exactness quietly leaks — the part that is only exact in theory, and the part that stops being exact the moment you change the temperature after measuring.

The first leak is the residual, and it is the step everyone drops. It is tempting, on a rejection, to just resample a fresh token from the target p — that is wrong. The accept branch has already spent some of p's mass (every token the draft could have proposed and had accepted), so resampling from the full p double-counts it and biases the result back toward the draft. The correct rejection distribution is the *residual*, the normalized positive part of p − q, which is exactly the mass the draft failed to deliver. This is the single line most hand-rolled implementations get wrong, and the bias it introduces is subtle — the output is still a valid distribution, just not p — so it survives casual testing and only shows up as a quality regression nobody can localize.

```python filename=modules/below-the-prompt/code/specdecode-inter-01/specdecode.py:48-52 COMPLETE
def residual(p, q):
    """The distribution to resample from after a rejection: the normalized positive part of p - q."""
    pos = [max(0.0, pi - qi) for pi, qi in zip(p, q)]
    z = sum(pos)
    return [x / z for x in pos]
```

The second leak is that "exact" means exact with respect to the p you actually verify against. Speculative decoding preserves whatever target distribution the verifier computes — so if the draft samples at temperature 1 but you want the target at temperature 0.7, the verifier must use the temperature-0.7 p, or the guarantee holds for the wrong distribution. The same applies to top-p and top-k truncation, repetition penalties, and logit biases: every transform that shapes the target's logits has to be inside the p the acceptance test uses, not bolted on after. Get that alignment wrong and the math is still "exact" — it faithfully reproduces a distribution you did not intend. And the acceptance rate α is not a free lunch you can tune to infinity: pushing the draft closer to the target (bigger draft, distillation, aligned temperatures) raises α and the tokens-per-pass, but a draft as expensive as the target erases the speedup, so the real design target is the sweet spot where α is high and the draft is cheap. Exactness is a property of the rule; the speedup is a property of the draft, and only the second one is yours to negotiate.

**Speculative decoding emits the target distribution exactly only under the full rule — accept with probability min(1, p/q) and, crucially, resample rejections from the residual (normalized positive part of p − q), never from the full p — and only for the p you actually verify against, so every temperature, truncation, and penalty must live inside that p; the draft then buys speed through the acceptance rate 1 − TV(p, q) without ever moving the output.**

## External resources

The speculative-sampling papers (Leviathan et al., "Fast Inference from Transformers via Speculative Decoding"; Chen et al., "Accelerating Large Language Model Decoding with Speculative Sampling") — the original derivations of the accept/residual rule and the proof that the emitted token is distributed exactly as the target.

Any reference on rejection sampling and the relationship between total-variation distance and the overlap sum min(p, q) — the general probability machinery the acceptance rate and the residual come from.

The companion "temperature and top-p shape the softmax" and "the KV cache — reuse the past" modules — speculative decoding must verify against the same shaped, truncated target distribution those modules build, and it reuses the KV cache across the draft block, so the three compose into one inference path.
