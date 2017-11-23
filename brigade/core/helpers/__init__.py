def merge_two_dicts(x, y):
    try:
        z = x.copy()
    except AttributeError:
        z = x.items()
    z.update(y)
    return z


def format_string(text, task, **kwargs):
    merged = merge_two_dicts(task.host.items(), task.brigade.inventory.data)
    return text.format(host=task.host,
                       **merge_two_dicts(merged, kwargs))
