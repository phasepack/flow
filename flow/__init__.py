from typing import Any, Callable, Dict, List
from time import time as _time


class Var:
    """A variable in the flow network."""
    def __init__(self, name, docs):
        self.name = name
        self.docs = docs

    def __repr__(self):
        return "<flow.Var : {}>".format(self.name)


class Tape:
    def __init__(self, loop):
        self.loop = loop
        self.histories = {}
        self.counter = 0

    def __getitem__(self, key):
        var = key[0]
        index = key[1]
        return self.histories[var][index]

    def __setitem__(self, var, value):
        if var not in self.histories:
            self.histories[var] = []
        self.histories[var].append(value)

    def __str__(self):
        s = "Tape[ n = {} \n".format(self.counter)
        for var, history in self.histories.items():
            s += "    " + var.name + " => " + ", ".join(map(str, history)) + "\n"
        return s + "]"

    def advance(self, values):
        self.counter += 1
        for var in self.loop.vars:
            if var in values:
                self[var] = values[var]


class State:
    def __init__(self):
        self.values = {}
        self.loop_stack = []
        self.tapes = {}
        self.saved_tapes = {}

    def get_tape(self, key):
        if isinstance(key, int):
            key = self.loop_stack[key]
        return self.tapes[key]

    def __getitem__(self, key):
        if isinstance(key, Var):
            return self.values[key]
        elif isinstance(key, tuple):
            if len(key) == 3:
                loop = key[0]
                var = key[1]
                index = key[2]
            else:
                loop = -1
                var = key[0]
                index = key[1]
            return self.get_tape(loop)[var,index]

    def __setitem__(self, var, value):
        self.values[var] = value

    def __delitem__(self, var):
        del self.values[var]

    def push_loop(self, loop):
        self.loop_stack.append(loop)
        self.tapes[loop] = Tape(loop)

    def pop_loop(self):
        loop = self.loop_stack.pop()
        tape = self.tapes[loop]
        del self.tapes[loop]
        if loop.save:
            self.saved_tapes[tape.loop] = tape

    def advance(self, loop):
        self.tapes[loop].advance(self.values)

    def __str__(self):
        s = "State[\n"
        for var in self.values:
            s += "    " + var.name + " => " + str(self.values[var]) + "\n"
        for loop in self.loop_stack:
            s += str(self.tapes[loop]) + "\n"
        return s + "]"


class Flow:
    def __init__(self, flow_op: Callable[[Dict, State], None]):
        self.flow_op = flow_op

    def operate(self, inputs, state):
        self.flow_op(inputs, state)

    def __rshift__(self, other: "Flow") -> "Flow":
        if other is None:
            return self

        def chain(inputs, state):
            self.operate(inputs, state)
            other.operate(inputs, state)
        return Flow(chain)


def test_condition(state):
    condition = state[CONDITION]
    del state[CONDITION]
    return condition


class Loop(Flow):
    def __init__(self, body_flow: Flow, condition_flow: Flow, loop_vars: List[Var], save: bool=False):
        self.body_flow = body_flow
        self.condition_flow = condition_flow
        self.vars = loop_vars
        self.save = save

        def flow_op(inputs, state):
            state.push_loop(self)
            state.advance(self)
            self.condition_flow.operate(inputs, state)

            while test_condition(state):
                self.body_flow.operate(inputs, state)
                self.condition_flow.operate(inputs, state)
                state.advance(self)

            state.pop_loop()

        super(Loop, self).__init__(flow_op)


def flow(flow_op: Callable[[Dict, State], None]) -> Flow:
    return Flow(flow_op)

# Useful flow decorators


def inspect(f):
    def inspected_flow(inp, state):
        print(str(state))
        f.operate(inp, state)
    return Flow(inspected_flow)


TIME = Var('t', """The system time.""")


def time(f):
    def timed_flow(inp, state):
        f.operate(inp, state)
        state[TIME] = _time()
    return Flow(timed_flow)


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


#
# # Backtracking
# M = flow.Var('M', "The maximum value of f over the last several iterations.")
#
# @flow
# def backtracking_condition(inp, state):
#     state[flow.CONDITION] = state[f] - \
#                             (state[M] + np.real(state[Dx].ravel().T @ state[gradf, -1].ravel()) + la.norm(state[Dx].ravel()) ** 2 / (2 * state[tau, -1])) > inp['EPSILON']
#
# @flow
# def backtracking_window_estimator(inp, state):
#     state[M] =