import ast
import os


import yaml


CONF = {
    'num_workers': {
        'description': 'Number of Brigade worker processes',
        'env': 'BRIGADE_NUM_WORKERS',
        'type': int,
        'default': 20,
    },
    'raise_on_error': {
        'description': "If set to ``True``, :meth:`run` method of will raise an exception if at "
                       "least a host failed.",
        'env': 'BRIGADE_RAISE_ON_ERROR',
        'type': bool,
        'default': True,
    },
    'ssh_config_file': {
        'description': 'User ssh_config_file',
        'env': 'BRIGADE_SSH_CONFIG_FILE',
        'type': str,
        'default': os.path.join(os.path.expanduser("~"), ".ssh", "config"),
    },
}


class Config:
    """
    Documentation

    """

    def __init__(self, config_file=None):

        if config_file:
            with open(config_file, 'r') as f:
                c = yaml.load(f.read())
        else:
            c = {}

        self._assign_properties(c)

    def _assign_properties(self, c):

        for p in CONF:
            if CONF[p]['type'] == bool:
                if os.environ.get(CONF[p]['env']) is not None:
                    v = os.environ.get(CONF[p]['env'])
                elif c.get(p) is not None:
                    v = c.get(p)
                else:
                    v = CONF[p]['default']
                v = ast.literal_eval(str(v).title())
            else:
                v = os.environ.get(CONF[p]['env']) or c.get(p) or CONF[p]['default']
                v = CONF[p]['type'](v)
            setattr(self, p, v)
