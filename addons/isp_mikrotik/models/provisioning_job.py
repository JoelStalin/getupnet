# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError
from .routeros_client import get_routeros_client, LibRouterosError


class IspProvisioningJob(models.Model):
    _inherit = "isp.provisioning_job"

    job_type = fields.Selection(
        selection_add=[
            ("activate_pppoe", "Activate PPPoE"),
            ("activate_dhcp", "Activate DHCP"),
            ("ensure_queue", "Ensure Queue"),
        ],
        ondelete={
            "activate_pppoe": "cascade",
            "activate_dhcp": "cascade",
            "ensure_queue": "cascade",
        },
    )

    def _get_router(self):
        self.ensure_one()
        Router = self.env["isp.mikrotik.router"]
        router = False
        if self.device_id:
            router = Router.search([("device_id", "=", self.device_id.id)], limit=1)
        if not router and self.subscription_id and self.subscription_id.router_id:
            router = self.subscription_id.router_id
        if not router and self.subscription_id and self.subscription_id.sector_id:
            router = Router.search([("sector_id", "=", self.subscription_id.sector_id.id)], limit=1)
        if not router:
            raise UserError("No MikroTik router found for this job.")
        return router

    def _routeros_pppoe_ensure_secret(self, client, subscription):
        profile = subscription.plan_id.mikrotik_profile or "default"
        try:
            client.cmd(
                "/ppp/secret/add",
                name=subscription.pppoe_username,
                password=subscription.pppoe_password,
                profile=profile,
                service="pppoe",
            )
        except LibRouterosError:
            client.cmd(
                "/ppp/secret/set",
                **{
                    "numbers": subscription.pppoe_username,
                    "password": subscription.pppoe_password,
                    "profile": profile,
                    "disabled": "no",
                },
            )

    def _routeros_pppoe_disable(self, client, subscription):
        try:
            client.cmd(
                "/ppp/secret/set",
                **{"numbers": subscription.pppoe_username, "disabled": "yes"},
            )
        except LibRouterosError:
            return

    def _routeros_pppoe_enable(self, client, subscription):
        try:
            client.cmd(
                "/ppp/secret/set",
                **{"numbers": subscription.pppoe_username, "disabled": "no"},
            )
        except LibRouterosError:
            return

    def _routeros_dhcp_ensure_lease(self, client, subscription):
        if not subscription.service_ip or not subscription.service_mac:
            return
        try:
            client.cmd(
                "/ip/dhcp-server/lease/add",
                address=subscription.service_ip,
                **{"mac-address": subscription.service_mac},
                comment=subscription.name,
            )
        except LibRouterosError:
            client.cmd(
                "/ip/dhcp-server/lease/set",
                **{
                    "numbers": subscription.service_ip,
                    "comment": subscription.name,
                    "disabled": "no",
                },
            )

    def _routeros_queue_ensure(self, client, subscription):
        if not subscription.service_ip:
            return
        down = subscription.plan_id.down_mbps or 0
        up = subscription.plan_id.up_mbps or 0
        max_limit = f"{down}M/{up}M"
        name = subscription.name
        try:
            client.cmd(
                "/queue/simple/add",
                name=name,
                target=f"{subscription.service_ip}/32",
                **{"max-limit": max_limit},
                comment=subscription.name,
            )
        except LibRouterosError:
            client.cmd(
                "/queue/simple/set",
                **{"numbers": name, "max-limit": max_limit, "disabled": "no"},
            )

    def _routeros_queue_disable(self, client, subscription):
        name = subscription.name
        try:
            client.cmd(
                "/queue/simple/set",
                **{"numbers": name, "disabled": "yes"},
            )
        except LibRouterosError:
            return

    def _routeros_queue_remove(self, client, subscription):
        name = subscription.name
        try:
            client.cmd("/queue/simple/remove", **{"numbers": name})
        except LibRouterosError:
            return

    def _handle_mikrotik_healthcheck(self):
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        try:
            resource = client.cmd("/system/resource/print")
            identity = client.cmd("/system/identity/print")
            version = False
            if resource:
                version = resource[0].get("version")
            if identity and identity[0].get("name"):
                router.device_id.name = identity[0].get("name")
            router.write(
                {
                    "routeros_version": version,
                    "last_healthcheck_at": fields.Datetime.now(),
                    "last_healthcheck_status": "ok",
                }
            )
        except Exception:
            router.write(
                {
                    "last_healthcheck_at": fields.Datetime.now(),
                    "last_healthcheck_status": "failed",
                }
            )
            raise

    def _handle_activate_subscription(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        sub._ensure_pppoe_credentials()
        router = self._get_router()
        client = get_routeros_client(self.env, router)

        if sub.plan_id.service_type == "pppoe":
            self._routeros_pppoe_ensure_secret(client, sub)
        elif sub.plan_id.service_type == "dhcp":
            self._routeros_dhcp_ensure_lease(client, sub)

        self._routeros_queue_ensure(client, sub)
        sub.write({"state": "active", "start_date": sub.start_date or fields.Date.today()})

    def _handle_suspend_subscription(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        if sub.plan_id.service_type == "pppoe":
            self._routeros_pppoe_disable(client, sub)
        self._routeros_queue_disable(client, sub)
        sub.write({"state": "suspended"})

    def _handle_reconnect_subscription(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        if sub.plan_id.service_type == "pppoe":
            self._routeros_pppoe_enable(client, sub)
        self._routeros_queue_ensure(client, sub)
        sub.write({"state": "active"})

    def _handle_terminate_subscription(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        if sub.plan_id.service_type == "pppoe":
            self._routeros_pppoe_disable(client, sub)
        self._routeros_queue_remove(client, sub)
        sub.write({"state": "terminated"})

    def _handle_change_plan(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        if sub.plan_id.service_type == "pppoe":
            self._routeros_pppoe_ensure_secret(client, sub)
        self._routeros_queue_ensure(client, sub)

    def _handle_disconnect_session(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        if sub.plan_id.service_type == "pppoe":
            client.cmd("/ppp/active/remove", **{"numbers": sub.pppoe_username})
        else:
            client.cmd("/ip/hotspot/active/remove", **{"numbers": sub.pppoe_username})

    def _handle_activate_pppoe(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        sub._ensure_pppoe_credentials()
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        self._routeros_pppoe_ensure_secret(client, sub)

    def _handle_activate_dhcp(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        self._routeros_dhcp_ensure_lease(client, sub)

    def _handle_ensure_queue(self):
        if not self.subscription_id:
            raise UserError("Subscription is required.")
        sub = self.subscription_id
        router = self._get_router()
        client = get_routeros_client(self.env, router)
        self._routeros_queue_ensure(client, sub)
