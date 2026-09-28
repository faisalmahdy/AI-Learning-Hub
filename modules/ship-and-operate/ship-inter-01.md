---
id: ship-inter-01
title: Compare secrets in constant time, or leak them one character at a time
topic: ship-and-operate
level: intermediate
status: ready
time: 8-10h
summary: Checking a token with == returns at the first wrong character, so a guess sharing more of the secret's prefix takes measurably longer to reject — the comparison examines 1 character for a fully-wrong guess and 4 for a right prefix. That rising count is a side channel: an attacker recovers the four-character secret by climbing it one position at a time and gets "m7k2" exactly, while a constant-time compare that always examines every character leaves the count flat at 4 and the same attack recovers only "aaaa". The fix is one loop that never short-circuits.
eli5: A cheap lock that clicks a little louder each time you get another digit right lets you feel your way to the code. A good lock gives the same feedback whether you are one digit off or all of them — so compare secrets in a way that always checks every character.
---

## Why this module

This module is the ship-and-operate track's security beat, and it takes the smallest, most counterintuitive secure-coding rule seriously: how you compare a secret matters as much as whether you compare it. The scan records the exact defect in the labs' own operator, which "compares [a token] with ==" — the natural, obvious, wrong way. Comparing a submitted token or password to the real one with `==` looks airtight: it returns True only on an exact match. The problem is not the answer; it is how long the answer takes.

`==` on a string returns the moment it finds a differing character. A guess that gets the first character right is rejected a hair slower than one that gets it wrong, because the comparison had to look at a second character before giving up. Do this in a loop and the time to reject a guess encodes how many leading characters it got right — a side channel. An attacker who can measure that time recovers the secret one position at a time: fix the first character by finding the guess that takes longest, then the second, and so on. A secret that would take astronomically long to brute-force whole falls in a linear number of guesses. The fix is a constant-time comparison that always examines every character, so the time reveals nothing.

You need no libraries beyond the standard one. To keep the whole thing deterministic and offline, this module measures the leak with a proxy — the number of characters the comparison examines before returning — which stands in for wall-clock time; a real attacker times the call, but the vulnerability and the fix are identical. `$0.00`, one sitting. The instinct to unlearn is that a comparison's only output is its result. A comparison also emits *how long it took*, and for secrets that channel is the whole vulnerability.

Here is the attack against both comparisons:

```
# modules/ship-and-operate/code/ship-inter-01/ — COMPLETE, run from that directory
$ python3 timing.py --attack

THE ATTACK — recover the secret one character at a time
------------------------------------------------------------
  against naive compare    recovered 'm7k2'  -> SECRET LEAKED
  against constant compare recovered 'aaaa'  -> held
```

run: 2026-08-25 · deterministic; comparison count stands in for time · secret_len=4, alphabet=36 · `python3 timing.py --attack`

The same attack recovers the exact secret against `==` and gets nothing but padding against the constant-time compare. This module is how the attack climbs the leak, and the one loop that flattens it.

## Concepts

Named here so you can find them again; each is built below.

- **Secret comparison** — checking a submitted token against the real one.
- **Early exit** — `==` returns at the first differing character; the source of the leak.
- **Timing side channel** — information leaked by *how long* an operation takes, not its result.
- **Comparison count** — characters examined before returning; the deterministic stand-in for time here.
- **Constant-time compare** — always examines every character, so the count is the same for every guess.
- **Character-at-a-time attack** — recover a secret one position at a time by climbing the timing signal.

## Worked example

Source: faisalmahdy/operator — the bearer-token check the scan flags for comparing with `==`, and the general secrets-hygiene lesson (`hmac.compare_digest` is the standard-library constant-time compare). The secret and alphabet are a toy fixture; never hard-code a real one.

Script and fixture: `modules/ship-and-operate/code/ship-inter-01/` — `timing.py`, and `secret.json`, a four-character secret over a 36-character alphabet. Every command runs from there.

### The frame: a lock that clicks louder as you get closer

