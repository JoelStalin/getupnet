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
        default="dhcp",
        ondelete="set default",
    )
    active = fields.Boolean(default=True)
    download_mbps = fields.Float(string="Download (Mbps)")
    upload_mbps = fields.Float(string="Upload (Mbps)")
    price_monthly = fields.Monetary(string="Monthly Price", currency_field="currency_id")
    
    # Deprecated fields (mapping to new names if needed, or just replace)
    # Keeping old names for compatibility if they were used, but mapping to new requirements
    down_mbps = fields.Float(related="download_mbps", store=True)
    up_mbps = fields.Float(related="upload_mbps", store=True)
    price = fields.Monetary(related="price_monthly", store=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    billing_cycle = fields.Selection(
        [("monthly", "Monthly")],
        default="monthly",
        required=True,
    )
    mikrotik_profile = fields.Char()
    qos_policy = fields.Char()
    suspend_after_days = fields.Integer(default=0)
