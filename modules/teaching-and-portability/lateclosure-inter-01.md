---
id: lateclosure-inter-01
title: Bind the loop variable at definition time — closures made in a loop capture the variable, not its value, so they all see the last one
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Building a function inside a loop is routine — a click handler per button, a callback per row, a small function per item — and each refers to the loop variable to know which item it belongs to. Every one of them ends up belonging to the same item, the last one, because a closure does not snapshot the loop variable when created; it captures the variable itself, a live reference. When the loop finishes, that variable holds its final value, and since all the closures point at the same variable, they all read the final value when called: you built N functions expecting N different behaviors and got N copies of the last one. The trap, stated exactly, is that closing over a variable captures the variable, not a snapshot of its value at capture time, so the value a closure sees is whatever the variable holds when the closure runs, not when it was defined — and in a loop all iterations reuse one loop variable. The fix is to bind the value at definition time instead of referring to the shared variable: in Python the idiom is a default argument, whose default is evaluated once when the function is defined, so each closure captures that iteration's value in the function itself, independent of the shared loop variable. On a fixture of items a, b, c with one closure built per item, the naive closures (referring to the loop variable) all return 'c', the last item, while the default-argument closures return 'a', 'b', 'c' — same loop, different binding, different behavior.
eli5: Imagine you set out three envelopes and, next to each, you put a sticky note that says "put in whatever number I'm thinking of." You count "one... two... three," and then later you open all the notes to fill the envelopes — but by now you're only thinking of "three," so all three envelopes get a three. The notes didn't remember the number you were thinking of at the moment you wrote them; they just said "the number I'm thinking of," and you only think of one number at a time. The fix is to write the actual number on each note as you make it — "put in 1," "put in 2," "put in 3" — so each note remembers its own number instead of pointing at your ever-changing thought.
---

## Why this module

Closures capturing a loop variable is one of the most reliable "wait, why are they all the same?" bugs in programming, and it crosses languages — it is the classic JavaScript `var`-in-a-loop bug and the Python lambda-in-a-loop bug and shows up anywhere loop closures capture by reference. It is worth understanding not as a quirk of one language but as a direct consequence of what a closure is: a function plus a live link to the variables it uses, not a copy of their values. Once you see that, the behavior stops being surprising and becomes predictable — which is exactly when you stop writing the bug.

The setup is any loop that manufactures functions: handlers, callbacks, deferred computations, one per item. Each function refers to the loop variable so it can act on "its" item. But there is only one loop variable — the loop reuses it every iteration — and each closure captures that one variable, not the value it held at the moment of capture. So all the closures share a single reference, and by the time any of them actually runs, the loop has long since finished and left the variable at its final value. Every closure reads that final value.

The fix is a one-token change once you understand it, and the misunderstanding is expensive because the code looks obviously correct. This module builds closures over three items both ways and calls them.

**When creating closures in a loop, bind the loop value at definition time — e.g. as a default argument — rather than referring to the loop variable directly, because a closure captures the variable, not its value, so all closures share the one loop variable and read its final value when they run, making every closure behave as if it belonged to the last iteration.**

## Concepts

The fixture is a list of three items, and the intent is to build one closure per item that returns its own item.

```json filename=modules/teaching-and-portability/code/lateclosure-inter-01/lateclosure.json:3 COMPLETE
  "items": ["a", "b", "c"]
```

The two builds differ by one thing. The naive closures refer to the loop variable `item` directly — every closure captures that one shared variable. The fixed closures bind the current value as a default argument, captured when the function is defined.

```python filename=modules/teaching-and-portability/code/lateclosure-inter-01/lateclosure.py:32-39 COMPLETE
def build_naive(items):
    """Each closure refers to the loop variable `item` directly -- they all share it."""
    return [lambda: item for item in items]


def build_fixed(items):
    """Each closure binds the current value as a default argument -- captured at definition."""
    return [lambda item=item: item for item in items]
```

