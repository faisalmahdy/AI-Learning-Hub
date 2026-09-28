---
id: deepcopy-inter-01
title: Deep-copy a nested structure — a slice or .copy() duplicates only the top level, so the copy's inner objects are still shared
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: You have a nested structure — a list of lists, a dict of lists, an object holding objects — and want an independent copy so you can modify one without touching the other. You reach for the obvious tools: a slice (list[:]), list(x), x.copy(), dict(d). They all make a copy, and for a flat structure it is fully independent; for a nested structure they make a shallow copy, which duplicates only the outermost container — the new container is a distinct object, but its elements are not copies, they are the very same inner objects the original holds, so copy[0] is original[0], the same list in memory referenced from two places. The bug this creates is spooky action at a distance: you mutate the copy's inner element and the original changes too, because there is only one inner element and both containers point at it. The code looks correct — you made a copy and modified the copy — and it is baffling until you know the copy was skin-deep. It is especially treacherous because the shallow copy is independent at the top level: appending a whole new element to the copy leaves the original alone, so it passes a naive test and fails only when you reach into the nesting, which is what real code does. The fix is copy.deepcopy, which recursively duplicates every level, so the copy's inner objects are new too and mutating them cannot reach the original — at the cost of walking and allocating the whole structure, so you use shallow when the structure is flat or sharing is intended and deep when you need true independence of a nested structure. On a fixture matrix [[1, 2], [3, 4]], a shallow copy shares the row lists (copy[0] is original[0]), so appending 9 to the shallow copy's first row makes the original's first row [1, 2, 9] too, while a deep copy's rows are independent and the same append leaves the original untouched.
eli5: Imagine you have a folder with some papers in it, and you want your own copy so you can scribble on it. If you just photocopy the folder's cover and put the SAME papers inside your new folder, you now have two folders — but they hold the same physical papers, so when you scribble on a paper in "your" folder, it's scribbled in the original too, because it's literally the same paper. That's a shallow copy: new folder, same papers. What you actually wanted was to photocopy every paper as well, so your folder has its own separate papers you can mark up freely — that's a deep copy. The tricky part is that the shallow copy fools you: if you just add a whole new paper to your folder, the original folder doesn't get it, so it seems independent — until you write on one of the shared papers.
---

## Why this module

Copying is one of those operations that seems too simple to get wrong, and the nested case is a reliable source of bugs precisely because the simple tools quietly do something other than what you mean. When you say "copy this," you almost always mean "give me a version I can change without affecting the original." For a flat list that is exactly what a slice does. For a nested list it is not, and the gap between what the tool does and what you meant is invisible until a mutation reaches through it.

The mechanism is that a shallow copy copies references, not the things they point to. The outer container is genuinely new — it has its own slots — but each slot is filled with the same object the original's slot held. For immutable inner values (numbers, strings, tuples) this never matters, because you cannot mutate them in place, so nothing leaks. For mutable inner values (lists, dicts, objects) it matters completely: the copy and the original share those objects, and an in-place mutation of one is a mutation of the other.

The deception is that the top level really is independent, so half your tests pass. This module makes both halves visible: it shows the shared inner identity, and it mutates through a shallow and a deep copy to show one leaking and one not.

**To independently copy a nested structure, use a deep copy (copy.deepcopy) rather than a slice, list(), or .copy(), because those make a shallow copy that duplicates only the top level and shares the inner objects — so mutating an inner element through the copy also mutates the original.**

## Concepts

The fixture is a nested list — a 2×2 matrix, a list whose elements are themselves lists.

```json filename=modules/teaching-and-portability/code/deepcopy-inter-01/deepcopy.json:3 COMPLETE
  "matrix": [[1, 2], [3, 4]]
```

A fresh copy for experimenting is built row by row. The shallow copy is a slice/list() — top level only; the deep copy walks every level.

```python filename=modules/teaching-and-portability/code/deepcopy-inter-01/deepcopy.py:33-45 COMPLETE
def fresh_matrix(data):
    """A fresh independent copy of the fixture matrix to experiment on."""
    return [list(row) for row in data["matrix"]]


def shallow_copy(m):
    """A slice / list() / .copy() -- duplicates the top level only."""
    return list(m)


def deep_copy(m):
    """copy.deepcopy -- duplicates every level recursively."""
    return copy.deepcopy(m)
```

