# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    isp_sector_ids = fields.Many2many("isp.sector", string="Allowed ISP Sectors")
