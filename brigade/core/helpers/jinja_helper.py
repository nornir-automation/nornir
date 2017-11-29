from brigade.core.exceptions import TemplateError


from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateSyntaxError


def render_from_file(path, template, **kwargs):
    env = Environment(loader=FileSystemLoader(path),
                      undefined=StrictUndefined,
                      trim_blocks=True)

    try:
        template = env.get_template(template)
    except TemplateSyntaxError as e:
        raise TemplateError(e.message, e.lineno,
                            name=e.name, filename=e.filename)

    return template.render(**kwargs)


def render_from_string(template, **kwargs):
    env = Environment(undefined=StrictUndefined,
                      trim_blocks=True)
    try:
        template = env.from_string(template)
    except TemplateSyntaxError as e:
        raise TemplateError(e.message, e.lineno,
                            name=e.name, filename=e.filename)
    return template.render(**kwargs)
