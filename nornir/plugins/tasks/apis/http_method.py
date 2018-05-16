from nornir.core.task import Result

import requests


def http_method(task=None, method="get", url="", raise_for_status=True, **kwargs):
    """
    This is a convenience task that uses `requests <http://docs.python-requests.org/en/master/>`_ to
    interact with an HTTP server.

    Arguments:
        method (string): HTTP method to call
        url (string): URL to connect to
        raise_for_status (bool): Whether to call `raise_for_status
            <http://docs.python-requests.org/en/master/api/#requests.Response.raise_for_status>`_
            method automatically or not. For quick reference, raise_for_status will consider an
            error if the return code is any of 4xx or 5xx
        **kwargs: Keyword arguments will be passed to the `request
            <http://docs.python-requests.org/en/master/api/#requests.request>`_
            method

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``string/dict``): Body of the response. Either text or a dict if the
            response was a json object
          * reponse (object): Original `Response
            <http://docs.python-requests.org/en/master/api/#requests.Response>`_
    """
    r = requests.request(method, url, **kwargs)

    if raise_for_status:
        r.raise_for_status()

    try:
        content_type = r.headers["Content-type"]
    except KeyError:
        content_type = "text"

    result = r.json() if "application/json" == content_type else r.text

    return Result(host=task.host if task else None, response=r, result=result)
