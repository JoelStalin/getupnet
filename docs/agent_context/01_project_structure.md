# Architecture & Data Models
> Use this reference to understand the system structure and dependencies.

## Module Structure

### 1. `isp_core` (Base)
**Purpose**: Central logic for ISP operations.
**Dependencies**: `base`, `web`, `mail`.
**Key Models**:
- `isp.subscription`: Core entity linking a customer (`res.partner`) to a service plan. Tracks state, billing cycles, and technical details.
- `isp.sector`: Geographical or logical network segment.
- `isp.service_plan`: Definitions of offered services (speed, price, technical profiles).
- `isp.device`: Network equipment (generic).
- `isp.provisioning_job`: Async tasks for configuring hardware.

### 2. `isp_billing` (Financial)
**Purpose**: Handling payments, invoices, and automated suspension.
**Dependencies**: `isp_core`, `account`.
**Key Logic**:
- **Recurring Invoicing**: Generated based on `isp.subscription` billing cycle.
- **Suspension**: Automated cron job checks for overdue invoices > grace period.
- **Bank Transfers**: Workflow for manual payment proof submission and approval.

### 3. `isp_mikrotik` (Hardware Integration)
**Purpose**: Interface with RouterOS devices.
**Dependencies**: `isp_core`.
**Technical**:
- Uses `librouteros` library.
- `routeros_client.py`: Wrapper for API calls.
- **Provisioning**: 
    - Creates Queues (Simple Queues).
    - Manages PPP Secrets.
    - Captive Portal user management.

### 4. `isp_onu` (Fiber Optic)
**Purpose**: Manage GPON/EPON endpoints.
**Dependencies**: `isp_core`.
**Logic**: Tracks ONU serials, inventory status, and assignment to subscriptions.

### 5. `isp_portal` & `isp_captive_portal` (Frontend)
**Purpose**: Customer self-service.
**Logic**:
- **Portal**: Standard Odoo website controllers for billing/support.
- **Captive**: Hotspot login pages and session management.

## Key Relationships
- **Subscription <-> Partner**: Many-to-One. One partner can have multiple subscriptions (e.g., home + office).
- **Subscription <-> Plan**: Many-to-One. Defines the service level.
- **Subscription <-> Device**: Many-to-One. The CPE (Customer Premise Equipment).
- **Sector**: Grouping for devices and subscriptions, often maps to a physical tower or OLT port.

## Critical Workflows

### Provisioning
1. **Trigger**: Subscription creation or plan change.
2. **Action**: Creates `isp.provisioning_job`.
3. **Execution**: Cron worker picks up job -> calls `isp_mikrotik` -> pushes config to router.
4. **Result**: Success (Active) or Failure (Retry/Error).

### Billing Cycle
1. **Invoice Generation**: Monthly cron job.
2. **Payment Matching**: Automated (Gateway) or Manual (Bank Transfer).
3. **Overdue Handling**: 
    - Day +1: Reminder.
    - Day +5: Warning.
    - Day +10: Service Suspension (via Provisioning Job).
