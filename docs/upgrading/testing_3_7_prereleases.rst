Testing the 3.7 pre-releases
############################

Nornir 3.7 adds three opt-in features:

* running ``async def`` tasks on your application's event loop with ``AsyncioRunner``,
* loading the inventory from an async application with ``AInitNornir``,
* following, cancelling and time-limiting long-running runs.

Pre-releases of 3.7, starting with 3.7.0a1, are published so that you can test these
features and your existing scripts before 3.7.0 is final. The new APIs can still change
until then, so do not use a pre-release in production automation.

Install a pre-release
=====================

``pip install nornir`` and ``pip install --upgrade nornir`` do not install a
pre-release. Request the version explicitly, in a separate virtual environment that also
contains the plugins your scripts use. The 3.7 pre-releases support Python 3.10 to 3.15.

.. code-block:: bash

    python -m venv .venv-nornir-3.7
    source .venv-nornir-3.7/bin/activate
    pip install "nornir==3.7.0a1"
    pip install nornir_utils nornir_netmiko   # replace with the plugins your scripts use
    python -c "import nornir; print(nornir.__version__)"

With uv, run ``uv pip install "nornir==3.7.0a1"`` instead. Check
`PyPI <https://pypi.org/project/nornir/#history>`_ for the latest pre-release.

1. Run your existing scripts unchanged
======================================

Existing scripts should keep working: ``ThreadedRunner`` is still the default runner, and
the synchronous plugin contracts are unchanged. Run your scripts and plugin test suites
against the pre-release and compare the results with 3.6.1. This step finds regressions,
which matter most before 3.7.0.

Four existing behaviours changed. Check whether your code relies on one of them:

* ``Nornir.run`` and ``Task.run`` raise ``AsyncTaskOnSyncRunError`` when given an
  ``async def`` task. Previously the coroutine was never awaited, its object was stored as
  the result and the host was reported as successful.
* A task that contains ``yield`` now runs, as a progress-reporting task. Previously its
  body never ran: the generator object was stored as the result and the host was reported
  as successful.
* ``InitNornir`` raises ``TransformFunctionNotSyncError`` before loading the inventory
  when the configured transform function is defined with ``async def``. Previously the
  transform function was never run and the hosts were left unchanged.
* ``Host.close_connections`` attempts to close every connection, raises the first error
  after the last attempt and logs each later error at ``ERROR`` level. Previously it
  stopped at the first connection it could not close. The connection errors also derive
  from ``ConnectionException``.

2. Try the new features
=======================

Each how-to guide linked below is a notebook whose output is checked in CI. The snippets
on this page use your own ``config.yaml`` and inventory.

Follow, stop and time-limit long-running runs
---------------------------------------------

A task reports progress by yielding ``PartialResult`` objects, and its ``return`` value is
still its final result. ``nr.stream()`` yields each event as it happens. ``nr.submit()``
starts the run in the background and returns a handle that yields each host's final
result as the host finishes, and that can cancel the run. Runners also accept a deadline
per host (``per_host_timeout``) and for the whole run (``timeout``).

This snippet runs on ``ThreadedRunner``, the default runner:

.. code-block:: python

    import time

    from nornir import InitNornir
    from nornir.core.task import PartialResult, Result, Task

    nr = InitNornir(config_file="config.yaml")


    def upgrade(task: Task):
        yield PartialResult(host=task.host, result="copying image", progress=0.5)
        time.sleep(0.1)  # replace with the real work
        return Result(host=task.host, result="done")


    for event in nr.stream(task=upgrade):
        print(type(event).__name__, event.host.name, event.result)

    FAIL_ON = next(iter(nr.inventory.hosts))


    def change(task: Task):
        for _ in range(20):
            task.checkpoint()  # cancellation and deadlines are delivered here
            time.sleep(0.05)
        if task.host.name == FAIL_ON:
            raise ValueError("rejected")
        return Result(host=task.host, result="applied")


    handle = nr.submit(task=change)
    for res in handle.results():
        if res.failed:
            handle.cancel()
            break
    for name, r in handle.result().items():
        print(name, type(r[0].exception).__name__ if r[0].failed else r[0].result)

