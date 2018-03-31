def merge_two_dicts(x, y):
    try:
        z = x.copy()
    except AttributeError:
        z = dict(x)
    z.update(y)
    return z


def format_object(obj, host, **kwargs):
    if isinstance(obj, dict):
        return {format_object(k, host, **kwargs): format_object(v, host, **kwargs)
                for k, v in obj.items()}
    elif any([isinstance(obj, t) for t in [list, set]]):
        return [format_object(e, host, **kwargs) for e in obj]
    elif isinstance(obj, str):
        return obj.format(**merge_two_dicts(host.items(), kwargs))
    else:
        return obj
