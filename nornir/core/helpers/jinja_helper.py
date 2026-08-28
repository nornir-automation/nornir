from __future__ import annotations

from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def render_from_file(
    path: str, template: str, jinja_filters: dict[str, Any] | None = None, **kwargs: Any
) -> str:
    """Render a jinja2 template read from a directory.

    The environment uses ``StrictUndefined``, so referring to a variable that was not
    passed in is an error rather than an empty string, and ``trim_blocks`` is on.

    Arguments:
        path: Directory the templates are loaded from
        template: Name of the template within ``path``
        jinja_filters: Extra filters to make available to the template
        **kwargs: Variables to render the template with

    Returns:
        The rendered template.

    """
    # This module has no callers inside nornir and jinja2 is not a dependency of it, so
    # importing it only works when something else in the environment brings jinja2 in.
    # nornir_jinja2 is the supported way to render templates.
    jinja_filters = jinja_filters or {}
    env = Environment(loader=FileSystemLoader(path), undefined=StrictUndefined, trim_blocks=True)
    env.filters.update(jinja_filters)
    t = env.get_template(template)
    return t.render(**kwargs)


def render_from_string(
    template: str, jinja_filters: dict[str, Any] | None = None, **kwargs: Any
) -> str:
    """Render a jinja2 template given as a string.

    As with :py:func:`render_from_file`, the environment uses ``StrictUndefined`` and
    ``trim_blocks``. Templates rendered this way cannot use ``include`` or ``extends``,
    since there is no loader to resolve the other templates with.

    Arguments:
        template: The template itself
        jinja_filters: Extra filters to make available to the template
        **kwargs: Variables to render the template with

    Returns:
        The rendered template.

    """
    jinja_filters = jinja_filters or {}
    env = Environment(undefined=StrictUndefined, trim_blocks=True)
    env.filters.update(jinja_filters)
    t = env.from_string(template)
    return t.render(**kwargs)
