def merge_two_dicts(x, y):
    try:
        z = x.copy()
    except AttributeError:
        z = dict(x)
    z.update(y)
    return z


def format_string(text, task, **kwargs):
    return text.format(host=task.host,
                       **merge_two_dicts(task.host.items(), kwargs))
