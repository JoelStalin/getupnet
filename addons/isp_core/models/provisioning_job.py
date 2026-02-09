# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models
from odoo.exceptions import UserError


class IspProvisioningJob(models.Model):
    _name = "isp.provisioning_job"
    _description = "ISP Provisioning Job"
    _order = "requested_at desc"

    name = fields.Char(default="New")
    job_type = fields.Selection(
        [
            ("activate_subscription", "Activate Subscription"),
            ("suspend_subscription", "Suspend Subscription"),
            ("reconnect_subscription", "Reconnect Subscription"),
            ("terminate_subscription", "Terminate Subscription"),
            ("change_plan", "Change Plan"),
            ("disconnect_session", "Disconnect Session"),
            ("mikrotik_healthcheck", "MikroTik Healthcheck"),
            ("captive_user_create", "Captive User Create"),
            ("captive_user_disable", "Captive User Disable"),
            ("walled_garden_apply", "Walled Garden Apply"),
            ("export_config_snapshot", "Export Config Snapshot"),
        ],
        required=True,
    )
    subscription_id = fields.Many2one("isp.subscription", ondelete="set null")
    device_id = fields.Many2one("isp.device", ondelete="set null")
    sector_id = fields.Many2one("isp.sector", ondelete="set null")
    state = fields.Selection(
        [("queued", "Queued"), ("running", "Running"), ("success", "Success"), ("failed", "Failed")],
        default="queued",
    )
    attempts = fields.Integer(default=0)
    max_attempts = fields.Integer(default=3)
    error_message = fields.Text()
    traceback = fields.Text()
    requested_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    requested_at = fields.Datetime(default=fields.Datetime.now)
    executed_at = fields.Datetime()
    payload_json = fields.Text(default="{}")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("isp.provisioning.job") or "JOB"
        return super().create(vals_list)

    @api.model
    def _cron_run_pending_jobs(self):
        jobs = self.search([("state", "=", "queued")], limit=20, order="requested_at asc")
        for job in jobs:
            job._execute()

    def action_run(self):
        for job in self:
            job._execute()

    def _execute(self):
        self.ensure_one()
        if self.state != "queued":
            return
        if self.attempts >= self.max_attempts:
            self.write({"state": "failed", "error_message": "Max attempts reached"})
            return
        self.write(
            {
                "state": "running",
                "attempts": self.attempts + 1,
                "executed_at": fields.Datetime.now(),
                "error_message": False,
                "traceback": False,
            }
        )
        try:
            self._dispatch()
            self.write({"state": "success"})
        except Exception as exc:
            self.write({"state": "failed", "error_message": str(exc)})
            raise

    def _dispatch(self):
        method_name = f"_handle_{self.job_type}"
        handler = getattr(self, method_name, None)
        if not handler:
            raise UserError(f"No handler for job type: {self.job_type}")
        return handler()

    def get_payload(self):
        self.ensure_one()
        try:
            return json.loads(self.payload_json or "{}")
        except Exception:
            return {}
