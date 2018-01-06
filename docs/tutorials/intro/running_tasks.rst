Running tasks
=============

Once you have your brigade objects you can start running :doc:`tasks </ref/tasks/index>`. The first thing you have to do is import the task you want to use::

	>>> from brigade.plugins.tasks.commands import command

Now you should be able to run that task for all devices::

	>>> result = brigade.run(command,
	...                      command="echo hi! I am {host} and I am a {host.nos} device")

.. note:: Note you can format strings using host data.

This should give us a :obj:`brigade.core.task.AggregatedResult` object, which is a dictionary-like object where the key is the name of ``Host`` and the value a :obj:`brigade.core.task.Result`.

Now, we can iterate over the object::

	>>> for host, res in result.items():
	...     print(host + ": " + res.stdout)
	...
	host1.cmh: hi! I am host1.cmh and I am a linux device
	host2.cmh: hi! I am host2.cmh and I am a linux device
	spine00.cmh: hi! I am spine00.cmh and I am a eos device
	spine01.cmh: hi! I am spine01.cmh and I am a junos device
	leaf00.cmh: hi! I am leaf00.cmh and I am a eos device
	leaf01.cmh: hi! I am leaf01.cmh and I am a junos device
	host1.bma: hi! I am host1.bma and I am a linux device
	host2.bma: hi! I am host2.bma and I am a linux device
	spine00.bma: hi! I am spine00.bma and I am a eos device
	spine01.bma: hi! I am spine01.bma and I am a junos device
	leaf00.bma: hi! I am leaf00.bma and I am a eos device
	leaf01.bma: hi! I am leaf01.bma and I am a junos device

Or we can use a task that knows how to operate on the :obj:`brigade.core.task.AggregatedResult` object like the task :obj:`brigade.plugins.tasks.text.print_result`::

    >>> b.run(print_result,
    ...       num_workers=1,
    ...       data=result,
    ...       vars=["stdout"])
    * host1.cmh ** changed : False *************************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am host1.cmh and I am a linux device

    * host2.cmh ** changed : False *************************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am host2.cmh and I am a linux device

    * spine00.cmh ** changed : False ***********************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am spine00.cmh and I am a eos device

    * spine01.cmh ** changed : False ***********************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am spine01.cmh and I am a junos device

    * leaf00.cmh ** changed : False ************************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am leaf00.cmh and I am a eos device

    * leaf01.cmh ** changed : False ************************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am leaf01.cmh and I am a junos device

    * host1.bma ** changed : False *************************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am host1.bma and I am a linux device

    * host2.bma ** changed : False *************************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am host2.bma and I am a linux device

    * spine00.bma ** changed : False ***********************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am spine00.bma and I am a eos device

    * spine01.bma ** changed : False ***********************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am spine01.bma and I am a junos device

    * leaf00.bma ** changed : False ************************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am leaf00.bma and I am a eos device

    * leaf01.bma ** changed : False ************************************************
    ---- command ** changed : False  -----------------------------------------------
    hi! I am leaf01.bma and I am a junos device

.. note:: We need to pass ``num_workers=1`` to the ``print_result`` task because otherwise brigade will run each host at the same time using multithreading mangling the output.
