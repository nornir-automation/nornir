import os

from brigade.core.inventory import Inventory

import requests


class NSOTInventory(Inventory):

    def __init__(self, **kwargs):
        NSOT_URL = os.environ.get('NSOT_URL', 'http://localhost:8990/api')
        NSOT_EMAIL = os.environ.get('NSOT_EMAIL', 'admin@acme.com')

        headers = {'X-NSoT-Email': NSOT_EMAIL}
        devices = requests.get('{}/devices'.format(NSOT_URL), headers=headers).json()
        sites = requests.get('{}/sites'.format(NSOT_URL), headers=headers).json()

        # We resolve site_id and assign "site" variable with the name of the sitee
        for d in devices:
            d['site'] = sites[d['site_id'] - 1]['name']

        # We assign the interfaces to the hosts
        for i in requests.get('{}/interfaces'.format(NSOT_URL), headers=headers).json():
            if "interfaces" not in devices[i['device'] - 1]:
                devices[i['device'] - 1]['interfaces'] = {}
            devices[i['device'] - 1]['interfaces'][i['name']] = i

        devices = {d['hostname']: d for d in devices}

        super().__init__(devices, None, **kwargs)
