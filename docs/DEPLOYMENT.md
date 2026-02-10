# Deployment and Testing

## Local Setup (Docker)
1. `docker compose up --build`
2. Open Odoo at `http://localhost:8069` and create DB `isp`
3. Install modules in order:
- `isp_core`
- `isp_mikrotik`
- `isp_onu`
- `isp_captive_portal`
- `isp_billing`
- `isp_portal`

## Update Modules
- `docker compose run --rm odoo odoo -d isp -u isp_core,isp_billing --stop-after-init`
- `docker start getupnet-odoo-1`

## Selenium (E2E)
- Run from container:
```
docker exec getupnet-odoo-1 sh -lc "export ODOO_BASE_URL=http://odoo:8069 ODOO_RPC_URL=http://odoo:8069 ODOO_DB=isp ODOO_ADMIN_USER=admin ODOO_ADMIN_PASS=admin SELENIUM_REMOTE_URL=http://selenium:4444/wd/hub ISP_E2E=1; python3 -m pytest /mnt/tests/isp_selenium/test_flows.py -vv -x -s"
```

## System Parameters
- `isp_billing.transfer_review_hours = 48`
- `isp_billing.transfer_attention_hours = 24`
- `isp_billing.grace_days = 5`
- `isp_billing.suspend_after_days = 10`
- `isp_core.mac_onboarding_token = <TOKEN>`
- `isp_core.mac_auto_create = 1` (optional)
- `isp_core.mac_default_plan_id = <plan_id>`
- `isp_mikrotik.dry_run = 1` (use 0 for real provisioning)

## Preloader
- See `tools/mikrotik_preloader/README.md`

## UAT Script
- See `docs/UAT_SCRIPT.md`
