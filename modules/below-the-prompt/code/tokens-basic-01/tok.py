#!/usr/bin/env python3
"""Tokens are the unit, not words: a tiny BPE, and the budget bug word-counting hides.

A model reads tokens -- chunks a byte-pair encoding (BPE) learns by merging the
most frequent adjacent pairs. Common words compress to one token; a rare word the
tokenizer never saw shatters into many. So "one word is about one token" is true
for the words you expect and badly false for the ones you don't, and a token
budget estimated by word count sails past on rare or dense text. This trains a
small BPE, shows a rare word costing five tokens, and measures the budget bug.

  --train        learn the merges from the corpus (letter pairs grow into words)
  --encode T     tokenize one string: its words vs its tokens
  --ratios       words and tokens for varied strings -- watch one word become five
  --budget       a token budget: what word-count says fits vs what truly fits
  --check        a rare word explodes in tokens; the word estimate says it is fine

Stdlib only. No network, no model -- the BPE is trained on a committed corpus.
Deterministic. Point it at your own text and your own token budget.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus.json"

NUM_MERGES = 60       # how many byte-pair merges to learn


def load():
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    return data["train_text"], data["samples"], data["budget"]


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


# --------------------------------------------------------------- training BPE

def learn_merges(text, num_merges):
    """Classic BPE: split each word into characters, then repeatedly merge the most
    frequent adjacent pair across the corpus. Returns the ordered merge list."""
    vocab = Counter(tuple(w) for w in words(text))
    merges = []
    for _ in range(num_merges):
        pairs = Counter()
        for word, freq in vocab.items():
            for i in range(len(word) - 1):
                pairs[(word[i], word[i + 1])] += freq
        if not pairs:
            break
        best = max(pairs.items(), key=lambda x: (x[1], x[0]))[0]
        merges.append(best)
        merged = {}
        for word, freq in vocab.items():
            w, i = [], 0
            while i < len(word):
                if i < len(word) - 1 and (word[i], word[i + 1]) == best:
                    w.append(word[i] + word[i + 1])
                    i += 2
                else:
                    w.append(word[i])
                    i += 1
            merged[tuple(w)] = merged.get(tuple(w), 0) + freq
        vocab = merged
    return merges


def encode_word(word, merges):
    """Apply the learned merges in order to one word -> its tokens."""
    w = list(word)
    for a, b in merges:
        out, i = [], 0
        while i < len(w):
            if i < len(w) - 1 and w[i] == a and w[i + 1] == b:
                out.append(a + b)
                i += 2
            else:
                out.append(w[i])
                i += 1
        w = out
    return w


def encode(text, merges):
    toks = []
    for wd in words(text):
        toks.extend(encode_word(wd, merges))
    return toks


# ------------------------------------------------------- the two length estimates

def word_estimate(text):
    """THE BUG: estimate token count as word count -- 'one word, one token'."""
    return len(words(text))


def true_tokens(text, merges):
    """The real token count: encode and count."""
    return len(encode(text, merges))


# ------------------------------------------------------------------- printing

def train_view(text):
    for k in (10, 30, NUM_MERGES):
        m = learn_merges(text, k)
        print("  %2d merges -> newest three: %s" % (k, ["".join(p) for p in m[-3:]]))
    print("-" * 62)
    print("  merges grow from letter pairs (th, er) into whole common words (the).")


def encode_view(merges, s):
    print("  %r" % s)
    print("    words: %d   tokens: %d" % (word_estimate(s), true_tokens(s, merges)))
    print("    tokens: %s" % encode(s, merges))


def ratios_view(samples, merges):
    print("WORDS vs TOKENS — one word is not one token")
    print("-" * 62)
    print("  %-28s words  tokens  tokens/word" % "text")
    for s in samples:
        w, t = word_estimate(s), true_tokens(s, merges)
        print("  %-28s %4d   %5d   %.2f" % (s[:28], w, t, t / w if w else 0))
    print("-" * 62)
    print("  a common word is ~1 token; a rare word the tokenizer never saw is many,")
    print("  so tokens-per-word swings and a word count cannot predict the token count.")


def budget_view(samples, merges, budget):
    print("BUDGET — a %d-token window: what word-count says fits vs what truly fits" % budget)
    print("-" * 62)
    print("  text                          words  says-fit   tokens  really-fits")
    for s in samples:
        w, t = word_estimate(s), true_tokens(s, merges)
        says = "fits" if w <= budget else "no"
        really = "fits" if t <= budget else "OVERFLOW"
        flag = "  <-- word count lied" if w <= budget and t > budget else ""
        print("  %-28s %4d   %-8s   %5d   %s%s" % (s[:28], w, says, t, really, flag))
    print("-" * 62)
    print("  every sample 'fits' by word count; the rare-word ones blow the budget in")
    print("  tokens. Budget on encoded tokens, never on a word or character estimate.")


def check(samples, merges, budget):
    print("SELF-TEST — a rare word explodes in tokens; the word estimate misses it")
    print("-" * 62)

    # the word estimate says every sample fits; the truth overflows on some.
    all_fit_by_words = all(word_estimate(s) <= budget for s in samples)
    overflow = [s for s in samples if true_tokens(s, merges) > budget]
    print("  every sample fits by word count = %s" % all_fit_by_words)
    print("  samples that truly overflow the %d-token budget = %d %s"
          % (budget, len(overflow), [s[:16] for s in overflow]))
    lie = all_fit_by_words and len(overflow) > 0

    # the mechanism: a rare word costs several tokens, a common word costs one.
    tpw = lambda s: true_tokens(s, merges) / max(1, word_estimate(s))
    common = min(samples, key=tpw)
    rare = max(samples, key=tpw)
    swings = tpw(rare) >= 2 * tpw(common)
    print("  tokens/word swings across text = %s (%.2f rare vs %.2f common)"
          % (swings, tpw(rare), tpw(common)))

    # a single rare word is more than one token.
    rare_word_tokens = true_tokens("qwerty", merges)
    explodes = rare_word_tokens > 1
    print("  the rare word 'qwerty' is %d tokens, not 1 = %s" % (rare_word_tokens, explodes))

    # merges are learned from data, not hand-set.
    m5 = learn_merges(load()[0], 5)
    learned = len(m5) == 5
    print("  BPE learned 5 merges from the corpus = %s (%s)" % (learned, ["".join(p) for p in m5]))

    det = encode(samples[0], merges) == encode(samples[0], merges)
    ok = lie and swings and explodes and learned and det
    print("-" * 62)
    print("SELF-TEST %s  word_count_lies=%s  swings=%s  rare_explodes=%s  learned=%s"
          % ("PASS" if ok else "FAIL", lie, swings, explodes, learned))
    return ok


def main():
    p = argparse.ArgumentParser(description="A tiny BPE and the word-count budget bug.")
    p.add_argument("--train", action="store_true")
    p.add_argument("--encode", metavar="T")
    p.add_argument("--ratios", action="store_true")
    p.add_argument("--budget", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    text, samples, budget = load()
    merges = learn_merges(text, NUM_MERGES)
    print("corpus_words=%d  merges=%d  budget=%d tok  file=%s  (corpus is a fixture)"
          % (len(words(text)), len(merges), budget, CORPUS.name))
    print("")

    if args.check:
        return 0 if check(samples, merges, budget) else 1
    if args.train:
        train_view(text)
    elif args.encode:
        encode_view(merges, args.encode)
    elif args.ratios:
        ratios_view(samples, merges)
    elif args.budget:
        budget_view(samples, merges, budget)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
