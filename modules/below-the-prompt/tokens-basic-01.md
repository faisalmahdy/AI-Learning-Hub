---
id: tokens-basic-01
title: One word is not one token — a tiny BPE and the budget that lies
topic: below-the-prompt
level: basic
status: ready
time: 6-8h
summary: Train a byte-pair encoder on plain English and a common word costs about one token, but a rare word the tokenizer never saw shatters into five — so "one word, one token" is true for the words you expect and false for the ones you don't. Give a 15-token window five snippets and every one fits by word count, yet the two built from rare words and numbers overflow at 19 and 21 tokens, because a token budget estimated in words sails past exactly on the text that breaks it.
eli5: A model reads text in chunks, not letters or words. Common words are one chunk each; a weird word you rarely see gets chopped into many. So counting words to guess how much fits is like counting suitcases to guess their weight — until one of them is full of bricks.
---

## Why this module

This opens the below-the-prompt track, which goes under the API to the machinery — tokenizers, attention, the KV cache — and it starts at the very first thing that happens to your text: it gets cut into tokens. A model never sees characters or words. It sees tokens, the chunks a byte-pair encoder produces, and almost every surprising limitation downstream — why models miscount letters, why a budget overflows, why a rare name costs a fortune — traces back to that cut. The scan lists these internals as "concept coverage is broad but zero implementation: no tiny-rebuilds executed." This is the first rebuild: the tokenizer, small enough to hold in your head and real enough to break a naive assumption.

The assumption is "one word is about one token." It is close enough to feel safe and wrong exactly when it costs you. A byte-pair encoder learns to merge frequent character pairs into subwords, so the common words it saw thousands of times collapse to a single token — but a rare word, a random string, a number, or a name it never saw stays shattered into many small pieces. Estimate a prompt's length by counting words and you will be right on ordinary prose and badly wrong on the dense, unusual text that is most likely to blow your context budget.

You need nothing but Python 3 and the standard library. Everything runs offline against a committed corpus, `$0.00`, one sitting. The instinct to unlearn is that text length is something you can eyeball in words or characters. Length, to a model, is measured in tokens, and tokens are only knowable by encoding.

Here is a 15-token window and five snippets that all "fit" by word count:

```
# modules/below-the-prompt/code/tokens-basic-01/ — COMPLETE, run from that directory
$ python3 tok.py --budget

BUDGET — a 15-token window: what word-count says fits vs what truly fits
--------------------------------------------------------------
  text                          words  says-fit   tokens  really-fits
  the cat sat on the mat and      7   fits           8   fits
  the children ran in the sun     6   fits           6   fits
  9 8 7 6 5 4 3 2 1 0 9 8 7 6    14   fits          14   fits
  xyzzy qwerty zxcvb plughh       4   fits          19   OVERFLOW  <-- word count lied
  invoice 4821 due 2026 03 28     6   fits          21   OVERFLOW  <-- word count lied
```

run: 2026-08-25 · deterministic; the corpus is a fixture · 60 merges, 15-token budget · `python3 tok.py --budget`

Every snippet has fewer than 15 words, so a word-count budget waves them all through. Two of them — four rare words, and a line of numbers — are actually 19 and 21 tokens, well over the window. The word count did not just mis-estimate; it lied most confidently about the shortest-looking text. This module is the tokenizer behind those numbers and why the four-word line is the biggest.

## Concepts

Named here so you can find them again; each is built below.

- **Token** — the unit a model actually reads: a character, a subword, or a whole common word.
- **Byte-pair encoding (BPE)** — learn a vocabulary by repeatedly merging the most frequent adjacent pair.
- **Merge** — one learned rule, "join these two symbols"; applied in order to encode.
- **Tokens per word** — how many tokens a word costs; ~1 for common words, many for rare ones.
- **The word estimate** — guessing token count from word count. Convenient, and the bug.
- **Token budget** — the real length limit, countable only by encoding.

## Worked example

Source: the below-the-prompt track's anatomy notes on tokenization (episode material on how text becomes tokens), rebuilt here as runnable code rather than prose. The corpus is ordinary English so the merges are the familiar ones.

Script and fixture: `modules/below-the-prompt/code/tokens-basic-01/` — `tok.py`, and `corpus.json`, a paragraph of training text and five sample strings. Every command runs from there.

### The frame: counting suitcases to guess the weight

Imagine a weight limit at the airport and you estimate your bag by counting suitcases: four cases, must be fine. It works until one case is full of bricks. Words are suitcases and tokens are pounds. Most words weigh about one token, so counting words usually approximates the weight — but a rare word is a case of bricks, five or six tokens for a single word, and no amount of counting cases reveals it. The only way to know the weight is to weigh it, and the only way to know the token count is to encode.

That is the whole module. The tokenizer decides which words are light and which are heavy, and it does so by what it saw during training: the words it saw often became single light tokens, and everything else stayed heavy. So the estimate that feels safe — one word, one token — is exactly inverted from where the risk is.

