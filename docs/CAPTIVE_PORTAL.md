# Captive Portal Guide

## MikroTik
- Preloader enables Hotspot and walled-garden for your domain.
- Ensure DNS points `portal.getupsoft.com.do` to MikroTik LAN IP or your Odoo host.
- For the Odoo-hosted portal, use `login-by=http-pap` in the Hotspot profile.

## Odoo
- Use `isp_captive_portal` module to manage vouchers and Hotspot users.
- Auto-provision can be enabled via System Parameters.

## Portal URL
- Odoo captive login page: `/captive`

## Walled Garden
Add your portal domain to the walled-garden list so clients can reach it without login.
