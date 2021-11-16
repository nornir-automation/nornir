from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Union,
    KeysView,
    ValuesView,
    ItemsView,
    Iterator,
    TypeVar,
)

from nornir.core.configuration import Config
from nornir.core.plugins.connections import (
    ConnectionPlugin,
    ConnectionPluginRegister,
)
from nornir.core.exceptions import ConnectionAlreadyOpen, ConnectionNotOpen

from mypy_extensions import Arg, KwArg


HostOrGroup = TypeVar("HostOrGroup", "Host", "Group")


class BaseAttributes(object):
    __slots__ = ("hostname", "port", "username", "password", "platform")

    def __init__(
        self,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> None:
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.platform = platform

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "hostname": "str",
            "port": "int",
            "username": "str",
            "password": "str",
            "platform": "str",
        }

    def dict(self) -> Dict[str, Any]:
        return {
            "hostname": object.__getattribute__(self, "hostname"),
            "port": object.__getattribute__(self, "port"),
            "username": object.__getattribute__(self, "username"),
            "password": object.__getattribute__(self, "password"),
            "platform": object.__getattribute__(self, "platform"),
        }


class ConnectionOptions(BaseAttributes):
    __slots__ = ("extras",)

    def __init__(
        self,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        platform: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.extras = extras
        super().__init__(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            platform=platform,
        )

    @classmethod
    def schema(self) -> Dict[str, Any]:
        return {
            "extras": {"$key": "$value"},
            **super().schema(),
        }

    def dict(self) -> Dict[str, Any]:
        return {
            "extras": self.extras,
            **super().dict(),
        }


class ParentGroups(List["Group"]):
    def __contains__(self, value: object) -> bool:
        if isinstance(value, str):
            return any([value == g.name for g in self])
        else:
            return any([value == g for g in self])

    def add(self, group: "Group") -> None:
        """
        Add the ParentGroup.  The group will only be appended
        if it does not exist.

        :param group: Parent Group object to add
        :return: None
        """
        # only add the group if it doesn't exist
        if not self.__contains__(group):
            self.append(group)


class InventoryElement(BaseAttributes):
    __slots__ = ("groups", "data", "connection_options")

    def __init__(
        self,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        platform: Optional[str] = None,
        groups: Optional[ParentGroups] = None,
        data: Optional[Dict[str, Any]] = None,
        connection_options: Optional[Dict[str, ConnectionOptions]] = None,
    ) -> None:
        self.groups = groups or ParentGroups()
        self.data = data or {}
        self.connection_options = connection_options or {}
        super().__init__(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            platform=platform,
        )

    @classmethod
    def schema(self) -> Dict[str, Any]:
        return {
            "groups": ["$group_name"],
            "data": {"$key": "$value"},
            "connection_options": {"$connection_type": ConnectionOptions.schema()},
            **super().schema(),
        }

    def dict(self) -> Dict[str, Any]:
        return {
            "groups": [g.name for g in self.groups],
            "data": self.data,
            "connection_options": {
                k: v.dict() for k, v in self.connection_options.items()
            },
            **super().dict(),
        }

    def extended_groups(self) -> List["Group"]:
        """
        Returns the groups this host belongs to by virtue of inheritance.

        This list is ordered based on the inheritance rules and groups are not
        duplicated. For instance, given a host with the following groups:

        hostA:
            groups:
                - group_a
                - group_b

        group_a:
            groups:
                - group_1
                - group_2
        group_b:
            groups:
                - group_2
                - group_3

        group_1:
            groups:
                - group_X

        this will return [group_a, group_1, group_X, group_2, group_b, group_3]
        """
        groups: List["Group"] = []

        for g in self.groups:
            if g not in groups:
                groups.append(g)

            for sg in g.extended_groups():
                if sg not in groups:
                    groups.append(sg)

        return groups


class Defaults(BaseAttributes):
    __slots__ = ("data", "connection_options")

    def __init__(
        self,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        platform: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        connection_options: Optional[Dict[str, ConnectionOptions]] = None,
    ) -> None:
        self.data = data or {}
        self.connection_options = connection_options or {}
        super().__init__(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            platform=platform,
        )

    @classmethod
    def schema(self) -> Dict[str, Any]:
        return {
            "data": {"$key": "$value"},
            "connection_options": {"$connection_type": ConnectionOptions.schema()},
            **super().schema(),
        }

    def dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "connection_options": {
                k: v.dict() for k, v in self.connection_options.items()
            },
            **super().dict(),
        }


