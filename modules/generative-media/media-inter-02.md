---
id: media-inter-02
title: Dedup generated images by what they look like, not by their bytes
topic: generative-media
level: intermediate
status: ready
time: 8-10h
summary: A cryptographic hash is built to scramble its entire output when one input bit flips, so it maps a brightened copy of an image and a totally different image to the same verdict — two unequal digests, no notion of near — and deduping a five-image library by SHA finds five distinct files and zero duplicates. A perceptual dHash records the gradient direction between adjacent pixels instead, so a uniform brightness shift hashes identically (Hamming distance 0), a one-pixel edit flips a single bit (distance 1), and a different picture flips most (distance 64); a distance threshold then collapses the library to three real images. The lesson is that integrity hashing and similarity hashing are opposite constructions, and using the integrity tool for the similarity job silently finds nothing.
eli5: If you want to check a document was not tampered with, you want a seal that shatters completely if even one letter changes — that is a cryptographic hash. But if you want to find two photos that look the same, that seal is useless: a tiny brightness change shatters it just as much as a totally different photo. For looking-alike you need a different fingerprint that captures the shape of the picture, so small changes barely move it and big changes move it a lot.
---

## Why this module

Generate images in bulk and you accumulate near-duplicates: the same picture at a slightly different exposure, a re-encode that shifted a few pixels, a one-pixel touch-up, the same prompt at two adjacent seeds. To clean the library you want to group the ones that look the same. The reflex — the one that works for every other dedup task — is to hash each file and group by hash. This module builds that reflex, watches it find absolutely nothing, and then builds the tool that actually works, because the reason it fails is a genuinely useful thing to understand about what a hash is for.

A cryptographic hash is engineered around one property: flip a single input bit and the entire output changes unpredictably. That avalanche is exactly what you want for integrity — any tampering is loud — and exactly what you must not have for similarity. It maps "almost identical" and "completely different" to the same outcome: two hashes that are not equal, carrying no information about how far apart the inputs were. So a SHA-based dedup can only find byte-for-byte duplicates, and generated near-duplicates are never byte-for-byte. A perceptual hash inverts the construction: it throws away the exact bytes and keeps a coarse structural summary, so small perceptual changes make small hash changes, and the distance between two hashes becomes a real measure of how alike two images look.

You need no prior module, only the idea of a grayscale image as a grid of numbers. Everything runs offline against an image fixture — five tiny 8×9 images, two of them near-duplicates of a third — stdlib Python 3, `$0.00`. The instinct to unlearn is that a hash tells you whether two things are similar. A cryptographic hash tells you only whether they are identical; similarity needs a hash built for the opposite job.

Here is the reflex, finding nothing:

```
# modules/generative-media/code/media-inter-02/ — COMPLETE, run from that directory
$ python3 phash.py --dedup

DEDUP — clusters by exact hash vs by perceptual threshold (<= 6)
------------------------------------------------------------------
  exact-hash clusters      = 5  [['imgA'], ['imgA_bright'], ['imgA_tweak'], ['imgB'], ['imgC']]
  perceptual clusters      = 3  [['imgA', 'imgA_bright', 'imgA_tweak'], ['imgB'], ['imgC']]
```

run: 2026-08-26 · deterministic; images are a fixture · 5 images · `python3 phash.py --dedup`

Five images in; exact hashing reports five distinct files, no duplicates found, even though two of them are obvious copies of the first. Perceptual hashing collapses those three into one cluster and reports the three genuinely different images. This module is the difference between those two lines.

## Concepts

Named here so you can find them again; each is built below.

- **Cryptographic hash** — a digest where one input bit flips the whole output; catches tampering, blind to similarity.
- **Avalanche effect** — the property that makes a cryptographic hash useless as a similarity measure.
- **Perceptual hash (dHash)** — a hash of image structure (adjacent-pixel gradients); small visual change, small hash change.
- **Hamming distance** — the number of differing bits between two hashes; the similarity measure.
- **Brightness invariance** — dHash is unchanged by a uniform shift, because it compares neighbours, not absolute values.
- **Threshold clustering** — grouping images whose hash distance is small enough to call the same.

## Worked example

