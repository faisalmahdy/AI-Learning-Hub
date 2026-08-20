#!/usr/bin/env python3
"""Three graders for the same 30 answers, from worst to least-bad.

  --strategy exact    string identity against a reference answer
  --strategy overlap  token-overlap F1 against the same reference
  --strategy rubric   six per-case boolean checks (the mechanized rubric)
  --strategy all      run all three and print where they disagree
  --check             re-derive the rubric score by a second, dumb route

Stdlib only. No network, no API keys, no model calls. The answers being
graded are fixtures stored in cases.json, so every run prints the same
numbers; see _meta.how_answers_were_produced in that file.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "cases.json"


def load_cases():
    data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    return data["_config"], data["cases"]


def words(text):
    """Lowercase alphanumeric tokens. Every strategy uses this one tokenizer."""
    return re.findall(r"[a-z0-9]+", text.lower())


# ----------------------------------------------------------------- strategy 1

def grade_exact(case):
    """Did the system emit the reference answer, character for character?"""
    got = case["answer"].strip()
    want = case["reference"].strip()
    if got == want:
        return True, "identical to reference"
    return False, "differs from reference"


# ----------------------------------------------------------------- strategy 2

def token_f1(answer, reference):
    """Harmonic mean of token precision and recall, each token counted once."""
    got = words(answer)
    want = words(reference)
    if not got or not want:
        return 0.0

    pool = list(want)
    hits = 0
    for token in got:
        if token in pool:
            pool.remove(token)
            hits = hits + 1

    if hits == 0:
        return 0.0
    precision = hits / len(got)
    recall = hits / len(want)
    return 2 * precision * recall / (precision + recall)


def grade_overlap(case, threshold):
    score = token_f1(case["answer"], case["reference"])
    return score >= threshold, score


# ----------------------------------------------------------------- strategy 3

def check_cites_valid_slug(case, config):
    """C1 grounding: at least one [[slug]], and no invented ones."""
    cited = re.findall(config["citation_pattern"], case["answer"])
    if not cited:
        return False, "no [[slug]] citation at all"
    known = set(config["known_slugs"])
    for slug in cited:
        if slug not in known:
            return False, "cites [[" + slug + "]], which is not a wiki page"
    return True, str(len(cited)) + " citation(s), all real"


def check_cites_required(case, config):
    """C2 grounding: did it route to the page this question belongs to?"""
    required = case["expect"]["must_cite"]
    if not required:
        return True, "no page required"
    for slug in required:
        if "[[" + slug + "]]" not in case["answer"]:
            return False, "missing required citation [[" + slug + "]]"
    return True, "cites all " + str(len(required)) + " required page(s)"


def check_key_facts(case, config):
    """C3 correctness: every fact this question must contain."""
    patterns = case["expect"]["must_match"]
    if not patterns:
        return True, "no required facts"
    for pattern in patterns:
        if not re.search(pattern, case["answer"]):
            return False, "missing required fact /" + pattern + "/"
    return True, "all " + str(len(patterns)) + " fact patterns present"


def check_no_known_error(case, config):
    """C4 correctness: the specific wrong claims this question attracts."""
    patterns = case["expect"]["must_not_match"]
    if not patterns:
        return True, "no error pattern for this case"
    for pattern in patterns:
        found = re.search(pattern, case["answer"])
        if found:
            return False, "asserts known error: " + repr(found.group(0))
    return True, "clear of " + str(len(patterns)) + " error pattern(s)"


def check_refusal_honesty(case, config):
    """C5 honest-refusal: refuse when the wiki cannot answer, and only then."""
    refused = False
    for marker in config["refusal_markers"]:
        if re.search(marker, case["answer"]):
            refused = True

    expected = case["expect"]["refusal_expected"]
    if expected and not refused:
        return False, "should have refused, answered instead"
    if refused and not expected:
        return False, "refused a question the wiki can answer"
    if expected:
        return True, "refused, correctly"
    return True, "answered, correctly"


def check_well_formed(case, config):
    """C6 completeness: inside the length band and carrying a Sources: line."""
    answer = case["answer"]
    count = len(answer.split())
    low = case["expect"].get("min_words", config["default_min_words"])
    high = case["expect"].get("max_words", config["default_max_words"])
    if count < low:
        return False, str(count) + " words, under the " + str(low) + "-word floor"
    if count > high:
        return False, str(count) + " words, over the " + str(high) + "-word cap"
    if not re.search(config["sources_line_pattern"], answer):
        return False, "no Sources: line"
    return True, str(count) + " words, has Sources:"


CHECKS = [
    ("C1", "cites-valid-slug", check_cites_valid_slug),
    ("C2", "cites-required-page", check_cites_required),
    ("C3", "key-facts-present", check_key_facts),
    ("C4", "no-known-error", check_no_known_error),
    ("C5", "refusal-honesty", check_refusal_honesty),
    ("C6", "well-formed", check_well_formed),
]


def grade_rubric(case, config):
    """Run all six checks over one case. Returns a list of (id, name, ok, why)."""
    results = []
    for check_id, name, function in CHECKS:
        ok, why = function(case, config)
        results.append((check_id, name, ok, why))
    return results


def rubric_marks(results):
    """'..x..x' — a dot per passing check, an x per failing one."""
    marks = ""
    for _, _, ok, _ in results:
        if ok:
            marks = marks + "."
        else:
            marks = marks + "x"
    return marks


# ---------------------------------------------------------------- run + print

def line(case_id, kind, rest):
    return case_id.ljust(5) + kind.ljust(14) + rest


def run_exact(config, cases):
    print("STRATEGY 1 — exact: answer.strip() == reference.strip()")
    print("-" * 78)
    matched = 0
    for case in cases:
        ok, why = grade_exact(case)
        if ok:
            matched = matched + 1
        verdict = "PASS" if ok else "FAIL"
        print(line(case["id"], case["kind"], verdict + "  " + why))
    score = matched / len(cases)
    print("-" * 78)
    print("SUMMARY exact    n=%d  matched=%d  score=%.3f" % (len(cases), matched, score))
    return score


def run_overlap(config, cases):
    threshold = config["overlap_threshold"]
    print("STRATEGY 2 — overlap: token F1 vs reference, pass at F1 >= %.2f" % threshold)
    print("-" * 78)
    passed = 0
    total_f1 = 0.0
    for case in cases:
        ok, score = grade_overlap(case, threshold)
        total_f1 = total_f1 + score
        if ok:
            passed = passed + 1
        verdict = "PASS" if ok else "FAIL"
        print(line(case["id"], case["kind"], verdict + "  f1=%.3f" % score))
    score = passed / len(cases)
    mean_f1 = total_f1 / len(cases)
    print("-" * 78)
    print("SUMMARY overlap  n=%d  passed=%d  score=%.3f  mean_f1=%.3f"
          % (len(cases), passed, score, mean_f1))
    return score


def run_rubric(config, cases):
    print("STRATEGY 3 — rubric: six boolean checks per case")
    for check_id, name, _ in CHECKS:
        print("  " + check_id + " " + name)
    print("-" * 78)

    checks_passed = 0
    clean_cases = 0
    failures_by_check = {}
    for check_id, _, _ in CHECKS:
        failures_by_check[check_id] = 0

    for case in cases:
        results = grade_rubric(case, config)
        hits = 0
        for _, _, ok, _ in results:
            if ok:
                hits = hits + 1
        checks_passed = checks_passed + hits
        if hits == len(CHECKS):
            clean_cases = clean_cases + 1
        marks = rubric_marks(results)
        verdict = "PASS" if hits == len(CHECKS) else "FAIL"
        print(line(case["id"], case["kind"],
                   "[" + marks + "]  " + str(hits) + "/6  " + verdict))
        for check_id, name, ok, why in results:
            if not ok:
                failures_by_check[check_id] = failures_by_check[check_id] + 1
                print("       " + check_id + " " + name + ": " + why)

    total_checks = len(cases) * len(CHECKS)
    score = checks_passed / total_checks
    clean_rate = clean_cases / len(cases)

    print("-" * 78)
    print("failures by check:")
    for check_id, name, _ in CHECKS:
        print("  " + check_id + " " + name.ljust(22)
              + str(failures_by_check[check_id]) + " of " + str(len(cases)) + " cases")
    print("failures by kind:")
    for kind in ("factual", "synthesis", "unanswerable"):
        kind_cases = 0
        kind_failed = 0
        for case in cases:
            if case["kind"] != kind:
                continue
            kind_cases = kind_cases + 1
            results = grade_rubric(case, config)
            for _, _, ok, _ in results:
                if not ok:
                    kind_failed = kind_failed + 1
        print("  " + kind.ljust(14) + str(kind_failed) + " failed checks over "
              + str(kind_cases * len(CHECKS)))
    print("-" * 78)
    print("SUMMARY rubric   n=%d  checks_passed=%d/%d  score=%.3f  clean_cases=%d/%d  clean_rate=%.3f"
          % (len(cases), checks_passed, total_checks, score,
             clean_cases, len(cases), clean_rate))
    return score


def run_all(config, cases):
    """One row per case, three verdicts, so disagreements are visible."""
    print("ALL THREE — one row per case")
    print("-" * 78)
    print("case  kind          exact   overlap        rubric")
    disagreements = []
    for case in cases:
        exact_ok, _ = grade_exact(case)
        overlap_ok, f1 = grade_overlap(case, config["overlap_threshold"])
        results = grade_rubric(case, config)
        hits = 0
        for _, _, ok, _ in results:
            if ok:
                hits = hits + 1
        rubric_ok = hits == len(CHECKS)

        print(case["id"].ljust(6) + case["kind"].ljust(14)
              + ("PASS" if exact_ok else "FAIL").ljust(8)
              + ("PASS" if overlap_ok else "FAIL") + " f1=%.2f" % f1 + "   "
              + "[" + rubric_marks(results) + "] " + str(hits) + "/6 "
              + ("PASS" if rubric_ok else "FAIL"))

        if overlap_ok and not rubric_ok:
            disagreements.append(
                case["id"] + ": overlap PASS (f1=%.2f) but rubric %d/6" % (f1, hits))
        if rubric_ok and not overlap_ok:
            disagreements.append(
                case["id"] + ": rubric 6/6 but overlap FAIL (f1=%.2f)" % f1)

    print("-" * 78)
    print("disagreements between overlap and rubric: " + str(len(disagreements)))
    for item in disagreements:
        print("  " + item)


def self_check(config, cases):
    """Compute the rubric score twice by different routes and compare."""
    print("SELF-TEST — re-derive the rubric score by a second, dumb route")
    print("-" * 78)

    # Route A: the route the report uses. Per case, count hits, sum them.
    route_a_hits = 0
    route_a_clean = 0
    for case in cases:
        results = grade_rubric(case, config)
        hits = 0
        for _, _, ok, _ in results:
            if ok:
                hits = hits + 1
        route_a_hits = route_a_hits + hits
        if hits == len(CHECKS):
            route_a_clean = route_a_clean + 1

    # Route B: forget cases exist. Flatten every check into one list of
    # booleans, then count the list with a plain loop.
    flat = []
    for case in cases:
        for check_id, name, function in CHECKS:
            ok, why = function(case, config)
            flat.append(ok)

    route_b_hits = 0
    for ok in flat:
        if ok:
            route_b_hits = route_b_hits + 1

    # Route B's clean-case count, also the dumb way: walk the flat list in
    # groups of six and require all six.
    route_b_clean = 0
    position = 0
    while position < len(flat):
        group = flat[position:position + len(CHECKS)]
        all_ok = True
        for ok in group:
            if not ok:
                all_ok = False
        if all_ok:
            route_b_clean = route_b_clean + 1
        position = position + len(CHECKS)

    total = len(cases) * len(CHECKS)
    print("route A (per case, summed)   checks_passed=%d/%d  score=%.6f  clean=%d"
          % (route_a_hits, total, route_a_hits / total, route_a_clean))
    print("route B (flat dumb loop)     checks_passed=%d/%d  score=%.6f  clean=%d"
          % (route_b_hits, len(flat), route_b_hits / len(flat), route_b_clean))
    print("flat list length=%d  expected=%d" % (len(flat), total))

    ok = (route_a_hits == route_b_hits and route_a_clean == route_b_clean
          and len(flat) == total)

    # And once more, to show the grader is deterministic across runs.
    again = []
    for case in cases:
        again.append(rubric_marks(grade_rubric(case, config)))
    once = []
    for case in cases:
        once.append(rubric_marks(grade_rubric(case, config)))
    deterministic = again == once
    print("determinism: two independent passes produce "
          + ("identical" if deterministic else "DIFFERENT") + " per-case marks")

    print("-" * 78)
    print("SELF-TEST " + ("PASS" if ok and deterministic else "FAIL")
          + "  routes agree=%s  deterministic=%s" % (ok, deterministic))
    return ok and deterministic


def main():
    parser = argparse.ArgumentParser(description="Grade 30 stored Query-workflow answers.")
    parser.add_argument("--strategy", choices=["exact", "overlap", "rubric", "all"])
    parser.add_argument("--check", action="store_true",
                        help="cross-verify the rubric score by a second route")
    args = parser.parse_args()

    config, cases = load_cases()
    print("cases=%d  file=%s  graders are deterministic (no model call)"
          % (len(cases), CASES_FILE.name))
    print("")

    if args.check:
        ok = self_check(config, cases)
        return 0 if ok else 1

    if args.strategy == "exact":
        run_exact(config, cases)
    elif args.strategy == "overlap":
        run_overlap(config, cases)
    elif args.strategy == "rubric":
        run_rubric(config, cases)
    elif args.strategy == "all":
        run_all(config, cases)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
