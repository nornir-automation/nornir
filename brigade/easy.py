from brigade.core import Brigade
from brigade.core.configuration import Config
from brigade.plugins.inventory.simple import SimpleInventory


def easy_brigade(host_file="host.yaml", group_file="groups.yaml", dry_run=False, **kwargs):
    """
    Helper function to create easily a :obj:`brigade.core.Brigade` object.

    Arguments:
        host_file (str): path to the host file that will be passed to
            :obj:`brigade.plugins.inventory.simple.SimpleInventory`
        group_file (str): path to the group file that will be passed to
            :obj:`brigade.plugins.inventory.simple.SimpleInventory`
        dry_run (bool): whether if this is a dry run or not
        **kwargs: Configuration parameters, see
            :doc:`configuration parameters </ref/configuration/index>`
    """
    return Brigade(
        inventory=SimpleInventory(host_file, group_file),
        dry_run=dry_run,
        config=Config(**kwargs),
    )
