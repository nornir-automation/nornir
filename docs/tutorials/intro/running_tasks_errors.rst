Dealing with task errors
========================

Tasks can fail due to many reasons. As we continue we will see how to deal with errors effectively with brigade.

Failing on error by default
---------------------------

Brigade can raise a :obj:`brigade.core.exceptions.BrigadeExecutionError` exception automatically as soon as an error occurs. For instance::

    >>> brigade = easy_brigade(
    ...         host_file="hosts.yaml", group_file="groups.yaml",
    ...         dry_run=True,
    ...         raise_on_error=True,
    ... )
    >>>
    >>>
    >>> def task_that_sometimes_fails(task):
    ...     if task.host.name == "leaf00.cmh":
    ...         raise Exception("an uncontrolled exception happened")
    ...     elif task.host.name == "leaf01.cmh":
    ...         return Result(host=task.host, result="yikes", failed=True)
    ...     else:
    ...         return Result(host=task.host, result="swoosh")
    ...
    >>>
    >>> b = brigade.filter(site="cmh")
    >>> r = b.run(task_that_sometimes_fails)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 191, in run
        result.raise_on_error()
      File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 145, in raise_on_error
        raise BrigadeExecutionError(self)
    brigade.core.exceptions.BrigadeExecutionError:
    ########################################
    # host1.cmh (succeeded)
    ########################################
    swoosh
    ########################################
    # host2.cmh (succeeded)
    ########################################
    swoosh
    ########################################
    # spine00.cmh (succeeded)
    ########################################
    swoosh
    ########################################
    # spine01.cmh (succeeded)
    ########################################
    swoosh
    ########################################
    # leaf00.cmh (failed)
    ########################################
    Traceback (most recent call last):
      File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 201, in run_task
        r = task._start(host=host, brigade=brigade, dry_run=dry_run)
      File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 41, in _start
        r = self.task(self, **self.params) or Result(host)
      File "<stdin>", line 3, in task_that_sometimes_fails
    Exception: an uncontrolled exception happened

    ########################################
    # leaf01.cmh (failed)
    ########################################
    yikes

Ok, let's see what happened there. First, we configured the default behavior to raise an Exception as soon as an error occurs::

    >>> brigade = easy_brigade(
    ...         host_file="hosts.yaml", group_file="groups.yaml",
    ...         dry_run=True,
    ...         raise_on_error=True,
    ... )
    >>>

Then, the following task fails with an exception for ``leaf00.cmh`` and with a controlled error on ``leaf01.cmh``. It doesn't matter if the error is controlled or not, both cases will trigger brigade to raise an Exception.

    >>> def task_that_sometimes_fails(task):
    ...     if task.host.name == "leaf00.cmh":
    ...         raise Exception("an uncontrolled exception happened")
    ...     elif task.host.name == "leaf01.cmh":
    ...         return Result(host=task.host, result="yikes", failed=True)
    ...     else:
    ...         return Result(host=task.host, result="swoosh")
    ...

Finally, when we run the task brigade fails immediately and the traceback is shown on the screen::

    >>> b = brigade.filter(site="cmh")
    >>> r = b.run(task_that_sometimes_fails)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 191, in run
        result.raise_on_error()
      File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 145, in raise_on_error
        raise BrigadeExecutionError(self)
    brigade.core.exceptions.BrigadeExecutionError:
    ########################################
    # host1.cmh (succeeded)
    ########################################
    swoosh
    ########################################
    # host2.cmh (succeeded)
    ########################################
    swoosh
    ########################################
    # spine00.cmh (succeeded)
    ########################################
    swoosh
    ########################################
    # spine01.cmh (succeeded)
    ########################################
    swoosh
    ########################################
    # leaf00.cmh (failed)
    ########################################
    Traceback (most recent call last):
      File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 201, in run_task
        r = task._start(host=host, brigade=brigade, dry_run=dry_run)
      File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 41, in _start
        r = self.task(self, **self.params) or Result(host)
      File "<stdin>", line 3, in task_that_sometimes_fails
    Exception: an uncontrolled exception happened

    ########################################
    # leaf01.cmh (failed)
    ########################################
    yikes

As with any other exception you can capture it::

    >>> try:
    ...     r = b.run(task_that_sometimes_fails)
    ... except BrigadeExecutionError as e:
    ...     error = e
    ...
    >>>

