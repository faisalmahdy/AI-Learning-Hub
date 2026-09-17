---
id: hashorder-inter-01
title: Sort a set before you serialize it — or the same data writes different bytes, and a different hash, on every run
topic: teaching-and-portability
level: intermediate
status: ready
time: 16 min
summary: Python randomizes the hash of str objects once per process (seeded from PYTHONHASHSEED), and a set stores its members in slots chosen by their hash, so the iteration order of a set of strings changes every time the interpreter starts. The set holds the same members; only the order it hands them back differs. That is invisible until you serialize the set — join it into a manifest, a cache key, or a config digest — at which point the bytes you produce depend on a per-process random seed you never chose, so the same tags produce different output and a different hash on the next run or a colleague's machine. The fix is one word: sort. On a fixture of nine tags run under two fixed hash seeds, the raw set order and its sha256 differ across the seeds while the sorted order and its sha256 are identical.
eli5: Imagine a bag of labeled balls. Every time you open the bag, the balls come out in a different order, even though it's the same balls. If you write down the order as your "answer," your answer changes every time for no real reason — and a friend copying your steps gets yet another answer. Python sets are that bag: the order changes each run. If you sort the balls first and then write them down, everyone gets the same answer every time. That's the whole fix.
---

## Why this module

A set is for membership, not for order — but the moment you serialize one, its per-run random order silently becomes part of your output, and the same data starts producing different bytes and a different hash on every run.

Python randomizes the hash of str objects once per process, seeded from the environment. A set stores each member in a slot chosen by that member's hash, and it iterates in slot order, so a set of strings comes out in a different order every time the interpreter starts. This is deliberate — hash randomization defends against a denial-of-service attack — and it is harmless as long as the set is only ever asked "is this in you?" The trouble begins when the set crosses into output. Join it into a manifest line, fold it into a cache key, hash it into a "did the config change?" digest, and the order the set happened to iterate this process becomes part of the bytes. Nothing about the data changed; a per-process random seed you never set did. The same tags write one string today and a different one tomorrow, one digest on your machine and another on your colleague's.

**A set of strings iterates in an order decided by per-process hash randomization, so serializing a set directly bakes a random seed into your output — the same data then produces different bytes, and a different hash, on the next run.**

The failure is quiet and expensive: a cache keyed on the digest misses on the next run for no real change, a golden-file test fails for nobody's reason, a reproducibility check reports drift that isn't there. The fix is one word. `sorted(s)` returns the members in a total order that does not depend on hashing, so the serialization is byte-identical across processes, machines, and Python versions. This module drives two child interpreters at fixed but different hash seeds to make the non-determinism visible and deterministic to test, then shows sorting collapse the two orders — and the two digests — back into one.

## Concepts

**Hash randomization** means Python picks a random seed for hashing str (and bytes) once per process, from the `PYTHONHASHSEED` environment variable. Two runs of the same program hash the same string to different values.

**A set iterates in slot order**, and each member's slot is chosen from its hash. So the iteration order of a set of strings is a function of the per-process hash seed — different every run, though the members are always the same.

```python filename=modules/teaching-and-portability/code/hashorder-inter-01/hashorder.py:50-52 COMPLETE
def set_order(tags):
    """The order a fresh set iterates these strings -- decided by their per-process randomized hashes."""
    return list(set(tags))
```

**Order-dependent output** is any serialization — a join, a hash, a written file, an equality comparison against a golden copy — where the sequence of elements matters. Feed a set's iteration order into one of these and you have made your output depend on the hash seed.

**Sorting imposes a hash-independent total order.** `sorted(tags)` returns the same sequence in every process, so any serialization built on it is reproducible.

