# MikroTik preloader

## Purpose
Auto-onboard MikroTik devices, apply sector network config (Starlink WAN, LAN bridge, DHCP, Hotspot),
and register them in Odoo. It also sets a DHCP lease-script to notify Odoo when a new ONU/ONT (or client
CPE behind the ONU) requests an IP address.

## Setup
1. Copy config.example.yaml to config.yaml
2. Export secrets:
   - MIKROTIK_MGMT_PASS
   - ODOO_ADMIN_PASS
   - ISP_MAC_TOKEN (matches isp_core.mac_onboarding_token in Odoo)
3. Install deps:
   - pip install -r requirements.txt

## Run
python preloader.py --config config.yaml

## Notes
- This script configures the MikroTik only. The GPON OLT stick is managed by its own software.
- DHCP-based discovery sees the MAC/IP that requests DHCP (often the CPE behind the ONU).
- For captive portal with Odoo domain, set `hotspot_dns_name` and `hotspot_walled_garden` in config.