Source: the perceptual-hashing pattern used for image dedup and content matching (average-hash and dHash, as popularized by the pHash library and content-ID systems), distilled to its arithmetic; the pixel grids here stand in for real generated images so the distances are exact and checkable.

Script and fixture: `modules/generative-media/code/media-inter-02/` — `phash.py`, and `images.json`, five 8×9 grayscale images: a base gradient `imgA`, a uniformly brightened copy `imgA_bright`, a one-pixel edit `imgA_tweak`, and two different pictures `imgB`, `imgC`. Every command runs from there.

### The reflex: a cryptographic hash

Hash the pixels, compare digests. It is the obvious move and it is exactly wrong for this.

```
# phash.py:45-48 — COMPLETE (a cryptographic content hash)
def exact_hash(img):
    """A cryptographic content hash: any pixel change -> a totally different digest."""
    flat = ",".join(str(v) for row in img for v in row)
    return hashlib.sha256(flat.encode("utf-8")).hexdigest()[:12]
```

Look at what it produces for the base image and its brightened twin — two pictures a human cannot tell apart:

```
# $ python3 phash.py --hashes
#   imgA         sha=a5bd664654b3  dhash=11111111...11111111
#   imgA_bright  sha=05a2af57e915  dhash=11111111...11111111
#   imgA_tweak   sha=014675211a38  dhash=11111111...011111...
#   imgB         sha=47ad792c718b  dhash=00000000...00000000
```

run: 2026-08-26 · deterministic · `python3 phash.py --hashes`

<svg viewBox="0 0 700 180" role="img" aria-label="Two panels. Left, cryptographic hash: imgA and imgA_bright feed in; a small +10 change produces two totally unrelated digests, drawn as scrambled and unrelated. Right, perceptual hash: the same two images produce identical bit strings. Below, imgB produces a hash far from imgA under the perceptual scheme but, under SHA, is no more different than imgA_bright was.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the same +10 brightness change, through two kinds of hash</text>
    <text x="40" y="44" fill="var(--ink)">cryptographic (SHA)</text>
    <rect x="40" y="54" width="120" height="22" rx="3" fill="var(--panel)" stroke="var(--line)"></rect><text x="100" y="69" text-anchor="middle" fill="var(--ink)" font-size="8">imgA -> a5bd66</text>
    <rect x="40" y="82" width="120" height="22" rx="3" fill="var(--panel)" stroke="var(--line)"></rect><text x="100" y="97" text-anchor="middle" fill="var(--s2)" font-size="8">+10 -> 05a2af</text>
    <text x="40" y="128" fill="var(--s2)" font-size="8">unrelated digests: distance</text><text x="40" y="140" fill="var(--s2)" font-size="8">"not equal", same as imgB</text>
    <text x="400" y="44" fill="var(--ink)">perceptual (dHash)</text>
    <rect x="400" y="54" width="150" height="22" rx="3" fill="var(--panel)" stroke="var(--line)"></rect><text x="475" y="69" text-anchor="middle" fill="var(--ink)" font-size="8">imgA -> 11111111...</text>
    <rect x="400" y="82" width="150" height="22" rx="3" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="475" y="97" text-anchor="middle" fill="var(--acc-ink)" font-size="8">+10 -> 11111111...</text>
    <text x="400" y="128" fill="var(--s1)" font-size="8">identical hashes: distance 0</text><text x="400" y="140" fill="var(--s1)" font-size="8">the shift left the gradient unchanged</text>
  </g>
</svg>
^ A uniform brightness shift scrambles the SHA completely — avalanche — but leaves the dHash untouched, because dHash records only which neighbour is brighter and the shift changes no such comparison. The construction that makes SHA tamper-evident is the same one that blinds it to similarity.

`imgA` and `imgA_bright` have completely unrelated SHA digests — `a5bd66…` versus `05a2af…` — because every pixel changed by 10, and the avalanche effect turned that uniform shift into total digest chaos. The hash cannot say these are close; it can only say they are not equal, which it also says about `imgA` versus the utterly different `imgB`. To a cryptographic hash, "brightened by 10" and "a different picture" are the same answer.

### The right tool: a perceptual hash

dHash ignores absolute pixel values and records only whether each pixel is brighter or darker than its right neighbour — the local gradient direction.

