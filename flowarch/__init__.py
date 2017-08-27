from abc import ABCMeta, abstractmethod
from typing import Callable, Dict, List, Set


class Var:
    """A variable in the flow network."""
    def __init__(self, name, docs):
        self.name = name
        self.docs = docs

    def __str__(self):
        return self.name


class State:
    """A state of the flow network, which contains definitions for all the variables."""
    def __init__(self):
        self.values = {}

    def __getitem__(self, key: Var):
        if key in self.values:
            return self.values[key]
        else:
            raise ValueError("state does not contain value for variable '{}'".format(key.name))

    def __setitem__(self, key: Var, value):
        self.values[key] = value

    def __delitem__(self, key: Var):
        if key in self.values:
            del self.values[key]
        else:
            raise ValueError("state does not contain value for variable '{}'".format(key.name))

    def __str__(self):
        desc = "state variables:\n"
        for var, value in self.values.items():
            desc += "  {} = {}\n".format(var, value)
        return desc


class Flow:
    def __init__(self, flow_function: Callable[[State], None], in_vars: Set[Var], out_vars: Set[Var]):
        self.flow_function = flow_function
        self.in_vars = in_vars
        self.out_vars = out_vars

    def __call__(self, state: State):
        self.flow_function(state)

    def __rshift__(self, other: "Flow") -> "Flow":
        if isinstance(other, Flow):
            def chain(state):
                self.flow_function(state)
                other.flow_function(state)
            return Flow(chain,
                        self.in_vars.union(self.out_vars.difference(other.in_vars)),
                        self.out_vars.union(other.out_vars))
        else:
            raise ValueError("flows can only be combined with other flows")


def flow(in_vars: List[Var], out_vars: List[Var]):
    def wrapper(flow_function: Callable[[State], None]) -> Flow:
        return Flow(flow_function, set(in_vars), set(out_vars))
    return wrapper


def switch(condition: Var, yes: Flow, no: Flow):
    def check(state):
        if state[condition]:
            yes(state)
        else:
            no(state)


def loop()