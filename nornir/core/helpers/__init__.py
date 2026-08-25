from __future__ import annotations

from typing import Any


def merge_two_dicts(x: dict[Any, Any], y: dict[Any, Any]) -> dict[Any, Any]:
    """Return a shallow copy of ``x`` updated with ``y``.

    Neither argument is modified. Where both define the same key, the value from ``y``
    wins.

    Arguments:
        x: Mapping to start from. Anything ``dict`` accepts works, not only a ``dict``
        y: Mapping whose keys take precedence

    Returns:
        The merged dictionary.

    """
    # Nothing in nornir calls this any more. It predates {**x, **y} being available.
    try:
        z = x.copy()
    except AttributeError:
        z = dict(x)
    z.update(y)
    return z
