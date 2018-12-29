from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def render_from_file(
    path: str,
    template: str,
    jinja_filters: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> str:
    jinja_filters = jinja_filters or {}
    env = Environment(
        loader=FileSystemLoader(path), undefined=StrictUndefined, trim_blocks=True
    )
    env.filters.update(jinja_filters)
    t = env.get_template(template)
    return t.render(**kwargs)


def render_from_string(
    template: str, jinja_filters: Optional[Dict[str, Any]] = None, **kwargs: Any
) -> str:
    jinja_filters = jinja_filters or {}
    env = Environment(undefined=StrictUndefined, trim_blocks=True)
    env.filters.update(jinja_filters)
    t = env.from_string(template)
    return t.render(**kwargs)
