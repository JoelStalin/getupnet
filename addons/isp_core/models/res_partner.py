# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_isp_customer = fields.Boolean(string="ISP Customer")
    isp_subscription_ids = fields.One2many("isp.subscription", "partner_id", string="Subscriptions")
