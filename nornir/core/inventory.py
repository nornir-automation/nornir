import getpass


class Host(object):
    """
    Represents a host.

    Arguments:
        name (str): Name of the host
        group (:obj:`Group`, optional): Group the host belongs to
        nornir (:obj:`nornir.core.Nornir`): Reference to the parent nornir object
        **kwargs: Host data

    Attributes:
        name (str): Name of the host
        groups (list of :obj:`Group`): Groups the host belongs to
        defaults (``dict``): Default values for host/group data
        data (dict): data about the device
        connections (``dict``): Already established connections

    Note:

        You can access the host data in two ways:

        1. Via the ``data`` attribute - In this case you will get access
           **only** to the data that belongs to the host.
           2. Via the host itself as a dict - :obj:`Host` behaves like a
           dict. The difference between accessing data via the ``data`` attribute
           and directly via the host itself is that the latter will also
           return the data if it's available via a parent :obj:`Group`.

        For instance::

            ---
            # hosts
            my_host:
                ip: 1.2.3.4
                groups: [bma]

            ---
            # groups
            bma:
                site: bma
                group: [all]
            all:
                domain: acme.com

        * ``my_host.data["ip"]`` will return ``1.2.3.4``
        * ``my_host["ip"]`` will return ``1.2.3.4``
        * ``my_host.data["site"]`` will ``fail``
        * ``my_host["site"]`` will return ``bma``
        * ``my_host.data["domain"]`` will ``fail``
        * ``my_host.group.data["domain"]`` will ``fail``
        * ``my_host["domain"]`` will return ``acme.com``
        * ``my_host.group["domain"]`` will return ``acme.com``
        * ``my_host.group.group.data["domain"]`` will return ``acme.com``
    """

    def __init__(self, name, groups=None, nornir=None, defaults=None, **kwargs):
        self.nornir = nornir
        self.name = name
        self.groups = groups or []
        self.data = {}
        self.data["name"] = name
        self.connections = {}
        self.defaults = defaults or {}

        if len(self.groups):
            if isinstance(groups[0], str):
                self.data["groups"] = groups
            else:
                self.data["groups"] = [g.name for g in groups]

        for k, v in kwargs.items():
            self.data[k] = v

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
        for k, v in self.defaults.items():
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
        for g in self.groups:
            if g is group or g.has_parent_group(group):
                return True

        return False

    def __getitem__(self, item):
        try:
            return self.data[item]

        except KeyError:
            for g in self.groups:
                r = g.get(item)
                if r:
                    return r

            r = self.defaults.get(item)
            if r:
                return r

            raise

    def __setitem__(self, item, value):
        self.data[item] = value

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        return self.data.__iter__()

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}: {}".format(self.__class__.__name__, self.name)

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

    @property
    def host(self):
        """String used to connect to the device. Either ``nornir_host`` or ``self.name``"""
        return self.get("nornir_host", self.name)

    @property
    def username(self):
        """Either ``nornir_username`` or user running the script."""
        return self.get("nornir_username", getpass.getuser())

    @property
    def password(self):
        """Either ``nornir_password`` or empty string."""
        return self.get("nornir_password", "")

    @property
    def ssh_port(self):
        """Either ``nornir_ssh_port`` or 22."""
        return self.get("nornir_ssh_port", 22)

    @property
    def network_api_port(self):
        """
        For network equipment this is the port where the device's API is listening to.
        Either ``nornir_network_api_port`` or ``None``.
        """
        return self.get("nornir_network_api_port")

    @property
    def os(self):
        """OS the device is running. Defaults to ``nornir_os``."""
        return self.get("nornir_os")

    @property
    def nos(self):
        """Network OS the device is running. Defaults to ``nornir_nos``."""
        return self.get("nornir_nos")

    def get_connection(self, connection):
        """
        The function of this method is twofold:

            1. If an existing connection is already established for the given type return it
            2. If non exists, establish a new connection of that type with default parameters
                and return it

        Raises:
            AttributeError: if it's unknown how to establish a connection for the given
                type

        Arguments:
            connection_name (str): Name of the connection, for instance, netmiko, paramiko,
                napalm...

        Returns:
            An already established connection of type ``connection``
        """
        if connection not in self.connections:
            try:
                conn_task = self.nornir.available_connections[connection]
            except KeyError:
                raise AttributeError(
                    "not sure how to establish a connection for {}".format(connection)
                )

            # We use `filter(name=self.name)` to call the connection task for only
            # the given host. We also have to set `num_workers=1` because chances are
            # we are already inside a thread
            # Task should establish a connection and populate self.connection[connection]
            r = self.nornir.filter(name=self.name).run(conn_task, num_workers=1)
            if r[self.name].exception:
                raise r[self.name].exception

        return self.connections[connection]


