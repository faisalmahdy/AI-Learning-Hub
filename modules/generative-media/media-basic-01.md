---
id: media-basic-01
title: Provenance needs a content hash, not a made-up id
topic: generative-media
level: basic
status: ready
time: 6-8h
summary: Record a generated asset's provenance by an id derived from its filename and a swapped image — new bytes, same name — verifies as genuine while two genuinely different images with the same name collide to one id, so the manifest is provenance theater. Hash the actual bytes with SHA-256 and the swap is caught (the recomputed hash no longer matches the manifest) and the collision disappears (distinct bytes, distinct hashes), because provenance has to be a function of the content, not its label.
eli5: A sticker with the product's name does not change if someone swaps what's inside the box. A wax seal made from the actual contents breaks the moment anything is different — so fingerprint the bytes, not the filename.
---

## Why this module

This opens the generative-media track, whose spine is provenance: for every image, video, or audio clip a pipeline produces, a record of what it is and where it came from. The scan points at the exact weak spot to fix first — a media pipeline that computes a "fake stableHex" for each asset, an id that looks like a fingerprint but is not one — and the fix, "replace the fake stableHex with real hashing." That one substitution is the difference between a provenance chain you can verify and a manifest that only pretends.

The trap is that a made-up id *looks* like provenance. It is stable, it is unique-ish, it goes in the manifest next to each asset. But if the id is derived from the filename or a counter, it says nothing about the bytes, and provenance is entirely about the bytes. Swap an asset's contents while keeping its name and the id is unchanged, so the manifest cheerfully verifies a tampered or substituted file as genuine. Worse, two different assets that happen to share a name collide to the same id, so the manifest cannot even tell them apart. A content hash — SHA-256 of the actual bytes — fixes both at once: it changes with any edit and is unique per content.

You need nothing but Python 3 and the standard library's `hashlib`. Everything runs offline against a small asset fixture, `$0.00`, one sitting. The instinct to unlearn is that any stable unique-looking string is a fingerprint. A fingerprint is a function of the thing it identifies; an id that ignores the content identifies nothing that matters.

Here is a delivery with one swapped asset, verified two ways:

```
# modules/generative-media/code/media-basic-01/ — COMPLETE, run from that directory
$ python3 hashprov.py --verify

VERIFY — one delivered asset was swapped (bytes changed, name kept)
------------------------------------------------------------------
  fake id (name)   verifies clean: True   flagged: none
  content hash     verifies clean: False   flagged: ['scanner.png']
```

run: 2026-08-25 · deterministic; asset bytes are a fixture · 3 produced, 3 delivered · `python3 hashprov.py --verify`

`scanner.png` was swapped — its bytes changed, its name did not. The name-based id verifies the whole delivery as clean, waving the swap through. The content hash recomputes from the new bytes, finds they no longer match the manifest, and flags exactly `scanner.png`. This module is the difference between those two rows.

## Concepts

Named here so you can find them again; each is built below.

- **Provenance** — a verifiable record of what an asset is, so a delivered file can be proven to be the produced one.
- **Manifest** — the record: each asset's provenance id, written at production time.
- **Fake id** — an id derived from metadata (name, counter, timestamp); looks like a fingerprint, ignores the bytes. The bug.
- **Content hash** — SHA-256 of the actual bytes; changes with any edit, unique per content. The fix.
- **Swap / tamper** — new bytes under an unchanged name; what a fake id cannot see.
- **Collision** — two different assets mapping to the same id; what a name-based id causes.

## Worked example

Source: faisalmahdy/ai-studio's `worker/genblaze_pipeline.py` and `storage_b2.py`, whose asset id is the "fake stableHex" the scan flags for replacement, and the hub's own asset pipeline (`docs/asset-pipeline.md`) whose manifest requires a provenance entry per asset. This module builds the real hash that manifest should carry.

Script and fixture: `modules/generative-media/code/media-basic-01/` — `hashprov.py`, and `assets.json`, three produced assets, a delivery with one swapped, and a name collision. Every command runs from there.

### The frame: a name sticker versus a wax seal

Imagine sealing a box of documents for delivery. One way is to slap a sticker on it that reads "Contract, March." The sticker is stable and identifies the box — and it does absolutely nothing if someone opens the box, swaps the contract, and reseals it, because the sticker was never about the contents. The other way is a wax seal pressed from the documents themselves: change a single page and the seal no longer matches. The sticker is a name; the wax seal is a content hash.

