"""Resolve the data file relative to the script, or it opens only from the author's directory and machine.

An artifact usually ships with a data file next to its script. To open it, the code has to name a path, and the
two obvious ways both break for the next person. Naming the file relative to the CURRENT WORKING DIRECTORY --
open("data.csv") -- resolves against wherever the learner happened to launch the script, so it works only when
they run it from the script's own folder and fails with 'file not found' from anywhere else. Hardcoding the
ABSOLUTE path the author had -- open("/home/alice/hub/code/mod/data.csv") -- resolves to a directory that exists
only on the author's machine, so it fails for everyone else. One breaks on a different directory; the other
breaks on a different machine. Both are the same mistake: the path depends on the environment, not on the code.

The fix is to resolve the file relative to the SCRIPT'S OWN LOCATION. The script knows where it lives, so
building the path from the script's directory plus the filename points at the data file wherever the whole
folder is copied and whatever directory it is launched from. Every artifact in this hub does exactly this with
`HERE = Path(__file__).resolve().parent` and `DATA = HERE / "data.csv"`. The data file travels with the script,
so the path should be computed from the script, not from the shell's current directory or a machine-specific
absolute string.

On this fixture the script and its data file live at /home/bob/hub/code/mod/ on the learner's machine. The
cwd-relative path finds the file only when launched from that exact folder (1 of 3 directories). The author's
hardcoded absolute path (on /home/alice/...) never finds it. The script-relative path finds it from all three
directories. This computes all three.

  --resolve   where each strategy looks for the data file, from each working directory
  --coverage  how many of the launch directories each strategy actually finds the file from
  --check     cwd-relative breaks from other directories, absolute breaks on other machines; script-relative works

The locations are the fixture; every resolved path is computed. Stdlib only.
"""
import argparse
import json
import posixpath
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "paths.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def real_location(script_dir, filename):
    """Where the data file actually is on this machine: next to the script."""
    return posixpath.join(script_dir, filename)


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


# ----------------------------------------------------------------- printing

def resolve_view(data):
    sd, fn, au, cwds = data["script_dir"], data["data_filename"], data["author_absolute"], data["cwds"]
    real = real_location(sd, fn)
    print("RESOLVE — where each strategy looks (file really at %s)" % real)
    print("-" * 74)
    for cwd in cwds:
        cr = cwd_relative(cwd, fn)
        print("  launched from %-22s cwd-relative -> %-32s %s" % (cwd, cr, "found" if finds(cr, real) else "NOT FOUND"))
    print("  absolute (any cwd):                  -> %-32s %s" % (au, "found" if finds(au, real) else "NOT FOUND"))
    print("  script-relative (any cwd):           -> %-32s %s" % (script_relative(sd, fn), "found"))
    print("-" * 74)
    print("  only the script-relative path points at the real file every time.")


def coverage_view(data):
    sd, fn, au, cwds = data["script_dir"], data["data_filename"], data["author_absolute"], data["cwds"]
    real = real_location(sd, fn)
    cr = sum(1 for cwd in cwds if finds(cwd_relative(cwd, fn), real))
    ab = sum(1 for _ in cwds if finds(absolute_hardcoded(au), real))
    sr = sum(1 for _ in cwds if finds(script_relative(sd, fn), real))
    print("COVERAGE — launch directories each strategy finds the file from (of %d)" % len(cwds))
    print("-" * 60)
    print("  cwd-relative:     %d / %d   (only from the script's own folder)" % (cr, len(cwds)))
    print("  absolute:         %d / %d   (wrong machine entirely)" % (ab, len(cwds)))
    print("  script-relative:  %d / %d   (works everywhere)" % (sr, len(cwds)))
    print("-" * 60)
    print("  the script-relative path is independent of the working directory.")


def check(data):
    print("SELF-TEST — cwd-relative breaks from other directories, absolute breaks on other machines; script-relative works")
    print("-" * 112)
    sd, fn, au, cwds = data["script_dir"], data["data_filename"], data["author_absolute"], data["cwds"]
    real = real_location(sd, fn)

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

    ok = cwd_relative_breaks_elsewhere and absolute_breaks_here and script_relative_always_finds and script_relative_independent_of_cwd and file_next_to_script
    print("-" * 112)
    print("SELF-TEST %s  cwd_relative_breaks_elsewhere=%s  absolute_breaks_here=%s  script_relative_always_finds=%s  script_relative_independent_of_cwd=%s  file_next_to_script=%s"
          % ("PASS" if ok else "FAIL", cwd_relative_breaks_elsewhere, absolute_breaks_here, script_relative_always_finds, script_relative_independent_of_cwd, file_next_to_script))
    return ok


def main():
    p = argparse.ArgumentParser(description="Resolve a data path relative to the script so it opens from any directory and machine.")
    p.add_argument("--resolve", action="store_true")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("script_dir=%s  data=%s  cwds=%d  file=%s  (the locations are a fixture)"
          % (data["script_dir"], data["data_filename"], len(data["cwds"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.resolve:
        resolve_view(data)
    elif args.coverage:
        coverage_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
