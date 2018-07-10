import copy


class F(object):
    AND = "AND"
    OR = "OR"

    def __init__(self, **kwargs):
        self.operator = self.AND
        self.operands = []
        self.filters = list(kwargs.items())
        self.negate = False

    def __call__(self, object):
        if self.operator == self.AND:
            reducer_func = all
        elif self.operator == self.OR:
            reducer_func = any
        matching_result = [o(object) for o in self.operands]
        matching_result += [
            F._verify_rules(object, k.split("__"), v) for k, v in self.filters
        ]
        if self.negate:
            return not reducer_func(matching_result)

        else:
            return reducer_func(matching_result)

    def __and__(self, other):
        res = F()
        if self.operator == self.AND and other.operator == self.AND:
            res.operator = self.AND
            res.operands = self.operands + other.operands
            res.filters = self.filters + other.filters
        else:
            res.operator = self.AND
            res.operands = [self, other]
        return res

    def __or__(self, other):
        res = F()
        if self.operator == self.OR and other.operator == self.OR:
            res.operator = self.OR
            res.oprands = self.operands + other.operands
            res.filters = self.filters + other.filters
        else:
            res.operator = self.OR
            res.operands = [self, other]
        return res

    def __invert__(self):
        res = copy.deepcopy(self)
        res.negate = ~res.negate
        return res

    def __repr__(self):
        if self.negate:
            template = "<Filter NOT {} {}>"
        else:
            template = "<Filter {} {}>"
        return template.format(self.operator, self.operands + self.filters)

    @staticmethod
    def _verify_rules(data, rule, value):
        if len(rule) > 1:
            return F._verify_rules(data.get(rule[0], {}), rule[1:], value)

        elif len(rule) == 1:
            operator = "__{}__".format(rule[0])
            if hasattr(data, operator):
                return getattr(data, operator)(value)

            else:
                return data.get(rule[0]) == value

        else:
            raise Exception(
                "I don't know how I got here:\n{}\n{}\n{}".format(data, rule, value)
            )
