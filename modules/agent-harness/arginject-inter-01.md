---
id: arginject-inter-01
title: Pass tool arguments as structured parameters, not string-interpolated into a command — a schema-valid argument can still inject a second command
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A companion module establishes that the model's tool arguments are untrusted and must be validated against the tool's schema before dispatch. That is necessary and not sufficient: schema validation asks whether an argument is the right type and shape, and a string that hides an injection is a perfectly valid string. The danger is in how the harness turns the argument into an action. The tempting shortcut is to build one command string — program name, a space, the argument — and hand it to a shell, but a shell re-parses that whole string and interprets any shell metacharacter the argument contains, so an argument of "report.txt; delete_all data" becomes two commands: the intended read and an injected delete the model only ever supplied as part of one argument to one tool. The fix is to never build a command string from an untrusted value: pass the program and its arguments as a list — argv — straight to exec with no shell, so the argument is delivered as a single opaque value whose semicolons and spaces are inert characters, not command separators; the database equivalent is a parameterized query with placeholders, where the value can never be parsed as SQL. On a fixture where both arguments pass the schema check, the interpolate-and-shell path splits the malicious argument into two commands and runs delete_all, while the argv path runs one command whose single argument is the whole payload, literally, and delete_all never executes.
eli5: Imagine a robot assistant you tell "fetch the file named X." If you write the whole sentence on a slip of paper and hand it to a literal-minded butler who does whatever the paper says, a sneaky value of X like "the-report; also throw out the trash" turns into two orders — fetch the report AND throw out the trash — because the butler read the semicolon as "new order." The safe way is to hand the butler a labeled box: the label says "the thing to fetch" and the box contains the whole value "the-report; also throw out the trash" as one weird name. The butler looks for a file with that exact odd name, finds none, and never throws out anything, because the value was in a box, not written into the order itself. Checking that X is a proper string does not help — "also throw out the trash" is a proper string; what matters is never letting the value become part of the command.
---

## Why this module

A harness that lets a model call tools has to take the model's arguments and do something real with them — read a file, run a query, call a command. A neighboring module makes the first essential point: those arguments are untrusted, so validate them against the tool's schema before you dispatch. A path argument should be a string, a count should be a positive integer, and a call that fails the schema should be rejected, not executed.

Passing the schema check feels like safety, and it is a real layer, but it answers a narrow question: is this argument the right type and shape? It does not ask what the argument's contents will do once you use them. A string argument that is a valid string can still contain text that, in the wrong hands, becomes a command.

<svg role="img" aria-label="A schema-check gate that both a benign argument and a malicious argument pass through, because both are valid strings. After the gate, the benign one is harmless but the malicious one still carries a hidden second command." viewBox="0 0 440 130">
<rect x="20" y="30" width="120" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="80" y="44" fill="var(--ink)" font-size="8" text-anchor="middle">"report.txt"</text>
<rect x="20" y="62" width="120" height="20" fill="var(--panel)" stroke="var(--s2)"/>
<text x="80" y="76" fill="var(--s2)" font-size="8" text-anchor="middle">"report.txt; delete_all"</text>
<rect x="180" y="40" width="70" height="40" fill="var(--panel)" stroke="var(--line)"/>
<text x="215" y="56" fill="var(--ink)" font-size="8" text-anchor="middle">schema</text>
<text x="215" y="68" fill="var(--ink)" font-size="8" text-anchor="middle">check</text>
<line x1="140" y1="40" x2="180" y2="52" stroke="var(--line)"/>
<line x1="140" y1="72" x2="180" y2="66" stroke="var(--s2)"/>
<line x1="250" y1="52" x2="300" y2="40" stroke="var(--line)"/>
<line x1="250" y1="66" x2="300" y2="72" stroke="var(--s2)"/>
<text x="360" y="44" fill="var(--muted)" font-size="8" text-anchor="middle">both valid strings</text>
<text x="360" y="76" fill="var(--s2)" font-size="8" text-anchor="middle">payload still inside</text>
<text x="215" y="100" fill="var(--muted)" font-size="8" text-anchor="middle">a valid-string check lets both through</text>
</svg>
^ The schema check passes both arguments because both are valid strings — it inspects type and shape, not whether the contents can become a command.

