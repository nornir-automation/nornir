.. nornir documentation master file, created by
   sphinx-quickstart on Sun Nov 19 10:41:40 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to nornir's documentation!
===================================

Nornir is an automation framework written in python to be used with python. Most automation
frameworks hide the language they are written in by using some cumbersome pseudo-language
which usually is almost Turing complete but lacks tooling to debug and troubleshoot. Integrating
with other systems is also usually quite hard as they usually have complex APIs if any at all.
Some of the other common problems of those pseudo-languages is that are usually quite bad
at dealing with data and re-usability is limited.

Nornir aims to solve those problems by providing a pure python framework. Just imagine Nornir
as the Flask of automation. Nornir will take care of dealing with the inventory where you
have your host information, it will take care of dispatching the tasks to your devices and
will provide a common framework to write "plugins".

How the documentation is structured
===================================

- The :doc:`Tutorial </tutorials/intro/index>` is a great place to start for new users.
- :doc:`How-to guides </howto/index>` aim to solve a specific use case or answer key problems. These guides can be more advanced than the tutorial and can assume some knowledge about how Nornir and related technologies work.
- :doc:`Reference guides </ref/index>` contains the API reference for Nornir and describe the core functions.
- :doc:`Configuration </configuration/index>` describe the configuration parameters of Nornir and their default settings.
- :doc:`Plugins </plugins/index>` shows which tasks and functions are available out of the box with Nornir and describe how they work.

Is something missing from the documentation? Please open an issue and `tell us what you are missing <https://github.com/nornir-automation/nornir/issues>`_ or `open a pull request <https://github.com/nornir-automation/nornir/pulls>`_ and suggest an improvement.

A first glance
==============

Here is an example on how to quickly build a runbook leveraging Nornir to retrieve information from the network::

    from nornir import InitNornir
    from nornir.plugins.functions.text import print_result
    from nornir.plugins.tasks.networking import napalm_get

    nr = InitNornir(
        config_file="nornir.yaml", dry_run=True
    )

    results = nr.run(
        task=napalm_get, getters=["facts", "interfaces"]
    )
    print_result(results)

You can find this and other examples `here <https://github.com/nornir-automation/nornir-tools/>`_.

Contents
========

.. toctree::
   :maxdepth: 1

   Home <self>
   Tutorials <tutorials/intro/index>
   Howto <howto/index>
   configuration/index
   plugins/index
   ref/index
   upgrading/index
   Contribute <contributing/index>


Indices and tables

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
