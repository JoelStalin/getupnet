# Troubleshooting

## No ONU appears in OLT
- Check fiber power / splitter ratio.
- Ensure ONU is compatible and powered.
- Use vendor software to discover/enable ONU.

## No MAC appears in Odoo
- ONU must request DHCP from MikroTik.
- Verify `lease-script` is set on DHCP server.
- Check `isp_core.mac_onboarding_token` matches `ISP_MAC_TOKEN`.

## Hotspot not redirecting
- Confirm Hotspot is enabled on LAN bridge.
- Verify `portal.getupsoft.com.do` resolves correctly.
- Ensure walled-garden has the portal domain.

## Subscription not created
- Set `isp_core.mac_auto_create = 1`.
- Set `isp_core.mac_default_plan_id` to a valid plan id.
- Ensure the sector exists.
