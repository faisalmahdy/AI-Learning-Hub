"""Pin the dependency version, or the next person installs a different one and your documented output breaks.

An artifact that depends on a library declares that dependency. If it declares a loose range -- "anything at
or above 1.0" -- the installer resolves it to whatever the newest matching version happens to be AT INSTALL
TIME. You installed on a day when the newest was 1.4.0; a learner installs a month later when 1.5.0 has
shipped, and gets 1.5.0. If anything changed between those versions -- a default, an output format, a bug
fix that alters a number -- the learner's run no longer matches your documented output, and they cannot tell
whether they made a mistake or the library moved under them. Your "you should see X" was only true against
the version you happened to have.

Pinning fixes it: declare the exact version -- "==1.4.0" -- so every install resolves to that same version
regardless of what has shipped since. The run becomes reproducible across people and dates, because the
dependency is frozen to the one you tested and documented against. A lockfile does this for the whole
dependency tree at once, capturing every transitive version so the entire environment is identical for the
next person. Loose ranges are convenient for getting updates; pinned versions are what make a documented,
checkable result.

On this fixture the library has 1.4.0 (behavior 'A') and a later 1.5.0 (behavior 'B'). A loose ">=1.0"
resolves to 1.4.0 on an early install date and 1.5.0 on a later one -- two different behaviors, and only
one matches the documented 'A'. A pinned "==1.4.0" resolves to 1.4.0 on both dates, always matching the
documented output. This computes both.

  --resolve    what each spec resolves to at an early vs a late install date
  --behave     the behavior each install produces, and whether it matches the documented output
  --check      the loose range resolves differently over time and breaks the doc; the pin stays reproducible

The available versions, specs, and dates are the fixture; every resolution is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "deps.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def parse(v):
    return tuple(int(x) for x in v.split("."))


def matches(version, spec):
    if spec["type"] == "exact":
        return version == spec["version"]
    return parse(version) >= parse(spec["min"])   # a loose lower-bound range


def resolve(spec, install_day, versions):
    """The newest version that matches the spec AND has been released by the install day."""
    available = [v for v in versions if versions[v]["released_day"] <= install_day and matches(v, spec)]
    return max(available, key=parse) if available else None


def behavior(spec, install_day, versions):
    v = resolve(spec, install_day, versions)
    return versions[v]["behavior"] if v else None


# ----------------------------------------------------------------- printing

def resolve_view(data):
    versions, early, late = data["versions"], data["early_day"], data["late_day"]
    print("RESOLVE — what each spec resolves to at day %d (early) vs day %d (late)" % (early, late))
    print("-" * 58)
    for name, spec in data["specs"].items():
        print("  %-8s (%s)  early -> %s   late -> %s"
              % (name, spec_str(spec), resolve(spec, early, versions), resolve(spec, late, versions)))
    print("-" * 58)
    print("  the loose range picks up the newer version at the later date.")


def spec_str(spec):
    return "==%s" % spec["version"] if spec["type"] == "exact" else ">=%s" % spec["min"]


def behave_view(data):
    versions, early, late, doc = data["versions"], data["early_day"], data["late_day"], data["documented_behavior"]
    print("BEHAVE — behavior per install, vs the documented output %r" % doc)
    print("-" * 58)
    for name, spec in data["specs"].items():
        be, bl = behavior(spec, early, versions), behavior(spec, late, versions)
        print("  %-8s early %r (%s)   late %r (%s)"
              % (name, be, "match" if be == doc else "MISMATCH", bl, "match" if bl == doc else "MISMATCH"))
    print("-" * 58)
    print("  only the pinned spec matches the documented output at both dates.")


def check(data):
    print("SELF-TEST — the loose range resolves differently over time and breaks the doc; the pin stays reproducible")
    print("-" * 100)
    versions, early, late, doc = data["versions"], data["early_day"], data["late_day"], data["documented_behavior"]
    loose, pinned = data["specs"]["loose"], data["specs"]["pinned"]

    loose_resolves_differently = resolve(loose, early, versions) != resolve(loose, late, versions)
    print("  the loose range resolves to different versions over time = %s (%s vs %s)"
          % (loose_resolves_differently, resolve(loose, early, versions), resolve(loose, late, versions)))

    loose_behavior_differs = behavior(loose, early, versions) != behavior(loose, late, versions)
    print("  the loose range produces different behavior over time = %s (%r vs %r)"
          % (loose_behavior_differs, behavior(loose, early, versions), behavior(loose, late, versions)))

    loose_breaks_doc = behavior(loose, late, versions) != doc
    print("  the late loose install no longer matches the documented output = %s" % loose_breaks_doc)

    pinned_resolves_same = resolve(pinned, early, versions) == resolve(pinned, late, versions)
    print("  the pinned spec resolves to the same version at both dates = %s (%s)" % (pinned_resolves_same, resolve(pinned, early, versions)))

    pinned_matches_doc = behavior(pinned, early, versions) == doc and behavior(pinned, late, versions) == doc
    print("  the pinned spec matches the documented output at both dates = %s" % pinned_matches_doc)

    ok = loose_resolves_differently and loose_behavior_differs and loose_breaks_doc and pinned_resolves_same and pinned_matches_doc
    print("-" * 100)
    print("SELF-TEST %s  loose_resolves_differently=%s  loose_behavior_differs=%s  loose_breaks_doc=%s  pinned_resolves_same=%s  pinned_matches_doc=%s"
          % ("PASS" if ok else "FAIL", loose_resolves_differently, loose_behavior_differs, loose_breaks_doc, pinned_resolves_same, pinned_matches_doc))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pin the dependency version so a documented result stays reproducible.")
    p.add_argument("--resolve", action="store_true")
    p.add_argument("--behave", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("versions=%d  specs=%s  early_day=%d  late_day=%d  file=%s  (the versions and specs are a fixture)"
          % (len(data["versions"]), list(data["specs"]), data["early_day"], data["late_day"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.resolve:
        resolve_view(data)
    elif args.behave:
        behave_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