Picture a combination lock with a flaw: each time you dial a correct digit, it clicks a little louder before rejecting the rest. You would not brute-force it; you would listen. Dial the first digit through all ten values, keep the one that clicks loudest — that is the first digit of the code. Then hold it and do the second. Ten digits times a few values each, and the lock is open, because it told you how close you were at every step. A secure lock gives identical feedback for "first digit right, rest wrong" and "everything wrong" — no gradient to climb.

`==` on a secret is the clicky lock. The "click" is the extra character it compares before rejecting a guess with a longer correct prefix. Constant-time comparison is the secure lock: it examines every character every time, so a guess that is one character off and a guess that is entirely wrong take exactly the same work, and there is nothing for the attacker to listen to. The whole module is replacing the clicky compare with the quiet one.

### The leak, made visible

The naive compare stops at the first mismatch and reports how many characters it examined.

```
# timing.py:38-48 — COMPLETE (== -style early exit; the count leaks the prefix)
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
```

Watch the count climb as a guess gets more of the prefix right:

```
# $ python3 timing.py --leak
#   correct prefix   guess                naive count   constant count
#   0               'aaaa'               1             4
#   1               'maaa'               2             4
#   2               'm7aa'               3             4
#   3               'm7ka'               4             4
#   4               'm7k2'               4             4
```

run: 2026-08-25 · fixture · `python3 timing.py --leak`

A fully-wrong guess is rejected after examining 1 character; a guess with three correct leading characters takes 4. That rising column is the side channel — each extra correct character costs the attacker one more comparison of observable time. The constant column never moves. A single guess shows the split directly:

```
# $ python3 timing.py --compare m7xx
#   naive (early exit)   compared 3 character(s)
#   constant time        compared 4 character(s)
```

run: 2026-08-25 · fixture · `python3 timing.py --compare "..."`

The guess `m7xx` shares two characters with `m7k2`, so the naive compare examines three (the two matches plus the first mismatch) and the constant compare examines all four — and it is that difference, not the True/False both agree on, that the attacker reads.

<svg viewBox="0 0 700 150" role="img" aria-label="Comparing m7xx to m7k2. Naive: match m, match 7, mismatch at position 3, stop — 3 examined. Constant: examine all four positions regardless — 4 examined.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--s2)">naive: stop at first mismatch</text>
    <g>
      <rect x="40" y="30" width="34" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="52" y="47" fill="var(--ink)">m=m</text>
      <rect x="80" y="30" width="34" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="92" y="47" fill="var(--ink)">7=7</text>
      <rect x="120" y="30" width="34" height="24" rx="3" fill="var(--s2)"></rect><text x="129" y="47" fill="var(--panel)">x≠k</text>
      <rect x="160" y="30" width="34" height="24" rx="3" fill="none" stroke="var(--muted)" stroke-dasharray="2 2"></rect><text x="172" y="47" fill="var(--muted)">-</text>
      <text x="210" y="47" fill="var(--s2)">stop: 3 examined (leaks "2 correct")</text>
    </g>
    <text x="20" y="88" fill="var(--s1)">constant: examine all four</text>
    <g>
      <rect x="40" y="100" width="34" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="52" y="117" fill="var(--ink)">m=m</text>
      <rect x="80" y="100" width="34" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="92" y="117" fill="var(--ink)">7=7</text>
      <rect x="120" y="100" width="34" height="24" rx="3" fill="var(--s2)"></rect><text x="129" y="117" fill="var(--panel)">x≠k</text>
      <rect x="160" y="100" width="34" height="24" rx="3" fill="var(--s2)"></rect><text x="172" y="117" fill="var(--panel)">x≠2</text>
      <text x="210" y="117" fill="var(--s1)">4 examined (reveals nothing)</text>
    </g>
  </g>
</svg>
^ The same mismatched guess. Naive stops at the first wrong character, so its work encodes the correct-prefix length; constant examines all four whatever it finds, so its work is the same for every guess. The leak is the early stop.