The test that exposes the sharing is to mutate an inner element of the copy in place and look at the original's corresponding element.

```python filename=modules/teaching-and-portability/code/deepcopy-inter-01/deepcopy.py:48-51 COMPLETE
def append_to_inner_and_return_original(m, cp, value):
    """Append value to the copy's first inner list; return the original's first inner list."""
    cp[0].append(value)
    return m[0]
```

<svg role="img" aria-label="A shallow copy: two outer list boxes each with slots pointing to the same two shared inner row objects; a deep copy: two outer boxes pointing to separate inner row objects" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8" fill="var(--s2)">shallow: outer copied, rows shared</text>
  <rect x="14" y="20" width="30" height="14" fill="var(--s2)"/><text x="18" y="30" font-size="7" fill="var(--panel)">orig</text>
  <rect x="14" y="38" width="30" height="14" fill="var(--s2)"/><text x="18" y="48" font-size="7" fill="var(--panel)">copy</text>
  <rect x="90" y="22" width="34" height="14" fill="var(--muted)"/><text x="96" y="32" font-size="7" fill="var(--panel)">[1,2]</text>
  <rect x="90" y="42" width="34" height="14" fill="var(--muted)"/><text x="96" y="52" font-size="7" fill="var(--panel)">[3,4]</text>
  <line x1="44" y1="27" x2="90" y2="29" stroke="var(--s2)" stroke-width="1"/><line x1="44" y1="45" x2="90" y2="31" stroke="var(--s2)" stroke-width="1"/>
  <text x="130" y="40" font-size="7.5" fill="var(--s2)">both → same rows</text>
  <text x="10" y="78" font-size="8" fill="var(--s1)">deep: rows copied too</text>
  <rect x="14" y="84" width="30" height="14" fill="var(--s1)"/><text x="18" y="94" font-size="7" fill="var(--panel)">orig</text>
  <rect x="14" y="102" width="30" height="14" fill="var(--s1)"/><text x="18" y="112" font-size="7" fill="var(--panel)">copy</text>
  <rect x="90" y="82" width="34" height="14" fill="var(--muted)"/><text x="96" y="92" font-size="7" fill="var(--panel)">[1,2]</text>
  <rect x="90" y="102" width="34" height="14" fill="var(--muted)"/><text x="96" y="112" font-size="7" fill="var(--panel)">[1,2]'</text>
  <line x1="44" y1="91" x2="90" y2="89" stroke="var(--s1)" stroke-width="1"/><line x1="44" y1="109" x2="90" y2="109" stroke="var(--s1)" stroke-width="1"/>
  <text x="130" y="100" font-size="7.5" fill="var(--s1)">each → own rows</text>
</svg>
^ A shallow copy makes a new outer list whose slots point at the original's row objects — both point at the same rows. A deep copy also duplicates the rows, so each outer list points at its own. Mutating a row leaks in the shallow case and not the deep.

**A shallow copy copies the slots, not what fills them — so a nested structure's inner mutable objects remain shared, and only a deep copy gives you an independent one.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the state-copying step of a data pipeline, reduced to a 2×2 matrix so every identity is checkable by hand.

Run `--identity` to see what each copy shares.

```text filename=deepcopy.py --identity
  outer list is a new object:  shallow True   deep True
  inner row IS the original's: shallow True   deep False
  a shallow copy duplicates the outer list but shares the inner rows
```

Both copies have a distinct outer list — so far they look equally independent. The difference is the inner row: for the shallow copy, `copy[0] is original[0]` is True — it is literally the same list object; for the deep copy it is False — a new list. This one line is the whole trap: the shallow copy passed the "is it a new object?" test at the top level and failed it one level down, where it counts.

Now `--mutate` reaches into the nesting.

```text filename=deepcopy.py --mutate
  shallow: original[0] after copy[0].append(9) = [1, 2, 9]
  deep:    original[0] after copy[0].append(9) = [1, 2]
```

Appending 9 to the shallow copy's first row changed the original's first row to [1, 2, 9] — because the copy's first row and the original's first row are the same list. The identical operation on the deep copy left the original at [1, 2], because the deep copy's first row is its own object. You modified "the copy" in both cases; only in the shallow case did the original change, and nothing in the code that did the mutation would tell you why.

**Mutating an inner row through the shallow copy silently changed the original to [1, 2, 9], while the deep copy's mutation stayed contained — same code, and only the copy's depth decided whether the original leaked.**

