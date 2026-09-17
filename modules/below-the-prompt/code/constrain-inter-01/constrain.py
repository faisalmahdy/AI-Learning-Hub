"""Mask the illegal next-tokens to negative infinity before the softmax, so generation is valid by construction -- an unconstrained decoder picks from the whole vocabulary and will emit a token the required format forbids.

A language model's head assigns a logit to every token in the vocabulary. Softmax turns those into a probability distribution and the decoder samples or takes the argmax. Nothing in that distribution encodes the output format the caller needs: the model was trained to predict likely text, not to guarantee valid JSON or a well-formed field. So at any position the most probable token can be one the grammar does not allow, and an unconstrained decoder emits it -- producing output that is invalid under the grammar even though every individual token was the model's honest preference.

The fix operates on the logits, at the same place the causal mask does. At each position the grammar knows which tokens are legal; set every illegal token's logit to negative infinity before the softmax. After the exponential, negative infinity becomes exactly zero probability, so the softmax renormalizes over the legal tokens alone and the decoder can only choose among them. The output is valid by construction -- not checked after the fact and repaired, but made impossible to violate.

Crucially, masking does not override the model; it filters it. Among the legal tokens the relative logits are untouched, so the chosen token is the most probable legal one -- the model's preference honored within the grammar. If the model wanted an illegal token most and a particular legal token second, constrained decoding gives that legal token, which is exactly the intended behavior.

On this fixture the output must match digit-colon-digit, but the model's raw argmax is illegal at every position (a letter, then a digit where a colon is required, then a colon where a digit is required), so the unconstrained decode is 'x2:' -- not a valid digit-colon-digit string. Constrained decoding masks the illegal tokens and yields '1:0', valid, each token the best legal option. This computes both.

  --naive       unconstrained argmax over the whole vocab: an invalid string
  --constrained mask illegal tokens before the softmax: a valid string, best legal token per position
  --check       the unconstrained decode is invalid while the constrained decode is valid and picks the best legal token at each position

vocab, the per-position legal tokens, and the logits are the fixture; the two decodes and the masked distributions are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "constrain.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def masked_softmax(logits, allowed_idx):
    """Softmax after setting illegal logits to -inf: legal tokens get a renormalized distribution, illegal ones 0."""
    masked = [(lg if i in allowed_idx else float("-inf")) for i, lg in enumerate(logits)]
    hi = max(masked)
    exps = [math.exp(lg - hi) if lg != float("-inf") else 0.0 for lg in masked]
    total = sum(exps)
    return [e / total for e in exps]


def best_token(logits, allowed_idx):
    """The argmax over the allowed tokens -- the most probable legal next token at this position."""
    return max(allowed_idx, key=lambda i: logits[i])


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


# ----------------------------------------------------------------- printing

def _text(data, idxs):
    return "".join(data["vocab"][i] for i in idxs)


def _valid(data, idxs):
    return all(data["vocab"][i] in data["legal_per_pos"][pos] for pos, i in enumerate(idxs))


def naive_view(data):
    idxs = decode(data, constrained=False)
    print("NAIVE — argmax over the whole vocabulary at each position")
    print("-" * 64)
    for pos, i in enumerate(idxs):
        legal = data["vocab"][i] in data["legal_per_pos"][pos]
        print("  pos %d: picked %r  legal here? %s  (legal set %s)" % (pos, data["vocab"][i], legal, data["legal_per_pos"][pos]))
    print("  output = %r   valid digit:digit? %s" % (_text(data, idxs), _valid(data, idxs)))
    print("-" * 64)
    print("  nothing stopped an illegal token, so the output does not match the required format")


def constrained_view(data):
    idxs = decode(data, constrained=True)
    print("CONSTRAINED — mask illegal tokens to -inf before the softmax")
    print("-" * 64)
    for pos, i in enumerate(idxs):
        allowed = {data["vocab"].index(t) for t in data["legal_per_pos"][pos]}
        probs = masked_softmax(data["logits_per_pos"][pos], allowed)
        print("  pos %d: picked %r  p(legal)=%.3f  (illegal tokens have p=0)" % (pos, data["vocab"][i], probs[i]))
    print("  output = %r   valid digit:digit? %s" % (_text(data, idxs), _valid(data, idxs)))
    print("-" * 64)
    print("  the choice is the most probable LEGAL token, so the output is valid by construction")


def check(data):
    print("SELF-TEST — the unconstrained decode is invalid while the constrained decode is valid and picks the best legal token at each position")
    print("-" * 112)
    naive = decode(data, constrained=False)
    constrained = decode(data, constrained=True)

    naive_invalid = not _valid(data, naive)
    print("  the unconstrained decode is invalid = %s (%r)" % (naive_invalid, _text(data, naive)))

    naive_illegal_every_pos = all(data["vocab"][i] not in data["legal_per_pos"][pos] for pos, i in enumerate(naive))
    print("  the unconstrained argmax is illegal at every position = %s" % naive_illegal_every_pos)

    constrained_valid = _valid(data, constrained)
    print("  the constrained decode is valid = %s (%r)" % (constrained_valid, _text(data, constrained)))

    constrained_is_best_legal = all(
        constrained[pos] == best_token(data["logits_per_pos"][pos], {data["vocab"].index(t) for t in data["legal_per_pos"][pos]})
        for pos in range(len(constrained)))
    print("  each constrained token is the most probable legal one = %s" % constrained_is_best_legal)

    illegal_prob_is_zero = all(
        masked_softmax(data["logits_per_pos"][pos], {data["vocab"].index(t) for t in data["legal_per_pos"][pos]})[naive[pos]] == 0.0
        for pos in range(len(naive)) if data["vocab"][naive[pos]] not in data["legal_per_pos"][pos])
    print("  masking gives the illegal tokens exactly zero probability = %s" % illegal_prob_is_zero)

    ok = (naive_invalid and naive_illegal_every_pos and constrained_valid
          and constrained_is_best_legal and illegal_prob_is_zero)
    print("-" * 112)
    print("SELF-TEST %s  naive_invalid=%s  naive_illegal_every_pos=%s  constrained_valid=%s  constrained_is_best_legal=%s  illegal_prob_is_zero=%s"
          % ("PASS" if ok else "FAIL", naive_invalid, naive_illegal_every_pos, constrained_valid,
             constrained_is_best_legal, illegal_prob_is_zero))
    return ok


def main():
    p = argparse.ArgumentParser(description="Constrained decoding: mask the grammar's illegal next-tokens to -inf before the softmax so generation can only produce valid output, because the model's logits do not encode the required format and an unconstrained decoder will emit the most probable token even when the grammar forbids it.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--constrained", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("vocab=%s  legal_per_pos=%s  file=%s  (these are a fixture)"
          % (data["vocab"], data["legal_per_pos"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.constrained:
        constrained_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
