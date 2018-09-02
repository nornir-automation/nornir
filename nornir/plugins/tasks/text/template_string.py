from typing import Any, Optional, Dict, Callable

from nornir.core.helpers import jinja_helper
from nornir.core.task import Result, Task

FiltersDict = Optional[Dict[str, Callable[..., str]]]


def template_string(
    task: Task, template: str, jinja_filters: FiltersDict = None, path: str = None, **kwargs: Any
):
    """
    Renders a string with jinja2. All the host data is available in the tempalte

    Arguments:
        template (string): template string
        jinja_filters (dict): jinja filters to enable. Defaults to nornir.config.jinja_filters
        path (string): if set, load FileSystemLoader with this path, Defaults to None
        **kwargs: additional data to pass to the template

    Returns:
        Result object with the following attributes set:
          * result (``string``): rendered string
    """
    jinja_filters = jinja_filters or {} or task.nornir.config.jinja_filters
    text = jinja_helper.render_from_string(
        template=template,
        host=task.host,
        jinja_filters=jinja_filters,
        path=path,
    )
    return Result(host=task.host, result=text)
