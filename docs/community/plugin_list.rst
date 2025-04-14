Community Plugins
=================

.. _Community Plugins:

.. list-table:: Community Nornir Plugins
   :header-rows: 1
   :widths: 20 20 40 20


   * - Name
     - Plugin Types
     - Description
     - Maintainers

   * - `nornir_napalm <https://github.com/nornir-automation/nornir_napalm>`_
     - | tasks
       | connection
     - | Allows interacting with
       | devices using the `napalm <https://github.com/napalm-automation/napalm/>`_ library.
     - `dbarrosop <https://github.com/dbarrosop>`_

   * - `nornir_netmiko <https://github.com/ktbyers/nornir_netmiko>`_
     - | tasks
       | connection
     - | Allows interacting with
       | devices using the `netmiko <https://github.com/ktbyers/netmiko>`_ library.
     - `ktbyers <https://github.com/ktbyers>`_

   * - `nornir_netbox <https://github.com/wvandeun/nornir_netbox>`_
     - | inventory
     - | Nornir inventory plugin
       | for `NetBox <https://github.com/netbox-community/netbox>`_.
     - | `wvandeun <https://github.com/wvandeun>`_
       | `clay584 <https://github.com/clay584>`_

   * - `nornir_ansible <https://github.com/carlmontanari/nornir_ansible>`_
     - | inventory
     - | inventory plugin to use
       | Ansible inventories with Nornir.
     - `carlmontanari <https://github.com/carlmontanari>`_

   * - `nornir_scrapli <https://github.com/scrapli/nornir_scrapli>`_
     - | tasks
       | connection
     - | Allows interacting with
       | devices using the `scrapli <https://github.com/carlmontanari/scrapli>`_ library.
     - `carlmontanari <https://github.com/carlmontanari>`_

   * - `nornir_utils <https://github.com/nornir-automation/nornir_utils>`_
     - | tasks
       | processors
       | inventory
       | functions
     - | Collection of simple plugins
       | for Nornir: YAMLInventory,
       | print_result, print_title,
       | echo_data, write_file,
       | load_json, load_yaml,
       | and more.
     - `dbarrosop <https://github.com/dbarrosop>`_

   * - `nornir_jinja2 <https://github.com/nornir-automation/nornir_jinja2>`_
     - | tasks
     - | Collection of tasks to work
       | with jinja2 templates.
     - `dbarrosop <https://github.com/dbarrosop>`_

   * - `ipfabric_nornir <https://gitlab.com/ip-fabric/integrations/ipfabric_nornir>`_
     - | inventory
     - | IP Fabric vendor supported
       | Nornir inventory plugin
       | forked from `nornir_ipfabric <https://github.com/routetonull/nornir_ipfabric>`_.
     - `IP Fabric <https://gitlab.com/ip-fabric/integrations>`_

   * - `nornir_ipfabric <https://github.com/routetonull/nornir_ipfabric>`_
     - | inventory
     - | Nornir inventory plugin
       | for IP Fabric.
     - `routetonull <https://github.com/routetonull>`_

   * - `nornir_salt <https://github.com/dmulyalin/nornir-salt>`_
     - | runners
       | inventory
       | functions
     - | Collection of Nornir plugins:
       | QueueRunner, RetryRunner,
       | DictInventory, ResultSerializer,
       | FFun.
     - `dmulyalin <https://github.com/dmulyalin>`_

   * - `nornir_pyez <https://github.com/DataKnox/nornir_pyez>`_
     - | tasks
       | connection
     - | Allows interacting with
       | Juniper devices using
       | the `PyEZ <https://github.com/Juniper/py-junos-eznc>`_ library.
     - `DataKnox <https://github.com/DataKnox>`_

   * - `nornir_f5 <https://github.com/erjac77/nornir_f5>`_
     - | tasks
       | connection
     - | Collection of Nornir plugins
       | to interact with F5 systems
       | and deploy declaratives to F5
       | Automation Toolchain (ATC)
       | services like AS3, DO, and TS.
     - `erjac77 <https://github.com/erjac77>`_

   * - `nornir-nautobot <https://github.com/nautobot/nornir-nautobot>`_
     - | inventory
       | processors
       | tasks
     - | Collection of Nornir plugins
       | with interactions to Nautobot,
       | including inventory, processor,
       | and tasks.
     - `Network to Code <https://github.com/networktocode>`_

   * - `nornir-cli <https://github.com/timeforplanb123/nornir_cli>`_
     - | cli
     - | CLI tool based on Nornir,
       | Nornir Plugins and Click.
     - `timeforplanb123 <https://github.com/timeforplanb123>`_

   * - `nornir_routeros <https://github.com/devon-mar/nornir_routeros>`_
     - | tasks
       | connection
     - | RouterOS API connection plugin
       | and tasks for Nornir.
     - `devon-mar <https://github.com/devon-mar>`_

   * - `nornir_paramiko <https://github.com/devon-mar/nornir_paramiko>`_
     - | tasks
       | connection
     - | Paramiko connection plugin
       | and tasks adapted from
       | Nornir 2.5.0.
     - `devon-mar <https://github.com/devon-mar>`_

   * - `nornir_http <https://github.com/InfrastructureAsCode-ch/nornir_http>`_
     - | tasks
     - | Collection of tasks to
       | interact with HTTP Servers.
     - `ubaumann <https://github.com/ubaumann>`_

   * - `nornir_table_inventory <https://github.com/jiujing/nornir_table_inventory>`_
     - | inventory
     - | Allows managing inventory
       | by table file (CSV or Excel).
     - `jiujing <https://github.com/jiujing>`_

   * - `nornir_pyxl <https://github.com/h4ndzdatm0ld/nornir_pyxl>`_
     - | tasks
     - | Collection of tasks to easily
       | import Excel data into Nornir
       | workflows using OpenPyxl.
     - `h4ndzdatm0ld <https://github.com/h4ndzdatm0ld>`_

   * - `nornir_netconf <https://github.com/h4ndzdatm0ld/nornir_netconf>`_
     - | tasks
       | connection
     - | Collection of tasks and
       | connection plugin using
       | the `ncclient <https://github.com/ncclient/ncclient>`_ library to
       | interact with devices
       | over NETCONF.
     - `h4ndzdatm0ld <https://github.com/h4ndzdatm0ld>`_

   * - `nornir-sql <https://github.com/viktorkertesz/nornir_sql>`_
     - | inventory
     - | Use SQL database as
       | source of inventory.
     - `viktorkertesz <https://github.com/viktorkertesz>`_

   * - `nornir_csv <https://github.com/matman26/nornir_csv>`_
     - | inventory
     - | Dynamic CSV Inventory
       | plugin with support for
       | Groups, Defaults, and
       | Connection Options.
     - `matman26 <https://github.com/matman26>`_

   * - `nornir-rich <https://github.com/InfrastructureAsCode-ch/nornir_rich>`_
     - | functions
       | processors
     - | Collection of functions
       | and processors for generating
       | nice looking output with rich.
     - `ubaumann <https://github.com/ubaumann>`_

   * - `nornir_librenms <https://github.com/shamalawy/nornir-librenms>`_
     - | inventory
     - | Use LibreNMS as source of
       | inventory to generate hosts,
       | groups, and many attributes
       | like version, model, etc.
     - `shamalawy <https://github.com/shamalawy>`_

   * - `nornir_pyntc <https://github.com/networktocode/nornir-pyntc>`_
     - | tasks
       | connection
     - | Collection of tasks and
       | connection plugin using
       | the pyntc library to
       | interact with devices.
     - `Network to Code <https://github.com/networktocode>`_

   * - `nornir_pygnmi <https://github.com/akarneliuk/nornir_pygnmi>`_
     - | tasks
       | connection
     - | Collection of tasks and
       | connection plugin using
       | the `pygnmi <https://github.com/akarneliuk/pygnmi>`_ Python
       | library.
     - `akarneliuk <https://github.com/akarneliuk>`_

   * - `nornir_pyfgt <https://github.com/gt732/nornir_pyfgt>`_
     - | tasks
       | connection
     - | Collection of tasks and
       | connection plugin using
       | the `fortigate-api <https://github.com/vladimirs-git/fortigate-api>`_
       | library to interact with
       | Fortigate firewall devices.
     - `gt732 <https://github.com/gt732>`_

   * - `nornir_infrahub <https://github.com/opsmill/nornir-infrahub>`_
     - | inventory
       | tasks
     - | Nornir plugin for `Infrahub <https://github.com/opsmill/infrahub>`_.
     - `OpsMill <https://github.com/opsmill/>`_

   * - `nornir-nuts <https://github.com/network-unit-testing-system/nornir_nuts>`_
     - | runners
     - | Nornir plugins designed
       | for use with Nuts;
       | CachedThreaded Runner.
     - `nuts <https://github.com/network-unit-testing-system>`_

   * - `nornir-conditional-runner <https://github.com/InfrastructureAsCode-ch/nornir_conditional_runner>`_
     - | runners
     - | Nornir plugin
       | ConditionalRunner that
       | enforces concurrency
       | limits based on host groups
       | or custom condition groups.
     - `slinder <https://github.com/SimLi1333>`_
