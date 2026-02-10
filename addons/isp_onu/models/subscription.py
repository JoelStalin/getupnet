# -*- coding: utf-8 -*-
from odoo import fields, models


class IspSubscription(models.Model):
    _inherit = "isp.subscription"

    onu_assignment_ids = fields.One2many("isp.onu.assignment", "subscription_id")