### Training the tokenizer: merge the frequent pairs

BPE starts with every word as a list of characters and repeatedly merges the most frequent adjacent pair into a new symbol. Do it enough times and frequent letter pairs become subwords, then whole common words.

```
# tok.py:44-70 — COMPLETE (learn merges by repeatedly joining the top pair)
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
```

Watch the vocabulary grow — the first merges are letter pairs, the later ones whole words:

```
# $ python3 tok.py --train
#   10 merges -> newest three: ['in', 'we', 'were']
#   30 merges -> newest three: ['ca', 'ay', 'wat']
#   60 merges -> newest three: ['watched', 'war', 'warm']
```

run: 2026-08-25 · fixture · `python3 tok.py --train`

The first five merges the corpus learns are `he`, `the`, `nd`, `and`, `wa` — the tokenizer is teaching itself that "the" and "and" are units, because it saw them constantly. Nothing hand-set that; frequency did.

<svg viewBox="0 0 700 150" role="img" aria-label="BPE merging: the word 'the' starts as three characters t, h, e, and two merges (t+h then th+e) collapse it to one token. The rare word 'xyzzy' has no frequent pairs, so it stays as five separate character tokens.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">a common word collapses to one token; a rare word stays shattered</text>
    <text x="20" y="52" fill="var(--ink)">the</text>
    <g><rect x="90" y="40" width="24" height="18" fill="var(--s1)" opacity="0.4"></rect><text x="97" y="53">t</text><rect x="116" y="40" width="24" height="18" fill="var(--s1)" opacity="0.4"></rect><text x="123" y="53">h</text><rect x="142" y="40" width="24" height="18" fill="var(--s1)" opacity="0.4"></rect><text x="149" y="53">e</text></g>
    <text x="180" y="53" fill="var(--muted)">-> merges -></text>
    <rect x="300" y="40" width="52" height="18" fill="var(--s1)"></rect><text x="312" y="53" fill="var(--panel)">the</text>
    <text x="370" y="53" fill="var(--s1)">1 token</text>
    <text x="20" y="100" fill="var(--ink)">xyzzy</text>
    <g><rect x="90" y="88" width="24" height="18" fill="var(--s2)" opacity="0.4"></rect><text x="97" y="101">x</text><rect x="116" y="88" width="24" height="18" fill="var(--s2)" opacity="0.4"></rect><text x="123" y="101">y</text><rect x="142" y="88" width="24" height="18" fill="var(--s2)" opacity="0.4"></rect><text x="149" y="101">z</text><rect x="168" y="88" width="24" height="18" fill="var(--s2)" opacity="0.4"></rect><text x="175" y="101">z</text><rect x="194" y="88" width="24" height="18" fill="var(--s2)" opacity="0.4"></rect><text x="201" y="101">y</text></g>
    <text x="240" y="101" fill="var(--muted)">-> no frequent pairs -></text>
    <text x="480" y="101" fill="var(--s2)">5 tokens</text>
  </g>
</svg>
^ "the" was seen so often that merges collapse it to a single token; "xyzzy" was never seen, so no merge applies and it stays five character tokens. Same length in words, five times the length in tokens.

### Encoding, and the two ways to measure length

Encoding applies the learned merges in order to a word.

```
# tok.py:73-86 — COMPLETE (apply merges in order to one word)
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
```

Now the two ways to measure a snippet's length — the cheap guess and the truth.

```
# tok.py:98-104 — COMPLETE (the word estimate vs the real token count)
def word_estimate(text):
    """THE BUG: estimate token count as word count -- 'one word, one token'."""
    return len(words(text))


def true_tokens(text, merges):
    """The real token count: encode and count."""
    return len(encode(text, merges))
```

Run them side by side and the estimate falls apart on rare words:

```
# $ python3 tok.py --ratios
#   text                         words  tokens  tokens/word
#   the cat sat on the mat and      7       8   1.14
#   the children ran in the sun     6       6   1.00
#   9 8 7 6 5 4 3 2 1 0 9 8 7 6    14      14   1.00
#   xyzzy qwerty zxcvb plughh       4      19   4.75
#   invoice 4821 due 2026 03 28     6      21   3.50
```

run: 2026-08-25 · fixture · `python3 tok.py --ratios`

Common prose runs about 1 token per word; the four made-up words run 4.75 tokens each, because the tokenizer has no merges for them and falls back to characters. Tokens-per-word is not a constant you can multiply by — it depends on whether the tokenizer has seen the words — which is why the word estimate is not off by a fixed factor you could correct, but off by an amount that depends on the exact text.