```
# phash.py:51-57 — COMPLETE (the perceptual hash: gradient direction per pixel pair)
def dhash(img):
    """Perceptual hash: 1 where a pixel is brighter than its right neighbour, else 0."""
    bits = []
    for row in img:
        for j in range(len(row) - 1):
            bits.append(1 if row[j] < row[j + 1] else 0)
    return bits
```

The magic is in what the comparison discards. Add 10 to every pixel and every "is my neighbour brighter" answer is unchanged — the gradient structure is identical — so `imgA` and `imgA_bright` hash to the exact same bits. That is why their dHashes above are identical (`11111111…`) while their SHAs are unrelated. The perceptual hash kept the thing that matters for "does it look the same" and threw away the thing that does not.

### Measuring similarity: Hamming distance

Now that similar images have similar hashes, the distance between hashes is a similarity score.

```
# phash.py:60-61 — COMPLETE (bits that differ = perceptual distance)
def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)
```

The pairwise table shows a real gradient of similarity, which a cryptographic hash could never produce:

```
# $ python3 phash.py --distances
#          imgA  imgA_bright  imgA_tweak  imgB  imgC
#   imgA     0        0            1        64    12
#   imgB    64       64           63         0    52
#   imgC    12       12           13        52     0
```

run: 2026-08-26 · deterministic · `python3 phash.py --distances`

Read the top row. `imgA` to `imgA_bright` is 0 — perceptually identical, exactly as it should be for a brightness shift. `imgA` to `imgA_tweak` is 1 — a single flipped bit for a single-pixel edit. `imgA` to `imgB` is 64 — the maximum, because `imgB` is the reversed gradient, every comparison inverted. `imgA` to `imgC` is 12. That ordering — 0, 1, 12, 64 — is a similarity measure, the exact thing the SHA digests could not give.

<svg viewBox="0 0 700 170" role="img" aria-label="A one-dimensional axis of perceptual distance from imgA, from 0 on the left to 64 on the right. imgA_bright sits at 0, imgA_tweak at 1, imgC at 12, imgB at 64. A dashed threshold line at 6 divides 'same image' on the left from 'different' on the right; only imgA_bright and imgA_tweak fall left of it.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">dHash Hamming distance from imgA — a real similarity axis</text>
    <line x1="50" y1="90" x2="650" y2="90" stroke="var(--grid)"></line>
    <g fill="var(--muted)" text-anchor="middle"><text x="50" y="108">0</text><text x="650" y="108">64</text></g>
    <line x1="106" y1="60" x2="106" y2="120" stroke="var(--acc)" stroke-dasharray="3 3"></line><text x="112" y="66" fill="var(--acc-ink)" font-size="8">threshold 6</text>
    <circle cx="50" cy="90" r="4" fill="var(--s1)"></circle><text x="50" y="78" text-anchor="middle" fill="var(--s1)" font-size="8">bright (0)</text>
    <circle cx="59" cy="90" r="4" fill="var(--s1)"></circle><text x="66" y="134" fill="var(--s1)" font-size="8">tweak (1)</text>
    <circle cx="162" cy="90" r="4" fill="var(--s2)"></circle><text x="162" y="78" text-anchor="middle" fill="var(--s2)" font-size="8">imgC (12)</text>
    <circle cx="650" cy="90" r="4" fill="var(--s2)"></circle><text x="650" y="78" text-anchor="middle" fill="var(--s2)" font-size="8">imgB (64)</text>
    <text x="70" y="150" fill="var(--muted)" font-size="8">left of the line: the same image, brightened or tweaked</text>
  </g>
</svg>
^ The near-duplicates sit at distance 0 and 1, the different images at 12 and 64, and a threshold of 6 cleanly separates them. A cryptographic hash would place all four at the same "not equal" — no axis, no threshold, no clusters.

### Deduping: group by distance, not equality

With a real distance, dedup is a threshold: images within a few bits of each other are the same picture.

```
# phash.py:74-93 — COMPLETE (single-link clustering by perceptual distance)
def dedup_perceptual(images, threshold=THRESHOLD):
    """Group images whose dHashes are within `threshold` Hamming distance (single-link)."""
    names = list(images)
    hashes = {n: dhash(images[n]) for n in names}
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(names)):
        for k in range(i + 1, len(names)):
            if hamming(hashes[names[i]], hashes[names[k]]) <= threshold:
                parent[find(names[i])] = find(names[k])
    clusters = {}
    for n in names:
        clusters.setdefault(find(n), []).append(n)
    return list(clusters.values())
```

