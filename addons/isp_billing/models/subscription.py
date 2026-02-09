# -*- coding: utf-8 -*-
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class IspSubscription(models.Model):
    _inherit = "isp.subscription"

    last_invoice_id = fields.Many2one("account.move", ondelete="set null")

    def action_generate_invoice(self):
        for sub in self:
            sub._generate_invoice()

    def _generate_invoice(self):
        self.ensure_one()
        if not self.partner_id:
            return False
        plan = self.plan_id
        move_vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": fields.Date.today(),
            "invoice_date_due": fields.Date.today(),
            "isp_subscription_id": self.id,
            "invoice_line_ids": [
                (0, 0, {
                    "name": plan.name,
                    "quantity": 1.0,
                    "price_unit": plan.price or 0.0,
                    "tax_ids": [(6, 0, plan.tax_ids.ids)],
                })
            ],
        }
        move = self.env["account.move"].create(move_vals)
        try:
            move.action_post()
        except Exception:
            # Leave in draft if posting fails.
            pass
        self.last_invoice_id = move.id
        self.next_invoice_date = (self.next_invoice_date or fields.Date.today()) + relativedelta(months=1)
        self.env["isp.audit_log"].sudo().log_action(
            action="invoice_generated",
            record=self,
            details=f"Invoice {move.name or move.id} generated",
        )
        return move

    @api.model
    def _cron_generate_invoices(self):
        today = fields.Date.today()
        subs = self.search([
            ("state", "=", "active"),
            ("next_invoice_date", "!=", False),
            ("next_invoice_date", "<=", today),
        ])
        for sub in subs:
            sub._generate_invoice()

    @api.model
    def _cron_suspend_overdue(self):
        today = fields.Date.today()
        moves = self.env["account.move"].search([
            ("isp_subscription_id", "!=", False),
            ("state", "=", "posted"),
            ("payment_state", "not in", ("paid", "in_payment")),
        ])
        for move in moves:
            sub = move.isp_subscription_id
            if not sub or sub.state != "active":
                continue
            days = sub.plan_id.suspend_after_days or 0
            due_date = move.invoice_date_due or move.invoice_date
            if not due_date:
                continue
            if today >= due_date + timedelta(days=days):
                sub._queue_job("suspend_subscription")

    @api.model
    def _cron_reconnect_on_payment(self):
        subs = self.search([("state", "=", "suspended")])
        for sub in subs:
            open_count = self.env["account.move"].search_count([
                ("isp_subscription_id", "=", sub.id),
                ("state", "=", "posted"),
                ("payment_state", "not in", ("paid", "in_payment")),
            ])
            if open_count == 0:
                sub._queue_job("reconnect_subscription")
