# ISP Data Dictionary

## Core
- `isp.sector`
- `name`, `code`, `city`, `zone`, `address`, `gps_lat`, `gps_lng`, `notes`

- `isp.device`
- `name`, `device_type`, `sector_id`, `mgmt_ip`, `mgmt_port`, `status`, `tags`

- `isp.mikrotik.router`
- `device_id`, `auth_method`, `routeros_version`, `last_healthcheck_at`, `last_healthcheck_status`

- `isp.service_plan`
- `name`, `service_type`, `down_mbps`, `up_mbps`, `price`, `currency_id`, `tax_ids`
- `mikrotik_profile`, `qos_policy`, `suspend_after_days`

- `isp.subscription`
- `name`, `partner_id`, `plan_id`, `sector_id`, `state`, `start_date`, `install_date`
- `gps_lat`, `gps_lng`, `address_text`, `pop_id`, `device_id`, `technician_id`
- `auth_method`, `dhcp_mode`, `service_ip`, `service_mac`, `pppoe_username`, `pppoe_password`, `pppoe_profile`
- `next_invoice_date`, `job_ids`

- `isp.provisioning_job`
- `job_type`, `subscription_id`, `device_id`, `sector_id`, `state`, `attempts`, `error_message`

- `isp.audit_log`
- `action`, `record_model`, `record_id`, `record_name`, `user_id`, `timestamp`, `details`

## Billing
- `isp.bank.transfer.payment`
- `partner_id`, `subscription_id`, `invoice_ids`, `bank_name`, `reference`, `amount`, `currency_id`
- `transfer_datetime`, `attachment_ids`, `state`, `review_deadline`, `attention_deadline`, `needs_attention`
- `accounting_payment_id`

- `account.move` (extended)
- `isp_subscription_id`, `isp_sector_id`, `isp_plan_id`

## ONU/ONT
- `isp.onu`
- `serial`, `mac_address`, `vendor`, `model`, `sector_id`, `olt_ref`, `pon_port`, `vlan`, `status`

- `isp.onu.assignment`
- `onu_id`, `subscription_id`, `active`, `assigned_at`, `unassigned_at`

## Portal / Tickets
- `isp.plan.change.request`
- `subscription_id`, `requested_plan_id`, `effective_date_mode`, `effective_date`
- `state`, `requested_by`, `approved_by`, `rejection_reason`

- `isp.fault.ticket`
- `partner_id`, `subscription_id`, `sector_id`, `fault_type`, `priority`
- `description`, `attachment_ids`, `state`, `assigned_to`, `opened_at`, `closed_at`
- `resolution_time_hours`, `sla_target_hours`

## Captive Portal
- `isp.captive.user`
- `name`, `password`, `profile`, `sector_id`, `state`

- `isp.captive.session`
- `user_id`, `ip_address`, `started_at`, `ended_at`, `bytes_in`, `bytes_out`

- `isp.captive.walled_garden`
- `dst_host`, `comment`, `active`
