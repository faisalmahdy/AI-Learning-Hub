"""After a run of heads, tails is not 'due' -- an independent coin has no memory, and long runs are expected, not omens.

Watch a fair coin come up heads four times and something in you insists the next one is more likely to be tails -- the
coin is 'due' to balance out. That is the gambler's fallacy, and it is wrong for a precise reason: the coin has no
memory. Each flip is an independent event, so the probability of heads on the next flip is exactly what it always was,
regardless of how the previous flips landed. P(heads | four heads in a row) equals P(heads), full stop. The past flips
already happened; they do not reach forward to nudge the next one. The pull toward 'tails is due' comes from confusing
two true facts -- that long runs are rare to start, and that the long-run average is 50/50 -- into a false one: that the
coin corrects itself as it goes. It does not correct; it simply keeps flipping fresh.

The second half of the fallacy is treating a run itself as surprising. A run of k heads has probability only p^k to
start from a given point, but across a long sequence there are many starting points, so at least one long run is not
rare -- it is expected. See heads four times running and the instinct is that something is off; but in twenty flips a
run of four shows up nearly half the time, and a run of three in about four-fifths. Reading a streak as evidence of bias, or as a debt the coin must repay, are the
same error from two sides: both assume the independent flips are somehow coordinated.

The fallacy is specifically about INDEPENDENCE, and that is the real lesson for data. When the process genuinely has
memory -- a Markov coin whose next flip depends on the last, an autocorrelated time series, a system with momentum --
conditioning on the recent past is not a fallacy, it is correct, because the past really does inform the future. On this
fixture the fair coin's P(heads | run of heads) stays 0.500 for every run length, while a 'sticky' coin whose next flip
copies the last with probability 0.8 has P(heads | a head) = 0.8, far from its 50/50 long-run rate. Whether updating on
a streak is fallacy or inference depends entirely on whether the process is independent. This computes both.

  --conditional  P(next heads | a run of k heads) for the independent coin (unchanged) vs the sticky coin (elevated)
  --streaks      how likely a long run is by chance in a sequence -- long runs are expected, not anomalies
  --check        the independent conditional never moves; a run of k has prob p^k; the sticky coin's history matters

The coin parameters are the fixture; every probability is computed exactly. Stdlib only.
"""
import argparse
import json
import sys
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "gambler.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def conditional_independent(p, k):
    """P(next heads | first k flips all heads) for an independent coin, computed by enumerating weighted sequences."""
    joint_runH = 0.0   # P(first k heads AND next heads)
    marg_runH = 0.0    # P(first k heads)
    for seq in product([1, 0], repeat=k + 1):
        pr = 1.0
        for flip in seq:
            pr *= p if flip == 1 else (1 - p)
        if all(seq[i] == 1 for i in range(k)):      # first k are heads
            marg_runH += pr
            if seq[k] == 1:                          # and the next is heads
                joint_runH += pr
    return joint_runH / marg_runH


def conditional_sticky(p_hh, k):
    """P(next heads | a run of heads) for a Markov 'sticky' coin: depends only on the last flip, so it is p_hh."""
    return p_hh


def run_probability(p, k):
    """P(a specific run of k heads) = p^k."""
    return p ** k


def prob_at_least_one_run(n, k, p):
    """P(at least one run of >= k heads somewhere in n flips), by DP over the current consecutive-heads count."""
    # state[c] = P(after i flips, current head-run = c, and no run of k yet)
    state = [0.0] * k
    state[0] = 1.0
    absorbed = 0.0   # probability mass that has hit a run of k
    for _ in range(n):
        nxt = [0.0] * k
        for c in range(k):
            nxt[0] += state[c] * (1 - p)             # tails resets the run
            if c + 1 < k:
                nxt[c + 1] += state[c] * p           # heads extends the run
            else:
                absorbed += state[c] * p             # heads completes a run of k
        state = nxt
    return absorbed


# ----------------------------------------------------------------- printing

