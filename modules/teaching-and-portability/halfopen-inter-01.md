---
id: halfopen-inter-01
title: Represent a range as half-open [start, end) — closed inclusive ranges double-count the shared boundary and overrun the end
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A range needs two numbers, a start and an end, and the only real decision is whether the end is part of it. A closed interval [a, b] includes both ends; a half-open interval [a, b) includes the start and excludes the end. That single difference decides whether ranges compose cleanly. The trouble with closed intervals appears the moment two are adjacent: chunk the indices 0..29 into tens as [0, 10] and [10, 20] and both chunks contain the index 10 — it is the end of the first and the start of the second, and a closed interval includes both, so 10 is in two chunks at once. Every boundary is double-counted, each chunk's size comes out as 11 instead of 10 (end − start + 1), and the last chunk [20, 30] reaches index 30, one past the last real item. Half-open intervals compose by construction: [0, 10) and [10, 20) meet exactly at 10, which belongs only to the second, so every index is in exactly one chunk, the chunks cover exactly 0..29 with no gap or overrun, and the size is just end − start = 10. This is why Python's range, list slicing, and almost every well-designed range API exclude the upper bound. The rule: represent ranges half-open, so adjacent ranges tile a whole without gaps or double-counting, the count is end − start with no fencepost correction, and chunk i is simply [i·size, (i+1)·size).
eli5: Think about a fence with posts and the sections of fence between them. If someone asks "how many sections are there from post 0 to post 10," the answer is 10 sections, but there are 11 posts — the classic fencepost mix-up. Ranges have the same trap. If you say a chunk is "from 0 to 10, both ends included," and the next chunk is "from 10 to 20," then the number 10 got counted in both chunks, like a fence post claimed by two sections. The fix is to say each chunk goes "from its start up to but not including its end," so 10 belongs to exactly one chunk. Then the chunks line up perfectly edge to edge with nothing shared and nothing missed, and counting is easy: end minus start.
---

## Why this module

Splitting something into ranges is one of the most common things code does — paginate results, chunk an array, slice a time window, partition work across threads. It looks trivial, and it is where off-by-one bugs breed, because the trivial-looking choice of whether a range includes its endpoint quietly decides whether your ranges fit together.

Write ranges the natural-language way — "items 1 through 10, then 11 through 20" — and you have chosen closed, inclusive intervals, and you have signed up for a lifetime of minus-ones. Adjacent inclusive ranges share their boundary, so either you subtract one everywhere to avoid overlap, or you double-count the seams. Every one of those corrections is a place to get the fencepost wrong.

This module chunks thirty items into three tens both ways and measures the damage. The closed version double-counts the indices 10 and 20, reports each chunk as size 11, and reaches a nonexistent index 30. The half-open version puts every index in exactly one chunk, covers exactly 0..29, and gives each chunk size 10 with no correction. Then it shows why half-open composes and closed does not, and why every good range API chose half-open.

**Whether a range includes its endpoint is not a stylistic detail but the thing that decides whether adjacent ranges tile cleanly — and closed ranges do not, which is why off-by-one bugs cluster wherever ranges meet.**

## Concepts

A closed interval [a, b] is the set of values from a to b with both ends included. A half-open interval [a, b) is the same but with b excluded — a up to, but not including, b. For integers, [0, 10] is the eleven values 0 through 10, while [0, 10) is the ten values 0 through 9.

The difference is invisible for a single range and decisive for adjacent ones. Put two closed ranges end to end — [0, 10] and [10, 20] — and their shared endpoint 10 is in both, because "included at both ends" means the first range's end and the second range's start are the same element, claimed twice. To make closed ranges partition without overlap you must offset by one — [0, 9], [10, 19], [20, 29] — and now the boundaries no longer line up numerically with the chunk size, so every computation of a chunk's start and end carries a minus-one that is easy to drop or double.

Half-open ranges remove the choice. [0, 10) and [10, 20) meet at 10, and 10 belongs only to the second range because the first excludes its end. Adjacent half-open ranges share a boundary value that lives in exactly one of them, so they partition the whole with nothing double-counted and nothing skipped. The boundary is written the same way it is computed: chunk i is [i·size, (i+1)·size), no correction.

The arithmetic falls out clean. The number of integers in [a, b) is exactly b − a — no plus-one — so a chunk of size 10 is [start, start+10), the empty range is [a, a), and the length of a slice is the difference of its bounds. This is why Python's range(a, b), list slicing s[a:b], and most range-based APIs are end-exclusive: half-open is the representation in which ranges compose and count without fencepost corrections.

