How to contribute to Brigade
============================

First of all, thank you for conidering to contribute to this project!

Support questions
-----------------

While we are happy to help, the `GitHub issues <https://github.com/brigade-automation/brigade/issues>`_ are intended for bugs and discussions about new features. If are struggling to get something to work but don't believe its due to a bug in Brigade, the place to ask questions is in the #brigade channel in the `networktoCode Slack team <https://networktocode.herokuapp.com/>`_.


Several ways to contribute
--------------------------

There are several things you can do to help the project.

- Spread the word about Brigade
- Suggest great features
- Report bugs
- Fix typos
- Write documentation
- Contribute your plugins
- Improve the Brigade core

Spread the word about Brigade
-----------------------------

Even if you aren't in the position that you can contribute your time to this project, it still helps us if you spread the word about the project. It could be just a short notice in social media or a discussion you have with your friends. As more people become aware of the project there's a better chance that we reach people who are able to contribute. So, even if you can't directly contribute yourself, someone you refer to us might.

Suggesting new features
-----------------------

It could be that you are aware of something that would be great to have in Brigade and we are always welcoming feature requests. Make sure you explain in what scenario your suggested feature would be useful.

Reporting bugs
--------------

When you are `reporting bugs <https://github.com/brigade-automation/brigade/issues>`_, make sure that you give a explaination about the outcome that you expect and what you are seeing. The bugs which are hardest to fix are the ones which we are unable to reproduce. For this reason it's important that you describe what you did and show us how we can reproduce the bug in another environment.

Fix typos
---------

While we try to take care, getting all the works correct can be.. differcult. Typos are the easiest things to fix and if you find any you can help us from looking silly. You can find more typos to fix by looking in the `Brigade source code <https://github.com/brigade-automation/brigade/tree/develop/brigade>`_ or by visiting the `Brigade documentation <https://brigade.readthedocs.io>`_.

Writing documentation
---------------------

Documentation is another great way to help if you don't want to contribute actual code. The documentation of Brigade is divided into different sections.

- Tutorials: Aims to help people learn Brigade with a lot of handholding, the user might not end up with something useful after following the tutorial. The goal is for people to learn how to use Brigade.
- How-to guides: This sections goal is to help people solve a specific task with Brigade
- Reference guides: This section describe the Brigade API and plugins. Most of the content in this area is generated from the source code itself.

Contributions to the documentation can be small fixes such as changing scentences to make the text more clear, or it could be new guides.

Contributing plugins
--------------------

If you have written your custom plugin for Brigade there's a good chance that it can be useful for others as well. General guidelines when writing plugins are:

- Make them as generic as possible, it doesn't help others if they only work in your environment
- Make sure that it's possible to have unit tests which automatically test that the plugins are working


Contributing to the Brigade core
--------------------------------

When you are contributing code to the core of Brigade make sure that the existing tests are passing, and add tests to the code you have added. Having your tests in place ensures that other won't accidentally brake it in the future.

Before you make any significant code changes to the core it's recommended that you open an issue to discuss your ideas before writing the code.

Setting up your environment
---------------------------

In order to run tests locally you need to have `Docker <https://docs.docker.com/install/>`_ and `Pandoc <https://pandoc.org/installing.html>`_ installed. Docker is used to test the Brigade plugins and Pandoc is required for building the documentation provided by `Sphinx <http://www.sphinx-doc.org/>`_. After those are installed you can go ahead and install the needed Python dependencies.

.. code-block:: bash

	pip -r requirements-dev.txt

Running tests
-------------

While the automated tests will be triggered when you submit a new pull request it can still save you time to run the tests locally first. 

.. code-block:: bash

	make tests

The test above will run the tests against the Brigade code and documentation.


Coding style
------------

Brigade uses `Black <https://github.com/ambv/black>`_, the the uncompromising Python code formatter. Black makes it easy for you to format your code as you can do so automatically after installing it. Note that Python 3.6 is required to run Black.

.. code-block:: bash

	make format

The Black GitHub repo has information about how you can integrate Black in your editor.
