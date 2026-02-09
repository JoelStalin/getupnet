# -*- coding: utf-8 -*-
from odoo import fields, models


class IspServicePlan(models.Model):
    _inherit = "isp.service_plan"

    tax_ids = fields.Many2many("account.tax", string="Taxes")
