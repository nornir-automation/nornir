from jinja2 import Environment, FileSystemLoader, StrictUndefined


def render_from_file(path, template, **kwargs):
    env = Environment(loader=FileSystemLoader(path),
                      undefined=StrictUndefined,
                      trim_blocks=True)
    #  env.filters.update(jinja_filters.filters())
    template = env.get_template(template)
    return template.render(**kwargs)


def render_from_string(template, **kwargs):
    env = Environment(undefined=StrictUndefined,
                      trim_blocks=True)
    template = env.from_string(template)
    return template.render(**kwargs)
