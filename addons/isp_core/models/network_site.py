# -*- coding: utf-8 -*-
from odoo import fields, models


class IspNetworkSite(models.Model):
    _name = "isp.network_site"
    _description = "ISP Network Site"
    _order = "name"

    name = fields.Char(required=True)
    sector_id = fields.Many2one("isp.sector", ondelete="set null")
    tags = fields.Char()
    notes = fields.Text()
