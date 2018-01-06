Grouping tasks
==============

Sometimes it is useful to group tasks either for reusability purposes or to speed up the execution (see :doc:`execution model </ref/internals/execution_model>`). Creating groups of tasks is very easy, for instance::

	def group_of_tasks(task):
		task.run(command,
				 command="echo hi! I am {host} and I am a {host.nos} device")
		task.run(command,
				 command="echo hi! I am a {host[type]}")

Groups of tasks are called as regular tasks::

	>>> b = brigade.filter(site="cmh")
	>>> result = b.run(group_of_tasks)
	>>>
	>>>
	>>> b.run(print_result,
	...       num_workers=1,
	...       data=result,
	...       vars=["stdout"])
	* host1.cmh ** changed : False *************************************************
	---- group_of_tasks ** changed : False  ----------------------------------------

	---- command ** changed : False  -----------------------------------------------
	hi! I am host1.cmh and I am a linux device

	---- command ** changed : False  -----------------------------------------------
	hi! I am a host

	* host2.cmh ** changed : False *************************************************
	---- group_of_tasks ** changed : False  ----------------------------------------

	---- command ** changed : False  -----------------------------------------------
	hi! I am host2.cmh and I am a linux device

	---- command ** changed : False  -----------------------------------------------
	hi! I am a host

	* spine00.cmh ** changed : False ***********************************************
	---- group_of_tasks ** changed : False  ----------------------------------------

	---- command ** changed : False  -----------------------------------------------
	hi! I am spine00.cmh and I am a eos device

	---- command ** changed : False  -----------------------------------------------
	hi! I am a network_device

	* spine01.cmh ** changed : False ***********************************************
	---- group_of_tasks ** changed : False  ----------------------------------------

	---- command ** changed : False  -----------------------------------------------
	hi! I am spine01.cmh and I am a junos device

	---- command ** changed : False  -----------------------------------------------
	hi! I am a network_device

	* leaf00.cmh ** changed : False ************************************************
	---- group_of_tasks ** changed : False  ----------------------------------------

	---- command ** changed : False  -----------------------------------------------
	hi! I am leaf00.cmh and I am a eos device

	---- command ** changed : False  -----------------------------------------------
	hi! I am a network_device

	* leaf01.cmh ** changed : False ************************************************
	---- group_of_tasks ** changed : False  ----------------------------------------

	---- command ** changed : False  -----------------------------------------------
	hi! I am leaf01.cmh and I am a junos device

	---- command ** changed : False  -----------------------------------------------
	hi! I am a network_device

Groups of tasks return for each host a :obj:`brigade.core.task.MultiResult` object which is a list-like object of :obj:`brigade.core.task.Result`. The object will contain the result for each individual task within the group of tasks::

	>>> result["leaf01.cmh"].__class__
	<class 'brigade.core.task.MultiResult'>
	>>> result["leaf01.cmh"][0].name
	'group_of_tasks'
	>>> result["leaf01.cmh"][1].name
	'command'
	>>> result["leaf01.cmh"][1].result
	'hi! I am leaf01.cmh and I am a junos device\n'

.. note:: Position ``0`` will be the result for the grouping itself while the rest will be the results for the task inside in the same order as defined in there.

Groups of tasks can also return their own result if needed::

	>>> from brigade.core.task import Result
	>>>
	>>>
	>>> def group_of_tasks_with_result(task):
	...     task.run(command,
	...              command="echo hi! I am {host} and I am a {host.nos} device")
	...     task.run(command,
	...              command="echo hi! I am a {host[type]}")
	...     return Result(host=task.host, result="Yippee ki-yay")
	...
	>>> result = b.run(group_of_tasks_with_result)
	>>>
	>>> result["leaf01.cmh"][0].name
	'group_of_tasks_with_result'
	>>> result["leaf01.cmh"][0].result
	'Yippee ki-yay'

Accessing host data
-------------------

Something interesting about groupings is that you can access host data from them. For instance::

	>>> def access_host_data(task):
	...     if task.host.nos == "eos":
	...         task.host["my-new-var"] = "setting a new var for eos"
	...     elif task.host.nos == "junos":
	...         task.host["my-new-var"] = "setting a new var for junos"
	...
	>>>
	>>> b.run(access_host_data)
	>>>
	>>> b.inventory.hosts["leaf00.cmh"]["my-new-var"]
	'setting a new var for eos'
	>>> b.inventory.hosts["leaf01.cmh"]["my-new-var"]
	'setting a new var for junos'

Reusability
-----------

We mentioned earlier that groups of tasks where also useful for reusability purposes. Let's see it with an example::

	>>> def count(task, to):
	...     task.run(command,
	...              command="echo {}".format(list(range(0, to))))
	...

Great, we created a super complex task that can count up to an arbitrary number. Let's count to 10::

	>>> result = b.run(count,
	...                to=10)
	>>>
	>>>
	>>> b.run(print_result,
	...       num_workers=1,
	...       data=result,
	...       vars=["stdout"])
	* host1.cmh ** changed : False *************************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

	* host2.cmh ** changed : False *************************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

	* spine00.cmh ** changed : False ***********************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

	* spine01.cmh ** changed : False ***********************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

	* leaf00.cmh ** changed : False ************************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

	* leaf01.cmh ** changed : False ************************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

And now to 20::

	>>> result = b.run(count,
	...                to=20)
	>>>
	>>> b.run(print_result,
	...       num_workers=1,
	...       data=result,
	...       vars=["stdout"])
	* host1.cmh ** changed : False *************************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

	* host2.cmh ** changed : False *************************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

	* spine00.cmh ** changed : False ***********************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

	* spine01.cmh ** changed : False ***********************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

	* leaf00.cmh ** changed : False ************************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

	* leaf01.cmh ** changed : False ************************************************
	---- count ** changed : False  -------------------------------------------------

	---- command ** changed : False  -----------------------------------------------
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

