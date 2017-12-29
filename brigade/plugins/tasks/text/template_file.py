from brigade.core.helpers import format_string, jinja_helper, merge_two_dicts
from brigade.core.task import Result


def template_file(task, template, path, **kwargs):
    """
    Renders contants of a file with jinja2. All the host data is available in the tempalte

    Arguments:
        template (string): filename
        path (string): path to dir with templates (will be rendered with format)
        **kwargs: additional data to pass to the template

    Returns:
        :obj:`brigade.core.task.Result`:
            * result (``string``): rendered string
    """
    merged = merge_two_dicts(task.host, kwargs)
    path = format_string(path, task, **kwargs)
    template = format_string(template, task, **kwargs)
    text = jinja_helper.render_from_file(template=template, path=path,
                                         host=task.host, **merged)
    return Result(host=task.host, result=text)
