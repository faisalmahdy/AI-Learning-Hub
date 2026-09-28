"""Accept the draft token with probability min(1, p/q) and resample the rest -- or you sample the small model, not the big one.

Speculative decoding runs a small fast "draft" model to propose the next token and a big slow "target" model to check
it, so the target can verify several proposed tokens in one forward pass instead of generating them one at a time.
The tempting shortcut is: let the draft propose a token, and if it looks fine, just keep it. But "keep the draft's
token" samples the DRAFT'S distribution q, not the target's distribution p -- the whole reason you run the big model
is that q is not p, so keeping draft tokens silently swaps the model you are sampling from. The output is biased by
exactly how far q sits from p.

The correct rule makes the speedup free of that bias. Draft a token x from q; accept it with probability
min(1, p(x) / q(x)); if it is rejected, do not fall back to a draft token -- resample from the RESIDUAL
distribution, the normalized positive part of p - q. That single rule has an exact guarantee: the token you emit is
distributed exactly as p, the target's own distribution, for any draft q whatsoever. The draft only changes the
SPEED, never the output: the fraction of proposals accepted is sum_x min(p(x), q(x)) = 1 - TV(p, q), so a draft
that agrees with the target often lets the target confirm a whole block of tokens in one pass, while a bad draft
just gets rejected down to ordinary one-token-at-a-time decoding. Faster when the draft is good, never wrong.

On this fixture the target and draft are two distributions over five tokens. The acceptance probability is
sum min(p,q) = 0.80, so the residual carries the remaining 0.20. Reconstructing the output distribution from the
accept-or-resample rule returns the target exactly (total-variation distance 0), while "just keep the draft" returns
the draft (total-variation distance 0.20 from the target). With draft_len=4 the target emits about 3.36 tokens per
forward pass instead of 1. This computes all of it exactly, no sampling.

  --verify   the speculative rule reproduces the target exactly; "keep the draft" reproduces the draft (biased)
  --speed    acceptance = 1 - TV(target, draft), and the expected tokens the target emits per forward pass
  --check    the correct rule is exact (TV 0); the naive rule is biased (TV>0); acceptance and speedup match theory

The two distributions and the draft length are the fixture; every probability is computed exactly. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "specdecode.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def acceptance(p, q):
    """Fraction of draft proposals the target accepts = sum min(p, q) = 1 - TV(p, q)."""
    return sum(min(pi, qi) for pi, qi in zip(p, q))


def residual(p, q):
    """The distribution to resample from after a rejection: the normalized positive part of p - q."""
    pos = [max(0.0, pi - qi) for pi, qi in zip(p, q)]
    z = sum(pos)
    return [x / z for x in pos]


def speculative_output(p, q):
    """The exact output distribution of accept-with-prob-min(1,p/q)-else-resample-residual. Equals p."""
    reject = 1.0 - acceptance(p, q)
    res = residual(p, q)
    out = []
    for pi, qi, ri in zip(p, q, res):
        accept_prob = min(1.0, pi / qi) if qi > 0 else 0.0
        out.append(qi * accept_prob + reject * ri)
    return out


def tv(a, b):
    """Total-variation distance between two distributions: half the sum of absolute differences."""
    return 0.5 * sum(abs(ai - bi) for ai, bi in zip(a, b))


def expected_tokens(alpha, k):
    """Expected tokens the target emits per forward pass with acceptance alpha and draft block length k."""
    return (1 - alpha ** (k + 1)) / (1 - alpha)


# ----------------------------------------------------------------- printing

def verify_view(data):
    vocab, p, q = data["vocab"], data["target"], data["draft"]
    out = speculative_output(p, q)
    print("VERIFY — the speculative rule emits the TARGET's distribution, not the draft's")
    print("-" * 70)
    print("  token     target p   draft q    spec-out    keep-draft")
    for v, pi, qi, oi in zip(vocab, p, q, out):
        print("  %-8s  %.3f      %.3f      %.3f       %.3f" % (v, pi, qi, oi, qi))
    print("-" * 70)
    print("  TV(spec-out, target)   = %.3f   (accept-or-resample is exact)" % tv(out, p))
    print("  TV(keep-draft, target) = %.3f   (keeping draft tokens samples q, not p)" % tv(q, p))


def speed_view(data):
    p, q, k = data["target"], data["draft"], data["draft_len"]
    a = acceptance(p, q)
    print("SPEED — acceptance is 1 - TV, and it multiplies tokens per target forward pass")
    print("-" * 66)
    print("  acceptance  alpha = sum min(p,q) = %.3f   ( = 1 - TV = 1 - %.3f )" % (a, tv(p, q)))
    print("  draft block length k               = %d" % k)
    print("  expected tokens per target pass    = %.3f   (vs 1.000 for plain decoding)" % expected_tokens(a, k))
    print("-" * 66)
    print("  a good draft (alpha near 1) confirms a whole block per pass; a bad one falls back to 1.")


def check(data):
    print("SELF-TEST — the correct rule is exact; 'keep the draft' is biased; acceptance and speedup match theory")
    print("-" * 102)
    p, q, k = data["target"], data["draft"], data["draft_len"]
    out = speculative_output(p, q)
    a = acceptance(p, q)

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

    ok = spec_exact and naive_biased and spec_is_distribution and accept_is_one_minus_tv and net_speedup
    print("-" * 102)
    print("SELF-TEST %s  spec_exact=%s  naive_biased=%s  spec_is_distribution=%s  accept_is_one_minus_tv=%s  net_speedup=%s"
          % ("PASS" if ok else "FAIL", spec_exact, naive_biased, spec_is_distribution, accept_is_one_minus_tv, net_speedup))
    return ok


def main():
    p = argparse.ArgumentParser(description="Speculative decoding: accept the draft token with prob min(1,p/q) and resample the residual on rejection, which emits the target distribution exactly while letting the draft supply the speedup.")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--speed", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("vocab=%s  draft_len=%d  file=%s  (the two distributions are a fixture)"
          % (data["vocab"], data["draft_len"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.verify:
        verify_view(data)
    elif args.speed:
        speed_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
