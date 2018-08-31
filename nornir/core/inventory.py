from typing import Any, Dict, List, Optional

from nornir.core.configuration import Config
from nornir.core.connections import Connections
from nornir.core.exceptions import ConnectionAlreadyOpen, ConnectionNotOpen

GroupsDict = None  # DELETEME
HostsDict = None  # DELETEME
VarsDict = None  # DELETEME


class ElementData(object):
    __slots__ = (
        "hostname",
        "port",
        "username",
        "password",
        "platform",
        "groups",
        "data",
        "connections",
    )

    def __init__(
        self,
        hostname: Optional[str] = None,
        port: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        platform: Optional[str] = None,
        groups: Optional[List["Group"]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.platform = platform
        self.groups = groups or []
        self.data = data or {}
        self.connections = Connections()


class Host(ElementData):
    __slots__ = ("name", "defaults")

    def __init__(
        self, name: str, defaults: Optional[ElementData] = None, *args, **kwargs
    ) -> None:
        self.name = name
        self.defaults = defaults or ElementData()
        super().__init__(*args, **kwargs)

    def _resolve_data(self):
        processed = []
        result = {}
        for k, v in self.data.items():
            processed.append(k)
            result[k] = v
        for g in self.groups:
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
        for g in self.groups:
            if g.name == group or g.has_parent_group(group):
                return True

    def _has_parent_group_by_object(self, group):
        for g in self.groups:
            if g is group or g.has_parent_group(group):
                return True

    def __getitem__(self, item):
        try:
            return self.data[item]

        except KeyError:
            for g in self.groups:
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
        v = object.__getattribute__(self, name)
        if v is None:
            for g in self.groups:
                r = object.__getattribute__(g, name)
                if r is not None:
                    return r

            return getattr(self.defaults, name)
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
        try:
            return self.__getitem__(item)

        except KeyError:
            return default

    @property
    def nornir(self):
        """Reference to the parent :obj:`nornir.core.Nornir` object"""
        return self._nornir

    @nornir.setter
    def nornir(self, value):
        # If it's already set we don't want to set it again
        # because we may lose valuable information
        if not getattr(self, "_nornir", None):
            self._nornir = value

    def get_connection_parameters(
        self, connection: Optional[str] = None
    ) -> Dict[str, Any]:
        if not connection:
            return {
                "hostname": self.hostname,
                "port": self.port,
                "username": self.username,
                "password": self.password,
                "platform": self.platform,
                "connection_options": {},
            }
        else:
            conn_params = self.get(f"{connection}_options", {})
            return {
                "hostname": conn_params.get("hostname", self.hostname),
                "port": conn_params.get("port", self.port),
                "username": conn_params.get("username", self.username),
                "password": conn_params.get("password", self.password),
                "platform": conn_params.get("platform", self.platform),
                "connection_options": conn_params.get("connection_options", {}),
            }

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
        if self.nornir:
            config = self.nornir.config
        else:
            config = None
        if connection not in self.connections:
            self.open_connection(
                connection,
                **self.get_connection_parameters(connection),
                configuration=config,
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
        connection_options: Optional[Dict[str, Any]] = None,
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

        self.connections[connection] = self.nornir.get_connection_type(connection)()
        if default_to_host_attributes:
            conn_params = self.get_connection_parameters(connection)
            self.connections[connection].open(
                hostname=hostname if hostname is not None else conn_params["hostname"],
                username=username if username is not None else conn_params["username"],
                password=password if password is not None else conn_params["password"],
                port=port if port is not None else conn_params["port"],
                platform=platform if platform is not None else conn_params["platform"],
                connection_options=connection_options
                if connection_options is not None
                else conn_params["connection_options"],
                configuration=configuration
                if configuration is not None
                else self.nornir.config,
            )
        else:
            self.connections[connection].open(
                hostname=hostname,
                username=username,
                password=password,
                port=port,
                platform=platform,
                connection_options=connection_options,
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


class Inventory(object):
    __slots__ = ("hosts", "groups", "defaults")

    def __init__(
        self,
        hosts: List[Host],
        groups: Optional[List[Group]] = None,
        defaults: Optional[ElementData] = None,
    ):
        self.hosts = hosts
        self.groups = groups or []
        self.defaults = defaults or ElementData()

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
        return Inventory(hosts=filtered, groups=self.groups)

    def __len__(self):
        return self.hosts.__len__()
