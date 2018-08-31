from typing import Any, Dict, List, Optional

from nornir.core.inventory import ElementData, Group, Host, Inventory

from pydantic import BaseModel


class CommonAttributes(BaseModel):
    hostname: Optional[str] = None
    port: Optional[int]
    username: Optional[str] = None
    password: Optional[str] = None
    platform: Optional[str] = None
    data: Dict[str, Any] = {}

    class Config:
        ignore_extra = False

    @staticmethod
    def serialize(e: ElementData) -> "CommonAttributes":
        return CommonAttributes(
            hostname=e.hostname,
            port=e.port,
            username=e.username,
            password=e.password,
            platform=e.platform,
            data=e.data,
        )


class InventoryElement(CommonAttributes):
    groups: List[str] = []


class HostSerializer(InventoryElement):
    @staticmethod
    def serialize(h: Host) -> "HostSerializer":
        return HostSerializer(
            hostname=object.__getattribute__(h, "hostname"),
            port=object.__getattribute__(h, "port"),
            username=object.__getattribute__(h, "username"),
            password=object.__getattribute__(h, "password"),
            platform=object.__getattribute__(h, "platform"),
            groups=[c.name for c in h.groups],
            data=object.__getattribute__(h, "data"),
        )


class GroupSerializer(InventoryElement):
    def serialize(g: Group) -> "GroupSerializer":
        return GroupSerializer(
            hostname=object.__getattribute__(g, "hostname"),
            port=object.__getattribute__(g, "port"),
            username=object.__getattribute__(g, "username"),
            password=object.__getattribute__(g, "password"),
            platform=object.__getattribute__(g, "platform"),
            groups=[c.name for c in g.groups],
            data=object.__getattribute__(g, "data"),
        )


class InventorySerializer(BaseModel):
    hosts: Dict[str, HostSerializer]
    groups: Dict[str, GroupSerializer] = GroupSerializer()
    defaults: CommonAttributes = CommonAttributes()

    class Config:
        ignore_extra = False

    @staticmethod
    def deserialize(i: Dict[str, Any]) -> Inventory:
        serialized = InventorySerializer(**i)
        defaults = ElementData(**serialized.defaults.dict())

        hosts = {}
        for n, h in serialized.hosts.items():
            hosts[n] = Host(name=n, **h.dict())
        groups = {}
        for n, g in serialized.groups.items():
            groups[n] = Group(name=n, **g.dict())

        for h in hosts.values():
            h.defaults = defaults
            h.groups = [groups[n] for n in h.groups]
        for g in groups.values():
            g.defaults = defaults
            g.groups = [groups[n] for n in g.groups]
        return Inventory(hosts, groups, defaults)

    @staticmethod
    def serialize(i: Inventory) -> "InventorySerializer":
        hosts = {n: HostSerializer.serialize(h) for n, h in i.hosts.items()}
        groups = {n: GroupSerializer.serialize(g) for n, g in i.groups.items()}
        defaults = CommonAttributes.serialize(i.defaults)
        return InventorySerializer(hosts=hosts, groups=groups, defaults=defaults)
