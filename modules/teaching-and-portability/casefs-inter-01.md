---
id: casefs-inter-01
title: Reference filenames with their exact case — a case-insensitive filesystem hides a wrong-case bug that breaks on Linux
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Whether two filenames are "the same file" depends on the filesystem, and the default differs across the platforms your code runs on. macOS and Windows are case-insensitive by default: "Data.csv", "data.csv", and "DATA.CSV" all refer to one file, so an import or open() with the wrong case still finds it. Linux is case-sensitive: those are three different names, and only an exact-case match resolves. This is a portability trap because most developers write and test on macOS or Windows while most CI and production servers run Linux — so a reference whose case does not match the file on disk works perfectly on the author's laptop, where the case-insensitive filesystem quietly forgives it, and fails the moment it runs on Linux. It is the canonical "works on my machine": not a difference in the code, but a difference in what the filesystem considers a match. An import Utils that should be import utils, an open("Data.csv") for a file committed as data.csv — each resolves locally and raises FileNotFoundError on the case-sensitive machine, and the author, never seeing the error, cannot reproduce the CI failure. There is a mirror hazard: two files differing only in case ("Log.txt", "log.txt") are distinct on Linux but collide to one name on a case-insensitive checkout. On a fixture referencing three files, a case-insensitive filesystem resolves all three while a case-sensitive one resolves only the exactly-cased "config.yaml" and misses "Data.csv" and "src/model.py"; and the pair "Log.txt"/"log.txt", two files on Linux, collide to one on macOS/Windows.
eli5: Imagine a librarian who doesn't care about capital letters — ask for "harry potter," "Harry Potter," or "HARRY POTTER" and they hand you the same book. You get used to being sloppy with capitals because it always works. Then you visit a stricter library where the capitals must match exactly, and suddenly your sloppy request finds nothing on the shelf — even though the book is right there under its proper name. Computers are like this: your own laptop is the easygoing librarian, but the server that actually runs your program is the strict one, so if you spelled a filename with the wrong capitals, it works for you and breaks for everyone on the strict machine.
---

## Why this module

Filenames feel like plain text, so it is natural to assume that spelling one with the wrong capitalization is harmless — and on the machine where you write the code, it is, which is exactly what makes it dangerous. Your laptop's filesystem quietly treats "Data.csv" and "data.csv" as the same file, so a mis-cased import or path resolves and the program runs, and you have no signal that anything is wrong. The bug is real and already committed; it is simply invisible on a case-insensitive filesystem, waiting for the code to run somewhere stricter.

The default differs across platforms. macOS and Windows are case-insensitive: "Data.csv", "data.csv", and "DATA.CSV" all refer to the one file, so an import or open() with the wrong case still finds it. Linux is case-sensitive: those are three different names, and only an exact-case match resolves. This is a portability trap because most developers write and test on macOS or Windows, while most continuous integration and production servers run Linux — so a wrong-case reference works on the author's laptop and fails the moment it runs on Linux, where the forgiving lookup is gone.

The failure is silent until the platform changes, and the author, never seeing the error locally, cannot reproduce the CI failure. The fix is discipline plus a check: always spell a filename in code with the exact case it has on disk, and verify with a case-sensitive lookup (which is what a Linux filesystem does) before it ships. This module runs the lookups both ways.

**Reference every filename in code with its exact on-disk case, and never let two files differ only in case — because a case-insensitive filesystem (macOS/Windows) hides a wrong-case reference that then breaks on a case-sensitive one (Linux CI/production), and a case-sensitive filesystem allows two case-differing files that then collide on a case-insensitive checkout.**

## Concepts

**The two filesystems differ in one line:** a case-sensitive lookup requires an exact match; a case-insensitive one folds case before matching.

```python filename=modules/teaching-and-portability/code/casefs-inter-01/casefs.py:55-63 COMPLETE
def found_case_sensitive(files, name):
    """A case-sensitive filesystem (Linux): only an exact-case match resolves."""
    return name in files


def found_case_insensitive(files, name):
    """A case-insensitive filesystem (macOS/Windows): a case-folded match resolves."""
    lowered = {f.lower(): f for f in files}
    return name.lower() in lowered
```

**We also resolve which on-disk file a case-insensitive lookup would land on**, to show the mismatch the author never sees.

```python filename=modules/teaching-and-portability/code/casefs-inter-01/casefs.py:66-68 COMPLETE
def insensitive_match(files, name):
    """The actual on-disk file a case-insensitive lookup would resolve `name` to, or None."""
    return {f.lower(): f for f in files}.get(name.lower())
```