class Host(InventoryElement):
    __slots__ = ("name", "connections", "defaults")

    def __init__(
        self,
        name: str,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        platform: Optional[str] = None,
        groups: Optional[ParentGroups] = None,
        data: Optional[Dict[str, Any]] = None,
        connection_options: Optional[Dict[str, ConnectionOptions]] = None,
        defaults: Optional[Defaults] = None,
    ) -> None:
        self.name = name
        self.defaults = defaults or Defaults(None, None, None, None, None, None, None)
        self.connections: Dict[str, ConnectionPlugin] = {}
        super().__init__(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            platform=platform,
            groups=groups,
            data=data,
            connection_options=connection_options,
        )

    def extended_data(self) -> Dict[str, Any]:
        """
        Returns the data associated with the object including inherited data
        """
        processed = []
        result = {}
        for k, v in self.data.items():
            processed.append(k)
            result[k] = v
        for g in self.extended_groups():
            for k, v in g.data.items():
                if k not in processed:
                    processed.append(k)
                    result[k] = v
        for k, v in self.defaults.data.items():
            if k not in processed:
                processed.append(k)
                result[k] = v
        return result

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "name": "str",
            "connection_options": {"$connection_type": ConnectionOptions.schema()},
            **super().schema(),
        }

    def dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "connection_options": {
                k: v.dict() for k, v in self.connection_options.items()
            },
            **super().dict(),
        }

    def keys(self) -> KeysView[str]:
        """Returns the keys of the attribute ``data`` and of the parent(s) groups."""
        return self.extended_data().keys()

    def values(self) -> ValuesView[Any]:
        """Returns the values of the attribute ``data`` and of the parent(s) groups."""
        return self.extended_data().values()

    def items(self) -> ItemsView[str, Any]:
        """
        Returns all the data accessible from a device, including
        the one inherited from parent groups
        """
        return self.extended_data().items()

    def has_parent_group(self, group: Union[str, "Group"]) -> bool:
        """Returns whether the object is a child of the :obj:`Group` ``group``"""
        if isinstance(group, str):
            return self._has_parent_group_by_name(group)

        else:
            return self._has_parent_group_by_object(group)

    def _has_parent_group_by_name(self, group: str) -> bool:
        for g in self.groups:
            if g.name == group or g.has_parent_group(group):
                return True
        return False

    def _has_parent_group_by_object(self, group: "Group") -> bool:
        for g in self.groups:
            if g is group or g.has_parent_group(group):
                return True
        return False

    def __getitem__(self, item: str) -> Any:
        try:
            return self.data[item]

        except KeyError:
            for g in self.extended_groups():
                try:
                    r = g.data[item]
                    return r
                except KeyError:
                    continue

            r = self.defaults.data.get(item)
            if r is not None:
                return r

            raise

    def __getattribute__(self, name: str) -> Any:
        if name not in ("hostname", "port", "username", "password", "platform"):
            return object.__getattribute__(self, name)
        v = object.__getattribute__(self, name)
        if v is None:
            for g in self.extended_groups():
                r = object.__getattribute__(g, name)
                if r is not None:
                    return r

            return object.__getattribute__(self.defaults, name)
        else:
            return v

    def __bool__(self) -> bool:
        return bool(self.name)

    def __setitem__(self, item: str, value: Any) -> None:
        self.data[item] = value

    def __len__(self) -> int:
        return len(self.extended_data().keys())

    def __iter__(self) -> Iterator[str]:
        return self.extended_data().__iter__()

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "{}: {}".format(self.__class__.__name__, self.name or "")

    def get(self, item: str, default: Any = None) -> Any:
        """
        Returns the value ``item`` from the host or hosts group variables.

        Arguments:
            item(``str``): The variable to get
            default(``any``): Return value if item not found
        """
        if hasattr(self, item):
            return getattr(self, item)
        try:
            return self.__getitem__(item)

        except KeyError:
            return default

    def get_connection_parameters(
        self, connection: Optional[str] = None
    ) -> ConnectionOptions:
        if not connection:
            d = ConnectionOptions(
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                platform=self.platform,
                extras={},
            )
        else:
            r = self._get_connection_options_recursively(connection)
            if r is not None:
                d = ConnectionOptions(
                    hostname=r.hostname if r.hostname is not None else self.hostname,
                    port=r.port if r.port is not None else self.port,
                    username=r.username if r.username is not None else self.username,
                    password=r.password if r.password is not None else self.password,
                    platform=r.platform if r.platform is not None else self.platform,
                    extras=r.extras if r.extras is not None else {},
                )
            else:
                d = ConnectionOptions(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    platform=self.platform,
                    extras={},
                )
        return d

    def _get_connection_options_recursively(
        self, connection: str
    ) -> Optional[ConnectionOptions]:
        p = self.connection_options.get(connection)
        if p is None:
            p = ConnectionOptions(None, None, None, None, None, None)

        for g in self.groups:
            sp = g._get_connection_options_recursively(connection)
            if sp is not None:
                p.hostname = p.hostname if p.hostname is not None else sp.hostname
                p.port = p.port if p.port is not None else sp.port
                p.username = p.username if p.username is not None else sp.username
                p.password = p.password if p.password is not None else sp.password
                p.platform = p.platform if p.platform is not None else sp.platform
                p.extras = p.extras if p.extras is not None else sp.extras

        sp = self.defaults.connection_options.get(connection, None)
        if sp is not None:
            p.hostname = p.hostname if p.hostname is not None else sp.hostname
            p.port = p.port if p.port is not None else sp.port
            p.username = p.username if p.username is not None else sp.username
            p.password = p.password if p.password is not None else sp.password
            p.platform = p.platform if p.platform is not None else sp.platform
            p.extras = p.extras if p.extras is not None else sp.extras
        return p

    def get_connection(self, connection: str, configuration: Config) -> Any:
        """
        The function of this method is twofold:

            1. If an existing connection is already established for the given type return it
            2. If none exists, establish a new connection of that type with default parameters
               and return it

        Raises:
            AttributeError: if it's unknown how to establish a connection for the given type

        Arguments:
            connection: Name of the connection, for instance, netmiko, paramiko, napalm...

        Returns:
            An already established connection
        """
        if connection not in self.connections:
            conn = self.get_connection_parameters(connection)
            self.open_connection(
                connection=connection,
                configuration=configuration,
                hostname=conn.hostname,
                port=conn.port,
                username=conn.username,
                password=conn.password,
                platform=conn.platform,
                extras=conn.extras,
            )
        return self.connections[connection].connection

    def open_connection(
        self,
        connection: str,
        configuration: Config,
        hostname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        port: Optional[int] = None,
        platform: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
        default_to_host_attributes: bool = True,
    ) -> ConnectionPlugin:
        """
        Open a new connection.

        If ``default_to_host_attributes`` is set to ``True`` arguments will default to host
        attributes if not specified.

        Raises:
            AttributeError: if it's unknown how to establish a connection for the given type

        Returns:
            An already established connection
        """
        conn_name = connection
        existing_conn = self.connections.get(conn_name)
        if existing_conn is not None:
            raise ConnectionAlreadyOpen(conn_name)

        plugin = ConnectionPluginRegister.get_plugin(conn_name)
        conn_obj = plugin()
        if default_to_host_attributes:
            conn_params = self.get_connection_parameters(conn_name)
            hostname = hostname if hostname is not None else conn_params.hostname
            username = username if username is not None else conn_params.username
            password = password if password is not None else conn_params.password
            port = port if port is not None else conn_params.port
            platform = platform if platform is not None else conn_params.platform
            extras = extras if extras is not None else conn_params.extras

        conn_obj.open(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            platform=platform,
            extras=extras,
            configuration=configuration,
        )
        self.connections[conn_name] = conn_obj
        return conn_obj

    def close_connection(self, connection: str) -> None:
        """Close the connection"""
        conn_name = connection
        if conn_name not in self.connections:
            raise ConnectionNotOpen(conn_name)

        conn_obj = self.connections.pop(conn_name)
        if conn_obj is not None:
            conn_obj.close()

    def close_connections(self) -> None:
        # Decouple deleting dictionary elements from iterating over connections dict
        existing_conns = list(self.connections.keys())
        for connection in existing_conns:
            self.close_connection(connection)


