def merge_two_dicts(x, y):
    try:
        z = x.copy()
    except AttributeError:
        z = x.expanded_data()
    z.update(y)
    return z


def format_string(text, task, **kwargs):
    merged = merge_two_dicts(task.host.expanded_data(), task.brigade.inventory.data)
    return text.format(host=task.host,
                       **merge_two_dicts(merged, kwargs))
