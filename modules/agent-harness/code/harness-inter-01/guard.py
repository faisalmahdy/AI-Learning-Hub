#!/usr/bin/env python3
"""The kernel import guard — an AST scan that enforces the one architecture rule
a type checker never will: the kernel may import only the standard library and
the abstract seams. A concrete import in the kernel still RUNS; only this fails.

  --imports FILE   list the top-level modules FILE imports, classified
  --check FILE     pass iff FILE (a kernel module) imports only stdlib + seams
  --all            check the good kernel and the broken one, and run the agent
  --run            just run the assembled agent (composition outside the kernel)

Stdlib only (ast, sys). Deterministic. This is the whole guard; a real one adds
package-walking and a CI hook, but the check is these few lines.
"""
import argparse
import ast
import subprocess
import sys

STDLIB = set(sys.stdlib_module_names)   # every stdlib top-level name, from Python itself
ALLOWED_LOCAL = {"seams"}               # the ONE local module the kernel may import


def top_level(dotted):
    """'a.b.c' -> 'a'."""
    return dotted.split(".")[0]


def imports_of(path):
    """Every top-level module name imported by the file, via its AST."""
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append(top_level(alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(top_level(node.module))
    return found


def classify(name):
    if name in STDLIB:
        return "stdlib"
    if name in ALLOWED_LOCAL:
        return "seam"
    return "FORBIDDEN"


def bad_imports(path):
    """The kernel rule: anything that is neither stdlib nor a seam is forbidden."""
    return [m for m in imports_of(path) if classify(m) == "FORBIDDEN"]


def show_imports(path):
    print("imports of %s (via AST):" % path)
    print("-" * 56)
    seen = []
    for m in imports_of(path):
        if m in seen:
            continue
        seen.append(m)
        print("  %-14s %s" % (m, classify(m)))


def check(path):
    bad = bad_imports(path)
    print("KERNEL IMPORT CHECK: %s" % path)
    print("-" * 56)
    if not bad:
        print("  PASS — imports only stdlib and the seams")
        return True
    for m in bad:
        print("  FORBIDDEN import in the kernel: '%s' (a concrete detail)" % m)
    print("  FAIL — the kernel must not depend on a concrete implementation")
    return False


def run_agent():
    """Prove the composition works — from outside the kernel."""
    out = subprocess.run([sys.executable, "agent.py"], capture_output=True, text=True)
    sys.stdout.write(out.stdout)


def main():
    p = argparse.ArgumentParser(description="Enforce the kernel import rule.")
    p.add_argument("--imports")
    p.add_argument("--check")
    p.add_argument("--all", action="store_true")
    p.add_argument("--run", action="store_true")
    args = p.parse_args()

    if args.imports:
        show_imports(args.imports)
        return 0
    if args.check:
        return 0 if check(args.check) else 1
    if args.run:
        run_agent()
        return 0
    if args.all:
        good = check("kernel_loop.py")
        print("")
        broken = check("kernel_loop_broken.py")
        print("")
        print("both loops RUN identically; only the guard tells them apart:")
        run_agent()
        return 0 if (good and not broken) else 1

    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