Calling the closures is where the difference surfaces — the naive ones read the loop variable's final value, the fixed ones read their stored default.

```python filename=modules/teaching-and-portability/code/lateclosure-inter-01/lateclosure.py:42-44 COMPLETE
def results(closures):
    """Call every closure and collect what it returns."""
    return [c() for c in closures]
```

<svg role="img" aria-label="Three naive closures each with an arrow pointing to a single shared loop variable holding c, versus three fixed closures each holding its own value a, b, c" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--s2)">naive: 3 closures → 1 shared variable</text>
  <rect x="14" y="24" width="26" height="14" fill="var(--s2)"/><text x="20" y="34" font-size="7.5" fill="var(--panel)">f0</text>
  <rect x="14" y="40" width="26" height="14" fill="var(--s2)"/><text x="20" y="50" font-size="7.5" fill="var(--panel)">f1</text>
  <rect x="14" y="56" width="26" height="14" fill="var(--s2)"/><text x="20" y="66" font-size="7.5" fill="var(--panel)">f2</text>
  <rect x="120" y="38" width="40" height="18" fill="var(--muted)"/><text x="128" y="51" font-size="8" fill="var(--panel)">item=c</text>
  <line x1="40" y1="31" x2="120" y2="45" stroke="var(--s2)" stroke-width="1"/>
  <line x1="40" y1="47" x2="120" y2="47" stroke="var(--s2)" stroke-width="1"/>
  <line x1="40" y1="63" x2="120" y2="49" stroke="var(--s2)" stroke-width="1"/>
  <text x="168" y="49" font-size="8" fill="var(--s2)">all read 'c'</text>
  <text x="10" y="92" font-size="8.5" fill="var(--s1)">fixed: each closure holds its own value</text>
  <rect x="14" y="100" width="40" height="14" fill="var(--s1)"/><text x="18" y="110" font-size="7.5" fill="var(--panel)">f0: a</text>
  <rect x="60" y="100" width="40" height="14" fill="var(--s1)"/><text x="64" y="110" font-size="7.5" fill="var(--panel)">f1: b</text>
  <rect x="106" y="100" width="40" height="14" fill="var(--s1)"/><text x="110" y="110" font-size="7.5" fill="var(--panel)">f2: c</text>
  <text x="156" y="110" font-size="8" fill="var(--s1)">return a, b, c</text>
</svg>
^ The naive closures all point at one shared loop variable, which ends at 'c', so all three return 'c'. The default-argument closures each store their own value at definition, so they return a, b, c. Same closures, different capture.

**A closure captures the variable, not its value — so what matters is not what the variable held when the closure was made but what it holds when the closure runs, which in a loop is the final value for all of them.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the callback-construction step of an event handler setup, reduced to three items so every closure's result is checkable by hand.

Run `--naive` to see the closures that refer to the loop variable.

```text filename=lateclosure.py --naive
  items            = ['a', 'b', 'c']
  closure results  = ['c', 'c', 'c']
  every closure returned 'c' (the last item) -- they share the loop variable
```

Three closures were built, one per item, and all three return 'c'. Not 'a', 'b', 'c' — 'c' three times. Each closure was supposed to remember its own item, but they all captured the same loop variable, and by the time they were called the loop had left that variable at 'c'. If these were click handlers, every button would act as if it were the last button; if they were row callbacks, every row would operate on the last row's data.

Now `--fixed` binds the value with a default argument.

```text filename=lateclosure.py --fixed
  items            = ['a', 'b', 'c']
  closure results  = ['a', 'b', 'c']
  each closure returned its own item -- the default captured the value at definition
```

The only change is `lambda: item` becoming `lambda item=item: item`, and now the closures return 'a', 'b', 'c'. The default argument is evaluated once, at definition, so each closure froze that iteration's value into its own parameter, independent of the shared loop variable. The loop is identical; the binding is different, and the behavior flips from "all the same" to "each its own."