def conditional_view(data):
    p, K, sticky = data["fair_p"], data["run_length"], data["sticky_p_heads_after_heads"]
    print("CONDITIONAL — P(next heads | a run of k heads): independent coin vs sticky coin")
    print("-" * 70)
    print("  run k    independent (fair %.2f)    sticky (P(H|H)=%.2f)" % (p, sticky))
    for k in range(1, K + 1):
        print("  %-6d   %.3f                     %.3f" % (k, conditional_independent(p, k), conditional_sticky(sticky, k)))
    print("-" * 70)
    print("  the independent coin never moves off %.3f; the sticky coin sits at %.3f -- history matters only with memory." % (p, sticky))


def streaks_view(data):
    p, n = data["fair_p"], data["sequence_length"]
    print("STREAKS — how likely a run of k heads is by chance in %d fair flips" % n)
    print("-" * 58)
    print("  run k    P(a single run of k)   P(>=1 run of k in %d flips)" % n)
    for k in range(2, 6):
        print("  %-6d   %.4f                 %.3f" % (k, run_probability(p, k), prob_at_least_one_run(n, k, p)))
    print("-" * 58)
    print("  a run of 3 shows up in ~80% of 20-flip sequences and a run of 4 nearly half -- long runs are expected, not omens.")


def check(data):
    print("SELF-TEST — the independent conditional never moves; a run of k has prob p^k; the sticky coin's history matters")
    print("-" * 112)
    p, K, n, sticky = data["fair_p"], data["run_length"], data["sequence_length"], data["sticky_p_heads_after_heads"]

    independent_constant = all(abs(conditional_independent(p, k) - p) < 1e-9 for k in range(1, K + 1))
    print("  independent P(heads | run of k) equals p for every k = %s (%.3f)" % (independent_constant, conditional_independent(p, K)))

    not_due = abs(conditional_independent(p, K) - p) < 1e-9
    print("  after %d heads, heads is NOT less likely (no 'due') = %s (%.3f, not < %.3f)" % (K, not_due, conditional_independent(p, K), p))

    run_is_p_to_k = abs(run_probability(p, K) - p ** K) < 1e-12
    print("  a run of %d heads has probability p^%d = %s (%.4f)" % (K, K, run_is_p_to_k, run_probability(p, K)))

    long_runs_expected = prob_at_least_one_run(n, 3, p) > 0.5
    print("  a run of 3 in %d flips is more likely than not = %s (%.3f)" % (n, long_runs_expected, prob_at_least_one_run(n, 3, p)))

    memory_changes_conditional = abs(conditional_sticky(sticky, 1) - p) > 0.2
    print("  a coin WITH memory changes the conditional (so the fallacy is about independence) = %s (%.3f vs %.3f)"
          % (memory_changes_conditional, conditional_sticky(sticky, 1), p))

    ok = independent_constant and not_due and run_is_p_to_k and long_runs_expected and memory_changes_conditional
    print("-" * 112)
    print("SELF-TEST %s  independent_constant=%s  not_due=%s  run_is_p_to_k=%s  long_runs_expected=%s  memory_changes_conditional=%s"
          % ("PASS" if ok else "FAIL", independent_constant, not_due, run_is_p_to_k, long_runs_expected, memory_changes_conditional))
    return ok


def main():
    p = argparse.ArgumentParser(description="The gambler's fallacy: for independent trials a run does not make the other outcome 'due' (the conditional is unchanged) and long runs are expected; the fallacy is specifically about independence.")
    p.add_argument("--conditional", action="store_true")
    p.add_argument("--streaks", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("fair_p=%.2f  run_length=%d  sequence_length=%d  sticky_p=%.2f  file=%s  (the coins are a fixture)"
          % (data["fair_p"], data["run_length"], data["sequence_length"], data["sticky_p_heads_after_heads"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.conditional:
        conditional_view(data)
    elif args.streaks:
        streaks_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
