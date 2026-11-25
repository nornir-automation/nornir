Testing the 3.7 pre-releases
############################

Nornir 3.7 adds five features. All five are optional:

* Read typed results. Your type checker and your editor know the type of the result of a
  task from the return annotation of the task.
* Run one action on hosts of different vendors with an Operation. Each host runs the task
  registered for its platform, and the result of each host has the same type.
* Follow the progress of a run, cancel it, and set time limits. This works with
  ``ThreadedRunner`` (the default runner), ``SerialRunner`` and ``AsyncioRunner``. You do
  not need any ``async`` code.
* Run ``async def`` tasks on the event loop of your application with ``AsyncioRunner``.
* Load the inventory from an async application with ``AInitNornir``.

The pre-releases let you test these features and your existing scripts before 3.7.0 is
final. Typed results and Operations are new in 3.7.0b1. The other three features were
already in 3.7.0a1. The new APIs can still change, so do not use a pre-release
in production.

Install a pre-release
=====================

``pip install --upgrade nornir`` does not install a pre-release. You must give the
version. Use a separate virtual environment, and install the plugins that your scripts
use. The 3.7 pre-releases support Python 3.10 to 3.15.

.. code-block:: bash

    python -m venv .venv-nornir-3.7
    source .venv-nornir-3.7/bin/activate
    pip install "nornir==3.7.0b1"
    pip install nornir_utils nornir_netmiko   # replace with the plugins your scripts use
    python -c "import nornir; print(nornir.__version__)"

With uv, run ``uv pip install "nornir==3.7.0b1"``. The latest pre-release is listed on
`PyPI <https://pypi.org/project/nornir/#history>`_.

Plugins that use the new APIs
=============================

Most plugins do not use the new async APIs yet. Two plugins have a pre-release version
that does. Use them to test the async features against real systems. If you write
plugins, you can also read them as examples.

* **nornir-scrapli**, to run async tasks on network devices. It adds async versions of
  the Scrapli CLI and Scrapli-Cfg tasks, and one connection plugin that supports both
  sync and asyncio. NETCONF is not covered. See
  `nornir_scrapli pull request #179 <https://github.com/scrapli/nornir_scrapli/pull/179>`_.
* **nornir-infrahub**, to load the inventory with ``AInitNornir``. It adds the
  ``InfrahubAsyncInventory`` plugin and async versions of its tasks. The existing
  ``InfrahubInventory`` plugin does not change. See
  `nornir-infrahub pull request #106 <https://github.com/opsmill/nornir-infrahub/pull/106>`_.

Like Nornir, these pre-releases are installed only when you give the version:

.. code-block:: bash

    pip install "nornir-scrapli[asyncio]==1.6.0a1"
    pip install "nornir-infrahub==1.3.0a1"

The ``asyncio`` extra of nornir-scrapli installs ``asyncssh``, which the async
connections use by default.

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

Run your type checker
---------------------

If you check your scripts or your plugins with mypy, Pyright or ty, run the type checker
again with the pre-release. Nothing changes when the code runs, but the type checker now
knows the type of the results, so it can report errors in code that passed with 3.6.1.
mypy 2.x is recommended.

Three cases need a change in your code:

* A variable that holds the runs of tasks with different return types. Annotate it with
  ``AggregatedResult``, for example ``result: AggregatedResult = nr.run(task=backup)``.
* Code that reads a field that the result type does not have. The type checker reports
  it. Before, the result was ``Any``, so every field was accepted.
* A ``Result`` annotation without a type, such as ``-> Result``, with an older type
  checker in strict mode. The type checker reports a missing type parameter. Use a type
  checker that supports type variable defaults (PEP 696), or write ``Result[Any]``.

2. Try the new features
=======================

The examples below use your own ``config.yaml`` and inventory.

Read typed results
------------------

* Give your task a return annotation: ``Result[T]``, or a plain type such as ``str``.
* ``nr.run()`` then returns ``AggregatedResult[T]``, and ``multi.result`` has the type
  ``T``. ``Task.run()``, ``stream()``, ``submit()`` and the async methods work the same
  way.
* A task annotated with ``Result`` without a type, a task without a return annotation,
  and a task that contains ``yield`` keep the type ``Any``.

.. code-block:: python

    from dataclasses import dataclass

    from nornir import InitNornir
    from nornir.core.task import Result, Task

    nr = InitNornir(config_file="config.yaml")


    @dataclass
    class Facts:
        hostname: str
        platform: str


    def get_facts(task: Task) -> Result[Facts]:
        facts = Facts(hostname=task.host.hostname or "", platform=task.host.platform or "")
        return Result(host=task.host, result=facts)


    results = nr.run(task=get_facts)
    for name, multi in results.items():
        if not multi.failed:
            print(name, multi.result.platform)

