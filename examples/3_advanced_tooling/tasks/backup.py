#!/usr/bin/env python
"""
This is a simple example where we use click and brigade to build a simple CLI tool to retrieve
hosts information.

The main difference with get_facts_simple.py is that instead of calling a plugin directly
we wrap it in a function. It is not very useful or necessary here but illustrates how
tasks can be grouped.
"""
from brigade.plugins import functions
from brigade.plugins.tasks import files, networking, text

import click


def backup_task(task, path):
    result = task.run(networking.napalm_get,
                      getters="config")

    return task.run(files.write,
                    content=result.result["config"]["running"],
                    filename="{}/{}".format(path, task.host))


@click.command()
@click.option('--backup-path', default=".")
@click.pass_context
def backup(ctx, backup_path, **kwargs):
    functions.text.print_title("Backing up configurations")
    filtered = ctx.obj["filtered"]
    results = filtered.run(backup_task,
                           path=backup_path)

    # Let's print the result on screen
    return filtered.run(text.print_result,
                        num_workers=1,
                        data=results)