The wrong hands are a shell. If the harness builds an action by pasting the argument into a command string and handing that string to a shell to run, the shell does not see "a program and one argument" — it re-parses the entire string and obeys any shell metacharacter inside it. The argument stops being data and becomes part of the program. This is the same class of bug as SQL injection, and it lands in agent harnesses precisely because the arguments come from a model that can be confused or steered into supplying a payload.

**Schema validation checks an argument's type and shape, not what its contents do; a schema-valid string interpolated into a shell command is re-parsed by the shell, so the argument can carry a second command that runs.**

## Concepts

Picture the two ways a harness can turn a tool call into execution. The unsafe way concatenates: it makes the single string "read_file " plus the argument, and passes that to a shell. The shell tokenizes and splits on metacharacters — a semicolon separates commands, so one string becomes a list of commands, and every one of them runs. The argument's job was to name a file; instead its semicolon got a vote on the control flow.

The safe way never makes that string. It builds a list — the program name, then each argument as its own element — and hands the list straight to the operating system's exec call, with no shell in between. Exec runs exactly the named program and delivers the rest of the list as its arguments, each one an opaque value. A semicolon in an argument is now just a byte in a filename; there is no shell to interpret it, so there is nothing to inject into.

<svg role="img" aria-label="Two paths for a tool call. The unsafe path joins the program and argument into one string, passes it to a shell, and the shell splits it on a semicolon into two commands, read_file and delete_all, both of which run. The safe path builds a two-element argv list and passes it to exec, which runs one command with the argument as a single value." viewBox="0 0 440 200">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">unsafe: string then shell</text>
<rect x="20" y="26" width="180" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="110" y="40" fill="var(--ink)" font-size="8" text-anchor="middle">"read_file report.txt; delete_all data"</text>
<text x="110" y="60" fill="var(--muted)" font-size="8" text-anchor="middle">shell parses (splits on ;)</text>
<rect x="20" y="68" width="85" height="20" fill="var(--panel)" stroke="var(--s1)"/>
<text x="62" y="82" fill="var(--ink)" font-size="8" text-anchor="middle">read_file</text>
<rect x="115" y="68" width="85" height="20" fill="var(--panel)" stroke="var(--s2)"/>
<text x="157" y="82" fill="var(--s2)" font-size="8" text-anchor="middle">delete_all</text>
<text x="110" y="104" fill="var(--s2)" font-size="8" text-anchor="middle">both run — injected</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">safe: argv then exec</text>
<rect x="240" y="26" width="180" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="330" y="40" fill="var(--ink)" font-size="8" text-anchor="middle">["read_file", "report.txt; delete_all data"]</text>
<text x="330" y="60" fill="var(--muted)" font-size="8" text-anchor="middle">exec, no shell</text>
<rect x="240" y="68" width="180" height="20" fill="var(--panel)" stroke="var(--s1)"/>
<text x="330" y="82" fill="var(--ink)" font-size="8" text-anchor="middle">read_file (arg is one value)</text>
<text x="330" y="104" fill="var(--s1)" font-size="8" text-anchor="middle">one runs — payload inert</text>
<text x="220" y="140" fill="var(--muted)" font-size="9" text-anchor="middle">the argument is identical in both — only the delivery differs</text>
</svg>
^ The same argument down two paths: interpolated into a string, the shell splits it into two commands; placed in an argv list, exec runs one command and the payload stays a single value.

The general rule the argv form expresses is: keep code and data separate, and never let untrusted data cross into the code channel. A command string mixes them — the program and its data live in the same text, so anything in the data can pretend to be program. A structured call keeps them in different channels — the program is chosen by you, the data rides in labeled slots — so data cannot promote itself to code.

This is why the same shape recurs across every system that takes untrusted values. For a database it is the parameterized query: you write the SQL with placeholders and bind the values separately, so a value can never be parsed as SQL. For a subprocess it is the argv list with no shell. For an HTTP call it is a structured body, not a hand-built URL. In each case the fix is identical in spirit — the value goes in a slot, never into the sentence.

**Build the call as structure — an argv list, a parameterized query, a labeled field — so the program is chosen by you and the untrusted value rides in a slot it cannot escape; a command string mixes code and data in one channel, letting the data become code.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/arginject-inter-01. The fixture is a program name, a benign argument, a malicious argument that hides a second command, and the verb that payload tries to smuggle in.