<svg role="img" aria-label="A number line around the boundary index 10. Under closed intervals, chunk 0 spans 0 to 10 inclusive and chunk 1 spans 10 to 20 inclusive, and the index 10 is marked as belonging to both. Under half-open, chunk 0 spans 0 up to but not including 10 and chunk 1 starts at 10, so 10 belongs only to chunk 1." viewBox="0 0 640 210">
<text x="60" y="30" fill="var(--ink)" font-size="12">closed [0,10] and [10,20]</text>
<line x1="60" y1="60" x2="300" y2="60" stroke="var(--s2)" stroke-width="3"/>
<line x1="300" y1="72" x2="540" y2="72" stroke="var(--ink)" stroke-width="3"/>
<circle cx="300" cy="60" r="5" fill="var(--s2)"/>
<circle cx="300" cy="72" r="5" fill="var(--ink)"/>
<text x="300" y="98" fill="var(--s2)" font-size="10" text-anchor="middle">10 is in BOTH chunks</text>
<text x="120" y="52" fill="var(--muted)" font-size="9" text-anchor="middle">chunk 0</text>
<text x="440" y="88" fill="var(--muted)" font-size="9" text-anchor="middle">chunk 1</text>
<text x="60" y="140" fill="var(--ink)" font-size="12">half-open [0,10) and [10,20)</text>
<line x1="60" y1="170" x2="295" y2="170" stroke="var(--s1)" stroke-width="3"/>
<line x1="300" y1="170" x2="540" y2="170" stroke="var(--ink)" stroke-width="3"/>
<circle cx="300" cy="170" r="5" fill="var(--ink)"/>
<text x="300" y="196" fill="var(--s1)" font-size="10" text-anchor="middle">10 is in chunk 1 only</text>
</svg>
^ Closed ranges share the boundary index between two chunks; half-open ranges give it to exactly one, so they meet without overlapping.

**A closed interval includes both ends, so adjacent ones collide at the boundary and need a minus-one to separate; a half-open interval excludes its end, so adjacent ones tile automatically and the count is just end minus start.**

## Worked example

The fixture is thirty items (indices 0..29) chunked into tens.

```json filename=modules/teaching-and-portability/code/halfopen-inter-01/halfopen.json:3-4 COMPLETE
  "n_items": 30,
  "chunk_size": 10
```

The chunk boundaries are the same numbers either way — the scheme is only how membership reads them.

```python filename=modules/teaching-and-portability/code/halfopen-inter-01/halfopen.py:30-32 COMPLETE
def make_chunks(n_items, chunk_size):
    """The (start, end) pairs, chunk i = (i*size, (i+1)*size) -- the boundaries themselves are scheme-neutral."""
    return [(i, i + chunk_size) for i in range(0, n_items, chunk_size)]
```

Closed membership includes the end; half-open excludes it.

```python filename=modules/teaching-and-portability/code/halfopen-inter-01/halfopen.py:35-38 COMPLETE
def contains_closed(chunk, x):
    """Closed interval [start, end]: the end index is included."""
    start, end = chunk
    return start <= x <= end
```

```python filename=modules/teaching-and-portability/code/halfopen-inter-01/halfopen.py:41-44 COMPLETE
def contains_halfopen(chunk, x):
    """Half-open interval [start, end): the end index is excluded."""
    start, end = chunk
    return start <= x < end
```

Under closed intervals the boundaries land in two chunks, the sizes come out wrong, and the last chunk overruns.

```text filename=halfopen.py --closed
CLOSED — inclusive ranges [start, end]
------------------------------------------------------------
  chunks: ['[0, 10]', '[10, 20]', '[20, 30]']
  indices in TWO chunks (double-counted): [10, 20]
  chunk sizes (end - start + 1): [11, 11, 11]
  overruns to index past the last item (29): [30]
------------------------------------------------------------
  the boundaries belong to two chunks and the last chunk reaches a nonexistent index
```

Indices 10 and 20 are each in two chunks, every chunk claims 11 items instead of 10, and chunk [20, 30] reaches index 30 — one past the last real item at 29. The half-open version is clean.

```text filename=halfopen.py --halfopen
HALF-OPEN — end-exclusive ranges [start, end)
------------------------------------------------------------
  chunks: ['[0, 10)', '[10, 20)', '[20, 30)']
  indices in two chunks: []
  chunk sizes (end - start): [10, 10, 10]
  covers exactly 0..29: True
------------------------------------------------------------
  every index is in exactly one chunk and the size is just end minus start
```

