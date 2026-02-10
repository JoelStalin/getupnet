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
- MikroTik preconfig profiles are managed in Odoo: `ISP > Configuration > MikroTik Preconfig`.

## MAC onboarding (optional)
For DHCP/bridge discovery, an HTTP endpoint is available at `/isp/mac_onboarding`:
- Set `isp_core.mac_onboarding_token` (default is CHANGEME).
- Optional auto-create:
  - `isp_core.mac_auto_create = 1`
  - `isp_core.mac_default_plan_id = <plan_id>`
The endpoint expects query params: `mac`, `ip`, `bound` (0/1), and optional `sector`, `hostname`.

## Preloader
See tools/mikrotik_preloader/README.md
The preloader can fetch routeros.config from Odoo first (see `odoo.fetch_preconfig` in config.yaml).

## Call-home (MikroTik → Odoo)
The preloader can configure a "call-home" script so each MikroTik reports its public IP to your domain.
Defaults (safe for dev):
- URL: `https://isp.getupsoft.com.do/isp/mikrotik/checkin`
- Token (default): `GETUPNET-DEFAULT-TOKEN` (override with `ISP_HOME_TOKEN`)
- Extra allowlist from env: `ODOO_PUBLIC_IPS` (comma-separated)

Recommended envs:
- `ISP_HOME_TOKEN` (production token)
- `ODOO_PUBLIC_IPS` (public IP(s) of your Odoo server)

## Selenium
Skeleton under tests/isp_selenium

Quick run (Windows + Docker):
1. `docker compose up -d --build`
2. `python -m venv .venv`
3. `.venv\\Scripts\\activate`
4. `pip install -r tests/isp_selenium/requirements.txt`
5. Set env:
   - `SELENIUM_REMOTE_URL=http://localhost:4444/wd/hub`
   - `ODOO_BASE_URL=http://host.docker.internal:8069`
   - `ODOO_ADMIN_USER=admin`
   - `ODOO_ADMIN_PASS=admin`
6. Run: `pytest tests/isp_selenium -k test_login_admin`

Note: If you run the browser locally (no Selenium container), unset `SELENIUM_REMOTE_URL`.

## Manuals and Guides
- docs/IMPLEMENTATION_GUIDE.md
- docs/MIKROTIK_PRELOADER.md
- docs/OLT_STICK_GUIDE.md
- docs/ODOO_MAC_ONBOARDING.md
- docs/CAPTIVE_PORTAL.md
- docs/TROUBLESHOOTING.md
- docs/TEST_CHECKLIST.md
- docs/ISP_SOLUTION.md
- docs/ISP_DATA_DICTIONARY.md
- docs/DEPLOYMENT.md
- docs/UAT_SCRIPT.md
