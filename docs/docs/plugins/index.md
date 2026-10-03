# Plugins

Nornir is a pluggable system and only very basic ones are included with nornir 3, for a list of third party plugins visit [community plugins](../community/plugin_list.md).

![Overview of the Nornir 3 plugin types](_static/Nornir3_Plugins_v0.jpg)

## Registering plugins

Starting with nornir3 some plugins need to be registered in order to be used. In particular:

- inventory plugins
- transform functions
- connection plugins
- runners

To do so you can use [entry points](https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins) or programmatically.

Using entrypoints in your `setup.py`:

```python
setup(
    # ...
    entry_points={
      "PATH": "NAME = path.to:Plugin",
    }
)
```

In your pyproject.toml, if using a standards-based build tool like `uv` (recommended):

```toml
[project.entry-points."PATH"]
NAME = "path.to:Plugin"
```

Or, if using `poetry`:

```toml
[tool.poetry.plugins."PATH"]
"NAME" = "path.to:Plugin"
```

Where PATH is:

- `nornir.plugins.inventory` - for inventory plugins
- `nornir.plugins.transform_function` - for transform functions
- `nornir.plugins.runners` - for runners
- `nornir.plugins.connections` - for connection plugins

Where NAME is the way you want to refer to it later on and `path.to:Plugin` the import path. For instance:

```toml
[project.entry-points."nornir.plugins.inventory"]
inventory-name = "path.to:InventoryPlugin"
```

To do it programmatically import the correct plugin register and use the `register` method. For instance:

```python
from nornir.core.plugins.inventory import InventoryPluginRegister

from path.to import InventoryPlugin


InventoryPluginRegister.register("inventory-name", InventoryPlugin)
```

## Connections

A connection plugin is a nornir plugin that allows nornir to manage connections with devices

## Inventory

An inventory plugin is a nornir plugin that allows nornir to create an Inventory object from an external source

### Included

- [`SimpleInventory`](../api/nornir-plugins-inventory-simple.mdx#SimpleInventory)

## Transform functions

A transform function is a plugin that manipulates the inventory independently from the inventory plugin used. Useful to extend data using the environment, a secret store or similar.

During inventory initialization, the transform function will be called in a for loop for each host. The transform function takes a host object as the first parameter and additional keyword arguments as specified in the `config.inventory.transform_function_options` dictionary.

## Runners

A runner is a plugin that dictates how to execute the tasks over the hosts

### Included

- [`SerialRunner`](../api/nornir-plugins-runners.mdx#SerialRunner)
- [`ThreadedRunner`](../api/nornir-plugins-runners.mdx#ThreadedRunner)

For more details about `ThreadedRunner` read the [execution model](execution_model.md).

## Processors

A processor is a plugin that taps into certain events and allows the user to execute arbitrary code on those events.
