---
id: teach-inter-19
title: Resolve the data file relative to the script — or it opens only from the author's directory and machine
topic: teaching-and-portability
level: intermediate
status: ready
time: 19 min
summary: An artifact usually ships with a data file next to its script, and opening it means naming a path. The two obvious ways both break for the next person. Naming the file relative to the current working directory — open("data.csv") — resolves against wherever the learner launched the script, so it works only from the script's own folder and fails from anywhere else. Hardcoding the author's absolute path — open("/home/alice/…/data.csv") — resolves to a directory that exists only on the author's machine. One breaks on a different directory, the other on a different machine; both make the path depend on the environment. The fix is to resolve the file relative to the script's own location, which travels with the folder — every hub artifact does HERE = Path(__file__).parent; DATA = HERE / "data.csv". On a fixture where the file lives at /home/bob/…/mod/, cwd-relative finds it from 1 of 3 launch directories, the author's absolute path from 0, and script-relative from all 3.
eli5: If you tell a friend "the snacks are in the top drawer," it only works if they are standing at your desk. If you say "the snacks are in the drawer at 12 Elm Street," it only works at your house. But if you tape the snacks to the back of the book you are lending them, they can open the book anywhere and always find the snacks. Attaching the data to the script — and finding it from the script — is taping it to the book.
---

## Why this module

A data file that travels with a script is easy to lose, because the two obvious ways to name its path both point somewhere other than where the file actually is.

The file sits next to the script, and the code has to open it. The first instinct — `open("data.csv")` — names the file relative to the current working directory, which is wherever the shell happens to be when the script launches. Run it from the script's folder and it works; run it from your home directory, from a scheduler, from an editor's "run" button that starts in the project root, and the path resolves to a directory with no `data.csv` in it, and you get file-not-found. The second instinct — paste in the absolute path the author had, `/home/alice/proj/data.csv` — resolves to a directory that exists only on the author's machine, so it fails for every other person outright.

**Both a bare relative path and a hardcoded absolute path make the file's location depend on the environment — the launch directory or the machine — instead of on the code that ships with the file.**

The fix is to compute the path from the one thing the code always knows: where the script itself lives. Build the data path from the script's own directory plus the filename, and it points at the file wherever the folder is copied and from whatever directory it is launched. This module resolves a data file three ways across several launch directories and shows which one always finds it.

## Concepts

The **current working directory** (cwd) is the directory the shell is in when the script starts — set by where the user is, not by where the script is. A **cwd-relative** path like `data.csv` is resolved against it, so the same code looks in a different place depending on how it was launched.

An **absolute path** like `/home/alice/proj/data.csv` names a fixed location from the filesystem root. It ignores the cwd, but it hardcodes one machine's directory layout, so it is correct only on the machine it was written on.

A **script-relative** path is built from the script's own location — in Python, `Path(__file__).resolve().parent` gives the directory the script lives in, and joining the filename onto it points at the neighboring data file. This is independent of both the cwd and the user's home directory: copy the folder anywhere, launch from anywhere, and the path still resolves to the file.

The mechanism is that the data file and the script move together — they are in the same folder — so a path anchored to the script is anchored to the file. A path anchored to the cwd or to an absolute string is anchored to the environment, which is exactly what changes when someone else runs it.

**The data ships with the script, so the path must be computed from the script; anchoring it to the working directory or an absolute string anchors it to what varies.**

Each strategy anchors the path to a different reference point, and only one of those points moves together with the data file.

<svg role="img" aria-label="Three anchors for the path: the working directory (varies by launch), the filesystem root (varies by machine), and the script's own directory (moves with the file)" viewBox="0 0 300 110" width="300" height="110">
  <rect x="15" y="30" width="80" height="22" fill="none" stroke="var(--s1)" stroke-width="1"/><text x="22" y="44" fill="var(--muted)" font-size="7">cwd anchor</text>
  <text x="20" y="66" fill="var(--s1)" font-size="6">changes each launch</text>
  <rect x="110" y="30" width="80" height="22" fill="none" stroke="var(--s1)" stroke-width="1"/><text x="117" y="44" fill="var(--muted)" font-size="7">root / abs anchor</text>
  <text x="118" y="66" fill="var(--s1)" font-size="6">changes each machine</text>
  <rect x="205" y="30" width="80" height="22" fill="var(--s2)"/><text x="212" y="44" fill="var(--panel)" font-size="7">script anchor</text>
  <text x="210" y="66" fill="var(--s2)" font-size="6">moves with the file</text>
  <text x="15" y="95" fill="var(--muted)" font-size="8">the data file sits inside the script's folder → anchor the path there</text>
