from typing import Any, List

from nornir.core.inventory import Host


class F_BASE:
    def __call__(self, host: Host) -> bool:
        raise NotImplementedError()


class F_OP_BASE(F_BASE):
    def __init__(self, op1: F_BASE, op2: F_BASE) -> None:
        self.op1 = op1
        self.op2 = op2

    def __and__(self, other: F_BASE) -> "AND":
        return AND(self, other)

    def __or__(self, other: F_BASE) -> "OR":
        return OR(self, other)

    def __repr__(self) -> str:
        return "( {} {} {} )".format(self.op1, self.__class__.__name__, self.op2)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, F_OP_BASE):
            # don't compare against unrelated types
            return NotImplemented
        return self.__class__ == other.__class__ and (
            (self.op1 == other.op1 and self.op2 == other.op2)
            or (self.op1 == other.op2 and self.op2 == other.op1)
        )


class AND(F_OP_BASE):
    def __call__(self, host: Host) -> bool:
        return self.op1(host) and self.op2(host)


class OR(F_OP_BASE):
    def __call__(self, host: Host) -> bool:
        return self.op1(host) or self.op2(host)


class F(F_BASE):
    def __init__(self, **kwargs: Any) -> None:
        self.filters = kwargs

    def __call__(self, host: Host) -> bool:
        return all(F._verify_rules(host, k.split("__"), v) for k, v in self.filters.items())

    def __and__(self, other: "F") -> AND:
        return AND(self, other)

    def __or__(self, other: "F") -> OR:
        return OR(self, other)

    def __invert__(self) -> "F":
        return NOT_F(**self.filters)

    def __repr__(self) -> str:
        return "<Filter ({})>".format(self.filters)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, F):
            # don't compare against unrelated types
            return NotImplemented
        return self.__class__ == other.__class__ and self.filters == other.filters

    @staticmethod
    def _verify_rule(data: Any, rule: str, value: Any) -> bool:
        operator = "__{}__".format(rule)
        if hasattr(data, operator):
            return getattr(data, operator)(value) is True

        if hasattr(data, rule):
            if callable(getattr(data, rule)):
                return bool(getattr(data, rule)(value))
            return bool(getattr(data, rule) == value)

        if rule == "in":
            return bool(data in value)

        if rule == "any":
            if isinstance(data, list):
                return any(x in data for x in value)
            return any(x == data for x in value)

        if rule == "all":
            if isinstance(data, list):
                return all(x in data for x in value)

            # it doesn't make sense to check a single value meets more than one case
            return False

        return bool(data.get(rule) == value)

    @staticmethod
    def _verify_rules(data: Any, rule: List[str], value: Any) -> bool:
        if len(rule) > 1:
            try:
                return F._verify_rules(data.get(rule[0], {}), rule[1:], value)
            except AttributeError:
                return False

        elif len(rule) == 1:
            return F._verify_rule(data, rule[0], value)

        else:
            raise Exception("I don't know how I got here:\n{}\n{}\n{}".format(data, rule, value))


class NOT_F(F):
    def __call__(self, host: Host) -> bool:
        return not any(F._verify_rules(host, k.split("__"), v) for k, v in self.filters.items())

    def __invert__(self) -> F:
        return F(**self.filters)

    def __repr__(self) -> str:
        return "<Filter NOT ({})>".format(self.filters)
