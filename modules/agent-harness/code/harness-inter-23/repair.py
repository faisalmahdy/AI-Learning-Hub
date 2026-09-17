r"""Repair the model's tool-call JSON before parsing, or a code fence aborts a turn that expressed a perfect call.

The model's output is text, and the harness turns that text into a tool call by parsing it as JSON. A strict
parser accepts only perfectly-formed JSON -- and models, being trained on prose and Markdown, routinely emit JSON
that is CLEAR but not strictly valid: wrapped in a ```json code fence, ending with a trailing comma, or a similar
surface-level slip. The call the model meant is unambiguous, but json.loads raises on the extra characters, and if
the harness treats a parse failure as a hard error it throws away the whole step -- the model has to be re-prompted,
the turn is wasted, and a run stutters on a mistake that changed none of the actual arguments.

A lightweight repair pass fixes the common malformations before parsing, with no model round-trip. Strip the code
fence if the string is wrapped in one; remove a trailing comma before a closing brace or bracket. These are the
mistakes models make most, and they are purely syntactic -- repairing them cannot change the call's meaning,
because the tool name and arguments are untouched. What repair must NOT do is pretend to fix everything: a
genuinely malformed structure (a missing comma BETWEEN fields, a truncated object) is not something a few regexes
can safely reconstruct, and guessing risks inventing a call the model never made. So repair recovers the easy,
unambiguous cases and lets the genuinely-broken ones fail loudly, which is the right split -- salvage the slips,
escalate the real errors.

On this fixture four candidate strings: a valid one, a fenced one, one with a trailing comma, and one missing a
comma between fields. Strict parsing accepts only the valid one -- 1 of 4. Repair-then-parse accepts the valid,
fenced, and trailing-comma ones -- 3 of 4 -- while the missing-comma structural error stays broken. This computes
both.

  --parse      each candidate under strict parsing vs repair-then-parse, and why
  --recover    how many calls each approach recovers, and which malformation stays broken
  --check      strict rejects the repairable slips; repair recovers them; the structural error still fails

The candidate strings are the fixture; every parse is real. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "calls.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def parses(raw):
    """Does the string parse as strict JSON?"""
    try:
        json.loads(raw)
        return True
    except json.JSONDecodeError:
        return False


def repair(raw):
    """Fix common model slips: strip a Markdown code fence and remove trailing commas. Does not fix structure."""
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)   # opening fence
    s = re.sub(r"\s*```$", "", s)             # closing fence
    s = re.sub(r",(\s*[}\]])", r"\1", s)      # trailing comma before } or ]
    return s.strip()


# ----------------------------------------------------------------- printing

def parse_view(data):
    print("PARSE — strict parsing vs repair-then-parse")
    print("-" * 60)
    print("  candidate        strict   repaired")
    for c in data["candidates"]:
        print("  %-15s  %-6s   %s" % (c["id"], parses(c["raw"]), parses(repair(c["raw"]))))
    print("-" * 60)
    print("  the fenced and trailing-comma slips fail strict but parse after repair.")


def recover_view(data):
    cands = data["candidates"]
    strict = [c["id"] for c in cands if parses(c["raw"])]
    repaired = [c["id"] for c in cands if parses(repair(c["raw"]))]
    broken = [c["id"] for c in cands if not parses(repair(c["raw"]))]
    print("RECOVER — calls recovered by each approach (of %d)" % len(cands))
    print("-" * 60)
    print("  strict parsing:      %d recovered   %s" % (len(strict), strict))
    print("  repair-then-parse:   %d recovered   %s" % (len(repaired), repaired))
    print("  still broken after repair: %s" % broken)
    print("-" * 60)
    print("  repair salvages the syntactic slips; the structural error is left to fail loudly.")


def check(data):
    print("SELF-TEST — strict rejects the repairable slips; repair recovers them; the structural error still fails")
    print("-" * 104)
    by_id = {c["id"]: c["raw"] for c in data["candidates"]}

    valid_parses_both = parses(by_id["valid"]) and parses(repair(by_id["valid"]))
    print("  a valid call parses strictly and after repair = %s" % valid_parses_both)

    strict_rejects_slips = not parses(by_id["fenced"]) and not parses(by_id["trailing_comma"])
    print("  strict parsing rejects the fenced and trailing-comma calls = %s" % strict_rejects_slips)

    repair_recovers_slips = parses(repair(by_id["fenced"])) and parses(repair(by_id["trailing_comma"]))
    print("  repair recovers both slips = %s" % repair_recovers_slips)

    structural_stays_broken = not parses(repair(by_id["missing_comma"]))
    print("  the structural (missing-comma) error still fails after repair = %s" % structural_stays_broken)

    repair_beats_strict = sum(parses(repair(c["raw"])) for c in data["candidates"]) > sum(parses(c["raw"]) for c in data["candidates"])
    print("  repair recovers more calls than strict = %s (%d > %d of %d)" % (repair_beats_strict, sum(parses(repair(c["raw"])) for c in data["candidates"]), sum(parses(c["raw"]) for c in data["candidates"]), len(data["candidates"])))

    ok = valid_parses_both and strict_rejects_slips and repair_recovers_slips and structural_stays_broken and repair_beats_strict
    print("-" * 104)
    print("SELF-TEST %s  valid_parses_both=%s  strict_rejects_slips=%s  repair_recovers_slips=%s  structural_stays_broken=%s  repair_beats_strict=%s"
          % ("PASS" if ok else "FAIL", valid_parses_both, strict_rejects_slips, repair_recovers_slips, structural_stays_broken, repair_beats_strict))
    return ok


def main():
    p = argparse.ArgumentParser(description="Repairing common tool-call JSON slips (code fences, trailing commas) before parsing recovers turns a strict parser would abort.")
    p.add_argument("--parse", action="store_true")
    p.add_argument("--recover", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("candidates=%d  file=%s  (the raw model outputs are a fixture)" % (len(data["candidates"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.parse:
        parse_view(data)
    elif args.recover:
        recover_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
