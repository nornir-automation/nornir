class F(object):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

    def __init__(self, **kwargs):
        self.operator = self.AND
        self.operands = []
        self.filters = list(kwargs.items())

    def match(self, object):
        if self.operator == self.AND:
            reducer_func = all
        elif self.operator == self.OR:
            reducer_func = any
        matching_result = [o.match(object) for o in self.operands]
        matching_result += [object.get(k) == v for k, v in self.filters]
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
