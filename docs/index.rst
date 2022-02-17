Welcome to nornir's documentation!
===================================

.. image:: _static/logo/nornir_logo_02.jpg
   :height: 500px
   :width: 500px

Nornir is an automation framework written in python to be used with python. Most automation
frameworks hide the language they are written in by using some cumbersome pseudo-language
which usually is almost Turing complete, but lacks tooling to debug and troubleshoot. Integrating
with other systems is also usually quite hard as they usually have complex APIs if any at all.
Some of the other common problems of those pseudo-languages is that are usually quite bad
at dealing with data and re-usability is limited.

Nornir aims to solve those problems by providing a pure python framework. Just imagine Nornir
as the Flask of automation. Nornir will take care of dealing with the inventory where you
have your host information, it will take care of dispatching the tasks to your devices and
will provide a common framework to write "plugins".

Nornir requires Python 3.7 or higher to be installed.

How the documentation is structured
===================================

- The :doc:`Tutorial <tutorial/index>` is a great place to start for new users.
- :doc:`How-to guides <howto/index>` aim to solve a specific use case or answer key problems. These guides can be more advanced than the tutorial and can assume some knowledge about how Nornir and related technologies work.
- :doc:`The API section <api/index>` contains the API reference for Nornir and describe the core functions.
- :doc:`Configuration <configuration/index>` describe the configuration parameters of Nornir and their default settings.
- `nornir.tech <https://nornir.tech/nornir/plugins/>`_ is a good place to find plugins for nornir

Is something missing from the documentation? Please open an issue and `tell us what you are missing <https://github.com/nornir-automation/nornir/issues>`_ or `open a pull request <https://github.com/nornir-automation/nornir/pulls>`_ and suggest an improvement.

A first glance
==============

Here is an example on how to quickly build a runbook leveraging Nornir to retrieve information from the network::

    from nornir import InitNornir
    from nornir_utils.plugins.functions import print_result
    from nornir_napalm.plugins.tasks import napalm_get

    nr = InitNornir(
        config_file="nornir.yaml", dry_run=True
    )

    results = nr.run(
        task=napalm_get, getters=["facts", "interfaces"]
    )
    print_result(results)


Contents
========

.. toctree::
   :maxdepth: 1

   Home <self>
   tutorial/index
   Howto <howto/index>
   configuration/index
   plugins/index
   Upgrading <upgrading/index>
   Contribute <contributing/index>
   Changelog <changelog/index>
   api/index

Indices and tables

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
