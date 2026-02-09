# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspMikrotikRouter(models.Model):
    _name = "isp.mikrotik.router"
    _description = "MikroTik Router"
    _order = "device_id"

    name = fields.Char(related="device_id.name", store=True)
    device_id = fields.Many2one("isp.device", required=True, ondelete="cascade", domain=[("device_type", "=", "mikrotik")])
    sector_id = fields.Many2one(related="device_id.sector_id", store=True)
    api_user = fields.Char(groups="isp_core.group_isp_admin,isp_core.group_isp_noc")
    auth_method = fields.Selection([( "api", "API"), ("ssh", "SSH")], default="api")
    routeros_version = fields.Char(readonly=True)
    last_healthcheck_at = fields.Datetime(readonly=True)
    last_healthcheck_status = fields.Selection([("ok", "OK"), ("failed", "Failed")], readonly=True)

    def _get_api_user(self):
        self.ensure_one()
        if self.api_user:
            return self.api_user
        return self.env["ir.config_parameter"].sudo().get_param("isp_mikrotik.default_api_user") or "odoo_noc"

    def _get_api_password(self):
        self.ensure_one()
        param_key = f"isp_mikrotik.router_password.{self.id}"
        password = self.env["ir.config_parameter"].sudo().get_param(param_key)
        if password:
            return password
        return self.env["ir.config_parameter"].sudo().get_param("isp_mikrotik.default_api_password")

    def action_healthcheck(self):
        for router in self:
            vals = {
                "job_type": "mikrotik_healthcheck",
                "device_id": router.device_id.id,
                "sector_id": router.sector_id.id,
            }
            self.env["isp.provisioning_job"].create(vals)

    def get_connection_info(self):
        self.ensure_one()
        return {
            "host": self.device_id.mgmt_ip,
            "port": self.device_id.mgmt_port or 8728,
            "user": self._get_api_user(),
            "password": self._get_api_password(),
        }
