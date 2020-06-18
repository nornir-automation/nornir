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
     - Plugin to use as Runner. Must be registered
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
     - kwargs to pass to the plugin
   * - **Type**
     - ``object``
   * - **Default**
     - ``{}``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_RUNNER_OPTIONS``

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
     - ``NORNIR_LOGGING_FILE``

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
