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
variable "anycast_ip" {}
variable "anycast_prefix" {}
variable "anycast6_ip" {}
variable "anycast6_prefix" {}
variable "anycast_valid_ip" {}
variable "anycast6_valid_ip" {}
variable "invalid_more_specific_prefix" {}
variable "invalid6_more_specific_prefix" {}
variable "ssh_private_key" {}

variable "regions" {}

provider "vultr" {
  api_key = var.vultr_api_key
  rate_limit = 100
  retry_limit = 3
}

provider "digitalocean" {
  token = var.do_api_key
}

resource "digitalocean_record" "anycast_aaaa" {
  name = "test"
  domain = var.parent_fqdn
  type = "NS"
  ttl = 60
  value = "test-ns.${var.parent_fqdn}."
}

resource "digitalocean_record" "anycast6_ns" {
  name = "test-ns"
  domain = var.parent_fqdn
  type = "AAAA"
  ttl = 60
  value = split("/", var.anycast6_ip)[0]
}

resource "digitalocean_record" "instance_aaaa" {
  for_each = tomap(var.regions)
  name = each.key
  domain = var.parent_fqdn
  type = "AAAA"
  ttl = 60
  value = vultr_instance.instance[each.key].v6_main_ip
}

data "template_file" "setup-instance" {
  template = file("setup-instance.py")

  vars = {
    anycast_ip = var.anycast_ip
    anycast_prefix = var.anycast_prefix
    anycast6_ip = var.anycast6_ip
    anycast6_prefix = var.anycast6_prefix
    parent_fqdn = var.parent_fqdn
    ssh_private_key = var.ssh_private_key
    anycast_valid_ip = var.anycast_valid_ip
    anycast6_valid_ip = var.anycast6_valid_ip
    invalid_more_specific_prefix = var.invalid_more_specific_prefix
    invalid6_more_specific_prefix = var.invalid6_more_specific_prefix
  }
}

resource "vultr_instance" "instance" {
  for_each = tomap(var.regions)
  region = "${each.key}"
  plan = "${each.value}"
  os_id = 1743 // Ubuntu 22.04
  enable_ipv6 = true
  hostname = "${each.key}.${var.parent_fqdn}"
  label = "${each.key}.${var.parent_fqdn}"
  tags = ["briefpost"]
  user_data = data.template_file.setup-instance.rendered
}
