"""Pass a model's tool arguments as structured parameters -- an argv list, or a parameterized query -- not string-interpolated into a command the shell then re-parses, because a schema-valid argument is still text and can carry a second command that the shell splits out and runs.

A companion module makes the case that the model's arguments are untrusted and must be validated against the tool's schema before dispatch. That is necessary and it is not enough. Schema validation asks "is this argument the right type and shape?" -- and a string that hides an injection is a perfectly valid string. It passes the schema and remains dangerous.

The danger appears in how the harness turns the argument into an action. The tempting shortcut is to build one command string -- the program name, a space, the argument -- and hand it to a shell. But a shell does not treat that string as "a program and one argument"; it re-parses the whole thing, and any shell metacharacter in the argument is interpreted. An argument of 'report.txt; delete_all data' becomes, after the shell reads the ';', two commands: the intended read, and an injected 'delete_all data' the model only ever supplied as part of one argument to one tool.

The fix is to never build a command string from an untrusted value. Pass the program and its arguments as a list -- argv -- directly to exec with no shell in the middle. The argument is then delivered as a single opaque value: its semicolons and spaces are just characters in a (strange) filename, not command separators, so the injected verb never becomes a command. The same principle for a database is a parameterized query -- placeholders bound to values -- where the value can never be parsed as SQL.

On this fixture both arguments are valid strings, so a schema check passes both. The interpolate-and-shell path splits the malicious argument into two commands and runs 'delete_all'; the argv path runs one command whose single argument is the whole payload, literally, and 'delete_all' never executes. This computes both.

  --unsafe  build a command string and let the shell parse it -- the injected verb splits out and runs
  --safe    pass an argv list with no shell -- the payload stays one literal argument
  --check   a schema-valid argument still injects under string interpolation; an argv list keeps it a single inert value

program, the two arguments, and the injected verb are the fixture; the command string, the shell's split, the argv list, and the executed verbs are computed. Stdlib only.
"""
import argparse
import json
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "arginject.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def is_valid_string_arg(arg):
    """Schema-level check: is the argument a non-empty string? Both fixture args pass this."""
    return isinstance(arg, str) and len(arg) > 0


def interpolate(program, arg):
    """The unsafe path: build one command string from the program and the argument."""
    return "%s %s" % (program, arg)


def shell_split(command_string):
    """A shell reads the string and splits it into separate commands on ';', each parsed into argv."""
    return [shlex.split(part.strip()) for part in command_string.split(";")]


def argv_of(program, arg):
    """The safe path: the program and the argument as a list, delivered straight to exec -- no shell."""
    return [program, arg]


def executed_verbs(commands):
    """The first token of each command the path runs is a program (verb) that executes."""
    return [c[0] for c in commands if c]


# ----------------------------------------------------------------- printing

def unsafe_view(data):
    program, arg, verb = data["program"], data["malicious_arg"], data["injected_verb"]
    cmd = interpolate(program, arg)
    commands = shell_split(cmd)
    print("UNSAFE — interpolate the argument into a command string, then let the shell parse it")
    print("-" * 64)
    print("  schema check on the argument : %s (it is a valid string)" % is_valid_string_arg(arg))
    print("  command string               : %r" % cmd)
    print("  shell splits into %d commands :" % len(commands))
    for c in commands:
        print("      %s" % c)
    print("-" * 64)
    print("  executed verbs = %s  -- the injected %r ran" % (executed_verbs(commands), verb))


def safe_view(data):
    program, arg, verb = data["program"], data["malicious_arg"], data["injected_verb"]
    argv = argv_of(program, arg)
    commands = [argv]
    print("SAFE — pass an argv list straight to exec, no shell to re-parse it")
    print("-" * 64)
    print("  schema check on the argument : %s (same valid string)" % is_valid_string_arg(arg))
    print("  argv list                    : %s" % argv)
    print("  the argument is one value    : %r" % argv[1])
    print("-" * 64)
    print("  executed verbs = %s  -- %r never became a command" % (executed_verbs(commands), verb))


def check(data):
    print("SELF-TEST — a schema-valid argument still injects under string interpolation; an argv list keeps it a single inert value")
    print("-" * 112)
    program, arg, verb = data["program"], data["malicious_arg"], data["injected_verb"]

    arg_is_schema_valid = is_valid_string_arg(arg)
    print("  the malicious argument passes the schema check = %s" % arg_is_schema_valid)

    unsafe_cmds = shell_split(interpolate(program, arg))
    unsafe_verbs = executed_verbs(unsafe_cmds)
    unsafe_runs_extra_command = len(unsafe_cmds) > 1
    print("  string interpolation runs more than one command = %s (%d commands)" % (unsafe_runs_extra_command, len(unsafe_cmds)))

    unsafe_executes_injection = verb in unsafe_verbs
    print("  the injected verb executes under interpolation = %s (verbs %s)" % (unsafe_executes_injection, unsafe_verbs))

    safe_argv = argv_of(program, arg)
    safe_verbs = executed_verbs([safe_argv])
    safe_runs_single_command = len(safe_verbs) == 1 and safe_verbs[0] == program
    print("  argv runs exactly one command, the intended program = %s (verbs %s)" % (safe_runs_single_command, safe_verbs))

    safe_payload_is_literal = safe_argv[1] == arg and verb not in safe_verbs
    print("  argv keeps the payload as one literal argument = %s (%r)" % (safe_payload_is_literal, safe_argv[1]))

    ok = (arg_is_schema_valid and unsafe_runs_extra_command and unsafe_executes_injection
          and safe_runs_single_command and safe_payload_is_literal)
    print("-" * 112)
    print("SELF-TEST %s  arg_is_schema_valid=%s  unsafe_runs_extra_command=%s  unsafe_executes_injection=%s  safe_runs_single_command=%s  safe_payload_is_literal=%s"
          % ("PASS" if ok else "FAIL", arg_is_schema_valid, unsafe_runs_extra_command, unsafe_executes_injection,
             safe_runs_single_command, safe_payload_is_literal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Argument injection: pass a model's tool arguments as structured parameters (an argv list or a parameterized query), not string-interpolated into a command the shell re-parses, because a schema-valid argument is still text and can carry a second command that the shell splits out and runs.")
    p.add_argument("--unsafe", action="store_true")
    p.add_argument("--safe", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("program=%r  malicious_arg=%r  injected_verb=%r  file=%s  (these are a fixture)"
          % (data["program"], data["malicious_arg"], data["injected_verb"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.unsafe:
        unsafe_view(data)
    elif args.safe:
        safe_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
