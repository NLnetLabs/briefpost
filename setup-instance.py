#!/usr/bin/env python3

import socket
import os
import time


hostname = socket.gethostname()
# TODO: Read these from the machine rather than rely on a remote server
ipv4_address = os.popen("curl -4 icanhazip.com").read().strip()
ipv6_address = os.popen("curl -6 icanhazip.com").read().strip()

anycast_ip = '${anycast_ip}'
anycast_prefix = '${anycast_prefix}'
anycast_ip_absolute = anycast_ip.split("/")[0]
parent_fqdn = '${parent_fqdn}'

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

os.system("apt-get install -y nginx")

open("/var/www/html/index.html", "w").write("<h1>" + hostname + "</h1>")

os.system("apt-get install -y nsd")

nsd_config = """
server:
    ip-address: $anycast_ip_absolute$

zone:
    name: test.$parent_fqdn$
    zonefile: /etc/nsd/test.$parent_fqdn$.zone
"""
nsd_config = nsd_config.replace("$anycast_ip_absolute$", anycast_ip_absolute)
nsd_config = nsd_config.replace("$parent_fqdn$", parent_fqdn)
open("/etc/nsd/nsd.conf.d/99-ron.conf", "w").write(nsd_config)

nsd_zone = """
$TTL 60                                         ; 1 hour default TTL
test.$parent_fqdn$.    IN      SOA      test.$parent_fqdn$. admin.$parent_fqdn$. (
                                2023022816      ; Serial
                                10800           ; Refresh
                                3600            ; Retry
                                60              ; Expire
                                60              ; Negative Response TTL
                        )

; NS records
                IN      NS      test.$parent_fqdn$.
                IN      NS      test.$parent_fqdn$.

; AAAA records
                IN      AAAA    $anycast_ip_absolute$

; TXT records
                IN      TXT     "$hostname$"

"""
nsd_zone = nsd_zone.replace("$parent_fqdn$", parent_fqdn)
nsd_zone = nsd_zone.replace("$anycast_ip_absolute$", anycast_ip_absolute)
nsd_zone = nsd_zone.replace("$hostname$", hostname)
open("/etc/nsd/test." + parent_fqdn + ".zone", "w").write(nsd_zone)

while True:
    os.system("systemctl restart nsd")
    hostname_dns = os.popen(f"dig TXT test.{parent_fqdn} @{anycast_ip_absolute} +short").read().strip()
    if hostname == hostname_dns.strip("\""):
        break
    else:
        print("NSD not yet started, trying again in 15 seconds...")
        time.sleep(15)


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

