#!/usr/bin/env python
"""
In this example we write a CLI tool with brigade and click to deploy configuration.
"""
import time

from brigade.plugins import functions
from brigade.plugins.tasks import data, networking, text

import click

from . import backup as backup_
from . import validate as validate_


def configure_task(task):
    r = task.run(text.template_file,
                 template="base.j2",
                 path="../templates/{brigade_nos}")
    task.host["config"] = r.result

    r = task.run(data.load_yaml,
                 file="../extra_data/{host}/l3.yaml")
    task.host["l3"] = r.result

    r = task.run(text.template_file,
                 template="interfaces.j2",
                 path="../templates/{brigade_nos}")
    task.host["config"] += r.result

    r = task.run(text.template_file,
                 template="routing.j2",
                 path="../templates/{brigade_nos}")
    task.host["config"] += r.result

    r = task.run(text.template_file,
                 template="{role}.j2",
                 path="../templates/{brigade_nos}")
    task.host["config"] += r.result

    return task.run(networking.napalm_configure,
                    replace=False,
                    configuration=task.host["config"])


@click.command()
@click.option("--validate/--no-validate", default=False)
@click.option("--rollback/--no-rollback", default=False)
@click.option("--backup/--no-backup", default=False)
@click.option('--backup-path', default=".")
@click.pass_context
def configure(ctx, validate, backup, backup_path, rollback):
    filtered = ctx.obj["filtered"]

    if backup:
        backup_.backup.invoke(ctx)

    functions.text.print_title("Configure Network")
    results = filtered.run(task=configure_task)

    filtered.run(text.print_result,
                 num_workers=1,  # we are printing on screen so we want to do this synchronously
                 data=results)

    if validate:
        time.sleep(10)
        r = validate_.validate.invoke(ctx)

        if r.failed and rollback:
            functions.text.print_title("Rolling back configuration!!!")
            r = filtered.run(networking.napalm_configure,
                             replace=True,
                             filename=backup_path + "/{host}")
            filtered.run(text.print_result,
                         num_workers=1,
                         data=r)
    import pdb; pdb.set_trace()  # noqa
