import os
from xmlrpc import client as xmlrpc_client


class OdooRPC:
    def __init__(self):
        self.url = os.environ.get("ODOO_BASE_URL", "http://localhost:8069")
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
