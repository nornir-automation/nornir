from nornir.core.task import Result


def napalm_validate(task, src=None, validation_source=None):
    """
    Gather information with napalm and validate it:

        http://napalm.readthedocs.io/en/develop/validate/index.html

    Arguments:
        src: file to use as validation source
        validation_source (list): instead of a file data needed to validate device's state

    Returns:
      :obj:`nornir.core.task.Result`:
        * result (``dict``): dictionary with the result of the validation
        * complies (``bool``): Whether the device complies or not
    """
    device = task.host.get_connection("napalm")
    r = device.compliance_report(
        validation_file=src, validation_source=validation_source
    )
    return Result(host=task.host, result=r)