```json filename=modules/agent-harness/code/arginject-inter-01/arginject.json:3-6 COMPLETE
  "program": "read_file",
  "safe_arg": "report.txt",
  "malicious_arg": "report.txt; delete_all data",
  "injected_verb": "delete_all"
```

The schema-level check asks only whether the argument is a non-empty string — which both arguments are.

```python filename=modules/agent-harness/code/arginject-inter-01/arginject.py:31-33 COMPLETE
def is_valid_string_arg(arg):
    """Schema-level check: is the argument a non-empty string? Both fixture args pass this."""
    return isinstance(arg, str) and len(arg) > 0
```

The unsafe path interpolates the argument into one command string, and the shell splits that string into separate commands on the semicolon.

```python filename=modules/agent-harness/code/arginject-inter-01/arginject.py:36-43 COMPLETE
def interpolate(program, arg):
    """The unsafe path: build one command string from the program and the argument."""
    return "%s %s" % (program, arg)


def shell_split(command_string):
    """A shell reads the string and splits it into separate commands on ';', each parsed into argv."""
    return [shlex.split(part.strip()) for part in command_string.split(";")]
```

The safe path builds an argv list — the program and the argument as separate elements — delivered straight to exec.

```python filename=modules/agent-harness/code/arginject-inter-01/arginject.py:46-48 COMPLETE
def argv_of(program, arg):
    """The safe path: the program and the argument as a list, delivered straight to exec -- no shell."""
    return [program, arg]
```

Before running it, predict: the malicious argument is a valid string, so it passes the schema check — and once interpolated, the shell will see the semicolon and run two commands. Run `--unsafe`:

```text filename=arginject.py --unsafe
UNSAFE — interpolate the argument into a command string, then let the shell parse it
----------------------------------------------------------------
  schema check on the argument : True (it is a valid string)
  command string               : 'read_file report.txt; delete_all data'
  shell splits into 2 commands :
      ['read_file', 'report.txt']
      ['delete_all', 'data']
----------------------------------------------------------------
  executed verbs = ['read_file', 'delete_all']  -- the injected 'delete_all' ran
```

The prediction holds, and it is exactly the failure. The schema check returns True — the argument is a valid string — so the layer that was supposed to make arguments safe waved this one through. Then the interpolated command string, parsed by the shell, split at the semicolon into two commands, and both ran: the intended read_file and the injected delete_all. One tool call, one argument, two commands executed, one of them never authorized.

Now the same argument down the safe path. Run `--safe`:

```text filename=arginject.py --safe
SAFE — pass an argv list straight to exec, no shell to re-parse it
----------------------------------------------------------------
  schema check on the argument : True (same valid string)
  argv list                    : ['read_file', 'report.txt; delete_all data']
  the argument is one value    : 'report.txt; delete_all data'
----------------------------------------------------------------
  executed verbs = ['read_file']  -- 'delete_all' never became a command
```

Same argument, same schema result — but the argv list keeps the whole payload as a single element. Exec runs one command, read_file, with an argument that is literally the string "report.txt; delete_all data" — a filename that does not exist, so the read simply fails harmlessly. The semicolon never separated anything because there was no shell to read it. delete_all never became a command. The only thing that changed between disaster and safety was the delivery mechanism, not the validation.

<svg role="img" aria-label="A comparison of executed verbs. The unsafe path executes read_file and delete_all, two verbs, with delete_all marked as injected. The safe path executes only read_file, one verb, with delete_all shown as inert text inside the single argument." viewBox="0 0 440 130">
<text x="20" y="20" fill="var(--muted)" font-size="9">verbs executed</text>
<text x="70" y="46" fill="var(--ink)" font-size="9" text-anchor="end">unsafe</text>
<rect x="78" y="36" width="90" height="16" fill="var(--s1)"/>
<text x="123" y="48" fill="var(--ink)" font-size="8" text-anchor="middle">read_file</text>
<rect x="172" y="36" width="90" height="16" fill="var(--s2)"/>
<text x="217" y="48" fill="var(--s2)" font-size="8" text-anchor="middle">delete_all</text>
<text x="270" y="48" fill="var(--s2)" font-size="8">injected — ran</text>
<text x="70" y="86" fill="var(--ink)" font-size="9" text-anchor="end">safe</text>
<rect x="78" y="76" width="90" height="16" fill="var(--s1)"/>
<text x="123" y="88" fill="var(--ink)" font-size="8" text-anchor="middle">read_file</text>
<rect x="172" y="76" width="150" height="16" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 3"/>
<text x="247" y="88" fill="var(--muted)" font-size="8" text-anchor="middle">"; delete_all" is inert text</text>
</svg>
^ Same malicious argument: interpolation executes two verbs including the injected delete_all; argv executes one and the payload stays inert data inside a single argument.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the malicious argument passes the schema check, that string interpolation runs more than one command, that the injected verb executes under interpolation, that argv runs exactly one command (the intended program), and that argv keeps the payload as a single literal argument.

