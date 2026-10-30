Writing capability-aware connection plugins
===========================================

Capability-aware connection plugins tell Nornir whether they can be used from
synchronous tasks, asyncio tasks, or both. They are structural protocols: a plugin
does not inherit from a Nornir class, but its methods and annotations should match
the appropriate protocol from :mod:`nornir.core.plugins.connections`.

Choose a protocol facet
-----------------------

Every capability-aware plugin implements the common
:class:`~nornir.core.plugins.connections.CapabilityConnectionPlugin` contract:

* it can be constructed without arguments and without performing device I/O;
* ``get_capabilities()`` returns its supported execution modes; and
* ``connection`` exposes the established transport after opening succeeds.

The operation facets describe the methods required by each execution mode:

* :class:`~nornir.core.plugins.connections.SyncCapabilityConnectionPlugin`
  adds synchronous ``open`` and ``close`` methods with the existing connection
  plugin signatures.
* :class:`~nornir.core.plugins.connections.AsyncCapabilityConnectionPlugin`
  adds native coroutine ``aopen`` and ``aclose`` methods. Async-only plugins do
  not need unsupported ``open`` or ``close`` stubs.
* :class:`~nornir.core.plugins.connections.DualCapabilityConnectionPlugin`
  combines both operation facets. The plugin opens in whichever mode Nornir
  calls, and the connection stays bound to that mode until it is closed. Each
  mode may create its own transport object.

Use the facet that represents the complete declaration when type-checking your
class. The base protocol alone describes capability reporting and connection
access; it does not make an operation available.

Declare capabilities
--------------------

``get_capabilities`` must be a synchronous, no-I/O operation whose result remains
stable for the lifetime of the plugin instance. Its exact return type is
``frozenset[ConnectionCapability]``, where ``ConnectionCapability`` is the literal
type ``Literal["sync", "asyncio"]``. These are the only valid declarations:

.. code-block:: python

   frozenset({"sync"})
   frozenset({"asyncio"})
   frozenset({"sync", "asyncio"})

Nornir validates the complete declaration before opening a connection. Every
declared operation must be present: synchronous operations must be regular
callables, and asyncio operations must be native coroutine functions. An empty
set, another collection type, an unknown value, a reporting error, or a missing
declared operation raises
:class:`~nornir.core.exceptions.ConnectionPluginContractError` before connection
I/O. Pre-open validation does not access ``connection``. Extra methods do not
enable an undeclared mode.

Register the plugin once
------------------------

Register a capability-aware plugin once, regardless of how many modes it
declares. For programmatic registration, use the capability-aware registry:

.. code-block:: python

   from nornir.core.plugins.connections import CapabilityConnectionPluginRegister

   CapabilityConnectionPluginRegister.register("my-transport", MyTransport)

To make an installed plugin discoverable by :func:`nornir.InitNornir`, publish it
in the execution-neutral ``nornir.plugins.capability_connections`` entry-point
group:

.. code-block:: toml

   [project.entry-points."nornir.plugins.capability_connections"]
   my-transport = "my_transport.connection:MyTransport"

Direct construction of :class:`~nornir.core.Nornir` does not perform automatic
discovery, so prepare the registry explicitly in that case.

The existing
:class:`~nornir.core.plugins.connections.ConnectionPluginRegister` and
``nornir.plugins.connections`` entry-point group remain the compatibility path
for legacy connection plugins. Legacy registrations are treated as sync-only,
even if their classes happen to provide async methods.

Within either registry, registering the same class under the same name again is
idempotent; registering a different class under that name raises
:class:`~nornir.core.exceptions.PluginAlreadyRegistered`. Do not register one name
in both registries. Cross-registry duplicates are ambiguous, even when both
registrations refer to the same class, and connection get/open operations raise
:class:`~nornir.core.exceptions.ConnectionPluginAmbiguousError`. Cleanup still
uses the cached instance's recorded ownership, so it can run after deregistration
or a later registry conflict.

Understand host caching and mode binding
----------------------------------------

