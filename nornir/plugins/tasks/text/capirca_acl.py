from capirca.lib import arista
from capirca.lib import aruba
from capirca.lib import brocade
from capirca.lib import cisco
from capirca.lib import ciscoasa
from capirca.lib import ciscoxr
from capirca.lib import ipset
from capirca.lib import iptables
from capirca.lib import juniper
from capirca.lib import junipersrx
from capirca.lib import naming
from capirca.lib import nftables
from capirca.lib import paloaltofw
from capirca.lib import policy
from capirca.lib import srxlo

from nornir.core.task import Result, Task

from typing import Set


class CapircaError(Exception):
    """Base Capirca error."""

    pass


class ACLParserError(CapircaError):
    """Raised when policy parsing fails."""

    pass


class ACLGeneratorError(CapircaError):
    """Raised when ACL generation fails."""

    pass


class PlatformNotSupported(CapircaError):
    """Raised when a platform has no associated ACL generator."""

    pass


class PlatformTargetNotFound(CapircaError):
    """Raised when a platform is not configured as a target in a policy file."""

    pass


ACL_GENERATORS = {
    "arista": arista.Arista,
    "aruba": aruba.Aruba,
    "brocade": brocade.Brocade,
    "cisco": cisco.Cisco,
    "ciscoasa": ciscoasa.CiscoASA,
    "ciscoxr": ciscoxr.CiscoXR,
    "ipset": ipset.Ipset,
    "iptables": iptables.Iptables,
    "juniper": juniper.Juniper,
    "junipersrx": junipersrx.JuniperSRX,
    "nftables": nftables.Nftables,
    "paloaltofw": paloaltofw.PaloAltoFW,
    "srxlo": srxlo.SRXlo,
}


def capirca_acl(
    task: Task,
    platform: str,
    policy_name: str,
    def_dir: str,
    exp: int = 2,
    shade_check: bool = False,
    optimize: bool = False,
) -> Result:
    """
    Renders a vendor-specific ACL from a Capirca policy file.

    Arguments:
        platform (str): platform type; valid platform types are:
            * arista
            * aruba
            * brocade
            * cisco
            * ciscoasa
            * ciscoxr
            * ipset
            * iptables
            * juniper
            * junipersrx
            * nftables
            * paloaltofw
            * srxlo
        policy_name (str): path to the policy file to be rendered
        def_dir (str): path to the naming definition files
        exp (int): generate warning when a term is set to expire within exp weeks
        shade_check (bool): check terms are not shaded by prior policy terms
        optimize (bool): enable ACL optimization

    Returns:
        Result object with the following attributes set:
          * result (``str``): rendered ACL
    """
    definitions = naming.Naming(def_dir)

    try:
        pol = policy.ParseFile(
            policy_name,
            definitions,
            optimize=optimize,
            base_dir=".",
            shade_check=shade_check,
        )
    except policy.ShadingError:
        raise
    except (policy.Error, naming.Error):
        raise ACLParserError("error parsing policy")

    platforms: Set[str] = set()
    for header in pol.headers:
        platforms.update(header.platforms)

    if platform not in platforms:
        raise PlatformTargetNotFound(
            f"platform {platform} not listed in policy file targets"
        )

    if platform in ACL_GENERATORS:
        gen = ACL_GENERATORS[platform]
    else:
        raise PlatformNotSupported(f"platform {platform} is not supported")

    try:
        acl = gen(pol, exp)
        return Result(host=task.host, result=str(acl))
    except (
        arista.Error,
        aruba.Error,
        brocade.Error,
        cisco.Error,
        ciscoasa.Error,
        ciscoxr.Error,
        ipset.Error,
        iptables.Error,
        juniper.Error,
        junipersrx.Error,
        nftables.Error,
        paloaltofw.Error,
        srxlo.Error,
    ):
        raise ACLGeneratorError(f"unable to generate acl for {policy_name}")