</svg>
^ The cwd anchor shifts with every launch and the absolute anchor with every machine; only the script anchor stays glued to the data file it ships beside.

Every artifact in this hub opens its fixture this way — `HERE = Path(__file__).resolve().parent` then `DATA = HERE / "data.json"` — which is why a stranger can clone the repo and run any of them from anywhere.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/teach-inter-19/resolve.py

The fixture places the script and its data file on the learner's machine, records the author's hardcoded path, and lists directories the learner might launch from.

```json filename=modules/teaching-and-portability/code/teach-inter-19/paths.json:1-6 COMPLETE
{
  "_meta": "A learner runs an artifact that needs to open a data file sitting next to the script. script_dir is where the script (and its data file) actually live on the learner's machine. data_filename is the file's name. author_absolute is the absolute path the ORIGINAL author hardcoded (on their own machine). cwds are the working directories the learner might launch the script from. The question: which way of naming the data file finds it no matter where or on whose machine the script runs?",
  "script_dir": "/home/bob/hub/code/mod",
  "data_filename": "data.csv",
  "author_absolute": "/home/alice/hub/code/mod/data.csv",
  "cwds": ["/home/bob/hub/code/mod", "/home/bob", "/tmp"]
}
```

Each strategy is one line of path arithmetic. Cwd-relative joins the filename onto the launch directory; absolute returns the author's string unchanged; script-relative joins the filename onto the script's own directory.

```python filename=modules/teaching-and-portability/code/teach-inter-19/resolve.py:48-64 COMPLETE
def cwd_relative(cwd, filename):
    """open("data.csv") resolves against the current working directory."""
    return posixpath.join(cwd, filename)


def absolute_hardcoded(author_absolute):
    """open("/home/alice/.../data.csv") resolves to the author's machine path, unchanged."""
    return author_absolute


def script_relative(script_dir, filename):
    """Path(__file__).parent / "data.csv" resolves against the script's own directory."""
    return posixpath.join(script_dir, filename)


def finds(resolved, real):
    return resolved == real
```

Run `--resolve` to see where each strategy looks.

```text filename=--resolve
RESOLVE — where each strategy looks (file really at /home/bob/hub/code/mod/data.csv)
--------------------------------------------------------------------------
  launched from /home/bob/hub/code/mod cwd-relative -> /home/bob/hub/code/mod/data.csv  found
  launched from /home/bob              cwd-relative -> /home/bob/data.csv               NOT FOUND
  launched from /tmp                   cwd-relative -> /tmp/data.csv                    NOT FOUND
  absolute (any cwd):                  -> /home/alice/hub/code/mod/data.csv NOT FOUND
  script-relative (any cwd):           -> /home/bob/hub/code/mod/data.csv  found
```

The cwd-relative path finds the file only when the learner launches from the script's exact folder; from home or from /tmp it points at a directory with no data.csv. The author's absolute path aims at /home/alice — a machine the learner is not on — so it never finds it. Only the script-relative path resolves to the real /home/bob/…/mod/data.csv every time.

