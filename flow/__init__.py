from typing import Any, Callable, Dict, List, Optional
from time import time as _time


class Var:
    """A variable in the flow network."""
    def __init__(self, name, docs):
        self.name = name
        self.docs = docs

    def __repr__(self):
        return "<flow.Var: '{}'>".format(self.name)


class Tape:
    def __init__(self, state, loop):
        self.state = state
        self.loop = loop
        self.histories = {}

    def __getitem__(self, key):
        var = key[0]
        index = key[1]
        return self.histories[var][index]

    def __setitem__(self, var, value):
        if var not in self.histories:
            self.histories[var] = []
        self.histories[var].append(value)

    def __contains__(self, var):
        return var in self.histories

    def __str__(self):
        s = "Tape[ n = {} \n".format(self.state[self.loop.counter])
        for var, history in self.histories.items():
            s += "    " + var.name + " => " + ", ".join(map(str, history)) + "\n"
        return s + "]"

    def advance(self, only_vars: List[vars]=None):
        self.state[self.loop.counter] += 1
        for var in only_vars if only_vars is not None else self.loop.vars:
            if var in self.state.values:
                self[var] = self.state.values[var]


class State:
    def __init__(self):
        self.values = {}
        self.loops = []
        self.tapes = {}
        self.saved_tapes = {}

    def __getitem__(self, key):
        if isinstance(key, Var):
            return self.values[key]
        elif isinstance(key, tuple):
            if len(key) == 3:
                if isinstance(key[0], Loop):
                    loop = key[0]
                else:
                    loop = self.loops[key[0]]
                var = key[1]
                index = key[2]
            else:
                loop = self.loops[-1]
                var = key[0]
                index = key[1]
            return self.tapes[loop][var,index]

    def __setitem__(self, var, value):
        self.values[var] = value

    def __delitem__(self, var):
        del self.values[var]

    def __contains__(self, var):
        return var in self.values

    def push_loop(self, loop):
        self.loops.append(loop)
        self.tapes[loop] = Tape(self, loop)
        self.values[loop.counter] = -1

    def pop_loop(self):
        loop = self.loops.pop()
        if not loop.save:
            del self.tapes[loop]
            del self[loop.counter]

    def advance(self, loop, only_vars: List[Var]=None):
        self.tapes[loop].advance(only_vars=only_vars)

    def __str__(self):
        s = "State[\n"
        for var in self.values:
            s += "    " + var.name + " => " + str(self.values[var]) + "\n"
        for loop in self.loops:
            s += str(self.tapes[loop]) + "\n"
        return s + "]"


class Flow:
    def __init__(self, name: str, flow_op: Callable[[Dict, State], None]):
        self.name = name
        self.flow_op = flow_op

    def operate(self, inputs, state):
        self.flow_op(inputs, state)

    def __rshift__(self, other: "Flow") -> "Flow":
        if other is None:
            return self

        def chain(inputs, state):
            self.operate(inputs, state)
            other.operate(inputs, state)
        return Flow("{} -> {}".format(self.name, other.name), chain)

    def __lshift__(self, other):
        return other >> self

    def __repr__(self):
        return "<flow.Flow: '{}'>".format(self.name)


def test_condition(state):
    condition = state[CONDITION]
    del state[CONDITION]
    return condition


class Loop(Flow):
    def __init__(self, body_flow: Flow, condition_flow: Flow, loop_vars: List[Var]=[], save: bool=False,
                 check_first: bool=True, initial_vars: List[Var]=None):
        self.body_flow = body_flow
        self.condition_flow = condition_flow
        self.vars = loop_vars
        self.save = save
        self.counter = Var('counter', "A loop counter.")

        def flow_op(inputs, state):
            state.push_loop(self)

            # Advance the initial variables (if any)
            state.advance(self, only_vars=initial_vars)

            stop = False

            # Check before the first iteration
            if check_first:
                self.condition_flow.operate(inputs, state)
                stop = not test_condition(state)

            while not stop:
                self.body_flow.operate(inputs, state)
                state.advance(self)
                self.condition_flow.operate(inputs, state)
                stop = not test_condition(state)

            state.pop_loop()

        super(Loop, self).__init__("Loop[{}? => {}]".format(condition_flow.name, body_flow.name), flow_op)


def flow(flow_op: Callable[[Dict, State], None]) -> Flow:
    return Flow(flow_op.__name__, flow_op)


# Useful flows
def inspect(f):
    """Prints the state before any given flow (useful for debugging)."""
    def inspector_flow(inputs, state):
        print(str(state))
    return Flow("inspector", inspector_flow) >> f


TIME = Var('t', """The system time.""")


def time(f):
    """Records the time after any given flow."""
    def timer_flow(inputs, state):
        state[TIME] = _time()
    return f >> Flow("timer", timer_flow)


CONDITION = Var('?', """The condition supplied to switches and loops.""")


def switch(yes: Flow, no: Flow=None) -> Flow:
    def check(inputs, state):
        # Check the condition that was passed in
        condition = state[CONDITION]
        del state[CONDITION]

        if condition:
            if yes:
                yes.operate(inputs, state)
        else:
            if no:
                no.operate(inputs, state)
    return Flow(check)