<svg role="img" aria-label="The reference Data.csv against the file data.csv: a case-insensitive filesystem folds both to data.csv and matches, while a case-sensitive filesystem keeps them distinct and does not match" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">reference 'Data.csv' vs on-disk 'data.csv'</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">case-insensitive (mac/win)</text>
  <text x="20" y="50" fill="var(--s2)" font-size="7">Data.csv</text><text x="90" y="50" fill="var(--muted)" font-size="7">→ fold →</text><text x="150" y="50" fill="var(--ink)" font-size="7">data.csv</text>
  <text x="200" y="50" fill="var(--s1)" font-size="7">= data.csv ✓ match</text>
  <line x1="14" y1="60" x2="286" y2="60" stroke="var(--grid)"/>
  <text x="10" y="78" fill="var(--muted)" font-size="7">case-sensitive (linux)</text>
  <text x="20" y="94" fill="var(--s2)" font-size="7">Data.csv</text><text x="90" y="94" fill="var(--muted)" font-size="7">(exact)</text><text x="150" y="94" fill="var(--ink)" font-size="7">data.csv</text>
  <text x="200" y="94" fill="var(--s2)" font-size="7">≠ no match ✗</text>
  <text x="10" y="110" fill="var(--muted)" font-size="6">same code, same file — the filesystem decides whether they match</text>
</svg>
^ The reference "Data.csv" and the on-disk "data.csv" match on a case-insensitive filesystem (both fold to "data.csv") and do not match on a case-sensitive one — the code and the file are identical across platforms; only the filesystem's notion of "same name" changes the outcome.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/casefs-inter-01/casefs.py

The fixture is the files as committed and the references as written in code — two of the three with mismatched case.

```json filename=modules/teaching-and-portability/code/casefs-inter-01/casefs.json:3-5 COMPLETE
  "files_on_disk": ["data.csv", "config.yaml", "src/Model.py"],
  "references": ["Data.csv", "config.yaml", "src/model.py"],
  "distinct_on_linux": ["Log.txt", "log.txt"]
```

Run `--lookup`.

```text filename=--lookup
LOOKUP — how each reference resolves on the two kinds of filesystem
------------------------------------------------------------------------------
  reference in code    on-disk file            case-sensitive   case-insensitive
  Data.csv             data.csv                MISSING          found
  config.yaml          config.yaml             FOUND            found
  src/model.py         src/Model.py            MISSING          found
------------------------------------------------------------------------------
  every reference resolves case-insensitively (macOS/Windows); the mis-cased ones fail on Linux.
```

Read the two rightmost columns. Every reference is "found" on a case-insensitive filesystem, so on the author's macOS or Windows laptop the program runs cleanly and nothing hints at a problem. On a case-sensitive filesystem, only "config.yaml" — the one reference whose case exactly matches its file — is FOUND; "Data.csv" is MISSING because the file is "data.csv", and "src/model.py" is MISSING because the file is "src/Model.py". Those two would raise FileNotFoundError on Linux. The devastating part is the asymmetry of who sees the failure: the author, testing locally, sees all three resolve and ships with confidence; the CI server, running Linux, sees two of them fail; and the author cannot reproduce the failure on their own machine because their filesystem forgives the exact mistake CI trips on. The bug lives in the gap between two defaults.

## Build

The hazard runs in the other direction too — case-sensitivity lets you create files that a case-insensitive checkout cannot keep apart.

```text filename=--collision
COLLISION — two filenames differing only in case
----------------------------------------------------------
  committed files: ['Log.txt', 'log.txt']
  on a case-sensitive filesystem (Linux):   2 distinct files
  on a case-insensitive filesystem (mac/win): 1 file(s) -- ['Log.txt', 'log.txt'] collide to ['log.txt']
----------------------------------------------------------
  committing both is fine on Linux and breaks the checkout on macOS/Windows.
```

On a case-sensitive filesystem, "Log.txt" and "log.txt" are two genuinely different files, and a Linux developer can create, commit, and use both without any conflict. But those two names fold to the same string on a case-insensitive filesystem, so when someone checks the repository out on macOS or Windows, the two files collide into one name — the checkout cannot place both, and one silently overwrites or shadows the other, corrupting the working tree in a way that is hard to diagnose because `git status` may show a phantom modification that never goes away. This is the mirror image of the first bug, and together they give the symmetric rule: do not rely on case-insensitivity to find a file (or a wrong-case reference breaks on Linux), and do not rely on case-sensitivity to distinguish two files (or a case-only pair collides on macOS/Windows). The only safe posture is to treat filenames as case-significant when you write them and case-*insignificant* when you decide whether two of them may coexist.

