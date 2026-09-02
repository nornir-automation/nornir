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

Nornir uses `uv <https://docs.astral.sh/uv/>`_ to manage dependencies and virtual environments. Install it either the recommended way: ``curl -LsSf https://astral.sh/uv/install.sh | sh`` or with ``pipx install uv``.

Then install the project dependencies:

.. code-block:: bash

   uv sync --locked

Optionally, you can install `Docker <https://docs.docker.com/get-started/get-docker/>`_ to run the whole test suite in a container (see the Tests section below).

Updating dependencies
---------------------

Nornir dependencies are managed by `uv <https://docs.astral.sh/uv/>`_ (see `Setting up your environment`_ above).

The guidelines to pin dependencies are:

1. For the application dependencies:
    a. if semver is supported we pin to major release
    b. if semver is not supported we pin to specific version
2. For development:
    a. ruff is pinned to a specific version
    b. everything is set to *

Then, to update them:

1. Adding, removing or changing a dependency requires **maintainer approval**, recorded in the pull request that makes the change. Approval is the gate: no dedicated issue and no dependency-only pull request is required, and your work does not need to wait for one. A feature or fix PR may carry the dependency change its own code needs, provided the change is limited to what that code actually requires, includes the resulting ``uv.lock`` update, and is called out explicitly for review.
2. Prior to a release we will update dependencies. A bulk refresh unrelated to any feature should still land on its own, so that lockfile churn is never mixed into a behavioural change.

These guidelines are not set in stone and can be changed or broken if there is a compelling reason.

Coding style
------------

Nornir uses `Ruff <https://docs.astral.sh/ruff/>`_. Ruff makes it easy for you to format your code as you can do so automatically after installing it.

.. code-block:: bash

   uv run ruff format --check .

The Ruff GitHub repo has information about how you can integrate Ruff in your editor.

Tests
-------------
As part of the automatic CI on every pull request, besides coding style checks and linting with ``ruff``, static type checking with ``mypy``, unit tests with ``pytest``, docs generation with ``sphinx`` and ``nbsphinx`` (for Jupyter notebooks) and verification of outputs in Jupyter notebook tutorials with pytest plugin ``nbval``.

After modifying any code in the core, at first, we recommend running unit tests locally before running the whole test suite (which takes longer time):

.. code-block:: bash

   uv run pytest

To run all CI tests, execute:

.. code-block:: bash

   make tests

To run only verification of Jupyter notebook tutorials outputs with ``nbval`` execute:

.. code-block:: bash

   make nbval

To run a specific unit test:

.. code-block:: bash

   make pytest ARGS="tests/core/test_tasks.py"

Alternatively, you can run the whole test suite inside a Docker container matching the CI Linux environment:

.. code-block:: bash

   make docker-tests

You can find commands to run other groups of tests in the ``Makefile``
