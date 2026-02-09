# -*- coding: utf-8 -*-
{
    "name": "ISP MikroTik",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "MikroTik RouterOS integration",
    "depends": ["isp_core"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/parameters.xml",
        "views/router_views.xml",
        "views/subscription_views.xml"
    ],
    "demo": [
        "demo/isp_mikrotik_demo.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
