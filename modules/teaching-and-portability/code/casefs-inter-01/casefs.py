"""Match filenames by exact case -- a case-insensitive filesystem hides a wrong-case reference that breaks on Linux.

Whether two filenames are 'the same file' depends on the filesystem, and the default differs across the platforms your
code will run on. macOS (HFS+/APFS in its default configuration) and Windows (NTFS) are case-INSENSITIVE: 'Data.csv',
'data.csv', and 'DATA.CSV' all refer to the one file, so an import or an open() with the wrong case still finds it. Linux
(ext4, xfs, and most others) is case-SENSITIVE: those are three different names, and only an exact-case match resolves.
This split is a portability trap because most developers write and test on macOS or Windows, while most continuous
integration and production servers run Linux. So a reference whose case does not match the file on disk works perfectly on
the author's laptop -- the case-insensitive filesystem quietly forgives it -- and then fails the moment it runs on Linux,
where the forgiving lookup is gone. It is the canonical 'works on my machine': not a difference in the code, but a
difference in what the filesystem considers a match.

The failure is silent until the platform changes. An `import Utils` that should be `import utils`, an `open("Data.csv")`
for a file committed as `data.csv`, a template path `src/Model.py` referenced as `src/model.py` -- each resolves on the
case-insensitive machine and raises FileNotFoundError (or ModuleNotFoundError) on the case-sensitive one, and the author,
never seeing the error locally, cannot reproduce the CI failure. The fix is discipline plus a check: always spell a
filename in code with the exact case it has on disk, and add a case-sensitive verification (a lookup that requires an exact
match, which is what a Linux filesystem does) to catch a mismatch before it ships.

There is a mirror hazard in the other direction. Two files whose names differ only in case -- 'Log.txt' and 'log.txt' --
are two distinct files on a case-sensitive filesystem, so a Linux author can commit both; but on a case-insensitive
filesystem they are the same name, so checking out that repository on macOS or Windows collides them, and one silently
overwrites or shadows the other. So the rule is symmetric: never rely on case to distinguish two files, and never rely on
case-insensitivity to find one.

The rule: reference every filename in code with its exact on-disk case, and never let two files differ only in case,
because a case-insensitive filesystem (macOS/Windows) hides a wrong-case reference that then breaks on a case-sensitive one
(Linux CI/production), and a case-sensitive filesystem allows two case-differing files that then collide on a
case-insensitive checkout.

On these fixtures the code references three files. On a case-insensitive filesystem all three resolve; on a case-sensitive
one only the exactly-cased 'config.yaml' resolves, and 'Data.csv' and 'src/model.py' fail because the files are 'data.csv'
and 'src/Model.py'. And the pair 'Log.txt'/'log.txt', two files on Linux, collide to one name on a case-insensitive
checkout. This computes both.

  --lookup     each reference: the exact file it should match, and whether it resolves case-sensitively vs case-insensitively
  --collision  the two case-differing files: distinct on a case-sensitive filesystem, collapsed to one on a case-insensitive one
  --check      the mis-cased references resolve case-insensitively but fail case-sensitively; the case-only pair collides

files_on_disk, references, and distinct_on_linux are the fixture; every lookup result and collision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "casefs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def found_case_sensitive(files, name):
    """A case-sensitive filesystem (Linux): only an exact-case match resolves."""
    return name in files


def found_case_insensitive(files, name):
    """A case-insensitive filesystem (macOS/Windows): a case-folded match resolves."""
    lowered = {f.lower(): f for f in files}
    return name.lower() in lowered


def insensitive_match(files, name):
    """The actual on-disk file a case-insensitive lookup would resolve `name` to, or None."""
    return {f.lower(): f for f in files}.get(name.lower())


# ----------------------------------------------------------------- printing

def lookup_view(data):
    files, refs = data["files_on_disk"], data["references"]
    print("LOOKUP — how each reference resolves on the two kinds of filesystem")
    print("-" * 78)
    print("  reference in code    on-disk file            case-sensitive   case-insensitive")
    for ref in refs:
        disk = insensitive_match(files, ref)
        cs = "FOUND" if found_case_sensitive(files, ref) else "MISSING"
        ci = "found" if found_case_insensitive(files, ref) else "missing"
        print("  %-20s %-23s %-16s %s" % (ref, disk if disk else "(none)", cs, ci))
    print("-" * 78)
    print("  every reference resolves case-insensitively (macOS/Windows); the mis-cased ones fail on Linux.")


def collision_view(data):
    pair = data["distinct_on_linux"]
    print("COLLISION — two filenames differing only in case")
    print("-" * 58)
    print("  committed files: %s" % pair)
    print("  on a case-sensitive filesystem (Linux):   %d distinct files" % len(set(pair)))
    folded = {name.lower() for name in pair}
    print("  on a case-insensitive filesystem (mac/win): %d file(s) -- %s collide to %s"
          % (len(folded), pair, sorted(folded)))
    print("-" * 58)
    print("  committing both is fine on Linux and breaks the checkout on macOS/Windows.")


def check(data):
    print("SELF-TEST — mis-cased references resolve case-insensitively but fail case-sensitively; the case-only pair collides")
    print("-" * 116)
    files, refs = data["files_on_disk"], data["references"]

    insensitive_finds_all = all(found_case_insensitive(files, r) for r in refs)
    print("  every reference resolves on a case-insensitive filesystem = %s" % insensitive_finds_all)

    broken = [r for r in refs if not found_case_sensitive(files, r)]
    sensitive_misses_some = len(broken) > 0
    print("  some references fail on a case-sensitive filesystem = %s (broken: %s)" % (sensitive_misses_some, broken))

    exact_ref_found_both = found_case_sensitive(files, "config.yaml") and found_case_insensitive(files, "config.yaml")
    print("  the exactly-cased 'config.yaml' resolves on both = %s" % exact_ref_found_both)

    pair = data["distinct_on_linux"]
    collision_on_insensitive = len({n.lower() for n in pair}) < len(set(pair))
    print("  the case-only pair %s collides on a case-insensitive filesystem = %s (%d -> %d names)"
          % (pair, collision_on_insensitive, len(set(pair)), len({n.lower() for n in pair})))

    verdicts_differ = any(found_case_sensitive(files, r) != found_case_insensitive(files, r) for r in refs)
    print("  the two filesystems disagree on at least one reference = %s" % verdicts_differ)

    ok = insensitive_finds_all and sensitive_misses_some and exact_ref_found_both and collision_on_insensitive and verdicts_differ
    print("-" * 116)
    print("SELF-TEST %s  insensitive_finds_all=%s  sensitive_misses_some=%s  exact_ref_found_both=%s  collision_on_insensitive=%s  verdicts_differ=%s"
          % ("PASS" if ok else "FAIL", insensitive_finds_all, sensitive_misses_some, exact_ref_found_both, collision_on_insensitive, verdicts_differ))
    return ok


def main():
    p = argparse.ArgumentParser(description="Filesystem case sensitivity: reference every filename in code with its exact on-disk case and never let two files differ only in case, because a case-insensitive filesystem (macOS/Windows) hides a wrong-case reference that then breaks on a case-sensitive one (Linux CI/production), and a case-sensitive filesystem allows two case-differing files that then collide on a case-insensitive checkout.")
    p.add_argument("--lookup", action="store_true")
    p.add_argument("--collision", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("files_on_disk=%s  references=%s  file=%s  (the files and references are a fixture)"
          % (data["files_on_disk"], data["references"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.lookup:
        lookup_view(data)
    elif args.collision:
        collision_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