<svg role="img" aria-label="Two files Log.txt and log.txt: on a case-sensitive filesystem they stay two separate files, but on a case-insensitive filesystem they fold to one name and collide" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">two files differing only in case — the mirror hazard</text>
  <rect x="20" y="26" width="60" height="16" fill="none" stroke="var(--s1)"/><text x="30" y="38" fill="var(--ink)" font-size="7">Log.txt</text>
  <rect x="20" y="46" width="60" height="16" fill="none" stroke="var(--s1)"/><text x="30" y="58" fill="var(--ink)" font-size="7">log.txt</text>
  <text x="10" y="80" fill="var(--s1)" font-size="6">case-sensitive: 2 files ✓</text>
  <line x1="90" y1="44" x2="150" y2="44" stroke="var(--muted)"/><text x="96" y="40" fill="var(--muted)" font-size="6">checkout on mac →</text>
  <rect x="170" y="36" width="60" height="16" fill="var(--s2)"/><text x="180" y="48" fill="var(--panel)" font-size="7">log.txt</text>
  <text x="236" y="48" fill="var(--s2)" font-size="6">collision</text>
  <text x="170" y="80" fill="var(--s2)" font-size="6">case-insensitive: 1 name, one file lost ✗</text>
</svg>
^ "Log.txt" and "log.txt" are two files on a case-sensitive filesystem but fold to the single name "log.txt" on a case-insensitive one, so a macOS/Windows checkout of a repo containing both collides them and loses one — the reverse of the wrong-case-reference bug, from the same root cause.

```python filename=modules/teaching-and-portability/code/casefs-inter-01/casefs.py:105-113 COMPLETE
    insensitive_finds_all = all(found_case_insensitive(files, r) for r in refs)
    print("  every reference resolves on a case-insensitive filesystem = %s" % insensitive_finds_all)

    broken = [r for r in refs if not found_case_sensitive(files, r)]
    sensitive_misses_some = len(broken) > 0
    print("  some references fail on a case-sensitive filesystem = %s (broken: %s)" % (sensitive_misses_some, broken))

    exact_ref_found_both = found_case_sensitive(files, "config.yaml") and found_case_insensitive(files, "config.yaml")
    print("  the exactly-cased 'config.yaml' resolves on both = %s" % exact_ref_found_both)
```

## Definition of done

The self-test pins the silent success on a case-insensitive filesystem, the exact references that fail on a case-sensitive one, and the case-only collision.

```python filename=modules/teaching-and-portability/code/casefs-inter-01/casefs.py:115-120 COMPLETE
    pair = data["distinct_on_linux"]
    collision_on_insensitive = len({n.lower() for n in pair}) < len(set(pair))
    print("  the case-only pair %s collides on a case-insensitive filesystem = %s (%d -> %d names)"
          % (pair, collision_on_insensitive, len(set(pair)), len({n.lower() for n in pair})))

    verdicts_differ = any(found_case_sensitive(files, r) != found_case_insensitive(files, r) for r in refs)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — mis-cased references resolve case-insensitively but fail case-sensitively; the case-only pair collides
--------------------------------------------------------------------------------------------------------------------
  every reference resolves on a case-insensitive filesystem = True
  some references fail on a case-sensitive filesystem = True (broken: ['Data.csv', 'src/model.py'])
  the exactly-cased 'config.yaml' resolves on both = True
  the case-only pair ['Log.txt', 'log.txt'] collides on a case-insensitive filesystem = True (2 -> 1 names)
  the two filesystems disagree on at least one reference = True
```

<svg role="img" aria-label="A verdict table for three references: Data.csv found case-insensitively but missing case-sensitively, config.yaml found on both, src/model.py found case-insensitively but missing case-sensitively" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">what the author sees (mac) vs what CI sees (linux)</text>
  <text x="130" y="28" fill="var(--muted)" font-size="6">insensitive</text><text x="215" y="28" fill="var(--muted)" font-size="6">sensitive</text>
  <text x="10" y="46" fill="var(--muted)" font-size="7">Data.csv</text><text x="130" y="46" fill="var(--s1)" font-size="7">found</text><text x="215" y="46" fill="var(--s2)" font-size="7">MISSING ✗</text>
  <text x="10" y="66" fill="var(--muted)" font-size="7">config.yaml</text><text x="130" y="66" fill="var(--s1)" font-size="7">found</text><text x="215" y="66" fill="var(--s1)" font-size="7">FOUND ✓</text>
  <text x="10" y="86" fill="var(--muted)" font-size="7">src/model.py</text><text x="130" y="86" fill="var(--s1)" font-size="7">found</text><text x="215" y="86" fill="var(--s2)" font-size="7">MISSING ✗</text>
  <line x1="120" y1="32" x2="120" y2="92" stroke="var(--grid)"/>
  <text x="10" y="104" fill="var(--muted)" font-size="6">the whole 'insensitive' column is green — the bug is invisible to the author</text>
