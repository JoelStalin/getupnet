# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class IspDevice(models.Model):
    _name = "isp.device"
    _description = "ISP Device"
    _order = "name"

    name = fields.Char(required=True)
    device_type = fields.Selection(
        [("mikrotik", "MikroTik"), ("olt", "OLT"), ("other", "Other")],
        required=True,
        default="mikrotik",
        ondelete="set default",
    )
    sector_id = fields.Many2one("isp.sector", ondelete="restrict")
    mgmt_ip = fields.Char()
    mgmt_port = fields.Integer(default=8728)
    status = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("maintenance", "Maintenance"), ("retired", "Retired")],
        default="draft",
    )
    tags = fields.Char()

    @api.constrains("device_type", "sector_id")
    def _check_sector_required_for_mikrotik(self):
        for rec in self:
            if rec.device_type == "mikrotik" and not rec.sector_id:
                raise ValidationError("MikroTik devices must be linked to a sector.")
