# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspCaptiveSession(models.Model):
    _name = "isp.captive.session"
    _description = "Captive Portal Session"
    _order = "started_at desc"

    username = fields.Char()
    ip_address = fields.Char()
    mac_address = fields.Char()
    router_id = fields.Many2one("isp.mikrotik.router", ondelete="set null")
    sector_id = fields.Many2one(related="router_id.sector_id", store=True, readonly=True)
    started_at = fields.Datetime()
    uptime = fields.Char()
    bytes_in = fields.Float()
    bytes_out = fields.Float()
    state = fields.Char()

    @api.model
    def _cron_sync_sessions(self):
        # Placeholder for future RouterOS session sync.
        return True
