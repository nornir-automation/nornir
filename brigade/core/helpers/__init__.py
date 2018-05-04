def merge_two_dicts(x, y):
    try:
        z = x.copy()
    except AttributeError:
        z = dict(x)
    z.update(y)
    return z
