from brigade.core.helpers import jinja_helper, merge_two_dicts
from brigade.core.task import Result


def template_string(task, template, **kwargs):
    """
    Renders a string with jinja2. All the host data is available in the tempalte

    Arguments:
        template (string): template string
        **kwargs: additional data to pass to the template

    Returns:
        :obj:`brigade.core.task.Result`:
            * result (``string``): rendered string
    """
    merged = merge_two_dicts(task.host, kwargs)
    text = jinja_helper.render_from_string(template=template,
                                           host=task.host, **merged)
    return Result(host=task.host, result=text)
