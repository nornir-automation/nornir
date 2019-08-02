import warnings
from typing import Any, Callable, Dict, Optional

from nornir.core import Nornir
from nornir.core.connections import Connections
from nornir.core.deserializer.configuration import Config
from nornir.core.state import GlobalState
from nornir.plugins.connections.napalm import Napalm
from nornir.plugins.connections.netconf import Netconf
from nornir.plugins.connections.netmiko import Netmiko
from nornir.plugins.connections.paramiko import Paramiko


def register_default_connection_plugins() -> None:
    Connections.register("napalm", Napalm)
    Connections.register("netconf", Netconf)
    Connections.register("netmiko", Netmiko)
    Connections.register("paramiko", Paramiko)


def cls_to_string(cls: Callable[..., Any]) -> str:
    return f"{cls.__module__}.{cls.__name__}"


def InitNornir(
    config_file: str = "",
    dry_run: bool = False,
    configure_logging: Optional[bool] = None,
    **kwargs: Dict[str, Any],
) -> Nornir:
    """
    Arguments:
        config_file(str): Path to the configuration file (optional)
        dry_run(bool): Whether to simulate changes or not
        configure_logging: Whether to configure logging or not. This argument is being
            deprecated. Please use logging.enabled parameter in the configuration
            instead.
        **kwargs: Extra information to pass to the
            :obj:`nornir.core.configuration.Config` object

    Returns:
        :obj:`nornir.core.Nornir`: fully instantiated and configured
    """
    register_default_connection_plugins()

    if callable(kwargs.get("inventory", {}).get("plugin", "")):
        kwargs["inventory"]["plugin"] = cls_to_string(kwargs["inventory"]["plugin"])

    if callable(kwargs.get("inventory", {}).get("transform_function", "")):
        kwargs["inventory"]["transform_function"] = cls_to_string(
            kwargs["inventory"]["transform_function"]
        )

    conf = Config.load_from_file(config_file, **kwargs)

    data = GlobalState(dry_run=dry_run)

    if configure_logging is not None:
        msg = (
            "'configure_logging' argument is deprecated, please use "
            "'logging.enabled' parameter in the configuration instead: "
            "https://nornir.readthedocs.io/en/stable/configuration/index.html"
        )
        warnings.warn(msg, DeprecationWarning)

    if conf.logging.enabled is None:
        if configure_logging is not None:
            conf.logging.enabled = configure_logging
        else:
            conf.logging.enabled = True

    conf.logging.configure()

    inv = conf.inventory.plugin.deserialize(
        transform_function=conf.inventory.transform_function,
        transform_function_options=conf.inventory.transform_function_options,
        config=conf,
        **conf.inventory.options,
    )

    return Nornir(inventory=inv, config=conf, data=data)
