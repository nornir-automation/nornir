#!/usr/bin/env python
"""
Runbook that verifies that BGP sessions are configured and up.
"""
from brigade.easy import easy_brigade
from brigade.plugins.tasks import data, networking, text


def validate(task):
    task.host["config"] = ""

    r = task.run(
        name="read data", task=data.load_yaml, file="../extra_data/{host}/l3.yaml"
    )

    validation_rules = [
        {"get_bgp_neighbors": {"global": {"peers": {"_mode": "strict"}}}}
    ]
    peers = validation_rules[0]["get_bgp_neighbors"]["global"]["peers"]
    for session in r.result["sessions"]:
        peers[session["ipv4"]] = {"is_up": True}

    task.run(
        name="validating data",
        task=networking.napalm_validate,
        validation_source=validation_rules,
    )


def print_compliance(task, results):
    """
    We use this task so we can access directly the result
    for each specific host and see if the task complies or not
    and pass it to print_result.
    """
    task.run(
        text.print_result,
        name="print result",
        data=results[task.host.name],
        failed=not results[task.host.name][2].result["complies"],
    )


brg = easy_brigade(
    host_file="../inventory/hosts.yaml",
    group_file="../inventory/groups.yaml",
    dry_run=False,
    raise_on_error=True,
)


filtered = brg.filter(type="network_device", site="cmh")

results = filtered.run(task=validate)

filtered.run(print_compliance, results=results, num_workers=1)
