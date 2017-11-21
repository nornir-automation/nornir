from brigade.core.helpers import jinja_helper, merge_two_dicts


def template_string(task, template, **kwargs):
    """
    Renders a string with jinja2. All the host data is available in the tempalte

    Arguments:
        template (string): template string
        **kwargs: additional data to pass to the template

    Returns:
        dictionary:
            * result (``string``): rendered string
    """
    merged = merge_two_dicts(task.host, kwargs)
    return {
        "result": jinja_helper.render_from_string(template=template,
                                                  host=task.host, **merged)}
