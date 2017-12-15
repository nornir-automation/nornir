import os
from builtins import super

from brigade.core.inventory import Inventory

import requests


class NSOTInventory(Inventory):
    """
    Inventory plugin that uses `nsot <https://github.com/dropbox/nsot>`_ as backend.

    Note:
        An extra attribute ``site`` will be assigned to the host. The value will be
        the name of the site the host belongs to.

    Environment Variables:
        * ``NSOT_URL``: URL to nsot's API (defaults to ``http://localhost:8990/api``)
        * ``NSOT_EMAIL``: email for authentication (defaults to admin@acme.com)

    Arguments:
        flatten_attributes (bool): Assign host attributes to the root object. Useful
            for filtering hosts.
    """

    def __init__(self, flatten_attributes=True, **kwargs):
        NSOT_URL = os.environ.get('NSOT_URL', 'http://localhost:8990/api')
        NSOT_EMAIL = os.environ.get('NSOT_EMAIL', 'admin@acme.com')

        headers = {'X-NSoT-Email': NSOT_EMAIL}
        devices = requests.get('{}/devices'.format(NSOT_URL), headers=headers).json()
        sites = requests.get('{}/sites'.format(NSOT_URL), headers=headers).json()
        interfaces = requests.get('{}/interfaces'.format(NSOT_URL), headers=headers).json()

        # We resolve site_id and assign "site" variable with the name of the site
        for d in devices:
            d['site'] = sites[d['site_id'] - 1]['name']
            d['interfaces'] = {}

            if flatten_attributes:
                # We assign attributes to the root
                for k, v in d.pop('attributes').items():
                    d[k] = v

        # We assign the interfaces to the hosts
        for i in interfaces:
            devices[i['device'] - 1]['interfaces'][i['name']] = i

        # Finally the inventory expects a dict of hosts where the key is the hostname
        devices = {d['hostname']: d for d in devices}

        super().__init__(devices, None, **kwargs)
