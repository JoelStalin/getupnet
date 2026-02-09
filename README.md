# GetUpNet ISP (Odoo 19)

This repo provides a full ISP stack on Odoo 19 with modules:
- isp_core
- isp_mikrotik
- isp_onu
- isp_captive_portal
- isp_billing
- isp_portal

## Quick start (Docker)
1. docker compose up --build
2. Open http://localhost:8069
3. Create a database
4. Install the ISP modules (start with isp_core, then the rest)
5. Optional: enable demo data when creating the database to load sample ISP records.

## Notes
- Default Odoo admin password in etc/odoo.conf is "admin". Change it for production.
- RouterOS integration uses librouteros installed in the custom Odoo image.
- Provisioning runs through isp.provisioning_job with a cron worker.
- Set these System Parameters in Odoo:
  - isp_mikrotik.dry_run = 1 (safe default). Set to 0 for real devices.
  - isp_mikrotik.default_api_user = odoo_noc (or your user)
  - isp_mikrotik.default_api_password = <secret>
- Sector-based record rules apply to NOC/Support/Field/Billing users. Assign `Allowed ISP Sectors` on the user form, or they will not see sector-bound records.

## Preloader
See tools/mikrotik_preloader/README.md

## Selenium
Skeleton under tests/selenium
