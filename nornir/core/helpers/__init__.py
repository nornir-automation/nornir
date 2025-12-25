from typing import Any


def merge_two_dicts(x: dict[Any, Any], y: dict[Any, Any]) -> dict[Any, Any]:
    try:
        z = x.copy()
    except AttributeError:
        z = dict(x)
    z.update(y)
    return z
