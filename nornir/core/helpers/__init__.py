from typing import Any, Dict


def merge_two_dicts(x: Dict[Any, Any], y: Dict[Any, Any]) -> Dict[Any, Any]:
    try:
        z = x.copy()
    except AttributeError:
        z = dict(x)
    z.update(y)
    return z
