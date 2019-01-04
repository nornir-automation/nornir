How to contribute to Nornir
============================

First of all, thank you for conidering to contribute to this project!

Several ways to contribute
--------------------------

There are several things you can do to help the project.

- Spread the word about Nornir
- Suggest great features
- Report bugs
- Fix typos
- Write documentation
- Contribute your plugins
- Improve the Nornir core

Spread the word about Nornir
-----------------------------

Even if you aren't in the position that you can contribute your time to this project, it still helps us if you spread the word about the project. It could be just a short notice in social media or a discussion you have with your friends. As more people become aware of the project there's a better chance that we reach people who are able to contribute. So, even if you can't directly contribute yourself, someone you refer to us might.

Suggesting new features
-----------------------

It could be that you are aware of something that would be great to have in Nornir and we are always welcoming feature requests. Make sure you explain in what scenario your suggested feature would be useful.

Reporting bugs
--------------

When you are `reporting bugs <https://github.com/nornir-automation/nornir/issues>`_, make sure that you give a explaination about the outcome that you expect and what you are seeing. The bugs which are hardest to fix are the ones which we are unable to reproduce. For this reason it's important that you describe what you did and show us how we can reproduce the bug in another environment.

Fix typos
---------

While we try to take care, getting all the works correct can be.. differcult. Typos are the easiest things to fix and if you find any you can help us from looking silly. You can find more typos to fix by looking in the `Nornir source code <https://github.com/nornir-automation/nornir/tree/develop/nornir>`_ or by visiting the `Nornir documentation <https://nornir.readthedocs.io>`_.

Writing documentation
---------------------

Documentation is another great way to help if you don't want to contribute actual code. The documentation of Nornir is divided into different sections.

- Tutorials: Aims to help people learn Nornir with a lot of handholding, the user might not end up with something useful after following the tutorial. The goal is for people to learn how to use Nornir.
- How-to guides: This sections goal is to help people solve a specific task with Nornir
- Reference guides: This section describe the Nornir API and plugins. Most of the content in this area is generated from the source code itself.

Contributions to the documentation can be small fixes such as changing scentences to make the text more clear, or it could be new guides.

Contributing plugins
--------------------

If you have written your custom plugin for Nornir there's a good chance that it can be useful for others as well. General guidelines when writing plugins are:

- Make them as generic as possible, it doesn't help others if they only work in your environment
- Make sure that it's possible to have unit tests which automatically test that the plugins are working


Contributing to the Nornir core
--------------------------------

When you are contributing code to the core of Nornir make sure that the existing tests are passing, and add tests to the code you have added. Having your tests in place ensures that other won't accidentally brake it in the future.

Before you make any significant code changes to the core it's recommended that you open an issue to discuss your ideas before writing the code.

Setting up your environment
---------------------------

In order to run tests locally you need to have `Docker <https://docs.docker.com/install/>`_ and `docker-compose <https://docs.docker.com/compose/>`_ installed.

Starting development environment
--------------------------------

You need some services to run the tests. Those are managed with ``docker-compose``. In order to start them you can execute:

.. code-block:: bash

   make start_dev_env

You can then stop it with:

.. code-block:: bash

   make stop_dev_env

Running tests
-------------

While the automated tests will be triggered when you submit a new pull request it can still save you time to run the tests locally first.

.. code-block:: bash

   make tests

That will run the entire test suite, if you want to target some specific test you can do:

.. code-block:: bash

   make build_test_container && make nbval

To run only ``nbval`` environment or:


.. code-block:: bash

   make build_test_container && make pytest ARGS="tests/plugins/tasks/networking/test_tcp_ping.py"

To run a specific test.


Coding style
------------

Nornir uses `Black <https://github.com/ambv/black>`_, the the uncompromising Python code formatter. Black makes it easy for you to format your code as you can do so automatically after installing it. Note that Python 3.6 is required to run Black.

.. code-block:: bash

   black .

The Black GitHub repo has information about how you can integrate Black in your editor.
