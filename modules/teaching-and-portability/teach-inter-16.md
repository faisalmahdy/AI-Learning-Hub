---
id: teach-inter-16
title: Pin the dependency version — or the next person installs a different one and your documented output breaks
topic: teaching-and-portability
level: intermediate
status: ready
time: 21 min
summary: An artifact that declares a loose dependency range resolves to whatever the newest matching version is at install time, so a learner who installs later gets a newer version — and if anything changed, the run no longer matches the documented output. Pinning the exact version freezes it, so every install is identical. On a library with 1.4.0 (behavior A) and a later 1.5.0 (behavior B), a ">=1.0" range resolves to 1.4.0 on an early install and 1.5.0 on a late one, breaking the documented A; "==1.4.0" resolves to 1.4.0 both times and always matches.
eli5: If a recipe says "use the newest flour," two cooks on different days get different flour and different results. If it says "use exactly this brand and bag size," everyone gets the same thing and the recipe comes out as written. Pinning a software version is naming the exact bag, so the next person's run matches yours.
---

## Why this module

A dependency declared as "anything recent enough" is a promise that quietly changes meaning every time someone new installs it.

An artifact that uses a library has to declare that dependency somewhere. There are two ways to write the declaration, and they behave very differently over time. A loose range — "any version at or above 1.0" — tells the installer to pick the newest version that satisfies it, and "newest" is evaluated at install time. You install today, when the newest matching version is 1.4.0, and you write your lesson and its expected output against 1.4.0. A learner installs next month, when 1.5.0 has shipped, and the same loose range now resolves to 1.5.0 for them. You and the learner ran different code from the identical dependency declaration.

If nothing changed between those versions, no harm done. But versions change things — a default value, an output format, a rounding fix, a renamed parameter — and the moment one does, the learner's run stops matching your documented output. They see a different number or a different result and cannot tell whether they made a mistake, their environment is broken, or the library moved under them. Your "you should see X" was only ever true against the specific version you happened to have installed, and the loose range did not preserve that version. This is the same reproducibility failure as an unseeded random generator, but the varying input is the dependency resolver reading a registry that gains new versions over time.

Pinning fixes it: declare the exact version — "==1.4.0" — so every install resolves to that same version no matter what has shipped since. The run becomes reproducible across people and dates, because the dependency is frozen to the one you tested and documented against. A lockfile extends this to the whole dependency tree at once, recording every transitive package's exact version so the entire environment is identical for the next person, not just your direct dependencies. Loose ranges are convenient when you want to receive updates automatically; pinned versions are what make a documented, checkable result.

On the fixture, the library has 1.4.0 (behavior A) and a later 1.5.0 (behavior B). A loose ">=1.0" resolves to 1.4.0 on an early install date and 1.5.0 on a later one — two different behaviors, and only one matches the documented A. A pinned "==1.4.0" resolves to 1.4.0 on both dates, always matching the documented output.

**A loose dependency range resolves to the newest matching version at install time, so a later install gets a newer version and a documented result breaks when anything changed; pinning the exact version (and a lockfile for the whole tree) freezes the dependency so every install is identical and reproducible.**

## Concepts

The root cause is that the resolver reads a moving target. A package registry only grows — new versions are published over time and old ones stay — so "the newest version matching this range" is a function of when you ask. A loose range delegates the version choice to that function, which means the choice is made at install time against whatever the registry currently holds, not at authoring time against what you tested. The dependency declaration is therefore not a specification of what will run; it is a query whose answer drifts. Two installs of the "same" artifact on different dates are genuinely two different programs.

Pinning removes the time-dependence by making the resolver's answer a constant. An exact version has exactly one match regardless of what else has been published, so the resolve function returns the same version on every date — the run becomes a pure function of the pinned versions plus your code, the same purity that makes any result reproducible. The trade is real and worth stating: a pin does not receive bug fixes or security patches automatically, so pinned dependencies must be updated deliberately (and re-tested), whereas a loose range receives them automatically at the cost of reproducibility. The right default for a documented, checkable artifact is to pin; the right default for a long-lived application balancing reproducibility against staying patched is a lockfile you update on a schedule.