Let's inspect the object. You can easily identify the tasks that failed::

    >>> error.failed_hosts
    {'leaf00.cmh': [<brigade.core.task.Result object at 0x109048940>], 'leaf01.cmh': [<brigade.core.task.Result object at 0x1090439e8>]}
    >>> error.failed_hosts['leaf00.cmh'][0].failed
    True
    >>> error.failed_hosts['leaf00.cmh'][0].result
    'Traceback (most recent call last):\n  File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 201, in run_task\n    r = task._start(host=host, brigade=brigade, dry_run=dry_run)\n  File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 41, in _start\n    r = self.task(self, **self.params) or Result(host)\n  File "<stdin>", line 3, in task_that_sometimes_fails\nException: an uncontrolled exception happened\n'
    >>> error.failed_hosts['leaf00.cmh'][0].exception
    Exception('an uncontrolled exception happened',)
    >>> error.failed_hosts['leaf01.cmh'][0].failed
    True
    >>> error.failed_hosts['leaf01.cmh'][0].result
    'yikes'
    >>> error.failed_hosts['leaf01.cmh'][0].exception
    >>>

Or you can just grab the :obj:`brigade.core.task.AggregatedResult` inside the exception and do something useful with it::

    >>> error.result.items()
    dict_items([('host1.cmh', [<brigade.core.task.Result object at 0x109043518>]), ('host2.cmh', [<brigade.core.task.Result object at 0x109048c50>]), ('spine00.cmh', [<brigade.core.task.Result object at 0x1090486a0>]), ('spine01.cmh', [<brigade.core.task.Result object at 0x1090483c8>]), ('leaf00.cmh', [<brigade.core.task.Result object at 0x109048940>]), ('leaf01.cmh', [<brigade.core.task.Result object at 0x1090439e8>])])

Not failing by default
----------------------

Now, let's repeat the previous example but setting ``raise_on_error=False``::

    >>> from brigade.core.task import Result
    >>> from brigade.easy import easy_brigade
    >>> from brigade.plugins.tasks.text import print_result
    >>>
    >>> brigade = easy_brigade(
    ...         host_file="hosts.yaml", group_file="groups.yaml",
    ...         dry_run=True,
    ...         raise_on_error=False,
    ... )
    >>>
    >>>
    >>> def task_that_sometimes_fails(task):
    ...     if task.host.name == "leaf00.cmh":
    ...         raise Exception("an uncontrolled exception happened")
    ...     elif task.host.name == "leaf01.cmh":
    ...         return Result(host=task.host, result="yikes", failed=True)
    ...     else:
    ...         return Result(host=task.host, result="swoosh")
    ...
    >>>
    >>> b = brigade.filter(site="cmh")
    >>>
    >>> r = b.run(task_that_sometimes_fails)
    >>>

If ``raise_on_error=False`` the result of the task will contain a :obj:`brigade.core.task.AggregatedResult` object describing what happened::

    >>> r["leaf00.cmh"].failed
    True
    >>> r["leaf00.cmh"].result
    'Traceback (most recent call last):\n  File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 201, in run_task\n    r = task._start(host=host, brigade=brigade, dry_run=dry_run)\n  File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 41, in _start\n    r = self.task(self, **self.params) or Result(host)\n  File "<stdin>", line 3, in task_that_sometimes_fails\nException: an uncontrolled exception happened\n'
    >>> r["leaf00.cmh"].exception
    Exception('an uncontrolled exception happened',)
    >>> r["leaf01.cmh"].failed
    True
    >>> r["leaf01.cmh"].result
    'yikes'
    >>> r["leaf01.cmh"].exception
    >>> r["host1.cmh"].failed
    False
    >>> r["host1.cmh"].result
    'swoosh'

Skipping Hosts
--------------

If you set ``raise_on_error=False`` and a task fails ``brigade`` will keep track of the failing hosts and will skip the host in following tasks::

	>>> r = b.run(task_that_sometimes_fails)
	>>> r.failed
	True
	>>> r.failed
	False

What did just happen? Let's inspect the result::

	>>> r.skipped
	True
	>>> r['leaf00.cmh'].failed
	False
	>>> r['leaf00.cmh'].skipped
	True
	>>> r['leaf00.cmh'].result
	>>> r['leaf01.cmh'].failed
	False
	>>> r['leaf01.cmh'].skipped
	True
	>>> r['leaf01.cmh'].result
	>>>

As you can see the second time we ran the same tasks didn't trigger any error because the hosts that failed the first time were skipped. You can inspect which devices are on the "blacklist"::

	>>> b.data.failed_hosts
	{'leaf00.cmh', 'leaf01.cmh'}

And even whitelist them:

	>>> r = b.run(task_that_sometimes_fails)
	>>> r['leaf00.cmh'].skipped
	True
	>>> r['leaf01.cmh'].skipped
	False
	>>> r['leaf01.cmh'].failed
	True

