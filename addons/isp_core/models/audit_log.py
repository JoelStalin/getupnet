# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IspAuditLog(models.Model):
    _name = "isp.audit_log"
    _description = "ISP Audit Log"
    _order = "timestamp desc"

    action = fields.Char(required=True)
    record_model = fields.Char()
    record_id = fields.Integer()
    record_name = fields.Char()
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    timestamp = fields.Datetime(default=fields.Datetime.now)
    details = fields.Text()

    @api.model
    def log_action(self, action, record, details=None):
        vals = {
            "action": action,
            "record_model": record._name if record else False,
            "record_id": record.id if record else False,
            "record_name": record.display_name if record else False,
            "details": details or "",
        }
        return self.create(vals)
