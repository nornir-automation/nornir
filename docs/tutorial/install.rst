Installing Nornir
==================

Before you go ahead and install Nornir, it's recommended to create your own Python virtualenv. That way you have complete control of your environment and you don't risk overwriting your systems Python environment.

.. note::

   This tutorial doesn't cover the creation of a Python virtual environment. The Python documentation offers a guide where you can learn more about `virtualenvs <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_. We also won't cover the `installation of pip <https://pip.pypa.io/en/stable/installing/>`_, but chances are that you already have pip on your system.

Nornir is published to `PyPI <https://pypi.org/project/nornir/>`_ and can be installed like most other Python packages using the pip tool. You can verify that you have pip installed by typing:

.. code-block:: bash

    $ pip --version
    pip 20.1 from /home/dbarroso/.virtualenvs/nornir/lib/python3.8/site-packages/pip (python 3.8)

It could be that you need to use the pip3 binary instead of pip as pip3 is for Python 3 on some systems.

As you would assume, the installation is then very easy.

.. code-block:: bash

    $ pip install nornir
    Collecting nornir
      Downloading nornir-3.0.0-py3-none-any.whl (28 kB)
    Requirement already satisfied: typing_extensions<4.0,>=3.7 in /home/dbarroso/.virtualenvs/tmp-nornir/lib/python3.8/site-packages (from nornir) (3.7.4.2)
    Requirement already satisfied: mypy_extensions<0.5.0,>=0.4.1 in /home/dbarroso/.virtualenvs/tmp-nornir/lib/python3.8/site-packages (from nornir) (0.4.3)
    Collecting ruamel.yaml<0.17,>=0.16
      Using cached ruamel.yaml-0.16.10-py2.py3-none-any.whl (111 kB)
    Collecting ruamel.yaml.clib>=0.1.2; platform_python_implementation == "CPython" and python_version < "3.9"
      Using cached ruamel.yaml.clib-0.2.0-cp38-cp38-manylinux1_x86_64.whl (578 kB)
    Installing collected packages: colorama, ruamel.yaml.clib, ruamel.yaml, nornir
    Successfully installed nornir-3.0.0 ruamel.yaml-0.16.10 ruamel.yaml.clib-0.2.0

Your output might not be an exact match, the important bit is that last line where it says that nornir was installed successfully.

Now we can verify that Nornir is installed and that you are able to import the package from Python.

.. code-block:: python

	$ python
	>>> from nornir import InitNornir
	>>>

Plugins
-------

Nornir is a pluggable system and most, if not all, of its functionality can be extended via plugins. To understand how plugins work and where you can find some of the plugins we recommend you to visit the `plugins <../plugins/>`_ section.
