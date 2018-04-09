from brigade.core.helpers import format_string, jinja_helper, merge_two_dicts
from brigade.core.task import Result


def template_file(task, template, path, jinja_filters=None, **kwargs):
    """
    Renders contants of a file with jinja2. All the host data is available in the tempalte

    Arguments:
        template (string): filename
        path (string): path to dir with templates (will be rendered with format)
        jinja_filters (dict): jinja filters to enable. Defaults to brigade.config.jinja_filters
        **kwargs: additional data to pass to the template

    Returns:
        :obj:`brigade.core.task.Result`:
            * result (``string``): rendered string
    """
    jinja_filters = jinja_filters or {} or task.brigade.config.jinja_filters
    merged = merge_two_dicts(task.host, kwargs)
    path = format_string(path, task, **kwargs)
    template = format_string(template, task, **kwargs)
    text = jinja_helper.render_from_file(
        template=template,
        path=path,
        host=task.host,
        jinja_filters=jinja_filters,
        **merged
    )
    return Result(host=task.host, result=text)
