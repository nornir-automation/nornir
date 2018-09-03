from collections import Sequence, UserList
from typing import Any, Dict, List, Optional

from nornir.core.configuration import Config
from nornir.core.connections import Connections
from nornir.core.exceptions import ConnectionAlreadyOpen, ConnectionNotOpen

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


class ParentGroups(UserList):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refs: Optional[List["Group"]] = []

    @classmethod
    def get_validators(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, Sequence):
            raise ValueError(f"expected a list, got a {type(v)}")

        return ParentGroups(v)

    def __contains__(self, value) -> bool:
        if isinstance(value, str):
            return value in self.data
        else:
            return value in self.refs


class InventoryElement(BaseAttributes):
    groups: ParentGroups = ParentGroups()
    data: Dict[str, Any] = {}
    connection_options: Dict[str, ConnectionOptions] = {}


class Defaults(BaseAttributes):
    data: Dict[str, Any] = {}
    connection_options: Dict[str, ConnectionOptions] = {}


class Host(InventoryElement):
    name: str = ""
    connections: Connections = Connections()
    defaults: InventoryElement = InventoryElement()
    config: Config = Config()

    class Config:
        ignore_extra = False

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d.pop("name")
        d.pop("connections")
        d.pop("defaults")
        d.pop("config")
        return d

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

    def to_dict(self):
        """ Return a dictionary representing the object. """
        return self.data

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
                r = g.get(item)
                if r:
                    return r

            r = self.defaults.data.get(item)
            if r:
                return r

            raise

    def __getattribute__(self, name):
        if name not in ("hostname", "port", "username", "password", "platform"):
            return object.__getattribute__(self, name)
        v = self.__values__[name]
        if v is None:
            for g in self.groups.refs:
                r = g.__values__[name]
                if r is not None:
                    return r

            return self.defaults.__values__[name]
        else:
            return v

    def __setitem__(self, item, value):
        self.data[item] = value

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        return self.data.__iter__()

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}: {}".format(self.__class__.__name__, self.hostname or "")

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
    ) -> Dict[str, Any]:
        if not connection:
            d = {
                "hostname": self.hostname,
                "port": self.port,
                "username": self.username,
                "password": self.password,
                "platform": self.platform,
                "extras": {},
            }
        else:
            d = self._get_connection_options_recursively(connection)
            if d is not None:
                return d
            else:
                d = {
                    "hostname": self.hostname,
                    "port": self.port,
                    "username": self.username,
                    "password": self.password,
                    "platform": self.platform,
                    "extras": {},
                }
        return ConnectionOptions(**d)

    def _get_connection_options_recursively(self, connection: str) -> Dict[str, Any]:
        p = self.connection_options.get(connection)
        if p is None:
            for g in self.groups.refs:
                p = g._get_connection_options_recursively(connection)
                if p is not None:
                    return p

            return self.defaults.connection_options.get(connection, None)
        else:
            return p

    def get_connection(self, connection: str) -> Any:
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
                connection,
                **self.get_connection_parameters(connection).dict(),
                configuration=self.config,
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
        hostname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        port: Optional[int] = None,
        platform: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
        default_to_host_attributes: bool = True,
    ) -> None:
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
                configuration=configuration
                if configuration is not None
                else self.config,
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


class Inventory(BaseModel):
    hosts: Hosts
    groups: Groups = Groups()
    defaults: Defaults = Defaults()
    _config: Optional[Config] = None

    def __init__(
        self,
        hosts: Dict[str, Dict[str, Any]],
        groups: Optional[Dict[str, Dict[str, Any]]] = None,
        defaults: Optional[Dict[str, Any]] = None,
        transform_function=None,
        *args,
        **kwargs,
    ):
        groups = groups or {}

        if defaults is None:
            defaults = Defaults()

        parsed_hosts = {}
        for n, h in hosts.items():
            if isinstance(h, Host):
                parsed_hosts[n] = h
            else:
                parsed_hosts[n] = Host(name=n, **h)
        parsed_groups = {}
        for n, g in groups.items():
            if isinstance(h, Host):
                parsed_groups[n] = g
            else:
                parsed_groups[n] = Group(name=n, **g)
        super().__init__(
            hosts=parsed_hosts, groups=parsed_groups, defaults=defaults, *args, **kwargs
        )

        for n, h in parsed_hosts.items():
            h.defaults = self.defaults
            for p in h.groups:
                h.groups.refs.append(parsed_groups[p])
        for n, g in parsed_groups.items():
            for p in g.groups:
                g.groups.refs.append(parsed_groups[p])

        if transform_function:
            h.defaults = self.defaults
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

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
        for host in self.hosts.values():
            host._config = value