```python filename=modules/agent-harness/code/arginject-inter-01/arginject.py:91-107 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the injection ever stopped landing on the unsafe path or the argv path ever let the payload split:

```text filename=arginject.py --check
SELF-TEST — a schema-valid argument still injects under string interpolation; an argv list keeps it a single inert value
----------------------------------------------------------------------------------------------------------------
  the malicious argument passes the schema check = True
  string interpolation runs more than one command = True (2 commands)
  the injected verb executes under interpolation = True (verbs ['read_file', 'delete_all'])
  argv runs exactly one command, the intended program = True (verbs ['read_file'])
  argv keeps the payload as one literal argument = True ('report.txt; delete_all data')
```

**The self-test asserts the argument passes the schema check and still injects — pinning the exact gap this module fills — and then that the argv path both runs only the intended program and preserves the payload verbatim, so a pass certifies the fix blocks the injection without silently mangling a legitimate (if odd) filename.**

## Definition of done

You can explain why schema validation of an argument's type and shape does not make its contents safe to use.
You can explain how a command string handed to a shell lets an argument's metacharacters become commands.
You can describe the argv-list fix and why exec with no shell delivers the argument as a single inert value.
You can name the same pattern in other settings — parameterized queries for SQL, structured bodies for HTTP — as "keep the value in a slot, never in the sentence."
You can explain why this bug is especially relevant in agent harnesses, where arguments come from a model that can be confused or steered.

## Boss fight

Suppose you cannot avoid a shell — a tool genuinely needs shell features like pipes or globbing. Reason about what to do, because "just use argv" is now off the table. The first move is to question the premise: often the shell features can be replaced by structured calls (do the glob in code, connect processes with pipes you create programmatically), keeping the no-shell guarantee. When a shell is truly required, the value must be quoted for that specific shell before interpolation — Python's shlex.quote wraps a value so the shell treats it as one literal token — but this is strictly worse than argv, because quoting is shell-dialect-specific and easy to get subtly wrong, and one un-quoted interpolation reopens the whole hole. The lesson is that escaping is a fallback, not a peer of parameterization: parameterization is safe by construction, while escaping is safe only if you never miss a spot.

Now the trap that a naive allowlist walks into. A tempting cheaper fix is to reject arguments containing dangerous characters — block semicolons, ampersands, backticks. This is a denylist, and denylists of shell metacharacters are notoriously incomplete: newlines, dollar-sign command substitution, glob characters, and shell-specific syntax all provide alternate injection routes, and blocking them also rejects legitimate arguments that happen to contain those bytes. Worse, a denylist gives a false sense of safety that discourages the real fix. The robust posture is structural, not lexical: pass values through slots so their contents are irrelevant to parsing, and if you must validate contents, use a narrow allowlist of what is permitted (this argument must match a filename pattern) rather than a denylist of what is forbidden.

**When a shell is unavoidable, quoting with a shell-aware quoter is a fallback that is safe only if never missed, while argv is safe by construction; and never rely on a denylist of dangerous characters — it is always incomplete, so validate with a narrow allowlist and keep values in structural slots.**

## External resources

The OWASP guidance on OS command injection and SQL injection describes the interpolation-versus-parameterization distinction and why parameterized APIs are the primary defense.
Python's subprocess documentation warns against shell=True with untrusted input and recommends passing an argument list; the DB-API and libraries like psycopg document parameterized queries with placeholders.
The topic's own modules on validating a tool call against its schema and on treating tool output as data cover the neighboring guarantees — a well-typed call and an untrusted-content boundary — that this one completes on the execution side.