<svg viewBox="0 0 700 180" role="img" aria-label="Naive comparison count rising with correct prefix length: 1, 2, 3, 4, 4 — a staircase. Constant comparison count flat at 4 for every guess.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">characters examined vs how much of the prefix the guess gets right</text>
    <line x1="60" y1="150" x2="640" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="150" stroke="var(--grid)"></line>
    <g fill="var(--s2)">
      <rect x="90" y="120" width="40" height="30"></rect><rect x="190" y="90" width="40" height="60"></rect><rect x="290" y="60" width="40" height="90"></rect><rect x="390" y="30" width="40" height="120"></rect><rect x="490" y="30" width="40" height="120"></rect>
    </g>
    <text x="150" y="24" fill="var(--s2)">naive: staircase (the leak)</text>
    <line x1="60" y1="30" x2="530" y2="30" stroke="var(--s1)" stroke-width="2" stroke-dasharray="5 3"></line>
    <text x="360" y="44" fill="var(--s1)">constant: flat at 4 (no signal)</text>
    <g fill="var(--muted)" text-anchor="middle"><text x="110" y="165">0</text><text x="210" y="165">1</text><text x="310" y="165">2</text><text x="410" y="165">3</text><text x="510" y="165">4</text></g>
    <text x="300" y="178" fill="var(--muted)">correct prefix length -></text>
  </g>
</svg>
^ The naive count is a staircase rising with each correct leading character; the constant-time count is a flat line. The attacker climbs the staircase; against the flat line there is nothing to climb.

### The attack climbs the staircase

Recovering the secret is a loop over positions: at each position, try every character and keep the one whose guess makes the comparison run the longest.

```
# timing.py:66-81 — COMPLETE (recover one position at a time by the timing signal)
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
```

Against the naive compare the loop recovers `m7k2` exactly, in roughly length times alphabet guesses — four positions times thirty-six characters, about 144 tries, versus 36⁴ ≈ 1.7 million to brute-force the whole secret at once. The cost collapsed from exponential in the length to linear. One honest note on the final character: at the last position the count is flat (every guess examines all four), so the code breaks the tie with the equality result — which is exactly the real attack, where timing narrows the secret to its last character and a trivial brute force finishes it.

<svg viewBox="0 0 700 160" role="img" aria-label="The attack recovering the secret position by position: first a from an empty prefix, then m, then m7, then m7k, then m7k2, each step fixing one more character by the longest comparison.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">each row fixes one more character by the longest comparison</text>
    <g fill="var(--ink)">
      <text x="40" y="48">position 1:  try a..z0..9  ->  longest is 'm'   known = m___</text>
      <text x="40" y="72">position 2:  hold m, try all  ->  longest is '7'   known = m7__</text>
      <text x="40" y="96">position 3:  hold m7, try all  ->  longest is 'k'   known = m7k_</text>
      <text x="40" y="120">position 4:  hold m7k, try all  ->  match is '2'    known = m7k2</text>
    </g>
    <rect x="30" y="132" width="360" height="20" rx="5" fill="var(--panel)" stroke="var(--s2)"></rect>
    <text x="40" y="146" fill="var(--s2)" font-size="9">~144 guesses, not 1.7 million: linear, not exponential</text>
  </g>
</svg>
^ The recovery walks left to right, each position settled by the guess that makes `==` work hardest before giving up. A brute force over the whole secret is exponential in its length; the timing leak turns it linear.

### The fix: examine every character

The constant-time compare never short-circuits. It walks the whole string, accumulating any difference with a bitwise OR, and decides only at the end.

```
# timing.py:51-61 — COMPLETE (never short-circuit; same work for every guess)
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
```

Its count is 4 for every same-length guess — the flat line — so the attack has no gradient and, run against it, recovers only `aaaa`, the padding character. The self-test confirms both the break and the fix, and that the constant compare still returns the right answer:

```
# $ python3 timing.py --check
#   attack vs naive recovers the secret = True ('m7k2')
#   attack vs constant recovers the secret = False ('aaaa')
#   naive comparison count varies with the guess = True (4 distinct)
#   constant comparison count is identical across guesses = True
#   constant compare still returns the right answer = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 timing.py --check`

**A secret comparison leaks through its timing, not its result: use a constant-time compare that examines every character, because `==` rejects a close guess a little slower and that difference recovers the secret one character at a time.**

### The running tally

