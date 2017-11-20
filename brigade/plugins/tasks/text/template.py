from brigade.core.helpers import format_string, jinja_helper, merge_two_dicts


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


def template_file(task, template, path, **kwargs):
    """
    Renders contants of a file with jinja2. All the host data is available in the tempalte

    Arguments:
        template (string): filename
        path (string): path to dir with templates (will be rendered with format)
        **kwargs: additional data to pass to the template

    Returns:
        dictionary:
            * result (``string``): rendered string
    """
    path = format_string(path, task, **kwargs)
    merged = merge_two_dicts(task.host, kwargs)
    return {
        "result": jinja_helper.render_from_file(template=template, path=path,
                                                host=task.host, **merged)}