<svg viewBox="0 0 700 180" role="img" aria-label="Two rows of the same five images. Top row, exact-hash dedup: five separate single-item boxes, no merging. Bottom row, perceptual dedup: imgA, imgA_bright, imgA_tweak enclosed in one box labelled one image; imgB and imgC in their own boxes. Five clusters become three.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">same five images, two dedup schemes</text>
    <text x="20" y="46" fill="var(--ink)">exact hash</text>
    <g fill="var(--panel)" stroke="var(--line)"><rect x="120" y="34" width="90" height="24" rx="3"></rect><rect x="216" y="34" width="90" height="24" rx="3"></rect><rect x="312" y="34" width="90" height="24" rx="3"></rect><rect x="408" y="34" width="70" height="24" rx="3"></rect><rect x="484" y="34" width="70" height="24" rx="3"></rect></g>
    <g fill="var(--ink)" font-size="8" text-anchor="middle"><text x="165" y="50">imgA</text><text x="261" y="50">imgA_bright</text><text x="357" y="50">imgA_tweak</text><text x="443" y="50">imgB</text><text x="519" y="50">imgC</text></g>
    <text x="560" y="50" fill="var(--s2)" font-size="8">5 clusters</text>
    <text x="20" y="116" fill="var(--ink)">perceptual</text>
    <rect x="120" y="104" width="282" height="24" rx="3" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <g fill="var(--acc-ink)" font-size="8" text-anchor="middle"><text x="165" y="120">imgA</text><text x="261" y="120">imgA_bright</text><text x="357" y="120">imgA_tweak</text></g>
    <text x="261" y="142" text-anchor="middle" fill="var(--acc-ink)" font-size="8">one image</text>
    <g fill="var(--panel)" stroke="var(--line)"><rect x="408" y="104" width="70" height="24" rx="3"></rect><rect x="484" y="104" width="70" height="24" rx="3"></rect></g>
    <g fill="var(--ink)" font-size="8" text-anchor="middle"><text x="443" y="120">imgB</text><text x="519" y="120">imgC</text></g>
    <text x="560" y="120" fill="var(--s1)" font-size="8">3 clusters</text>
  </g>
</svg>
^ Exact hashing leaves all five apart; perceptual dedup encloses the base, its brightened copy, and its one-pixel edit in a single cluster, leaving three real images. The library did not change — the measure of sameness did.

This collapses the five images to three: `{imgA, imgA_bright, imgA_tweak}` as one picture, plus `imgB` and `imgC`. The cold open's exact-hash run left all five separate. Same library, same goal, and the only difference is whether the hash underneath measures identity or similarity.

**A cryptographic hash answers "are these the same bytes"; near-duplicate dedup needs "do these look the same", and only a perceptual hash — whose distance grows with visual difference — can answer it, because avalanche makes the cryptographic distance a coin with no in-between.**

### The self-test

The `--check` mode asserts both failures and both fixes: exact hashing merges nothing, perceptual dedup merges the near-dups, the brightness shift is exactly invariant, and a real difference stays above threshold.

```
# $ python3 phash.py --check
#   exact hash merges nothing (every file distinct) = True (5 clusters)
#   perceptual dedup merges near-dups = True (3 clusters < 5)
#   every known near-dup pair is clustered together = True
#   uniform brightness shift -> identical dHash = True (distance 0)
#   a genuinely different image stays above threshold = True (distance 64 > 6)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 phash.py --check`

The `bright_invariant` line is the correctness anchor: a uniform brightness shift must give distance exactly 0, and it is the property the whole approach rests on — if a refactor broke it (say, by comparing absolute values instead of neighbours), that assertion would fail first. The `separates` line guards the other side: the threshold must not be so loose that it merges genuinely different images, so a distinct picture is required to stay above it.

### The running tally

| pair | SHA verdict | dHash distance | dedup outcome |
|---|---|---|---|
| imgA vs imgA_bright | different digests | 0 | same image (perceptual) |
| imgA vs imgA_tweak | different digests | 1 | same image (perceptual) |
| imgA vs imgB | different digests | 64 | distinct |
| imgA vs imgC | different digests | 12 | distinct |

