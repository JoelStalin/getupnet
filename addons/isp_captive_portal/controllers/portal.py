# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class IspCaptivePortal(http.Controller):
    @http.route(["/captive"], type="http", auth="public", website=True)
    def captive_login(self, **kw):
        params = request.params
        link_login = params.get("link-login") or params.get("link_login")
        link_orig = params.get("link-orig") or params.get("link_orig")
        chap_id = params.get("chap-id") or params.get("chap_id")
        chap_challenge = params.get("chap-challenge") or params.get("chap_challenge")
        error = params.get("error")
        mac = params.get("mac")
        ip = params.get("ip")

        values = {
            "link_login": link_login,
            "link_orig": link_orig or "/captive/success",
            "chap_id": chap_id,
            "chap_challenge": chap_challenge,
            "error": error,
            "mac": mac,
            "ip": ip,
        }
        return request.render("isp_captive_portal.captive_login", values)

    @http.route(["/captive/success"], type="http", auth="public", website=True)
    def captive_success(self, **kw):
        return request.render("isp_captive_portal.captive_success", {})
