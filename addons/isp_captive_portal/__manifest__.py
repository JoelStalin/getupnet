# -*- coding: utf-8 -*-
{
    "name": "ISP Captive Portal",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Captive portal management and vouchers",
    "depends": ["isp_core", "isp_mikrotik", "website"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/cron.xml",
        "views/captive_user_views.xml",
        "views/walled_garden_views.xml",
        "views/session_views.xml",
        "views/portal_templates.xml"
    ],
    "demo": [
        "demo/isp_captive_demo.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
