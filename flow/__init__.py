from typing import Any, Callable, Dict


class Var:
    """A variable in the flow network."""
    def __init__(self, name, docs):
        self.name = name
        self.docs = docs

    def __str__(self):
        return self.name


class Tape:
    def __init__(self, var):
        self.var = var
        self.value = None
        self.previous_value = None
        self.history = None

    def track(self):
        if not self.history:
            self.history = []

    def __getitem__(self, key):
        if key == (-1,):
            return self.previous_value

        return self.history[key]

    def advance(self):
        self.previous_value = self.value

        if self.history is not None:
            self.history.append(self.value)

        self.value = None

    def __str__(self):
        return "  {} -> {}".format(self.var.name, self.value)


class State:
    """A state of the flow network, which contains definitions for all the variables."""
    def __init__(self):
        self.tapes = {}

    def __getitem__(self, key):
        if isinstance(key, Var):
            if key in self.tapes:
                return self.tapes[key].value
            else:
                raise ValueError("state does not contain tape for variable '{}'".format(key.name))
        elif isinstance(key, tuple):
            var = key[0]
            if var in self.tapes:
                key = key[1:]
                return self.tapes[var][key]
            else:
                raise ValueError("state does not contain tape for variable '{}'".format(var.name))

    def __setitem__(self, key: Var, value):
        if key not in self.tapes:
            self.tapes[key] = Tape(key)

        self.tapes[key].value = value

    def __delitem__(self, key: Var):
        if key in self.tapes:
            del self.tapes[key]
        else:
            raise ValueError("state does not contain tape for variable '{}'".format(key.name))

    def __str__(self):
        desc = "state variables:\n"
        for tape in self.tapes:
            desc += tape
        return desc


class Flow:
    def __init__(self, flow_function: Callable[[Dict, Dict, State], None], track=None):
        self.flow_function = flow_function
        self.track = track

    def __call__(self, state: State):
        if self.track:
            for var in self.track:
                state.tapes[var].track()

        self.flow_function(inputs, options, state)

    def __rshift__(self, other: "Flow") -> "Flow":
        if isinstance(other, Flow):
            def chain(state):
                self.flow_function(state)
                other.flow_function(state)
            return Flow(chain)
        else:
            raise ValueError("flows can only be combined with other flows")


def flow():
    def wrap(flow_function: Callable[[Any, Any, State], None]) -> Flow:
        return Flow(flow_function)
    return wrap


CONDITION = Var('?', """The condition supplied to switches and loops.""")


def switch(yes: Flow, no: Flow=None) -> Flow:
    def check(inputs, options, state):
        # Check the condition that was passed in
        condition = state[CONDITION]
        del state[CONDITION]

        if condition:
            if yes:
                yes(inputs, options, state)
        else:
            if no:
                no(inputs, options, state)
    return Flow(check)


def loop(conditioner: Flow, body: Flow, advance=None, track=None) -> Flow:
    def check(inputs, options, state):
        while True:
            if track:
                for var in track:
                    if var in state.tapes:
                        state.tapes[var].track()

            conditioner(inputs, options, state)

            # Check the condition that was passed in
            condition = state[CONDITION]
            del state[CONDITION]

            if condition:
                if advance:
                    for var in advance:
                        if var in state.tapes:
                            state.tapes[var].advance()

                body(inputs, options, state)
            else:
                break
    return Flow(check)
