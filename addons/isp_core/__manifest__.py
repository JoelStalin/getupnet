# -*- coding: utf-8 -*-
{
    "name": "ISP Core",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Core ISP domain models and provisioning framework",
    "depends": ["base"],
    "data": [
        "security/isp_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/sequence.xml",
        "data/cron.xml",
        "views/isp_menu.xml",
        "views/sector_views.xml",
        "views/device_views.xml",
        "views/service_plan_views.xml",
        "views/subscription_views.xml",
        "views/res_partner_views.xml",
        "views/res_users_views.xml",
        "views/job_views.xml",
        "views/audit_views.xml"
    ],
    "demo": [
        "demo/isp_demo.xml",
    ],
    "application": True,
    "installable": True,
    "license": "LGPL-3",
}
