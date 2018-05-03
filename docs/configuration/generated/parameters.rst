The configuration parameters will be set by the :doc:`Brigade.core.configuration.Config </ref/api/configuration>` class.


----------

inventory
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_INVENTORY</td>
			
				<td>str</td>
				<td>brigade.plugins.inventory.simple.SimpleInventory</td>
			</tr>
	</table>

Path to inventory modules.


----------

jinja_filters
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_JINJA_FILTERS</td>
			
				<td>str</td>
				<td>{}</td>
			</tr>
	</table>

Path to callable returning jinja filters to be used.


----------

logging_dictConfig
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>N/A</td>
			
				<td>dict</td>
				<td>{}</td>
			</tr>
	</table>

Configuration dictionary schema supported by the logging subsystem. Overrides rest of logging_* parameters.


----------

logging_file
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_LOGGING_FILE</td>
			
				<td>str</td>
				<td>brigade.log</td>
			</tr>
	</table>

Logging file. Empty string disables logging to file.


----------

logging_format
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_LOGGING_FORMAT</td>
			
				<td>str</td>
				<td>%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s</td>
			</tr>
	</table>

Logging format


----------

logging_level
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_LOGGING_LEVEL</td>
			
				<td>str</td>
				<td>debug</td>
			</tr>
	</table>

Logging level. Can be any supported level by the logging subsystem


----------

logging_loggers
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>N/A</td>
			
				<td>list</td>
				<td>['brigade']</td>
			</tr>
	</table>

List of loggers to configure. This allows you to enable logging for multiple loggers. For instance, you could enable logging for both brigade and paramiko or just for paramiko. An empty list will enable logging for all loggers.


----------

logging_to_console
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_LOGGING_TO_CONSOLE</td>
			
				<td>bool</td>
				<td>False</td>
			</tr>
	</table>

Whether to log to stdout or not.


----------

num_workers
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_NUM_WORKERS</td>
			
				<td>int</td>
				<td>20</td>
			</tr>
	</table>

Number of Brigade worker processes that are run at the same time, configuration can be overridden on individual tasks by using the `num_workers` argument to (:obj:`brigade.core.Brigade.run`)


----------

raise_on_error
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_RAISE_ON_ERROR</td>
			
				<td>bool</td>
				<td>False</td>
			</tr>
	</table>

If set to ``True``, (:obj:`brigade.core.Brigade.run`) method of will raise an exception if at least a host failed.


----------

ssh_config_file
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_SSH_CONFIG_FILE</td>
			
				<td>str</td>
				<td>~/.ssh/config</td>
			</tr>
	</table>

User ssh_config_file


----------

transform_function
----------------------------------


.. raw:: html

	<table border="1" class="docutils">
		<th>Environment variable</th>
		<th>Type</th>
		<th>Default</th>
			<tr>
			
				<td>BRIGADE_TRANSFORM_FUNCTION</td>
			
				<td>str</td>
				<td>{}</td>
			</tr>
	</table>

Path to transform function. The transform_function you provide will run against each host in the inventory. This is useful to manipulate host data and make it more consumable. For instance, if your inventory has a 'user' attribute you could use this function to map it to 'brigade_user'

