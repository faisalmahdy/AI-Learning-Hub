---
id: nancompare-inter-01
title: Test for NaN with isnan, never with equality — not-a-number does not equal itself, so every comparison silently breaks on it
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A missing or undefined numeric value often arrives as NaN — the IEEE-754 float for "not a number", produced by 0.0/0.0, the log of a negative, a failed parse, or a gap in a dataset. NaN has one property that violates the intuition every other value obeys: it does not equal itself. nan == nan is False, nan != nan is True, and every ordered comparison with it (<, <=, >, >=) is also False, because NaN is unordered with respect to everything including itself. This is the standard, and it is deliberate — an undefined result should not compare equal to another undefined result — but it means any operation built on equality or ordering does the wrong thing silently the moment a NaN is present. Four everyday operations break: detecting the missing value by equality fails because comparing to a NaN sentinel never matches, so the NaN slips through; sorting fails because sort relies on pairwise comparisons that are all False against NaN, so the "sorted" list comes back not actually ordered; deduplication and membership tests fail for the same reason; and arithmetic propagates, so any sum, mean, min, or max including a NaN returns NaN, letting one gap contaminate the whole aggregate. The portable fix is the purpose-built test: math.isnan(x), or the equivalent x != x, true for exactly one kind of value — NaN — precisely because NaN is the only value not equal to itself. On a fixture of readings 2, 3, missing, 1, equality-based detection finds zero NaNs (there is one), sorting returns [2, 3, nan, 1] with the 1 stranded after the 3, and the naive sum is NaN — while isnan finds the one gap and the clean mean is (2+3+1)/3 = 2.0.
eli5: Imagine a box that is supposed to hold a number but is empty, and it has a strange rule: if you ask "are you the same as yourself?" it says no. That sounds silly, but it breaks a lot of things. If you go through a shelf of boxes asking "are you the empty one?" by comparing each to another empty box, none of them ever say yes — so you never find the empty box. If you try to sort the boxes smallest to largest, the empty one refuses to be bigger or smaller than anything, so the line ends up jumbled. And if you add up all the numbers, the empty box turns the whole total into "nothing" too. The fix is to stop asking "are you equal to empty?" and instead ask the one question that works: "are you not equal to yourself?" — because only the empty box says yes to that. Find the empties that way, set them aside, and then sort and add the real numbers.
---

## Why this module

NaN is the value that breaks the one assumption you never think to question: that a thing equals itself. Every other value in a program obeys `x == x`. NaN does not, and because so much code is quietly built on equality and ordering — filtering, sorting, deduplicating, comparing — a single NaN flowing through a pipeline produces wrong results without raising an error. It is a portability and correctness trap that spans every language with IEEE-754 floats, which is nearly all of them, and it is worth seeing precisely because the failures are silent: no exception, no crash, just a filter that misses, a sort that is not sorted, and an average that is NaN.

The behavior is not a bug. NaN represents an undefined or missing result, and the standard deliberately makes it unordered with everything, itself included: two undefined results should not be declared equal, and an undefined value is neither less than nor greater than a real one. So `nan == nan` is False, `nan != nan` is True, and `nan < x`, `nan > x`, `nan <= x`, `nan >= x` are all False for every x. That rule is coherent, and it is exactly what breaks equality-based detection, comparison-based sorting, and every aggregate.

This module runs the same four-element reading list through the naive equality-and-ordering operations and through the isnan-based ones, and shows each naive result being silently wrong.

**Detect NaN with a dedicated isnan test (or x != x), never by equality or ordering, and remove or handle it before sorting or aggregating, because NaN does not equal itself and is unordered with everything — so equality-based detection misses it, comparison-based sorting misplaces it, and any arithmetic including it returns NaN, each failing silently.**

## Concepts

The fixture is four sensor readings with one gap. It is stored as raw JSON with `null` marking the missing reading, and the loader turns that gap into `float('nan')` — which is how a real pipeline ends up with a NaN in a numeric array.

```json filename=modules/teaching-and-portability/code/nancompare-inter-01/nancompare.json:3 COMPLETE
  "readings_raw": [2.0, 3.0, null, 1.0]
```

The loader maps the null to NaN. From there, the two detection strategies diverge on one line each. The naive one compares every element to a NaN sentinel — which can never match, because the comparison is always False. The correct one calls `math.isnan`.

