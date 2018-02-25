import importlib

from brigade.core.brigade import Brigade
from brigade.core.configuration import Config


def from_conf(config_file="", dry_run=False, **kwargs):
    """
    Arguments:
        config_file(str): Path to the configuration file (optional)
        dry_run(bool): Whether to simulate changes or not
        **kwargs: Extra information to pass to the
            :obj:`brigade.core.configuration.Config` object

    Returns:
        :obj:`brigade.core.Brigade`: fully instantiated and configured
    """
    conf = Config(config_file=config_file, **kwargs)

    module_path = ".".join(conf.inventory.split(".")[:-1])
    inv_class_name = conf.inventory.split(".")[-1]
    module = importlib.import_module(module_path)
    inv_class = getattr(module, inv_class_name)

    inv = inv_class(**getattr(conf, inv_class_name, {}))

    return Brigade(
        inventory=inv,
        dry_run=dry_run,
        config=conf,
    )
