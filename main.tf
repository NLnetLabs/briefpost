terraform {
  required_providers {
    vultr = {
      source = "vultr/vultr"
      version = "2.12.1"
    }
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "2.26.0"
    }
  }
}

variable "vultr_api_key" {}
variable "do_api_key" {}
variable "parent_fqdn" {}

variable "regions" {}

provider "vultr" {
  api_key = var.vultr_api_key
  rate_limit = 100
  retry_limit = 3
}

provider "digitalocean" {
  token = var.do_api_key
}

resource "digitalocean_record" "instance_aaaa" {
  for_each = toset(var.regions)
  name = each.key
  domain = var.parent_fqdn
  type = "AAAA"
  ttl = 300
  value = vultr_instance.instance[each.key].v6_main_ip
}

# data "template_file" "setup-instance" {
#   for_each = toset(var.regions)

#   template = file("setup-instance.py")

#   vars = {
#     hostname = vultr_instance.instance[each.key].hostname
#     ipv4_address = vultr_instance.instance[each.key].main_ip
#     ipv6_address = vultr_instance.instance[each.key].v6_main_ip
#   }
# }

resource "vultr_instance" "instance" {
  for_each = toset(var.regions)
  region = "${each.key}"
  plan = "vc2-1c-1gb"
  os_id = 1743 // Ubuntu 22.04
  enable_ipv6 = true
  hostname = "${each.key}.ron.nlnetlabs.net"
  label = "${each.key}.ron.nlnetlabs.net"
  tags = ["ron"]
  user_data = file("setup-instance.py")
}