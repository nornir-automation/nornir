from jinja2 import Environment, FileSystemLoader, StrictUndefined


def render_from_file(path, template, jinja_filters=None, **kwargs):
    jinja_filters = jinja_filters or {}
    env = Environment(
        loader=FileSystemLoader(path), undefined=StrictUndefined, trim_blocks=True
    )
    env.filters.update(jinja_filters)
    template = env.get_template(template)
    return template.render(**kwargs)


def render_from_string(template, jinja_filters=None, **kwargs):
    jinja_filters = jinja_filters or {}
    env = Environment(undefined=StrictUndefined, trim_blocks=True)
    env.filters.update(jinja_filters)
    template = env.from_string(template)
    return template.render(**kwargs)