<svg role="img" aria-label="A timeline: the loop runs and advances the variable to c, then later the closures are called and all read c; a closure called during the loop would read the current value" viewBox="0 0 320 100">
  <line x1="20" y1="45" x2="300" y2="45" stroke="var(--line)" stroke-width="1"/>
  <text x="24" y="30" font-size="7.5" fill="var(--muted)">loop builds closures, var → a,b,c</text>
  <rect x="24" y="38" width="90" height="14" fill="var(--muted)"/>
  <text x="150" y="30" font-size="7.5" fill="var(--muted)">later: closures called</text>
  <rect x="150" y="38" width="60" height="14" fill="var(--s2)"/>
  <text x="216" y="49" font-size="7.5" fill="var(--s2)">all read final 'c'</text>
  <line x1="114" y1="34" x2="114" y2="56" stroke="var(--ink)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="24" y="72" font-size="7.5" fill="var(--ink)">the variable already moved to 'c' before any closure ran — that timing is the bug</text>
</svg>
^ The closures are built during the loop but called after it, once the variable has already advanced to 'c'. Because they read the variable at call time, they all see 'c'. A closure that ran during its own iteration would see the current value — which is why the bug hides in deferred callbacks.

**The same three-item loop produces three identical results with the naive capture and three distinct correct ones with the default-argument capture — the bug and the fix differ by binding the value instead of the variable.**

## Build

The self-test asserts the failure precisely: the naive closures all return the same value, that value is the last item, and the results do not match the intended items.

```python filename=modules/teaching-and-portability/code/lateclosure-inter-01/lateclosure.py:78-88 COMPLETE
    naive_all_same = len(set(naive)) == 1
    print("  the naive closures all return the same value = %s (%s)" % (naive_all_same, naive))

    naive_all_last = all(r == items[-1] for r in naive)
    print("  that value is the LAST item = %s ('%s')" % (naive_all_last, items[-1]))

    naive_not_distinct = naive != items
    print("  the naive results do NOT match the items = %s (%s != %s)" % (naive_not_distinct, naive, items))

    fixed_matches_items = fixed == items
    print("  the default-argument closures return their own items = %s (%s)" % (fixed_matches_items, fixed))
```

<svg role="img" aria-label="A loop over a, b, c with the loop variable advancing; naive closures all bound to the final value c, fixed closures each snapshotting a, b, c" viewBox="0 0 320 110">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">loop variable over iterations: a → b → c (ends at c)</text>
  <text x="30" y="40" font-size="9" fill="var(--muted)">a</text><text x="60" y="40" font-size="9" fill="var(--muted)">b</text><text x="90" y="40" font-size="9" fill="var(--ink)">c</text>
  <line x1="38" y1="36" x2="55" y2="36" stroke="var(--line)"/><line x1="68" y1="36" x2="85" y2="36" stroke="var(--line)"/>
  <text x="10" y="70" font-size="8.5" fill="var(--s2)">naive: all closures → final 'c'</text>
  <rect x="180" y="60" width="30" height="14" fill="var(--s2)"/><text x="188" y="70" font-size="7.5" fill="var(--panel)">c c c</text>
  <text x="10" y="96" font-size="8.5" fill="var(--s1)">fixed: snapshot each → a, b, c</text>
  <rect x="180" y="86" width="30" height="14" fill="var(--s1)"/><text x="186" y="96" font-size="7.5" fill="var(--panel)">a b c</text>
</svg>
^ The loop variable moves a→b→c and ends at c. Naive closures, holding a reference to it, all resolve to c; fixed closures snapshot the value each iteration, preserving a, b, c.

Running the check confirms every clause, including that the same loop yields different behavior under different binding.

```text filename=lateclosure.py --check
  the naive closures all return the same value = True (['c', 'c', 'c'])
  that value is the LAST item = True ('c')
  the naive results do NOT match the items = True (['c', 'c', 'c'] != ['a', 'b', 'c'])
  the default-argument closures return their own items = True (['a', 'b', 'c'])
  the fixed results are all distinct (one per closure) = True
  same loop, different binding, different behavior = True
```

