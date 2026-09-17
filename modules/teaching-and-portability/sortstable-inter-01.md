---
id: sortstable-inter-01
title: Multi-key sorting by successive sorts needs a stable sort — an unstable one scrambles the secondary order
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: The standard way to sort by a primary key and then a secondary key, when your sort takes one key at a time, is two passes: sort by the secondary key first, then sort by the primary key — and the trick works only because of a property of the second sort called stability. A stable sort preserves the relative order of records that compare equal on its key, so when the second pass sorts by the primary key, all the records that share a primary key keep the order the first pass gave them, which was secondary-key order; the result is sorted by primary key and, within each group, by secondary key. An unstable sort makes no such promise: it can place equal-key records in any order, so the second pass reorders records within a primary group however its internals land and discards the secondary ordering the first pass built. The output is still correctly sorted by the primary key, because those keys differ — only the ties are scrambled, which is what makes the bug dangerous. On the fixture five employees are sorted by department then name: the stable two-pass sort leaves each department's names ascending (eng: Ann, Bob, Cara; sales: Ann, Bob), while an unstable primary sort leaves each department's names reversed (eng: Cara, Bob, Ann; sales: Bob, Ann). Both put the departments in the right order; only the stable sort keeps the names sorted within a department. The rule: stacking single-key sorts to get a multi-key order is a contract with the sort's stability, so either use a sort you know is stable or sort once by a compound key.
eli5: Imagine sorting a stack of cards first by name, then by team. If your sorting method keeps cards that are on the same team in the order they were already in, then after the team sort each team's cards are still in name order — great, that's what you wanted. But if your method shuffles same-team cards around instead of leaving them be, the name order you set up in the first pass gets wrecked, and each team's cards come out in some random order. The teams are still grouped correctly, so it looks fine until you check the names inside a team. Whether the two-pass trick works depends entirely on whether your sorter leaves tied cards alone.
---

## Why this module

Sorting by more than one key is one of the most ordinary things a program does — a table by department then name, transactions by date then amount, results by score then time. And one of the most ordinary ways to do it is to sort twice: least-significant key first, most-significant key last.

That technique is not free of assumptions. It quietly depends on the sort you are using being stable, and not every sort is. When it is not, the two-pass sort produces output that is correctly grouped by the primary key and silently wrong inside each group — a failure that passes a glance and fails an audit.

**Stacking single-key sorts to build a multi-key order is a contract with the sort's stability, and the contract is invisible until a tie reveals it.**

## Concepts

A sort is stable if it never reorders records that compare equal on its key: two records with the same key come out in the same order they went in. A sort is unstable if it is allowed to reorder them — which many efficient sorts (a plain quicksort, a heapsort) do as a side effect of how they move elements.

The two-pass technique leans on this exactly. To sort by primary then secondary, you first sort by the secondary key, putting the whole list in secondary order. Then you sort by the primary key. If that second sort is stable, every group of records sharing a primary key retains the secondary order they were already in, so the final list is primary-then-secondary sorted. Stability is the load-bearing property; without it the first pass was wasted.

Run the second pass with an unstable sort and the records within a primary group can land in any order. The primary keys are all distinct across groups, so they still sort correctly — the departments are grouped, the dates are in order. But inside a group, the ties are at the mercy of the sort's internals, and whatever secondary order the first pass established is gone.

This is a nasty bug precisely because of what stays right. The output is not obviously broken: the top-level ordering is perfect, the counts are correct, nothing is missing. Only the arrangement within tied groups is wrong, which is the one thing a quick look does not check and the one thing you ran two passes to get.

The fixes are two. Use a sort you know to be stable for the primary pass — many languages guarantee it (Python's sort, Java's Collections.sort for objects), some do not (C's qsort, JavaScript's sort historically). Or sidestep the whole dependency by sorting once with a compound key — a tuple of (primary, secondary) — so ties never arise and stability is irrelevant.

**A stable primary pass keeps each group in the secondary order the first pass built; an unstable one scrambles the ties while leaving the primary order — right where you look, wrong where you don't.**