```python filename=modules/teaching-and-portability/code/nancompare-inter-01/nancompare.py:57-72 COMPLETE
def readings(data):
    """Turn the raw list (null marks the missing value) into floats, with the gap as NaN."""
    return [float("nan") if x is None else float(x) for x in data["readings_raw"]]


def detect_by_equality(vals):
    """Naive: try to find the missing value by comparing each element to a NaN sentinel."""
    sentinel = float("nan")
    return [i for i, x in enumerate(vals) if x == sentinel]


def detect_by_isnan(vals):
    """Correct: test each element with math.isnan."""
    return [i for i, x in enumerate(vals) if math.isnan(x)]
```

The other two failures are ordering and arithmetic. A monotonic check reveals whether a "sorted" list is actually ordered — with a NaN present it never is, because the pairwise comparison at the NaN is False. And cleaning is just filtering by `math.isnan` before computing.

```python filename=modules/teaching-and-portability/code/nancompare-inter-01/nancompare.py:75-88 COMPLETE
def is_monotonic(vals):
    """Whether the list is actually non-decreasing (adjacent pairs in order)."""
    return all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))


def clean(vals):
    """Drop the NaNs, keeping the real readings."""
    return [x for x in vals if not math.isnan(x)]


def mean(vals):
    return sum(vals) / len(vals)
```

<svg role="img" aria-label="A NaN box with four arrows out, each labeled False: equals-itself, less-than, greater-than, and equality-detection, versus one isnan arrow labeled True" viewBox="0 0 320 150">
  <rect x="130" y="60" width="60" height="30" fill="none" stroke="var(--ink)" stroke-width="2"/>
  <text x="146" y="80" font-size="12" fill="var(--ink)">NaN</text>
  <text x="40" y="24" font-size="9" fill="var(--s2)">nan == nan → False</text>
  <text x="40" y="40" font-size="9" fill="var(--s2)">nan &lt; x → False</text>
  <text x="200" y="24" font-size="9" fill="var(--s2)">nan &gt; x → False</text>
  <text x="200" y="40" font-size="9" fill="var(--s2)">x == nan → False</text>
  <line x1="150" y1="60" x2="110" y2="44" stroke="var(--s2)" stroke-width="1"/>
  <line x1="170" y1="60" x2="240" y2="44" stroke="var(--s2)" stroke-width="1"/>
  <text x="90" y="128" font-size="10" fill="var(--s1)">isnan(nan) → True</text>
  <text x="90" y="142" font-size="10" fill="var(--s1)">nan != nan → True</text>
  <line x1="150" y1="90" x2="135" y2="118" stroke="var(--s1)" stroke-width="1.5"/>
</svg>
^ Every equality and ordering test against NaN returns False, so anything built on them fails silently. Only the two purpose-built tests — isnan, and the equivalent nan != nan — return True, which is why detection must use them.

**NaN's single broken axiom, that it does not equal itself, is not one bug but the root of four: equality detection, sorting, deduplication, and aggregation all rest on comparisons that NaN makes False.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the data-cleaning step of a metrics pipeline, reduced to four readings so every comparison and aggregate is checkable by hand.

Run `--naive` to see the equality-and-ordering operations, each silently wrong.

```text filename=nancompare.py --naive
  readings           = [2, 3, nan, 1]
  nan == nan         = False ; nan != nan = True
  detect by equality = [] indices (x == nan never matches -- misses the gap)
  sorted(readings)   = [2, 3, nan, 1]  monotonic? False
  sum(readings)      = nan (one NaN contaminates the whole aggregate)
```

Three failures, no errors. Equality detection returns an empty list — it found zero NaNs when there is plainly one, because `x == nan` is False for every x including the NaN itself. The sort is the vivid one: `sorted([2, 3, nan, 1])` comes back as `[2, 3, nan, 1]` — the 1 is stranded at the very end, after the 3, because the sort's comparisons involving the NaN were all False and it could not move anything past it. The list is labeled sorted and is not. And the sum is NaN: one missing reading turned the entire aggregate into NaN.

Now `--clean` uses the purpose-built test.

```text filename=nancompare.py --clean
  detect by isnan = [2] indices (finds the gap)
  x != x for each = [False, False, True, False] (true only for NaN)
  clean readings  = [2, 3, 1]
  mean(clean)     = 2 = (2+3+1)/3
```

`math.isnan` finds the gap at index 2. The `x != x` column is the same test without importing anything — True at exactly one position, the NaN, because NaN is the only value not equal to itself. Filter those out and the clean readings are [2, 3, 1], whose mean is (2+3+1)/3 = 2.0 — the correct answer, recovered by detecting and removing the NaN before aggregating.

