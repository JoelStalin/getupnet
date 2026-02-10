# Optimized Project Master Plan & Requirements
> **Source**: Synthesized from `ISP_Odoo19_MikroTik_MasterPlan.md` and `Prompt_Odoo19_ISP_PortalCautivo_Completo.md`.
> **Context**: High-level directives for Odoo 19 ISP implementation.

## 1. Core Directives
- **Stack**: Odoo 19 (Python), PostgreSQL, Docker Compose.
- **Network Topology**: Starlink (Backhaul) -> MikroTik (Edge/BNG) -> OLT -> ONU -> Client.
- **Role**: Functional & Technical Architect.
- **Philosophy**: Use Odoo native features where possible (Portal, Subscriptions, Invoicing).

## 2. Functional Scope
### A. Customer Portal (Self-Service)
- **Login**: Individual portal access.
- **Dashboard**: View plan, speed, invoices, and status (Active/Suspended).
- **Plan Change**: Request upgrade/downgrade -> Backoffice Approval -> Provisioning.
- **Payments**: 
    - **Transfer**: Report payment with attachment (screenshot). SLA 24/48h for validation.
    - **Card**: Future phase (Gateway integration).
- **Faults**: Report connectivity issues (Tickets).

### B. Admin Backoffice (ISP Management)
- **Billing**: Recurring invoicing, automated suspension (Day 10), automated reconnection on payment.
- **Provisioning**:
    - **Methods**: DHCP (Dynamic/Static) [Default] or PPPoE.
    - **Hardware**: Management of MikroTik, OLT, ONUs.
    - **Geo**: GPS coordinates mandatory for installation.
- **Dashboards**:
    - **KPIs**: Active/Suspended/Overdue count, MRR, Ticket SLA.
    - **Drill-down**: Clickable charts to lists.

## 3. Technical Architecture
### Data Models
- **`isp_core`**: 
    - `isp.subscription` (Contract), `isp.sector` (Zone), `isp.device` (MikroTik), `isp.onu` (CPE).
    - **Constraints**: 1 Subscription = 1 ONU/Device.
- **`isp_billing`**: 
    - `isp.bank.transfer.payment` (Workflow: Draft -> Review -> Approved -> Applied).
- **`isp_mikrotik`**: 
    - Wrapper for `librouteros`.
    - **Security**: Passwords encrypted/masked. admin only visibility.

### Verification & Testing
- **Unit**: Validation of unique constraints (PPPoE user, MAC), State transitions.
- **Functional (Selenium)**:
    - Flows: Create Customer -> Create Sub -> Provision -> Invoice -> Suspend -> Pay -> Reconnect.
    - Run in standard Docker environment (Headless Chrome).

## 4. Automation & Tools
### Preloader Script
- **Goal**: Auto-onboard new factory-default MikroTiks.
- **Flow**: Scan Subnet -> Connect (Default creds) -> Secure (Create `odoo_noc` user, Firewall) -> Register in Odoo.

### Provisioning Jobs
- Async queue (`isp.provisioning_job`) for all router interactions (avoid blocking UI).
- **Retries**: Configurable max attempts.
- **Audit**: Log all config changes to `isp.audit_log`.

## 5. Roadmap
- **Phase 1 (MVP)**:
    - Core Models & CRM.
    - Portal (Plan change, Transfer reporting).
    - Billing (Recurring + Manual suspension).
    - Basic MikroTik Integration (Simulated/Dry-run).
- **Phase 2**:
    - Full Automated Provisioning (Queues/Secret sync).
    - Card Payment Gateway.
    - Advanced Maps/Geo-analytics.
