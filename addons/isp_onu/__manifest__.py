# -*- coding: utf-8 -*-
{
    "name": "ISP ONU",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "ONU inventory and assignments",
    "depends": ["isp_core"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/onu_views.xml",
        "views/assignment_views.xml"
    ],
    "demo": [
        "demo/isp_onu_demo.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
