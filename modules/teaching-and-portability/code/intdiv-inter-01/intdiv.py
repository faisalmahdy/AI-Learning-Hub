"""Integer division rounds two different ways across languages, so a ported remainder flips sign and a hash bucket goes negative.

Every language agrees that dividing positives gives the same integer quotient and remainder. They disagree the instant a
negative is involved, because there are two ways to round the quotient to an integer. Python and Ruby FLOOR toward
negative infinity: -7 divided by 3 rounds down to -3... no, to -4, and the remainder is +2, taking the sign of the
DIVISOR so it is never negative for a positive divisor. C, Java, Go, JavaScript, and Rust TRUNCATE toward zero: -7
divided by 3 rounds to -2, and the remainder is -1, taking the sign of the DIVIDEND. Same operands, same operators,
different answers -- so a formula that is correct in one language is wrong when you port it to the other, and the bug
hides until a negative value flows through.

The place this bites hardest is `value % n`, the workhorse of hashing, indexing, and wrap-around. Programmers rely on it
to produce a number in [0, n) -- a valid bucket, a valid array index, a clock position. That is true in Python for any
value, but in a truncating language a negative value gives a NEGATIVE remainder, so `hash % num_buckets` returns a
negative index and reads out of bounds or selects the wrong bucket. The portable way to force a non-negative result in
ANY language is `((value % n) + n) % n`: it is a harmless no-op where the remainder is already non-negative and it lifts
a negative one back into range. Assume `%` is always non-negative and your code is a hidden crash waiting for the first
negative input on a truncating runtime.

On this fixture the negative pairs come out differently under the two roundings (the floored remainder is non-negative,
the truncated one can be negative), while both satisfy dividend = quotient*divisor + remainder. A negative hash gives a
negative bucket under truncation, which the portable formula corrects back into [0, num_buckets). This computes both.

  --divmod  each (dividend, divisor) under floored (Python) and truncated (C) division -- where and how they differ
  --bucket  a hash mapped to a bucket by floored %, truncated % (can go negative), and the portable ((h % n) + n) % n
  --check   the two roundings agree on non-negatives but differ on negatives; the portable form is always in [0, n)

The pairs, hashes, and bucket count are the fixture; every quotient and remainder is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "intdiv.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def floor_divmod(a, b):
    """Python/Ruby semantics: quotient floored toward -inf, remainder takes the divisor's sign (native // and %)."""
    return a // b, a % b


def trunc_divmod(a, b):
    """C/Java/Go/JS/Rust semantics: quotient truncated toward zero, remainder takes the dividend's sign."""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q, a - q * b


def portable_bucket(h, n):
    """A non-negative bucket in [0, n) under ANY language's %: lift a possibly-negative remainder back into range."""
    return ((trunc_divmod(h, n)[1]) + n) % n


# ----------------------------------------------------------------- printing

def divmod_view(data):
    print("DIVMOD — floored (Python/Ruby) vs truncated (C/Java/Go/JS/Rust) integer division")
    print("-" * 74)
    print("  a    b     floored q,r      truncated q,r    differ?")
    for a, b in data["pairs"]:
        fq, fr = floor_divmod(a, b)
        tq, tr = trunc_divmod(a, b)
        differ = (fq, fr) != (tq, tr)
        print("  %-4d %-4d  %-15s  %-15s  %s" % (a, b, "%d, %d" % (fq, fr), "%d, %d" % (tq, tr), differ))
    print("-" * 74)
    print("  positives agree; a negative operand splits the quotient and flips the remainder's sign.")


def bucket_view(data):
    n = data["num_buckets"]
    print("BUCKET — hash %% %d under each rule, and the portable form" % n)
    print("-" * 70)
    print("  hash      floored %%   truncated %%   portable ((h%%n)+n)%%n   in [0,%d)?" % n)
    for h in data["hashes"]:
        fr = floor_divmod(h, n)[1]
        tr = trunc_divmod(h, n)[1]
        pb = portable_bucket(h, n)
        print("  %-8d  %-9d  %-11d  %-20d  %s" % (h, fr, tr, pb, 0 <= pb < n))
    print("-" * 70)
    print("  the truncated column goes negative on a negative hash -- an out-of-bounds bucket; the portable one never does.")


def check(data):
    print("SELF-TEST — the two roundings agree on non-negatives but differ on negatives; the portable form is always in [0, n)")
    print("-" * 116)
    pairs, hashes, n = data["pairs"], data["hashes"], data["num_buckets"]

    agree_on_nonneg = all(floor_divmod(a, b) == trunc_divmod(a, b) for a, b in pairs if a >= 0 and b > 0)
    print("  floored and truncated agree when operands are non-negative = %s" % agree_on_nonneg)

    differ_on_neg = any(floor_divmod(a, b) != trunc_divmod(a, b) for a, b in pairs if a < 0 or b < 0)
    print("  they differ once a negative operand appears = %s" % differ_on_neg)

    identity_both = all(fq * b + fr == a and tq * b + tr == a
                        for a, b in pairs
                        for (fq, fr), (tq, tr) in [(floor_divmod(a, b), trunc_divmod(a, b))])
    print("  both satisfy dividend = quotient*divisor + remainder = %s" % identity_both)

    trunc_can_go_negative = any(trunc_divmod(h, n)[1] < 0 for h in hashes)
    print("  a truncated hash %% n can be negative (out-of-bounds bucket) = %s (%s)"
          % (trunc_can_go_negative, [trunc_divmod(h, n)[1] for h in hashes]))

    portable_in_range = all(0 <= portable_bucket(h, n) < n for h in hashes)
    print("  the portable ((h%%n)+n)%%n is always a valid bucket in [0,%d) = %s (%s)"
          % (n, portable_in_range, [portable_bucket(h, n) for h in hashes]))

    portable_matches_floor = all(portable_bucket(h, n) == floor_divmod(h, n)[1] for h in hashes)
    print("  the portable form equals Python's floored %% for every hash = %s" % portable_matches_floor)

    ok = agree_on_nonneg and differ_on_neg and identity_both and trunc_can_go_negative and portable_in_range and portable_matches_floor
    print("-" * 116)
    print("SELF-TEST %s  agree_on_nonneg=%s  differ_on_neg=%s  identity_both=%s  trunc_can_go_negative=%s  portable_in_range=%s  portable_matches_floor=%s"
          % ("PASS" if ok else "FAIL", agree_on_nonneg, differ_on_neg, identity_both, trunc_can_go_negative, portable_in_range, portable_matches_floor))
    return ok


def main():
    p = argparse.ArgumentParser(description="Integer division rounds toward -inf (Python/Ruby) or toward zero (C/Java/Go/JS/Rust), so a ported remainder flips sign; force a non-negative bucket with ((v % n) + n) % n.")
    p.add_argument("--divmod", action="store_true")
    p.add_argument("--bucket", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pairs=%s  hashes=%s  num_buckets=%d  file=%s  (the operands are a fixture)"
          % (data["pairs"], data["hashes"], data["num_buckets"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.divmod:
        divmod_view(data)
    elif args.bucket:
        bucket_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
