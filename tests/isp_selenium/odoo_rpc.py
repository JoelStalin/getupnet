import os
from xmlrpc import client as xmlrpc_client


class OdooRPC:
    def __init__(self):
        self.url = os.environ.get("ODOO_RPC_URL") or os.environ.get("ODOO_BASE_URL", "http://localhost:8069")
        self.db = os.environ.get("ODOO_DB", "odoo")
        self.user = os.environ.get("ODOO_ADMIN_USER", "admin")
        self.password = os.environ.get("ODOO_ADMIN_PASS", "admin")
        self._uid = None
        self._models = None

    def _connect(self):
        common = xmlrpc_client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        uid = common.authenticate(self.db, self.user, self.password, {})
        if not uid:
            raise RuntimeError("Odoo authentication failed")
        self._uid = uid
        self._models = xmlrpc_client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    @property
    def uid(self):
        if self._uid is None:
            self._connect()
        return self._uid

    @property
    def models(self):
        if self._models is None:
            self._connect()
        return self._models

    def create(self, model, vals):
        return self.models.execute_kw(self.db, self.uid, self.password, model, "create", [vals])

    def search(self, model, domain, limit=0):
        return self.models.execute_kw(self.db, self.uid, self.password, model, "search", [domain], {"limit": limit})

    def ensure(self, model, domain, vals):
        ids = self.search(model, domain, limit=1)
        if ids:
            return ids[0]
        return self.create(model, vals)

    def _get_xmlid_record(self, xmlid):
        module, name = xmlid.split(".", 1)
        data = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            "ir.model.data",
            "search_read",
            [[("module", "=", module), ("name", "=", name)]],
            {"fields": ["res_id", "model"], "limit": 1},
        )
        if not data:
            raise RuntimeError(f"XMLID not found: {xmlid}")
        return data[0]

    def menu_action(self, xmlid):
        data = self._get_xmlid_record(xmlid)
        if data["model"] != "ir.ui.menu":
            raise RuntimeError(f"XMLID {xmlid} is not a menu (model={data['model']})")
        menu_id = data["res_id"]
        menu = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            "ir.ui.menu",
            "read",
            [[menu_id]],
            {"fields": ["action"]},
        )
        action_id = False
        if menu and menu[0].get("action"):
            action_ref = menu[0]["action"]
            if isinstance(action_ref, str) and "," in action_ref:
                action_id = int(action_ref.split(",")[1])
        return menu_id, action_id

    def ensure_user_in_group(self, login, group_xmlid):
        group = self._get_xmlid_record(group_xmlid)
        if group["model"] != "res.groups":
            raise RuntimeError(f"XMLID {group_xmlid} is not a group (model={group['model']})")
        group_id = group["res_id"]
        users = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            "res.users",
            "search",
            [[("login", "=", login)]],
            {"limit": 1},
        )
        if not users:
            raise RuntimeError(f"User not found: {login}")
        self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            "res.users",
            "write",
            [[users[0]], {"group_ids": [(4, group_id)]}],
        )