## Build

The self-test asserts the deceptive part first: the shallow copy's outer list is independent, but it shares the inner rows, while the deep copy's inner rows are new.

```python filename=modules/teaching-and-portability/code/deepcopy-inter-01/deepcopy.py:89-96 COMPLETE
    shallow_outer_independent = s is not m
    print("  the shallow copy's OUTER list is a distinct object = %s" % shallow_outer_independent)

    shallow_shares_inner = s[0] is m[0]
    print("  the shallow copy shares the original's inner rows = %s (copy[0] is original[0])" % shallow_shares_inner)

    deep_inner_independent = d[0] is not m[0]
    print("  the deep copy's inner rows are new objects = %s" % deep_inner_independent)
```

<svg role="img" aria-label="A test matrix: shallow copy passes the top-level independence test but fails the inner-mutation test; deep copy passes both" viewBox="0 0 320 100">
  <text x="120" y="18" font-size="8" fill="var(--muted)">top-level test</text>
  <text x="230" y="18" font-size="8" fill="var(--muted)">inner-mutation test</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">shallow</text>
  <rect x="120" y="30" width="70" height="16" fill="var(--s1)"/><text x="140" y="43" font-size="7.5" fill="var(--panel)">pass</text>
  <rect x="230" y="30" width="70" height="16" fill="var(--s2)"/><text x="248" y="43" font-size="7.5" fill="var(--panel)">FAIL (leaks)</text>
  <text x="10" y="70" font-size="8.5" fill="var(--s1)">deep</text>
  <rect x="120" y="58" width="70" height="16" fill="var(--s1)"/><text x="140" y="71" font-size="7.5" fill="var(--panel)">pass</text>
  <rect x="230" y="58" width="70" height="16" fill="var(--s1)"/><text x="248" y="71" font-size="7.5" fill="var(--panel)">pass</text>
  <text x="10" y="92" font-size="7.5" fill="var(--muted)">shallow passes the easy test and fails the one real code hits</text>
</svg>
^ The shallow copy passes the top-level independence test (fooling a naive check) and fails the inner-mutation test that real code triggers; the deep copy passes both. That one failing cell is the bug.

Running the check confirms every clause, including that the shallow mutation leaks and the deep one does not.

```python filename=modules/teaching-and-portability/code/deepcopy-inter-01/deepcopy.py:98-108 COMPLETE
    m1 = fresh_matrix(data)
    s1 = shallow_copy(m1)
    orig_after_shallow = append_to_inner_and_return_original(m1, s1, 9)
    shallow_leaks = orig_after_shallow == [1, 2, 9]
    print("  mutating the shallow copy's inner list changed the original = %s (%s)" % (shallow_leaks, orig_after_shallow))

    m2 = fresh_matrix(data)
    d2 = deep_copy(m2)
    orig_after_deep = append_to_inner_and_return_original(m2, d2, 9)
    deep_isolated = orig_after_deep == [1, 2]
    print("  mutating the deep copy's inner list left the original unchanged = %s (%s)" % (deep_isolated, orig_after_deep))
```

```text filename=deepcopy.py --check
  the shallow copy's OUTER list is a distinct object = True
  the shallow copy shares the original's inner rows = True (copy[0] is original[0])
  the deep copy's inner rows are new objects = True
  mutating the shallow copy's inner list changed the original = True ([1, 2, 9])
  mutating the deep copy's inner list left the original unchanged = True ([1, 2])
  appending a whole new row to the shallow copy is safe (top-level is independent) = True
```

**The check pins the leak to the shared inner rows and shows the deep copy isolating it, plus the top-level-safe result that makes the shallow copy deceptive — independent where you test, shared where you mutate.**

## Definition of done

Two properties close it. Mutating an inner element through the shallow copy must change the original (the bug), and mutating through the deep copy must leave it unchanged (the fix) — shown in the mutation block above. The deep copy's inner-object independence is what guarantees the second: new objects cannot alias the originals.

