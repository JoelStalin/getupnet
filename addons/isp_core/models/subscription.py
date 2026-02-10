# -*- coding: utf-8 -*-
import json
import secrets
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class IspSubscription(models.Model):
    _name = "isp.subscription"
    _description = "ISP Subscription"
    _order = "id desc"

    name = fields.Char(default="New")
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    plan_id = fields.Many2one("isp.service_plan", required=True, ondelete="restrict")
    sector_id = fields.Many2one("isp.sector", required=True, ondelete="restrict")
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("suspended", "Suspended"), ("terminated", "Terminated")],
        default="draft",
    )
    start_date = fields.Date()
    install_date = fields.Date()
    gps_lat = fields.Float()
    gps_lng = fields.Float()
    address_text = fields.Text()
    pop_id = fields.Many2one("isp.network_site", string="POP/Site", ondelete="set null")
    device_id = fields.Many2one("isp.device", string="MikroTik", ondelete="set null")
    technician_id = fields.Many2one("res.users", string="Technician", ondelete="set null")
    auth_method = fields.Selection(
        [("dhcp", "DHCP"), ("pppoe", "PPPoE")],
        default="dhcp",
        required=True,
    )
    dhcp_mode = fields.Selection(
        [("dynamic", "Dynamic"), ("static", "Static")],
        default="dynamic",
        required=True,
    )
    next_invoice_date = fields.Date()
    pppoe_username = fields.Char(groups="isp_core.group_isp_admin,isp_core.group_isp_noc")
    pppoe_password = fields.Char(groups="isp_core.group_isp_admin,isp_core.group_isp_noc")
    pppoe_profile = fields.Char()
    service_ip = fields.Char(string="Service IP")
    service_mac = fields.Char(string="Service MAC")
    ip_address = fields.Char(related="service_ip", string="IP Address", store=True, readonly=False)
    mac_address = fields.Char(related="service_mac", string="MAC Address", store=True, readonly=False)
    notes = fields.Text()
    job_ids = fields.One2many("isp.provisioning_job", "subscription_id")
    plan_change_request_ids = fields.One2many("isp.plan.change.request", "subscription_id")
    fault_ticket_ids = fields.One2many("isp.fault.ticket", "subscription_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("isp.subscription") or "SUB"
            if not vals.get("auth_method") and vals.get("plan_id"):
                plan = self.env["isp.service_plan"].browse(vals["plan_id"])
                if plan and plan.service_type in ("pppoe", "dhcp"):
                    vals["auth_method"] = plan.service_type
        records = super().create(vals_list)
        for rec in records:
            rec._ensure_pppoe_credentials()
        return records

    def _ensure_pppoe_credentials(self):
        for rec in self:
            if rec.auth_method != "pppoe":
                continue
            if not rec.pppoe_username:
                rec.pppoe_username = rec.name
            if not rec.pppoe_password:
                rec.pppoe_password = secrets.token_hex(6)
            if not rec.pppoe_profile and rec.plan_id:
                rec.pppoe_profile = rec.plan_id.mikrotik_profile or rec.pppoe_profile

    @api.onchange("plan_id")
    def _onchange_plan_id_auth_method(self):
        for rec in self:
            if rec.plan_id and rec.plan_id.service_type in ("pppoe", "dhcp"):
                rec.auth_method = rec.plan_id.service_type
            if rec.plan_id and rec.plan_id.mikrotik_profile:
                rec.pppoe_profile = rec.plan_id.mikrotik_profile

    @api.constrains("auth_method", "pppoe_username", "pppoe_password")
    def _check_pppoe_credentials(self):
        for rec in self:
            if rec.auth_method == "pppoe":
                if not rec.pppoe_username or not rec.pppoe_password:
                    raise ValidationError("PPPoE username and password are required.")

    @api.constrains("auth_method", "dhcp_mode", "service_ip")
    def _check_dhcp_static_ip(self):
        for rec in self:
            if rec.auth_method == "dhcp" and rec.dhcp_mode == "static" and not rec.service_ip:
                raise ValidationError("Static DHCP requires an IP address.")

    @api.constrains("auth_method", "dhcp_mode", "service_ip")
    def _check_unique_static_ip(self):
        for rec in self:
            if rec.auth_method != "dhcp" or rec.dhcp_mode != "static" or not rec.service_ip:
                continue
            count = self.search_count([
                ("id", "!=", rec.id),
                ("service_ip", "=", rec.service_ip),
                ("auth_method", "=", "dhcp"),
                ("dhcp_mode", "=", "static"),
            ])
            if count:
                raise ValidationError("Static IP address must be unique.")

    @api.constrains("state", "gps_lat", "gps_lng")
    def _check_gps_required_for_active(self):
        for rec in self:
            if rec.state in ("active", "suspended") and (not rec.gps_lat or not rec.gps_lng):
                raise ValidationError("GPS coordinates are required for active installations.")

    @api.constrains("sector_id", "device_id")
    def _check_device_sector_match(self):
        for rec in self:
            if rec.device_id and rec.device_id.sector_id and rec.device_id.sector_id != rec.sector_id:
                raise ValidationError("The selected device does not belong to the subscription's sector.")

    _pppoe_user_uniq = models.Constraint(
        "unique (pppoe_username)",
        "PPPoE username must be unique.",
    )

    def _queue_job(self, job_type, payload=None):
        self.ensure_one()
        vals = {
            "job_type": job_type,
            "subscription_id": self.id,
            "device_id": False,
            "sector_id": self.sector_id.id,
            "payload_json": json.dumps(payload or {}),
        }
        job = self.env["isp.provisioning_job"].create(vals)
        self.env["isp.audit_log"].sudo().log_action(
            action=job_type,
            record=self,
            details=f"Queued job {job.name}",
        )
        return job

    def action_activate(self):
        for rec in self:
            rec._ensure_pppoe_credentials()
            rec._queue_job("activate_subscription")

    def action_suspend(self):
        for rec in self:
            rec._queue_job("suspend_subscription")

    def action_reconnect(self):
        for rec in self:
            rec._queue_job("reconnect_subscription")

    def action_terminate(self):
        for rec in self:
            rec._queue_job("terminate_subscription")

    def action_change_plan(self):
        for rec in self:
            rec._queue_job("change_plan")

    def action_request_plan_change(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Plan Change Request",
            "res_model": "isp.plan.change.request",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_subscription_id": self.id,
            },
        }
