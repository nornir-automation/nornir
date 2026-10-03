---
title: Community plugins
---

# Community plugins

Nornir ships without device or protocol plugins. Everything that talks to a specific vendor or protocol lives in a separate package, and the list below is a non-exhaustive collection of them.

Wrote a plugin? Add it to this table with a pull request that edits [`docs/docs/community/plugin_list.md`](https://github.com/nornir-automation/nornir/blob/main/docs/docs/community/plugin_list.md).

| Name | Plugin Types | Description | Maintainers |
| --- | --- | --- | --- |
| [nornir_napalm](https://github.com/nornir-automation/nornir_napalm) | tasks<br />connection | Allows interacting with devices using the [napalm](https://github.com/napalm-automation/napalm/) library. | [dbarrosop](https://github.com/dbarrosop) |
| [nornir_netmiko](https://github.com/ktbyers/nornir_netmiko) | tasks<br />connection | Allows interacting with devices using the [netmiko](https://github.com/ktbyers/netmiko) library. | [ktbyers](https://github.com/ktbyers) |
| [nornir_netbox](https://github.com/wvandeun/nornir_netbox) | inventory | Nornir inventory plugin for [NetBox](https://github.com/netbox-community/netbox). | [wvandeun](https://github.com/wvandeun)<br />[clay584](https://github.com/clay584) |
| [nornir_ansible](https://github.com/carlmontanari/nornir_ansible) | inventory | inventory plugin to use Ansible inventories with Nornir. | [carlmontanari](https://github.com/carlmontanari) |
| [nornir_scrapli](https://github.com/scrapli/nornir_scrapli) | tasks<br />connection | Allows interacting with devices using the [scrapli](https://github.com/carlmontanari/scrapli) library. | [carlmontanari](https://github.com/carlmontanari) |
| [nornir_utils](https://github.com/nornir-automation/nornir_utils) | tasks<br />processors<br />inventory<br />functions | Collection of simple plugins for Nornir: YAMLInventory, print_result, print_title, echo_data, write_file, load_json, load_yaml, and more. | [dbarrosop](https://github.com/dbarrosop) |
| [nornir_jinja2](https://github.com/nornir-automation/nornir_jinja2) | tasks | Collection of tasks to work with jinja2 templates. | [dbarrosop](https://github.com/dbarrosop) |
| [ipfabric_nornir](https://gitlab.com/ip-fabric/integrations/ipfabric_nornir) | inventory | IP Fabric vendor supported Nornir inventory plugin forked from [nornir_ipfabric](https://github.com/routetonull/nornir_ipfabric). | [IP Fabric](https://gitlab.com/ip-fabric/integrations) |
| [nornir_ipfabric](https://github.com/routetonull/nornir_ipfabric) | inventory | Nornir inventory plugin for IP Fabric. | [routetonull](https://github.com/routetonull) |
| [nornir_salt](https://github.com/dmulyalin/nornir-salt) | runners<br />inventory<br />functions | Collection of Nornir plugins: QueueRunner, RetryRunner, DictInventory, ResultSerializer, FFun. | [dmulyalin](https://github.com/dmulyalin) |
| [nornir_pyez](https://github.com/DataKnox/nornir_pyez) | tasks<br />connection | Allows interacting with Juniper devices using the [PyEZ](https://github.com/Juniper/py-junos-eznc) library. | [DataKnox](https://github.com/DataKnox) |
| [nornir_f5](https://github.com/erjac77/nornir_f5) | tasks<br />connection | Collection of Nornir plugins to interact with F5 systems and deploy declaratives to F5 Automation Toolchain (ATC) services like AS3, DO, and TS. | [erjac77](https://github.com/erjac77) |
| [nornir-nautobot](https://github.com/nautobot/nornir-nautobot) | inventory<br />processors<br />tasks | Collection of Nornir plugins with interactions to Nautobot, including inventory, processor, and tasks. | [Network to Code](https://github.com/networktocode) |
| [nornir-cli](https://github.com/timeforplanb123/nornir_cli) | cli | CLI tool based on Nornir, Nornir Plugins and Click. | [timeforplanb123](https://github.com/timeforplanb123) |
| [nornir_routeros](https://github.com/devon-mar/nornir_routeros) | tasks<br />connection | RouterOS API connection plugin and tasks for Nornir. | [devon-mar](https://github.com/devon-mar) |
| [nornir_paramiko](https://github.com/devon-mar/nornir_paramiko) | tasks<br />connection | Paramiko connection plugin and tasks adapted from Nornir 2.5.0. | [devon-mar](https://github.com/devon-mar) |
| [nornir_http](https://github.com/InfrastructureAsCode-ch/nornir_http) | tasks | Collection of tasks to interact with HTTP Servers. | [ubaumann](https://github.com/ubaumann) |
| [nornir_table_inventory](https://github.com/jiujing/nornir_table_inventory) | inventory | Allows managing inventory by table file (CSV or Excel). | [jiujing](https://github.com/jiujing) |
| [nornir_pyxl](https://github.com/h4ndzdatm0ld/nornir_pyxl) | tasks | Collection of tasks to easily import Excel data into Nornir workflows using OpenPyxl. | [h4ndzdatm0ld](https://github.com/h4ndzdatm0ld) |
| [nornir_netconf](https://github.com/h4ndzdatm0ld/nornir_netconf) | tasks<br />connection | Collection of tasks and connection plugin using the [ncclient](https://github.com/ncclient/ncclient) library to interact with devices over NETCONF. | [h4ndzdatm0ld](https://github.com/h4ndzdatm0ld) |
| [nornir-sql](https://github.com/viktorkertesz/nornir_sql) | inventory | Use SQL database as source of inventory. | [viktorkertesz](https://github.com/viktorkertesz) |
| [nornir_csv](https://github.com/matman26/nornir_csv) | inventory | Dynamic CSV Inventory plugin with support for Groups, Defaults, and Connection Options. | [matman26](https://github.com/matman26) |
| [nornir-rich](https://github.com/InfrastructureAsCode-ch/nornir_rich) | functions<br />processors | Collection of functions and processors for generating nice looking output with rich. | [ubaumann](https://github.com/ubaumann) |
| [nornir_librenms](https://github.com/shamalawy/nornir-librenms) | inventory | Use LibreNMS as source of inventory to generate hosts, groups, and many attributes like version, model, etc. | [shamalawy](https://github.com/shamalawy) |
| [nornir_pyntc](https://github.com/networktocode/nornir-pyntc) | tasks<br />connection | Collection of tasks and connection plugin using the pyntc library to interact with devices. | [Network to Code](https://github.com/networktocode) |
| [nornir_pygnmi](https://github.com/akarneliuk/nornir_pygnmi) | tasks<br />connection | Collection of tasks and connection plugin using the [pygnmi](https://github.com/akarneliuk/pygnmi) Python library. | [akarneliuk](https://github.com/akarneliuk) |
| [nornir_pyfgt](https://github.com/gt732/nornir_pyfgt) | tasks<br />connection | Collection of tasks and connection plugin using the [fortigate-api](https://github.com/vladimirs-git/fortigate-api) library to interact with Fortigate firewall devices. | [gt732](https://github.com/gt732) |
| [nornir_infrahub](https://github.com/opsmill/nornir-infrahub) | inventory<br />tasks | Nornir plugin for [Infrahub](https://github.com/opsmill/infrahub). | [OpsMill](https://github.com/opsmill/) |
| [nornir-nuts](https://github.com/network-unit-testing-system/nornir_nuts) | runners | Nornir plugins designed for use with Nuts; CachedThreaded Runner. | [nuts](https://github.com/network-unit-testing-system) |
| [nornir-conditional-runner](https://github.com/InfrastructureAsCode-ch/nornir_conditional_runner) | runners | Nornir plugin ConditionalRunner that enforces concurrency limits based on host groups or custom condition groups. | [slinder](https://github.com/SimLi1333) |
