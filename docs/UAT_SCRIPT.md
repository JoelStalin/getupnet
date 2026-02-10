# UAT Script (ISP Odoo 19)

This script validates end-to-end business flows per role.

## Portal Customer
1. Login to portal.
2. Open `My ISP` summary and verify subscription counts and status.
3. Open `My Invoices` and download a posted invoice.
4. Submit a plan change request (next cycle) and confirm confirmation message.
5. Report a bank transfer with attachment and reference.
6. Create a fault ticket with description and attachment.

## Billing Agent
1. Open `ISP -> Operations -> Transfer Payments`.
2. Open the transfer in review and approve it.
3. Verify the payment is applied and the invoice is updated.
4. Check `ISP -> Reports -> Dashboard` KPIs.
5. Open `ISP -> Reports -> Overdue Invoices` and filter by sector.

## Support Agent
1. Open `ISP -> Operations -> Fault Tickets`.
2. Start a ticket and set state to `In Progress`.
3. Resolve and close a ticket.
4. Verify resolution time and SLA metrics.

## Technician
1. Open assigned fault ticket.
2. Update GPS fields (if required) and add notes.
3. Move ticket to resolved.

## NOC / Admin
1. Create a sector, MikroTik device, and service plan.
2. Create a subscription and verify DHCP defaults.
3. Trigger activation and check provisioning job success.
4. Suspend and reconnect subscription, then check audit log.
5. Open `ISP -> Reports -> Suspensions & Reconnections` and verify entries.

## Acceptance
- Portal users cannot see other customers’ data.
- PPPoE password visible only for Admin/NOC.
- Transfer review SLA: flagged after 24h, due at 48h.
- Suspension after 10 days past due (unless overridden on plan).