Three clarifications keep the choice right rather than reflexive. First, shallow is often the correct and cheaper choice: if the inner objects are immutable (numbers, strings, tuples) sharing them is harmless, and if you actually want the copy to share and see updates to the inner objects, shallow is what you want — deep copy is not "the safe default to always use," it is what you use when you will mutate nested mutable state and need isolation. Second, the trap generalizes beyond lists: dict(d), a copy constructor, and assignment of a nested object all copy references; the same rule applies to any container of mutable objects, and copy.deepcopy handles arbitrary nesting (and cycles) that hand-rolled copying often gets wrong. Third, deep copy has real costs and edge cases: it walks the entire structure (slow for large objects), it duplicates things you might have wanted shared (an open file handle, a database connection, a cache), and objects can customize deepcopy via `__deepcopy__`; for those, a targeted copy (copy the specific lists you will mutate) is often better than a blanket deepcopy. The reliable habit is to ask "will I mutate anything below the top level?" — if yes, a slice is not a copy of what you think, and you need a deep copy or a deliberate per-level one.

<svg role="img" aria-label="A decision: will I mutate below the top level? if no, shallow is fine; if yes and inner objects are mutable, deep copy needed" viewBox="0 0 320 110">
  <rect x="90" y="10" width="140" height="22" fill="none" stroke="var(--ink)" stroke-width="1"/><text x="96" y="25" font-size="8" fill="var(--ink)">mutate below top level?</text>
  <line x1="130" y1="32" x2="70" y2="54" stroke="var(--s1)" stroke-width="1"/>
  <line x1="190" y1="32" x2="250" y2="54" stroke="var(--s2)" stroke-width="1"/>
  <rect x="20" y="56" width="100" height="20" fill="var(--s1)"/><text x="30" y="70" font-size="7.5" fill="var(--panel)">no → shallow is fine</text>
  <rect x="200" y="56" width="105" height="20" fill="var(--s2)"/><text x="210" y="70" font-size="7.5" fill="var(--panel)">yes → deep copy</text>
  <text x="20" y="94" font-size="7" fill="var(--muted)">(also fine if inner objects are immutable — nothing to leak)</text>
  <text x="200" y="94" font-size="7" fill="var(--muted)">or copy just the sections you mutate</text>
</svg>
^ The rule is a single question: will you mutate anything below the top level? No (or the inner objects are immutable) → a shallow copy is correct and cheaper. Yes, with mutable inner objects → deep copy, or deliberately copy just the nested sections you will change.

**Done means the shallow copy's inner mutation leaks to the original while the deep copy's does not — a reference-vs-value distinction where shallow shares nested mutable objects and deep duplicates them, with shallow still correct for flat or intentionally-shared structures.**

## Boss fight

A function takes a configuration dictionary, makes a copy with `config.copy()` so it can apply some overrides without disturbing the caller's config, and returns the modified copy. It works for most configs, but callers occasionally report that their original config gets mutated anyway — specifically when the override touches a nested section like `config["database"]["timeout"]`. What is happening, and what is the fix?

`config.copy()` (and dict(config), and a slice for lists) makes a shallow copy: the returned dict is a new top-level dict, but its values are the same objects as the caller's config, so `copy["database"]` is the same dictionary as `config["database"]`. When the function overrides a top-level key (copy["region"] = "eu"), it replaces the slot in the copy only and the caller's config is untouched — which is why it works for most configs and passes casual testing. But when the override reaches into a nested section (copy["database"]["timeout"] = 30), it mutates the shared inner dict in place, and because the caller's config points at that same inner dict, the caller's config["database"]["timeout"] changes too — the leak the users report, appearing exactly when the override is nested. The fix is to deep-copy the config before applying overrides: `import copy; working = copy.deepcopy(config)`, which duplicates every nested level so the function's mutations cannot reach the caller's structure. If deep-copying the whole config is too expensive or copies things you want shared (a connection object stored in the config, say), the targeted alternative is to shallow-copy and then explicitly copy only the nested sections you are about to mutate (copy the "database" sub-dict before writing to it). Either way, the rule the code violated is that a shallow copy is only independent at the top level, and any function that mutates nested config state needs a deep (or deliberately per-level) copy, not `.copy()`.

## External resources

The Python `copy` module documentation — the authoritative description of shallow vs deep copy, when each is appropriate, how copy.deepcopy handles recursive structures and cycles, and the `__copy__`/`__deepcopy__` customization hooks.

Any language's aliasing/reference-semantics documentation (Java's clone() shallow-copy caveat, JavaScript's spread/Object.assign shallow copy, C#'s MemberwiseClone) — the same shallow-vs-deep distinction across languages, useful for seeing that "copy shares nested references" is a general property of reference semantics, not a Python quirk.
