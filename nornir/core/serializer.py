from typing import Any, Dict, List, Optional

from nornir.core.inventory import ElementData, Group, Groups, Host, Inventory

from pydantic import BaseModel


class BaseAttributes(BaseModel):
    hostname: Optional[str] = None
    port: Optional[int]
    username: Optional[str] = None
    password: Optional[str] = None
    platform: Optional[str] = None

    class Config:
        ignore_extra = False


class ConnectionOptions(BaseAttributes):
    extras: Dict[str, Any] = {}


class CommonAttributes(BaseAttributes):
    data: Dict[str, Any] = {}
    connection_options: Dict[str, ConnectionOptions] = {}

    @staticmethod
    def serialize(e: ElementData) -> "CommonAttributes":
        return CommonAttributes(
            hostname=e.hostname,
            port=e.port,
            username=e.username,
            password=e.password,
            platform=e.platform,
            data=e.data,
            connection_options=e.connection_options,
        )


class InventoryElement(CommonAttributes):
    groups: List[str] = []


class HostSerializer(InventoryElement):
    @staticmethod
    def serialize(h: Host) -> "HostSerializer":
        return HostSerializer(
            hostname=h.__values__["hostname"],
            port=h.__values__["port"],
            username=h.__values__["username"],
            password=h.__values__["password"],
            platform=h.__values__["platform"],
            groups=[c.name for c in h.groups],
            data=h.__values__["data"],
            connection_options=h.__values__["connection_options"],
        )


class GroupSerializer(InventoryElement):
    def serialize(g: Group) -> "GroupSerializer":
        return GroupSerializer(
            hostname=g.__values__["hostname"],
            port=g.__values__["port"],
            username=g.__values__["username"],
            password=g.__values__["password"],
            platform=g.__values__["platform"],
            groups=[c.name for c in g.groups],
            data=g.__values__["data"],
            connection_options=g.__values__["connection_options"],
        )


class InventorySerializer(BaseModel):
    hosts: Dict[str, HostSerializer]
    groups: Dict[str, GroupSerializer] = GroupSerializer()
    defaults: CommonAttributes = CommonAttributes()

    class Config:
        ignore_extra = False

    @staticmethod
    def deserialize(i: Dict[str, Any], *args, **kwargs) -> Inventory:
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
            h.groups = Groups([groups[n] for n in h.groups])
        for g in groups.values():
            g.defaults = defaults
            g.groups = Groups([groups[n] for n in g.groups])
        return Inventory(hosts, groups, defaults, *args, **kwargs)

    @staticmethod
    def serialize(i: Inventory) -> "InventorySerializer":
        hosts = {n: HostSerializer.serialize(h) for n, h in i.hosts.items()}
        groups = {n: GroupSerializer.serialize(g) for n, g in i.groups.items()}
        defaults = CommonAttributes.serialize(i.defaults)
        return InventorySerializer(hosts=hosts, groups=groups, defaults=defaults)
