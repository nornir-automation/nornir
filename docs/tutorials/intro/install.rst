Installing Nornir
==================

Before you go ahead and install Nornir it's recommended to create your own Python virtualenv. That way you have complete control of your environment and you don't risk overwriting your systems Python environment.

.. note::

   This tutorial doesn't cover the creation of a Python virtual environment. The Python documentation offers a guide where you can learn more about `virtualenvs <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_. We also won't cover the `installation of pip <https://pip.pypa.io/en/stable/installing/>`_, but changes are that you already have pip on your system.

Nornir is published to `PyPI <https://pypi.org/project/nornir/>`_ and can be installed like most other Python packages using the pip tool. You can verify that you have pip installed by typing:

.. code-block:: bash
	
	pip --version

	pip 9.0.3 from /Users/patrick/nornir/lib/python3.6/site-packages (python 3.6)

It could be that you need to use the pip3 binary instead of pip as pip3 is for Python 3 on some systems. Speaking of Python 3, this tutorial is written with Python 3.6 in mind. This has mostly to do with the use of f-strings, you should however be able to follow along even if you are still at Python 2.7. However, if you are starting something new don't use Python 2.7. If you have to make sure that you're pip is up to date as you might have trouble installing some of the Nornir dependencies if you have a very old pip if you are on version 9.0 or later you should be find.

As you would assume, the installation is then very easy.

.. code-block:: bash

	pip install nornir

	Collecting nornir
	Collecting colorama (from nornir)
	[...]
	Successfully installed MarkupSafe-1.0 asn1crypto-0.24.0 bcrypt-3.1.4 nornir-0.0.6

Please note that the above output has been abbreviated for readability. Your output will be quite a bit longer. You should see that `nornir` is successfully installed. 

Now we can verify that Nornir is installed and that you are able to import the package from Python.

.. code-block:: python

	python
	>>>import nornir.core
	>>>

Great, now you're ready to create an inventory.
