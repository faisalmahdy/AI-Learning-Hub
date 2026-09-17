---
id: mutdefault-inter-01
title: A mutable default argument is created once at def time and shared by every call — so it accumulates instead of resetting
topic: teaching-and-portability
level: intermediate
status: ready
time: 14 min
summary: Python evaluates a function's default argument values once, when the def statement runs, not each time the function is called. For an immutable default like 0 or None that never shows, because you cannot change the value in place. For a mutable default — a list, a dict, a set — it is a trap: the single object created when the function was defined becomes the default for every call that omits the argument, and if the body mutates it, the change persists into the next call. So def add(item, bucket=[]) does not give each call a fresh empty list; it gives every call the same list, which fills up across calls, and the bug surfaces as "why does the second call already contain the first call's data?" — often far from the definition and often only in production where the function is called more than once. The cause is that the default is an attribute of the function object (its __defaults__), fixed at creation, so bucket=[] runs the [] exactly once. The fix is the sentinel: default the argument to None and construct the fresh mutable object inside the body when it is None. On a fixture appending three items one per call, the buggy version returns ['a'], then ['a','b'], then ['a','b','c'] (one shared list, growing), while the fixed version returns ['a'], then ['b'], then ['c'] (a fresh list each time) — and the shared default can be seen mutating in place on the function's __defaults__.
eli5: Imagine a teacher who says "start each student with a blank notebook." If she buys ONE notebook the day she makes the rule and hands that same notebook to every student in turn, the second student opens it and finds the first student's work already inside — not blank at all. That's what happens when you give a Python function a list as its default: the list is made once, when the function is written, and reused for everyone. The fix is to make a brand-new blank notebook inside the function each time someone shows up without one, instead of reusing the single old one.
---

## Why this module

A function that says its argument "defaults to an empty list" reads as a promise that each call starts fresh. Python does not make that promise — it makes the empty list once, at definition, and reuses it forever. The gap between what the signature seems to say and what actually happens is a bug that hides through every test that calls the function once and detonates the first time it is called twice.

Python evaluates a function's default argument values once, at the moment the `def` statement runs, not each time the function is called. For an immutable default like 0 or None that distinction never shows, because you cannot change the value in place. For a mutable default — a list, a dict, a set — it is a trap: the single object created when the function was defined becomes the default for every call that omits the argument, and if the body mutates it (appends to the list, adds to the dict), the change persists into the next call. So `def add(item, bucket=[])` does not give each call a fresh empty list; it gives every call the same list, which fills up across calls. The function that looks like it starts from empty each time is quietly accumulating state between invocations, and the bug surfaces as "why does the second call already contain the first call's data?" — often far from the definition, and often only in production where the function is called more than once.

The cause is that the default value is an attribute of the function object, stored in its `__defaults__`, fixed when the function is created. `bucket=[]` runs the `[]` exactly once and binds that list as the default forever; calling the function without a bucket reuses that same bound list. The fix is the standard sentinel: default the argument to None — an immutable, safe default — and create the fresh mutable object inside the body when the argument is None. Now each call that omits the argument builds its own new list, and the shared-state bug is gone. This module runs the buggy and fixed versions on three appends and shows the accumulation.

**A default argument value is evaluated once at def time and stored on the function, so a mutable default is one object shared by every call that omits it — mutating it accumulates state across calls — and the fix is to default to None and construct the mutable object inside the body.**

## Concepts

**The buggy collector** gives `bucket` a list default. The `[]` runs once when the inner `def` executes, so all calls that omit `bucket` append to that one list.

```python filename=modules/teaching-and-portability/code/mutdefault-inter-01/mutdefault.py:43-48 COMPLETE
def make_buggy():
    """A collector with a MUTABLE default -- the [] is evaluated once at def time and shared by every call."""
    def add(item, bucket=[]):
        bucket.append(item)
        return bucket
    return add
```

**The fixed collector** defaults to None and builds the list inside. None is immutable, so there is nothing to share; each call with no bucket makes its own list.

