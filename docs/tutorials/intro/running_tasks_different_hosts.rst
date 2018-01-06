Running tasks on different groups of hosts
==========================================

Below you can see an example where we use the ``filtering`` capabilities of ``brigade`` to run different tasks on different devices::

	>>> switches = brigade.filter(type="network_device")
	>>> hosts = brigade.filter(type="host")
	>>>
	>>> rs = switches.run(command,
	...                   command="echo I am a switch")
	>>>
	>>> rh = hosts.run(command,
	...                command="echo I am a host")

Because :obj:`brigade.core.task.AggregatedResult` objects behave like dictionaries you can add the results of the second task to the result of the first one::

	>>> rs.update(rh)

And then just print the result for all the devices::

	>>> brigade.run(print_result,
	...              num_workers=1,
	...              data=rs,
	...              vars=["stdout"])
	* host1.cmh ** changed : False *************************************************
	---- command ** changed : False  -----------------------------------------------
	I am a host

	* host2.cmh ** changed : False *************************************************
	---- command ** changed : False  -----------------------------------------------
	I am a host

	* spine00.cmh ** changed : False ***********************************************
	---- command ** changed : False  -----------------------------------------------
	I am a switch

	* spine01.cmh ** changed : False ***********************************************
	---- command ** changed : False  -----------------------------------------------
	I am a switch

	* leaf00.cmh ** changed : False ************************************************
	---- command ** changed : False  -----------------------------------------------
	I am a switch

	* leaf01.cmh ** changed : False ************************************************
	---- command ** changed : False  -----------------------------------------------
	I am a switch

	* host1.bma ** changed : False *************************************************
	---- command ** changed : False  -----------------------------------------------
	I am a host

	* host2.bma ** changed : False *************************************************
	---- command ** changed : False  -----------------------------------------------
	I am a host

	* spine00.bma ** changed : False ***********************************************
	---- command ** changed : False  -----------------------------------------------
	I am a switch

	* spine01.bma ** changed : False ***********************************************
	---- command ** changed : False  -----------------------------------------------
	I am a switch

	* leaf00.bma ** changed : False ************************************************
	---- command ** changed : False  -----------------------------------------------
	I am a switch

	* leaf01.bma ** changed : False ************************************************
	---- command ** changed : False  -----------------------------------------------
	I am a switch

