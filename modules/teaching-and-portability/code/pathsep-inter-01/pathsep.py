"""Parse paths with the library or on both separators -- never a hardcoded '/' -- because the directory separator is OS-dependent, so splitting on '/' returns the whole path when it holds a backslash.

Pulling the filename off a path looks like a one-liner: split on '/', take the last piece. It runs correctly on the machine it was written on and carries a latent bug that fires somewhere else, because the character that separates directories is not universal. POSIX systems -- Linux, macOS -- use '/'. Windows uses '\\' (backslash), while also tolerating '/'. So 'the separator' is a platform fact, and any code that bakes in one value has made an assumption about where it will run and where its data came from.

That assumption breaks in two ways. The code can run on the other OS, where the paths it constructs and parses use the other separator. Or -- and this bites even on a single machine -- the code can be handed a path string that originated on the other OS: an uploaded file, a path stored in a database by a Windows client, an entry in a cross-platform archive. Split a backslash path on '/', and the split finds no delimiter and returns the whole string as one piece, so the 'filename' you extract is actually the entire path. It is a silent wrong answer, not a crash, which is what makes it survive to production.

The fix is to stop hardcoding the separator. For paths on the current system, use the standard library -- os.path.basename and os.path.split, or pathlib.PurePath -- which knows the platform's separator. For parsing paths that may have come from either OS, split on both '/' and '\\', so a backslash path is handled the same as a forward-slash one. The principle is the same one behind fixing encodings and locales: a value the environment controls (here, the separator) must never be assumed constant in code that has to be portable.

The rule: extract and build path components with the path library or by handling both '/' and '\\', not a hardcoded '/', because the directory separator is OS-dependent -- so a '/'-only split returns the whole path when it contains a backslash, silently yielding the wrong filename on the other OS or on foreign path data.

On this fixture three paths mix separators. The naive '/'-split extracts the correct filename from only the one pure-POSIX path (1 of 3); the separator-agnostic parse extracts all three correctly. This computes both.

  --parse    each path's filename by the naive '/'-split vs the separator-agnostic parse
  --score    how many filenames each method extracts correctly
  --check    the naive '/'-split fails on backslash paths; the separator-agnostic parse handles all of them

paths and expected are the fixture; the extracted filenames and the counts are computed. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pathsep.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_basename(path):
    """Hardcode '/': take the last piece after a forward slash."""
    return path.split("/")[-1]


def portable_basename(path):
    """Separator-agnostic: split on either '/' or '\\'."""
    return re.split(r"[/\\]", path)[-1]


# ----------------------------------------------------------------- printing

def parse_view(data):
    print("PARSE — filename extracted by the naive '/'-split vs the separator-agnostic parse")
    print("-" * 72)
    print("  path              naive split('/')   separator-agnostic   correct")
    for p, exp in zip(data["paths"], data["expected"]):
        n, pt = naive_basename(p), portable_basename(p)
        print("  %-16s  %-17s  %-19s  %s" % (repr(p), repr(n), repr(pt), exp))
    print("-" * 72)
    print("  a backslash path split on '/' comes back whole — the filename is the entire path")


def score_view(data):
    paths, expected = data["paths"], data["expected"]
    naive_ok = sum(1 for p, e in zip(paths, expected) if naive_basename(p) == e)
    port_ok = sum(1 for p, e in zip(paths, expected) if portable_basename(p) == e)
    print("SCORE — filenames extracted correctly (of %d)" % len(paths))
    print("-" * 50)
    print("  naive '/'-split          = %d / %d" % (naive_ok, len(paths)))
    print("  separator-agnostic parse = %d / %d" % (port_ok, len(paths)))
    print("-" * 50)
    print("  the naive split only handles pure forward-slash paths")


def check(data):
    print("SELF-TEST — the naive '/'-split fails on backslash paths; the separator-agnostic parse handles all of them")
    print("-" * 116)
    paths, expected = data["paths"], data["expected"]
    naive_ok = [p for p, e in zip(paths, expected) if naive_basename(p) == e]
    port_ok = [p for p, e in zip(paths, expected) if portable_basename(p) == e]

    has_backslash_path = any("\\" in p for p in paths)
    print("  some path uses the Windows backslash separator = %s" % has_backslash_path)

    naive_fails_some = len(naive_ok) < len(paths)
    print("  the naive '/'-split gets some filenames wrong = %s (%d of %d correct)" % (naive_fails_some, len(naive_ok), len(paths)))

    naive_returns_whole_path = any(naive_basename(p) == p and p != e for p, e in zip(paths, expected))
    print("  a backslash path split on '/' returns the whole path = %s" % naive_returns_whole_path)

    portable_gets_all = len(port_ok) == len(paths)
    print("  the separator-agnostic parse gets every filename right = %s (%d of %d)" % (portable_gets_all, len(port_ok), len(paths)))

    portable_beats_naive = len(port_ok) > len(naive_ok)
    print("  the separator-agnostic parse beats the naive split = %s (%d > %d)" % (portable_beats_naive, len(port_ok), len(naive_ok)))

    ok = (has_backslash_path and naive_fails_some and naive_returns_whole_path and portable_gets_all and portable_beats_naive)
    print("-" * 116)
    print("SELF-TEST %s  has_backslash_path=%s  naive_fails_some=%s  naive_returns_whole_path=%s  portable_gets_all=%s  portable_beats_naive=%s"
          % ("PASS" if ok else "FAIL", has_backslash_path, naive_fails_some, naive_returns_whole_path, portable_gets_all, portable_beats_naive))
    return ok


def main():
    p = argparse.ArgumentParser(description="Path separators: extract and build path components with the path library or by handling both '/' and '\\\\', not a hardcoded '/', because the directory separator is OS-dependent -- so a '/'-only split returns the whole path when it contains a backslash, silently yielding the wrong filename on the other OS or on foreign path data.")
    p.add_argument("--parse", action="store_true")
    p.add_argument("--score", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("paths=%s  file=%s  (the paths are a fixture)" % (data["paths"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.parse:
        parse_view(data)
    elif args.score:
        score_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
