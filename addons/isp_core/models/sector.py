# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspSector(models.Model):
    _name = "isp.sector"
    _description = "ISP Sector"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    city = fields.Char()
    zone = fields.Char()
    address = fields.Char()
    gps_lat = fields.Float()
    gps_lng = fields.Float()
    notes = fields.Text()

    _sql_constraints = [
        ("isp_sector_code_uniq", "unique(code)", "Sector code must be unique."),
    ]
