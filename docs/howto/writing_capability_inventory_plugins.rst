Writing capability-aware inventory plugins
==========================================

Capability-aware inventory plugins tell Nornir whether they load the inventory
synchronously, asynchronously, or both. :func:`nornir.InitNornir` uses the
synchronous ``load``; ``await`` :func:`nornir.AInitNornir` uses the asynchronous
``aload`` when the plugin declares it, and otherwise runs ``load`` in a worker
thread. Like the connection plugin contracts, these are structural protocols from
:mod:`nornir.core.plugins.inventory`: a plugin does not inherit from a Nornir
class.

Existing inventory plugins that implement
:class:`~nornir.core.plugins.inventory.InventoryPlugin` need no change. They keep
working with ``InitNornir`` and also work with ``AInitNornir``, which constructs
and loads them in a worker thread.

Choose a protocol facet
-----------------------

Every capability-aware inventory plugin implements the common
:class:`~nornir.core.plugins.inventory.CapabilityInventoryPlugin` contract:

* it is constructed with the ``inventory.options`` of the configuration, and the
  constructor performs no I/O; and
* ``get_capabilities()`` returns the loading modes it supports.

The loading facets describe the methods each mode requires:

* :class:`~nornir.core.plugins.inventory.SyncCapabilityInventoryPlugin` adds a
  synchronous ``load`` that returns an
  :class:`~nornir.core.inventory.Inventory`.
* :class:`~nornir.core.plugins.inventory.AsyncCapabilityInventoryPlugin` adds a
  native coroutine ``aload`` that returns the same kind of
  :class:`~nornir.core.inventory.Inventory`. An asyncio-only plugin does not need
  a ``load`` stub.
* :class:`~nornir.core.plugins.inventory.DualCapabilityInventoryPlugin` combines
  both. ``InitNornir`` calls ``load`` and ``AInitNornir`` calls ``aload``.

Declare capabilities
--------------------

``get_capabilities`` must be a synchronous operation that performs no I/O. Its
return type is ``frozenset[InventoryCapability]``, where ``InventoryCapability``
is ``Literal["sync", "asyncio"]``. These are the only valid declarations:

.. code-block:: python

   frozenset({"sync"})
   frozenset({"asyncio"})
   frozenset({"sync", "asyncio"})

Nornir constructs the plugin, then validates the declaration before calling any
loading method. A synchronous ``load`` must be a regular callable and ``aload``
must be a native coroutine function. An empty set, another collection type, an
unknown value, an exception raised by ``get_capabilities``, or a missing declared
method raises :class:`~nornir.core.exceptions.InventoryPluginContractError`.

``InitNornir`` raises :class:`~nornir.core.exceptions.InventoryPluginNotSyncError`
for a plugin that only declares ``asyncio``. The message tells the user to call
``await AInitNornir(...)`` instead.

Implement ``aload``
-------------------

``aload`` runs on the application's event loop, so it must not block it: await
every network call, and do not call blocking client libraries or ``time.sleep``.
Keep the conversion from the API payload to hosts, groups and defaults in a helper
that both ``load`` and ``aload`` use:

.. code-block:: python

   import httpx

   from nornir.core.inventory import Inventory
   from nornir.core.plugins.inventory import InventoryCapability


   class MyApiInventory:
       def __init__(self, url: str, token: str) -> None:
           self.url = url
           self.token = token

       def get_capabilities(self) -> frozenset[InventoryCapability]:
           return frozenset({"sync", "asyncio"})

       def load(self) -> Inventory:
           with httpx.Client(timeout=30) as client:
               data = client.get(self.url, headers=self._headers()).json()
           return self._build_inventory(data)

       async def aload(self) -> Inventory:
           async with httpx.AsyncClient(timeout=30) as client:
               data = (await client.get(self.url, headers=self._headers())).json()
           return self._build_inventory(data)

When the application cancels ``AInitNornir``, the cancellation is delivered into
``aload`` at its current ``await``. Release what ``aload`` acquired, for example
with ``async with``, and let the cancellation propagate.

Set timeouts in ``load``
------------------------

Under ``AInitNornir``, a synchronous ``load`` runs in a worker thread from the
event loop's default executor. A thread cannot be interrupted: when the
application cancels ``AInitNornir``, control returns to the application at once,
but the thread runs until ``load`` returns and its result is discarded. A
``load`` that waits forever on a network call can delay the application's
shutdown, so set timeouts on every network call it makes.

Register the plugin once
------------------------

Register a capability-aware plugin once, whatever it declares. For programmatic
registration, use the capability-aware registry:

.. code-block:: python

   from nornir.core.plugins.inventory import CapabilityInventoryPluginRegister

   CapabilityInventoryPluginRegister.register("my_api_inventory", MyApiInventory)

To make an installed plugin discoverable by ``InitNornir`` and ``AInitNornir``,
publish it in the ``nornir.plugins.capability_inventory`` entry-point group:

.. code-block:: toml

   [project.entry-points."nornir.plugins.capability_inventory"]
   my_api_inventory = "my_package.inventory:MyApiInventory"

Users select it by name, exactly as before:

.. code-block:: yaml

   inventory:
       plugin: my_api_inventory
       options:
           url: "https://inventory.example.com/api/devices"
           token: "..."

Do not register one name in both the ``nornir.plugins.inventory`` and
``nornir.plugins.capability_inventory`` groups. Both entry points raise
:class:`~nornir.core.exceptions.InventoryPluginAmbiguousError` for such a name,
even when both registrations refer to the same class. A package that must still
support Nornir releases without the capability registry keeps its legacy
registration under a different name.

The legacy inventory, transform function, runner and connection registries
currently share one set of names. A capability-aware inventory plugin whose name
is already used by one of them, for example ``threaded`` (the threaded runner),
is also reported as ambiguous. Choose names that are specific to your plugin.

Write async transform functions
-------------------------------

A transform function defined with ``async def`` enriches hosts from an
asynchronous source, such as a secrets store or an IPAM. It receives the same
arguments as a synchronous transform function:

.. code-block:: python

   from typing import Any

   from nornir.core.inventory import Host


   async def read_password(host: Host, **kwargs: Any) -> None:
       host.password = await vault.read_secret(host.name)

Register it in the
:data:`~nornir.core.plugins.inventory.AsyncTransformFunctionRegister`, or publish
it in the ``nornir.plugins.async_transform_function`` entry-point group:

.. code-block:: toml

   [project.entry-points."nornir.plugins.async_transform_function"]
   read_password = "my_package.transforms:read_password"

``AInitNornir`` awaits an async transform function once per host, in inventory
order, one host at a time. A synchronous transform function runs in a worker
thread. ``InitNornir`` raises
:class:`~nornir.core.exceptions.TransformFunctionNotSyncError` for a transform
function defined with ``async def`` before the inventory is loaded.

Nornir decides how to call a transform function from how it is defined, not from
the registry it was found in, so define async transforms as ``async def``
functions. A callable object with an ``async def __call__`` is not detected as
asynchronous. As for inventory plugins, registering one name in both transform
function registries raises
:class:`~nornir.core.exceptions.TransformFunctionAmbiguousError`.
