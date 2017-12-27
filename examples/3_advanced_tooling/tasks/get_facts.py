from brigade.plugins.tasks import networking, text

import click


@click.command()
@click.option('--get', '-g', multiple=True,
              help="getters you want to use")
@click.pass_context
def get(ctx, get):
    """
    Retrieve information from network devices using napalm
    """
    filtered = ctx.obj["filtered"]
    results = filtered.run(networking.napalm_get,
                           getters=get)

    # Let's print the result on screen
    filtered.run(text.print_result,
                 num_workers=1,  # we are printing on screen so we want to do this synchronously
                 data=results)
