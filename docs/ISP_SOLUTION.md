# ISP Solution (Odoo 19)

## Architecture Overview
- Core modules
- `isp_core`: core domain (sectors, devices, plans, subscriptions, jobs, audit, plan change, fault tickets)
- `isp_billing`: recurring billing, transfers, suspension/reconnect automation, dashboard, invoice reports
- `isp_onu`: ONU inventory and assignment to subscriptions
- `isp_mikrotik`: RouterOS integration and provisioning jobs
- `isp_captive_portal`: vouchers, hotspot users, walled-garden, captive sessions
- `isp_portal`: customer portal pages, forms, and security rules

## Assumptions (Defaults)
- Auth method: `dhcp` with `dhcp_mode=dynamic`.
- Plan change: approval required, effective date next cycle, proration disabled.
- Transfer SLA: review 48h, attention flag at 24h.
- Grace period: 5 days, suspend at 10 days past due.
- Tickets SLA: low=72h, normal=48h, high=24h, urgent=8h.
- GPS required for active installations.
- PPPoE password visible only to Admin/NOC.
- Single-company mode by default. Multi-company can be added by adding `company_id` fields and rules.

## ERD (Textual)
- `res.partner` 1..n `isp.subscription`
- `isp.service_plan` 1..n `isp.subscription`
- `isp.sector` 1..n `isp.subscription`
- `isp.device` 1..n `isp.subscription` (MikroTik optional)
- `isp.subscription` 1..n `isp.provisioning_job`
- `isp.subscription` 1..n `isp.plan.change.request`
- `isp.subscription` 1..n `isp.bank.transfer.payment`
- `isp.subscription` 1..n `isp.fault.ticket`
- `isp.subscription` 1..n `account.move` (via `isp_subscription_id`)
- `isp.onu` 1..n `isp.onu.assignment` n..1 `isp.subscription`
- `isp.audit_log` references any record (model + id)
- `isp.captive.user` / `isp.captive.session` / `isp.captive.walled_garden` linked to MikroTik

## Process Flows
- Plan change
- Portal submits request -> state `submitted` -> backoffice `approved` or `rejected`
- Approved with effective date -> apply -> update subscription plan -> queue provisioning job -> audit log -> notify

- Bank transfer payment
- Portal submits transfer with attachment -> `in_review`
- Billing approves -> payment created/applied -> invoices reconciled -> state `applied`
- Billing rejects -> reason required -> notify

- Suspension / reconnect
- Daily cron checks overdue invoices -> suspend after grace days
- On payment -> reconnect if no open invoices

- Fault tickets
- Portal or backoffice creates -> `new`
- Support moves to `in_progress` -> `resolved` -> `closed`
- SLA metrics computed and stored

- MAC onboarding
- MikroTik DHCP lease-script posts MAC -> Odoo creates MAC profile
- Optional auto-create subscription and captive user

## Module Structure
- `addons/isp_core`
- `models/`, `views/`, `data/`, `security/`, `controllers/`
- `addons/isp_billing`
- `models/`, `views/`, `data/`, `security/`
- `addons/isp_onu`
- `models/`, `views/`, `security/`
- `addons/isp_mikrotik`
- `models/`, `views/`, `data/`, `security/`
- `addons/isp_captive_portal`
- `models/`, `views/`, `data/`, `security/`, `controllers/`
- `addons/isp_portal`
- `controllers/`, `views/`, `security/`

## Portal Endpoints
- `GET /my/isp` summary dashboard
- `GET /my/isp/service/<id>` subscription detail
- `GET /my/isp/invoices` invoices list
- `GET/POST /my/isp/plan/change` plan change form
- `GET/POST /my/isp/payments/transfer` bank transfer form
- `GET /my/isp/faults` fault tickets list
- `GET/POST /my/isp/faults/new` new fault ticket form

## Roadmap
- Phase 1 (MVP)
- Core models, portal, transfer payments, plan changes, fault tickets
- Dashboard and reports (including top sectors by overdue balance)
- Basic provisioning and audit

- Phase 2
- RouterOS automation for QoS/queues and automatic suspension
- Card gateway integration (payment provider + webhooks)
- Maps/geo analytics

## Risks and Mitigations
- RouterOS compatibility
- Mitigation: run with `dry_run=1` and staged devices
- Data quality (GPS, MAC, plan IDs)
- Mitigation: constraints + required fields + validation errors
- Transfer reconciliation errors
- Mitigation: approval step and audit log entries
- Portal security
- Mitigation: record rules for portal users on all models

## UAT Checklist
- See `docs/UAT_SCRIPT.md`
