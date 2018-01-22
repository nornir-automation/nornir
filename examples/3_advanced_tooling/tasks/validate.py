#!/usr/bin/env python
"""
In this example we write a CLI tool with brigade and click to deploy configuration.
"""
from brigade.plugins import functions
from brigade.plugins.tasks import data, networking, text

import click


def validate_task(task):
    task.host["config"] = ""

    r = task.run(name="read data",
                 task=data.load_yaml,
                 file="../extra_data/{host}/l3.yaml")

    validation_rules = [{
        'get_bgp_neighbors': {
            'global': {
                'peers': {
                    '_mode': 'strict',
                }
            }
        }
    }]
    peers = validation_rules[0]['get_bgp_neighbors']['global']['peers']
    for session in r.result['sessions']:
        peers[session['ipv4']] = {'is_up': True}

    return task.run(name="validating data",
                    task=networking.napalm_validate,
                    validation_source=validation_rules)


@click.command()
@click.pass_context
def validate(ctx, **kwargs):
    functions.text.print_title("Make sure BGP sessions are UP")
    filtered = ctx.obj["filtered"]

    results = filtered.run(task=validate_task)

    filtered.run(name="print validate result",
                 num_workers=1,
                 task=text.print_result,
                 data=results)

    return results
