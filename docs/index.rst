.. brigade documentation master file, created by
   sphinx-quickstart on Sun Nov 19 10:41:40 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to brigade's documentation!
===================================

Brigade is an automation framework written in python to be used with python. Most automation
frameworks hide the language they are written in by using some cumbersome pseudo-language
which usually is almost Turing complete but lacks tooling to debug and troubleshoot. Integrating
with other systems is also usually quite hard as they usually have complex APIs if any at all.
Some of the other common problems of those pseudo-languages is that are usually quite bad
at dealing with data and re-usability is limited.

Brigade aims to solve those problems by providing a pure python framework. Just imagine Brigade
as the Flask of automation. Brigade will take care of dealing with the inventory where you
have your host information, it will take care of dispatching the tasks to your devices and
will provide a common framework to write "plugins".

How the documentation is structured
===================================

- The :doc:`Tutorial </tutorials/intro/index>` is a great place to start for new users.
- :doc:`How-to guides </howto/index>` aim to solve a specific use case or answer key problems. These guides can be more advanced than the tutorial and can assume some knowledge about how Brigade and related technologies work.
- :doc:`Reference guides </ref/index>` contains the API reference for Brigade and describe the core functions and plugins.

Is something missing from the documentation? Please open an issue and `tell us what you are missing <https://github.com/brigade-automation/brigade/issues>`_ or `open a pull request <https://github.com/brigade-automation/brigade/pulls>`_ and suggest an improvement.

A first glance
==============

Here is an example on how to quickly build a cli tool leveraging on Brigade and click::

    from brigade.core import Brigade
    from brigade.plugins import tasks
    from brigade.plugins.inventory.simple import SimpleInventory

    import click


    def get_facts(task, facts):
        r = tasks.napalm_get_facts(task, facts)
        print(task.host.name)
        print("============")
        print(r["result"])
        print()


    @click.command()
    @click.argument('site')
    @click.argument('role')
    @click.argument('facts')
    def main(site, role, facts):
        brigade = Brigade(
            inventory=SimpleInventory("hosts.yaml", "groups.yaml"),
            dry_run=True,
        )

        filtered = brigade.filter(site=site, role=role)
        filtered.run(task=get_facts,
                     facts=facts)


    if __name__ == "__main__":
        main()

That you can use like:

* give me general information from all my leafs in bma::

    $ ./get_facts_role.py bma leaf get_facts
    switch00.bma
    ============
    {'hostname': 'switch00.bma', 'fqdn': 'switch00.bma.bma.acme.com', 'vendor': 'Arista', 'model': 'vEOS', 'serial_number': '', 'os_version': '4.17.5M-4414219.4175M', 'uptime': 80747, 'interface_list': ['Ethernet1', 'Ethernet2', 'Management1']}
    
    switch01.bma
    ============
    {'vendor': 'Juniper', 'model': 'FIREFLY-PERIMETER', 'serial_number': 'a7defdc362ff', 'os_version': '12.1X47-D20.7', 'hostname': 'switch01.bma', 'fqdn': 'switch01.bma.bma.acme.com', 'uptime': 80644, 'interface_list': ['ge-0/0/0', 'gr-0/0/0', 'ip-0/0/0', 'lsq-0/0/0', 'lt-0/0/0', 'mt-0/0/0', 'sp-0/0/0', 'ge-0/0/1', 'ge-0/0/2', '.local.', 'dsc', 'gre', 'ipip', 'irb', 'lo0', 'lsi', 'mtun', 'pimd', 'pime', 'pp0', 'ppd0', 'ppe0', 'st0', 'tap', 'vlan']}

* give me interface information from all my leafs in cmh::

    $ ./get_facts_role.py cmh leaf interfaces
    switch00.cmh
    ============
    {'Ethernet2': {'is_up': False, 'is_enabled': False, 'description': 'Another interface in bma', 'last_flapped': 1511034159.0400283, 'speed': 0, 'mac_address': '08:00:27:AB:42:B6'}, 'Management1': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 1511033376.7964902, 'speed': 1000, 'mac_address': '08:00:27:47:87:83'}, 'Ethernet1': {'is_up': True, 'is_enabled': True, 'description': 'An Interface in bma', 'last_flapped': 1511033362.0303102, 'speed': 0, 'mac_address': '08:00:27:2D:F4:5A'}}
    
    switch01.cmh
    ============
    {'ge-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 80603.0, 'mac_address': '08:00:27:AA:8C:76', 'speed': 1000}, 'gr-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'ip-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'lsq-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 80604.0, 'mac_address': 'None', 'speed': -1}, 'lt-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': '02:96:14:8C:76:B3', 'speed': 800}, 'mt-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'sp-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 80604.0, 'mac_address': 'Unspecified', 'speed': 800}, 'ge-0/0/1': {'is_up': True, 'is_enabled': True, 'description': 'An Interface in bma', 'last_flapped': 80604.0, 'mac_address': '08:00:27:FB:F0:FC', 'speed': 1000}, 'ge-0/0/2': {'is_up': False, 'is_enabled': False, 'description': 'Another interface in bma', 'last_flapped': 79892.0, 'mac_address': '08:00:27:32:60:54', 'speed': 1000}, '.local.': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'dsc': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'gre': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'ipip': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'irb': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': '4C:96:14:8C:76:B0', 'speed': -1}, 'lo0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'lsi': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'mtun': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pimd': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pime': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pp0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'ppd0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'ppe0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'st0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'tap': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'vlan': {'is_up': False, 'is_enabled': True, 'description': '', 'last_flapped': 80614.0, 'mac_address': '00:00:00:00:00:00', 'speed': 1000}}

Contents
========

.. toctree::
   :maxdepth: 1

   Home <self>
   Tutorials <tutorials/intro/index>
   Howto <howto/index>
   ref/index


Indices and tables

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