<svg role="img" aria-label="The same three strings hash to different slots under two seeds, so the set iterates them in two different orders, while sorting yields one fixed order" viewBox="0 0 300 118" width="300" height="118">
  <text x="8" y="12" fill="var(--muted)" font-size="8">members {a, b, c} → slots by hash → iteration order</text>
  <text x="8" y="34" fill="var(--s2)" font-size="8">seed 1</text>
  <rect x="46" y="26" width="18" height="12" fill="none" stroke="var(--line)"/><text x="51" y="35" fill="var(--ink)" font-size="8">b</text>
  <rect x="66" y="26" width="18" height="12" fill="none" stroke="var(--line)"/><text x="71" y="35" fill="var(--ink)" font-size="8">a</text>
  <rect x="86" y="26" width="18" height="12" fill="none" stroke="var(--line)"/><text x="91" y="35" fill="var(--ink)" font-size="8">c</text>
  <text x="112" y="35" fill="var(--s2)" font-size="7">→ b, a, c</text>
  <text x="8" y="58" fill="var(--s1)" font-size="8">seed 2</text>
  <rect x="46" y="50" width="18" height="12" fill="none" stroke="var(--line)"/><text x="51" y="59" fill="var(--ink)" font-size="8">c</text>
  <rect x="66" y="50" width="18" height="12" fill="none" stroke="var(--line)"/><text x="71" y="59" fill="var(--ink)" font-size="8">b</text>
  <rect x="86" y="50" width="18" height="12" fill="none" stroke="var(--line)"/><text x="91" y="59" fill="var(--ink)" font-size="8">a</text>
  <text x="112" y="59" fill="var(--s1)" font-size="7">→ c, b, a</text>
  <line x1="8" y1="74" x2="292" y2="74" stroke="var(--grid)"/>
  <text x="8" y="90" fill="var(--muted)" font-size="8">sorted()</text>
  <text x="112" y="90" fill="var(--ink)" font-size="8">→ a, b, c  (every seed)</text>
  <text x="8" y="110" fill="var(--muted)" font-size="8">same members, two set orders, one sorted order</text>
</svg>
^ The same members land in different slots under two hash seeds, so the set iterates in two different orders; sorting ignores the slots and returns one order for every seed.

**A set answers "is this a member?"; it never answers "in what order?" — so sort (or otherwise impose an order) at the exact moment a collection crosses into anything you serialize, hash, compare, or commit.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/hashorder-inter-01/hashorder.py

The fixture is nine category tags and two fixed hash seeds, so the non-determinism itself can be reproduced.

```json filename=modules/teaching-and-portability/code/hashorder-inter-01/hashorder.json:1-5 COMPLETE
{
  "_meta": "A set of string labels serialized two ways. tags is a collection of category strings that a pipeline builds into a Python set and then writes out -- a manifest, a cache key, a hash of the config. Python randomizes the hashing of str objects per process (PYTHONHASHSEED), so the ITERATION ORDER of a set of strings changes from run to run. Serialize the set directly and the same tags produce different output -- and a different digest -- on the next run or on a colleague's machine. Sort before you serialize and the order is fixed, so the output and its digest are reproducible. This fixture drives two child processes with fixed but different PYTHONHASHSEED values to make the non-determinism visible and deterministic to test.",
  "tags": ["vision", "audio", "text", "tabular", "graph", "timeseries", "reinforcement", "generative", "retrieval"],
  "seeds": [1, 2]
}
```

A real program cannot choose its hash seed after it starts, so to demonstrate the effect on demand the script launches two child interpreters, each pinned to a different `PYTHONHASHSEED`, and captures how each iterates the very same set.

```python filename=modules/teaching-and-portability/code/hashorder-inter-01/hashorder.py:55-60 COMPLETE
def run_worker(seed, tags):
    """Run --worker in a child interpreter pinned to `seed`, and return that process's set iteration order."""
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    out = subprocess.run([sys.executable, str(Path(__file__)), "--worker"],
                         capture_output=True, text=True, env=env, check=True)
    return out.stdout.strip().split(",")
```

Run `--order` to see the two child processes iterate the same set differently, and sorting recover one order.

```text filename=--order
ORDER — the same set iterates differently under different hash seeds
------------------------------------------------------------------------------
  set order  (PYTHONHASHSEED=1):  retrieval, reinforcement, audio, timeseries, graph, tabular, vision, generative, text
  set order  (PYTHONHASHSEED=2):  text, graph, generative, retrieval, reinforcement, vision, timeseries, audio, tabular
  differ across the two seeds?  True

  sorted     (any seed):           audio, generative, graph, reinforcement, retrieval, tabular, text, timeseries, vision
  identical across every seed?     True
```

The two set orders share not a single position — `retrieval` leads under seed 1, `text` under seed 2 — yet both are the same nine tags. That is the whole hazard in one screen: the members never changed, but the sequence did, purely because the two processes hashed the strings with different seeds. The sorted line, by contrast, is byte-for-byte the same regardless of seed. Change nothing but stop trusting the set's order, and the output stops moving.

