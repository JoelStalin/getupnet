# -*- coding: utf-8 -*-
{
    "name": "ISP Portal",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Customer portal for ISP subscriptions",
    "depends": ["isp_core", "isp_billing", "portal", "website"],
    "data": [
        "security/isp_portal_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/portal_templates.xml"
    ],
    "installable": True,
    "license": "LGPL-3",
}
