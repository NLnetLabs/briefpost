#!/usr/bin/env python3

import socket
import os


hostname = socket.gethostname()
# TODO: Read these from the machine rather than rely on a remote server
ipv4_address = os.popen("curl -4 icanhazip.com").read().strip()
ipv6_address = os.popen("curl -6 icanhazip.com").read().strip()

anycast_ip = '${anycast_ip}'
anycast_prefix = '${anycast_prefix}'

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
              - "$anycast_ip$":
                  lifetime: 0
"""
# The lifetime trick above makes it so that normal traffic (apt, curl) 
# will use the default non-anycast address by default

netplan_config = netplan_config.replace("$anycast_ip$", anycast_ip)
netplan_config = netplan_config.replace("$anycast_prefix$", anycast_prefix)
netplan_config = netplan_config.replace("$ipv4$", ipv4_address)
netplan_config = netplan_config.replace("$ipv6$", ipv6_address)

open("/etc/netplan/99-ron.yaml", "w").write(netplan_config)

os.system("netplan apply")

# TODO: Set up NSD, ensure it listens, then continue setting up BIRD

os.system("apt-get install -y bird")

# TODO: Do the same below for BIRD IPv4

bird6_config = """
router id $ipv4$;

protocol static {
	route $anycast_prefix$ blackhole;
}

filter bgp_out {
    if net = $anycast_prefix$ then {
        accept;
    }
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
bird6_config = bird6_config.replace("$anycast_ip$", anycast_ip)
bird6_config = bird6_config.replace("$anycast_prefix$", anycast_prefix)
bird6_config = bird6_config.replace("$ipv4$", ipv4_address)
bird6_config = bird6_config.replace("$ipv6$", ipv6_address)

open("/etc/bird/bird6.conf", "w").write(bird6_config)

os.system("systemctl restart bird")
os.system("systemctl restart bird6")