A fake provenance id is the sticker. It goes in the manifest, it looks official, and it verifies a swapped asset as genuine because it never looked at the asset. A content hash is the wax seal: recompute it from the delivered bytes and any change breaks the match. The whole module is trading the sticker for the seal.

### The two id schemes

The fake id hashes the *name* — stable, unique per name, and blind to the bytes.

```
# hashprov.py:37-40 — COMPLETE (the bug: an id derived from the name only)
def fake_id(asset):
    """THE BUG: an id derived from the name only. Blind to the bytes -- rename-stable
    but also swap-blind, and it collides whenever two assets share a name."""
    return "id-" + hashlib.sha256(asset["name"].encode()).hexdigest()[:8]
```

Note it *uses* SHA-256 — which is what makes it so convincing. The hash function is not the point; *what you hash* is. Hash the name and you get a fingerprint of the name, which is exactly the wrong thing. The content hash hashes the bytes.

```
# hashprov.py:43-45 — COMPLETE (the fix: hash the actual bytes)
def content_hash(asset):
    """The fix: SHA-256 of the actual bytes. Changes with any edit; unique per content."""
    return hashlib.sha256(asset["bytes"].encode()).hexdigest()[:12]
```

At production time each is written into a manifest — the provenance record the delivered assets will later be checked against.

```
# hashprov.py:48-50 — COMPLETE (record the id at production time)
def build_manifest(assets, id_fn):
    """Record each asset's id at production time -- the provenance record."""
    return {a["name"]: id_fn(a) for a in assets}
```

### Verification: recompute and compare

To verify a delivery, recompute each asset's id from what actually arrived and compare it to the manifest. A mismatch means the bytes changed since production.

```
# hashprov.py:55-63 — COMPLETE (recompute the id, compare to the manifest)
def verify(delivered, manifest, id_fn):
    """Recompute each delivered asset's id and compare to the manifest. A mismatch
    means the bytes changed since production; absence of a mismatch means 'genuine'."""
    results = []
    for a in delivered:
        recomputed = id_fn(a)
        recorded = manifest.get(a["name"])
        results.append((a["name"], recorded == recomputed))
    return results
```

Under the fake id, the swapped `scanner.png` recomputes to the same id — because its name is unchanged and the name is all the id ever saw — so it matches the manifest and verifies clean. Under the content hash, its new bytes produce a new hash that does not match the recorded one, and the swap is caught.

<svg viewBox="0 0 700 190" role="img" aria-label="scanner.png at production has bytes A, content hash H1, recorded in the manifest. At delivery its bytes are B (swapped), content hash H2. The fake id is name-based and identical at both, so it matches and misses the swap. The content hash differs H1 vs H2, so it catches it.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">scanner.png — produced (bytes A) vs delivered (bytes B, swapped)</text>
    <rect x="30" y="34" width="280" height="60" rx="5" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="40" y="52" fill="var(--ink)">produced: "...missing one parcel"</text>
    <text x="40" y="70" fill="var(--s2)">fake id = id-5c458368</text>
    <text x="40" y="86" fill="var(--s1)">content = d6657969ac5f</text>
    <rect x="390" y="34" width="280" height="60" rx="5" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="400" y="52" fill="var(--ink)">delivered: "...a hidden backdoor"</text>
    <text x="400" y="70" fill="var(--s2)">fake id = id-5c458368  (same!)</text>
    <text x="400" y="86" fill="var(--s1)">content = d99... (different)</text>
    <text x="30" y="124" fill="var(--s2)">fake id matches -> "genuine" -> swap MISSED</text>
    <text x="30" y="150" fill="var(--s1)">content hash differs -> mismatch -> swap CAUGHT</text>
  </g>
</svg>
^ The swap keeps the name and changes the bytes. The name-based id is identical before and after, so it matches the manifest and misses the tamper; the content hash moves with the bytes, so it breaks the match and catches it.

### The collision, and the fix in one run

The fake id has a second failure: two different assets that share a name collide to one id, so the manifest cannot tell them apart.

```
# $ python3 hashprov.py --collision
#   logo.png (bytes='version one: a blue circle...') fake=id-ab211233 content=efc53e1210d9
#   logo.png (bytes='version two: a red square...')  fake=id-ab211233 content=8f58c77848ee
```

run: 2026-08-25 · fixture · `python3 hashprov.py --collision`

Same name, same fake id — the manifest would record one and silently overwrite the other. The content hashes are distinct, because the bytes are, so a content-addressed manifest keeps both straight. The self-test confirms every claim at once:

```
# $ python3 hashprov.py --check
#   fake id verifies the tampered delivery as clean = True
#   content hash flags the tampered asset = True (['scanner.png'])
#   same-name assets: fake ids collide = True, content hashes distinct = True
#   content hash is stable under rename (same bytes) = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 hashprov.py --check`

