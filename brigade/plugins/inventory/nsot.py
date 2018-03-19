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
        * ``nsot_url``: URL to nsot's API (defaults to ``http://localhost:8990/api``)
        * ``nsot_email``: email for authentication (defaults to admin@acme.com)
        * ``nsot_auth_method``: auth_header or auth_token
        * ``nsot_auth_header``: used for auth_header authentication method
        * ``nsot_secret_key``: needed for auth_method = auth_token

    Arguments:
        flatten_attributes (bool): Assign host attributes to the root object. Useful
            for filtering hosts.
    """

    def __init__(self, nsot_url="", nsot_email="", nsot_auth_method="",
                 nsot_secret_key="", nsot_auth_header="", flatten_attributes=True, **kwargs):
        nsot_url = nsot_url or os.environ.get('NSOT_URL', 'http://localhost:8990/api')
        nsot_email = nsot_email or os.environ.get('NSOT_EMAIL', 'admin@acme.com')
        nsot_auth_method = nsot_auth_method or os.environ.get('NSOT_AUTH_METHOD', 'auth_header')

        if nsot_auth_method == "auth_token":
            nsot_secret_key = nsot_secret_key or os.environ.get('NSOT_SECRET_KEY', 'empty')
            data = {'email': nsot_email, 'secret_key': nsot_secret_key}
            res = requests.post('{}/authenticate/'.format(nsot_url), data=data)
            auth_token = res.json().get('auth_token')
            headers = {'Authorization': 'AuthToken {}:{}'.format(nsot_email, auth_token)}

        else:
            nsot_auth_header = nsot_auth_header or os.environ.get('NSOT_AUTH_HEADER',
                                                                  'X-NSoT-Email')
            headers = {nsot_auth_header: nsot_email}

        devices = requests.get('{}/devices'.format(nsot_url), headers=headers).json()
        sites = requests.get('{}/sites'.format(nsot_url), headers=headers).json()
        interfaces = requests.get('{}/interfaces'.format(nsot_url), headers=headers).json()

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