| comparison | count for a wrong guess | count varies? | attack result |
|---|---|---|---|
| naive (`==`, early exit) | 1–4, by prefix | yes | recovers `m7k2` |
| constant time (examine all) | always 4 | no | recovers `aaaa` |

Both comparisons return the same correct answer for any given guess; they differ only in what they leak while doing it. The naive one is not wrong — it is *indiscreet*, and for a secret, indiscretion is the vulnerability. The fix costs nothing but a few extra character comparisons on the rejects you were going to reject anyway, and it converts an attack that is linear in the secret's length back into one that is exponential.

### What we did not settle

The comparison count is a clean stand-in for time, but real timing attacks fight noise: a single measurement is drowned by scheduling and cache effects, so an attacker averages thousands of timed calls per guess, and defenders sometimes add rate limits and random delays as (weaker) mitigations on top of constant-time compares. Two more real details: `hmac.compare_digest` is the standard-library constant-time compare you should actually call — do not hand-roll it in production, since a clever compiler or interpreter can reintroduce a short-circuit; and length itself can leak, so comparisons over secrets of varying length need care that a fixed-length digest comparison sidesteps. The dial here is one comparison; the discipline is never comparing a secret with `==` anywhere in the system.

## Build

The pipeline in one paragraph: never compare a secret, token, or MAC with `==` or `!=`; use a constant-time comparison (`hmac.compare_digest`) that examines every byte regardless of where the first difference is; and, where you can, compare fixed-length digests of the secrets rather than the raw values so length cannot leak either. Confirm the fix by mounting the character-at-a-time attack against both and checking it breaks only the naive one.

We opened on the attack. The compare that defeats it:

```
# modules/ship-and-operate/code/ship-inter-01/ — COMPLETE, run from that directory
$ python3 timing.py --attack
  against constant compare recovered 'aaaa'  -> held
```

Now audit your own secret checks. Find every place a token, password, or signature is compared, and replace `==` with a constant-time compare. Your check is the attack: run the character-at-a-time recovery against your comparison and confirm it fails. Build the naive version too and confirm the same attack recovers the secret, so the fix is measured, not assumed. Bring back the two attack results — secret leaked against naive, held against constant. Good luck.

## Definition of done

- [ ] A naive `==`-style secret comparison and a constant-time one that examines every character
- [ ] A deterministic leak signal (comparison count here; real timing in production) shown to vary for naive and be flat for constant
- [ ] A character-at-a-time recovery attack driven by that signal
- [ ] The attack recovering the secret against the naive compare and failing against the constant one
- [ ] Your own audit of where secrets are compared, with `==` replaced by a constant-time compare
- [ ] `python3 timing.py --check` printing SELF-TEST PASS: naive leaks, constant holds, count varies vs flat, answer still correct
- [ ] The two attack results recorded, and the constant-time compare used in your real code
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. `==` returns the correct True/False for a secret comparison. Explain what it leaks anyway and through what channel.
2. Walk through how an attacker recovers a four-character secret in about 144 guesses instead of 1.7 million, using the timing signal.
3. Why does the constant-time compare examine every character even after it has found a difference?
4. The demo's attack needed the equality result to get the last character. Explain why timing alone stops one character short, and why that does not save the secret.
5. Your own attack ran against both comparisons. What did it recover against each, and where in your code did you replace `==`?

## External resources

- Python `hmac.compare_digest` — https://docs.python.org/3/library/hmac.html#hmac.compare_digest — my summary: the standard-library constant-time comparison you should call instead of `==` for any secret or MAC; read it for the exact function and why the docs warn against `==`.
- faisalmahdy/operator — the token check the scan flags — my summary: the real `==` secret comparison this module fixes, alongside the committed-token and key-audit issues; read it for how a timing-safe compare fits into a broader secrets-hygiene pass (rotation, scanning, audit).
- Coda Hale, *A Lesson In Timing Attacks* — https://codahale.com/a-lesson-in-timing-attacks/ — my summary: the classic write-up of the string-comparison timing attack with real measurements; read it for how the noisy wall-clock version is made to work, the reality behind this module's clean comparison-count proxy.
