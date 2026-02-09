# Implementation Guide (Starlink + MikroTik + OLT Stick + ONU/ONT)

## Topology
Starlink (WAN) -> MikroTik (WAN) -> MikroTik (LAN bridge) -> OLT Stick -> Fiber -> ONU/ONT (router mode)

## Goal
- MikroTik routes Internet from Starlink.
- OLT stick handles GPON discovery.
- When a new ONU/ONT connects and requests DHCP, MikroTik notifies Odoo.
- Odoo creates a MAC profile and (optionally) subscription + captive user.

## Step 1: Prepare Odoo
1. Create a sector:
   - Code: `SEC-001-los_cacaos`
   - Name: `Los Cacaos`
2. Create a service plan (e.g. DHCP 20/5).
3. Set System Parameters:
   - `isp_core.mac_onboarding_token` = `<token>`
   - `isp_core.mac_auto_create` = `1` (optional)
   - `isp_core.mac_default_plan_id` = `<plan_id>` (optional)
   - `isp_core.mac_auto_create_captive_user` = `1` (optional)
   - `isp_core.mac_auto_provision_captive` = `1` (optional)
   - `isp_core.mac_captive_default_profile` = `default`

## Step 2: Configure MikroTik with Preloader
1. Copy `tools/mikrotik_preloader/config.example.yaml` to `config.yaml`.
2. Adjust:
   - `wan_interface` = Starlink interface (e.g. `ether1`)
   - `lan_ports` = ports connected to OLT stick (e.g. `sfp1`, `ether2`)
   - `hotspot_dns_name` = `portal.getupsoft.com.do`
3. Export env vars:
   - `MIKROTIK_MGMT_PASS`
   - `ODOO_ADMIN_PASS`
   - `ISP_MAC_TOKEN` (same as Odoo token)
4. Run:
   - `python tools/mikrotik_preloader/preloader.py --config tools/mikrotik_preloader/config.yaml`

### Optional: SSH tunnel (Option A)
If MikroTik is only reachable from your local LAN, open an SSH tunnel from your host first:
```
ssh -L 8728:<MIKROTIK_LAN_IP>:8728 <user>@<remote_server>
```
Then set in `config.yaml`:
```
mgmt_subnet: "127.0.0.1/32"
routeros:
  api_port: 8728
```

## Step 3: OLT Stick
- Use the OLT stick software to enable discovery and register ONU/ONT.
- Ensure ONU/ONT are in router mode and pull DHCP from MikroTik.

## Step 4: Verify
- When ONU/ONT connects, a MAC profile appears in Odoo:
  - Menu: ISP -> Operations -> MAC Profiles
- Optional: subscriptions and captive users are created automatically if enabled.

## Notes
- If the ONU/ONT uses PPPoE, DHCP lease-script won't fire.
- For captive portal, ensure Hotspot is enabled and domain is in walled-garden.
