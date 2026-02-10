# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class IspBankTransferPayment(models.Model):
    _name = "isp.bank.transfer.payment"
    _description = "ISP Bank Transfer Payment"
    _order = "id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(default="New")
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    subscription_id = fields.Many2one("isp.subscription", ondelete="set null")
    invoice_ids = fields.Many2many("account.move", string="Invoices")
    bank_name = fields.Char(required=True)
    reference = fields.Char(required=True)
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    transfer_datetime = fields.Datetime(default=fields.Datetime.now)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    notes = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("applied", "Applied"),
        ],
        default="draft",
    )
    reviewer_id = fields.Many2one("res.users", ondelete="set null")
    review_deadline = fields.Datetime()
    attention_deadline = fields.Datetime()
    rejection_reason = fields.Text()
    accounting_payment_id = fields.Many2one("account.payment", ondelete="set null")
    needs_attention = fields.Boolean(default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("isp.bank.transfer.payment") or "BTP"
        records = super().create(vals_list)
        for rec in records:
            rec._set_review_deadline()
        return records

    def _set_review_deadline(self):
        review_hours = int(self.env["ir.config_parameter"].sudo().get_param("isp_billing.transfer_review_hours", "48"))
        attention_hours = int(self.env["ir.config_parameter"].sudo().get_param("isp_billing.transfer_attention_hours", "24"))
        for rec in self:
            base_dt = rec.transfer_datetime or fields.Datetime.now()
            rec.review_deadline = base_dt + timedelta(hours=review_hours)
            rec.attention_deadline = base_dt + timedelta(hours=attention_hours)

    @api.constrains("state", "attachment_ids")
    def _check_attachments(self):
        for rec in self:
            if rec.state != "draft" and not rec.attachment_ids:
                raise ValidationError("Transfer payments require at least one attachment.")

    def action_submit(self):
        for rec in self:
            rec._set_review_deadline()
            rec.state = "in_review"
            rec.env["isp.audit_log"].sudo().log_action(
                action="transfer_submitted",
                record=rec,
                details=f"Transfer submitted {rec.name}",
            )
            rec._send_template("isp_billing.mail_template_transfer_submitted")

    def action_reject(self):
        for rec in self:
            if not rec.rejection_reason:
                raise ValidationError("Rejection reason is required.")
            rec.state = "rejected"
            rec.reviewer_id = self.env.user
            rec.env["isp.audit_log"].sudo().log_action(
                action="transfer_rejected",
                record=rec,
                details=f"Transfer rejected {rec.name}",
            )
            rec._send_template("isp_billing.mail_template_transfer_rejected")

    def action_approve(self):
        for rec in self:
            rec.reviewer_id = self.env.user
            rec.state = "approved"
            rec._create_and_apply_payment()
            rec.env["isp.audit_log"].sudo().log_action(
                action="transfer_approved",
                record=rec,
                details=f"Transfer approved {rec.name}",
            )
            rec._send_template("isp_billing.mail_template_transfer_approved")

    def _create_and_apply_payment(self):
        for rec in self:
            if rec.accounting_payment_id:
                rec.state = "applied"
                continue
            journal = rec._get_default_journal()
            if not journal:
                raise ValidationError("No suitable journal found for inbound payments.")
            if rec.invoice_ids:
                ctx = {
                    "active_model": "account.move",
                    "active_ids": rec.invoice_ids.ids,
                }
                wizard = self.env["account.payment.register"].with_context(ctx).create({
                    "payment_date": fields.Date.context_today(rec),
                    "amount": rec.amount,
                    "journal_id": journal.id,
                })
                payments = wizard._create_payments()
                if payments:
                    rec.accounting_payment_id = payments[0].id
            else:
                method_line = journal.inbound_payment_method_line_ids[:1]
                payment = self.env["account.payment"].create({
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": rec.partner_id.id,
                    "amount": rec.amount,
                    "currency_id": rec.currency_id.id,
                    "journal_id": journal.id,
                    "payment_method_line_id": method_line.id if method_line else False,
                    "date": fields.Date.context_today(rec),
                    "ref": rec.reference,
                })
                payment.action_post()
                rec.accounting_payment_id = payment.id
            rec.state = "applied"

    def _get_default_journal(self):
        company_id = self.env.company.id
        return self.env["account.journal"].search(
            [("type", "in", ("bank", "cash")), ("company_id", "=", company_id)],
            limit=1,
        )

    @api.model
    def _cron_transfer_deadlines(self):
        now = fields.Datetime.now()
        records = self.search([
            ("state", "=", "in_review"),
            ("attention_deadline", "!=", False),
            ("attention_deadline", "<=", now),
        ])
        for rec in records:
            rec.needs_attention = True

    def _send_template(self, xmlid):
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template:
            return
        for rec in self:
            if not rec.partner_id or not rec.partner_id.email:
                continue
            template.send_mail(rec.id, force_send=False, raise_exception=False)