<svg viewBox="0 0 700 150" role="img" aria-label="Two different logo.png assets. Both map to the same fake id id-ab211233 because the name is identical. Their content hashes efc53e1210d9 and 8f58c77848ee are different because the bytes are.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">two DIFFERENT assets named logo.png</text>
    <rect x="30" y="34" width="300" height="46" rx="5" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="40" y="52" fill="var(--ink)">logo.png = blue circle</text>
    <text x="40" y="70" fill="var(--muted)">fake id-ab211233   content efc53e1210d9</text>
    <rect x="30" y="88" width="300" height="46" rx="5" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="40" y="106" fill="var(--ink)">logo.png = red square</text>
    <text x="40" y="124" fill="var(--muted)">fake id-ab211233   content 8f58c77848ee</text>
    <text x="360" y="58" fill="var(--s2)">fake ids collide (id-ab211233)</text>
    <text x="360" y="76" fill="var(--s2)">-> manifest overwrites one</text>
    <text x="360" y="112" fill="var(--s1)">content hashes differ</text>
    <text x="360" y="130" fill="var(--s1)">-> both kept apart</text>
  </g>
</svg>
^ Same name, so the same fake id — the manifest records one and loses the other. The bytes differ, so the content hashes differ, and a content-addressed manifest keeps both. Identity by name collides; identity by content cannot.

The last line is the one that shows the content hash is not merely stricter but *correct*: it is stable under a rename, because a rename does not change the bytes. It moves when and only when the content moves — which is exactly what a fingerprint must do.

**Provenance is a fingerprint of the content, not its label: hash the bytes, so a swap changes the id and a rename does not — an id derived from the name catches neither the tamper nor the collision.**

## Build

The pipeline in one paragraph: at production, compute each asset's provenance id as a cryptographic hash of its actual bytes and record it in the manifest; at delivery or audit, recompute the hash from the bytes that arrived and compare to the manifest, failing on any mismatch; and content-address the manifest by that hash so two different assets can never collide. Never derive a provenance id from a name, a counter, or a timestamp.

We opened on the swap. The scheme that catches it:

```
# modules/generative-media/code/media-basic-01/ — COMPLETE, run from that directory
$ python3 hashprov.py --verify
  content hash     verifies clean: False   flagged: ['scanner.png']
```

Now hash your own assets. Take a folder of generated media, compute a SHA-256 per file, and write a manifest keyed by that hash. Your number to beat is the **swap-detection rate**: tamper with one file's bytes and confirm your manifest flags it while a name-based scheme would not. Build two different files with the same name and confirm the content hashes differ. Bring back the caught swap and the two distinct hashes. Good luck.

## Definition of done

- [ ] A provenance id computed as a cryptographic hash of each asset's actual bytes
- [ ] A manifest recording that hash per asset at production time
- [ ] Verification that recomputes the hash from delivered bytes and fails on a mismatch
- [ ] Your own `assets.json` (or real files) with a swapped asset and a name collision
- [ ] The name-based fake id kept for contrast, so the swap it misses is visible
- [ ] `python3 hashprov.py --check` printing SELF-TEST PASS: fake misses the swap, hash catches it, fake collides, hash is rename-stable
- [ ] The swap-detection result recorded, and the two distinct hashes for the collision
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A swapped image verified as genuine under one provenance scheme. Name the scheme, and say what its id was actually a fingerprint of.
2. The fake id used SHA-256 and was still wrong. Explain why the hash function was not the problem.
3. Two different assets shared a name and got the same id. Which scheme caused that, and how does the content hash avoid it?
4. Why must a good provenance id change under a byte swap but stay the same under a rename?
5. Your own run caught a swap. What file did you tamper with, and what were the two hashes (before and after)?

## External resources

- faisalmahdy/ai-studio — `worker/genblaze_pipeline.py` and `storage_b2.py` — my summary: the media pipeline whose "fake stableHex" this module replaces; read it for where an asset id is minted and how a real content hash drops into the same slot, per the scan's fix.
- The hub's `docs/asset-pipeline.md` — my summary: the manifest-first asset lineage every generated asset in this hub must carry; read it for the provenance-entry schema this module's content hash belongs in.
- IPFS / content addressing — https://docs.ipfs.tech/concepts/content-addressing/ — my summary: a whole storage model where the address of a file *is* the hash of its content, so identity and integrity are the same thing; read it for the principle this module applies at the scale of one manifest.
