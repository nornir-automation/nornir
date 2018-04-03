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

Before contributing for the first time

- Git: If you don't have git installed get it `here <https://git-scm.com/>`_
- Configure git with your `username and email <https://help.github.com/articles/setting-your-username-in-git/>`_
- Create a `Github account <https://github.com/join>`_
- `Fork the repo <https://github.com/brigade-automation/brigade#fork-destination-box>`_
- Clone your copy:
	
	git clone git clone https://github.com/{username}/brigade
	cd brigade

- Create a new branch:
	
	git checkout -b new_stuff

- Create a virtualenv: It's recommended that you do your coding in a `virtualenv <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_
- Install Brigade in editable mode
	
	pip install -e .

- Commit and push your local changes
	
	git add .
	git commit -m "Meaningful commit message"
	git push

- Create pull request, visit `the repo <https://github.com/brigade-automation/brigade>`_ and choose the link to create a new pull request.

Running tests
-------------

While the automated tests will be triggered when you submit a new pull request it can still save you time to run the tests locally first. 


	pip install tox
	tox

The test above will run the tests against the Brigade code. Aside from the code the documentation generated by `Spinx <http://www.sphinx-doc.org/>`_ is also validated. In order to test this you will be required to also install `Pandoc <https://pandoc.org/installing.html>`_. 

Coding style
------------

TBD