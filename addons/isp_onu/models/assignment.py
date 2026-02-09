# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class IspOnuAssignment(models.Model):
    _name = "isp.onu.assignment"
    _description = "ONU Assignment"
    _order = "assigned_at desc"

    onu_id = fields.Many2one("isp.onu", required=True, ondelete="restrict")
    subscription_id = fields.Many2one("isp.subscription", required=True, ondelete="cascade")
    sector_id = fields.Many2one(related="subscription_id.sector_id", store=True, readonly=True)
    active = fields.Boolean(default=True)
    assigned_at = fields.Datetime()
    unassigned_at = fields.Datetime()
    vlan = fields.Char()
    profile = fields.Char()
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("active", True) and not vals.get("assigned_at"):
                vals["assigned_at"] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals:
            for rec in self:
                if rec.active and not rec.assigned_at:
                    rec.assigned_at = fields.Datetime.now()
                if not rec.active and not rec.unassigned_at:
                    rec.unassigned_at = fields.Datetime.now()
        return res

    @api.constrains("onu_id", "active")
    def _check_one_active_per_onu(self):
        for rec in self:
            if rec.active:
                count = self.search_count([
                    ("onu_id", "=", rec.onu_id.id),
                    ("active", "=", True),
                    ("id", "!=", rec.id),
                ])
                if count:
                    raise ValidationError("ONU already has an active assignment.")

    @api.constrains("subscription_id", "active")
    def _check_one_active_per_subscription(self):
        for rec in self:
            if rec.active:
                count = self.search_count([
                    ("subscription_id", "=", rec.subscription_id.id),
                    ("active", "=", True),
                    ("id", "!=", rec.id),
                ])
                if count:
                    raise ValidationError("Subscription already has an active ONU.")