There is one logical connection per host and name, bound to the execution mode
that opened it. Use :meth:`~nornir.core.inventory.Host.get_connection` from
synchronous tasks and await :meth:`~nornir.core.inventory.Host.aget_connection`
from asyncio tasks. Requesting an undeclared mode raises a named sync/async
mismatch error, including on a cache hit, without discarding the cached
connection.

The public ``Host.connections`` cache retains its existing type,
``dict[str, ConnectionPlugin]``. It contains legacy, sync-capable, and
dual-capability instances. Async-only instances live in private typed host
storage and intentionally do not appear in ``Host.connections``. Do not inspect
or mutate Nornir's private connection caches or capability metadata.

A dual-capability plugin is stored once and bound to the mode that opened it.
After ``open_connection`` or a synchronous ``get_connection``, the connection is
in sync mode: ``aget_connection`` raises
:class:`~nornir.core.exceptions.ConnectionModeMismatchError` and nothing is
reopened. After ``aopen_connection`` or ``aget_connection``, the connection is
in asyncio mode: ``get_connection`` and the synchronous ``close_connection``
raise the same error, because the synchronous path cannot await ``aclose``. The
error names the mode the connection is in and the close method that releases
it. Once closed, the name can be opened in the other mode.

Concurrent ``aget_connection`` calls for a name that is still opening, for
example from subtasks started with ``asyncio.gather``, wait for that open and
share the connection it establishes; if the open fails, every waiter receives
the failure. An explicit ``aopen_connection`` or a synchronous ``get_connection``
for a name that is opening raises ``ConnectionAlreadyOpen`` instead.

Nornir records the mode and exposes it through
:meth:`~nornir.core.inventory.Host.connection_mode`, so a plugin keeps no mode
state of its own: ``open`` and ``close`` belong to sync mode, ``aopen`` and
``aclose`` to asyncio mode, and Nornir only ever calls the pair that matches the
bound mode. A helper that a plugin adds beyond the contract can consult
``host.connection_mode(name)`` when it needs the current mode.

Implement safe async lifecycle methods
--------------------------------------

``aopen`` and ``aclose`` must be native ``async def`` methods and must not block
the event loop. Keep these resource ownership rules inside the plugin:

* Publish ``connection`` only after opening has succeeded.
* If ``aopen`` fails or is cancelled after acquiring a partial resource, close
  that resource before propagating the exception.
* Make ``aclose`` idempotent, including before opening and after a failed or
  cancelled opening attempt.
* Clear the plugin's transport state while closing so repeated cleanup remains
  safe.

Nornir publishes a plugin into a host cache only after opening succeeds. A failed
or cancelled ``aopen`` is not cached, but releasing resources acquired inside
``aopen`` remains the plugin's responsibility.

Await :meth:`~nornir.core.inventory.Host.aclose_connection` or
:meth:`~nornir.core.inventory.Host.aclose_connections` when async-capable
connections may be present. Asynchronous cleanup closes a connection bound to
sync mode through its synchronous ``close`` and a connection bound to asyncio
mode through ``aclose``, so one call cleans up a mixed host. That synchronous
``close`` runs inline on the event loop and blocks it until it returns, like a
synchronous subtask. If an async close fails or is cancelled, Nornir
retains that cached connection and its metadata so cleanup can be retried. Bulk
cleanup, synchronous or asynchronous, attempts the remaining connections after
an error, logs each later error, and then raises the first one; the synchronous
:meth:`~nornir.core.inventory.Host.close_connections` therefore closes every
sync-bound connection before raising the mode error for an asyncio-bound one.
Cancellation of asynchronous cleanup propagates immediately. Retry failed
Nornir-level cleanup with ``on_failed=True``, or invoke host cleanup directly,
because the default Nornir selection excludes failed hosts.

Callers must serialize get, open, close, and connection use for a name while that
name is closing. Concurrent cleanup and use of the same connection are not
supported. Await closing before reusing or reopening the name.

Async-only reference plugin
---------------------------

This tested asyncio echo plugin demonstrates a stable declaration, native async
operations, serialized transport use, cleanup after partial opening, and
idempotent closing:

.. literalinclude:: ../../tests/plugins/connections/async_echo.py
   :language: python
   :linenos:
