from typing import Any, Dict, List, Optional, Union

from nornir.core import inventory

from pydantic import BaseModel

GroupsDict = None  # DELETEME
HostsDict = None  # DELETEME
VarsDict = None  # DELETEME


class BaseAttributes(BaseModel):
    hostname: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    platform: Optional[str] = None

    class Config:
        ignore_extra = False


class ConnectionOptions(BaseAttributes):
    extras: Dict[str, Any] = {}


class InventoryElement(BaseAttributes):
    groups: List[str] = []
    data: Dict[str, Any] = {}
    connection_options: Dict[str, ConnectionOptions] = {}

    @classmethod
    def serialize(cls, e: Union[inventory.Host, inventory.Group]) -> "InventoryElement":
        d = {}
        for f in cls.__fields__:
            d[f] = object.__getattribute__(e, f)
        d["groups"] = list(d["groups"])
        return InventoryElement(**d)


class Defaults(BaseAttributes):
    data: Dict[str, Any] = {}
    connection_options: Dict[str, ConnectionOptions] = {}

    @classmethod
    def serialize(cls, defaults: inventory.Defaults) -> "InventoryElement":
        d = {}
        for f in cls.__fields__:
            d[f] = getattr(defaults, f)
        return Defaults(**d)


class Inventory(BaseModel):
    hosts: Dict[str, InventoryElement]
    groups: Dict[str, InventoryElement] = {}
    defaults: Defaults = {}

    @classmethod
    def deserialize(cls, transform_function=None, *args, **kwargs):
        deserialized = cls(*args, **kwargs)

        defaults = inventory.Defaults(**deserialized.defaults.dict())

        hosts = inventory.Hosts()
        for n, h in deserialized.hosts.items():
            h.groups = inventory.ParentGroups(h.groups)
            hosts[n] = inventory.Host(defaults=defaults, name=n, **h.dict())

        groups = inventory.Groups()
        for n, g in deserialized.groups.items():
            g.groups = inventory.ParentGroups(g.groups)
            groups[n] = inventory.Group(defaults=defaults, name=n, **g.dict())

        return inventory.Inventory(
            hosts=hosts,
            groups=groups,
            defaults=defaults,
            transform_function=transform_function,
        )

    @classmethod
    def serialize(cls, inv: inventory.Inventory):
        hosts = {}
        for n, h in inv.hosts.items():
            hosts[n] = InventoryElement.serialize(h)
        groups = {}
        for n, g in inv.groups.items():
            groups[n] = InventoryElement.serialize(g)
        defaults = Defaults.serialize(inv.defaults)
        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