<svg role="img" aria-label="The two-pass technique. Pass 1 sorts by the secondary key so the whole list is in secondary order. Pass 2 sorts by the primary key; a stable pass 2 keeps each primary group in the secondary order pass 1 built." viewBox="0 0 440 150">
<rect x="0" y="0" width="440" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">two passes: secondary first, then primary</text>
<text x="20" y="52" fill="var(--muted)" font-size="10">pass 1: sort by secondary</text>
<text x="240" y="52" fill="var(--s2)" font-size="10">whole list in name order</text>
<text x="200" y="80" fill="var(--muted)" font-size="14">&#8595;</text>
<text x="20" y="108" fill="var(--muted)" font-size="10">pass 2: sort by primary</text>
<text x="240" y="102" fill="var(--s2)" font-size="10">stable &#8594; groups keep name order</text>
<text x="240" y="120" fill="var(--s1)" font-size="10">unstable &#8594; groups scrambled</text>
</svg>
^ Pass 1 establishes the secondary order across the whole list; pass 2's stability is what decides whether that order survives inside each primary group.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/teaching-and-portability/code/sortstable-inter-01/sortstable.py

The fixture sorts five employees by department then name.

```json filename=modules/teaching-and-portability/code/sortstable-inter-01/sortstable.json:3-11 COMPLETE
  "primary_key": "dept",
  "secondary_key": "name",
  "records": [
    {"dept": "eng", "name": "Bob"},
    {"dept": "sales", "name": "Ann"},
    {"dept": "eng", "name": "Ann"},
    {"dept": "sales", "name": "Bob"},
    {"dept": "eng", "name": "Cara"}
  ]
```

The two sorts differ only in what they do to ties.

```python filename=modules/teaching-and-portability/code/sortstable-inter-01/sortstable.py:31-33 COMPLETE
def stable_sort(items, key):
    """A stable sort: equal-key records keep their input order (Python's sorted is stable)."""
    return sorted(items, key=key)
```

```python filename=modules/teaching-and-portability/code/sortstable-inter-01/sortstable.py:36-38 COMPLETE
def unstable_sort(items, key):
    """An unstable sort: equal-key records are reordered (here, into reverse input order)."""
    return [x for _idx, x in sorted(enumerate(items), key=lambda p: (key(p[1]), -p[0]))]
```

The two-pass sort applies secondary-then-primary.

```python filename=modules/teaching-and-portability/code/sortstable-inter-01/sortstable.py:41-44 COMPLETE
def two_pass(records, primary, secondary, primary_sort):
    """Sort by the secondary key (stably), then by the primary key with the given sort."""
    by_secondary = stable_sort(records, key=lambda r: r[secondary])
    return primary_sort(by_secondary, key=lambda r: r[primary])
```

With a stable primary pass, the names stay sorted within each department.

```text filename=sortstable.py --stable
STABLE — sorted by dept then name
----------------------------------------------------------------
  result: [('eng', 'Ann'), ('eng', 'Bob'), ('eng', 'Cara'), ('sales', 'Ann'), ('sales', 'Bob')]
  eng    names ['Ann', 'Bob', 'Cara']  ordered=True
  sales  names ['Ann', 'Bob']  ordered=True
```

Every department is grouped and every department's names are ascending — the two-pass sort did its job because the primary pass left the name order intact. Now the unstable primary pass:

```text filename=sortstable.py --unstable
UNSTABLE — sorted by dept then name
----------------------------------------------------------------
  result: [('eng', 'Cara'), ('eng', 'Bob'), ('eng', 'Ann'), ('sales', 'Bob'), ('sales', 'Ann')]
  eng    names ['Cara', 'Bob', 'Ann']  ordered=False
  sales  names ['Bob', 'Ann']  ordered=False
```

The departments are still perfectly grouped — eng before sales — but the names inside each are reversed. The unstable sort reordered the tied-department records, discarding the name order the first pass built. Same primary order, wrecked secondary order.

<svg role="img" aria-label="The eng group after the first pass has names Ann, Bob, Cara in order. After a stable primary sort it stays Ann, Bob, Cara. After an unstable primary sort it becomes Cara, Bob, Ann, reversed." viewBox="0 0 440 160">
<rect x="0" y="0" width="440" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">the eng group's names through the primary sort</text>
<text x="20" y="52" fill="var(--muted)" font-size="10">after pass 1 (by name)</text>
<text x="250" y="52" fill="var(--s2)" font-size="11">Ann &#183; Bob &#183; Cara</text>
<text x="20" y="90" fill="var(--muted)" font-size="10">stable primary sort</text>
<text x="250" y="90" fill="var(--s2)" font-size="11">Ann &#183; Bob &#183; Cara &#10003;</text>
<text x="20" y="128" fill="var(--muted)" font-size="10">unstable primary sort</text>
<text x="250" y="128" fill="var(--s1)" font-size="11">Cara &#183; Bob &#183; Ann &#10007;</text>
</svg>
^ The stable sort leaves the group's names exactly as the first pass ordered them; the unstable sort reorders the ties, and the carefully built name order is gone.

## Build

The self-test isolates what stays right and what breaks: both sort the departments correctly, only the stable sort keeps the names ordered within a department.