<svg role="img" aria-label="Three strategies aiming at the real file: cwd-relative hits only from one folder, absolute misses to another machine, script-relative always hits" viewBox="0 0 300 120" width="300" height="120">
  <rect x="200" y="50" width="90" height="20" fill="var(--s2)"/><text x="206" y="64" fill="var(--panel)" font-size="7">real: bob/mod/data.csv</text>
  <text x="10" y="20" fill="var(--s1)" font-size="8">cwd-relative</text>
  <line x1="80" y1="17" x2="200" y2="52" stroke="var(--s1)" stroke-width="1"/><text x="120" y="30" fill="var(--s1)" font-size="6">only from that folder</text>
  <line x1="80" y1="17" x2="150" y2="95" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="10" y="95" fill="var(--muted)" font-size="7">/tmp/data.csv (miss)</text>
  <text x="10" y="112" fill="var(--s1)" font-size="8">absolute</text>
  <line x1="70" y1="108" x2="120" y2="108" stroke="var(--s1)" stroke-width="1"/><text x="125" y="111" fill="var(--muted)" font-size="6">alice/mod (miss, wrong machine)</text>
  <text x="10" y="45" fill="var(--s2)" font-size="8">script-relative</text>
  <line x1="95" y1="42" x2="200" y2="58" stroke="var(--s2)" stroke-width="1.5"/><text x="120" y="52" fill="var(--s2)" font-size="6">always hits</text>
</svg>
^ Cwd-relative lands on the file only from one folder and misses elsewhere; absolute aims at another machine entirely; the script-relative arrow lands on the real file every time.

## Build

The coverage view counts, for each strategy, how many launch directories actually reach the real file.

```python filename=modules/teaching-and-portability/code/teach-inter-19/resolve.py:85-93 COMPLETE
    real = real_location(sd, fn)
    cr = sum(1 for cwd in cwds if finds(cwd_relative(cwd, fn), real))
    ab = sum(1 for _ in cwds if finds(absolute_hardcoded(au), real))
    sr = sum(1 for _ in cwds if finds(script_relative(sd, fn), real))
    print("COVERAGE — launch directories each strategy finds the file from (of %d)" % len(cwds))
    print("-" * 60)
    print("  cwd-relative:     %d / %d   (only from the script's own folder)" % (cr, len(cwds)))
    print("  absolute:         %d / %d   (wrong machine entirely)" % (ab, len(cwds)))
    print("  script-relative:  %d / %d   (works everywhere)" % (sr, len(cwds)))
```

Count the wins with `--coverage`.

```text filename=--coverage
COVERAGE — launch directories each strategy finds the file from (of 3)
------------------------------------------------------------
  cwd-relative:     1 / 3   (only from the script's own folder)
  absolute:         0 / 3   (wrong machine entirely)
  script-relative:  3 / 3   (works everywhere)
------------------------------------------------------------
  the script-relative path is independent of the working directory.
```

Cwd-relative works from 1 of 3 launch directories — the one that happens to be the script's folder. Absolute works from 0, because the whole path is wrong on this machine. Script-relative works from all 3, and it would work from any directory at all, because its resolved path does not contain the cwd anywhere: it is the script's directory plus the filename, full stop. That independence is the entire property you want.

<svg role="img" aria-label="Coverage bars: cwd-relative 1 of 3, absolute 0 of 3, script-relative 3 of 3" viewBox="0 0 300 110" width="300" height="110">
  <line x1="90" y1="12" x2="90" y2="85" stroke="var(--grid)" stroke-width="1"/>
  <line x1="90" y1="85" x2="285" y2="85" stroke="var(--grid)" stroke-width="1"/>
  <rect x="90" y="20" width="60" height="14" fill="var(--s1)"/><text x="154" y="31" fill="var(--muted)" font-size="8">cwd-relative 1/3</text>
  <rect x="90" y="42" width="2" height="14" fill="var(--s1)"/><text x="96" y="53" fill="var(--muted)" font-size="8">absolute 0/3</text>
  <rect x="90" y="64" width="180" height="14" fill="var(--s2)"/><text x="150" y="75" fill="var(--panel)" font-size="8">script-relative 3/3</text>
  <text x="90" y="102" fill="var(--muted)" font-size="8">only the script-relative path is launch-directory-proof</text>
</svg>
^ Script-relative is the only bar that reaches full coverage; the others fail from most directories or from the start on a different machine.

## Definition of done

