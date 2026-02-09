# OLT Stick Guide

## Scope
This guide documents how to use the OLT stick with the MikroTik bridge and Odoo onboarding.

## Steps
1. Connect the OLT stick to the MikroTik LAN (bridge port).
2. Use the vendor software to:
   - Enable ONU discovery
   - Register or enable ONU/ONT
3. Ensure ONU/ONT is in router mode and requests DHCP from MikroTik.

## Expected results
- ONU appears in the OLT software dashboard.
- MikroTik DHCP lease-script fires when ONU requests DHCP.
- Odoo MAC Profile is created automatically.

## Notes
- The OLT stick is managed by its own software, not RouterOS.
- If you need real ONU serials, use the OLT software/API directly.
