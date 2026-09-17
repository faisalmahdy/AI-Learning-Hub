"""Gate tool execution on the response's finish_reason, not on whether the arguments parse -- a response cut off by the max-token limit carries truncated arguments, and when the truncation happens to leave valid JSON, a harness that trusts a successful parse executes a call the model never finished specifying, running a dangerous, wrong operation.

A model emits a tool call as structured text and the harness parses it and runs the tool. Alongside the text the provider returns a finish_reason -- why generation stopped. When the model finished the call, finish_reason is a completion reason (tool_calls or stop) and the arguments are whole. When generation stopped because it hit the max-token limit, finish_reason is length and the arguments are only whatever had been written so far.

Truncation usually mangles the JSON -- an unterminated string, a missing brace -- and a naive parse fails. It is tempting to treat that as the whole problem and reach for a more lenient parser. That is the wrong lesson, and dangerous, because truncation can also stop at a point where the partial JSON is accidentally well-formed. The model meant to write {"tool": "delete_dir", "path": "/data/tmp/cache"} but got cut off after the first path segment, leaving {"tool": "delete_dir", "path": "/data"} -- valid JSON, parses cleanly, and asks to delete /data instead of /data/tmp/cache. A harness that decides by whether json.loads succeeds runs it.

The authoritative signal is finish_reason, not JSON validity. A response with finish_reason length is an unfinished turn: its tool call is incomplete whether or not the fragment parses, and it must not be executed. The harness continues the generation with more budget, or errors -- it never guesses the missing arguments. Validity tells you the bytes are well-formed; finish_reason tells you the model was done, and only the second licenses running the call.

On this fixture r1 is a complete call, r2 is truncated into invalid JSON, and r3 is truncated but accidentally valid. A naive harness (parse, run if it parses) runs r1 correctly, fails on r2, and runs r3 with the wrong path -- a delete on /data. A finish_reason-gated harness runs only r1 and refuses both truncated responses. This computes both.

  --naive   parse-and-run: executes r1, fails to parse r2, and executes r3 with truncated arguments
  --safe    gate on finish_reason: executes only the completed r1, refuses both length-truncated responses
  --check   the naive harness executes a truncated call because it parsed, while the safe harness refuses every finish_reason=length response, and JSON validity alone does not detect the truncation

each response's text, finish_reason, and intended path are the fixture; whether each harness executes it and with what path is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "trunccall.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def parses(text):
    """Whether the emitted text is well-formed JSON -- a property of the bytes, not of completeness."""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def is_complete(resp, complete_reasons):
    """Whether generation finished the call, by finish_reason -- the authoritative signal."""
    return resp["finish_reason"] in complete_reasons


def naive_execute(resp):
    """Run the call if the text parses, ignoring why generation stopped."""
    if not parses(resp["text"]):
        return {"ran": False, "reason": "parse failed"}
    args = json.loads(resp["text"])
    return {"ran": True, "path": args.get("path")}


def safe_execute(resp, complete_reasons):
    """Run the call only if finish_reason says the turn completed; refuse a truncated response."""
    if not is_complete(resp, complete_reasons):
        return {"ran": False, "reason": "finish_reason=%s (truncated, not executed)" % resp["finish_reason"]}
    if not parses(resp["text"]):
        return {"ran": False, "reason": "parse failed"}
    args = json.loads(resp["text"])
    return {"ran": True, "path": args.get("path")}


# ----------------------------------------------------------------- printing

def naive_view(data):
    print("NAIVE — parse the text and run the call if it parses (ignores finish_reason)")
    print("-" * 72)
    for r in data["responses"]:
        res = naive_execute(r)
        if res["ran"]:
            wrong = "" if res["path"] == r["intended_path"] else "   <- WRONG path (intended %s)" % r["intended_path"]
            print("  %s [%s]  RAN path=%s%s" % (r["id"], r["finish_reason"], res["path"], wrong))
        else:
            print("  %s [%s]  did not run (%s)" % (r["id"], r["finish_reason"], res["reason"]))
    print("-" * 72)
    print("  r3 parsed cleanly and ran with a truncated path -- a delete on /data, not /data/tmp/cache")


def safe_view(data):
    cr = data["complete_reasons"]
    print("SAFE — run only if finish_reason is a completion reason")
    print("-" * 72)
    for r in data["responses"]:
        res = safe_execute(r, cr)
        if res["ran"]:
            print("  %s [%s]  RAN path=%s" % (r["id"], r["finish_reason"], res["path"]))
        else:
            print("  %s [%s]  refused (%s)" % (r["id"], r["finish_reason"], res["reason"]))
    print("-" * 72)
    print("  only the completed r1 runs; both length-truncated responses are held back")


def check(data):
    print("SELF-TEST — the naive harness executes a truncated call because it parsed, while the safe harness refuses every finish_reason=length response, and JSON validity alone does not detect the truncation")
    print("-" * 112)
    cr = data["complete_reasons"]
    by_id = {r["id"]: r for r in data["responses"]}
    r1, r2, r3 = by_id["r1"], by_id["r2"], by_id["r3"]

    naive_runs_truncated = naive_execute(r3)["ran"] and naive_execute(r3)["path"] != r3["intended_path"]
    print("  naive harness runs the accidentally-valid truncated r3 with the WRONG path = %s (ran path=%s, intended %s)"
          % (naive_runs_truncated, naive_execute(r3)["path"], r3["intended_path"]))

    r3_parses_but_truncated = parses(r3["text"]) and not is_complete(r3, cr)
    print("  r3 is valid JSON yet truncated, so validity alone would pass it = %s (parses=%s, finish_reason=%s)"
          % (r3_parses_but_truncated, parses(r3["text"]), r3["finish_reason"]))

    safe_blocks_truncated = (not safe_execute(r2, cr)["ran"]) and (not safe_execute(r3, cr)["ran"])
    print("  safe harness refuses both truncated responses (r2 and r3) = %s" % safe_blocks_truncated)

    safe_runs_complete = safe_execute(r1, cr)["ran"] and safe_execute(r1, cr)["path"] == r1["intended_path"]
    print("  safe harness runs the completed r1 with the right path = %s (path=%s)" % (safe_runs_complete, safe_execute(r1, cr)["path"]))

    r2_invalid = not parses(r2["text"])
    print("  r2 truncation left invalid JSON (the easy case, caught by any parser) = %s" % r2_invalid)

    ok = (naive_runs_truncated and r3_parses_but_truncated and safe_blocks_truncated
          and safe_runs_complete and r2_invalid)
    print("-" * 112)
    print("SELF-TEST %s  naive_runs_truncated=%s  r3_parses_but_truncated=%s  safe_blocks_truncated=%s  safe_runs_complete=%s  r2_invalid=%s"
          % ("PASS" if ok else "FAIL", naive_runs_truncated, r3_parses_but_truncated, safe_blocks_truncated,
             safe_runs_complete, r2_invalid))
    return ok


def main():
    p = argparse.ArgumentParser(description="Truncated tool call: gate tool execution on the response's finish_reason, not on whether the arguments parse, because a response cut off at the max-token limit (finish_reason=length) carries incomplete arguments -- and when the truncation happens to leave valid JSON, a harness that trusts a successful parse runs a call the model never finished, with the wrong arguments; a finish_reason=length response is an unfinished turn whose call must not be executed.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--safe", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("responses=%d  complete_reasons=%s  file=%s" % (len(data["responses"]), data["complete_reasons"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.safe:
        safe_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