<svg role="img" aria-label="A manifest pins the top library but its transitive dependencies are still ranges that drift; a lockfile freezes the whole tree" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">a pin freezes the top; a lockfile freezes the whole tree</text>
  <text x="30" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">pin only the direct dep</text>
  <rect x="40" y="54" width="80" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="48" y="69" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">lib ==1.4.0</text>
  <line x1="80" y1="76" x2="60" y2="96" stroke="var(--line)"/><line x1="80" y1="76" x2="120" y2="96" stroke="var(--line)"/>
  <rect x="30" y="98" width="70" height="20" fill="var(--panel)" stroke="var(--s2)"/><text x="36" y="112" font-family="var(--mono)" font-size="7" fill="var(--s2)">dep-x &gt;=2 (drifts)</text>
  <rect x="105" y="98" width="70" height="20" fill="var(--panel)" stroke="var(--s2)"/><text x="111" y="112" font-family="var(--mono)" font-size="7" fill="var(--s2)">dep-y &gt;=1 (drifts)</text>
  <text x="280" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">lockfile</text>
  <rect x="290" y="54" width="80" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="298" y="69" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">lib ==1.4.0</text>
  <rect x="280" y="98" width="70" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="286" y="112" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">dep-x ==2.3.1</text>
  <rect x="355" y="98" width="70" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="361" y="112" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">dep-y ==1.9.0</text>
  <text x="30" y="150" font-family="var(--mono)" font-size="7" fill="var(--muted)">pinning only the top leaves the transitive deps free to change under you</text>
</svg>
^ Pinning the direct dependency still lets its transitive dependencies drift as ranges; a lockfile records every package's exact version, freezing the entire environment.

A lockfile is the industrial form of pinning and handles the part a single pin misses: transitive dependencies. Your library depends on other libraries, which depend on still others, and even if you pin your direct dependency, its dependencies may be declared as ranges and drift. A lockfile captures the exact resolved version of every package in the tree — direct and transitive — so the whole environment is reproduced, not just the top layer. This is why ecosystems ship lockfiles (package-lock.json, poetry.lock, Cargo.lock, requirements.txt with hashes): the manifest says what you want, and the lockfile records exactly what you got, so the next person gets the same. Reproducing an environment means reproducing the lockfile, not just the manifest.

This is one instance of the general reproducibility discipline that runs through portability: remove every hidden, drifting input so the output depends only on what is committed. An unseeded RNG drifts with the clock; an absolute path drifts with the machine; an unpinned dependency drifts with the registry; a network call drifts with the world. Each is fixed the same way — pin it down and commit it (a seed, a relative path, an exact version, a recorded fixture). A documented result is a claim, and a claim is only checkable if everything it depends on is frozen. The loose range is convenient precisely because it is not frozen, which is exactly why it cannot back a reproducible result.

**A loose range makes the version a time-dependent query against a growing registry, so it drifts; pinning makes it a constant and the run a pure function of committed inputs (at the cost of manual updates), with a lockfile freezing the whole transitive tree — the same "commit every drifting input" rule as seeding, relative paths, and fixtures.**

## Worked example

The fixture is a library's versions, two dependency specs, and two install dates.

```json filename=modules/teaching-and-portability/code/teach-inter-16/deps.json:3-14 COMPLETE
  "versions": {
    "1.4.0": {"released_day": 10, "behavior": "A"},
    "1.5.0": {"released_day": 20, "behavior": "B"}
  },
  "specs": {
    "loose": {"type": "range", "min": "1.0"},
    "pinned": {"type": "exact", "version": "1.4.0"}
  },
  "early_day": 15,
  "late_day": 25,
  "documented_behavior": "A"
```

Version 1.4.0 (behavior A) shipped on day 10; 1.5.0 (behavior B) shipped on day 20 — a behavior change. The lesson was written and documented against 1.4.0, so the documented behavior is A. Resolving a spec picks the newest version that both matches the spec and had been released by the install day.

```python filename=modules/teaching-and-portability/code/teach-inter-16/pin.py:52-55 COMPLETE
def resolve(spec, install_day, versions):
    """The newest version that matches the spec AND has been released by the install day."""
    available = [v for v in versions if versions[v]["released_day"] <= install_day and matches(v, spec)]
    return max(available, key=parse) if available else None
```

The loose range matches any version at or above its floor; the pin matches only its exact version.

```python filename=modules/teaching-and-portability/code/teach-inter-16/pin.py:46-49 COMPLETE
def matches(version, spec):
    if spec["type"] == "exact":
        return version == spec["version"]
    return parse(version) >= parse(spec["min"])   # a loose lower-bound range
```

The behavior an install produces is just the behavior of the version it resolved to.

```python filename=modules/teaching-and-portability/code/teach-inter-16/pin.py:58-60 COMPLETE
def behavior(spec, install_day, versions):
    v = resolve(spec, install_day, versions)
    return versions[v]["behavior"] if v else None
```

Predict: on the early day (15), only 1.4.0 exists, so both specs resolve to it. On the late day (25), 1.5.0 also exists, so the loose range jumps to 1.5.0 while the pin stays on 1.4.0. Resolve both.

```text filename=modules/teaching-and-portability/code/teach-inter-16/pin.py --resolve
RESOLVE — what each spec resolves to at day 15 (early) vs day 25 (late)
----------------------------------------------------------
  loose    (>=1.0)  early -> 1.4.0   late -> 1.5.0
  pinned   (==1.4.0)  early -> 1.4.0   late -> 1.4.0
----------------------------------------------------------
  the loose range picks up the newer version at the later date.
```

