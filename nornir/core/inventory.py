from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypeGuard,
    TypeVar,
)

from nornir.core.configuration import Config
from nornir.core.exceptions import (
    ConnectionAlreadyOpen,
    ConnectionNotOpen,
    ConnectionPluginAmbiguousError,
    ConnectionPluginContractError,
    ConnectionPluginNotAsyncError,
    ConnectionPluginNotSyncError,
)
from nornir.core.plugins.connections import (
    AsyncCapabilityConnectionPlugin,
    CapabilityConnectionPlugin,
    CapabilityConnectionPluginRegister,
    ConnectionCapability,
    ConnectionPlugin,
    ConnectionPluginRegister,
    DualCapabilityConnectionPlugin,
    SyncCapabilityConnectionPlugin,
)

if TYPE_CHECKING:
    import builtins
    from collections.abc import Callable, ItemsView, Iterator, KeysView, ValuesView

HostOrGroup = TypeVar("HostOrGroup", "Host", "Group")


@dataclass(frozen=True)
class _CapabilityConnectionState:
    plugin: CapabilityConnectionPlugin
    capabilities: frozenset[ConnectionCapability]


def _is_sync_capability_plugin(
    plugin: CapabilityConnectionPlugin,
) -> TypeGuard[SyncCapabilityConnectionPlugin]:
    open_method = getattr(plugin, "open", None)
    close_method = getattr(plugin, "close", None)
    return (
        callable(open_method)
        and not inspect.iscoroutinefunction(open_method)
        and callable(close_method)
        and not inspect.iscoroutinefunction(close_method)
    )


def _is_async_capability_plugin(
    plugin: CapabilityConnectionPlugin,
) -> TypeGuard[AsyncCapabilityConnectionPlugin]:
    async_open = inspect.iscoroutinefunction(getattr(plugin, "aopen", None))
    async_close = inspect.iscoroutinefunction(getattr(plugin, "aclose", None))
    return async_open and async_close


def _is_dual_capability_plugin(
    plugin: CapabilityConnectionPlugin,
) -> TypeGuard[DualCapabilityConnectionPlugin]:
    return _is_sync_capability_plugin(plugin) and _is_async_capability_plugin(plugin)


def _validate_capability_plugin(
    connection_name: str, plugin: CapabilityConnectionPlugin
) -> frozenset[ConnectionCapability]:
    try:
        reporter = getattr(plugin, "get_capabilities", None)
    except Exception as exc:
        raise ConnectionPluginContractError(
            connection_name, "get_capabilities could not be accessed"
        ) from exc
    if not callable(reporter) or inspect.iscoroutinefunction(reporter):
        raise ConnectionPluginContractError(
            connection_name, "get_capabilities must be a synchronous callable"
        )

    try:
        capabilities = reporter()
    except Exception as exc:
        raise ConnectionPluginContractError(connection_name, "get_capabilities failed") from exc

    valid_declarations = (
        frozenset({"sync"}),
        frozenset({"asyncio"}),
        frozenset({"sync", "asyncio"}),
    )
    if not isinstance(capabilities, frozenset) or capabilities not in valid_declarations:
        raise ConnectionPluginContractError(
            connection_name,
            "get_capabilities must return a nonempty frozenset containing only "
            "'sync' and/or 'asyncio'",
        )

    operation_guard: Callable[[CapabilityConnectionPlugin], bool]
    if capabilities == valid_declarations[2]:
        operation_guard = _is_dual_capability_plugin
        invalid_reason = (
            "dual capability requires synchronous open/close and native async aopen/aclose"
        )
    elif "sync" in capabilities:
        operation_guard = _is_sync_capability_plugin
        invalid_reason = "sync capability requires synchronous open and close"
    else:
        operation_guard = _is_async_capability_plugin
        invalid_reason = "asyncio capability requires native async aopen and aclose"

    try:
        operations_valid = operation_guard(plugin)
    except Exception as exc:
        raise ConnectionPluginContractError(
            connection_name, "declared operations could not be accessed"
        ) from exc

    if not operations_valid:
        raise ConnectionPluginContractError(connection_name, invalid_reason)

    return capabilities


