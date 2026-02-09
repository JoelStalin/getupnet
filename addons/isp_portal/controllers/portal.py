# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class IspPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        values["isp_subscription_count"] = request.env["isp.subscription"].sudo().search_count([
            ("partner_id", "=", partner.id),
        ])
        return values

    @http.route(["/my/isp/subscriptions"], type="http", auth="user", website=True)
    def portal_my_isp_subscriptions(self, **kw):
        partner = request.env.user.partner_id
        subscriptions = request.env["isp.subscription"].sudo().search([
            ("partner_id", "=", partner.id),
        ])
        return request.render(
            "isp_portal.portal_my_isp_subscriptions",
            {
                "subscriptions": subscriptions,
            },
        )
