Installing Brigade
==================

Before you go ahead and install Brigade it's recommended to create your own Python virtualenv. That way you have complete control of your environment and you don't risk overwriting your systems Python environment.

.. note::

   This tutorial doesn't cover the creation of a Python virtual environment. The Python documentation offers a guide where you can learn more about `virtualenvs <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_. We also won't cover the `installation of pip <https://pip.pypa.io/en/stable/installing/>`_, but changes are that you already have pip on your system.

Brigade is published to `PyPI <https://pypi.org/project/brigade/>`_ and can be installed like most other Python packages using the pip tool. You can verify that you have pip installed by typing:

.. code-block:: bash
	
	pip --version

	pip 1.5.4 from /home/vagrant/brigade/local/lib/python2.7/site-packages (python 2.7)

It could be that you need to use the pip3 binary instead of pip as pip3 is for Python 3 on some systems.

So above we can see that we have pip installed. However the version 1.5.4 is pretty old. To save ourselves from trouble when installing packages we start by upgrading pip.

.. code-block:: bash

	pip install "pip>=9.0.1"

	pip --version

	pip 9.0.1 from /home/vagrant/brigade/local/lib/python2.7/site-packages (python 2.7)

That's more like it! The next step is to install Brigade.

.. code-block:: bash

	pip install brigade

	Collecting brigade
	[...]
	Successfully installed MarkupSafe-1.0
	asn1crypto-0.23.0 bcrypt-3.1.4 brigade-0.0.5 
	certifi-2017.11.5 cffi-1.11.2 chardet-3.0.4 
	cryptography-2.1.4 enum34-1.1.6 future-0.16.0 
	idna-2.6 ipaddress-1.0.18 jinja2-2.10 
	jtextfsm-0.3.1 junos-eznc-2.1.7 lxml-4.1.1 
	napalm-2.2.0 ncclient-0.5.3 netaddr-0.7.19 
	netmiko-1.4.3 paramiko-2.4.0 pyIOSXR-0.52 
	pyasn1-0.4.2 pycparser-2.18 pyeapi-0.8.1 
	pynacl-1.2.1 pynxos-0.0.3 pyserial-3.4 
	pyyaml-3.12 requests-2.18.4 scp-0.10.2 
	six-1.11.0 urllib3-1.22

Please note that the above output has been abbreviated for readability. Your output will probably be longer. You should see that `brigade` is successfully installed. 

Now we can verify that Brigade is installed and that you are able to import the package from Python.

.. code-block:: python

	python
	>>>import brigade.core
	>>>

Great, now you're ready to create an inventory.
