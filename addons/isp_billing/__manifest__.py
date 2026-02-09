# -*- coding: utf-8 -*-
{
    "name": "ISP Billing",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Recurring billing and suspension automation",
    "depends": ["isp_core", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/cron.xml",
        "views/subscription_views.xml",
        "views/service_plan_views.xml"
    ],
    "installable": True,
    "license": "LGPL-3",
}