No index is in two chunks, each size is exactly end − start = 10, and the chunks cover exactly 0..29 with nothing past the end. The figure shows the two tilings across the whole range.

<svg role="img" aria-label="Two rows tiling the indices 0 to 30. The closed row shows three bars overlapping at 10 and 20 and extending to 30 past the data. The half-open row shows three bars meeting exactly at 10 and 20 and ending at 30, covering 0 to 29." viewBox="0 0 640 190">
<text x="40" y="30" fill="var(--ink)" font-size="11">closed: overlaps at 10, 20; overruns to 30</text>
<rect x="40" y="44" width="200" height="24" fill="var(--s2)" opacity="0.5" stroke="var(--line)"/>
<rect x="220" y="50" width="200" height="24" fill="var(--s2)" opacity="0.5" stroke="var(--line)"/>
<rect x="400" y="44" width="220" height="24" fill="var(--s2)" opacity="0.5" stroke="var(--line)"/>
<text x="230" y="90" fill="var(--s2)" font-size="9" text-anchor="middle">overlap</text>
<text x="410" y="90" fill="var(--s2)" font-size="9" text-anchor="middle">overlap</text>
<text x="600" y="90" fill="var(--s2)" font-size="9" text-anchor="middle">past 29</text>
<text x="40" y="128" fill="var(--ink)" font-size="11">half-open: tiles 0..29 exactly</text>
<rect x="40" y="142" width="193" height="24" fill="var(--s1)" opacity="0.5" stroke="var(--line)"/>
<rect x="235" y="142" width="193" height="24" fill="var(--s1)" opacity="0.5" stroke="var(--line)"/>
<rect x="430" y="142" width="193" height="24" fill="var(--s1)" opacity="0.5" stroke="var(--line)"/>
<text x="136" y="182" fill="var(--muted)" font-size="9" text-anchor="middle">[0,10)</text>
<text x="331" y="182" fill="var(--muted)" font-size="9" text-anchor="middle">[10,20)</text>
<text x="526" y="182" fill="var(--muted)" font-size="9" text-anchor="middle">[20,30)</text>
</svg>
^ Closed chunks overlap at each boundary and run past the data; half-open chunks meet edge to edge and stop exactly at the end.

**The closed chunks reporting size 11 and reaching index 30 are the same bug seen twice — the included endpoint is counted in the size and exists past the data — and both vanish when the endpoint is excluded.**

## Build

The self-test pins both failures of the closed scheme and both successes of the half-open one: closed double-counts a boundary and overruns the end, while half-open puts every index in exactly one chunk.

```python filename=modules/teaching-and-portability/code/halfopen-inter-01/halfopen.py:95-103 COMPLETE
    closed_multi = [x for x in universe if len(chunks_of(chunks, x, contains_closed)) > 1]
    closed_double_counts = len(closed_multi) > 0
    print("  closed intervals put a boundary index in two chunks = %s (%s)" % (closed_double_counts, closed_multi))

    closed_overruns = any(contains_closed(c, n) for c in chunks)
    print("  a closed chunk reaches the nonexistent index %d = %s" % (n, closed_overruns))

    halfopen_partitions = all(len(chunks_of(chunks, x, contains_halfopen)) == 1 for x in universe)
    print("  half-open intervals put every index in exactly one chunk = %s" % halfopen_partitions)
```

The remaining flags confirm half-open covers exactly 0..29 and its size is end − start. All five pass.

```text filename=halfopen.py --check
SELF-TEST — closed intervals double-count boundaries and overrun the end, while half-open intervals partition the items exactly
----------------------------------------------------------------------------------------------------------------
  closed intervals put a boundary index in two chunks = True ([10, 20])
  a closed chunk reaches the nonexistent index 30 = True
  half-open intervals put every index in exactly one chunk = True
  half-open chunks cover exactly 0..29, no gap or overrun = True
  a half-open chunk's size is end minus start = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  closed_double_counts=True  closed_overruns=True  halfopen_partitions=True  halfopen_covers_exactly=True  halfopen_size_is_diff=True
```

**"Every index in exactly one chunk" is the property that makes a partition, and only the half-open scheme has it here without any minus-one — the closed scheme would need one on every boundary to get there.**

## Definition of done