```python filename=modules/teaching-and-portability/code/mutdefault-inter-01/mutdefault.py:51-58 COMPLETE
def make_fixed():
    """The same collector with the None-sentinel fix -- a fresh list is built inside the body per call."""
    def add(item, bucket=None):
        if bucket is None:
            bucket = []
        bucket.append(item)
        return bucket
    return add
```

<svg role="img" aria-label="A timeline: the def statement runs once and creates the default empty list; then three separate calls all point at that same one list object" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the [] is created ONCE at def; every call shares it</text>
  <rect x="10" y="24" width="80" height="22" fill="none" stroke="var(--s1)"/><text x="16" y="38" fill="var(--muted)" font-size="7">def runs → []</text>
  <rect x="120" y="20" width="40" height="16" fill="var(--s2)"/><text x="126" y="31" fill="var(--panel)" font-size="7">call 1</text>
  <rect x="120" y="52" width="40" height="16" fill="var(--s2)"/><text x="126" y="63" fill="var(--panel)" font-size="7">call 2</text>
  <rect x="120" y="84" width="40" height="16" fill="var(--s2)"/><text x="126" y="95" fill="var(--panel)" font-size="7">call 3</text>
  <rect x="220" y="52" width="60" height="16" fill="var(--s1)"/><text x="226" y="63" fill="var(--panel)" font-size="7">one list</text>
  <line x1="160" y1="28" x2="220" y2="56" stroke="var(--muted)"/><line x1="160" y1="60" x2="220" y2="60" stroke="var(--muted)"/><line x1="160" y1="92" x2="220" y2="64" stroke="var(--muted)"/>
  <line x1="50" y1="46" x2="230" y2="52" stroke="var(--s1)" stroke-dasharray="2 2"/>
  <text x="200" y="108" fill="var(--muted)" font-size="7">all three calls append to the same object the def created</text>
</svg>
^ The `def` creates the default list a single time; each later call that omits the argument is routed to that same one list object, so their appends pile into one shared list rather than three separate ones.

**A mutable default is one object bound to the function at definition, so every call that omits the argument shares and mutates it; a None default has nothing to share, so the body can build a fresh object per call.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/mutdefault-inter-01/mutdefault.py

The fixture is three items appended one per call, each call omitting the bucket.

```json filename=modules/teaching-and-portability/code/mutdefault-inter-01/mutdefault.json:3-3 COMPLETE
  "items": ["a", "b", "c"]
```

Run `--buggy`.

```text filename=--buggy
BUGGY — def add(item, bucket=[]): the default list is shared across calls
--------------------------------------------------------------
  add('a')  -> ['a']
  add('b')  -> ['a', 'b']
  add('c')  -> ['a', 'b', 'c']
--------------------------------------------------------------
  each call reused the SAME default list, so it accumulated to ['a', 'b', 'c'].
```

Three calls, each passing a single item and no bucket, and the returned list grows: `['a']`, then `['a', 'b']`, then `['a', 'b', 'c']`. The second call was supposed to start from an empty bucket and return `['b']`, but it returned `['a', 'b']` — the `'a'` from the first call was still there. That is the whole bug in three lines: the default `[]` was created once, when `add` was defined, and every call that omitted `bucket` appended to that same list, so the list carries data from one call into the next. In a real program this is a function you wrote expecting a clean slate each call — a default accumulator, a per-request cache, a "collect the errors" helper — silently sharing state across requests, users, or test cases, and the symptom (data from an earlier call appearing in a later one) shows up nowhere near the `def` line that caused it.

## Build

The fix is one sentinel, and it makes each call independent. Run `--fixed`.

```text filename=--fixed
FIXED — def add(item, bucket=None): build a fresh list inside when None
--------------------------------------------------------------
  add('a')  -> ['a']
  add('b')  -> ['b']
  add('c')  -> ['c']
```

Now each call returns exactly its own item: `['a']`, `['b']`, `['c']`. Defaulting `bucket` to None and constructing `[]` inside the body means the fresh list is built *when the function runs*, once per call, instead of once at definition — so there is no shared object to accumulate into. The reason this works, and the reason the bug existed, is that the default lives on the function object itself: it is stored in `add.__defaults__`, computed at creation, and the buggy version's `__defaults__[0]` *is* the list that grows. You can watch it mutate.

