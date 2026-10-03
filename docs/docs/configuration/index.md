# Configuration

The configuration is comprised of a set of sections and parameters for those sections. You can set the configuration programmatically using nornir by passing a dictionary of options for each section, by using a YAML file, by setting the corresponding environment variables or by a combination of the three. The order of preference from less preferred to more preferred is "env variable" -> "configuration file" -> "code".

An example using `InitNornir` would be:

```python
nr = InitNornir(
    runner={"plugin": "threaded", "options": {"num_workers": 20}},
    logging={"log_file": "mylogs", "level": "DEBUG"}
)
```

A similar example using a `yaml` file:

```yaml
---
inventory:
    plugin: SimpleInventory
    options:
        host_file: "advanced_filtering/inventory/hosts.yaml"
        group_file: "advanced_filtering/inventory/groups.yaml"
runner:
    plugin: threaded
    options:
        num_workers: 20
```

## Logging

By default, Nornir automatically configures logging when `InitNornir` is called. Logging configuration can be modified and available options are described in the section below. If you want to use Python logging module to configure logging, make sure to set `logging.enabled` parameter to `False` in order to avoid potential issues.

In some situations Nornir will detect previous logging configuration and will emit [`ConflictingConfigurationWarning`](../api/nornir-core-exceptions.mdx#ConflictingConfigurationWarning).

## Parameters

Next, you can find each section and their corresponding options.

### core

#### `raise_on_error`

| Property | Value |
| --- | --- |
| **Description** | If set to `True`, [`Nornir.run`](../api/nornir-core.mdx#Nornir.run) will raise [`NornirExecutionError`](../api/nornir-core-exceptions.mdx#NornirExecutionError) if at least a host failed |
| **Type** | `boolean` |
| **Default** | `False` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_CORE_RAISE_ON_ERROR` |

### runner

#### `plugin`

| Property | Value |
| --- | --- |
| **Description** | Plugin to use as Runner. Must be registered |
| **Type** | `string` |
| **Default** | `Threaded` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_RUNNER_PLUGIN` |

#### `options`

| Property | Value |
| --- | --- |
| **Description** | kwargs to pass to the plugin |
| **Type** | `object` |
| **Default** | `{}` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_RUNNER_OPTIONS` |

### inventory

#### `plugin`

| Property | Value |
| --- | --- |
| **Description** | Plugin to use. Must be registered |
| **Type** | `string` |
| **Default** | `SimpleInventory` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_INVENTORY_PLUGIN` |

#### `options`

| Property | Value |
| --- | --- |
| **Description** | kwargs to pass to the plugin |
| **Type** | `object` |
| **Default** | `{}` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_INVENTORY_OPTIONS` |

#### `transform_function`

| Property | Value |
| --- | --- |
| **Description** | Plugin to use. Must be registered |
| **Type** | `string` |
| **Default** | `None` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_INVENTORY_TRANSFORM_FUNCTION` |

#### `transform_function_options`

| Property | Value |
| --- | --- |
| **Description** | kwargs to pass to the transform_function |
| **Type** | `object` |
| **Default** | `{}` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_INVENTORY_TRANSFORM_FUNCTION_OPTIONS` |

### ssh

#### `config_file`

| Property | Value |
| --- | --- |
| **Description** | Path to ssh configuration file |
| **Type** | `string` |
| **Default** | `~/.ssh/config` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_SSH_CONFIG_FILE` |

### logging

#### `enabled`

| Property | Value |
| --- | --- |
| **Description** | Whether to configure logging or not |
| **Type** | `boolean` |
| **Default** | `None` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_LOGGING_ENABLED` |

#### `level`

| Property | Value |
| --- | --- |
| **Description** | Logging level |
| **Type** | `string` |
| **Default** | `INFO` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_LOGGING_LEVEL` |

#### `log_file`

| Property | Value |
| --- | --- |
| **Description** | Logging file |
| **Type** | `string` |
| **Default** | `nornir.log` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_LOGGING_LOG_FILE` |

#### `format`

| Property | Value |
| --- | --- |
| **Description** | Logging format |
| **Type** | `string` |
| **Default** | `%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_LOGGING_FORMAT` |

#### `to_console`

| Property | Value |
| --- | --- |
| **Description** | Whether to log to console or not |
| **Type** | `boolean` |
| **Default** | `False` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_LOGGING_TO_CONSOLE` |

#### `loggers`

| Property | Value |
| --- | --- |
| **Description** | Loggers to configure |
| **Type** | `array` |
| **Default** | `['nornir']` |
| **Required** | `False` |
| **Environment Variable** | `NORNIR_LOGGING_LOGGERS` |

### user_defined

You can set any `<k, v>` pair you want here and you will have it available under your configuration object, i.e. `nr.config.user_defined.my_app_option`.
