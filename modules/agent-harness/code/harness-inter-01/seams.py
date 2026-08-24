"""The seams — the abstract interfaces the kernel depends on.

The kernel (the agent loop) imports ONLY this file. Concrete providers, tools,
sandboxes and engines implement these interfaces and are wired in from outside
the kernel. This is dependency inversion: the core depends on abstractions, and
the details depend on the core — never the other way round. guard.py enforces it.
"""
from abc import ABC, abstractmethod


class Msg:
    """One turn in the transcript: role is user / assistant / tool."""
    def __init__(self, role, content, tool=None, args=None):
        self.role = role
        self.content = content
        self.tool = tool
        self.args = args


class Reply:
    """What a provider hands back: EITHER a final answer OR a tool call."""
    def __init__(self, final=None, tool=None, args=None):
        self.final = final
        self.tool = tool
        self.args = args


class Provider(ABC):
    """A model, behind one method. A real one calls an API; a fake one is scripted."""
    @abstractmethod
    def respond(self, messages):
        ...


class Tool(ABC):
    """A named capability the model can call."""
    name = "?"

    @abstractmethod
    def run(self, args):
        ...


class Sandbox(ABC):
    """Where a tool's side effects run — a subprocess, a container, a fake."""
    @abstractmethod
    def exec(self, command):
        ...


class Engine(ABC):
    """The loop itself, behind a seam, so it too can be swapped (e.g. for an SDK)."""
    @abstractmethod
    def drive(self, provider, tools, task):
        ...