<svg role="img" aria-label="The list 2, 3, NaN, 1 after sorting still reads 2, 3, NaN, 1, with an arrow showing the 1 stranded at the end because comparisons with NaN are all False" viewBox="0 0 320 110">
  <text x="10" y="22" font-size="9" fill="var(--muted)">sorted([2, 3, nan, 1]) =</text>
  <rect x="30" y="34" width="34" height="26" fill="var(--s1)"/>
  <text x="43" y="51" font-size="11" fill="var(--panel)">2</text>
  <rect x="68" y="34" width="34" height="26" fill="var(--s1)"/>
  <text x="81" y="51" font-size="11" fill="var(--panel)">3</text>
  <rect x="106" y="34" width="42" height="26" fill="var(--muted)"/>
  <text x="114" y="51" font-size="11" fill="var(--panel)">nan</text>
  <rect x="152" y="34" width="34" height="26" fill="var(--s2)"/>
  <text x="165" y="51" font-size="11" fill="var(--panel)">1</text>
  <path d="M 169 34 Q 130 10 90 32" fill="none" stroke="var(--s2)" stroke-width="1.3"/>
  <text x="80" y="82" font-size="8.5" fill="var(--s2)">the 1 should be first, but no comparison could move it</text>
  <text x="80" y="96" font-size="8.5" fill="var(--muted)">past the NaN (every nan comparison is False)</text>
</svg>
^ A correct sort would put the 1 first; instead it is stranded last, after the 3. The NaN acts as a wall the sort cannot compare across, so nothing moves past it — the list is labeled sorted and is visibly not.

**The naive run finds zero NaNs, sorts the 1 to the wrong end, and sums to NaN — all without an error; the isnan run finds the one gap and computes the correct mean.**

## Build

The self-test asserts the defining property and each of its consequences, so the failure is documented, not just the fix. It confirms NaN is unequal to itself, that equality detection misses it while isnan finds exactly one, that the sort is not monotonic, and that the sum is contaminated.

```python filename=modules/teaching-and-portability/code/nancompare-inter-01/nancompare.py:110-124 COMPLETE
    nan_not_equal_itself = float("nan") != float("nan")
    print("  NaN does not equal itself (nan != nan) = %s" % nan_not_equal_itself)

    equality_misses_nan = len(detect_by_equality(vals)) == 0
    print("  equality-based detection misses the NaN = %s (found %d, there is 1)" % (equality_misses_nan, len(detect_by_equality(vals))))

    isnan_finds_one = len(detect_by_isnan(vals)) == 1
    print("  isnan-based detection finds exactly the one NaN = %s (index %s)" % (isnan_finds_one, detect_by_isnan(vals)))

    sort_not_monotonic = not is_monotonic(sorted(vals))
    print("  comparison-based sort is NOT actually ordered = %s (%s)" % (sort_not_monotonic, show(sorted(vals))))

    sum_contaminated = math.isnan(sum(vals))
    print("  a sum including the NaN is NaN = %s (one gap contaminates the aggregate)" % sum_contaminated)
```

<svg role="img" aria-label="Two rows: naive operations all marked wrong (detection empty, sort jumbled, sum NaN), clean operations all correct (one NaN found, values filtered, mean 2)" viewBox="0 0 330 130">
  <text x="10" y="20" font-size="9" fill="var(--muted)">naive (equality / ordering)</text>
  <rect x="10" y="28" width="90" height="18" fill="var(--s2)"/>
  <text x="16" y="41" font-size="8" fill="var(--panel)">detect: [] (missed)</text>
  <rect x="104" y="28" width="110" height="18" fill="var(--s2)"/>
  <text x="110" y="41" font-size="8" fill="var(--panel)">sort: [2,3,nan,1]</text>
  <rect x="218" y="28" width="80" height="18" fill="var(--s2)"/>
  <text x="224" y="41" font-size="8" fill="var(--panel)">sum: nan</text>
  <text x="10" y="76" font-size="9" fill="var(--muted)">clean (isnan)</text>
  <rect x="10" y="84" width="90" height="18" fill="var(--s1)"/>
  <text x="16" y="97" font-size="8" fill="var(--panel)">detect: [2] (found)</text>
  <rect x="104" y="84" width="110" height="18" fill="var(--s1)"/>
  <text x="110" y="97" font-size="8" fill="var(--panel)">clean: [2,3,1]</text>
  <rect x="218" y="84" width="80" height="18" fill="var(--s1)"/>
  <text x="224" y="97" font-size="8" fill="var(--panel)">mean: 2.0</text>