What to check:

* Progress and results arrive in the order you expect for your devices.
* After ``handle.cancel()``, the hosts that were still running stop at their next
  checkpoint and carry ``TaskCancelledError``. Tasks built on blocking libraries should
  call ``task.checkpoint()`` between commands.
* A host that passes ``per_host_timeout`` carries ``TaskTimeoutError``, and the other
  hosts are not affected.

Read more:

* :doc:`../howto/long_running_tasks`
* The "Streaming, cancellation and deadlines" section of :doc:`../plugins/execution_model`,
  which includes a table of what each runner supports

Load the inventory and run ``async def`` tasks on the event loop
----------------------------------------------------------------

``nr = await AInitNornir(...)`` takes the same arguments as ``InitNornir`` and returns the
same ``Nornir`` object without blocking the event loop. Existing inventory plugins and
synchronous transform functions run in a worker thread. ``AsyncioRunner`` runs
``async def`` tasks on the caller's event loop, with at most ``num_workers`` hosts running
at the same time, and ``async with nr`` closes the connections asynchronously.

.. code-block:: python

    import asyncio

    from nornir import AInitNornir
    from nornir.core.task import Result, Task
    from nornir.plugins.runners import AsyncioRunner


    async def hello(task: Task) -> Result:
        await asyncio.sleep(0.1)  # replace with an awaited call to the device or an API
        return Result(host=task.host, result=f"hello from {task.host.name}")


    async def main() -> None:
        nr = await AInitNornir(config_file="config.yaml")
        nr = nr.with_runner(AsyncioRunner(num_workers=10))
        async with nr:
            results = await nr.arun(task=hello)
        for name, r in results.items():
            print(name, r[0].result)


    asyncio.run(main())

What to check:

* Your current inventory plugin loads with ``AInitNornir``. A plugin that must run in the
  main thread, for example to install a signal handler, fails with ``AInitNornir``.
* Your processors still work in an asyncio run. Processor hooks are synchronous and run on
  the event loop, so a hook that blocks also blocks every running task.

Read more:

* :doc:`../howto/async_inventory`
* :doc:`../howto/asyncio_runner`
* :doc:`../plugins/execution_model`

3. Test your plugins
====================

If you maintain a plugin, run its test suite against the pre-release first. Then, if your
plugin talks to devices or APIs through an asynchronous client, follow the guide for the
new contract:

* :doc:`../howto/writing_capability_connection_plugins`: connection plugins that support
  synchronous use, asyncio or both.
* :doc:`../howto/writing_capability_inventory_plugins`: inventory plugins that load
  synchronously, asynchronously or both. A plugin can keep its
  ``nornir.plugins.inventory`` entry point so that it still loads on older Nornir
  releases.

Send feedback
=============

Report what works and what does not on any of these channels:

* A comment on the proposal issue for the feature:
  `#1085 Async Runner <https://github.com/nornir-automation/nornir/issues/1085>`_,
  `#1086 Runner Enhancements <https://github.com/nornir-automation/nornir/issues/1086>`_ or
  `#1087 Async Inventory <https://github.com/nornir-automation/nornir/issues/1087>`_.
* A `new GitHub issue <https://github.com/nornir-automation/nornir/issues/new>`_ for a
  bug. Include the steps to reproduce it, the Nornir version, your Python version and your
  operating system.
* The ``#nornir`` channel in the `OpsMill Discord server <https://discord.gg/opsmill>`_,
  or the Nornir Slack channel in the
  `networktocode Slack team <https://networktocode.herokuapp.com/>`_.

The complete list of changes is in the :doc:`changelog <../changelog/index>`.
