"""Normalize a tool's path before checking containment -- a raw prefix check lets '..' escape the sandbox.

When an agent has a file tool -- read_file, write_file, list_dir -- the harness must confine every path the model
proposes to a sandbox root, or the model (led by a confused plan, a prompt-injected instruction in some document, or plain
error) can reach files it was never meant to touch: credentials, other tenants' data, system files. The confinement is a
containment check: given the sandbox root and a requested path, decide whether the access stays inside the root. It sounds
trivial, and the obvious implementation is subtly, dangerously wrong.

The obvious implementation joins the requested path onto the root and tests whether the resulting string starts with the
root: root + path, does it start with root? That check is defeated by the '..' parent-directory segment, because it never
resolves the path. The string '/work/project/../secrets.env' literally starts with '/work/project', so the naive check
says 'inside, allowed' -- but that path RESOLVES to '/work/secrets.env', which is outside the sandbox entirely. The model
asked for '../secrets.env', the naive guard waved it through on a string-prefix match, and the tool read a file above the
root. This is the classic directory-traversal (path-traversal) vulnerability, and it is exactly as exploitable inside an
agent's tool sandbox as it is in a web server.

The fix is to NORMALIZE the joined path first -- collapse the '..' and '.' segments to get the real target location -- and
only then test containment. After normalization '/work/project/../secrets.env' becomes '/work/secrets.env', which does not
start with the root, so it is correctly denied. Crucially, normalization also stops you from over-blocking: a path like
'sub/../notes.txt' contains a '..' but resolves back to '/work/project/notes.txt', safely inside, so a guard that just
bans the substring '..' would wrongly reject a legitimate path. Normalize-then-contain accepts exactly the paths that
truly land inside the root and rejects exactly the ones that truly escape -- which banning a substring, or prefix-matching
the un-normalized string, both get wrong in opposite directions.

The rule: to confine a tool's path argument to a sandbox, resolve the path (join to the root and normalize away '..'/'.'
segments) BEFORE testing containment, and allow it only if the resolved path is the root or sits under it -- because a
containment check on the un-normalized string is fooled by '..' into allowing an escape, and a substring ban on '..' is
fooled into rejecting a safe path that merely passes through a parent.

On this fixture the sandbox root is /work/project. The naive check allows '../secrets.env' and '../../etc/passwd' (their
un-normalized joins start with the root) even though they resolve outside it; the correct check resolves them to
/work/secrets.env and /etc/passwd and denies both, while still allowing 'sub/../notes.txt' which resolves back inside. This
computes both.

  --paths    each requested path, its naive join, its resolved (normalized) target, and the naive vs correct verdict
  --exploit  the escape '../secrets.env': the naive prefix check passes it, but it resolves outside the sandbox root
  --check    the naive check allows paths that escape the sandbox; the correct check allows exactly those that resolve inside

root and requests are the fixture; every join, resolution, and verdict is computed. Stdlib only (posixpath for determinism).
"""
import argparse
import json
import posixpath as pp
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pathjail.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_join(root, path):
    """Join without normalizing -- the '..' segments survive in the string."""
    return pp.join(root, path)


def resolved_target(root, path):
    """Join and normalize -- collapse '..'/'.' to the real target location."""
    return pp.normpath(pp.join(root, path))


def contains(root, candidate):
    """True if candidate is the root itself or sits under it."""
    return candidate == root or candidate.startswith(root + "/")


def naive_allows(root, path):
    """The BUGGY guard: containment test on the un-normalized join."""
    return contains(root, naive_join(root, path))


def correct_allows(root, path):
    """The correct guard: normalize first, then test containment."""
    return contains(root, resolved_target(root, path))


# ----------------------------------------------------------------- printing

def paths_view(data):
    root, reqs = data["root"], data["requests"]
    print("PATHS — confining tool paths to sandbox root %s" % root)
    print("-" * 96)
    print("  requested path       naive join                     resolved target        naive  correct")
    for path in reqs:
        print("  %-20s %-30s %-22s %-6s %s"
              % (path, naive_join(root, path), resolved_target(root, path),
                 "ALLOW" if naive_allows(root, path) else "deny",
                 "ALLOW" if correct_allows(root, path) else "DENY"))
    print("-" * 96)
    print("  where naive says ALLOW but correct says DENY, the naive guard let an escape through.")


def exploit_view(data):
    root = data["root"]
    path = "../secrets.env"
    print("EXPLOIT — the traversal '%s' against root %s" % (path, root))
    print("-" * 68)
    print("  naive join      = %s" % naive_join(root, path))
    print("    starts with %r ? %s -> naive verdict: %s"
          % (root, naive_join(root, path).startswith(root), "ALLOW (wrong!)" if naive_allows(root, path) else "deny"))
    print("  resolved target = %s" % resolved_target(root, path))
    print("    under %r ? %s -> correct verdict: %s"
          % (root, contains(root, resolved_target(root, path)), "allow" if correct_allows(root, path) else "DENY (right)"))
    print("-" * 68)
    print("  the '..' survives the naive string check but resolves the target OUT of the sandbox.")


def check(data):
    print("SELF-TEST — the naive check allows sandbox escapes; the correct check allows exactly the paths that resolve inside")
    print("-" * 114)
    root, reqs = data["root"], data["requests"]

    escapes = ["../secrets.env", "../../etc/passwd"]
    naive_allows_escape = all(naive_allows(root, p) for p in escapes)
    print("  naive check ALLOWS the escaping paths %s = %s" % (escapes, naive_allows_escape))

    correct_denies_escape = all(not correct_allows(root, p) for p in escapes)
    print("  correct check denies the escaping paths = %s (resolve to %s)"
          % (correct_denies_escape, [resolved_target(root, p) for p in escapes]))

    safe_dotdot = "sub/../notes.txt"
    correct_allows_safe_dotdot = correct_allows(root, safe_dotdot)
    print("  correct check allows the safe '..' path %r = %s (resolves to %s)"
          % (safe_dotdot, correct_allows_safe_dotdot, resolved_target(root, safe_dotdot)))

    inside = ["notes.txt", "sub/data.csv"]
    both_allow_inside = all(naive_allows(root, p) and correct_allows(root, p) for p in inside)
    print("  both checks allow the plainly-inside paths %s = %s" % (inside, both_allow_inside))

    verdicts_differ = any(naive_allows(root, p) != correct_allows(root, p) for p in reqs)
    print("  the two checks disagree on at least one path = %s" % verdicts_differ)

    ok = naive_allows_escape and correct_denies_escape and correct_allows_safe_dotdot and both_allow_inside and verdicts_differ
    print("-" * 114)
    print("SELF-TEST %s  naive_allows_escape=%s  correct_denies_escape=%s  correct_allows_safe_dotdot=%s  both_allow_inside=%s  verdicts_differ=%s"
          % ("PASS" if ok else "FAIL", naive_allows_escape, correct_denies_escape, correct_allows_safe_dotdot, both_allow_inside, verdicts_differ))
    return ok


def main():
    p = argparse.ArgumentParser(description="Path containment for tool sandboxes: resolve a tool's path argument (join to the root and normalize away '..'/'.' segments) BEFORE testing containment, and allow it only if the resolved path is the root or under it, because a containment check on the un-normalized string is fooled by '..' into allowing an escape and a substring ban on '..' is fooled into rejecting a safe path that merely passes through a parent.")
    p.add_argument("--paths", action="store_true")
    p.add_argument("--exploit", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("root=%s  requests=%d  file=%s  (the root and requested paths are a fixture)"
          % (data["root"], len(data["requests"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.paths:
        paths_view(data)
    elif args.exploit:
        exploit_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
