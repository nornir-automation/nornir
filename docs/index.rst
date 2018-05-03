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

Here is an example on how to quickly build a runbook leveraging Brigade to retrieve information from the network::

    from brigade.core import InitBrigade
    from brigade.plugins.functions.text import print_result
    from brigade.plugins.tasks.networking import napalm_get

    brg = InitBrigade(
        config_file="brigade.yaml", dry_run=True, num_workers=20
    )

    results = brg.run(
        task=napalm_get, getters=["facts", "interfaces"]
    )
    print_result(results)

You can find this and other examples `here <https://github.com/brigade-automation/brg-tools/>`_.

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
   Contribute <contributing/index>


Indices and tables

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