<svg role="img" aria-label="The first position of the set is retrieval under seed 1 and text under seed 2, differing, while the sorted first position is audio under both seeds" viewBox="0 0 300 96" width="300" height="96">
  <text x="8" y="12" fill="var(--muted)" font-size="8">first three positions of the nine-tag output</text>
  <text x="8" y="32" fill="var(--s2)" font-size="8">set, seed 1</text>
  <text x="78" y="32" fill="var(--ink)" font-size="8">retrieval · reinforcement · audio …</text>
  <text x="8" y="50" fill="var(--s1)" font-size="8">set, seed 2</text>
  <text x="78" y="50" fill="var(--ink)" font-size="8">text · graph · generative …</text>
  <text x="220" y="41" fill="var(--muted)" font-size="7">← no shared position</text>
  <line x1="8" y1="58" x2="292" y2="58" stroke="var(--grid)"/>
  <text x="8" y="74" fill="var(--muted)" font-size="8">sorted</text>
  <text x="78" y="74" fill="var(--ink)" font-size="8">audio · generative · graph …</text>
  <text x="220" y="74" fill="var(--muted)" font-size="7">← same under both</text>
  <text x="8" y="90" fill="var(--muted)" font-size="8">two set rows disagree everywhere; the sorted row is identical</text>
</svg>
^ The two set orders disagree at the very first position — retrieval versus text — while the sorted order opens with audio under either seed, which is why only the sorted serialization is reproducible.

## Build

Serialize the set directly and the danger becomes concrete: the hash of the output is a coin flip. Run `--digest`, which joins each order and takes its sha256 — exactly what a cache key or a config-change digest does.

```text filename=--digest
DIGEST — serialize the set directly and its hash is a coin flip; sort first and it is fixed
------------------------------------------------------------------------------
  sha256(join(set order))  seed=1:  791eb70efdd344a072e1e260d10b02f0589ff69d3f1377c638c365f5d983c999
  sha256(join(set order))  seed=2:  78bba7450088cbed39dca7e7f8f0ef23e73faab19773a6d4ba543b789f3e8dc6
  the two digests differ?  True

  sha256(join(sorted))     any seed:  64f2669a75337761da79443dbe646e13ca44953d60889457c091a1ddfc430270
  identical across seeds?  True
```

Two completely different digests from identical data. A cache keyed on `791eb7…` is a guaranteed miss the next time the process starts and produces `78bba7…`; a "has the config changed?" guard fires on every run; a golden-file test that recorded one digest fails against the other. None of it reflects a real change — it reflects the process's hash seed, which is random by default and which you almost never want in your output. The sorted digest, `64f266…`, is the same in both children and will be the same on your reviewer's laptop and in CI, because sorting removed the only seed-dependent quantity. The lesson generalizes past sets: dict-key order was seed-dependent too before insertion order was guaranteed, and `frozenset`, set comprehensions, and `dict` built from a set all inherit the hazard. Reproducible output must never depend on a container's internal iteration order.

<svg role="img" aria-label="The raw set order forks into two different sha256 digests under two seeds, while the sorted order converges to a single digest for both" viewBox="0 0 300 110" width="300" height="110">
  <text x="8" y="12" fill="var(--muted)" font-size="8">sha256 of the joined order</text>
  <text x="8" y="34" fill="var(--ink)" font-size="8">raw set</text>
  <line x1="52" y1="30" x2="150" y2="22" stroke="var(--s2)"/><line x1="52" y1="30" x2="150" y2="44" stroke="var(--s2)"/>
  <rect x="152" y="15" width="120" height="14" fill="var(--s2)"/><text x="156" y="25" fill="var(--panel)" font-size="7">seed 1: 791eb7…</text>
  <rect x="152" y="37" width="120" height="14" fill="var(--s2)"/><text x="156" y="47" fill="var(--panel)" font-size="7">seed 2: 78bba7…</text>
  <text x="150" y="62" fill="var(--muted)" font-size="7">two digests → cache miss, false diff</text>
  <text x="8" y="86" fill="var(--ink)" font-size="8">sorted</text>
  <line x1="52" y1="82" x2="150" y2="82" stroke="var(--s1)"/>
  <rect x="152" y="75" width="120" height="14" fill="var(--s1)"/><text x="156" y="85" fill="var(--panel)" font-size="7">any seed: 64f266…</text>
  <text x="150" y="102" fill="var(--muted)" font-size="7">one digest → reproducible</text>
</svg>
^ The raw set order forks into two digests across the seeds — every downstream cache and comparison sees a phantom change — while the sorted order collapses to one digest for both.

## Definition of done