class Group(Host):
    """Same as :obj:`Host`"""

    def children(self):
        return {
            n: h
            for n, h in self.nornir.inventory.hosts.items()
            if h.has_parent_group(self)
        }


class Inventory(object):
    """
    An inventory contains information about hosts and groups.

    Arguments:
        hosts (dict): keys are hostnames and values are either :obj:`Host` or a dict
            representing the host data.
        groups (dict): keys are group names and values are either :obj:`Group` or a dict
            representing the group data.
        transform_function (callable): we will call this function for each host. This is useful
            to manipulate host data and make it more consumable. For instance, if your inventory
            has a "user" attribute you could use this function to map it to "nornir_user"

    Attributes:
        hosts (dict): keys are hostnames and values are :obj:`Host`.
        groups (dict): keys are group names and the values are :obj:`Group`.
    """

    def __init__(
        self, hosts, groups=None, defaults=None, transform_function=None, nornir=None
    ):
        self._nornir = nornir

        self.defaults = defaults or {}

        self.groups = groups or {}
        for n, g in self.groups.items():
            if isinstance(g, dict):
                g = Group(name=n, nornir=nornir, **g)
            self.groups[n] = g

        for group in self.groups.values():
            group.groups = self._resolve_groups(group.groups)

        self.hosts = {}
        for n, h in hosts.items():
            if isinstance(h, dict):
                h = Host(name=n, nornir=nornir, defaults=self.defaults, **h)

            if transform_function:
                transform_function(h)

            h.groups = self._resolve_groups(h.groups)
            self.hosts[n] = h

    def _resolve_groups(self, groups):
        r = []
        if len(groups):
            if not isinstance(groups[0], Group):
                r = [self.groups[g] for g in groups]
            else:
                r = groups
        return r

    def filter(self, filter_func=None, **kwargs):
        """
        Returns a new inventory after filtering the hosts by matching the data passed to the
        function. For instance, assume an inventory with::

            ---
            host1:
                site: bma
                role: http
            host2:
                site: cmh
                role: http
            host3:
                site: bma
                role: db

        * ``my_inventory.filter(site="bma")`` will result in ``host1`` and ``host3``
        * ``my_inventory.filter(site="bma", role="db")`` will result in ``host3`` only

        Arguments:
            filter_func (callable): if filter_func is passed it will be called against each
              device. If the call returns ``True`` the device will be kept in the inventory
        """
        if filter_func:
            filtered = {n: h for n, h in self.hosts.items() if filter_func(h, **kwargs)}
        else:
            filtered = {
                n: h
                for n, h in self.hosts.items()
                if all(h.get(k) == v for k, v in kwargs.items())
            }
        return Inventory(hosts=filtered, groups=self.groups, nornir=self.nornir)

    def __len__(self):
        return self.hosts.__len__()

    @property
    def nornir(self):
        """Reference to the parent :obj:`nornir.core.Nornir` object"""
        return self._nornir

    @nornir.setter
    def nornir(self, value):
        if not getattr(self, "_nornir", None):
            self._nornir = value

        for h in self.hosts.values():
            h.nornir = value

        for g in self.groups.values():
            g.nornir = value
