def upper(blah: str) -> str:
    return blah.upper()


def lower(blah: str) -> str:
    return blah.lower()


def jinja_filters():
    return {"upper": upper, "lower": lower}