**The check pins the naive results to the last item and the fixed results to the items themselves — the difference is entirely the binding, proven by running the identical loop both ways.**

## Definition of done

Two properties close it. The naive closures must all return the last item (the bug in full), and the default-argument closures must return their own distinct items (the fix in full). Showing both from the same loop is what proves the cause is the binding, not the loop or the items.

```python filename=modules/teaching-and-portability/code/lateclosure-inter-01/lateclosure.py:90-94 COMPLETE
    fixed_distinct = len(set(fixed)) == len(items)
    print("  the fixed results are all distinct (one per closure) = %s" % fixed_distinct)

    same_loop_different_binding = naive != fixed
    print("  same loop, different binding, different behavior = %s" % same_loop_different_binding)
```

Three clarifications keep the fix well-understood. First, the default-argument idiom works because default arguments are evaluated once at definition time and stored on the function object, which is exactly the "snapshot the value now" semantics you want — but it is a slight abuse of defaults (the parameter is not really meant to be passed), so many codebases prefer a factory function (`def make(item): return lambda: item`) that takes the value as a genuine argument, or a `functools.partial`; all three snapshot the value and are equivalent in effect. Second, this is the same trap across languages and the same class of fix: JavaScript's version is solved by declaring the loop variable with `let` (which creates a fresh binding per iteration) instead of `var` (one shared binding), and older code used an immediately-invoked function to capture the value — recognizing the pattern transfers. Third, the trap only bites when the closures are called after the loop finishes (or otherwise after the variable has moved); a closure that runs immediately during its own iteration sees the current value and is fine, which is why the bug hides in deferred callbacks specifically. The reliable habit is: whenever you build a closure in a loop that will run later, bind the value it needs, do not lean on the loop variable.

**Done means the naive closures all return the last item and the default-argument closures return their own — a binding fix (snapshot the value, not the variable) that generalizes across languages and matters exactly for closures called after the loop.**

## Boss fight

A developer builds a dashboard where each of ten buttons should filter the table to its own category. They create the handlers in a loop, and in testing every button filters to the last category, "Archived," no matter which one is clicked. They suspect an event-binding bug in the UI framework. What is actually wrong, and what is the minimal fix — and why did it pass the developer's first manual test of the loop?

It is not a framework bug; it is a late-binding closure. The handlers were created in a loop and each refers to the loop variable holding the category, but they all capture the same variable, and by the time any button is clicked the loop has finished and left that variable at its final value, "Archived" — so every handler filters to "Archived." The buttons and the framework are wired correctly; the ten handlers are effectively identical because they share one variable instead of each remembering its own category. The minimal fix is to bind the category at handler-definition time rather than referring to the loop variable: give the closure a default argument holding the current category (`lambda cat=category: filter(cat)`), or build each handler in a factory function that takes the category as an argument, or — in JavaScript — declare the loop variable with `let` instead of `var` so each iteration gets its own binding. Any of these snapshots the category per handler. As for why the first test passed: if the developer tested the loop by calling or logging inside it — during each iteration, before the loop advanced — the variable still held that iteration's value, so it looked correct; the bug only appears when the handlers run later (on click), after the loop has moved the shared variable to its last value. That timing is exactly why late-binding closure bugs survive a casual in-loop test and surface only in the deferred callbacks.

## External resources

The Python FAQ entry "Why do lambdas defined in a loop with different values all return the same result?" and the documentation on default argument evaluation — the authoritative statement of the capture-by-variable behavior and the default-argument idiom used here.

MDN's documentation on closures and the `let` vs `var` loop-binding behavior in JavaScript — the same trap and its per-iteration-binding fix in another language, useful for seeing that this is a general property of closures over loop variables, not a Python quirk.
