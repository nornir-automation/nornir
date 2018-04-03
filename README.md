[![Build Status](https://travis-ci.org/brigade-automation/brigade.svg?branch=master)](https://travis-ci.org/brigade-automation/brigade) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)


Brigade
=======
Brigade is a pure Python automation framework intented to be used directly from Python. While most automation frameworks use their own DSL which you use to describe what you want to have done, Brigade lets you control everything from Python.

One of the benefits we want to highlight with this approach is the ease of troubleshooting, if something goes wrong you can just use your existing debug tools directly from Python (just add a line of `import pdb` & `pdb.set_trace()` and you're good to go). Doing the same using a DSL can be quite time consuming.

What Brigade brings to the table is that it takes care of dealing with your inventory and manages the job of dispatching the tasks you want to run against your nodes and devices. The framework provides a very simple way to write plugins if you aren't happy with the ones we ship. Of course if you have written a plugin you think can be useful to others, please send us your code and test cases as a [pull request](https://github.com/brigade-automation/brigade/pulls).


Install
=======

While Brigade still supports Python 2.7 the recommended version is 3.6. Install it with pip.

```
pip install brigade
```

Documentation
=============

Read the [Brigade documentation](https://brigade.readthedocs.io/en/latest/) online or review it's [code here](https://github.com/brigade-automation/brigade/tree/develop/docs)


Bugs & New features
===================

If you think you have bug or would like to request a new feature, please register a GitHub account and [open an issue](https://github.com/brigade-automation/brigade/issues).


Contact
=======

Slack is probably the easiest way to get help with Brigade. You can find us in the `brigade` channel on the [networktoCode()](https://networktocode.herokuapp.com/) team.
