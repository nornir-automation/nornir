from collections import UserList
from typing import Any, Dict, List, Optional, Set, Union

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin, Connections
from nornir.core.exceptions import ConnectionAlreadyOpen, ConnectionNotOpen


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

    def __recursive_slots__(self):
        s = self.__slots__
        for b in self.__class__.__bases__:
            if hasattr(b, "__recursive_slots__"):
                s += b().__recursive_slots__()
            elif hasattr(b, "__slots__"):
                s += b.__slots__
        return s

    def dict(self):
        return {k: object.__getattribute__(self, k) for k in self.__recursive_slots__()}


class ConnectionOptions(BaseAttributes):
    __slots__ = ("extras",)

    def __init__(self, extras: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        self.extras = extras
        super().__init__(**kwargs)


class ParentGroups(UserList):
    __slots__ = "refs"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.refs: List["Group"] = kwargs.get("refs", [])

    def __contains__(self, value) -> bool:
        return value in self.data or value in self.refs


class InventoryElement(BaseAttributes):
    __slots__ = ("groups", "data", "connection_options")

    def __init__(
        self,
        groups: Optional[ParentGroups] = None,
        data: Optional[Dict[str, Any]] = None,
        connection_options: Optional[Dict[str, ConnectionOptions]] = None,
        **kwargs,
    ) -> None:
        self.groups = groups or ParentGroups()
        self.data = data or {}
        self.connection_options = connection_options or {}
        super().__init__(**kwargs)


class Defaults(BaseAttributes):
    __slots__ = ("data", "connection_options")

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        connection_options: Optional[Dict[str, ConnectionOptions]] = None,
        **kwargs,
    ) -> None:
        self.data = data or {}
        self.connection_options = connection_options or {}
        super().__init__(**kwargs)


class Host(InventoryElement):
    __slots__ = ("name", "connections", "defaults")

    def __init__(
        self, name: str, defaults: Optional[Defaults] = None, **kwargs
    ) -> None:
        self.name = name
        self.defaults = defaults or Defaults()
        self.connections: Connections = Connections()
        super().__init__(**kwargs)

    def _resolve_data(self):
        processed = []
        result = {}
        for k, v in self.data.items():
            processed.append(k)
            result[k] = v
        for g in self.groups.refs:
            for k, v in g.items():
                if k not in processed:
                    processed.append(k)
                    result[k] = v
        for k, v in self.defaults.data.items():
            if k not in processed:
                processed.append(k)
                result[k] = v
        return result

    def keys(self):
        """Returns the keys of the attribute ``data`` and of the parent(s) groups."""
        return self._resolve_data().keys()

    def values(self):
        """Returns the values of the attribute ``data`` and of the parent(s) groups."""
        return self._resolve_data().values()

    def items(self):
        """
        Returns all the data accessible from a device, including
        the one inherited from parent groups
        """
        return self._resolve_data().items()

    def has_parent_group(self, group):
        """Retuns whether the object is a child of the :obj:`Group` ``group``"""
        if isinstance(group, str):
            return self._has_parent_group_by_name(group)

        else:
            return self._has_parent_group_by_object(group)

    def _has_parent_group_by_name(self, group):
        for g in self.groups.refs:
            if g.name == group or g.has_parent_group(group):
                return True

    def _has_parent_group_by_object(self, group):
        for g in self.groups.refs:
            if g is group or g.has_parent_group(group):
                return True

    def __getitem__(self, item):
        try:
            return self.data[item]

        except KeyError:
            for g in self.groups.refs:
                try:
                    r = g[item]
                    return r
                except KeyError:
                    continue

            r = self.defaults.data.get(item)
            if r:
                return r

            raise

    def __getattribute__(self, name):
        if name not in ("hostname", "port", "username", "password", "platform"):
            return object.__getattribute__(self, name)
        v = object.__getattribute__(self, name)
        if v is None:
            for g in self.groups.refs:
                r = getattr(g, name)
                if r is not None:
                    return r

            return object.__getattribute__(self.defaults, name)
        else:
            return v

    def __bool__(self):
        return bool(self.name)

    def __setitem__(self, item, value):
        self.data[item] = value

    def __len__(self):
        return len(self._resolve_data().keys())

    def __iter__(self):
        return self.data.__iter__()

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}: {}".format(self.__class__.__name__, self.name or "")

    def get(self, item, default=None):
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
            p = ConnectionOptions()

        for g in self.groups.refs:
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
            self.open_connection(
                connection=connection,
                configuration=configuration,
                **self.get_connection_parameters(connection).dict(),
            )
        return self.connections[connection].connection

    def get_connection_state(self, connection: str) -> Dict[str, Any]:
        """
        For an already established connection return its state.
        """
        if connection not in self.connections:
            raise ConnectionNotOpen(connection)

        return self.connections[connection].state

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
        if connection in self.connections:
            raise ConnectionAlreadyOpen(connection)

        self.connections[connection] = self.connections.get_plugin(connection)()
        if default_to_host_attributes:
            conn_params = self.get_connection_parameters(connection)
            self.connections[connection].open(
                hostname=hostname if hostname is not None else conn_params.hostname,
                username=username if username is not None else conn_params.username,
                password=password if password is not None else conn_params.password,
                port=port if port is not None else conn_params.port,
                platform=platform if platform is not None else conn_params.platform,
                extras=extras if extras is not None else conn_params.extras,
                configuration=configuration,
            )
        else:
            self.connections[connection].open(
                hostname=hostname,
                username=username,
                password=password,
                port=port,
                platform=platform,
                extras=extras,
                configuration=configuration,
            )
        return self.connections[connection]

    def close_connection(self, connection: str) -> None:
        """ Close the connection"""
        if connection not in self.connections:
            raise ConnectionNotOpen(connection)

        self.connections.pop(connection).close()

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


class Inventory(object):
    __slots__ = ("hosts", "groups", "defaults")

    def __init__(
        self,
        hosts: Hosts,
        groups: Optional[Groups] = None,
        defaults: Optional[Defaults] = None,
        transform_function=None,
    ) -> None:
        self.hosts = hosts
        self.groups = groups or Groups()
        self.defaults = defaults or Defaults()

        for host in self.hosts.values():
            host.groups.refs = [self.groups[p] for p in host.groups]
        for group in self.groups.values():
            group.groups.refs = [self.groups[p] for p in group.groups]

        if transform_function:
            for h in self.hosts.values():
                transform_function(h)

    def filter(self, filter_obj=None, filter_func=None, *args, **kwargs):
        filter_func = filter_obj or filter_func
        if filter_func:
            filtered = {n: h for n, h in self.hosts.items() if filter_func(h, **kwargs)}
        else:
            filtered = {
                n: h
                for n, h in self.hosts.items()
                if all(h.get(k) == v for k, v in kwargs.items())
            }
        return Inventory(hosts=filtered, groups=self.groups, defaults=self.defaults)

    def __len__(self):
        return self.hosts.__len__()

    def children_of_group(self, group: Union[str, Group]) -> Set[Host]:
        """
        Returns set of hosts that belongs to a group including those that belong
        indirectly via inheritance
        """
        hosts: List[Host] = set()
        for host in self.hosts.values():
            if host.has_parent_group(group):
                hosts.add(host)
        return hosts
