# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspSubscription(models.Model):
    _inherit = "isp.subscription"

    router_id = fields.Many2one("isp.mikrotik.router", domain="[(\"sector_id\", \"=\", sector_id)]")

    @api.onchange("sector_id")
    def _onchange_sector_id_set_router(self):
        for rec in self:
            if not rec.sector_id:
                rec.router_id = False
                continue
            routers = self.env["isp.mikrotik.router"].search([
                ("sector_id", "=", rec.sector_id.id),
            ])
            if len(routers) == 1:
                rec.router_id = routers[0]
