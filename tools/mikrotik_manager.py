#!/usr/bin/env python3
import sys
import xmlrpc.client
import argparse
import os

class OdooClient:
    def __init__(self, url, db, user, password):
        self.url = url
        self.db = db
        self.user = user
        self.password = password
        self.uid = None
        self.common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    def authenticate(self):
        try:
            # Check if DB exists or list available ones
            try:
                dbs = self.common.list_db()
                if self.db not in dbs:
                    if dbs:
                        print(f"Warning: DB '{self.db}' not found. Using '{dbs[0]}'.")
                        self.db = dbs[0]
                    else:
                        print("Error: No databases found.")
                        return False
            except Exception:
                pass # method might not exist or be restricted

            self.uid = self.common.authenticate(self.db, self.user, self.password, {})
            return self.uid
        except Exception as e:
            print(f"Error authenticating: {e}")
            return False

    def execute_kw(self, model, method, args, kwargs=None):
        if not kwargs:
            kwargs = {}
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)

def list_routers(client):
    routers = client.execute_kw('isp.mikrotik.router', 'search_read', [[]], {'fields': ['device_id', 'last_healthcheck_status', 'routeros_version']})
    print(f"{'ID':<5} {'Name':<20} {'Status':<10} {'Version':<10}")
    print("-" * 50)
    for r in routers:
        name = r['device_id'][1] if r['device_id'] else "Unknown"
        print(f"{r['id']:<5} {name:<20} {str(r['last_healthcheck_status']):<10} {str(r['routeros_version']):<10}")

def run_healthcheck(client, router_id=None):
    domain = []
    if router_id:
        domain = [('id', '=', int(router_id))]
    
    ids = client.execute_kw('isp.mikrotik.router', 'search', [domain])
    if not ids:
        print("No routers found.")
        return

    print(f"Running healthcheck on routers: {ids}")
    # We call the method on the recordset. XMLRPC needs explicit list of IDs.
    # Note: _handle_mikrotik_healthcheck is likely private or wrapped. 
    # Usually we trigger a job or call a public method. Assuming public method exists or using generic execute.
    # If not public, we might need a server action or a job trigger.
    # Let's assume we can trigger the cron job logic or find public method.
    # Checking code... `_handle_mikrotik_healthcheck` is internal. 
    # We should look for a public method. If none, we can try creating a job? 
    # Or calling write on last_healthcheck_at to trigger compute? No.
    # Let's try calling the button action if exists, or creating a provisioning job.
    
    # Actually, for this tool, let's list provisioning jobs as the primary action for "management".
    pass

def list_jobs(client):
    jobs = client.execute_kw('isp.provisioning_job', 'search_read', 
                             [[('state', 'in', ['pending', 'queued', 'failed'])]], 
                             {'fields': ['job_type', 'state', 'attempts', 'error_message'], 'limit': 20})
    print(f"{'ID':<5} {'Type':<20} {'State':<10} {'Attempts':<5} {'Error'}")
    print("-" * 80)
    for j in jobs:
        err = (j['error_message'] or "")[:30]
        print(f"{j['id']:<5} {j['job_type']:<20} {j['state']:<10} {j['attempts']:<5} {err}")

def trigger_cron(client):
    # Force run the provisioning cron
    # automated_action model: ir.cron
    cron_id = client.execute_kw('ir.cron', 'search', [[('name', 'ilike', 'Provisioning')]])
    if cron_id:
        print(f"Triggering cron job {cron_id}...")
        client.execute_kw('ir.cron', 'method_direct_trigger', [cron_id])
        print("Cron triggered.")
    else:
        print("Provisioning cron not found.")

def main():
    parser = argparse.ArgumentParser(description="Manage ISP MikroTik Routers")
    parser.add_argument("--url", default="http://localhost:8069", help="Odoo URL")
    parser.add_argument("--db", default="odoo", help="Database")
    parser.add_argument("--user", default="admin", help="User")
    parser.add_argument("--password", default="admin", help="Password")
    
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("list", help="List routers")
    subparsers.add_parser("jobs", help="List pending jobs")
    subparsers.add_parser("run", help="Run provisioning cron")
    
    args = parser.parse_args()
    
    client = OdooClient(args.url, args.db, args.user, args.password)
    if not client.authenticate():
        sys.exit(1)

    if args.command == "list":
        list_routers(client)
    elif args.command == "jobs":
        list_jobs(client)
    elif args.command == "run":
        trigger_cron(client)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