```python filename=modules/teaching-and-portability/code/sortstable-inter-01/sortstable.py:96-102 COMPLETE
    st_groups = groups_in_order(st, primary, secondary)
    stable_keeps_secondary = all(ok for _names, ok in st_groups.values())
    print("  stable sort keeps every group's secondary key in order = %s (%s)" % (stable_keeps_secondary, {k: n for k, (n, _o) in st_groups.items()}))

    un_groups = groups_in_order(un, primary, secondary)
    unstable_breaks_secondary = any(not ok for _names, ok in un_groups.values())
    print("  unstable sort breaks some group's secondary order = %s (%s)" % (unstable_breaks_secondary, {k: n for k, (n, _o) in un_groups.items()}))
```

```text filename=sortstable.py --check
SELF-TEST — both order the primary key correctly, but only the stable sort keeps each group's secondary key in order
----------------------------------------------------------------------------------------------------------------
  both put the primary key in correct order = True
  stable sort keeps every group's secondary key in order = True ({'eng': ['Ann', 'Bob', 'Cara'], 'sales': ['Ann', 'Bob']})
  unstable sort breaks some group's secondary order = True ({'eng': ['Cara', 'Bob', 'Ann'], 'sales': ['Bob', 'Ann']})
  same primary order, different tie arrangement (the invisible part) = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  both_primary_sorted=True  stable_keeps_secondary=True  unstable_breaks_secondary=True  same_primary_diff_ties=True
```

<svg role="img" aria-label="A summary. Both sorts: primary key correct. Stable: secondary order kept. Unstable: secondary order scrambled. The difference is only in the ties." viewBox="0 0 440 140">
<rect x="0" y="0" width="440" height="140" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">what each sort gets right and wrong</text>
<text x="170" y="46" fill="var(--muted)" font-size="10">primary order</text>
<text x="330" y="46" fill="var(--muted)" font-size="10">order within ties</text>
<text x="20" y="76" fill="var(--s2)" font-size="11">stable</text>
<text x="185" y="76" fill="var(--s2)" font-size="10">&#10003;</text>
<text x="360" y="76" fill="var(--s2)" font-size="10">&#10003;</text>
<text x="20" y="104" fill="var(--s1)" font-size="11">unstable</text>
<text x="185" y="104" fill="var(--s2)" font-size="10">&#10003;</text>
<text x="360" y="104" fill="var(--s1)" font-size="10">&#10007; scrambled</text>
</svg>
^ The two sorts agree on the visible column — the primary order — and differ only on the ties, which is the one column a glance skips.

**same_primary_diff_ties being True is the whole hazard: the two outputs match on the primary key, so nothing at the top level flags the bug, and only the tie order — what you used two passes to control — differs.**

## Definition of done

You can define a stable sort precisely — it preserves the input order of equal-key records — and say why the two-pass technique depends on the second pass being stable.

You can trace why an unstable primary pass still sorts the primary key correctly while scrambling the secondary order, and why that partial correctness is what makes the bug hard to spot.

You can name the two fixes — use a sort guaranteed stable, or sort once by a compound (primary, secondary) key — and say when you would reach for each.

You can name at least one environment whose sort is guaranteed stable and one whose is not, because "sort twice" is portable only where stability is guaranteed.

## Boss fight

A report sorts a list of orders by customer, then within each customer by date, using two passes. It looks right in your tests and ships. A colleague ports the report to another language by translating the two sort calls line for line, and now the dates within a customer come out jumbled — but only sometimes, and only for customers with several orders.

First: explain why the ported version breaks and the original did not, with reference to a property that differs between the two languages' default sorts. Why "only for customers with several orders"?

Then: the colleague's first instinct is to re-sort the jumbled dates in a third pass. Explain why adding passes is the wrong direction and can reintroduce the same class of bug, and give the two clean fixes — one that keeps two passes, one that uses a single sort.

Finally: the single-sort fix uses a compound key. For sorting by customer ascending then date descending, a naive tuple key does not work directly. Describe how you build a compound key that sorts one field up and the other down, and why that is more robust than relying on stability across a mix of ascending and descending keys.

## External resources

Language sort documentation states stability explicitly: Python's list.sort and sorted are guaranteed stable, Java's Arrays.sort is stable for objects but not primitives, and the ECMAScript spec has required Array.prototype.sort to be stable only since 2019 — the exact portability surface this module warns about.

Any algorithms text's comparison of sorting methods marks each as stable or not (merge sort stable, heapsort and typical quicksort not), which is the underlying reason a language's choice of sort determines whether the two-pass technique is safe.
