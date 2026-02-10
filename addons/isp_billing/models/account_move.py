# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    isp_subscription_id = fields.Many2one("isp.subscription", ondelete="set null")
    isp_sector_id = fields.Many2one(
        "isp.sector",
        related="isp_subscription_id.sector_id",
        store=True,
        readonly=True,
    )
    isp_plan_id = fields.Many2one(
        "isp.service_plan",
        related="isp_subscription_id.plan_id",
        store=True,
        readonly=True,
    )
