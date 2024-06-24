How to contribute to Nornir
============================

First of all, thank you for considering to contribute to this project!

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

When you are `reporting bugs <https://github.com/nornir-automation/nornir/issues>`_, make sure that you give a explanation about the outcome that you expect and what you are seeing. The bugs which are hardest to fix are the ones which we are unable to reproduce. For this reason it's important that you describe what you did and show us how we can reproduce the bug in another environment.

Fix typos
---------

While we try to take care, getting all the works correct can be.. differcult. Typos are the easiest things to fix and if you find any you can help us from looking silly. You can find more typos to fix by looking in the `Nornir source code <https://github.com/nornir-automation/nornir/tree/develop/nornir>`_ or by visiting the `Nornir documentation <https://nornir.readthedocs.io>`_.

Writing documentation
---------------------

Documentation is another great way to help if you don't want to contribute actual code. The documentation of Nornir is divided into different sections.

- Tutorials: Aims to help people learn Nornir with a lot of handholding, the user might not end up with something useful after following the tutorial. The goal is for people to learn how to use Nornir.
- How-to guides: This sections goal is to help people solve a specific task with Nornir
- Reference guides: This section describe the Nornir API and plugins. Most of the content in this area is generated from the source code itself.

Contributions to the documentation can be small fixes such as changing sentences to make the text more clear, or it could be new guides.

Contributing plugins
--------------------

If you have written your custom plugin for Nornir there's a good chance that it can be useful for others as well. General guidelines when writing plugins are:

- Make them as generic as possible, it doesn't help others if they only work in your environment
- Make sure that it's possible to have unit tests which automatically test that the plugins are working


Contributing to the Nornir core
--------------------------------

When you are contributing code to the core of Nornir make sure that the existing tests are passing, and add tests for the code you wrote. Having your tests in place ensures that other won't accidentally break the contributed code in the future.

Before you make any significant code changes to the core, it's recommended that you open a GitHub issue to discuss your ideas.

Setting up your environment
---------------------------

In order to run tests locally you need to have `Docker <https://docs.docker.com/install/>`_ and `docker-compose <https://docs.docker.com/compose/>`_ installed.

Updating dependencies
---------------------

| Nornir dependencies are managed by `poetry <https://github.com/sdispater/poetry>`_.
| When installing `poetry`, please make sure it is not installed in the project virtual environment.
| Either use the recommended way of installation: ``curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python`` or install it in your home directory ``python3 -m pip install --user poetry``.

The guidelines to pin dependencies are:

1. For the application dependencies:
    a. if semver is supported we pin to major release
    b. if semver is not supported we pin to specific version
2. For development:
    a. black is pinned to a specific version
    b. everything is set to *

Then, to update them:

1. PRs can't update dependencies, if development or application dependencies need to be updated we will have a dedicated PR
2. Prior to a release we will update dependencies

These guidelines are not set in stone and can be changed or broken if there is a compelling reason.

Starting development environment
--------------------------------
Some tests requires additional services to be running which are managed by ``docker-compose``. You can start these services with:

.. code-block:: bash

   make start_dev_env

You can then stop them with:

.. code-block:: bash

   make stop_dev_env


Coding style
------------

Nornir uses `Black <https://github.com/ambv/black>`_, the uncompromising Python code formatter. Black makes it easy for you to format your code as you can do so automatically after installing it.

.. code-block:: bash

   poetry run black .

The Black GitHub repo has information about how you can integrate Black in your editor.

Tests
-------------
As part of the automatic CI on every pull request, besides coding style checks with ``black``, we also do linting with ``ruff``, static type checking with ``mypy``, unit tests with ``pytest``, docs generation with ``sphinx`` and ``nbsphinx`` (for Jupyter notebooks) and verification of outputs in Jupyter notebook tutorials with pytest plugin ``nbval``.

After modifying any code in the core, at first, we recommend running unit tests locally before running the whole test suite (which takes longer time):

.. code-block:: bash

   poetry run pytest

Note: unit tests which require additional services to be running are skipped automatically, when not running in Docker.

To run all CI tests, execute:

.. code-block:: bash

   make tests

To run only verification of Jupyter notebook tutorials outputs with ``nbval`` execute:

.. code-block:: bash

   make build_test_container && make nbval


To run a specific unit test:

.. code-block:: bash

   make build_test_container && make pytest ARGS="tests/plugins/tasks/networking/test_tcp_ping.py"

You can find commands to run other groups of tests in the ``Makefile``
