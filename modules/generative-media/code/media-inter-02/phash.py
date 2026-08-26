#!/usr/bin/env python3
"""Dedup a library of generated images -- and why a cryptographic hash finds nothing.

You generate images in bulk and end up with near-duplicates: the same picture at a
slightly different brightness, one re-encode, a one-pixel edit. To dedup them, the
reflex is to hash each file and group by hash. That reflex fails completely, and the
failure is instructive: a cryptographic hash is designed so that flipping a single
bit of input scrambles the entire output. That is exactly the property you want for
integrity and exactly the property you do NOT want for similarity -- it maps "almost
identical" and "totally different" to the same thing: two unequal hashes, no signal
about how far apart the inputs are.

A perceptual hash is the opposite construction. dHash records, for each adjacent
pixel pair, whether it goes up or down in brightness -- the image's gradient
structure. Uniform brightness shifts leave every comparison unchanged, so a
brightened copy hashes IDENTICALLY; a small local edit flips a bit or two; a
different picture flips many. Now the Hamming distance between two hashes is a real
similarity measure, and a threshold clusters the near-duplicates a cryptographic
hash could never see.

  --hashes      each image's exact (content) hash and dHash bits
  --distances   pairwise Hamming distance between dHashes; near-dups vs distinct
  --dedup       group by exact hash vs by perceptual threshold; count the clusters
  --check       exact hashing finds no near-dups; perceptual does; the threshold separates

Stdlib only. Deterministic.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "images.json"
THRESHOLD = 6  # dHash Hamming distance at or below which two images are "the same"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the hashes

def exact_hash(img):
    """A cryptographic content hash: any pixel change -> a totally different digest."""
    flat = ",".join(str(v) for row in img for v in row)
    return hashlib.sha256(flat.encode("utf-8")).hexdigest()[:12]


def dhash(img):
    """Perceptual hash: 1 where a pixel is brighter than its right neighbour, else 0."""
    bits = []
    for row in img:
        for j in range(len(row) - 1):
            bits.append(1 if row[j] < row[j + 1] else 0)
    return bits


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


# ------------------------------------------------------------- deduplication

def dedup_exact(images):
    """Group images whose exact content hash is identical (byte-for-byte duplicates)."""
    groups = {}
    for name, img in images.items():
        groups.setdefault(exact_hash(img), []).append(name)
    return list(groups.values())


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


# ----------------------------------------------------------------- printing

def hashes_view(data):
    images = data["images"]
    print("HASHES — cryptographic digest vs perceptual dHash")
    print("-" * 66)
    for name, img in images.items():
        bits = "".join(str(b) for b in dhash(img))
        print("  %-12s sha=%s  dhash=%s" % (name, exact_hash(img), bits))
    print("-" * 66)
    print("  brightening every pixel changes the sha completely but the dhash not at all.")


def distances_view(data):
    images = data["images"]
    names = list(images)
    hashes = {n: dhash(images[n]) for n in names}
    print("DISTANCES — pairwise dHash Hamming distance (0 = perceptually identical)")
    print("-" * 66)
    print("       " + "".join("%-12s" % n[:11] for n in names))
    for a in names:
        cells = "".join("%-12d" % hamming(hashes[a], hashes[b]) for b in names)
        print("  %-5s%s" % (a[:5], cells))
    print("-" * 66)
    print("  near-dups sit at small distances; genuinely different images sit far apart.")


def dedup_view(data):
    images = data["images"]
    ex = dedup_exact(images)
    pc = dedup_perceptual(images)
    print("DEDUP — clusters by exact hash vs by perceptual threshold (<= %d)" % THRESHOLD)
    print("-" * 66)
    print("  exact-hash clusters      = %d  %s" % (len(ex), sorted(sorted(g) for g in ex)))
    print("  perceptual clusters      = %d  %s" % (len(pc), sorted(sorted(g) for g in pc)))
    print("-" * 66)
    print("  exact hashing sees %d distinct files (no near-dups merged); perceptual" % len(ex))
    print("  merges the brightened and tweaked copies, leaving %d real images." % len(pc))


def check(data):
    print("SELF-TEST — exact hashing misses near-dups; perceptual finds them; threshold separates")
    print("-" * 66)
    images = data["images"]

    ex = dedup_exact(images)
    pc = dedup_perceptual(images)
    exact_misses = len(ex) == len(images)
    print("  exact hash merges nothing (every file distinct) = %s (%d clusters)" % (exact_misses, len(ex)))

    perceptual_merges = len(pc) < len(ex)
    print("  perceptual dedup merges near-dups = %s (%d clusters < %d)" % (perceptual_merges, len(pc), len(ex)))

    # The documented near-dup pairs must land in the same perceptual cluster.
    def same_cluster(clusters, a, b):
        return any(a in g and b in g for g in clusters)
    pairs_ok = all(same_cluster(pc, a, b) for a, b in data["near_dup_pairs"])
    print("  every known near-dup pair is clustered together = %s" % pairs_ok)

    # Brightness invariance: a uniform shift gives an identical dHash (distance 0).
    d_bright = hamming(dhash(images["imgA"]), dhash(images["imgA_bright"]))
    bright_invariant = d_bright == 0
    print("  uniform brightness shift -> identical dHash = %s (distance %d)" % (bright_invariant, d_bright))

    # Distinct images stay far apart -> the threshold actually discriminates.
    d_distinct = hamming(dhash(images["imgA"]), dhash(images["imgB"]))
    separates = d_distinct > THRESHOLD
    print("  a genuinely different image stays above threshold = %s (distance %d > %d)"
          % (separates, d_distinct, THRESHOLD))

    ok = exact_misses and perceptual_merges and pairs_ok and bright_invariant and separates
    print("-" * 66)
    print("SELF-TEST %s  exact_misses=%s  perceptual_merges=%s  pairs_ok=%s  bright_invariant=%s  separates=%s"
          % ("PASS" if ok else "FAIL", exact_misses, perceptual_merges, pairs_ok, bright_invariant, separates))
    return ok


def main():
    p = argparse.ArgumentParser(description="Perceptual hashing for near-duplicate image dedup.")
    p.add_argument("--hashes", action="store_true")
    p.add_argument("--distances", action="store_true")
    p.add_argument("--dedup", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("images=%d  file=%s  (images are a fixture)" % (len(data["images"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.hashes:
        hashes_view(data)
    elif args.distances:
        distances_view(data)
    elif args.dedup:
        dedup_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
