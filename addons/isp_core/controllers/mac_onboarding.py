# -*- coding: utf-8 -*-
import json
import secrets
from odoo import fields, http
from odoo.http import request, Response


class IspMacOnboardingController(http.Controller):
    @http.route("/isp/mac_onboarding", type="http", auth="public", csrf=False, methods=["GET", "POST"])
    def mac_onboarding(self, **kw):
        env = request.env
        token = kw.get("token") or request.httprequest.headers.get("X-ISP-TOKEN")
        expected = env["ir.config_parameter"].sudo().get_param("isp_core.mac_onboarding_token")
        if not expected:
            return Response("mac_onboarding_token not configured", status=403)
        if token != expected:
            return Response("unauthorized", status=401)

        mac = kw.get("mac") or kw.get("leaseActMAC")
        ip = kw.get("ip") or kw.get("leaseActIP")
        bound = kw.get("bound") or kw.get("leaseBound") or "1"
        sector_code = kw.get("sector")
        hostname = kw.get("hostname")

        if not mac:
            return Response("mac required", status=400)

        MacProfile = env["isp.mac_profile"].sudo()
        norm_mac = MacProfile.normalize_mac(mac)

        sector_id = False
        if sector_code:
            sector = env["isp.sector"].sudo().search([("code", "=", sector_code)], limit=1)
            sector_id = sector.id if sector else False

        profile = MacProfile.search([("mac_address", "=", norm_mac)], limit=1)
        values = {
            "mac_address": norm_mac,
            "sector_id": sector_id,
            "last_seen_ip": ip,
            "last_seen_at": fields.Datetime.now(),
            "hostname": hostname,
        }
        if str(bound).lower() in ("0", "false", "no"):
            values["state"] = "offline"
        else:
            values["state"] = "online"

        if profile:
            profile.write(values)
        else:
            profile = MacProfile.create(values)

        auto_create = env["ir.config_parameter"].sudo().get_param("isp_core.mac_auto_create")
        if auto_create in ("1", "true", "True") and not profile.subscription_id:
            plan_id = env["ir.config_parameter"].sudo().get_param("isp_core.mac_default_plan_id")
            if plan_id and str(plan_id).isdigit():
                plan = env["isp.service_plan"].sudo().browse(int(plan_id))
                sector_for_sub = sector_id or profile.sector_id.id
                if not sector_for_sub:
                    return Response("sector required for auto-create", status=400)
                partner = profile.partner_id
                if not partner:
                    partner = env["res.partner"].sudo().create({
                        "name": f"Auto {norm_mac}",
                        "is_isp_customer": True,
                    })
                    profile.partner_id = partner.id
                sub = env["isp.subscription"].sudo().create({
                    "partner_id": partner.id,
                    "plan_id": plan.id,
                    "sector_id": sector_for_sub,
                    "service_mac": norm_mac,
                    "service_ip": ip,
                    "state": "draft",
                })
                profile.subscription_id = sub.id
                profile.plan_id = plan.id

        auto_captive = env["ir.config_parameter"].sudo().get_param("isp_core.mac_auto_create_captive_user")
        if auto_captive in ("1", "true", "True") and "isp.captive.user" in env.registry.models:
            username = f"onu_{norm_mac.replace(':', '').lower()}"
            captive = env["isp.captive.user"].sudo().search([("username", "=", username)], limit=1)
            if not captive:
                profile_name = env["ir.config_parameter"].sudo().get_param("isp_core.mac_captive_default_profile") or "default"
                password = secrets.token_hex(4)
                router_id = False
                router = False
                if sector_id and "isp.mikrotik.router" in env.registry.models:
                    router = env["isp.mikrotik.router"].sudo().search([("sector_id", "=", sector_id)], limit=1)
                    router_id = router.id if router else False
                captive = env["isp.captive.user"].sudo().create({
                    "username": username,
                    "password": password,
                    "profile": profile_name,
                    "router_id": router_id,
                    "state": "disabled",
                })
                auto_prov = env["ir.config_parameter"].sudo().get_param("isp_core.mac_auto_provision_captive")
                if auto_prov in ("1", "true", "True") and router_id:
                    payload = {"captive_user_id": captive.id}
                    env["isp.provisioning_job"].sudo().create({
                        "job_type": "captive_user_create",
                        "payload_json": json.dumps(payload),
                        "sector_id": sector_id,
                        "device_id": router.device_id.id if router else False,
                    })

        return Response("ok", status=200)
