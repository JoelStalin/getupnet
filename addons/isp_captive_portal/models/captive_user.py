# -*- coding: utf-8 -*-
import json
from odoo import fields, models


class IspCaptiveUser(models.Model):
    _name = "isp.captive.user"
    _description = "Captive Portal User"
    _order = "username"

    username = fields.Char(required=True)
    password = fields.Char(groups="isp_core.group_isp_admin,isp_core.group_isp_noc,isp_core.group_isp_support")
    profile = fields.Char()
    state = fields.Selection([("active", "Active"), ("disabled", "Disabled")], default="disabled")
    router_id = fields.Many2one("isp.mikrotik.router", ondelete="set null")
    sector_id = fields.Many2one(related="router_id.sector_id", store=True)
    expires_at = fields.Datetime()
    last_login_at = fields.Datetime()
    notes = fields.Text()

    _sql_constraints = [
        ("isp_captive_user_uniq", "unique(username)", "Captive username must be unique."),
    ]

    def action_enable(self):
        for rec in self:
            payload = {"captive_user_id": rec.id}
            self.env["isp.provisioning_job"].create(
                {
                    "job_type": "captive_user_create",
                    "payload_json": json.dumps(payload),
                    "sector_id": rec.sector_id.id if rec.sector_id else False,
                    "device_id": rec.router_id.device_id.id if rec.router_id else False,
                }
            )

    def action_disable(self):
        for rec in self:
            payload = {"captive_user_id": rec.id}
            self.env["isp.provisioning_job"].create(
                {
                    "job_type": "captive_user_disable",
                    "payload_json": json.dumps(payload),
                    "sector_id": rec.sector_id.id if rec.sector_id else False,
                    "device_id": rec.router_id.device_id.id if rec.router_id else False,
                }
            )
