# -*- coding: utf-8 -*-
{
    "name": "ISP Billing",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Recurring billing and suspension automation",
    "depends": ["isp_core", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/parameters.xml",
        "data/mail_template.xml",
        "data/sequence.xml",
        "data/dashboard.xml",
        "data/cron.xml",
        "views/dashboard_views.xml",
        "views/bank_transfer_views.xml",
        "views/invoice_report_views.xml",
        "views/subscription_views.xml",
        "views/service_plan_views.xml"
    ],
    "installable": True,
    "license": "LGPL-3",
}
