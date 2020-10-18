from ast import literal_eval
import shlex
from typing import Any, List, Optional

from nornir.core.filter import AND, OR, F, F_FILTER, NOT


EmptyExpression = SyntaxError("got empty expression")

_NOT = "NOT"

_EQUAL = "=="
_NOT_EQUAL = "!="

_AND = "AND"
_OR = "OR"

_LP = "("
_RP = ")"
_LB = "["
_RB = "]"
_COMMA = ","

_EOF = ""

_P_P = 5
_P_NOT = 4
_P_AND = 3
_P_OR = 2


def _parse_list(sh: shlex.shlex) -> List[Any]:
    r: List[Any] = []
    while True:
        cur = sh.get_token()
        if cur == _EOF:
            raise SyntaxError("expected ']', got EOF")
        elif cur == _RB:
            break
        elif cur == _COMMA:
            continue
        else:
            r.append(literal_eval(cur))
    return r


def _parse_op(sh: shlex.shlex) -> F_FILTER:
    left = sh.get_token()

    op = sh.get_token()
    if op in ["=", "!"]:
        op += sh.get_token()

    cur = sh.get_token()
    if cur == _LB:
        right = _parse_list(sh)
    else:
        right = literal_eval(cur)

    if op == _EQUAL:
        return F(**{left: right})
    elif op == _NOT_EQUAL:
        return NOT(F(**{left: right}))
    else:
        return F(**{f"{left}__{op}": right})


def _parse_parenthesis(sh: shlex.shlex) -> F_FILTER:
    cur = sh.get_token()
    if cur in ["", ")"]:
        raise SyntaxError("expresession inside paranthesis is empty")

    sh.push_token(cur)

    f = _parse(sh, _P_P)
    if f is None:
        raise ValueError("parenthesis expression didn't yield any filter'")

    cur = sh.get_token()
    if cur != _RP:
        raise SyntaxError(f"expected ')', got '{cur}'")
    return f


def _parse_single_expression(sh: shlex.shlex, priority: int) -> Optional[F_FILTER]:
    cur = sh.get_token()

    if cur in [_EOF, _RP]:
        sh.push_token(cur)
        return None
    elif cur == _NOT:
        e = _parse_single_expression(sh, _P_NOT)
        if e is None:
            raise EmptyExpression
        f: F_FILTER = NOT(e)
    elif cur == _LP:
        f = _parse_parenthesis(sh)
    else:
        sh.push_token(cur)
        f = _parse_op(sh)
    return f


def _parse(sh: shlex.shlex, priority: int) -> Optional[F_FILTER]:
    f = _parse_single_expression(sh, priority)
    if f is None:
        return None

    cur_p = priority
    while True:
        cur = sh.get_token()

        if cur in [_EOF, _RP]:
            sh.push_token(cur)
            return f
        elif cur == "AND":
            left = f
            right = _parse(sh, _P_AND)

            if right is None:
                raise EmptyExpression

            if cur_p > _P_AND:
                f = AND(left, right)
            else:
                f = AND(right, left)
        elif cur == "OR":
            left = f
            right = _parse(sh, _P_OR)

            if right is None:
                raise EmptyExpression

            if cur_p > _P_OR:
                f = OR(left, right)
            else:
                f = OR(right, left)
        else:
            raise SyntaxError("you shouldn't be here")

    return f


def parse(text: str) -> F_FILTER:
    sh = shlex.shlex(text)
    f = _parse(sh, 0)
    if f is None:
        if f is None:
            raise EmptyExpression

    cur = sh.get_token()
    if cur != _EOF:
        raise SyntaxError(f"expected EOF, got '{cur}'")

    return f
