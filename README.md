Briefpost
=========

This is a terraform that sets up servers in most available Vultr locations (see terraform.tfvars.example for the precise locations), points an AAAA record to them, and makes them execute a script (setup-instance.py) that sets up NSD, nginx, and BIRD.

The DNS is hosted at DigitalOcean, because Vultr does not support subdomains.