The loose range resolves to 1.4.0 early and 1.5.0 late — the newer version appeared and the range grabbed it. The pin resolves to 1.4.0 both times. Same declaration, different result across dates for the loose range; identical for the pin. Now the behavior each install produces, against the documented A.

```text filename=modules/teaching-and-portability/code/teach-inter-16/pin.py --behave
BEHAVE — behavior per install, vs the documented output 'A'
----------------------------------------------------------
  loose    early 'A' (match)   late 'B' (MISMATCH)
  pinned   early 'A' (match)   late 'A' (match)
----------------------------------------------------------
  only the pinned spec matches the documented output at both dates.
```

The loose install matches the documented A on the early date and produces B on the late date — a mismatch. A learner installing after 1.5.0 shipped runs the lesson, gets behavior B, and finds it disagrees with the documented A, with no way to know the cause is a version bump. The pin produces A on both dates, so the documented output is reproducible whenever the learner installs. The only difference is whether the version was frozen; the loose range let the registry choose, and the registry changed.

<svg role="img" aria-label="A timeline with 1.4.0 released at day 10 and 1.5.0 at day 20; a loose range resolves to 1.4.0 at day 15 and 1.5.0 at day 25, while a pin stays on 1.4.0 at both" viewBox="0 0 470 185" width="470" height="185">
  <rect x="0" y="0" width="470" height="185" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">install date decides what a loose range resolves to</text>
  <line x1="40" y1="60" x2="450" y2="60" stroke="var(--line)"/>
  <circle cx="130" cy="60" r="4" fill="var(--acc-line)"/><text x="105" y="50" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">1.4.0 (A) day10</text>
  <circle cx="280" cy="60" r="4" fill="var(--s2)"/><text x="258" y="50" font-family="var(--mono)" font-size="7" fill="var(--s2)">1.5.0 (B) day20</text>
  <line x1="190" y1="55" x2="190" y2="130" stroke="var(--muted)" stroke-dasharray="2 2"/><text x="170" y="145" font-family="var(--mono)" font-size="7" fill="var(--muted)">install day15</text>
  <line x1="360" y1="55" x2="360" y2="130" stroke="var(--muted)" stroke-dasharray="2 2"/><text x="340" y="145" font-family="var(--mono)" font-size="7" fill="var(--muted)">install day25</text>
  <text x="30" y="105" font-family="var(--mono)" font-size="8" fill="var(--s2)">loose:</text>
  <text x="168" y="105" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1.4.0 A</text>
  <text x="338" y="105" font-family="var(--mono)" font-size="8" fill="var(--s2)">1.5.0 B ✗</text>
  <text x="30" y="125" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">pin:</text>
  <text x="168" y="125" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1.4.0 A</text>
  <text x="338" y="125" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1.4.0 A ✓</text>
  <text x="30" y="170" font-family="var(--mono)" font-size="7" fill="var(--muted)">the pin ignores the day-20 release; the loose range grabs it and breaks the doc</text>
</svg>
^ At day 15 both specs give 1.4.0 (A); after 1.5.0 ships, the day-25 loose install jumps to 1.5.0 (B, mismatching the documented A) while the pin stays on 1.4.0 (A).

## Build

Reproduce the resolutions. Pure standard library, deterministic, so the loose range's 1.4.0→1.5.0 drift and the pin's steady 1.4.0 come out exactly.

Run `--resolve` for the versions, `--behave` for the behaviors versus the documented output, `--check` for the gate. <svg role="img" aria-label="A two-by-two: loose matches the documented output on the early install but mismatches on the late one; the pin matches on both" viewBox="0 0 470 155" width="470" height="155">
  <rect x="0" y="0" width="470" height="155" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">matches documented output 'A'?</text>
  <text x="170" y="44" font-family="var(--mono)" font-size="9" fill="var(--muted)">early install</text>
  <text x="320" y="44" font-family="var(--mono)" font-size="9" fill="var(--muted)">late install</text>
  <text x="20" y="80" font-family="var(--mono)" font-size="9" fill="var(--s2)">loose</text>
  <text x="180" y="80" font-family="var(--mono)" font-size="10" fill="var(--acc-line)">A ✓</text>
  <text x="325" y="80" font-family="var(--mono)" font-size="10" fill="var(--s2)">B ✗</text>
  <text x="20" y="118" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">pin</text>
  <text x="180" y="118" font-family="var(--mono)" font-size="10" fill="var(--acc-line)">A ✓</text>
  <text x="325" y="118" font-family="var(--mono)" font-size="10" fill="var(--acc-line)">A ✓</text>
  <line x1="150" y1="52" x2="150" y2="130" stroke="var(--line)"/>
  <line x1="15" y1="90" x2="440" y2="90" stroke="var(--line)" stroke-dasharray="2 2"/>
