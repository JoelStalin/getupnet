# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import UserError

try:
    from librouteros import connect
    from librouteros.exceptions import LibRouterosError
except Exception:  # pragma: no cover - optional dependency
    connect = None
    LibRouterosError = Exception


class DummyRouterOS:
    def __init__(self, env, router):
        self.env = env
        self.router = router

    def cmd(self, path, **kwargs):
        self.env["isp.audit_log"].sudo().log_action(
            action="routeros.dry_run",
            record=self.router.device_id,
            details=f"{path} {kwargs}",
        )
        return []


class RouterOSAdapter:
    def __init__(self, env, router):
        if not connect:
            raise UserError("librouteros is not installed in this Odoo environment.")
        info = router.get_connection_info()
        if not info.get("host"):
            raise UserError("Router management IP is missing.")
        if not info.get("password"):
            raise UserError("Router API password is missing.")
        self.env = env
        self.router = router
        self.api = connect(
            host=info["host"],
            username=info["user"],
            password=info["password"],
            port=info.get("port") or 8728,
        )

    def cmd(self, path, **kwargs):
        return list(self.api(path, **kwargs))


def get_routeros_client(env, router):
    dry_run = env["ir.config_parameter"].sudo().get_param("isp_mikrotik.dry_run")
    if dry_run in ("1", "true", "True", True):
        return DummyRouterOS(env, router)
    return RouterOSAdapter(env, router)
