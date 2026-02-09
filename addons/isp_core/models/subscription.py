# -*- coding: utf-8 -*-
import json
import secrets
from odoo import api, fields, models


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
    next_invoice_date = fields.Date()
    pppoe_username = fields.Char(groups="isp_core.group_isp_admin,isp_core.group_isp_noc")
    pppoe_password = fields.Char(groups="isp_core.group_isp_admin,isp_core.group_isp_noc")
    service_ip = fields.Char()
    service_mac = fields.Char()
    notes = fields.Text()
    job_ids = fields.One2many("isp.provisioning_job", "subscription_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("isp.subscription") or "SUB"
        records = super().create(vals_list)
        for rec in records:
            rec._ensure_pppoe_credentials()
        return records

    def _ensure_pppoe_credentials(self):
        for rec in self:
            if rec.plan_id and rec.plan_id.service_type != "pppoe":
                continue
            if not rec.pppoe_username:
                rec.pppoe_username = rec.name
            if not rec.pppoe_password:
                rec.pppoe_password = secrets.token_hex(6)

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
