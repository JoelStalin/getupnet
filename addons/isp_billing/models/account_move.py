# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    isp_subscription_id = fields.Many2one("isp.subscription", ondelete="set null")