```python filename=modules/teaching-and-portability/code/mutdefault-inter-01/mutdefault.py:113-118 COMPLETE
    d = make_buggy()
    default_before = d.__defaults__[0]
    d("z")
    default_after = d.__defaults__[0]
    default_mutated = default_before is default_after and default_after == ["z"]
    print("  the default stored on the function is mutated in place = %s (__defaults__[0] = %s)" % (default_mutated, default_after))
```

<svg role="img" aria-label="Two rows of call results: the buggy version accumulates a, a-b, a-b-c into one list; the fixed version returns separate lists a, b, c" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">buggy accumulates into one list; fixed returns fresh lists</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">buggy</text>
  <g transform="translate(60,22)" font-size="7">
  <rect x="0" y="0" width="40" height="16" fill="var(--s2)"/><text x="6" y="11" fill="var(--panel)">[a]</text>
  <rect x="50" y="0" width="60" height="16" fill="var(--s2)"/><text x="56" y="11" fill="var(--panel)">[a,b]</text>
  <rect x="120" y="0" width="80" height="16" fill="var(--s2)"/><text x="126" y="11" fill="var(--panel)">[a,b,c]</text>
  <text x="210" y="11" fill="var(--muted)">one shared list</text>
  </g>
  <text x="10" y="72" fill="var(--muted)" font-size="7">fixed</text>
  <g transform="translate(60,60)" font-size="7">
  <rect x="0" y="0" width="40" height="16" fill="var(--s1)"/><text x="6" y="11" fill="var(--panel)">[a]</text>
  <rect x="50" y="0" width="40" height="16" fill="var(--s1)"/><text x="56" y="11" fill="var(--panel)">[b]</text>
  <rect x="100" y="0" width="40" height="16" fill="var(--s1)"/><text x="106" y="11" fill="var(--panel)">[c]</text>
  <text x="150" y="11" fill="var(--muted)">three fresh lists</text>
  </g>
</svg>
^ The buggy calls all return the same growing list (`[a]`, `[a,b]`, `[a,b,c]`), while the fixed calls each return a separate single-item list (`[a]`, `[b]`, `[c]`) — the difference between one object shared and one built per call.

## Definition of done

The self-test pins the accumulation, the reset, and the shared-object identity.

```python filename=modules/teaching-and-portability/code/mutdefault-inter-01/mutdefault.py:96-106 COMPLETE
    buggy_accumulates = buggy_results == [["a"], ["a", "b"], ["a", "b", "c"]]
    print("  the buggy function accumulates across calls = %s (%s)" % (buggy_accumulates, buggy_results))

    fixed_results = run(make_fixed(), items)
    fixed_resets = fixed_results == [["a"], ["b"], ["c"]]
    print("  the fixed function resets each call = %s (%s)" % (fixed_resets, fixed_results))

    b = make_buggy()
    r1, r2 = b("x"), b("y")
    buggy_same_object = r1 is r2
    print("  the buggy calls return the SAME list object = %s" % buggy_same_object)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the buggy default is one shared object that accumulates; the fixed version resets; the default is mutated in place
----------------------------------------------------------------------------------------------------------------------------
  the buggy function accumulates across calls = True ([['a'], ['a', 'b'], ['a', 'b', 'c']])
  the fixed function resets each call = True ([['a'], ['b'], ['c']])
  the buggy calls return the SAME list object = True
  the fixed calls return DIFFERENT list objects = True
  the default stored on the function is mutated in place = True (__defaults__[0] = ['z'])
```

**Done means the shared-default bug and its fix are proven by running both: the buggy function accumulates across calls (['a'], ['a','b'], ['a','b','c']) and its calls return the same list object, the fixed function resets each call (['a'], ['b'], ['c']) with a different object each time, and the buggy default is shown mutating in place on the function's __defaults__ — so a mutable default is one object shared across calls, and defaulting to None and building inside fixes it.**

## Boss fight

Predict two ways this generalizes beyond the classic list example, because the same evaluate-once rule bites in more places and one common "fix" is itself a bug.