The self-test pins all four facts: the raw order differs across seeds, the members are nonetheless identical, the raw digest therefore differs, and sorting recovers one order and one stable digest.

```python filename=modules/teaching-and-portability/code/hashorder-inter-01/hashorder.py:102-115 COMPLETE
    order_differs = orders[0] != orders[1]
    print("  the raw set iteration order differs across the two seeds = %s" % order_differs)

    same_members = set(orders[0]) == set(orders[1]) == set(tags)
    print("  yet both hold exactly the same members = %s" % same_members)

    digest_differs = digest(orders[0]) != digest(orders[1])
    print("  so the digest of the joined set order differs across seeds = %s" % digest_differs)

    sorted_identical = sorted(orders[0]) == sorted(orders[1]) == sorted(tags)
    print("  sorting recovers one identical order for every seed = %s" % sorted_identical)

    sorted_digest_stable = len({digest(sorted(o)) for o in orders}) == 1
    print("  and the digest of the sorted order is stable across seeds = %s" % sorted_digest_stable)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — raw set order and its digest differ across seeds; sorted order and its digest are identical
--------------------------------------------------------------------------------------------------------
  the raw set iteration order differs across the two seeds = True
  yet both hold exactly the same members = True
  so the digest of the joined set order differs across seeds = True
  sorting recovers one identical order for every seed = True
  and the digest of the sorted order is stable across seeds = True
```

**Done means the non-determinism is proven and cured: under two fixed hash seeds the same nine tags iterate in two different orders and produce two different sha256 digests, while `sorted()` yields one identical order and one stable digest — so serializing the raw set is non-reproducible and serializing the sorted order is reproducible.**

## Boss fight

Sorting fixed the serialization, but predict the version that sorting alone does not fix, and the one an ordinary test run hides. It is tempting to think a passing test means your output is order-stable.

The first trap is that the default catches nothing: from Python 3.3 on, `PYTHONHASHSEED` is random, but many test harnesses and CI setups pin it (`PYTHONHASHSEED=0`) for exactly the "flaky test" reasons this module is about — and once it is pinned, every run in that environment hashes identically, so a set-order bug produces the same bytes every time and every test passes. The bug then ships and detonates on the first machine that did not pin the seed. The lesson: a green suite under a pinned seed is not evidence of order-stability; prove it by running the serialization under two different seeds, which is precisely what the digest here does. The fix is still to sort, but the test must vary the seed or it verifies nothing.

The second trap is that sorting is necessary but not always sufficient. `sorted()` on strings orders by Unicode code point, which is stable across machines — but `sorted(..., key=locale.strxfrm)` or any locale-aware key reintroduces environment dependence, and sorting objects without a total order (mixed types, or instances whose `__lt__` ties) leaves the tie broken by insertion order, which for a set is again hash order. And sorting only fixes the container you remembered to sort: a nested set inside a sorted list, a set used as a dict value, or a `json.dumps` without `sort_keys=True` over a dict built from set iteration each re-open the same hole one level down. The rule that actually holds is not "call sorted" but "no reproducible output may depend on any container's internal iteration order" — sorting is the usual way to satisfy it, at every level where a hash-ordered collection meets your bytes.

```python filename=modules/teaching-and-portability/code/hashorder-inter-01/hashorder.py:45-47 COMPLETE
def digest(items):
    """A sha256 over the joined items -- the kind of digest a cache key or config hash would use."""
    return hashlib.sha256("|".join(items).encode("utf-8")).hexdigest()
```

**Set and dict-key iteration order depends on per-process hash randomization, so any output built from it is non-reproducible — sort (by a hash- and locale-independent key) at every point a hash-ordered collection crosses into bytes you serialize, hash, or compare, and test the property under two different hash seeds, because a suite run under one pinned seed passes a bug it cannot see.**

## External resources

The Python documentation for `PYTHONHASHSEED` and `object.__hash__` — the primary description of per-process str/bytes hash randomization, why it exists (hash-collision denial-of-service defense), and how to pin or disable it.

Reproducible-build and reproducible-research guidance on eliminating non-determinism from outputs — sorted directory listings, sorted set/dict serialization, `json.dumps(..., sort_keys=True)` — which treat "sort before you serialize" as a general discipline, not a Python quirk.

The companion "seed the random generator" and "specify encoding when you read and write" modules — the same reproducibility principle applied to the other two silent per-environment variables (the RNG seed and the platform text encoding) that leak into output the moment you forget to pin them.
