from typing import List, Optional

from nornir.core.task import Result, Task

from ntc_rosetta import get_driver


def ntc_rosetta_parse_config(
    task: Task,
    config: Optional[str] = None,
    model: str = "openconfig",
    target: str = "running",
    validate: bool = True,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Result:
    """
    The task ``ntc_rosetta_parse_config`` parses native configuration using
    `ntc_rosetta <https://ntc-rosetta.readthedocs.io/>`_

    The user can specify the configuration to parse by passing the ``config`` parameter. If not
    specified, the task will use napalm to retrieve it.

    For parameters that belong to ``ntc_rosetta`` refer to the following link:

        https://ntc-rosetta.readthedocs.io/en/latest/api/drivers.html#ntc_rosetta.drivers.base.Driver.parse

    Arguments:
        config: Config to parse. If not spcified retrieve with napalm
        model: Refer to https://ntc-rosetta.readthedocs.io/en/latest/models/matrix/index.html
        target: Target database to retrieve, i.e., "candidate" or "running".
        validate: Refer to ``ntc_rosetta`` documentaiton
        include: Refer to ``ntc_rosetta`` documentaiton
        exclude: Refer to ``ntc_rosetta`` documentaiton

    Returns:
        Result:
            * result: The ``ntc_rosetta.drivers.ParseResults`` object that ``ntc_rosetta`` returns.
    """
    if target not in ["candidate", "running"]:
        raise ValueError(
            f"target '{target}' not supported. Only 'running', and 'candidate' are."
        )

    if config is None:
        device = task.host.get_connection("napalm", task.nornir.config)
        config = device.get_config(retrieve=target)[target]

    rosetta_driver = get_driver(task.host.platform, model)
    rosetta_instance = rosetta_driver()

    parsed = rosetta_instance.parse(
        native={"dev_conf": config}, include=include, exclude=exclude, validate=validate
    )

    return Result(host=task.host, result=parsed)