The self-test pins all three outcomes: cwd-relative fails from some directory, the author's absolute path fails on this machine, script-relative finds the file from every directory, resolves the same regardless of cwd, and the file lives next to the script.

```python filename=modules/teaching-and-portability/code/teach-inter-19/resolve.py:104-117 COMPLETE
    cwd_relative_breaks_elsewhere = any(not finds(cwd_relative(cwd, fn), real) for cwd in cwds)
    bad = [c for c in cwds if not finds(cwd_relative(c, fn), real)]
    print("  cwd-relative fails from some launch directory = %s (e.g. %s)" % (cwd_relative_breaks_elsewhere, bad[0]))

    absolute_breaks_here = not finds(absolute_hardcoded(au), real)
    print("  the author's absolute path is not found on this machine = %s (%s)" % (absolute_breaks_here, au))

    script_relative_always_finds = all(finds(script_relative(sd, fn), real) for _ in cwds)
    print("  script-relative finds the file from every directory = %s" % script_relative_always_finds)

    script_relative_independent_of_cwd = len({script_relative(sd, fn) for _ in cwds}) == 1
    print("  script-relative resolves the same regardless of cwd = %s (%s)" % (script_relative_independent_of_cwd, script_relative(sd, fn)))

    file_next_to_script = real_location(sd, fn) == posixpath.join(sd, fn)
    print("  the data file lives next to the script = %s" % file_next_to_script)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — cwd-relative breaks from other directories, absolute breaks on other machines; script-relative works
----------------------------------------------------------------------------------------------------------------
  cwd-relative fails from some launch directory = True (e.g. /home/bob)
  the author's absolute path is not found on this machine = True (/home/alice/hub/code/mod/data.csv)
  script-relative finds the file from every directory = True
  script-relative resolves the same regardless of cwd = True (/home/bob/hub/code/mod/data.csv)
  the data file lives next to the script = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  cwd_relative_breaks_elsewhere=True  absolute_breaks_here=True  script_relative_always_finds=True  script_relative_independent_of_cwd=True  file_next_to_script=True
```

**Done means the fix is demonstrated across environments, not asserted: cwd-relative finds the file from 1 of 3 directories, absolute from 0, and script-relative from all 3 with an identical resolved path each time.**

## Boss fight

Script-relative fixed this. Predict whether it is still needed if you promise to always run the script from its own folder. It is tempting to think a discipline about how you launch replaces the code fix.

It is not, because you do not control how the next person launches it, and many launchers do not use the folder you expect. A cron job runs from the home directory or /; an IDE's run button often starts at the project root; an import from another script inherits that script's cwd; a packaged tool runs from wherever the user invoked it. "Always cd into the folder first" is an instruction that will be forgotten, automated around, or impossible in half the contexts the script ends up in. The script-relative path removes the assumption entirely, so no discipline is required — which is exactly what makes it portable.

The mirror-image mistake is reaching for an absolute path to "be safe" after a cwd-relative one bit you. That trades a launch-directory dependency for a machine dependency, which is strictly worse for sharing — it fails for literally everyone else, not just when they run from the wrong folder. The right anchor is neither the cwd nor the filesystem root; it is the script's own location, the one reference point that moves with the file.

```python filename=modules/teaching-and-portability/code/teach-inter-19/resolve.py:58-60 COMPLETE
def script_relative(script_dir, filename):
    """Path(__file__).parent / "data.csv" resolves against the script's own directory."""
    return posixpath.join(script_dir, filename)
```

**Build a data path from the script's own directory — Path(__file__).resolve().parent joined with the filename — so it opens from any launch directory and any machine, because the data ships with the script and the path is anchored to it.**

## External resources

The Python `pathlib` documentation on `Path(__file__)` and `.resolve().parent` — the idiom for locating a script's own directory, and why `resolve()` handles symlinks and relative invocations.

The distinction between `os.getcwd()` and a module's `__file__` — any Python packaging guide covers why the working directory is unreliable for locating bundled data, and points to `importlib.resources` for data inside installed packages.

This hub's "portable means a stranger can run it" module — the broader portability principle; script-relative paths are one of the concrete things a portability scan looks for.
