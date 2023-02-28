#!/usr/bin/env python3

import socket
import os


hostname = socket.gethostname()
ipv4_address = os.popen("curl -4 icanhazip.com").read().strip()
ipv6_address = os.popen("curl -6 icanhazip.com").read().strip()

netplan_config = """
network:
    version: 2
    ethernets:
        enp1s0:
            accept-ra: true
            dhcp4: true
            dhcp6: true
            set-name: enp1s0
            addresses:
              - "2001:ddb::1/48"
"""

open("/etc/netplan/99-ron.yaml", "w").write(netplan_config)

os.system("netplan apply")

os.system("apt install -y bird")

bird6_config = """
router id $ipv4$;

protocol static {
	route 2001:ddb::/48 blackhole;
}

filter bgp_out {
    if net = 2001:ddb::/48 then {
        accept;
    }
    # if net = 2a04:b905::/33 then {
    #     bgp_community.add((20473,6000));
    #     accept;
    # }
	# if net = 2001:ddb::/48 then {
	#     accept;
	# }
    reject;
}

protocol bgp vultr
{
	local as 211321;
	source address $ipv6$;
	import all;
	export filter bgp_out;
	graceful restart on;
	multihop 2;
	neighbor 2001:19f0:ffff::1 as 64515;
	password "Ahxaen5EeTheetiuphu8";
}
"""
bird6_config = bird6_config.replace("$ipv4$", ipv4_address)
bird6_config = bird6_config.replace("$ipv6$", ipv6_address)

open("/etc/bird/bird6.conf", "w").write(bird6_config)

os.system("systemctl restart bird")
os.system("systemctl restart bird6")

