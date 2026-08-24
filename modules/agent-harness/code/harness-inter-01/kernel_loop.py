"""The kernel: the agent loop. It imports ONLY seams (plus the standard library),
never a concrete provider, tool, or sandbox. guard.py fails the build if that
rule is broken. The loop receives its provider and tools as arguments, so it
never needs to name a concrete one."""
from seams import Msg


def run(provider, tools, task, max_steps=8):
    """Drive whatever provider and tools it is handed. Returns (answer, steps)."""
    messages = [Msg("user", task)]
    for step in range(1, max_steps + 1):
        reply = provider.respond(messages)
        if reply.final is not None:
            return reply.final, step
        tool = tools.get(reply.tool)
        result = tool.run(reply.args) if tool else "ERROR: no tool " + reply.tool
        messages.append(Msg("assistant", "", tool=reply.tool, args=reply.args))
        messages.append(Msg("tool", result))
    return None, max_steps