What to check:

* Your editor completes the fields of ``multi.result``, here ``hostname`` and
  ``platform``.
* Change ``multi.result.platform`` to ``multi.result.platfrom`` and run your type
  checker. It reports the error.
* The type is correct only for a host that succeeded. For a failed host, ``multi.result``
  contains the error text, so check ``multi.failed`` first.
* The type checker results of your existing tasks. Tell us when a type is wrong, or when
  code that is correct is reported as an error.

Read more: the "Typing the results" section of :doc:`../tutorial/task_results`.

Run one action across vendors with Operations
---------------------------------------------

* An Operation is a class with a ``name``, an input model and an output model. A
  dataclass or a Pydantic model works as a model.
* An implementation is a normal task for one platform and one connection. It receives
  the input as ``params`` and returns the output model.
* ``nr.run_operation()`` runs, on each host, the task registered for the platform of the
  host. ``results()`` gives the final result of each host.
* ``nr.submit_operation()``, ``nr.arun_operation()`` and ``nr.asubmit_operation()``
  follow the rules of ``submit``, ``astream`` and ``asubmit``.

In this example, replace ``ios`` with a platform of your inventory, and ``netmiko`` with
the connection that your task uses:

.. code-block:: python

    from dataclasses import dataclass

    from nornir import InitNornir
    from nornir.core.operations import Operation, OperationRegistry
    from nornir.core.task import Task

    nr = InitNornir(config_file="config.yaml")


    @dataclass
    class GetVersionInput:
        detail: bool = False


    @dataclass
    class GetVersionOutput:
        version: str


    class GetVersion(Operation[GetVersionInput, GetVersionOutput]):
        name = "get_version"


    def ios_get_version(task: Task, params: GetVersionInput) -> GetVersionOutput:
        return GetVersionOutput(version="17.9.4")  # replace with a call to the device


    OperationRegistry.register(
        operation="get_version", platform="ios", connection="netmiko", task=ios_get_version
    )

    stream = nr.run_operation(GetVersion, GetVersionInput(), connection="netmiko")
    for res in stream.results():
        if res.failed:
            print(res.host, "FAILED:", res.exception)
        else:
            print(res.host, res.result.version)

What to check:

* The hosts of the platform that you registered return a ``GetVersionOutput``. The type
  checker types ``res.result.version`` as ``str``.
* A host of a platform without a registered task fails with
  ``OperationNotRegisteredError``. The other hosts are not affected.
* A wrong field name in the input, such as ``nr.run_operation(GetVersion, {"detial":
  True}, connection="netmiko")``, raises ``OperationInputError`` before any host starts.
* If you set ``core.operation_connection`` in the configuration file, you do not need
  ``connection=`` in each call.
* If you write plugins, declare your tasks in the ``nornir.plugins.operation_tasks``
  entry-point group, and check that ``OperationRegistry.operations()`` lists them.

Read more: :doc:`../howto/operations`.

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

If you maintain a plugin, first run its tests and its type checker with the pre-release.
Add a return annotation to your tasks, such as ``Result[str]``, so that your users get
typed results. To implement an Operation, see :doc:`../howto/operations`.

If your plugin uses an asynchronous client, you can also add async support with the new
plugin contracts:

* Connection plugins: :doc:`../howto/writing_capability_connection_plugins`
* Inventory plugins: :doc:`../howto/writing_capability_inventory_plugins`

The nornir-scrapli and nornir-infrahub pre-releases listed in
`Plugins that use the new APIs`_ show what these changes look like in a real plugin.

Send feedback
=============

Tell us what works and what does not:

* Comment on the issue of the feature:
  `#1085 Async Runner <https://github.com/nornir-automation/nornir/issues/1085>`_,
  `#1086 Runner Enhancements <https://github.com/nornir-automation/nornir/issues/1086>`_,
  `#1087 Async Inventory <https://github.com/nornir-automation/nornir/issues/1087>`_ or
  `#1089 Operations <https://github.com/nornir-automation/nornir/issues/1089>`_.
  For typed results, comment on
  `pull request #1129 <https://github.com/nornir-automation/nornir/pull/1129>`_.
* Open a `new issue <https://github.com/nornir-automation/nornir/issues/new>`_ for a bug.
  Include the steps to reproduce it, and your Nornir and Python versions.
* Write in the ``#nornir`` channel of the
  `OpsMill Discord server <https://discord.gg/opsmill>`_ or in the
  `networktocode Slack team <https://networktocode.herokuapp.com/>`_.

The :doc:`changelog <../changelog/index>` has the complete list of changes.
