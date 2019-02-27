Changelog
==========

2.1.1 - March 19 2019
---------------------

* [MISC] Workaround to sdispater/poetry#743 #358
* [MISC] Fix automated deployment to pypi #358

Thanks to the following people for their contributions:

* `dbarrosop <https://github.com/dbarrosop>`_

2.1.0 - March 18 2019
---------------------

* [CORE_ENHANCEMENTS] inventory's transform function supports options #292
* [CORE_ENHANCEMENTS] minor improvements to tests #293 #296 #306 #307 #312 #337
* [CORE_ENHANCEMENTS] mypy improvements #308
* [CORE_ENHANCEMENTS] expand user home when deserializing configuration #304
* [CORE_ENHANCEMENTS] fix order of preference when deserializing config #309
* [CORE_ENHANCEMENTS] fix and deprecate dict() function #314
* [CORE_ENHANCEMENTS] migrate to poetry #315
* [CORE_ENHANCEMENTS] Improve logging #316
* [CORE_BUGFIX] (windows only) fix issue #319 - ascii color codes appear instead of color in output #320 #323
* [PLUGIN_IMPROVEMENT] napalm and netmiko plugins support now reading ssh configuration from file #298
* [PLUGIN_BUGFIX] fix paramiko chan.recv_exit_status() call order #313
* [PLUGIN_BUGFIX] temporary fix for enum34 and netmiko-poetry issue #322
* [PLUGIN_IMPROVEMENT] Print OrderDicts nicely in print_result #345
* [DOCS] Various improvements #303 #305 #310 #318 #331 #335 #340

Thanks to the following people for their contributions:

* `bradh11 <https://github.com/bradh11>`_
* `fallenarc <https://github.com/fallenarc>`_
* `floatingstatic <https://github.com/floatingstatic>`_
* `jimmelville <https://github.com/jimmelville>`_
* `optiz0r <https://github.com/optiz0r>`_
* `wdesmedt <https://github.com/wdesmedt>`_
* `dmfigol <https://github.com/dmfigol>`_
* `ktbyers <https://github.com/ktbyers>`_
* `dbarrosop <https://github.com/dbarrosop>`_


2.0.0 - December 17 2018
------------------------

For details about upgrading to 2.0.0 see the `notes <https://nornir.readthedocs.io/en/develop/upgrading/1_to_2.html>`__.

+ [CORE_ENHANCEMENTS] Lots of core enhancements, too many to document
+ [CORE_ENHANCEMENTS] Changes on how the inventory
+ [CORE_ENHANCEMENTS] New ``F`` object for advanced filtering of hosts `(docs) <https://nornir.readthedocs.io/en/develop/howto/advanced_filtering.html>`__
+ [CORE_ENHANCEMENTS] Improvements on how to serialize/deserialize user facing data like the configuration and the inventory
+ [CORE_ENHANCEMENTS] Connections are now their own type of plugin
+ [CORE_ENHANCEMENTS] Ability to handle connections manually `(docs) <https://nornir.readthedocs.io/en/develop/howto/handling_connections.html>`__
+ [CORE_BUGFIX] Lots
+ [PLUGIN_BUGFIX] Lots
+ [PLUGIN_NEW] netmiko_save_config
+ [PLUGIN_NEW] echo_data

1.1.0 - July 12 2018
------------------------

+ [PLUGIN_IMPROVEMENT] print_result is now thread safe `#182 <https://github.com/nornir-automation/nornir/issues/182>`_
+ [DOCUMENTATION] Minor fixes to documentation `#179 <https://github.com/nornir-automation/nornir/issues/179>`_ `#178 <https://github.com/nornir-automation/nornir/issues/178>`_ `#153 <https://github.com/nornir-automation/nornir/issues/153>`_ `#148 <https://github.com/nornir-automation/nornir/issues/148>`_ `#145 <https://github.com/nornir-automation/nornir/issues/145>`_
+ [TESTS] replace nsot container with requests-mock `#172 <https://github.com/nornir-automation/nornir/issues/172>`_
+ [PLUGIN_IMPROVEMENT] Support SSH Agent forwarding for paramiko SSH connections `#159 <https://github.com/nornir-automation/nornir/issues/159>`_
+ [PLUGIN_IMPROVEMENT] allow passing options to napalm getters `#156 <https://github.com/nornir-automation/nornir/issues/156>`_
+ [PLUGIN_BUGFIX] Fix for SSH and API port mapping issues `#154 <https://github.com/nornir-automation/nornir/issues/154>`_
+ [CORE_NEW_FEATURE] add to_dict function so the inventory is serializable `#146 <https://github.com/nornir-automation/nornir/issues/146>`_
+ [CORE_BUGFIX] Fix issues with using built-in and overwriting variable with loop variable `#144 <https://github.com/nornir-automation/nornir/issues/144>`_


1.0.1 - May 16 2018
------------------------

+ [CORE] Rename brigade to nornir `#139 <https://github.com/nornir-automation/nornir/issues/139>`_


1.0.0 - May 4 2018
------------------------

+ [CORE] First release
