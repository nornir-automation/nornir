import os

from nornir.plugins.tasks import text


BASE_DIR = os.path.dirname(os.path.realpath(__file__))
INPUT_POLICY = f"{BASE_DIR}/test_data/nornir.pol"
DEFINITIONS_DIR = f"{BASE_DIR}/test_data/def"


ARISTA_ACL = """! $Id:$
! $Date:$
! $Revision:$
no ip access-list LOOPBACK
ip access-list LOOPBACK
 remark $Id:$
 remark Sample multitarget loopback filter


 remark accept-icmp
 permit icmp any any


 remark accept-traceroute
 remark Allow inbound traceroute from any source.
 remark Owner: jeff
 permit udp any any range 33434 33534


 remark accept-ospf
 remark Allow outbound OSPF traffic from other RFC1918 routers.
 permit ospf 10.0.0.0/8 any
 permit ospf 172.16.0.0/12 any
 permit ospf 192.168.0.0/16 any


 remark discard-default
 deny ip any any

exit
"""

JUNIPER_ACL = """firewall {
    family inet {
        replace:
        /*
        ** $Id:$
        ** $Date:$
        ** $Revision:$
        **
        ** Sample multitarget loopback filter
        */
        filter LOOPBACK {
            interface-specific;
            term accept-icmp {
                from {
                    protocol icmp;
                }
                then {
                    count icmp-loopback;
                    policer rate-limit-icmp;
                    accept;
                }
            }
            /*
            ** Allow inbound traceroute from any source.
            ** Owner: jeff
            */
            term accept-traceroute {
                from {
                    protocol udp;
                    destination-port 33434-33534;
                }
                then {
                    count inbound-traceroute;
                    policer rate-limit-to-router;
                    accept;
                }
            }
            /*
            ** Allow outbound OSPF traffic from other RFC1918 routers.
            */
            term accept-ospf {
                from {
                    source-address {
                        /* non-public */
                        10.0.0.0/8;
                        /* non-public */
                        172.16.0.0/12;
                        /* non-public */
                        192.168.0.0/16;
                    }
                    protocol ospf;
                }
                then {
                    count ospf;
                    accept;
                }
            }
            term discard-default {
                then {
                    count discard-default;
                    discard;
                }
            }
        }
    }
}
"""


def gen_acl(task):
    return task.run(
        task=text.capirca_acl,
        platform=task.host["capirca"]["platform"],
        policy_name=INPUT_POLICY,
        def_dir=DEFINITIONS_DIR,
        exp=task.host["capirca"]["expiration"],
        shade_check=task.host["capirca"]["shade_check"],
        optimize=task.host["capirca"]["optimize"],
    )


class Test:
    def test_gen_acl(self, nornir):
        hosts = nornir.filter(site="site2")
        result = hosts.run(task=gen_acl)
        got = result["dev3.group_2"][0].result[0].result
        assert got == ARISTA_ACL
        got = result["dev4.group_2"][0].result[0].result
        assert got == JUNIPER_ACL

    def test_platform_not_supported(self, nornir):
        hosts = nornir.filter(name="dev3.group_2")
        hosts.inventory.hosts["dev3.group_2"].data["capirca"]["platform"] = "crisco"
        result = hosts.run(task=gen_acl)
        assert result["dev3.group_2"][0].failed

    def test_platform_target_not_found(self, nornir):
        hosts = nornir.filter(name="dev3.group_2")
        hosts.inventory.hosts["dev3.group_2"].data["capirca"]["platform"] = "cisco"
        result = hosts.run(task=gen_acl)
        assert result["dev3.group_2"][0].failed
