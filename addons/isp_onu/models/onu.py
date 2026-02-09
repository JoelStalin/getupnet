# -*- coding: utf-8 -*-
from odoo import fields, models


class IspOnu(models.Model):
    _name = "isp.onu"
    _description = "ONU/ONT"
    _order = "serial"

    serial = fields.Char(required=True)
    vendor = fields.Char()
    model = fields.Char()
    sector_id = fields.Many2one("isp.sector", ondelete="set null")
    olt_ref = fields.Char()
    pon_port = fields.Char()
    vlan = fields.Char()
    status = fields.Selection(
        [("stock", "Stock"), ("installed", "Installed"), ("faulty", "Faulty")],
        default="stock",
    )
    notes = fields.Text()

    _sql_constraints = [
        ("isp_onu_serial_uniq", "unique(serial)", "ONU serial must be unique."),
    ]