<svg viewBox="0 0 700 160" role="img" aria-label="Words versus tokens for four snippets. Common prose is 7 words and 8 tokens, nearly equal. A line of digits is 14 words and 14 tokens. Four rare words are 4 words but 19 tokens. A mixed number line is 6 words but 21 tokens.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">words (light) vs tokens (dark) — the gap opens on rare words</text>
    <g>
      <text x="20" y="45" fill="var(--ink)">prose</text>
      <rect x="120" y="36" width="70" height="10" fill="var(--s1)" opacity="0.4"></rect><rect x="120" y="48" width="80" height="10" fill="var(--s1)"></rect><text x="210" y="57" fill="var(--muted)">7w / 8t</text>
      <text x="20" y="85" fill="var(--ink)">digits</text>
      <rect x="120" y="76" width="140" height="10" fill="var(--s1)" opacity="0.4"></rect><rect x="120" y="88" width="140" height="10" fill="var(--s1)"></rect><text x="270" y="97" fill="var(--muted)">14w / 14t</text>
      <text x="20" y="125" fill="var(--ink)">rare words</text>
      <rect x="120" y="116" width="40" height="10" fill="var(--s2)" opacity="0.4"></rect><rect x="120" y="128" width="190" height="10" fill="var(--s2)"></rect><text x="320" y="137" fill="var(--s2)">4w / 19t</text>
    </g>
  </g>
</svg>
^ Words and tokens track each other for prose and digits, then diverge hard for rare words: four words, nineteen tokens. The light bar is what a word-count budget sees; the dark bar is what the model charges you.

**Length, to a model, is counted in tokens, and tokens are only knowable by encoding — a word count is a guess that is most wrong on the rare, dense text most likely to overflow.**

The self-test pins the failure to the mechanism:

```
# $ python3 tok.py --check
#   every sample fits by word count = True
#   samples that truly overflow the 15-token budget = 2 ['xyzzy qwerty zxc', 'invoice 4821 due']
#   tokens/word swings across text = True (4.75 rare vs 1.00 common)
#   the rare word 'qwerty' is 4 tokens, not 1 = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 tok.py --check`

## Build

The pipeline in one paragraph: train a BPE by merging the most frequent adjacent pairs to a target vocabulary; encode text by applying the merges in order; and whenever you need a length — for a budget, a truncation, a cost estimate — encode and count tokens, never multiply a word or character count by a fixed ratio. Never let a word count gate a token budget.

We opened on the lying budget. The fix is to read the token column, not the word column:

```
# modules/below-the-prompt/code/tokens-basic-01/ — COMPLETE, run from that directory
$ python3 tok.py --budget
  xyzzy qwerty zxcvb plughh       4   fits          19   OVERFLOW
```

Now tokenize your own text. Train the BPE on a corpus in your domain and encode a handful of real strings — a name, an ID, a code snippet, a sentence of prose — and compare the word count to the token count. Your number to beat is the **worst tokens-per-word** in your samples: the string where the word estimate is most wrong is the one that will silently overflow a budget. Feed a budget the shortest-looking rare-word string you can find and confirm it overflows in tokens while passing by word count. Bring back the words-versus-tokens table and the worst ratio. Good luck.

## Definition of done

- [ ] A BPE trained on your own corpus by merging the most frequent pairs to a target vocabulary
- [ ] An encoder that applies the merges in order to produce tokens
- [ ] A words-versus-tokens comparison over varied strings, including at least one rare-word or number-heavy sample
- [ ] A token budget checked with the word estimate and with the true encoded count
- [ ] `python3 tok.py --check` printing SELF-TEST PASS: word count says all fit, some truly overflow, tokens-per-word swings, a rare word explodes
- [ ] The worst tokens-per-word ratio recorded, and the sample that produced it
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A four-word snippet was 19 tokens and a fourteen-word snippet was 14. Explain why the shorter one costs more, in terms of what the tokenizer learned.
2. Describe one BPE merge step in a sentence, and why the first merges a corpus learns are pairs like "th" and "the".
3. Why is tokens-per-word not a fixed constant you can multiply a word count by to get the token count?
4. You have a 15-token window and a snippet of four rare words. What does a word-count budget say, what is the truth, and which one governs whether the model sees the whole snippet?
5. Your own run produced a worst tokens-per-word ratio. What string caused it, and how many tokens was it versus its word count?

## External resources

- Karpathy, *Let's build the GPT Tokenizer* — https://www.youtube.com/watch?v=zduSFxRajkE — my summary: builds BPE from scratch and shows the downstream oddities tokenization causes (spelling, arithmetic, non-English); watch it for the full byte-level version this module simplifies, and for why "why can't the model count letters" is a tokenizer question.
- Sennrich, Haddow & Birch, *Neural Machine Translation of Rare Words with Subword Units* (2016) — https://arxiv.org/abs/1508.07909 — my summary: the paper that introduced BPE to NLP, and the argument for subwords over words precisely to handle the rare-word explosion this module measures.
- OpenAI, *tiktoken* — https://github.com/openai/tiktoken — my summary: the production tokenizer library; read it to encode real strings against a real vocabulary and confirm the tokens-per-word swing at scale, and to replace this module's toy budget estimate with an exact count in your own tools.
