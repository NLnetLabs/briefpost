#!/usr/bin/env python3

import socket
import os
import time


hostname = socket.gethostname()
# TODO: Read these from the machine rather than rely on a remote server
ipv4_address = os.popen("curl -4 icanhazip.com").read().strip()
ipv6_address = os.popen("curl -6 icanhazip.com").read().strip()

anycast6_ip = '${anycast6_ip}'
anycast6_prefix = '${anycast6_prefix}'
anycast6_ip_absolute = anycast6_ip.split("/")[0]

anycast_ip = '${anycast_ip}'
anycast_prefix = '${anycast_prefix}'
anycast_ip_absolute = anycast_ip.split("/")[0]

parent_fqdn = '${parent_fqdn}'

ssh_private_key = """${ssh_private_key}"""

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
              - "$anycast6_ip$":
                  lifetime: 0
              - "$anycast_ip$":
                  lifetime: 0
"""
# The lifetime trick above makes it so that normal traffic (apt, curl) 
# will use the default non-anycast address by default

netplan_config = netplan_config.replace("$anycast6_ip$", anycast6_ip)
netplan_config = netplan_config.replace("$anycast_ip$", anycast_ip)

open("/etc/netplan/99-briefpost.yaml", "w").write(netplan_config)

os.system("netplan apply")

os.system("apt-get install -y ldnsutils")

# Disable the firewall... This could probably be done cleaner
os.system("ufw disable")

open("/tmp/ssh-key", "w").write(ssh_private_key)
os.system("chmod 0600 /tmp/ssh-key")

while True:
    os.system("scp -o \"StrictHostKeyChecking no\" -i /tmp/ssh-key -pr \"root@manson.nlnetlabs.nl:/root/rpkitest.nlnetlabs.nl\" /root")
    # This copies it to the folder /etc/nsd, because /etc/nsd does not exist yet.
    os.system("scp -o \"StrictHostKeyChecking no\" -i /tmp/ssh-key -pr \"root@manson.nlnetlabs.nl:/etc/nsd/ldns-signed4invalid\" /etc/nsd")

    if os.path.exists("/root/rpkitest.nlnetlabs.nl") and os.path.exists("/etc/nsd"):
        break
    else:
        print("Something went wrong copying files, retrying in 15 seconds...")
        time.sleep(15)

os.system("mv /etc/nsd/ldns-signed4invalid /etc/nsd/rpkitest.nlnetlabs.nl")
os.system("cd /etc/nsd/rpkitest.nlnetlabs.nl && make resign")

os.system("apt-get install -y nginx")

nginx_config = """
server {
    listen $anycast_ip_absolute$:443 ssl;
    listen [$anycast6_ip_absolute$]:443 ssl;
    server_name rpkitest.nlnetlabs.nl;
    error_log  /var/log/nginx.error.log  warn;
    access_log /var/log/nginx.log;
    ssl_certificate /root/rpkitest.nlnetlabs.nl/fullchain.pem;
    ssl_certificate_key /root/rpkitest.nlnetlabs.nl/privkey.pem;

    location / {
        if ($request_method = 'GET') {
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
            add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range' always;
        }
       default_type application/json;
       return 200 '{"rpki-valid-passed":true,"rpki-invalid-passed":false,"ip":"$remote_addr","pop":"$hostname$"}';
    }
}
"""
nginx_config = nginx_config.replace("$anycast_ip_absolute$", anycast_ip_absolute)
nginx_config = nginx_config.replace("$anycast6_ip_absolute$", anycast6_ip_absolute)
nginx_config = nginx_config.replace("$hostname$", hostname)

open("/etc/nginx/sites-enabled/default", "w").write(nginx_config)

os.system("systemctl restart nginx")

os.system("apt-get install -y nsd")

nsd_config = """
server:
    ip-address: $anycast6_ip_absolute$
    ip-address: $anycast_ip_absolute$

zone:
    name: test.$parent_fqdn$
    zonefile: /etc/nsd/test.$parent_fqdn$.zone

zone:
    name: rpkitest.nlnetlabs.nl
    zonefile: /etc/nsd/rpkitest.nlnetlabs.nl.signed

zone:
    name: rpkitest4.nlnetlabs.nl
    zonefile: /etc/nsd/rpkitest4.nlnetlabs.nl.signed

zone:
    name: rpkitest6.nlnetlabs.nl
    zonefile: /etc/nsd/rpkitest6.nlnetlabs.nl.signed
"""
nsd_config = nsd_config.replace("$anycast_ip_absolute$", anycast_ip_absolute)
nsd_config = nsd_config.replace("$anycast6_ip_absolute$", anycast6_ip_absolute)
nsd_config = nsd_config.replace("$parent_fqdn$", parent_fqdn)
open("/etc/nsd/nsd.conf.d/99-briefpost.conf", "w").write(nsd_config)

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
                IN      AAAA    $anycast6_ip_absolute$

; TXT records
                IN      TXT     "$hostname$"

"""
nsd_zone = nsd_zone.replace("$parent_fqdn$", parent_fqdn)
nsd_zone = nsd_zone.replace("$anycast6_ip_absolute$", anycast6_ip_absolute)
nsd_zone = nsd_zone.replace("$hostname$", hostname)
open("/etc/nsd/test." + parent_fqdn + ".zone", "w").write(nsd_zone)

while True:
    os.system("systemctl restart nsd")
    hostname_dns = os.popen(f"dig TXT test.{parent_fqdn} @{anycast6_ip_absolute} +short").read().strip()
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
	route $anycast6_prefix$ blackhole;
}

filter bgp_out {
    if net = $anycast6_prefix$ then {
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
bird6_config = bird6_config.replace("$anycast6_ip$", anycast6_ip)
bird6_config = bird6_config.replace("$anycast6_prefix$", anycast6_prefix)
bird6_config = bird6_config.replace("$ipv4$", ipv4_address)
bird6_config = bird6_config.replace("$ipv6$", ipv6_address)

open("/etc/bird/bird6.conf", "w").write(bird6_config)

bird_config = """
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
	source address $ipv4$;
	import all;
	export filter bgp_out;
	graceful restart on;
	multihop 2;
	neighbor 169.254.169.254 as 64515;
	password "Ahxaen5EeTheetiuphu8";
}
"""
bird_config = bird_config.replace("$anycast_ip$", anycast_ip)
bird_config = bird_config.replace("$anycast_prefix$", anycast_prefix)
bird_config = bird_config.replace("$ipv4$", ipv4_address)

open("/etc/bird/bird.conf", "w").write(bird_config)


os.system("systemctl restart bird")
os.system("systemctl restart bird6")

