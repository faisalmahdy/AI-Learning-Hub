#!/usr/bin/env python3
"""Compare secrets in constant time, or leak them one character at a time.

Checking a token or password with `==` feels safe -- it returns True only on an
exact match. But `==` stops at the first differing character, so a guess that
shares more of its prefix with the secret takes measurably longer to reject. An
attacker who can time the comparison learns the secret one character at a time,
turning an impossible brute force (the whole secret at once) into a cheap linear
search. The fix is a constant-time compare that always looks at every character.
This measures the leak with a deterministic proxy -- the number of characters
compared before returning -- and mounts the character-at-a-time attack against
both comparisons.

  --compare G     characters compared for one guess, naive (early-exit) vs constant
  --leak          the comparison count rises as a guess shares more of the prefix
  --attack        recover the secret char-by-char against each comparison
  --check         the naive compare leaks and is broken; the constant-time one is not

Uses the character-comparison count as a stand-in for wall-clock time so the whole
thing is deterministic and offline. Stdlib only. The secret is a fixture.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONF = HERE / "secret.json"


def load():
    data = json.loads(CONF.read_text(encoding="utf-8"))
    return data["secret"], data["alphabet"]


# --------------------------------------------------------------- the two compares

def naive_equal(guess, secret):
    """THE BUG: `==`-style early exit. Returns at the first mismatch, so the number
    of characters compared -- a proxy for time -- depends on the shared prefix."""
    compares = 0
    if len(guess) != len(secret):
        return False, 0
    for g, s in zip(guess, secret):
        compares += 1
        if g != s:
            return False, compares          # stops early: leaks the prefix length
    return True, compares


def constant_equal(guess, secret):
    """The fix (like hmac.compare_digest): always compare every character, accumulate
    the difference, and decide at the end. Same count for every same-length guess."""
    if len(guess) != len(secret):
        return False, 0
    diff = 0
    compares = 0
    for g, s in zip(guess, secret):
        compares += 1
        diff |= ord(g) ^ ord(s)             # never short-circuits
    return diff == 0, compares


# ------------------------------------------------------------------- the attack

def recover(secret, alphabet, compare):
    """Guess the secret one position at a time: at each position, the correct char is
    the one whose guess makes the comparison run the longest (against a leaky compare)."""
    known = ""
    for _ in range(len(secret)):
        best_char, best_key = alphabet[0], (-1, 0)
        for c in alphabet:
            guess = (known + c).ljust(len(secret), alphabet[0])
            equal, count = compare(guess, secret)
            # more characters compared is the timing signal; the equality result
            # only breaks the tie at the final position, where counts are flat.
            key = (count, 1 if equal else 0)
            if key > best_key:
                best_key, best_char = key, c
        known += best_char
    return known


# ------------------------------------------------------------------- printing

def compare_view(secret, guess):
    _, nc = naive_equal(guess.ljust(len(secret), secret[0])[:len(secret)], secret)
    _, cc = constant_equal(guess.ljust(len(secret), secret[0])[:len(secret)], secret)
    print("COMPARE — characters examined for guess %r" % guess)
    print("-" * 60)
    print("  naive (early exit)   compared %d character(s)" % nc)
    print("  constant time        compared %d character(s)" % cc)
    print("-" * 60)
    print("  the naive count changes with the guess; the constant count never does.")


def leak_view(secret, alphabet):
    print("THE LEAK — comparison count vs how much of the prefix a guess gets right")
    print("-" * 60)
    print("  correct prefix   guess                naive count   constant count")
    for k in range(len(secret) + 1):
        guess = (secret[:k] + alphabet[0] * (len(secret) - k))
        if k < len(secret) and secret[k] == alphabet[0]:
            guess = secret[:k] + alphabet[1] + alphabet[0] * (len(secret) - k - 1)
        _, nc = naive_equal(guess, secret)
        _, cc = constant_equal(guess, secret)
        print("  %-15d %-20r %-13d %d" % (k, guess, nc, cc))
    print("-" * 60)
    print("  the naive count climbs with each correct leading character -- that rise")
    print("  is the side channel; the constant count is flat, so there is nothing to read.")


def attack_view(secret, alphabet):
    print("THE ATTACK — recover the secret one character at a time")
    print("-" * 60)
    got_naive = recover(secret, alphabet, naive_equal)
    got_const = recover(secret, alphabet, constant_equal)
    print("  against naive compare    recovered %r  -> %s" % (got_naive, "SECRET LEAKED" if got_naive == secret else "failed"))
    print("  against constant compare recovered %r  -> %s" % (got_const, "SECRET LEAKED" if got_const == secret else "held"))
    print("-" * 60)
    print("  the flat count gives the attacker no gradient to climb, so the guess")
    print("  collapses to the first alphabet character -- the secret stays secret.")


def check(secret, alphabet):
    print("SELF-TEST — the naive compare leaks the secret; constant time does not")
    print("-" * 60)

    got_naive = recover(secret, alphabet, naive_equal)
    got_const = recover(secret, alphabet, constant_equal)
    print("  attack vs naive recovers the secret = %s (%r)" % (got_naive == secret, got_naive))
    print("  attack vs constant recovers the secret = %s (%r)" % (got_const == secret, got_const))
    naive_broken = got_naive == secret
    const_safe = got_const != secret

    # the leak itself: naive counts differ across guesses of different prefix length.
    counts = set()
    for k in range(len(secret)):
        guess = secret[:k] + ("x" if secret[k] != "x" else "y") + "a" * (len(secret) - k - 1)
        counts.add(naive_equal(guess, secret)[1])
    naive_varies = len(counts) > 1
    print("  naive comparison count varies with the guess = %s (%d distinct)" % (naive_varies, len(counts)))

    # constant count is the same for every same-length guess.
    const_counts = {constant_equal("a" * len(secret), secret)[1],
                    constant_equal(secret, secret)[1],
                    constant_equal(secret[:-1] + ("z" if secret[-1] != "z" else "q"), secret)[1]}
    const_flat = len(const_counts) == 1
    print("  constant comparison count is identical across guesses = %s" % const_flat)

    # both compares still agree on the actual answer.
    correct = constant_equal(secret, secret)[0] and not constant_equal("a" * len(secret), secret)[0]
    print("  constant compare still returns the right answer = %s" % correct)

    ok = naive_broken and const_safe and naive_varies and const_flat and correct
    print("-" * 60)
    print("SELF-TEST %s  naive_leaks=%s  constant_holds=%s  count_varies=%s  count_flat=%s"
          % ("PASS" if ok else "FAIL", naive_broken, const_safe, naive_varies, const_flat))
    return ok


def main():
    p = argparse.ArgumentParser(description="Constant-time secret comparison vs the timing leak.")
    p.add_argument("--compare", metavar="G")
    p.add_argument("--leak", action="store_true")
    p.add_argument("--attack", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    secret, alphabet = load()
    print("secret_len=%d  alphabet=%d chars  file=%s  (secret is a fixture)"
          % (len(secret), len(alphabet), CONF.name))
    print("")

    if args.check:
        return 0 if check(secret, alphabet) else 1
    if args.compare:
        compare_view(secret, args.compare)
    elif args.leak:
        leak_view(secret, alphabet)
    elif args.attack:
        attack_view(secret, alphabet)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
