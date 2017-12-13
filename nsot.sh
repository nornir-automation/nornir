-x
nsot sites add --name site1

nsot attributes add --site-id 1 --resource-name device --name os
nsot attributes add --site-id 1 --resource-name device --name host
nsot attributes add --site-id 1 --resource-name device --name user
nsot attributes add --site-id 1 --resource-name device --name password --allow-empty
nsot attributes add --site-id 1 --resource-name device --name port

nsot devices add --site-id 1 --hostname rtr00-site1
nsot devices update --site-id 1 --id 1 -a os=eos -a host=127.0.0.1 -a user=vagrant -a password=vagrant -a port=12443
nsot devices add --site-id 1 --hostname rtr01-site1
nsot devices update --site-id 1 --id 2 -a os=junos -a host=127.0.0.1 -a user=vagrant -a password="" -a port=12203


nsot attributes add --site-id 1 --resource-name device --name asn
nsot attributes add --site-id 1 --resource-name device --name router_id

nsot devices update --site-id 1 --id 1 -a asn=65001 -a router_id=10.1.1.1
nsot devices update --site-id 1 --id 2 -a asn=65002 -a router_id=10.1.1.2

nsot attributes add --site-id 1 --resource-name network --name type
nsot networks add --site-id 1 --cidr 2001:db8:b33f::/64 -a type=loopbacks

nsot attributes add --site-id 1 --resource-name interface --name link_type
nsot attributes add --site-id 1 --resource-name interface --name connects_to_device
nsot attributes add --site-id 1 --resource-name interface --name connects_to_iface

nsot interfaces add --site-id 1 --device 1 --name lo0 --addresses 2001:db8:b33f::100/128 -a link_type=loopback -a connects_to_device=loopback -a connects_to_iface=lo0
nsot interfaces add --site-id 1 --device 2 --name lo0 --addresses 2001:db8:b33f::101/128 -a link_type=loopback -a connects_to_device=loopback -a connects_to_iface=lo0

nsot networks add --site-id 1 --cidr 2001:db8:caf3::/64 -a type=ptp
nsot networks add --site-id 1 --cidr 2001:db8:caf3::/127 -a type=ptp
nsot networks add --site-id 1 --cidr 2001:db8:caf3::2/127 -a type=ptp

nsot interfaces add --site-id 1 --device 1 --name et1 -a link_type=fabric -a connects_to_device=rtr01 -a connects_to_iface=ge-0/0/1 -c 2001:db8:caf3::
nsot interfaces add --site-id 1 --device 1 --name et2 -a link_type=fabric -a connects_to_device=rtr01 -a connects_to_iface=ge-0/0/2 -c 2001:db8:caf3::2

nsot interfaces add --site-id 1 --device 2 --name ge-0/0/1 -a link_type=fabric -a connects_to_device=rtr00 -a connects_to_iface=et1 -c 2001:db8:caf3::1
nsot interfaces add --site-id 1 --device 2 --name ge-0/0/2 -a link_type=fabric -a connects_to_device=rtr00 -a connects_to_iface=et2 -c 2001:db8:caf3::3

nsot sites add --name site2

nsot attributes add --site-id 2 --resource-name device --name os
nsot attributes add --site-id 2 --resource-name device --name host
nsot attributes add --site-id 2 --resource-name device --name user
nsot attributes add --site-id 2 --resource-name device --name password --allow-empty
nsot attributes add --site-id 2 --resource-name device --name port

nsot devices add --site-id 2 --hostname rtr00-site2
nsot devices update --site-id 2 --id 3 -a os=eos -a host=127.0.0.1 -a user=vagrant -a password=vagrant -a port=12443
nsot devices add --site-id 2 --hostname rtr01-site2
nsot devices update --site-id 2 --id 4 -a os=junos -a host=127.0.0.1 -a user=vagrant -a password="" -a port=12203


nsot attributes add --site-id 2 --resource-name device --name asn
nsot attributes add --site-id 2 --resource-name device --name router_id

nsot devices update --site-id 2 --id 3 -a asn=65001 -a router_id=10.1.1.1
nsot devices update --site-id 2 --id 4 -a asn=65002 -a router_id=10.1.1.2

nsot attributes add --site-id 2 --resource-name network --name type
nsot networks add --site-id 2 --cidr 2001:db8:f4c3::/64 -a type=loopbacks

nsot attributes add --site-id 2 --resource-name interface --name link_type
nsot attributes add --site-id 2 --resource-name interface --name connects_to_device
nsot attributes add --site-id 2 --resource-name interface --name connects_to_iface

nsot interfaces add --site-id 2 --device 3 --name lo0 --addresses 2001:db8:f4c3::100/128 -a link_type=loopback -a connects_to_device=loopback -a connects_to_iface=lo0
nsot interfaces add --site-id 2 --device 4 --name lo0 --addresses 2001:db8:f4c3::101/128 -a link_type=loopback -a connects_to_device=loopback -a connects_to_iface=lo0

nsot networks add --site-id 2 --cidr 2001:db8:dead::/64 -a type=ptp
nsot networks add --site-id 2 --cidr 2001:db8:dead::/127 -a type=ptp
nsot networks add --site-id 2 --cidr 2001:db8:dead::2/127 -a type=ptp

nsot interfaces add --site-id 2 --device 3 --name et1 -a link_type=fabric -a connects_to_device=rtr01 -a connects_to_iface=ge-0/0/1 -c 2001:db8:dead::
nsot interfaces add --site-id 2 --device 3 --name et2 -a link_type=fabric -a connects_to_device=rtr01 -a connects_to_iface=ge-0/0/2 -c 2001:db8:dead::2

nsot interfaces add --site-id 2 --device 4 --name ge-0/0/1 -a link_type=fabric -a connects_to_device=rtr00 -a connects_to_iface=et1 -c 2001:db8:dead::1
nsot interfaces add --site-id 2 --device 4 --name ge-0/0/2 -a link_type=fabric -a connects_to_device=rtr00 -a connects_to_iface=et2 -c 2001:db8:dead::3
