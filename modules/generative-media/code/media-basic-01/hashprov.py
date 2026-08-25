#!/usr/bin/env python3
"""Provenance needs a content hash, not a made-up id -- or a swapped asset verifies clean.

A generated-media pipeline records a provenance id for every asset so you can later
prove the delivered file is the one that was produced. If that id is derived from
metadata -- the filename, a counter, a timestamp -- it says nothing about the
bytes, so a tampered or swapped image whose name is unchanged verifies as genuine,
and two different images with the same name collide to one id. A content hash
(SHA-256 of the actual bytes) is the fix: it changes with any edit and is unique
per content. This builds both and measures which one catches a swap.

  --manifest      each asset's fake (name-based) id and its real (content) hash
  --verify        deliver assets with one swapped; which id scheme catches it
  --collision     two different assets with the same name -- fake ids collide
  --check         the fake id misses the swap and collides; the content hash does neither

Stdlib only (hashlib). No network. Asset 'bytes' are short strings standing in for
image/video bytes; the provenance logic is identical. Deterministic. A fixture.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets.json"


def load():
    data = json.loads(ASSETS.read_text(encoding="utf-8"))
    return data["produced"], data["delivered"], data["collision"]


# ------------------------------------------------------------- the two id schemes

def fake_id(asset):
    """THE BUG: an id derived from the name only. Blind to the bytes -- rename-stable
    but also swap-blind, and it collides whenever two assets share a name."""
    return "id-" + hashlib.sha256(asset["name"].encode()).hexdigest()[:8]


def content_hash(asset):
    """The fix: SHA-256 of the actual bytes. Changes with any edit; unique per content."""
    return hashlib.sha256(asset["bytes"].encode()).hexdigest()[:12]


def build_manifest(assets, id_fn):
    """Record each asset's id at production time -- the provenance record."""
    return {a["name"]: id_fn(a) for a in assets}


# ------------------------------------------------------------------- verification

def verify(delivered, manifest, id_fn):
    """Recompute each delivered asset's id and compare to the manifest. A mismatch
    means the bytes changed since production; absence of a mismatch means 'genuine'."""
    results = []
    for a in delivered:
        recomputed = id_fn(a)
        recorded = manifest.get(a["name"])
        results.append((a["name"], recorded == recomputed))
    return results


# ------------------------------------------------------------------- printing

def manifest_view(produced):
    print("MANIFEST — provenance id recorded at production, two ways")
    print("-" * 66)
    print("  asset          fake id (name)   content hash (bytes)")
    for a in produced:
        print("  %-13s  %-15s  %s" % (a["name"], fake_id(a), content_hash(a)))
    print("-" * 66)
    print("  the fake id is a function of the name; the content hash of the bytes.")


def verify_view(produced, delivered):
    print("VERIFY — one delivered asset was swapped (bytes changed, name kept)")
    print("-" * 66)
    for label, id_fn in (("fake id (name)", fake_id), ("content hash", content_hash)):
        man = build_manifest(produced, id_fn)
        res = verify(delivered, man, id_fn)
        bad = [n for n, ok in res if not ok]
        print("  %-16s verifies clean: %s   flagged: %s"
              % (label, all(ok for _, ok in res), bad or "none"))
    print("-" * 66)
    print("  the fake id verifies the swapped asset as genuine; the content hash")
    print("  recomputes from the new bytes and catches the mismatch.")


def collision_view(collision):
    print("COLLISION — two DIFFERENT assets that share a name")
    print("-" * 66)
    a, b = collision
    print("  %s (bytes=%r) fake=%s content=%s" % (a["name"], a["bytes"], fake_id(a), content_hash(a)))
    print("  %s (bytes=%r) fake=%s content=%s" % (b["name"], b["bytes"], fake_id(b), content_hash(b)))
    print("-" * 66)
    print("  same fake id (name is identical) -> the manifest cannot tell them apart;")
    print("  different content hashes -> the bytes distinguish them.")


def check(produced, delivered, collision):
    print("SELF-TEST — the fake id misses the swap and collides; the hash does neither")
    print("-" * 66)

    fake_man = build_manifest(produced, fake_id)
    real_man = build_manifest(produced, content_hash)
    fake_res = verify(delivered, fake_man, fake_id)
    real_res = verify(delivered, real_man, content_hash)

    fake_clean = all(ok for _, ok in fake_res)
    real_flagged = [n for n, ok in real_res if not ok]
    print("  fake id verifies the tampered delivery as clean = %s" % fake_clean)
    print("  content hash flags the tampered asset = %s (%s)" % (bool(real_flagged), real_flagged))
    swap_caught = fake_clean and len(real_flagged) > 0

    # the swap really did change bytes but keep the name.
    a, b = collision
    fake_collides = fake_id(a) == fake_id(b)
    hash_distinct = content_hash(a) != content_hash(b)
    print("  same-name assets: fake ids collide = %s, content hashes distinct = %s"
          % (fake_collides, hash_distinct))

    # a content hash changes iff the bytes change (rename does not move it).
    renamed = dict(produced[0])
    renamed = {"name": "renamed.png", "bytes": produced[0]["bytes"]}
    hash_rename_stable = content_hash(renamed) == content_hash(produced[0])
    print("  content hash is stable under rename (same bytes) = %s" % hash_rename_stable)

    det = content_hash(produced[0]) == content_hash(produced[0])
    ok = swap_caught and fake_collides and hash_distinct and hash_rename_stable and det
    print("-" * 66)
    print("SELF-TEST %s  swap_caught=%s  fake_collides=%s  hash_distinct=%s  rename_stable=%s"
          % ("PASS" if ok else "FAIL", swap_caught, fake_collides, hash_distinct, hash_rename_stable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Content-hash provenance vs a made-up id.")
    p.add_argument("--manifest", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--collision", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    produced, delivered, collision = load()
    print("produced=%d  delivered=%d  file=%s  (assets are a fixture)"
          % (len(produced), len(delivered), ASSETS.name))
    print("")

    if args.check:
        return 0 if check(produced, delivered, collision) else 1
    if args.manifest:
        manifest_view(produced)
    elif args.verify:
        verify_view(produced, delivered)
    elif args.collision:
        collision_view(collision)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
