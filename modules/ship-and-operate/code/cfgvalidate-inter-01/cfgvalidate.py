"""Validate the whole configuration at startup and refuse to boot on any error -- lazy per-field validation surfaces one bad value only when the first request happens to read it, in production, and never catches the fields no request touched.

A configuration value is only checked when something reads it, and a service reads its fields at different times. The port is read at boot, a timeout on the first outbound call, a feature mode only when that feature is hit, a retry count only when something fails. So 'validate a field when it is used' means the bad values reveal themselves on a schedule set by traffic, not by you.

That schedule is the problem. An invalid field on a common path crashes the service in production the moment real traffic touches it -- after a green deploy, mid-incident, one field at a time, with every other bad field still hidden behind its own code path. And an invalid field on a path that your smoke test never exercised is not caught at all: it ships, and waits for the rare request months later that finally reads it.

Startup validation removes the dependence on traffic. Run every field's rule once, before the service accepts a single request, and refuse to start if any field fails -- printing all the errors together. Now the bad config is caught at deploy time, where a human is watching the rollout and can fix it, and it is caught completely: every invalid field, not just the ones today's requests happened to reach.

On this fixture the config has three invalid fields (port out of range, a negative timeout, an unknown mode). Startup validation reports all three and refuses to boot. The lazy run serves two requests fine, crashes on the third when it first reads the timeout, and never even looks at the invalid port or mode -- which would crash some later request in production. This computes both.

  --lazy      validate each field as the running service first reads it: one late crash, two errors still lurking
  --startup   validate every field before accepting traffic: all three errors at once, refuse to boot
  --check     startup catches every invalid field before serving, while the lazy run crashes late and leaves invalid fields undetected

config and access_order are the fixture; the startup errors and the lazy run's single crash and lurking fields are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "cfgvalidate.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def validate_field(name, value):
    """Return None if the field is valid, else a human-readable reason -- one rule per field."""
    if name == "port":
        return None if isinstance(value, int) and 1 <= value <= 65535 else "port %r out of range 1..65535" % value
    if name == "timeout_seconds":
        return None if isinstance(value, (int, float)) and value > 0 else "timeout_seconds %r must be > 0" % value
    if name == "mode":
        return None if value in ("fast", "safe") else "mode %r not in {fast, safe}" % value
    if name == "workers":
        return None if isinstance(value, int) and value >= 1 else "workers %r must be >= 1" % value
    if name == "retries":
        return None if isinstance(value, int) and value >= 0 else "retries %r must be >= 0" % value
    return "unknown field %r" % name


def validate_at_startup(config):
    """Check every field once, before serving; return the list of all errors (empty means safe to boot)."""
    return [err for name, value in config.items() if (err := validate_field(name, value)) is not None]


def lazy_run(config, access_order):
    """Validate each field only as it is first read; stop at the first error (the production crash)."""
    for step, name in enumerate(access_order):
        err = validate_field(name, config[name])
        if err is not None:
            return {"crashed_at_step": step, "error": err, "served_before_crash": step}
    return {"crashed_at_step": None, "error": None, "served_before_crash": len(access_order)}


def lurking_invalid_fields(config, access_order):
    """Invalid fields the lazy run never reads -- they ship and crash some later request in production."""
    return [name for name in config if validate_field(name, config[name]) is not None and name not in access_order]


# ----------------------------------------------------------------- printing

def lazy_view(data):
    config, order = data["config"], data["access_order"]
    run = lazy_run(config, order)
    print("LAZY — validate each field only when the running service first reads it")
    print("-" * 64)
    print("  read order: %s" % order)
    if run["error"] is not None:
        print("  served %d request(s) OK, then crashed reading '%s' at step %d:"
              % (run["served_before_crash"], order[run["crashed_at_step"]], run["crashed_at_step"]))
        print("    %s" % run["error"])
    print("  invalid fields never read this run (still lurking): %s" % lurking_invalid_fields(config, order))
    print("-" * 64)
    print("  the crash is in production, and the untouched bad fields are still waiting")


def startup_view(data):
    config = data["config"]
    errors = validate_at_startup(config)
    print("STARTUP — validate every field before accepting any traffic")
    print("-" * 64)
    print("  checked %d fields; %d invalid:" % (len(config), len(errors)))
    for err in errors:
        print("    %s" % err)
    print("  decision: %s" % ("REFUSE TO START" if errors else "start"))
    print("-" * 64)
    print("  every bad field surfaced at once, at deploy time, before a single request")


def check(data):
    print("SELF-TEST — startup catches every invalid field before serving, while the lazy run crashes late and leaves invalid fields undetected")
    print("-" * 112)
    config, order = data["config"], data["access_order"]
    all_invalid = [n for n in config if validate_field(n, config[n]) is not None]
    startup_errors = validate_at_startup(config)
    run = lazy_run(config, order)
    lurking = lurking_invalid_fields(config, order)

    startup_catches_all = len(startup_errors) == len(all_invalid) and len(all_invalid) > 0
    print("  startup validation reports every invalid field = %s (%d of %d)" % (startup_catches_all, len(startup_errors), len(all_invalid)))

    startup_before_serving = len(startup_errors) > 0
    print("  startup validation fails before any request is served = %s (refuse to boot)" % startup_before_serving)

    lazy_crashes_after_serving = run["crashed_at_step"] is not None and run["served_before_crash"] > 0
    print("  the lazy run serves real requests, then crashes = %s (served %d, crashed at step %d)"
          % (lazy_crashes_after_serving, run["served_before_crash"], run["crashed_at_step"]))

    lazy_leaves_errors_lurking = len(lurking) > 0
    print("  the lazy run leaves invalid fields undetected = %s (%s)" % (lazy_leaves_errors_lurking, lurking))

    startup_strictly_better = startup_catches_all and lazy_leaves_errors_lurking
    print("  startup catches what the lazy run misses = %s" % startup_strictly_better)

    ok = (startup_catches_all and startup_before_serving and lazy_crashes_after_serving
          and lazy_leaves_errors_lurking and startup_strictly_better)
    print("-" * 112)
    print("SELF-TEST %s  startup_catches_all=%s  startup_before_serving=%s  lazy_crashes_after_serving=%s  lazy_leaves_errors_lurking=%s  startup_strictly_better=%s"
          % ("PASS" if ok else "FAIL", startup_catches_all, startup_before_serving, lazy_crashes_after_serving,
             lazy_leaves_errors_lurking, startup_strictly_better))
    return ok


def main():
    p = argparse.ArgumentParser(description="Config validation at startup: validate every configuration field once before accepting traffic and refuse to boot on any error, rather than validating each field lazily when first read, because lazy validation surfaces a bad value only when a request happens to touch it -- crashing in production, one field at a time, and never catching the fields no request exercised.")
    p.add_argument("--lazy", action="store_true")
    p.add_argument("--startup", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("config=%s  access_order=%s  file=%s  (these are a fixture)"
          % (data["config"], data["access_order"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.lazy:
        lazy_view(data)
    elif args.startup:
        startup_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
