import ast
import os


import yaml


CONF = {
    'num_workers': {
        'description': 'Number of Brigade worker processes that are run at the same time, '
                       'configuration can be overridden on individual tasks by using the '
                       '`num_workers` argument to (:obj:`brigade.core.Brigade.run`)',
        'type': 'int',
        'default': 20,
    },
    'raise_on_error': {
        'description': "If set to ``True``, (:obj:`brigade.core.Brigade.run`) method of will raise "
                       "an exception if at least a host failed.",
        'type': 'bool',
        'default': True,
    },
    'ssh_config_file': {
        'description': 'User ssh_config_file',
        'type': 'str',
        'default': os.path.join(os.path.expanduser("~"), ".ssh", "config"),
        'default_doc': '~/.ssh/config'
    },
}

types = {
    'int': int,
    'str': str,
}


class Config:
    """
    This object handles the configuration of Brigade.

    Arguments:
        config_file(``str``): Yaml configuration file.
    """

    def __init__(self, config_file=None, **kwargs):

        if config_file:
            with open(config_file, 'r') as f:
                c = yaml.load(f.read())
        else:
            c = {}

        self._assign_properties(c)

        for k, v in kwargs.items():
            setattr(self, k, v)

    def _assign_properties(self, c):

        for p in CONF:
            env = CONF[p].get('env') or 'BRIGADE_' + p.upper()
            v = os.environ.get(env) or c.get(p)
            v = v if v is not None else CONF[p]['default']
            if CONF[p]['type'] == 'bool':
                v = ast.literal_eval(str(v).title())
            else:
                v = types[CONF[p]['type']](v)
            setattr(self, p, v)