</svg>
^ The same three operations, both ways: equality/ordering miss the NaN, jumble the sort, and poison the sum; isnan finds the one gap so the filtered values sort and average correctly.

Running the check confirms every clause, including that the x != x trick flags exactly the NaNs.

```text filename=nancompare.py --check
  NaN does not equal itself (nan != nan) = True
  equality-based detection misses the NaN = True (found 0, there is 1)
  isnan-based detection finds exactly the one NaN = True (index [2])
  comparison-based sort is NOT actually ordered = True ([2, 3, nan, 1])
  a sum including the NaN is NaN = True (one gap contaminates the aggregate)
  the x != x trick flags exactly the NaNs = True
  cleaning then averaging gives the correct mean = True (2 == 2.0)
```

**The check documents the whole failure surface — detection, ordering, arithmetic — and shows isnan closing each one, so the fix is tied to the exact property that breaks the naive code.**

## Definition of done

Two properties close it. The equivalence of `x != x` and `math.isnan` must hold across the whole list — that is what makes the portable, import-free NaN test trustworthy — and cleaning then averaging must give the correct 2.0, proving the aggregate is recoverable once the NaN is removed rather than merely ignored.

```python filename=modules/teaching-and-portability/code/nancompare-inter-01/nancompare.py:126-132 COMPLETE
    xnex_only_nan = [x != x for x in vals] == [math.isnan(x) for x in vals]
    print("  the x != x trick flags exactly the NaNs = %s" % xnex_only_nan)

    clean_mean_correct = abs(mean(clean(vals)) - 2.0) < 1e-9
    print("  cleaning then averaging gives the correct mean = %s (%g == 2.0)" % (clean_mean_correct, mean(clean(vals))))
```

One boundary keeps the tool honest. NaN is not the same as a signaling exception, and it is not the same as `None` — a language may also have `None`/`null` for missing, which does equal itself and does raise on arithmetic, so you cannot detect both with the same test. And the sort behavior is implementation-defined: some sorts leave NaN where the comparisons happen to strand it (as here), others push all NaNs to one end, and a few raise; you cannot rely on any particular placement, only on the fact that a NaN-containing sort is not trustworthy. The single portable rule that survives all of this is: never compare to NaN to reason about it — test with isnan (or x != x), decide explicitly whether the missing value should be dropped, imputed, or propagated, and only then sort or aggregate.

**Done means the x != x test matches isnan exactly and the cleaned mean is provably correct — so the recovery rests on detecting NaN with the one test that works, never on any assumption about how it compares or sorts.**

## Boss fight

A data pipeline computes the median latency per endpoint and alerts when it exceeds a threshold. One endpoint occasionally records a NaN latency (a timing that failed to complete), and ever since, its alerts have behaved strangely: sometimes the median comes out as a wildly wrong value, sometimes the endpoint silently drops out of the report entirely, and the on-call engineer cannot reproduce it. Given what you know about NaN, what are the two distinct failures happening, and what is the one change that fixes both?

The two failures both trace to NaN breaking comparisons, but in different operations. The wildly-wrong median comes from sorting: the median is computed by sorting the latencies and taking the middle, but a NaN in the list makes the sort's comparisons False, so the "sorted" list is not actually ordered and the middle element is not the true median — it is whatever value the NaN stranded in the center. The endpoint silently dropping out comes from a downstream equality or filtering step: something compares values to detect or deduplicate them, and because nothing equals the NaN (and the NaN equals nothing), the endpoint's row fails a match it should pass and is excluded, or an aggregate over it returns NaN and gets filtered as invalid. The single change that fixes both is to detect NaNs explicitly with isnan at ingestion and decide their fate before any sort, compare, or aggregate — drop them as failed timings (and note the drop count), or treat them as a distinct "incomplete" category — rather than letting them flow into operations that assume every value equals itself. Once no NaN reaches the sort or the equality check, the median is computed on real latencies and the endpoint stops vanishing.

## External resources

The IEEE 754 standard's treatment of NaN, summarized in the Wikipedia "NaN" article — the authoritative source for why NaN is unordered and unequal to itself, and the distinction between quiet and signaling NaNs that underlies this behavior in every conforming language.

The NumPy documentation on handling NaN (np.isnan, np.nanmean, np.nansum and the nan-aware reductions) — the production answer to exactly this problem at array scale, showing how mature numeric libraries provide separate NaN-detecting and NaN-skipping operations precisely because ordinary comparison and aggregation cannot handle NaN.
