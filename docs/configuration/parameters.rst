core
----

``raise_on_error``
__________________

.. list-table::
   :widths: 15 85

   * - **Description**
     - If set to ``True``, (:obj:`nornir.core.Nornir.run`) method of will raise exception :obj:`nornir.core.exceptions.NornirExecutionError` if at least a host failed
   * - **Type**
     - ``boolean``
   * - **Default**
     - ``False``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_CORE_RAISE_ON_ERROR``

runner
---------

``plugin``
__________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Registered runner plugin to use. ``Threaded`` runs synchronous tasks in a thread
       pool and remains the default. Select ``asyncio`` explicitly to run native
       coroutine tasks with ``await nr.arun(...)``.
   * - **Type**
     - ``string``
   * - **Default**
     - ``Threaded``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_RUNNER_PLUGIN``

``options``
___________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Keyword arguments passed to the runner plugin. ``Threaded`` and ``asyncio`` accept
       ``num_workers``, the maximum number of hosts in flight; both default to ``20``.
       For ``asyncio``, ``num_workers`` must be a positive integer. ``Serial`` has no
       options.
   * - **Type**
     - ``object``
   * - **Default**
     - ``{}``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_RUNNER_OPTIONS``

For example, select the asyncio runner and allow up to 100 concurrent hosts::

    runner:
      plugin: asyncio
      options:
        num_workers: 100

The asyncio runner uses the caller's event loop and requires ``async def`` tasks invoked
through ``await nr.arun(...)``. Omitting the runner configuration continues to select
``Threaded``. See :doc:`../plugins/execution_model` and the executed
:doc:`../howto/asyncio_runner` notebook.

inventory
---------

``plugin``
__________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Plugin to use. Must be registered
   * - **Type**
     - ``string``
   * - **Default**
     - ``SimpleInventory``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_INVENTORY_PLUGIN``

``options``
___________

.. list-table::
   :widths: 15 85

   * - **Description**
     - kwargs to pass to the plugin
   * - **Type**
     - ``object``
   * - **Default**
     - ``{}``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_INVENTORY_OPTIONS``

``transform_function``
______________________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Plugin to use. Must be registered
   * - **Type**
     - ``string``
   * - **Default**
     - 
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_INVENTORY_TRANSFORM_FUNCTION``

``transform_function_options``
______________________________

.. list-table::
   :widths: 15 85

   * - **Description**
     - kwargs to pass to the transform_function
   * - **Type**
     - ``object``
   * - **Default**
     - ``{}``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_INVENTORY_TRANSFORM_FUNCTION_OPTIONS``





ssh
---

``config_file``
_______________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Path to ssh configuration file
   * - **Type**
     - ``string``
   * - **Default**
     - ``~/.ssh/config``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_SSH_CONFIG_FILE``





logging
-------

``enabled``
___________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Whether to configure logging or not
   * - **Type**
     - ``boolean``
   * - **Default**
     - ``None``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_LOGGING_ENABLED``

``level``
_________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Logging level
   * - **Type**
     - ``string``
   * - **Default**
     - ``INFO``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_LOGGING_LEVEL``

``log_file``
____________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Logging file
   * - **Type**
     - ``string``
   * - **Default**
     - ``nornir.log``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_LOGGING_LOG_FILE``

``format``
__________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Logging format
   * - **Type**
     - ``string``
   * - **Default**
     - ``%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_LOGGING_FORMAT``

``to_console``
______________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Whether to log to console or not
   * - **Type**
     - ``boolean``
   * - **Default**
     - ``False``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_LOGGING_TO_CONSOLE``

``loggers``
___________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Loggers to configure
   * - **Type**
     - ``array``
   * - **Default**
     - ``['nornir']``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_LOGGING_LOGGERS``