The SHA column is constant — "different digests" for every pair, the near-duplicates and the genuinely-different alike — which is precisely why it is useless here: a column with no variation carries no signal. The dHash column varies from 0 to 64 and that variation is the whole product. When your tool gives the same answer to "identical" and "unrelated", you have the wrong tool, not a hard problem.

### What we did not settle

dHash is the simplest perceptual hash and has real limits. It is not rotation- or crop-invariant — rotate the image 90 degrees and the gradient structure changes completely, so a rotated duplicate reads as different; robust matching against crops and rotations needs feature-based methods (SIFT-style keypoints) or learned embeddings. The threshold is a tuning knob with the usual tradeoff: too tight misses real duplicates, too loose merges distinct images, and the right value depends on your library and is set on a labelled sample, exactly like the retrieval thresholds elsewhere in the hub. And single-link clustering can chain — A near B, B near C, so A and C merge even if far apart — which is fine at this scale but wants a tighter linkage on a big library. The construction here is the floor: a hash whose distance means something.

## Build

The practice in one paragraph: never dedup by cryptographic hash unless you truly mean byte-identical; for "looks the same", compute a perceptual hash (dHash or average-hash), measure Hamming distance, set a threshold on a labelled sample, and cluster within it; and remember which hash answers which question — a cryptographic hash for integrity and tamper-evidence, a perceptual hash for similarity — because they are opposite constructions and swapping them fails silently, returning "all distinct" instead of an error. Keep the cryptographic hash too; it is the right tool for provenance, just not for similarity.

We opened on the two dedup lines. The number that proves the perceptual tool works is the cluster count:

```
# modules/generative-media/code/media-inter-02/ — COMPLETE, run from that directory
$ python3 phash.py --dedup
  exact-hash clusters      = 5
  perceptual clusters      = 3
```

Now do it to your own library. Take a handful of generated images, make a couple of near-duplicates (brighten one, edit a pixel, re-encode one), and dedup them both ways. Your number to beat is not the perceptual cluster count alone; it is **the gap between exact-hash clusters and perceptual clusters** — how many real duplicates the cryptographic hash missed — plus the distance your brightness-shifted copy lands at, which should be near 0. Then sweep the threshold and watch clusters merge. Bring back both cluster counts and the brightness distance. Good luck.

## Definition of done

- [ ] A cryptographic hash and a perceptual dHash computed for each image
- [ ] Pairwise Hamming distance between dHashes, showing a real similarity gradient
- [ ] Dedup by exact hash and by perceptual threshold, with cluster counts compared
- [ ] Confirmation that a uniform brightness shift gives perceptual distance 0
- [ ] Confirmation that a genuinely different image stays above the threshold
- [ ] `python3 phash.py --check` printing SELF-TEST PASS: exact misses, perceptual merges, invariance, separation
- [ ] Your own near-duplicates deduped both ways, with the missed-duplicate gap recorded
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a cryptographic hash find zero near-duplicates, and which of its design properties is responsible?
2. Explain why dHash gives an identical hash to a uniformly brightened image. What exactly does the comparison discard?
3. What does the Hamming distance between two dHashes measure, and why can a cryptographic hash never produce an equivalent number?
4. When would you still reach for the cryptographic hash rather than the perceptual one? Name the job it is correct for.
5. Your own library was deduped both ways. How many duplicates did the exact hash miss, what distance did your brightened copy land at, and how did the cluster count move as you swept the threshold?

## External resources

- Neal Krawetz, *Looks Like It* (the dHash / perceptual-hash explainer) — http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html — my summary: the canonical walkthrough of average-hash and difference-hash and why gradient-based hashes survive brightness and scaling; read it for the intuition behind the construction this module implements.
- OpenTimestamps / any SHA-256 reference on the avalanche effect — my summary: the design goal that one input bit flips half the output bits, which is what makes a cryptographic hash tamper-evident and useless for similarity; read it for why the failure here is not a bug but the hash working as intended.
- This hub, *media-basic-01* — modules/generative-media/media-basic-01.md — my summary: the other side of hashing generated media, using a cryptographic content hash for provenance and integrity; read it for the job the cryptographic hash is correct for, the exact one this module tells you not to use for similarity.
