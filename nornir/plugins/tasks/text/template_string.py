from typing import Any, Optional, Dict, Callable

from nornir.core.helpers import jinja_helper
from nornir.core.task import Result, Task

FiltersDict = Optional[Dict[str, Callable[..., str]]]


def template_string(
    task: Task, template: str, jinja_filters: FiltersDict = None, **kwargs: Any
) -> Result:
    """
    Renders a string with jinja2. All the host data is available in the template

    Arguments:
        template (string): template string
        jinja_filters (dict): jinja filters to enable. Defaults to nornir.config.jinja2.filters
        **kwargs: additional data to pass to the template

    Returns:
        Result object with the following attributes set:
          * result (``string``): rendered string
    """
    jinja_filters = jinja_filters or {} or task.nornir.config.jinja2.filters
    text = jinja_helper.render_from_string(
        template=template, host=task.host, jinja_filters=jinja_filters, **kwargs
    )
    return Result(host=task.host, result=text)
