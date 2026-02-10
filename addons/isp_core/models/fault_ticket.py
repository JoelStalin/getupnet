# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspFaultTicket(models.Model):
    _name = "isp.fault.ticket"
    _description = "ISP Fault Ticket"
    _order = "id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(default="New")
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    subscription_id = fields.Many2one("isp.subscription", ondelete="set null")
    sector_id = fields.Many2one(related="subscription_id.sector_id", store=True, readonly=True)
    gps_lat = fields.Float()
    gps_lng = fields.Float()
    fault_type = fields.Selection(
        [
            ("outage", "Outage"),
            ("speed", "Speed"),
            ("billing", "Billing"),
            ("equipment", "Equipment"),
            ("other", "Other"),
        ],
        default="outage",
        required=True,
    )
    priority = fields.Selection(
        [("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")],
        default="normal",
        required=True,
    )
    description = fields.Text()
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    state = fields.Selection(
        [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("waiting_customer", "Waiting Customer"),
            ("resolved", "Resolved"),
            ("closed", "Closed"),
        ],
        default="new",
    )
    assigned_to = fields.Many2one("res.users", string="Assigned To", ondelete="set null")
    opened_at = fields.Datetime()
    closed_at = fields.Datetime()
    resolution_time_hours = fields.Float(compute="_compute_resolution_time_hours", store=True)
    sla_target_hours = fields.Float(compute="_compute_sla_target_hours", store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("isp.fault.ticket") or "FLT"
            if not vals.get("opened_at"):
                vals["opened_at"] = fields.Datetime.now()
        records = super().create(vals_list)
        for rec in records:
            if rec.subscription_id:
                rec.gps_lat = rec.subscription_id.gps_lat
                rec.gps_lng = rec.subscription_id.gps_lng
            rec._send_template("isp_core.mail_template_fault_created")
        return records

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            for rec in self:
                if rec.state in ("resolved", "closed") and not rec.closed_at:
                    rec.closed_at = fields.Datetime.now()
        return res

    @api.depends("opened_at", "closed_at")
    def _compute_resolution_time_hours(self):
        for rec in self:
            if rec.opened_at and rec.closed_at:
                delta = rec.closed_at - rec.opened_at
                rec.resolution_time_hours = delta.total_seconds() / 3600.0
            else:
                rec.resolution_time_hours = 0.0

    @api.depends("priority")
    def _compute_sla_target_hours(self):
        mapping = {
            "low": 72.0,
            "normal": 48.0,
            "high": 24.0,
            "urgent": 8.0,
        }
        for rec in self:
            rec.sla_target_hours = mapping.get(rec.priority, 48.0)

    def action_start(self):
        for rec in self:
            rec.state = "in_progress"

    def action_waiting(self):
        for rec in self:
            rec.state = "waiting_customer"

    def action_resolve(self):
        for rec in self:
            rec.state = "resolved"
            if not rec.closed_at:
                rec.closed_at = fields.Datetime.now()
            rec._send_template("isp_core.mail_template_fault_resolved")

    def action_close(self):
        for rec in self:
            rec.state = "closed"
            if not rec.closed_at:
                rec.closed_at = fields.Datetime.now()
            rec._send_template("isp_core.mail_template_fault_closed")

    def _send_template(self, xmlid):
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template:
            return
        for rec in self:
            if not rec.partner_id or not rec.partner_id.email:
                continue
            template.send_mail(rec.id, force_send=False, raise_exception=False)
