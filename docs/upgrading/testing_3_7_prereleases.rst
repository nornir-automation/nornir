Testing the 3.7 pre-releases
############################

Nornir 3.7 adds three features. All three are optional:

* Follow the progress of a run, cancel it, and set time limits. This works with
  ``ThreadedRunner`` (the default runner), ``SerialRunner`` and ``AsyncioRunner``. You do
  not need any ``async`` code.
* Run ``async def`` tasks on the event loop of your application with ``AsyncioRunner``.
* Load the inventory from an async application with ``AInitNornir``.

The pre-releases, starting with 3.7.0a1, let you test these features and your existing
scripts before 3.7.0 is final. The new APIs can still change, so do not use a pre-release
in production.

Install a pre-release
=====================

``pip install --upgrade nornir`` does not install a pre-release. You must give the
version. Use a separate virtual environment, and install the plugins that your scripts
use. The 3.7 pre-releases support Python 3.10 to 3.15.

.. code-block:: bash

    python -m venv .venv-nornir-3.7
    source .venv-nornir-3.7/bin/activate
    pip install "nornir==3.7.0a1"
    pip install nornir_utils nornir_netmiko   # replace with the plugins your scripts use
    python -c "import nornir; print(nornir.__version__)"

With uv, run ``uv pip install "nornir==3.7.0a1"``. The latest pre-release is listed on
`PyPI <https://pypi.org/project/nornir/#history>`_.

1. Run your existing scripts
============================

Run your scripts and the tests of your plugins without changing them, and compare the
results with 3.6.1. This is the most useful test: everything that works with 3.6.1 should
still work. ``ThreadedRunner`` is still the default runner, and the existing plugin
contracts did not change.

Four behaviours changed. Check if your code depends on one of them:

* ``Nornir.run`` and ``Task.run`` now raise ``AsyncTaskOnSyncRunError`` for an
  ``async def`` task. Before, the task did not run, but the host was reported as
  successful.
* A task that contains ``yield`` now runs. Before, the task did not run, but the host was
  reported as successful.
* ``InitNornir`` now raises ``TransformFunctionNotSyncError`` for a transform function
  defined with ``async def``. Before, the transform function did not run.
* ``Host.close_connections`` now tries to close every connection, then raises the first
  error. Before, it stopped at the first connection that it could not close.

2. Try the new features
=======================

The examples below use your own ``config.yaml`` and inventory.

Follow, stop and time-limit runs with your current runner
---------------------------------------------------------

These features work with normal synchronous tasks. You do not need ``async def`` tasks or
a different runner.

* **Progress:** a task reports progress with ``yield PartialResult(...)``. Its ``return``
  value is still the final result.
* **Follow a run:** ``nr.stream()`` gives you each event when it happens.
* **Run in the background:** ``nr.submit()`` returns a handle. Use the handle to read the
  result of each host when the host finishes, and to cancel the run.
* **Time limits:** set ``per_host_timeout`` (for each host) or ``timeout`` (for the whole
  run) on the runner, in seconds. You can also set them under ``runner.options`` in the
  configuration file.

What each runner supports:

.. list-table::
   :header-rows: 1

   * - Runner
     - Follow a run
     - Run in the background
     - When a cancellation or a time limit stops a task
   * - ``ThreadedRunner`` (default)
     - ``stream``
     - ``submit``
     - at the next checkpoint
   * - ``SerialRunner``
     - ``stream``
     - not supported
     - at the next checkpoint
   * - ``AsyncioRunner``
     - ``astream``
     - ``asubmit``
     - at the call that the task is awaiting

A checkpoint is a call to ``task.checkpoint()``, a ``yield``, or the start of a subtask.

This example uses synchronous tasks. The second part uses ``submit``, so it needs
``ThreadedRunner``:

.. code-block:: python

    import time

    from nornir import InitNornir
    from nornir.core.task import PartialResult, Result, Task

    nr = InitNornir(config_file="config.yaml")


    def upgrade(task: Task):
        yield PartialResult(host=task.host, result="copying image", progress=0.5)
        time.sleep(0.1)  # replace with the real work
        return Result(host=task.host, result="done")


    # Part 1: follow the run
    for event in nr.stream(task=upgrade):
        print(type(event).__name__, event.host.name, event.result)

    FAIL_ON = next(iter(nr.inventory.hosts))


    def change(task: Task):
        for _ in range(20):
            task.checkpoint()  # a cancellation or a time limit stops the task here
            time.sleep(0.05)
        if task.host.name == FAIL_ON:
            raise ValueError("rejected")
        return Result(host=task.host, result="applied")


    # Part 2: cancel the run when one host fails
    handle = nr.submit(task=change)
    for res in handle.results():
        if res.failed:
            handle.cancel()
            break
    for name, r in handle.result().items():
        print(name, type(r[0].exception).__name__ if r[0].failed else r[0].result)

What to check:

* After ``handle.cancel()``, the hosts that were still running stop at their next
  checkpoint. Their result contains ``TaskCancelledError``.
* A host that takes longer than ``per_host_timeout`` gets ``TaskTimeoutError``. The other
  hosts are not affected.
* If your tasks use a blocking library, add ``task.checkpoint()`` between commands and
  check that the task stops there.

Read more: :doc:`../howto/long_running_tasks` and :doc:`../plugins/execution_model`.

Load the inventory and run ``async def`` tasks on the event loop
----------------------------------------------------------------

* ``AInitNornir`` takes the same arguments as ``InitNornir`` and returns the same
  ``Nornir`` object. It does not block the event loop. Your current inventory plugin
  works with it.
* ``AsyncioRunner`` runs ``async def`` tasks on your event loop. ``num_workers`` is the
  maximum number of hosts that run at the same time.
* ``async with nr`` closes the connections when the block ends.

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

* Your inventory plugin loads with ``AInitNornir``. A plugin that must run in the main
  thread does not work with ``AInitNornir``. Use ``InitNornir`` for it.
* Your processors still work. Processor hooks are synchronous and run on the event loop,
  so a slow hook also stops all the running tasks until it returns.

Read more: :doc:`../howto/async_inventory`, :doc:`../howto/asyncio_runner` and
:doc:`../plugins/execution_model`.

3. Test your plugins
====================

If you maintain a plugin, first run its tests with the pre-release. If your plugin uses
an asynchronous client, you can also add async support with the new plugin contracts:

* Connection plugins: :doc:`../howto/writing_capability_connection_plugins`
* Inventory plugins: :doc:`../howto/writing_capability_inventory_plugins`

Send feedback
=============

Tell us what works and what does not:

* Comment on the issue of the feature:
  `#1085 Async Runner <https://github.com/nornir-automation/nornir/issues/1085>`_,
  `#1086 Runner Enhancements <https://github.com/nornir-automation/nornir/issues/1086>`_ or
  `#1087 Async Inventory <https://github.com/nornir-automation/nornir/issues/1087>`_.
* Open a `new issue <https://github.com/nornir-automation/nornir/issues/new>`_ for a bug.
  Include the steps to reproduce it, and your Nornir and Python versions.
* Write in the ``#nornir`` channel of the
  `OpsMill Discord server <https://discord.gg/opsmill>`_ or in the
  `networktocode Slack team <https://networktocode.herokuapp.com/>`_.

The :doc:`changelog <../changelog/index>` has the complete list of changes.
