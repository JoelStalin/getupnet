# Test Checklist

This checklist is for initial validation of the ISP stack (Starlink + MikroTik + OLT stick + ONU/ONT + Odoo).

## 1. Infra
1. Starlink has stable internet (ping + browsing).
2. MikroTik WAN connected to Starlink (e.g. `ether1`).
3. OLT stick connected to MikroTik LAN (bridge `br-pon` via `sfp1` or `ether2`).

## 2. Odoo (Docker)
1. Run Odoo: `docker compose up --build`.
2. Create database in Odoo.
3. Install modules in order:
1. `isp_core`
2. `isp_mikrotik`
3. `isp_onu`
4. `isp_captive_portal`
5. `isp_billing`
6. `isp_portal`
4. Create sector:
1. Code: `SEC-001-los_cacaos`
2. Name: `Los Cacaos`
5. Create a service plan (DHCP recommended).

## 3. Odoo System Parameters
1. `isp_core.mac_onboarding_token = <TOKEN>`
2. `isp_core.mac_auto_create = 1` (optional)
3. `isp_core.mac_default_plan_id = <plan_id>` (required if auto-create)
4. `isp_core.mac_auto_create_captive_user = 1` (optional)
5. `isp_core.mac_auto_provision_captive = 1` (optional)
6. `isp_core.mac_captive_default_profile = default`
7. `isp_mikrotik.dry_run = 1` (set to `0` for real devices)

## 4. Preloader
1. Copy `tools/mikrotik_preloader/config.example.yaml` -> `config.yaml`.
2. Verify config:
1. `sector_code: SEC-001-los_cacaos`
2. `wan_interface: ether1`
3. `lan_ports: [sfp1, ether2]`
4. `hotspot_dns_name: portal.getupsoft.com.do`
3. Export env vars:
1. `MIKROTIK_MGMT_PASS`
2. `ODOO_ADMIN_PASS`
3. `ISP_MAC_TOKEN` (same as `isp_core.mac_onboarding_token`)
4. Run:
1. `python tools/mikrotik_preloader/preloader.py --config tools/mikrotik_preloader/config.yaml`

## 5. OLT Stick
1. Open OLT software.
2. Ensure discovery is enabled.
3. Connect one ONU/ONT and verify it appears in the OLT dashboard.

## 6. Odoo MAC Onboarding
1. Wait for DHCP from ONU/ONT.
2. Go to Odoo -> ISP -> Operations -> MAC Profiles.
3. Confirm the MAC is present.
4. If auto-create is enabled, confirm:
1. Subscription created in ISP -> Subscriptions.
2. Captive user created (if enabled).
5. Optional test script:
1. Set `ISP_MAC_TOKEN` and `ODOO_URL`.
2. Run `python tools/test_mac_onboarding.py`.

## 7. Captive Portal
1. Confirm `portal.getupsoft.com.do` resolves to MikroTik LAN IP or Odoo host.
2. Confirm walled-garden includes the portal domain.
3. Test client redirection to portal.
4. Optional test script:
1. Set `ODOO_URL`.
2. Run `python tools/test_captive_portal.py`.

## 8. Provisioning
1. Activate a subscription in Odoo.
2. Verify job is `success` in ISP -> Provisioning Jobs.

## 9. Portal (Customer)
1. Login as a portal user.
2. Open `My Account -> ISP Summary` and confirm subscriptions and counts.
3. Open `My Account -> ISP Subscriptions` and verify list.
4. Open `My Account -> Invoices` and verify posted invoices appear.
5. Submit a plan change request (next cycle).
6. Report a bank transfer with attachment.
7. Create a fault ticket.

## 10. Dashboard / Reports
1. Open ISP -> Reports -> Dashboard.
2. Check KPI counts match data.
3. Open ISP -> Reports -> Subscriptions Report.
4. Open ISP -> Operations -> Transfer Payments.
5. Open ISP -> Operations -> Fault Tickets.

## 11. Troubleshooting Quick Checks
1. No MAC in Odoo:
1. Check DHCP lease-script on MikroTik.
2. Confirm token matches `isp_core.mac_onboarding_token`.
2. No portal redirect:
1. Check Hotspot status and DNS.
2. Ensure walled-garden domain exists.
3. No subscription created:
1. Confirm `isp_core.mac_auto_create = 1` and valid plan id.
2. Sector code must exist.
