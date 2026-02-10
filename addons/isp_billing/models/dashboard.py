# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class IspDashboard(models.Model):
    _name = "isp.dashboard"
    _description = "ISP Dashboard"
    _rec_name = "name"

    name = fields.Char(default="ISP Dashboard")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    active_subscriptions = fields.Integer(compute="_compute_metrics", store=False)
    up_to_date_subscriptions = fields.Integer(compute="_compute_metrics", store=False)
    suspended_subscriptions = fields.Integer(compute="_compute_metrics", store=False)
    overdue_subscriptions = fields.Integer(compute="_compute_metrics", store=False)
    grace_subscriptions = fields.Integer(compute="_compute_metrics", store=False)
    mrr = fields.Monetary(compute="_compute_metrics", store=False, currency_field="currency_id")
    invoices_month = fields.Monetary(compute="_compute_metrics", store=False, currency_field="currency_id")
    transfer_pending = fields.Integer(compute="_compute_metrics", store=False)
    transfer_attention = fields.Integer(compute="_compute_metrics", store=False)
    faults_open = fields.Integer(compute="_compute_metrics", store=False)
    faults_closed = fields.Integer(compute="_compute_metrics", store=False)
    avg_resolution_hours = fields.Float(compute="_compute_metrics", store=False)
    top_overdue_sectors = fields.Char(compute="_compute_metrics", store=False)

    @api.depends_context("uid")
    def _compute_metrics(self):
        today = fields.Date.today()
        month_start = date(today.year, today.month, 1)
        month_end = month_start + relativedelta(months=1, days=-1)
        Subscription = self.env["isp.subscription"].sudo()
        Move = self.env["account.move"].sudo()
        Transfer = self.env["isp.bank.transfer.payment"].sudo()
        Fault = self.env["isp.fault.ticket"].sudo()

        active_subs = Subscription.search_count([("state", "=", "active")])
        suspended_subs = Subscription.search_count([("state", "=", "suspended")])
        status_map = self._get_subscription_status_map()
        overdue_subs = sum(1 for status in status_map.values() if status == "in_arrears")
        grace_subs = sum(1 for status in status_map.values() if status == "grace")
        up_to_date_subs = sum(1 for status in status_map.values() if status == "up_to_date")
        mrr_total = sum(Subscription.search([("state", "=", "active")]).mapped("plan_id.price"))
        invoices_month = sum(Move.search([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", month_start),
            ("invoice_date", "<=", month_end),
        ]).mapped("amount_total"))
        transfer_pending = Transfer.search_count([("state", "=", "in_review")])
        transfer_attention = Transfer.search_count([("state", "=", "in_review"), ("needs_attention", "=", True)])
        faults_open = Fault.search_count([("state", "not in", ("resolved", "closed"))])
        faults_closed = Fault.search_count([("state", "in", ("resolved", "closed"))])
        resolution_group = Fault.read_group(
            [("state", "in", ("resolved", "closed")), ("resolution_time_hours", ">", 0)],
            ["resolution_time_hours:avg"],
            [],
        )
        avg_resolution = resolution_group[0]["resolution_time_hours_avg"] if resolution_group else 0.0
        top_overdue = self._get_top_overdue_sectors()

        for rec in self:
            rec.active_subscriptions = active_subs
            rec.up_to_date_subscriptions = up_to_date_subs
            rec.suspended_subscriptions = suspended_subs
            rec.overdue_subscriptions = overdue_subs
            rec.grace_subscriptions = grace_subs
            rec.mrr = mrr_total
            rec.invoices_month = invoices_month
            rec.transfer_pending = transfer_pending
            rec.transfer_attention = transfer_attention
            rec.faults_open = faults_open
            rec.faults_closed = faults_closed
            rec.avg_resolution_hours = avg_resolution
            rec.top_overdue_sectors = top_overdue

    def _get_subscription_status_map(self):
        today = fields.Date.today()
        grace_days = int(self.env["ir.config_parameter"].sudo().get_param("isp_billing.grace_days", "5"))
        subs = self.env["isp.subscription"].sudo().search([("state", "=", "active")])
        status_map = {sub.id: "up_to_date" for sub in subs}
        if not subs:
            return status_map
        moves = self.env["account.move"].sudo().search([
            ("isp_subscription_id", "in", subs.ids),
            ("state", "=", "posted"),
            ("payment_state", "not in", ("paid", "in_payment")),
            ("invoice_date_due", "!=", False),
        ])
        for move in moves:
            sub_id = move.isp_subscription_id.id
            if not sub_id:
                continue
            due_date = move.invoice_date_due
            if not due_date:
                continue
            if due_date + relativedelta(days=grace_days) >= today:
                if status_map.get(sub_id) != "in_arrears":
                    status_map[sub_id] = "grace"
            else:
                status_map[sub_id] = "in_arrears"
        return status_map

    def _get_top_overdue_sectors(self):
        Move = self.env["account.move"].sudo()
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "not in", ("paid", "in_payment")),
            ("invoice_date_due", "!=", False),
            ("isp_sector_id", "!=", False),
        ]
        groups = Move.read_group(domain, ["amount_residual:sum"], ["isp_sector_id"])
        def residual_amount(g):
            return g.get("amount_residual", 0.0) or g.get("amount_residual_sum", 0.0)
        sorted_groups = sorted(
            [g for g in groups if g.get("isp_sector_id")],
            key=residual_amount,
            reverse=True,
        )[:5]
        parts = []
        for group in sorted_groups:
            sector = group["isp_sector_id"][1]
            amount = residual_amount(group)
            parts.append(f"{sector} ({amount:.2f})")
        return ", ".join(parts)

    def action_open_active_subscriptions(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Active Subscriptions",
            "res_model": "isp.subscription",
            "view_mode": "list,form",
            "domain": [("state", "=", "active")],
        }

    def action_open_suspended_subscriptions(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Suspended Subscriptions",
            "res_model": "isp.subscription",
            "view_mode": "list,form",
            "domain": [("state", "=", "suspended")],
        }

    def action_open_overdue_invoices(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Overdue Invoices",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "not in", ("paid", "in_payment")),
                ("invoice_date_due", "<", fields.Date.today()),
            ],
        }

    def action_open_up_to_date_subscriptions(self):
        status_map = self._get_subscription_status_map()
        ids = [sid for sid, status in status_map.items() if status == "up_to_date"]
        return {
            "type": "ir.actions.act_window",
            "name": "Up to Date Subscriptions",
            "res_model": "isp.subscription",
            "view_mode": "list,form",
            "domain": [("id", "in", ids)],
        }

    def action_open_in_arrears_subscriptions(self):
        status_map = self._get_subscription_status_map()
        ids = [sid for sid, status in status_map.items() if status == "in_arrears"]
        return {
            "type": "ir.actions.act_window",
            "name": "Subscriptions in Arrears",
            "res_model": "isp.subscription",
            "view_mode": "list,form",
            "domain": [("id", "in", ids)],
        }

    def action_open_transfer_pending(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Transfers In Review",
            "res_model": "isp.bank.transfer.payment",
            "view_mode": "list,form",
            "domain": [("state", "=", "in_review")],
        }

    def action_open_faults_open(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Open Fault Tickets",
            "res_model": "isp.fault.ticket",
            "view_mode": "list,form",
            "domain": [("state", "not in", ("resolved", "closed"))],
        }