class Group(Host):
    pass


class Hosts(Dict[str, Host]):
    pass


class Groups(Dict[str, Group]):
    pass


TransformFunction = Callable[[Arg(Host), KwArg(Any)], None]
FilterObj = Callable[[Arg(Host), KwArg(Any)], bool]


class Inventory(object):
    __slots__ = ("hosts", "groups", "defaults")

    def __init__(
        self,
        hosts: Hosts,
        groups: Optional[Groups] = None,
        defaults: Optional[Defaults] = None,
        transform_function: TransformFunction = None,
        transform_function_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.hosts = hosts
        self.groups = groups or Groups()
        self.defaults = defaults or Defaults(None, None, None, None, None, None, None)

    def filter(
        self, filter_obj: FilterObj = None, filter_func: FilterObj = None, **kwargs: Any
    ) -> "Inventory":
        filter_func = filter_obj or filter_func
        if filter_func:
            filtered = Hosts(
                {n: h for n, h in self.hosts.items() if filter_func(h, **kwargs)}
            )
        else:
            filtered = Hosts(
                {
                    n: h
                    for n, h in self.hosts.items()
                    if all(h.get(k) == v for k, v in kwargs.items())
                }
            )
        return Inventory(hosts=filtered, groups=self.groups, defaults=self.defaults)

    def __len__(self) -> int:
        return self.hosts.__len__()

    def children_of_group(self, group: Union[str, Group]) -> Set[Host]:
        """
        Returns set of hosts that belongs to a group including those that belong
        indirectly via inheritance
        """
        hosts: Set[Host] = set()
        for host in self.hosts.values():
            if host.has_parent_group(group):
                hosts.add(host)
        return hosts

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        """
        Return serialized dictionary of inventory
        """
        return {
            "hosts": {"$name": Host.schema()},
            "groups": {"$group": Group.schema()},
            "defaults": Defaults.schema(),
        }

    def dict(self) -> Dict[str, Any]:
        """
        Return serialized dictionary of inventory
        """
        return {
            "hosts": {n: h.dict() for n, h in self.hosts.items()},
            "groups": {n: g.dict() for n, g in self.groups.items()},
            "defaults": self.defaults.dict(),
        }