class BaseAttributes:
    __slots__ = ("hostname", "password", "platform", "port", "username")

    def __init__(
        self,
        hostname: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        platform: str | None = None,
    ) -> None:
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.platform = platform

    @classmethod
    def schema(cls) -> dict[str, Any]:
        """Return a description of the serialized form of the object.

        This is documentation rather than a schema you can validate against: the values
        are the names of the expected types, and elsewhere ``$name`` placeholders stand
        for keys the user chooses.

        Returns:
            The shape of what :py:meth:`dict` returns.

        """
        return {
            "hostname": "str",
            "port": "int",
            "username": "str",
            "password": "str",
            "platform": "str",
        }

    def dict(self) -> dict[str, Any]:
        """Return the object serialized as a dictionary.

        Only the values set on the object itself are returned. Subclasses that resolve
        their attributes through groups and defaults, :obj:`Host` and :obj:`Group`, are
        deliberately bypassed here, so a value inherited rather than set directly shows
        up as ``None``.

        Returns:
            The attributes of the object.

        """
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
        hostname: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        platform: str | None = None,
        extras: dict[str, Any] | None = None,
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
    def schema(cls) -> dict[str, Any]:
        """Return a description of the serialized form of the connection options.

        Returns:
            The shape of what :py:meth:`dict` returns, with ``extras`` holding whatever
            keys the connection plugin accepts.

        """
        return {
            "extras": {"$key": "$value"},
            **super().schema(),
        }

    def dict(self) -> dict[str, Any]:
        """Return the connection options serialized as a dictionary.

        Returns:
            The attributes of the object, including ``extras``.

        """
        return {
            "extras": self.extras,
            **super().dict(),
        }


class ParentGroups(list["Group"]):
    def __contains__(self, value: object) -> bool:
        if isinstance(value, str):
            return any(value == g.name for g in self)

        return any(value == g for g in self)

    def add(self, group: Group) -> None:
        """Add the ParentGroup.

        The group will only be appended if it does not exist.

        :param group: Parent Group object to add
        :return: None
        """
        # only add the group if it doesn't exist
        if not self.__contains__(group):
            self.append(group)


