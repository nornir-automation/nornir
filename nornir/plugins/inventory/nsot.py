import os
from typing import Any

from nornir.core.deserializer.inventory import Inventory, InventoryElement

import requests


class NSOTInventory(Inventory):
    """
    Inventory plugin that uses `nsot <https://github.com/dropbox/nsot>`_ as backend.

    Note:
        An extra attribute ``site`` will be assigned to the host. The value will be
        the name of the site the host belongs to.

    Environment Variables:
        * ``NSOT_URL``: Corresponds to nsot_url argument
        * ``NSOT_EMAIL``: Corresponds to nsot_email argument
        * ``NSOT_AUTH_HEADER``: Corresponds to nsot_auth_header argument
        * ``NSOT_SECRET_KEY``: Corresponds to nsot_secret_key argument

    Arguments:
        flatten_attributes: Assign host attributes to the root object. Useful
            for filtering hosts.
        nsot_url: URL to nsot's API (defaults to ``http://localhost:8990/api``)
        nsot_email: email for authtication (defaults to admin@acme.com)
        nsot_auth_header: String for auth_header authentication (defaults to X-NSoT-Email)
        nsot_secret_key: Secret Key for auth_token method. If given auth_token
            will be used as auth_method.
    """

    def __init__(
        self,
        nsot_url: str = "",
        nsot_email: str = "",
        nsot_secret_key: str = "",
        nsot_auth_header: str = "",
        flatten_attributes: bool = True,
        *args: Any,
        **kwargs: Any
    ) -> None:
        nsot_url = nsot_url or os.environ.get("NSOT_URL", "http://localhost:8990/api")
        nsot_email = nsot_email or os.environ.get("NSOT_EMAIL", "admin@acme.com")
        secret_key = nsot_secret_key or os.environ.get("NSOT_SECRET_KEY")

        if secret_key:
            data = {"email": nsot_email, "secret_key": secret_key}
            res = requests.post("{}/authenticate/".format(nsot_url), data=data)
            auth_token = res.json().get("auth_token")
            headers = {
                "Authorization": "AuthToken {}:{}".format(nsot_email, auth_token)
            }

        else:
            nsot_auth_header = nsot_auth_header or os.environ.get(
                "NSOT_AUTH_HEADER", "X-NSoT-Email"
            )
            headers = {nsot_auth_header: nsot_email}

        devices = requests.get("{}/devices".format(nsot_url), headers=headers).json()
        sites = requests.get("{}/sites".format(nsot_url), headers=headers).json()
        interfaces = requests.get(
            "{}/interfaces".format(nsot_url), headers=headers
        ).json()

        # We resolve site_id and assign "site" variable with the name of the site
        for d in devices:
            d["data"] = {"site": sites[d["site_id"] - 1]["name"], "interfaces": {}}

            remove_keys = []
            for k, v in d.items():
                if k not in InventoryElement().__fields__:
                    remove_keys.append(k)
                    d["data"][k] = v
            for r in remove_keys:
                d.pop(r)

            if flatten_attributes:
                # We assign attributes to the root
                for k, v in d["data"].pop("attributes").items():
                    d["data"][k] = v

        # We assign the interfaces to the hosts
        for i in interfaces:
            devices[i["device"] - 1]["data"]["interfaces"][i["name"]] = i

        # Finally the inventory expects a dict of hosts where the key is the hostname
        hosts = {d["hostname"]: d for d in devices}
        super().__init__(hosts=hosts, groups={}, defaults={}, *args, **kwargs)