You are done when ranges in your code are half-open by default — start included, end excluded — so adjacent ranges tile, the size is end − start, and you never add a fencepost correction to make chunks line up.

The habit is to write every range as [start, end) and to compute with that in mind: a chunk of size s starting at i is [i, i + s); the count of items is end − start; the empty range is [a, a); splitting [a, c) at b gives [a, b) and [b, c) with no shared element. Most languages already lean this way — Python's range and slicing, Go and Rust slice bounds, C++ iterator ranges [begin, end) — so following the convention keeps your code consistent with the standard library rather than fighting it. Two cautions. When an external system hands you inclusive bounds — a SQL BETWEEN, a date range "through" a day, an API that documents an inclusive end — convert at the boundary by adding one to the end as you bring it in, and do it once, explicitly, rather than sprinkling minus-ones through the logic. And be careful with the inclusive end for continuous or maximum-valued ranges: a half-open [a, b) cannot represent a range whose last element is the largest possible value, which is one of the few places an inclusive end is genuinely needed and worth calling out.

<svg role="img" aria-label="A summary of half-open properties: the count of [a,b) is b minus a; chunk i is [i times size, (i plus 1) times size); adjacent ranges [a,b) and [b,c) tile [a,c); Python range and slicing are end-exclusive." viewBox="0 0 640 180">
<rect x="40" y="30" width="260" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="170" y="54" fill="var(--ink)" font-size="11" text-anchor="middle">count of [a, b) = b − a</text>
<rect x="340" y="30" width="260" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="470" y="54" fill="var(--ink)" font-size="11" text-anchor="middle">chunk i = [i·size, (i+1)·size)</text>
<rect x="40" y="90" width="260" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="170" y="114" fill="var(--ink)" font-size="11" text-anchor="middle">[a, b) + [b, c) tiles [a, c)</text>
<rect x="340" y="90" width="260" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="470" y="114" fill="var(--ink)" font-size="11" text-anchor="middle">range / slicing are end-exclusive</text>
<text x="320" y="160" fill="var(--muted)" font-size="10" text-anchor="middle">half-open ranges compose and count with no fencepost correction</text>
</svg>
^ The half-open convention makes counting, chunking, and splitting fencepost-free, and matches the standard library's own range semantics.

**Half-open is the representation in which ranges add up: the count is a subtraction, chunks are the plain multiples, and adjacent ranges partition — so making it the default removes the whole class of boundary off-by-ones rather than fixing them one at a time.**

## Boss fight

Your turn: change the item count so the last chunk is partial and watch half-open handle it while closed compounds its error. Set `n_items` to 25, so the chunks are [0,10), [10,20), [20,30) but only indices 0..24 exist. The half-open scheme still partitions the real items — the last chunk simply contributes indices 20..24, and a length computed as min(end, n) − start gives the correct 5 — while the closed scheme now double-counts 10 and 20 and also claims indices 25 through 30 that do not exist, five phantom items on top of the two double-counts. Partial final chunks are where range bugs concentrate, and half-open degrades gracefully there because the end was never a real element to begin with.

Then meet the one case where an inclusive end is the honest choice. Suppose you must represent "all timestamps up to and including the last microsecond of the day," or "all 32-bit integers from 0 to the maximum." A half-open range would need an end one past the last value — one microsecond into the next day, or 2^32 — which may not be representable, or may falsely include a real next element. Here the inclusive end says exactly what you mean and the half-open end cannot. This is the boundary of the rule: half-open is the right default for counting and chunking, where the excluded end is a clean fencepost, but a range whose semantics genuinely reach a maximum value is one of the few places to use a closed end deliberately — and to document that you did, so the next reader does not "fix" it back to half-open and reintroduce the off-by-one.

**Half-open is the default because it makes counting and tiling fencepost-free, but a range that must include a maximum representable value is the honest exception — so choose half-open on purpose and reach for a closed end only where the excluded endpoint cannot be represented.**

## External resources

Dijkstra's note "Why numbering should start at zero" (EWD831) is the classic argument for half-open ranges — it shows [a, b) is the convention that makes the count b − a and avoids off-by-one at both ends.

The Python documentation for range() and for sequence slicing states the end-exclusive semantics directly, and is the most-used example of the convention: range(a, b) and s[a:b] both stop before b.

The C++ standard library's iterator ranges [begin, end) and the STL's half-open convention throughout are the same idea in another ecosystem, and any reference on them explains why past-the-end iterators make the algorithms compose.
