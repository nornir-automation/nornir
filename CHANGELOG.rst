2.0.0 - December 17 2018
========================

For details about upgrading to 2.0.0 see the [https://nornir.readthedocs.io/en/2.0.0-beta/upgrading/1_to_2.html](notes).

+ [CORE_ENHANCEMENTS] Lots of core enhancements, too many to document
+ [CORE_ENHANCEMENTS] Changes on how the inventory
+ [CORE_ENHANCEMENTS] New ``F`` object for advanced filtering of hosts [docs](file:///Users/dbarroso/workspace/nornir/docs/_build/html/howto/advanced_filtering.html)
+ [CORE_ENHANCEMENTS] Improvements on how to serialize/deserialize user facing data like the configuration and the inventory
+ [CORE_ENHANCEMENTS] Connections are now their own type of plugin
+ [CORE_ENHANCEMENTS] Ability to handle connections manually [docs](file:///Users/dbarroso/workspace/nornir/docs/_build/html/howto/handling_connections.html)
+ [CORE_BUGFIX] Lots
+ [PLUGIN_BUGFIX] Lots
+ [PLUGIN_NEW] netmiko_save_config
+ [PLUGIN_NEW] echo_data

1.1.0 - July 12 2018
====================

+ [PLUGIN_IMPROVEMENT] print_result is now thread safe #182
+ [DOCUMENTATION] Minor fixes to documentation #179 #178 #178 #153 #148 #145
+ [TESTS] replace nsot container with requests-mock #172 
+ [PLUGIN_IMPROVEMENT] Support SSH Agent forwarding for paramiko SSH connections #159
+ [PLUGIN_IMPROVEMENT] allow passing options to napalm getters #156 
+ [PLUGIN_BUGFIX] Fix for SSH and API port mapping issues #154
+ [CORE_NEW_FEATURE] add to_dict function so the inventory is serializable #146
+ [CORE_BUGFIX] Fix issues with using built-in and overwriting variable with loop variable #144 


1.0.1 - May 16 2018
===================

+ [CORE] Rename brigade to nornir #139


1.0.0 - May 4 2018
==================

+ [CORE] First release
