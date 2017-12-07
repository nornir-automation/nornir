import os
import yaml


CONF = {
    'num_workers': {
        'description': 'Number of Brigade worker processes',
        'environment': 'BRIGADE_NUM_WORKERS',
        'default': 20,
    },
    'ssh_config_file': {
        'description': 'User ssh_config_file',
        'environment': 'BRIGADE_SSH_CONFIG_FILE',
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
            v = os.environ.get(CONF[p]['environment']) or c.get(p) or CONF[p]['default']
            setattr(self, p, v)
