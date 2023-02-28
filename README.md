This is a terraform that sets up servers in all available Vultr locations (see terraform.tfvars.example), points an AAAA record to them, and makes them execute a script (setup-instance.py) that sets up BIRD.

The DNS is hosted at DigitalOcean, because Vultr does not support subdomains.