</svg>
^ On a case-insensitive filesystem all three references resolve, so the author sees a clean green column and no bug; on a case-sensitive filesystem the two mis-cased references go MISSING while only the exactly-cased one survives — the disagreement is the entire failure, hidden by the author's forgiving platform.

**Done means the split is proven on real lookups: all three references resolve on a case-insensitive filesystem (what the author sees), while a case-sensitive filesystem finds only the exactly-cased "config.yaml" and misses "Data.csv" and "src/model.py", and the pair "Log.txt"/"log.txt" that is two files on Linux collides to one on macOS/Windows — so filenames must be referenced with exact case and never differ only in case.**

## Boss fight

Predict two ways this bug slips past even a careful developer, because the platform defaults have exceptions and the tooling can hide the mismatch.

The first trap is that "macOS is case-insensitive, Linux is case-sensitive" is a default, not a law, and the exceptions bite in both directions. macOS can be formatted case-sensitive (APFS supports it), and some developers do, so a mac is not a reliable stand-in for "case-insensitive." A Linux filesystem can be mounted case-insensitively (ciopfs, or ext4's casefold feature, or a mounted NTFS/exFAT volume), so a Linux box is not a guaranteed stand-in for "case-sensitive" either. Network and container filesystems add more: a case-insensitive host directory bind-mounted into a Linux container carries the host's behavior, so the "same" path behaves differently depending on where the volume came from. And beyond the filesystem, other name-matching layers have their own rules — HTTP URLs are case-sensitive in the path, S3 object keys are case-sensitive, but Windows environment variables and DNS hostnames are not. So you cannot infer case behavior from the operating system name; the only safe assumptions are the strict ones (treat every filename as case-sensitive when writing it, and as case-insensitive when checking for duplicates), and the only reliable verification is to actually run on a truly case-sensitive filesystem in CI.

The second trap is that Git and editors actively hide the mismatch, so the mistake persists and even resists correction. Git on a case-insensitive filesystem tracks the case a file was *first* added with and does not notice a later case change: rename "Data.csv" to "data.csv" in your editor and Git may show nothing, because to the filesystem the name did not change, so the wrong case stays committed. Fixing it needs an explicit two-step (`git mv --force`, or remove and re-add) or `git config core.ignorecase false`, and a repository that already contains a case-only collision (committed from Linux) will refuse to check out cleanly on a mac until it is resolved. Editors and shells autocomplete against the case-insensitive filesystem, so they will happily complete "data.csv" when you type "Data", reinforcing the wrong case. The defenses are procedural: reference files programmatically with a single source of truth (a constant, not a retyped string), add a CI job that runs on Linux (which turns the silent bug into a loud test failure), and add a lint/pre-commit check that flags case-only duplicate paths and, ideally, filenames referenced in code that do not match an on-disk file by exact case. The filesystem will not warn you; your pipeline has to.

**Do not infer case behavior from the OS name — macOS can be case-sensitive, Linux can be mounted case-insensitive, bind-mounts and container volumes carry the host's behavior, and URL/S3/DNS layers each have their own rules — so assume filenames are case-sensitive when writing them and case-insensitive when checking for duplicates, and verify on a truly case-sensitive CI. And defend against the tooling that hides the mismatch: Git on a case-insensitive filesystem ignores a later case change (needs git mv --force or core.ignorecase false), editors autocomplete the wrong case, so reference files from a single constant and add a Linux CI job plus a pre-commit check for case-only duplicates and mismatched references.**

## External resources

Git documentation on `core.ignorecase` and the case-sensitivity notes for GitHub/GitLab — how Git behaves on case-insensitive filesystems, why a case-only rename can go unnoticed, and how case-only duplicate paths break cross-platform checkouts.

Filesystem documentation for APFS/HFS+ (macOS), NTFS (Windows), and ext4 casefold (Linux) — the actual case-sensitivity defaults and options per filesystem, and why the OS name is not a reliable predictor.

The companion line-ending, encoding, and Unicode-normalization modules in this topic — all four are cases where a platform default silently changes how bytes or names compare, so a program that works on the author's machine breaks on a stranger's, and the fix is to make the assumption explicit and verify it in CI.
