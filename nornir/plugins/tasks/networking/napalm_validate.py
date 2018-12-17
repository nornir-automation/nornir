from typing import Any, Dict, Optional

from nornir.core.task import Result, Task

ValidationSourceData = Optional[Dict[str, Dict[str, Any]]]


def napalm_validate(
    task: Task,
    src: Optional[str] = None,
    validation_source: ValidationSourceData = None,
) -> Result:
    """
    Gather information with napalm and validate it:

        http://napalm.readthedocs.io/en/develop/validate/index.html

    Arguments:
        src: file to use as validation source
        validation_source (list): data to validate device's state

    Returns:
        Result object with the following attributes set:
        * result (``dict``): dictionary with the result of the validation
        * complies (``bool``): Whether the device complies or not
    """
    device = task.host.get_connection("napalm", task.nornir.config)
    r = device.compliance_report(
        validation_file=src, validation_source=validation_source
    )
    return Result(host=task.host, result=r)
