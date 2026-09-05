#!/usr/bin/env python3
"""Portable means a stranger can run it: scan for what only works on your machine.

Extracting a personal project into a teachable module is mostly deleting: the
absolute path to your home directory, the hardcoded API token, your email, the
IP of the box on your desk. Each one reads fine to you because it works on your
machine, and each one is a wall a stranger hits on line one. A module is not
portable because it looks generic; it is portable when a scan for machine-specific
references comes back empty. This scans an extracted module before and after
de-personalization and counts what would stop someone else from running it.

  --scan V       the violations in variant V (raw|portable): file, line, kind, snippet
  --rules        the machine-specific patterns the scan looks for
  --compare      violation counts, raw (as-extracted) vs portable (de-personalized)
  --check        the raw module has blockers and a leaked secret; the portable one has none

Stdlib only (re). No network. The two module variants are a fixture. Deterministic.
Point the scan at your own extracted module before you publish it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "files.json"

# machine-specific patterns that break a module for anyone but its author.
RULES = [
    ("home_path", r"/(?:home|Users)/[A-Za-z][\w.-]*"),
    ("hardcoded_secret", r"\b(?:sk-[A-Za-z0-9]{6,}|AKIA[0-9A-Z]{8,}|ghp_[A-Za-z0-9]{6,})\b"),
    ("personal_email", r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ("local_address", r"\b(?:127\.0\.0\.1|localhost|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(?::\d+)?\b"),
]


def load():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    return data["variants"]


def scan(files):
    """Every machine-specific reference in a set of files: (file, line, kind, text)."""
    hits = []
    for name, content in files.items():
        for lineno, line in enumerate(content.splitlines(), 1):
            for kind, pat in RULES:
                for m in re.finditer(pat, line):
                    hits.append((name, lineno, kind, m.group(0)))
    return hits


def is_portable(files):
    return len(scan(files)) == 0


# ------------------------------------------------------------------- printing

def scan_view(variants, which):
    files = variants[which]
    hits = scan(files)
    print("SCAN — %s variant" % which)
    print("-" * 68)
    for name, lineno, kind, text in hits:
        print("  %-12s:%-3d  %-17s %s" % (name, lineno, kind, text))
    if not hits:
        print("  no machine-specific references -- a stranger can run this.")
    print("-" * 68)
    print("  %d blocker(s). portable = %s" % (len(hits), is_portable(files)))


def rules_view():
    print("RULES — what makes a module unrunnable for anyone but its author")
    print("-" * 68)
    for kind, pat in RULES:
        print("  %-17s %s" % (kind, pat))
    print("-" * 68)
    print("  each is a reference that resolves on your machine and nowhere else.")


def compare_view(variants):
    print("PORTABILITY — violations, as-extracted vs de-personalized")
    print("-" * 68)
    for which in ("raw", "portable"):
        hits = scan(variants[which])
        kinds = sorted({k for _, _, k, _ in hits})
        print("  %-10s %d blocker(s)  %s" % (which, len(hits), kinds or "clean"))
    print("-" * 68)
    print("  'raw' looks done and runs -- for its author. 'portable' runs for anyone.")


def check(variants):
    print("SELF-TEST — the raw module blocks a stranger and leaks a secret; portable is clean")
    print("-" * 68)
    raw, portable = variants["raw"], variants["portable"]
    raw_hits, port_hits = scan(raw), scan(portable)

    raw_blocked = len(raw_hits) > 0
    portable_clean = len(port_hits) == 0
    print("  raw has machine-specific blockers = %s (%d)" % (raw_blocked, len(raw_hits)))
    print("  portable has none = %s" % portable_clean)

    # the most dangerous kind: a hardcoded secret must be caught.
    raw_kinds = {k for _, _, k, _ in raw_hits}
    catches_secret = "hardcoded_secret" in raw_kinds
    print("  the scan catches the hardcoded secret in raw = %s" % catches_secret)

    # every rule kind that fires in raw is absent from portable.
    port_kinds = {k for _, _, k, _ in port_hits}
    all_fixed = raw_kinds and not (raw_kinds & port_kinds)
    print("  every blocker kind in raw is gone in portable = %s (raw=%s)" % (all_fixed, sorted(raw_kinds)))

    det = scan(raw) == scan(raw)
    ok = raw_blocked and portable_clean and catches_secret and all_fixed and det
    print("-" * 68)
    print("SELF-TEST %s  raw_blocked=%s  portable_clean=%s  catches_secret=%s  all_fixed=%s"
          % ("PASS" if ok else "FAIL", raw_blocked, portable_clean, catches_secret, all_fixed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Scan an extracted module for machine-specific references.")
    p.add_argument("--scan", metavar="V", choices=["raw", "portable"])
    p.add_argument("--rules", action="store_true")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    variants = load()
    print("variants=%s  rules=%d  file=%s  (module variants are a fixture)"
          % (list(variants), len(RULES), DATA.name))
    print("")

    if args.check:
        return 0 if check(variants) else 1
    if args.scan:
        scan_view(variants, args.scan)
    elif args.rules:
        rules_view()
    elif args.compare:
        compare_view(variants)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
