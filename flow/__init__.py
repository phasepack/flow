from typing import Any, Callable, Dict, List


class Var:
    """A variable in the flow network."""
    def __init__(self, name, docs):
        self.name = name
        self.docs = docs

    def __str__(self):
        return self.name


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
        self.tapes = {}

    def __getitem__(self, var):
        return self.values[var]

    def __setitem__(self, var, value):
        self.values[var] = value

    def __delitem__(self, var):
        del self.values[var]

    def push_loop(self, loop):
        self.tapes[loop] = Tape(loop)

    def pop_loop(self, loop):
        del self.tapes[loop]

    def advance(self, loop):
        self.tapes[loop].advance(self.values)

    def __str__(self):
        s = "State[\n"
        for var in self.values:
            s += "    " + var.name + " => " + str(self.values[var]) + "\n"
        for tape in self.tapes.values():
            s += str(tape) + "\n"
        return s + "]"


class Flow:
    def __init__(self, flow_op: Callable[[Dict, Dict, State], None]):
        self.flow_op = flow_op

    def operate(self, inputs, options, state):
        self.flow_op(inputs, options, state)

    def __rshift__(self, other: "Flow") -> "Flow":
        def chain(inputs, options, state):
            self.operate(inputs, options, state)
            other.operate(inputs, options, state)
        return Flow(chain)


def test_condition(state):
    condition = state[CONDITION]
    del state[CONDITION]
    return condition


class Loop(Flow):
    def __init__(self, body_flow: Flow, condition_flow: Flow, loop_vars: List[Var]):
        self.body_flow = body_flow
        self.condition_flow = condition_flow
        self.vars = loop_vars

        def flow_op(inputs, options, state):
            state.push_loop(self)
            self.condition_flow.operate(inputs, options, state)

            while test_condition(state):
                state.advance(self)
                self.body_flow.operate(inputs, options, state)
                self.condition_flow.operate(inputs, options, state)

            state.pop_loop(self)

        super(Loop, self).__init__(flow_op)


def flow(flow_op: Callable[[Dict, Dict, State], None]) -> Flow:
    return Flow(flow_op)


CONDITION = Var('?', """The condition supplied to switches and loops.""")
LOOP_COUNTER = Var('#', """The number of iterations in a loop.""")


def switch(yes: Flow, no: Flow=None) -> Flow:
    def check(inputs, options, state):
        # Check the condition that was passed in
        condition = state[CONDITION]
        del state[CONDITION]

        if condition:
            if yes:
                yes.operate(inputs, options, state)
        else:
            if no:
                no.operate(inputs, options, state)
    return Flow(check)
