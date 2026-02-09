# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import UserError
from odoo.addons.isp_mikrotik.models.routeros_client import get_routeros_client, LibRouterosError


class IspProvisioningJob(models.Model):
    _inherit = "isp.provisioning_job"

    def _get_router_for_captive(self, rec):
        Router = self.env["isp.mikrotik.router"]
        if rec.router_id:
            return rec.router_id
        if rec.sector_id:
            router = Router.search([("sector_id", "=", rec.sector_id.id)], limit=1)
            if router:
                return router
        raise UserError("No MikroTik router found for captive operation.")

    def _handle_captive_user_create(self):
        payload = self.get_payload()
        user_id = payload.get("captive_user_id")
        if not user_id:
            raise UserError("captive_user_id missing in payload.")
        user = self.env["isp.captive.user"].browse(user_id)
        router = self._get_router_for_captive(user)
        client = get_routeros_client(self.env, router)
        profile = user.profile or "default"
        try:
            client.cmd(
                "/ip/hotspot/user/add",
                name=user.username,
                password=user.password or "",
                profile=profile,
                disabled="no",
                comment=user.sector_id.code if user.sector_id else "",
            )
        except LibRouterosError:
            client.cmd(
                "/ip/hotspot/user/set",
                **{"numbers": user.username, "profile": profile, "disabled": "no"},
            )
        user.state = "active"

    def _handle_captive_user_disable(self):
        payload = self.get_payload()
        user_id = payload.get("captive_user_id")
        if not user_id:
            raise UserError("captive_user_id missing in payload.")
        user = self.env["isp.captive.user"].browse(user_id)
        router = self._get_router_for_captive(user)
        client = get_routeros_client(self.env, router)
        try:
            client.cmd(
                "/ip/hotspot/user/set",
                **{"numbers": user.username, "disabled": "yes"},
            )
        except LibRouterosError:
            return
        user.state = "disabled"

    def _handle_walled_garden_apply(self):
        payload = self.get_payload()
        wg_id = payload.get("walled_garden_id")
        if not wg_id:
            raise UserError("walled_garden_id missing in payload.")
        wg = self.env["isp.captive.walled_garden"].browse(wg_id)
        router = self._get_router_for_captive(wg)
        client = get_routeros_client(self.env, router)
        try:
            client.cmd(
                "/ip/hotspot/walled-garden/add",
                **{"dst-host": wg.domain},
            )
        except LibRouterosError:
            return
