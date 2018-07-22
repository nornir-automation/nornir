from typing import Dict, TYPE_CHECKING, Type


from .napalm import Napalm
from .netmiko import Netmiko
from .paramiko import Paramiko

if TYPE_CHECKING:
    from nornir.core.connections import ConnectionPlugin  # noqa


available_connections: Dict[str, Type["ConnectionPlugin"]] = {
    "napalm": Napalm,
    "netmiko": Netmiko,
    "paramiko": Paramiko,
}
