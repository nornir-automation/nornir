from typing import Any, Callable, Dict, List, Optional, Union

from nornir.core import inventory

from nornir._vendor.pydantic import BaseModel


VarsDict = Dict[str, Any]
HostsDict = Dict[str, VarsDict]
GroupsDict = Dict[str, VarsDict]
DefaultsDict = VarsDict


class BaseAttributes(BaseModel):
    hostname: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    platform: Optional[str] = None

    class Config:
        ignore_extra = False


class ConnectionOptions(BaseAttributes):
    extras: Optional[Dict[str, Any]]

    @classmethod
    def serialize(cls, i: inventory.ConnectionOptions) -> "ConnectionOptions":
        return ConnectionOptions(
            hostname=i.hostname,
            port=i.port,
            username=i.username,
            password=i.password,
            platform=i.platform,
            extras=i.extras,
        )


class InventoryElement(BaseAttributes):
    groups: List[str] = []
    data: Dict[str, Any] = {}
    connection_options: Dict[str, ConnectionOptions] = {}

    @classmethod
    def deserialize(
        cls,
        name: str,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        platform: Optional[str] = None,
        groups: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
        connection_options: Optional[Dict[str, Dict[str, Any]]] = None,
        defaults: inventory.Defaults = None,
    ) -> Dict[str, Any]:
        parent_groups = inventory.ParentGroups(groups)
        connection_options = connection_options or {}
        conn_opts = {
            k: inventory.ConnectionOptions(**v) for k, v in connection_options.items()
        }
        return {
            "name": name,
            "hostname": hostname,
            "port": port,
            "username": username,
            "password": password,
            "platform": platform,
            "groups": parent_groups,
            "data": data,
            "connection_options": conn_opts,
            "defaults": defaults,
        }

    @classmethod
    def deserialize_host(cls, **kwargs: Any) -> inventory.Host:
        return inventory.Host(**cls.deserialize(**kwargs))

    @classmethod
    def deserialize_group(cls, **kwargs: Any) -> inventory.Group:
        return inventory.Group(**cls.deserialize(**kwargs))

    @classmethod
    def serialize(cls, e: Union[inventory.Host, inventory.Group]) -> "InventoryElement":
        d = {}
        for f in cls.__fields__:
            d[f] = object.__getattribute__(e, f)
        d["groups"] = list(d["groups"])
        d["connection_options"] = {
            k: ConnectionOptions.serialize(v)
            for k, v in d["connection_options"].items()
        }
        return InventoryElement(**d)


class Defaults(BaseAttributes):
    data: Dict[str, Any] = {}
    connection_options: Dict[str, ConnectionOptions] = {}

    @classmethod
    def serialize(cls, defaults: inventory.Defaults) -> "Defaults":
        d = {}
        for f in cls.__fields__:
            d[f] = getattr(defaults, f)

        d["connection_options"] = {
            k: ConnectionOptions.serialize(v)
            for k, v in d["connection_options"].items()
        }
        return Defaults(**d)


class Inventory(BaseModel):
    hosts: Dict[str, InventoryElement]
    groups: Dict[str, InventoryElement]
    defaults: Defaults

    @classmethod
    def deserialize(
        cls,
        transform_function: Optional[Callable[..., Any]] = None,
        transform_function_options: Optional[Dict[str, Any]] = None,
        *args: Any,
        **kwargs: Any
    ) -> inventory.Inventory:
        transform_function_options = transform_function_options or {}
        deserialized = cls(*args, **kwargs)

        defaults_dict = deserialized.defaults.dict()
        for k, v in defaults_dict["connection_options"].items():
            defaults_dict["connection_options"][k] = inventory.ConnectionOptions(**v)
        defaults = inventory.Defaults(**defaults_dict)

        hosts = inventory.Hosts()
        for n, h in deserialized.hosts.items():
            hosts[n] = InventoryElement.deserialize_host(
                defaults=defaults, name=n, **h.dict()
            )

        groups = inventory.Groups()
        for n, g in deserialized.groups.items():
            groups[n] = InventoryElement.deserialize_group(name=n, **g.dict())

        return inventory.Inventory(
            hosts=hosts,
            groups=groups,
            defaults=defaults,
            transform_function=transform_function,
            transform_function_options=transform_function_options,
        )

    @classmethod
    def serialize(cls, inv: inventory.Inventory) -> "Inventory":
        hosts = {}
        for n, h in inv.hosts.items():
            hosts[n] = InventoryElement.serialize(h)
        groups = {}
        for n, g in inv.groups.items():
            groups[n] = InventoryElement.serialize(g)
        defaults = Defaults.serialize(inv.defaults)
        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
