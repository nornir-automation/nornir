



core
----

``num_workers``
_______________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Number of Nornir worker threads that are run at the same time by default
   * - **Type**
     - ``integer``
   * - **Default**
     - ``20``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_CORE_NUM_WORKERS``

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





inventory
---------

``plugin``
__________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Import path to inventory plugin
   * - **Type**
     - ``string``
   * - **Default**
     - ``nornir.plugins.inventory.simple.SimpleInventory``
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_INVENTORY_PLUGIN``

``options``
___________

.. list-table::
   :widths: 15 85

   * - **Description**
     - kwargs to pass to the inventory plugin
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
     - Path to transform function. The transform_function you provide will run against each host in the inventory
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

``file``
________

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





jinja2
------

``filters``
___________

.. list-table::
   :widths: 15 85

   * - **Description**
     - Path to callable returning jinja filters to be used
   * - **Type**
     - ``string``
   * - **Default**
     - 
   * - **Required**
     - ``False``
   * - **Environment Variable**
     - ``NORNIR_JINJA2_FILTERS``



