# -*- coding: utf-8 -*-
import json
from odoo import fields, models


class IspCaptiveWalledGarden(models.Model):
    _name = "isp.captive.walled_garden"
    _description = "Captive Portal Walled Garden"
    _order = "domain"

    domain = fields.Char(required=True)
    router_id = fields.Many2one("isp.mikrotik.router", ondelete="set null")
    sector_id = fields.Many2one(related="router_id.sector_id", store=True, readonly=True)
    active = fields.Boolean(default=True)
    notes = fields.Text()

    _sql_constraints = [
        ("isp_captive_wg_uniq", "unique(domain)", "Domain must be unique."),
    ]

    def action_apply(self):
        for rec in self:
            payload = {"walled_garden_id": rec.id}
            self.env["isp.provisioning_job"].create(
                {
                    "job_type": "walled_garden_apply",
                    "payload_json": json.dumps(payload),
                    "sector_id": rec.router_id.sector_id.id if rec.router_id else False,
                    "device_id": rec.router_id.device_id.id if rec.router_id else False,
                }
            )