The first trap is that this is not about lists specifically — it is about *any* default value that is either mutable or computed once, and the two cases have opposite fixes. Every mutable default has the bug: `bucket={}` shares one dict, `seen=set()` shares one set, `config=SomeObject()` shares one instance, and a default that is a mutable class attribute has the same shape. But the evaluate-once rule also surprises in the other direction, with defaults that are meant to be *dynamic*: `def log(msg, when=datetime.now())` freezes `when` to the single timestamp computed when the module was imported, so every log line gets the import time, not the call time — a default that looks like "now" but means "then". The unifying rule is that a default expression is evaluated exactly once at definition, so any default that should be fresh per call — a new container, the current time, a new id, a value read from changing state — must be defaulted to None (or a sentinel) and computed inside the body. The list is just the most common instance of a rule about *all* per-call defaults.

<svg role="img" aria-label="A function with when defaulting to datetime.now(): the timestamp is frozen at import time, so calls at 09:00, 12:00, and 17:00 all receive the same 08:00 import time instead of their own call time" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">when=datetime.now() freezes to import time, not call time</text>
  <rect x="10" y="24" width="96" height="20" fill="none" stroke="var(--s1)"/><text x="16" y="38" fill="var(--muted)" font-size="7">import @ 08:00 → now()</text>
  <g font-size="7">
  <text x="130" y="34" fill="var(--muted)">call 09:00</text><text x="210" y="34" fill="var(--s2)">gets 08:00</text>
  <text x="130" y="54" fill="var(--muted)">call 12:00</text><text x="210" y="54" fill="var(--s2)">gets 08:00</text>
  <text x="130" y="74" fill="var(--muted)">call 17:00</text><text x="210" y="74" fill="var(--s2)">gets 08:00</text>
  </g>
  <line x1="106" y1="38" x2="128" y2="31" stroke="var(--muted)"/><line x1="106" y1="38" x2="128" y2="51" stroke="var(--muted)"/><line x1="106" y1="38" x2="128" y2="71" stroke="var(--muted)"/>
  <text x="10" y="96" fill="var(--muted)" font-size="7">a "now" default that always reports "then" — same evaluate-once rule</text>
</svg>
^ A `when=datetime.now()` default is computed once at import, so every call receives the import timestamp (08:00) no matter when it runs — the same evaluate-once rule as the shared list, in the opposite-looking guise of a stale-time bug.

The second trap is that the None sentinel has an edge case, and the popular one-liner "fix" reintroduces a bug. Defaulting to None fails when None is a *legitimate* argument value the caller might pass deliberately — then you cannot distinguish "caller omitted it" from "caller passed None" — so the robust pattern uses a private unique sentinel object (`_MISSING = object()`, default to that, and check `if arg is _MISSING`) rather than None. And the tempting compact fix `def add(item, bucket=None): bucket = bucket or []` is subtly wrong: `bucket or []` treats any *falsy* passed value — an empty list, `0`, `""` — as "not provided" and silently replaces it with a new list, so a caller who passes an existing empty list to fill gets a different list back and their append is lost. The correct check is `if bucket is None`, an identity test, not a truthiness test. So the discipline is precise: never a mutable or dynamic default; default to None (or a dedicated sentinel when None is a valid value); and gate on `is None`, not on truthiness — because both the bug and its most popular fix come from treating "the default" and "a falsy value the caller meant" as the same thing.

**The evaluate-once rule bites every mutable or dynamic default (dicts, sets, objects, datetime.now()), all fixed by defaulting to None and computing inside the body — but the fix must gate on `if arg is None` (an identity test), never `arg or default` (which clobbers a caller's legitimate empty/falsy value), and must use a dedicated sentinel object instead of None whenever None is itself a valid argument.**

## External resources

The Python documentation and FAQ on default argument values ("Why are default values shared between objects?") — the evaluate-once-at-definition rule, the `__defaults__` attribute, and the recommended None-sentinel pattern.

Any Python style guide or "common gotchas" reference on mutable default arguments — the list/dict/set cases, the `datetime.now()` dynamic-default case, and why `arg or default` is a buggy substitute for `arg is None`.

The companion integer-division and round-half-even modules in this topic — like them, this is a case where a language's precise evaluation rule contradicts a reasonable-looking intuition, so the code does something correct-by-the-rules but surprising until you know the rule.
