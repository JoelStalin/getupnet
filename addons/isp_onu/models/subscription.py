# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspSubscription(models.Model):
    _inherit = "isp.subscription"

    onu_assignment_ids = fields.One2many("isp.onu.assignment", "subscription_id")
    onu_assignment_id = fields.Many2one(
        "isp.onu.assignment",
        compute="_compute_active_onu_assignment",
        store=True,
    )

    @api.depends("onu_assignment_ids", "onu_assignment_ids.active")
    def _compute_active_onu_assignment(self):
        for rec in self:
            active = rec.onu_assignment_ids.filtered(lambda x: x.active)
            rec.onu_assignment_id = active[:1].id if active else False
