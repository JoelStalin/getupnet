# ISP Business Rules & Logic
> **Context**: Key decision logic for system automation.

## 1. Billing & Collection
### Recurring Invoicing
- **Cycle**: Monthly.
- **Generation Date**: Configurable (e.g., 1st of month or anniversary).
- **Grace Period**: 5 days after due date.

### Suspension Policy
- **Trigger**: Automatic cron job.
- **Condition**: Invoice overdue > 10 days (Grace Period + 5).
- **Action**: 
    1. Set Subscription state to `suspended`.
    2. Create `provisioning_job` to disable service on MikroTik (Disable PPPoE Secret / Block Queue).
- **Exclusions**: VIP customers or flagged `manual_suspend_only`.

### Reconnection
- **Trigger**: Payment registration (Full balance cleared).
- **Action**:
    1. Set Subscription state to `active`.
    2. Create `provisioning_job` to re-enable service.

## 2. Plan Changes
- **Request**: Can be initiated by Customer (Portal) or Admin.
- **Approval**: Required for Portal requests.
- **Effective Date**: 
    - Default: Next billing cycle start.
    - Immediate: Admin overrides only (proration disabled by default).
- **Logic**:
    1. Update `isp.subscription.plan_id`.
    2. Trigger `provisioning_job` to update Queue limits / PPPoE Profile.

## 3. Provisioning
### Credential Management
- **PPPoE Password**: Auto-generated or set by Admin. Visible only to `group_isp_admin`.
- **IP Address**:
    - **Dynamic**: Managed by MikroTik Pool.
    - **Static**: Assigned in Odoo, pushed to Lease/Secret.
- **MAC Address**: Required for DHCP compliance and security.

### Hardware Hierarchy
- 1 Subscription <-> 1 Device (CPE/ONU).
- Device must be linked to a `Sector`.
- `Sector` defines the `MikroTik` router responsible for auth.

## 4. Ticketing (Faults)
- **SLA**:
    - Urgent: 8h
    - High: 24h
    - Normal: 48h
    - Low: 72h
- **Escalation**: Dashboard highlights tickets nearing SLA breach.