You can also reset the list of blacklisted hosts::

	>>> b.data.failed_hosts = set()
	>>> r = b.run(task_that_sometimes_fails)
	>>> r['leaf00.cmh'].skipped
	False
	>>> r['leaf00.cmh'].failed
	True
	>>> r['leaf01.cmh'].skipped
	False
	>>> r['leaf01.cmh'].failed
	True

``AggreggatedResult``
---------------------

Regardless of if you had ``raise_on_error`` set to ``True`` or ``False`` you will have access to the very same :obj:`brigade.core.task.AggregatedResult` object. The only difference is that in the former case you will have the object in the ``result`` attribute of a :obj:`brigade.core.exceptions.BrigadeExecutionError` object and on the latter you will get it in the assigned variable.

Let's see a few things you can do with an :obj:`brigade.core.task.AggregatedResult` object::

	>>> r
	AggregatedResult: task_that_sometimes_fails
	>>> r.failed
	True
	>>> r.failed_hosts
	{'leaf00.cmh': [<brigade.core.task.Result object at 0x108be7518>], 'leaf01.cmh': [<brigade.core.task.Result object at 0x109051f98>]}
	>>> r.raise_on_error()
	Traceback (most recent call last):
	  File "<stdin>", line 1, in <module>
	  File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 145, in raise_on_error
		raise BrigadeExecutionError(self)
	brigade.core.exceptions.BrigadeExecutionError:
	########################################
	# host1.cmh (succeeded)
	########################################
	swoosh
	########################################
	# host2.cmh (succeeded)
	########################################
	swoosh
	########################################
	# spine00.cmh (succeeded)
	########################################
	swoosh
	########################################
	# spine01.cmh (succeeded)
	########################################
	swoosh
	########################################
	# leaf00.cmh (failed)
	########################################
	Traceback (most recent call last):
	  File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 201, in run_task
		r = task._start(host=host, brigade=brigade, dry_run=dry_run)
	  File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 41, in _start
		r = self.task(self, **self.params) or Result(host)
	  File "<stdin>", line 3, in task_that_sometimes_fails
	Exception: an uncontrolled exception happened

	########################################
	# leaf01.cmh (failed)
	########################################
	yikes

As you can see you can quickly discern if the execution failed and you can even trigger the exception automatically if needed (if no host failed ``r.raise_on_error`` will just return ``None``)

Overriding default behavior
---------------------------

Regardless of the default behavior you can force ``raise_on_error`` on a per task basis::

	>>> r = b.run(task_that_sometimes_fails,
	...           raise_on_error=True)
	Traceback (most recent call last):
	  File "<stdin>", line 2, in <module>
	r = b.run(task_that_sometimes_fails,
			  raise_on_error=False)
	  File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 191, in run
		result.raise_on_error()
	  File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 145, in raise_on_error
		raise BrigadeExecutionError(self)
	brigade.core.exceptions.BrigadeExecutionError:
	########################################
	# host1.cmh (succeeded)
	########################################
	swoosh
	########################################
	# host2.cmh (succeeded)
	########################################
	swoosh
	########################################
	# spine00.cmh (succeeded)
	########################################
	swoosh
	########################################
	# spine01.cmh (succeeded)
	########################################
	swoosh
	########################################
	# leaf00.cmh (failed)
	########################################
	Traceback (most recent call last):
	  File "/Users/dbarroso/workspace/brigade/brigade/core/__init__.py", line 201, in run_task
		r = task._start(host=host, brigade=brigade, dry_run=dry_run)
	  File "/Users/dbarroso/workspace/brigade/brigade/core/task.py", line 41, in _start
		r = self.task(self, **self.params) or Result(host)
	  File "<stdin>", line 3, in task_that_sometimes_fails
	Exception: an uncontrolled exception happened

	########################################
	# leaf01.cmh (failed)
	########################################
	yikes

	>>> r = b.run(task_that_sometimes_fails,
	...           raise_on_error=False)
	>>>

As you can see, regardless of what ``brigade`` had been configured to do, the task failed on the first case but didn't on the second one.

Which one to use
----------------

It depends™. As a rule of thumb it's probably safer to fail by default and capture errors explicitly. For instance, a continuation you can see an example where we run a task that can change the system and if it fails we try to run a cleanup operation and if it doesn't succeed either we blacklist the host so further tasks are skipped for that host::

	try:
		brigade.run(task_that_attempts_to_change_the_system)
	except BrigadeExecutionError as e:
		for host in e.failed_hosts.keys():
			r = brigade.filter(name=host).run(task_that_reverts_changes,
											  raise_on_error=True)
			if r.failed:
				brigade.data.failed_hosts.add(host)

In other simpler cases it might be just simpler and completely safe to ignore errors::

	r = brigade.run(a_task_that_is_safe_if_it_fails)
	brigade.run(print_result,
				data=result)
