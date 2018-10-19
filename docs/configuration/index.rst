Configuration
=============

The configuration is comprised of a set of sections and parameters for those sections. You can set the configuration programmatically using nornir by passing a dictionary of options for each section, by using a YAML file, by setting the corresponding environment variables or by a combination of the three. The order of preference from less to more preferred is "configuration file" -> "env variable" -> "code".

An example using ``InitNornir`` would be::

    nr = InitNornir(
        core={"num_workers": 20},
        logging={"file": "mylogs", "level": "debug"}
    )

A similar example using a ``yaml`` file:

.. include:: ../howto/advanced_filtering/config.yaml
   :code: yaml

Next, you can find each section and their corresponding options.

.. include:: generated/parameters.rst

user_defined
------------

You can set any ``<k, v>`` pair you want here and you will have it available under your configuration object, i.e. ``nr.config.user_defined.my_app_option``.
