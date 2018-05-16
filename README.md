[![Build Status](https://travis-ci.org/nornir-automation/nornir.svg?branch=develop)](https://travis-ci.org/nornir-automation/nornir) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black) [![Coverage Status](https://coveralls.io/repos/github/nornir-automation/nornir/badge.svg?branch=develop)](https://coveralls.io/github/nornir-automation/nornir?branch=develop)


Nornir
=======
Nornir is a pure Python automation framework intented to be used directly from Python. While most automation frameworks use their own DSL which you use to describe what you want to have done, Nornir lets you control everything from Python.

One of the benefits we want to highlight with this approach is the ease of troubleshooting, if something goes wrong you can just use your existing debug tools directly from Python (just add a line of `import pdb` & `pdb.set_trace()` and you're good to go). Doing the same using a DSL can be quite time consuming.

What Nornir brings to the table is that it takes care of dealing with your inventory and manages the job of dispatching the tasks you want to run against your nodes and devices. The framework provides a very simple way to write plugins if you aren't happy with the ones we ship. Of course if you have written a plugin you think can be useful to others, please send us your code and test cases as a [pull request](https://github.com/nornir-automation/nornir/pulls).


Install
=======

While Nornir still supports Python 2.7 the recommended version is 3.6. Install it with pip.

```
pip install nornir
```

Documentation
=============

Read the [Nornir documentation](https://nornir.readthedocs.io/) online or review it's [code here](https://github.com/nornir-automation/nornir/tree/develop/docs)

Examples
========

You can find some examples and already made tools [here](https://github.com/nornir-automation/brg-tools/)


Bugs & New features
===================

If you think you have bug or would like to request a new feature, please register a GitHub account and [open an issue](https://github.com/nornir-automation/nornir/issues).


Contact & Support
=================

While we are happy to help, the [GitHub issues](<https://github.com/nornir-automation/nornir/issues>) are intended for bugs and discussions about new features. If are struggling to get something to work but don't believe its due to a bug in Nornir, the place to ask questions is in the #nornir channel in the [networktoCode Slack team](https://networktocode.herokuapp.com/).


Contributing to Nornir
=======================

If you want to help the project, the [Contribution Guidelines](https://nornir.readthedocs.io/en/develop/contributing/index.html) is the best place to start.
