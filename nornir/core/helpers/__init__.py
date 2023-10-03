from typing import Any, Dict, Optional, MutableMapping


def merge_two_dicts(x: Dict[Any, Any], y: Dict[Any, Any]) -> Dict[Any, Any]:
    try:
        z = x.copy()
    except AttributeError:
        z = dict(x)
    z.update(y)
    return z


def nested_update(
    dct: Optional[MutableMapping[Any, Any]], upd: Optional[MutableMapping[Any, Any]]
) -> None:
    """
    Nested update of dict-like 'dct' with dict-like 'upd'.

    This function merges 'upd' into 'dct' even with nesting.
    By the same keys, the values will be overwritten.

    :param dct: Dictionary-like to update
    :param upd: Dictionary-like to update with
    :return: None
    """
    # update with dict-likes only
    if not isinstance(dct, MutableMapping) or not isinstance(upd, MutableMapping):
        return

    for key in upd:
        if (
            key in dct
            and isinstance(dct[key], MutableMapping)
            and isinstance(upd[key], MutableMapping)
        ):
            nested_update(dct[key], upd[key])
        else:
            dct[key] = upd[key]
