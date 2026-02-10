# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class IspPlanChangeRequest(models.Model):
    _name = "isp.plan.change.request"
    _description = "ISP Plan Change Request"
    _order = "id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(default="New")
    subscription_id = fields.Many2one("isp.subscription", required=True, ondelete="cascade")
    partner_id = fields.Many2one(related="subscription_id.partner_id", store=True, readonly=True)
    current_plan_id = fields.Many2one(related="subscription_id.plan_id", store=True, readonly=True)
    requested_plan_id = fields.Many2one("isp.service_plan", required=True, ondelete="restrict")
    effective_date_mode = fields.Selection(
        [("immediate", "Immediate"), ("next_cycle", "Next Cycle"), ("custom", "Custom")],
        default="next_cycle",
        required=True,
    )
    effective_date = fields.Date()
    prorate = fields.Boolean(default=False)
    state = fields.Selection(
        [("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"), ("rejected", "Rejected"), ("applied", "Applied")],
        default="draft",
    )
    requested_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    requested_at = fields.Datetime(default=fields.Datetime.now)
    approved_by = fields.Many2one("res.users")
    rejection_reason = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("isp.plan.change.request") or "PCR"
        records = super().create(vals_list)
        for rec in records:
            rec._ensure_effective_date()
        return records

    def _ensure_effective_date(self):
        for rec in self:
            if rec.effective_date:
                continue
            if rec.effective_date_mode == "immediate":
                rec.effective_date = fields.Date.context_today(rec)
            elif rec.effective_date_mode == "next_cycle":
                next_date = rec.subscription_id.next_invoice_date
                if not next_date:
                    next_date = fields.Date.context_today(rec) + relativedelta(months=1)
                rec.effective_date = next_date

    @api.constrains("requested_plan_id", "current_plan_id")
    def _check_plan_diff(self):
        for rec in self:
            if rec.requested_plan_id and rec.current_plan_id and rec.requested_plan_id.id == rec.current_plan_id.id:
                raise ValidationError("Requested plan must be different from current plan.")

    @api.constrains("effective_date_mode", "effective_date")
    def _check_effective_date(self):
        for rec in self:
            if rec.effective_date_mode == "custom" and not rec.effective_date:
                raise ValidationError("Custom effective date is required.")

    def action_submit(self):
        for rec in self:
            if rec.effective_date_mode == "immediate" and not self.env.user.has_group("isp_core.group_isp_admin") and not self.env.user.has_group("isp_core.group_isp_noc"):
                raise ValidationError("Immediate plan changes require Admin or NOC permissions.")
            rec._ensure_effective_date()
            rec.state = "submitted"
            rec.env["isp.audit_log"].sudo().log_action(
                action="plan_change_submitted",
                record=rec.subscription_id,
                details=f"Plan change requested to {rec.requested_plan_id.name}",
            )
            rec._send_template("isp_core.mail_template_plan_change_submitted")

    def action_approve(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec._ensure_effective_date()
            rec.state = "approved"
            rec.approved_by = self.env.user
            rec.env["isp.audit_log"].sudo().log_action(
                action="plan_change_approved",
                record=rec.subscription_id,
                details=f"Plan change approved to {rec.requested_plan_id.name}",
            )
            rec._send_template("isp_core.mail_template_plan_change_approved")
            if rec.effective_date and rec.effective_date <= today:
                rec.action_apply()

    def action_reject(self):
        for rec in self:
            if not rec.rejection_reason:
                raise ValidationError("Rejection reason is required.")
            rec.state = "rejected"
            rec.env["isp.audit_log"].sudo().log_action(
                action="plan_change_rejected",
                record=rec.subscription_id,
                details="Plan change rejected",
            )
            rec._send_template("isp_core.mail_template_plan_change_rejected")

    def action_apply(self):
        for rec in self:
            sub = rec.subscription_id
            if not sub:
                continue
            sub.plan_id = rec.requested_plan_id
            sub._ensure_pppoe_credentials()
            sub._queue_job("change_plan")
            rec.state = "applied"
            rec.env["isp.audit_log"].sudo().log_action(
                action="plan_change_applied",
                record=sub,
                details=f"Plan changed to {rec.requested_plan_id.name}",
            )
            rec._send_template("isp_core.mail_template_plan_change_applied")

    @api.model
    def _cron_apply_plan_changes(self):
        today = fields.Date.today()
        records = self.search([
            ("state", "=", "approved"),
            ("effective_date", "!=", False),
            ("effective_date", "<=", today),
        ])
        for rec in records:
            rec.action_apply()

    def _send_template(self, xmlid):
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template:
            return
        for rec in self:
            if not rec.partner_id or not rec.partner_id.email:
                continue
            template.send_mail(rec.id, force_send=False, raise_exception=False)
