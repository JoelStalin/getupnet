# Odoo MAC Onboarding

## Endpoint
`/isp/mac_onboarding`

## Required token
Set in System Parameters:
- `isp_core.mac_onboarding_token`

## Query params
- `mac` (required)
- `ip`
- `bound` (0/1)
- `sector` (sector code)
- `hostname` (optional)

## Optional auto-create
Set these System Parameters:
- `isp_core.mac_auto_create = 1`
- `isp_core.mac_default_plan_id = <plan_id>`
- `isp_core.mac_auto_create_captive_user = 1`
- `isp_core.mac_auto_provision_captive = 1`
- `isp_core.mac_captive_default_profile = default`

## Result
- Creates/updates `isp.mac_profile`.
- Optionally creates `isp.subscription` (and links to a router in the sector if available).
- Optionally creates `isp.captive.user` and provisions it to MikroTik.
