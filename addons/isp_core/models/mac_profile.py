# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspMacProfile(models.Model):
    _name = "isp.mac_profile"
    _description = "ISP MAC Access Profile"
    _order = "last_seen_at desc"

    mac_address = fields.Char(required=True)
    sector_id = fields.Many2one("isp.sector", ondelete="set null")
    plan_id = fields.Many2one("isp.service_plan", ondelete="set null")
    partner_id = fields.Many2one("res.partner", ondelete="set null")
    subscription_id = fields.Many2one("isp.subscription", ondelete="set null")
    state = fields.Selection([("online", "Online"), ("offline", "Offline")], default="online")
    last_seen_ip = fields.Char()
    last_seen_at = fields.Datetime()
    hostname = fields.Char()
    notes = fields.Text()

    _sql_constraints = [
        ("isp_mac_profile_uniq", "unique(mac_address)", "MAC address must be unique."),
    ]

    @api.model
    def normalize_mac(self, mac):
        if not mac:
            return False
        return mac.strip().upper()
