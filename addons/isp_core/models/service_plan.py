# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspServicePlan(models.Model):
    _name = "isp.service_plan"
    _description = "ISP Service Plan"
    _order = "name"

    name = fields.Char(required=True)
    service_type = fields.Selection(
        [("pppoe", "PPPoE"), ("dhcp", "DHCP"), ("hotspot", "Hotspot")],
        required=True,
        default="pppoe",
    )
    down_mbps = fields.Float()
    up_mbps = fields.Float()
    price = fields.Monetary()
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    mikrotik_profile = fields.Char()
    qos_policy = fields.Char()
    suspend_after_days = fields.Integer(default=0)