</svg>
^ The loose range matches the documented output only on the early install and breaks on the late one; the pin matches on both, whenever the learner installs.

The self-test pins the loose range's drift and doc break, and the pin's stability.

```python filename=modules/teaching-and-portability/code/teach-inter-16/pin.py:98-100 COMPLETE
    loose_resolves_differently = resolve(loose, early, versions) != resolve(loose, late, versions)
    print("  the loose range resolves to different versions over time = %s (%s vs %s)"
          % (loose_resolves_differently, resolve(loose, early, versions), resolve(loose, late, versions)))
```

```text filename=modules/teaching-and-portability/code/teach-inter-16/pin.py --check
SELF-TEST — the loose range resolves differently over time and breaks the doc; the pin stays reproducible
----------------------------------------------------------------------------------------------------
  the loose range resolves to different versions over time = True (1.4.0 vs 1.5.0)
  the loose range produces different behavior over time = True ('A' vs 'B')
  the late loose install no longer matches the documented output = True
  the pinned spec resolves to the same version at both dates = True (1.4.0)
  the pinned spec matches the documented output at both dates = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  loose_resolves_differently=True  loose_behavior_differs=True  loose_breaks_doc=True  pinned_resolves_same=True  pinned_matches_doc=True
```

Five True flags. Loose_resolves_differently: the range gives 1.4.0 early and 1.5.0 late. Loose_behavior_differs: those versions behave A versus B. Loose_breaks_doc: the late install's B no longer matches the documented A. Pinned_resolves_same: the pin gives 1.4.0 at both dates. Pinned_matches_doc: so it matches the documented A whenever installed. The loose_breaks_doc flag is the one that connects the drift to the learner's experience — the version changed, the behavior changed, and the documented answer became unreachable for anyone who installed after the new release.

**The loose_breaks_doc flag is the payoff of the drift — a later install runs a version you never tested, so the documented output becomes unreachable through no fault of the learner, which is exactly what pinning prevents.**

## Definition of done

You are done when you reproduce the loose drift and the pinned stability, and can explain why a range is not reproducible.

Concretely: `--resolve` shows the loose range at 1.4.0 early and 1.5.0 late while the pin stays 1.4.0; `--behave` shows the loose late install producing B against the documented A, and the pin producing A both times; `--check` prints PASS with five True flags. You can explain that a package registry only grows so "newest matching" is a function of install date, that pinning makes the resolved version a constant (at the cost of not auto-receiving fixes), and that a lockfile freezes the whole transitive tree. You can place this alongside seeding, relative paths, and fixtures as instances of committing every drifting input.

The habit to carry: pin exact versions (and commit a lockfile) for any artifact whose output you document, test, or want a learner to reproduce, and update those pins deliberately with a re-test rather than floating on ranges. When someone reports getting a different result than the documented one, and their code matches, check their installed dependency versions before anything else — a floated range is a leading cause of "works on my machine." Freeze what you documented against.

## Boss fight

The instructive failure is a tutorial whose notebook worked for a year and then broke for everyone at once.

A popular tutorial declares its dependencies as loose ranges and documents specific outputs. For a year the newest matching versions happen to behave as documented, so it works. Then a dependency ships a major version with a changed default, and overnight every new learner's run produces different numbers than the tutorial shows — a flood of "this is broken" reports, though the author changed nothing. The author cannot even reproduce the old behavior without knowing which versions were current when they wrote it. The fix is to pin the exact versions the tutorial was validated against (and commit a lockfile), so a learner installing any time reproduces the documented output; updating to the new major version becomes a deliberate, tested change. The tell is a working artifact breaking with no code change, correlated with a dependency release.

Your turn, two moves. First, model the lockfile gap: add a transitive dependency (the library itself depends on another library declared as a range) and confirm that pinning only the top-level library still lets the transitive one drift and change behavior — showing that a single pin is insufficient and a lockfile over the whole tree is what actually freezes the environment. Second, model the update trade-off: ship a 1.4.1 that fixes a bug (behavior "A-fixed") and confirm the pin to 1.4.0 does not receive it while the loose range does — the reproducibility-versus-staying-patched tension, and why pins must be updated on a schedule rather than never.

## External resources

Packaging documentation across ecosystems (Python's pip and Poetry, npm, Cargo) explains the manifest-versus-lockfile distinction and recommends pinning or lockfiles for reproducible installs — the exact mechanism this module models.

Guides on reproducible research and computational environments (the "Ten Simple Rules" papers, and tools like conda-lock and pip-tools) list pinning exact dependency versions alongside seeding and environment capture as core reproducibility practices.

Writing on semantic versioning and the reasons even patch and minor updates can change behavior (and why "it should be backward compatible" is not a guarantee) motivates pinning over trusting ranges for anything whose output you document.
