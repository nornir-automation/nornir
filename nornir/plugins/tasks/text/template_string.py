from nornir.core.helpers import jinja_helper, merge_two_dicts
from nornir.core.task import Result


def template_string(task, template, jinja_filters=None, **kwargs):
    """
    Renders a string with jinja2. All the host data is available in the tempalte

    Arguments:
        template (string): template string
        jinja_filters (dict): jinja filters to enable. Defaults to nornir.config.jinja_filters
        **kwargs: additional data to pass to the template

    Returns:
        :obj:`nornir.core.task.Result`:
            * result (``string``): rendered string
    """
    jinja_filters = jinja_filters or {} or task.nornir.config.jinja_filters
    merged = merge_two_dicts(task.host, kwargs)
    text = jinja_helper.render_from_string(
        template=template, host=task.host, jinja_filters=jinja_filters, **merged
    )
    return Result(host=task.host, result=text)
