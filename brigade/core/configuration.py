import os

c = {
    'ssh_config_file': os.environ.get('BRIGADE_SSH_CONFIG_FILE') or
    os.path.join(os.path.expanduser("~"), ".ssh", "config"),
}


class Config:
    """
    Documentation

    """

    def __init__(self):
        self.ssh_config_file = c['ssh_config_file']