class InventoryElement(BaseAttributes):
    __slots__ = ("connection_options", "data", "groups")

    def __init__(
        self,
        hostname: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        platform: str | None = None,
        groups: ParentGroups | None = None,
        data: dict[str, Any] | None = None,
        connection_options: dict[str, ConnectionOptions] | None = None,
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
    def schema(cls) -> dict[str, Any]:
        """Return a description of the serialized form of the object.

        Returns:
            The shape of what :py:meth:`dict` returns.

        """
        return {
            "groups": ["$group_name"],
            "data": {"$key": "$value"},
            "connection_options": {"$connection_type": ConnectionOptions.schema()},
            **super().schema(),
        }

    def dict(self) -> dict[str, Any]:
        """Return the object serialized as a dictionary.

        The parent groups are reduced to their names, so the result is a flat structure
        that can be written back out as YAML or JSON.

        Returns:
            The attributes of the object, without anything it inherits.

        """
        return {
            "groups": [g.name for g in self.groups],
            "data": self.data,
            "connection_options": {k: v.dict() for k, v in self.connection_options.items()},
            **super().dict(),
        }

    def extended_groups(self) -> list[Group]:
        """Return the groups this host belongs to by virtue of inheritance.

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

        Returns:
            The groups this host belongs to, directly or through inheritance.

        """
        groups: list[Group] = []

        for g in self.groups:
            if g not in groups:
                groups.append(g)

            for sg in g.extended_groups():
                if sg not in groups:
                    groups.append(sg)

        return groups


class Defaults(BaseAttributes):
    __slots__ = ("connection_options", "data")

    def __init__(
        self,
        hostname: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        platform: str | None = None,
        data: dict[str, Any] | None = None,
        connection_options: dict[str, ConnectionOptions] | None = None,
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
    def schema(cls) -> dict[str, Any]:
        """Return a description of the serialized form of the defaults.

        Returns:
            The shape of what :py:meth:`dict` returns.

        """
        return {
            "data": {"$key": "$value"},
            "connection_options": {"$connection_type": ConnectionOptions.schema()},
            **super().schema(),
        }

    def dict(self) -> dict[str, Any]:
        """Return the defaults serialized as a dictionary.

        Returns:
            The attributes of the object, with the connection options serialized too.

        """
        return {
            "data": self.data,
            "connection_options": {k: v.dict() for k, v in self.connection_options.items()},
            **super().dict(),
        }


class Host(InventoryElement):  # noqa: PLR0904 - the public lifecycle API adds four required methods.
    __slots__ = (
        "_async_connections",
        "_capability_connections",
        "_opening",
        "connections",
        "defaults",
        "name",
    )

    def __init__(
        self,
        name: str,
        hostname: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        platform: str | None = None,
        groups: ParentGroups | None = None,
        data: dict[str, Any] | None = None,
        connection_options: dict[str, ConnectionOptions] | None = None,
        defaults: Defaults | None = None,
    ) -> None:
        self.name = name
        self.defaults = defaults or Defaults(None, None, None, None, None, None, None)
        self.connections: dict[str, ConnectionPlugin] = {}
        self._async_connections: dict[str, AsyncCapabilityConnectionPlugin] = {}
        self._capability_connections: dict[str, _CapabilityConnectionState] = {}
        self._opening: set[str] = set()
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

    def extended_data(self) -> dict[str, Any]:
        """Return the data associated with the object including inherited data.

        Returns:
            The data of the object merged with the data inherited from its groups
            and from the defaults.

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
    def schema(cls) -> dict[str, Any]:
        """Return a description of the serialized form of the host.

        This is the structure a host takes in an inventory file, which makes it a handy
        reference when writing one::

            >>> import json
            >>> print(json.dumps(Host.schema(), indent=4))

        Returns:
            The shape of what :py:meth:`dict` returns.

        """
        return {
            "name": "str",
            "connection_options": {"$connection_type": ConnectionOptions.schema()},
            **super().schema(),
        }

    def dict(self) -> dict[str, Any]:
        """Return the host serialized as a dictionary.

        Only what is set on the host itself is returned. Attribute access resolves
        through the groups and the defaults but this does not, so ``host.hostname`` and
        ``host.dict()["hostname"]`` differ whenever the hostname comes from a group or
        from the defaults. Use :py:meth:`extended_data` for the data as the host sees it.

        Returns:
            The attributes of the host, with its groups reduced to their names.

        """
        return {
            "name": self.name,
            "connection_options": {k: v.dict() for k, v in self.connection_options.items()},
            **super().dict(),
        }

    def keys(self) -> KeysView[str]:
        """Return the keys of the attribute ``data`` and of the parent(s) groups.

        Returns:
            A view of the available keys.

        """
        return self.extended_data().keys()

    def values(self) -> ValuesView[Any]:
        """Return the values of the attribute ``data`` and of the parent(s) groups.

        Returns:
            A view of the available values.

        """
        return self.extended_data().values()

    def items(self) -> ItemsView[str, Any]:
        """Return all the data accessible from a device.

        This includes the data inherited from the parent groups.

        Returns:
            A view of the available key/value pairs.

        """
        return self.extended_data().items()

    def has_parent_group(self, group: str | Group) -> bool:
        """Return whether the object is a child of the :obj:`Group` ``group``.

        Returns:
            ``True`` if the object is a child of ``group``, ``False`` otherwise.

        """
        if isinstance(group, str):
            return self._has_parent_group_by_name(group)

        return self._has_parent_group_by_object(group)

    def _has_parent_group_by_name(self, group: str) -> bool:
        return any(g.name == group or g.has_parent_group(group) for g in self.groups)

    def _has_parent_group_by_object(self, group: Group) -> bool:
        return any(g is group or g.has_parent_group(group) for g in self.groups)

    def __getitem__(self, item: str) -> Any:
        try:
            return self.data[item]

        except KeyError:
            for g in self.extended_groups():
                try:
                    return g.data[item]
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
        return f"{self.__class__.__name__}: {self.name or ''}"

    def get(self, item: str, default: Any = None) -> Any:
        """Return the value ``item`` from the host or hosts group variables.

        Arguments:
            item(``str``): The variable to get
            default(``any``): Return value if item not found

        Returns:
            The value of ``item``, or ``default`` if it could not be found.

        """
        if hasattr(self, item):
            return getattr(self, item)
        try:
            return self.__getitem__(item)

        except KeyError:
            return default

    def get_connection_parameters(self, connection: str | None = None) -> ConnectionOptions:
        """Return the parameters to open a connection of the given type with.

        The options set for ``connection`` on the host win, then those of its groups in
        the order they are listed, then those of the defaults. Anything still unset
        falls back to the matching attribute of the host, which resolves through the
        groups and the defaults in turn.

        Arguments:
            connection: Name of the connection, for instance, netmiko, paramiko,
                napalm... When omitted, the attributes of the host are returned with no
                connection specific options at all

        Returns:
            :obj:`ConnectionOptions`: The parameters to open the connection with.

        """
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

    def _get_connection_options_recursively(self, connection: str) -> ConnectionOptions | None:
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
        """Return an established connection of the given type.

        The function of this method is twofold:

            1. If an existing connection is already established for the given type return it
            2. If none exists, establish a new connection of that type with default parameters
               and return it

        Arguments:
            connection: Name of the connection, for instance, netmiko, paramiko, napalm...
            configuration: Configuration to pass to the connection plugin

        Returns:
            An already established connection

        Raises:
            AttributeError: if it's unknown how to establish a connection for the given type
            ConnectionPluginNotSyncError: if the cached or registered plugin is async-only

        """
        self._check_connection_lookup(connection)
        existing = self.connections.get(connection)
        if existing is not None:
            state = self._public_capability_state(connection, existing)
            if state is not None and "sync" not in state.capabilities:
                raise ConnectionPluginNotSyncError(connection)
            return existing.connection
        if connection in self._async_connections:
            raise ConnectionPluginNotSyncError(connection)

        if existing is None:
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

    async def aget_connection(self, connection: str, configuration: Config) -> Any:
        """Return an established asyncio-capable connection, opening it if needed.

        Returns:
            The established connection.

        Raises:
            ConnectionPluginNotAsyncError: if the plugin does not declare asyncio support

        """
        self._check_connection_lookup(connection)
        existing = self.connections.get(connection)
        if existing is not None:
            state = self._public_capability_state(connection, existing)
            if state is None or "asyncio" not in state.capabilities:
                raise ConnectionPluginNotAsyncError(connection)
            return existing.connection

        async_existing = self._async_connections.get(connection)
        if async_existing is not None:
            state = self._private_capability_state(connection, async_existing)
            if "asyncio" not in state.capabilities:
                raise ConnectionPluginNotAsyncError(connection)
            return async_existing.connection

        conn = self.get_connection_parameters(connection)
        plugin = await self.aopen_connection(
            connection=connection,
            configuration=configuration,
            hostname=conn.hostname,
            port=conn.port,
            username=conn.username,
            password=conn.password,
            platform=conn.platform,
            extras=conn.extras,
        )
        return plugin.connection

    def open_connection(
        self,
        connection: str,
        configuration: Config,
        hostname: str | None = None,
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
        platform: str | None = None,
        extras: builtins.dict[str, Any] | None = None,
        default_to_host_attributes: bool = True,
    ) -> ConnectionPlugin:
        """Open a new connection.

        If ``default_to_host_attributes`` is set to ``True`` arguments will default to host
        attributes if not specified.

        Returns:
            The newly opened connection

        Raises:
            AttributeError: if it's unknown how to establish a connection for the given type
            nornir.core.exceptions.ConnectionAlreadyOpen: a connection of the given type
                is already open
            ConnectionPluginContractError: if a capability declaration is malformed
            ConnectionPluginNotSyncError: if the plugin does not declare sync support

        """
        conn_name = connection
        self._check_connection_lookup(conn_name)
        self._raise_if_connection_exists(conn_name)

        capability_plugin = CapabilityConnectionPluginRegister.available.get(conn_name)
        if capability_plugin is None:
            plugin = ConnectionPluginRegister.get_plugin(conn_name)
            conn_obj = plugin()
            capability_state = None
        else:
            capability_conn_obj = capability_plugin()
            capabilities = _validate_capability_plugin(conn_name, capability_conn_obj)
            if "sync" not in capabilities:
                raise ConnectionPluginNotSyncError(conn_name)
            if not _is_sync_capability_plugin(capability_conn_obj):
                raise ConnectionPluginContractError(
                    conn_name, "validated sync operations are no longer available"
                )
            conn_obj = capability_conn_obj
            capability_state = _CapabilityConnectionState(capability_conn_obj, capabilities)

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
        if capability_state is not None:
            self._capability_connections[conn_name] = capability_state
        return conn_obj

    async def aopen_connection(
        self,
        connection: str,
        configuration: Config,
        hostname: str | None = None,
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
        platform: str | None = None,
        extras: builtins.dict[str, Any] | None = None,
        default_to_host_attributes: bool = True,
    ) -> AsyncCapabilityConnectionPlugin:
        """Open a capability-aware connection through its native asyncio operations.

        Returns:
            The opened plugin instance.

        Raises:
            ConnectionPluginContractError: if a capability declaration is malformed
            ConnectionPluginNotAsyncError: if the plugin does not declare asyncio support

        """
        conn_name = connection
        self._check_connection_lookup(conn_name)
        self._raise_if_connection_exists(conn_name)

        if conn_name in ConnectionPluginRegister.available:
            raise ConnectionPluginNotAsyncError(conn_name)
        plugin = CapabilityConnectionPluginRegister.get_plugin(conn_name)

        conn_obj = plugin()
        capabilities = _validate_capability_plugin(conn_name, conn_obj)
        if "asyncio" not in capabilities:
            raise ConnectionPluginNotAsyncError(conn_name)
        if not _is_async_capability_plugin(conn_obj):
            raise ConnectionPluginContractError(
                conn_name, "validated asyncio operations are no longer available"
            )

        if default_to_host_attributes:
            conn_params = self.get_connection_parameters(conn_name)
            hostname = hostname if hostname is not None else conn_params.hostname
            username = username if username is not None else conn_params.username
            password = password if password is not None else conn_params.password
            port = port if port is not None else conn_params.port
            platform = platform if platform is not None else conn_params.platform
            extras = extras if extras is not None else conn_params.extras

        self._opening.add(conn_name)
        try:
            await conn_obj.aopen(
                hostname=hostname,
                username=username,
                password=password,
                port=port,
                platform=platform,
                extras=extras,
                configuration=configuration,
            )
            if "sync" in capabilities:
                if not _is_dual_capability_plugin(conn_obj):
                    raise ConnectionPluginContractError(
                        conn_name, "validated dual operations are no longer available"
                    )
                self.connections[conn_name] = conn_obj
            else:
                self._async_connections[conn_name] = conn_obj
            self._capability_connections[conn_name] = _CapabilityConnectionState(
                conn_obj, capabilities
            )
            return conn_obj
        finally:
            self._opening.remove(conn_name)

    def close_connection(self, connection: str) -> None:
        """Close the connection.

        Raises:
            nornir.core.exceptions.ConnectionNotOpen: no connection of the given type is open
            ConnectionPluginNotSyncError: if the connection is async-only

        """
        conn_name = connection
        self._check_connection_cache_conflict(conn_name)
        if conn_name in self._async_connections:
            raise ConnectionPluginNotSyncError(conn_name)
        if conn_name not in self.connections:
            raise ConnectionNotOpen(conn_name)

        conn_obj = self.connections[conn_name]
        state = self._public_capability_state(conn_name, conn_obj)
        if state is not None and "sync" not in state.capabilities:
            raise ConnectionPluginNotSyncError(conn_name)
        self.connections.pop(conn_name)
        self._remove_capability_state(conn_name, conn_obj)
        if conn_obj is not None:
            conn_obj.close()

    async def aclose_connection(self, connection: str) -> None:
        """Close one connection, awaiting native async cleanup when declared.

        Raises:
            ConnectionNotOpen: if the connection is not open
            ConnectionPluginContractError: if private connection state is inconsistent

        """
        conn_name = connection
        self._check_connection_cache_conflict(conn_name)
        async_conn = self._async_connections.get(conn_name)
        if async_conn is not None:
            self._private_capability_state(conn_name, async_conn)
            await async_conn.aclose()
            if self._async_connections.get(conn_name) is async_conn:
                self._async_connections.pop(conn_name)
            self._remove_capability_state(conn_name, async_conn)
            return

        conn_obj = self.connections.get(conn_name)
        if conn_obj is None:
            raise ConnectionNotOpen(conn_name)
        state = self._public_capability_state(conn_name, conn_obj)
        if state is not None and "asyncio" in state.capabilities:
            plugin = state.plugin
            if not _is_async_capability_plugin(plugin):
                raise ConnectionPluginContractError(
                    conn_name, "cached asyncio operations are no longer available"
                )
            await plugin.aclose()
        else:
            conn_obj.close()

        if self.connections.get(conn_name) is conn_obj:
            self.connections.pop(conn_name)
        self._remove_capability_state(conn_name, conn_obj)

    def close_connections(self) -> None:
        """Close every connection open on this host.

        Closing a connection that was never opened is not an error here, unlike
        :py:meth:`close_connection`: a host with nothing open is left alone.
        """
        # Snapshot both stores so synchronous cleanup remains deterministic and fail-fast.
        existing_conns = list(self.connections) + list(self._async_connections)
        for connection in existing_conns:
            self.close_connection(connection)

    async def aclose_connections(self) -> None:
        """Close every connection, attempting all entries after ordinary errors.

        Callers must serialize use and cleanup of an individual connection name.
        """
        existing_conns = list(self.connections) + list(self._async_connections)
        first_error: Exception | None = None
        for connection in existing_conns:
            try:
                await self.aclose_connection(connection)
            except Exception as exc:  # noqa: BLE001 - plugin errors must not skip later cleanup.
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error

    def _check_connection_ambiguity(self, connection: str) -> None:
        if (
            connection in ConnectionPluginRegister.available
            and connection in CapabilityConnectionPluginRegister.available
        ):
            raise ConnectionPluginAmbiguousError(connection)

    def _check_connection_cache_conflict(self, connection: str) -> None:
        if connection in self.connections and connection in self._async_connections:
            raise ConnectionPluginContractError(
                connection, "connection exists in both the public and private caches"
            )

    def _check_connection_lookup(self, connection: str) -> None:
        self._check_connection_ambiguity(connection)
        self._check_connection_cache_conflict(connection)
        if connection in self._opening:
            raise ConnectionAlreadyOpen(connection)

    def _raise_if_connection_exists(self, connection: str) -> None:
        if connection in self.connections or connection in self._async_connections:
            raise ConnectionAlreadyOpen(connection)

    def _public_capability_state(
        self, connection: str, plugin: ConnectionPlugin
    ) -> _CapabilityConnectionState | None:
        state = self._capability_connections.get(connection)
        if state is not None and state.plugin is not plugin:
            self._capability_connections.pop(connection)
            return None
        return state

    def _private_capability_state(
        self, connection: str, plugin: AsyncCapabilityConnectionPlugin
    ) -> _CapabilityConnectionState:
        state = self._capability_connections.get(connection)
        if state is None or state.plugin is not plugin:
            raise ConnectionPluginContractError(
                connection, "private connection cache has no matching capability metadata"
            )
        return state

    def _remove_capability_state(
        self, connection: str, plugin: ConnectionPlugin | CapabilityConnectionPlugin
    ) -> None:
        state = self._capability_connections.get(connection)
        if state is not None and state.plugin is plugin:
            self._capability_connections.pop(connection)


class Group(Host):
    pass


class Hosts(dict[str, Host]):
    pass


class Groups(dict[str, Group]):
    pass


class TransformFunction(Protocol):
    """Interface a transform function has to implement.

    A transform function is called once per host after the inventory has been loaded,
    which is where you enrich hosts with data that does not belong in the inventory
    files, such as credentials pulled from a vault.
    """

    def __call__(self, host: Host, **kwargs: Any) -> None:
        """Modify the host in place.

        Anything returned is discarded, so the host has to be changed in place for the
        change to survive.

        Arguments:
            host: Host to modify
            **kwargs: The ``transform_function_options`` of the configuration

        """


class FilterObj(Protocol):
    """Interface a filter passed to :py:meth:`Inventory.filter` has to implement."""

    def __call__(self, host: Host, **kwargs: Any) -> bool:
        """Return whether the host is kept.

        Arguments:
            host: Host to consider
            **kwargs: The keyword arguments given to :py:meth:`Inventory.filter`

        Returns:
            ``True`` to keep ``host`` in the filtered inventory, ``False`` to drop it.

        """
        ...


class Inventory:
    __slots__ = ("defaults", "groups", "hosts")

    def __init__(
        self,
        hosts: Hosts,
        groups: Groups | None = None,
        defaults: Defaults | None = None,
        transform_function: TransformFunction | None = None,
        transform_function_options: dict[str, Any] | None = None,
    ) -> None:
        self.hosts = hosts
        self.groups = groups or Groups()
        self.defaults = defaults or Defaults(None, None, None, None, None, None, None)

    def filter(
        self,
        filter_obj: FilterObj | None = None,
        filter_func: FilterObj | None = None,
        **kwargs: Any,
    ) -> Inventory:
        """Return a new inventory with only the hosts that match.

        Without a callable, a host is kept when every keyword argument equals the value
        the host has under that name. The lookup is the one :py:meth:`Host.get` performs,
        so it sees attributes as well as data, inherited or not, but it compares for
        equality only. Use ``filter_obj`` with an :obj:`nornir.core.filter.F` object for
        anything richer.

        The hosts, groups and defaults are the same objects as in the original
        inventory, not copies, so filtering is cheap and a change made to a host through
        one inventory is visible from the other.

        Arguments:
            filter_obj: Callable deciding whether to keep each host
            filter_func: Same as ``filter_obj``, kept for backwards compatibility and
                ignored when ``filter_obj`` is given
            **kwargs: Passed to the callable, or compared against the hosts when there
                is none

        Returns:
            :obj:`Inventory`: A new inventory holding the hosts that matched.

        """
        filter_func = filter_obj or filter_func
        if filter_func:
            filtered = Hosts({n: h for n, h in self.hosts.items() if filter_func(h, **kwargs)})
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

    def children_of_group(self, group: str | Group) -> set[Host]:
        """Return the set of hosts that belong to a group.

        This includes the hosts that belong to it indirectly via inheritance.

        Returns:
            The hosts that belong to ``group``.

        """
        hosts: set[Host] = set()
        for host in self.hosts.values():
            if host.has_parent_group(group):
                hosts.add(host)
        return hosts

    @classmethod
    def schema(cls) -> dict[str, Any]:
        """Return the schema of a serialized inventory.

        Returns:
            The schema of the hosts, groups and defaults of an inventory.

        """
        return {
            "hosts": {"$name": Host.schema()},
            "groups": {"$group": Group.schema()},
            "defaults": Defaults.schema(),
        }

    def dict(self) -> dict[str, Any]:
        """Return a serialized dictionary of the inventory.

        Returns:
            The hosts, groups and defaults of the inventory serialized as dictionaries.

        """
        return {
            "hosts": {n: h.dict() for n, h in self.hosts.items()},
            "groups": {n: g.dict() for n, g in self.groups.items()},
            "defaults": self.defaults.dict(),
        }
