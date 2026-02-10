import sys
import os
import xmlrpc.client
import ssl

# Use librouteros from the environment
try:
    from librouteros import connect
except ImportError:
    print("Error: librouteros not found. Run this inside the Odoo container.")
    sys.exit(1)

def main():
    # MikroTik Config
    ROUTER_IP = "192.168.88.1"
    ROUTER_USER = "admin"
    ROUTER_PASS = "getupsoft"
    INTERFACE = "ether3" # OLT Interface

    # Odoo Config
    ODOO_URL = "http://localhost:8069"
    ODOO_DB = "odoo"
    ODOO_USER = "admin"
    ODOO_PASS = "admin"

    print(f"--- Connecting to MikroTik {ROUTER_IP} ---")
    try:
        api = connect(username=ROUTER_USER, password=ROUTER_PASS, host=ROUTER_IP)
    except Exception as e:
        print(f"Failed to connect to MikroTik: {e}")
        sys.exit(1)

    print(f"Scanning interface {INTERFACE}...")
    found_devices = []

    # Monitor Interface first
    try:
         print(f"--- Monitoring {INTERFACE} ---")
         # Fetch all and filter
         all_ifaces = list(api(cmd='/interface/ethernet/print'))
         iface_details = [i for i in all_ifaces if i.get('name') == INTERFACE]
         
         if iface_details:
             detail = iface_details[0]
             print(f"Status: {detail.get('running') and 'RUNNING' or 'DOWN'}")
             print(f"Auto-Negotiation: {detail.get('auto-negotiation')}")
             print(f"Speed: {detail.get('speed')}")
             # Monitor call - 'numbers' usually requires internal ID *or* name depending on version. 
             # Let's try name first, if fails we might need ID.
             # Note: 'monitor' usually returns a generator of dicts.
             try:
                 mon = list(api(cmd='/interface/ethernet/monitor', numbers=INTERFACE, once=True))
                 for m in mon:
                     print(f"Rate: {m.get('rate')}")
                     print(f"Duplex: {m.get('full-duplex') and 'Full' or 'Half'}")
                     if 'sfp-module-present' in m:
                         print(f"SFP Present: {m.get('sfp-module-present')}")
             except Exception as e:
                 print(f"Monitor command failed: {e}")
         else:
             print(f"Interface {INTERFACE} not found in ethernet print.")
    except Exception as e:
        print(f"Monitor Error: {e}")

    # 0. Active Probing for OLT
    try:
        print(f"--- Probing for Zisa OLT on {INTERFACE} ---")
        
        # Ensure IP 192.168.1.2/24 exists
        all_ips = list(api(cmd='/ip/address/print'))
        has_olt_ip = any(ip.get('interface') == INTERFACE and ip.get('address').startswith('192.168.1.') for ip in all_ips)
        
        if not has_olt_ip:
            print(f"Adding 192.168.1.2/24 to {INTERFACE}...")
            api(cmd='/ip/address/add', address='192.168.1.2/24', interface=INTERFACE)
        
        # Probe common Zisa IPs
        targets = ['192.168.1.1', '192.168.1.10']
        
        for target in targets:
            print(f"Pinging {target}...", end=" ")
            ping_res = list(api(cmd='/ping', address=target, count=2, interface=INTERFACE))
            if any(p.get('received') == 1 for p in ping_res):
                print("REACHABLE!")
                found_devices.append({'mac': 'Unknown (OLT)', 'ip': target, 'source': 'Ping Probe'})
            else:
                print("No response.")

        # Check for specific Zisa MAC from user image
        target_mac = "48:E6:63:13:58:45"
        print(f"Checking ARP for {target_mac}...")
        all_arp = list(api(cmd='/ip/arp/print'))
        # Normalize MACs
        arp_entry = next((e for e in all_arp if e.get('mac-address', '').upper() == target_mac), None)
        
        if arp_entry:
             print(f"FOUND OLT by MAC! IP: {arp_entry.get('address')}")
             found_devices.append({'mac': target_mac, 'ip': arp_entry.get('address'), 'source': 'ARP Match'})
        
        # DEBUG: Print all ARP on interface
        print(f"--- All ARP on {INTERFACE} ---")
        interface_arps = [e for e in all_arp if e.get('interface') == INTERFACE]
        for e in interface_arps:
            print(f"MAC: {e.get('mac-address')} IP: {e.get('address')}")

    except Exception as e:
        print(f"Error probing OLT: {e}")

    # 1. Check ARP Table
    try:
        # Fetch full list and filter manually to avoid generator issues
        all_arp = list(api(cmd='/ip/arp/print'))
        arp_entries = [e for e in all_arp if e.get('interface') == INTERFACE]
        
        print(f"Found {len(arp_entries)} ARP entries.")
        for entry in arp_entries:
            mac = entry.get('mac-address')
            ip = entry.get('address')
            if mac:
                found_devices.append({'mac': mac, 'ip': ip, 'source': 'ARP'})
    except Exception as e:
        print(f"Error scanning ARP: {e}")

    # 2. Check DHCP Leases (if any)
    try:
        all_leases = list(api(cmd='/ip/dhcp-server/lease/print'))
        # Filter manually
        # Note: Leases might not have 'interface' directly, usually tied to server -> interface
        # But we can match by MAC if we already found it, or just list all unique MACs
        # For simplicity, let's just grab all active leases and see if they map to our OLT network if known.
        # Since we don't know the OLT subnet, we can't filter easily by interface unless we check the server.
        # Let's skip complex DHCP mapping for now and rely on ARP which is Layer 2 direct.
        pass
    except Exception as e:
        print(f"Error scanning DHCP: {e}")
        
    if not found_devices:
        print("No devices found. Ensure the OLT/ONUs are powered on and generating traffic (ARP).")
        # Try a ping broadcast?
        # api(cmd='/ping', address='255.255.255.255', interface=INTERFACE, count=3)
        return

    # Remove duplicates
    unique_devices = {d['mac']: d for d in found_devices}.values()

    print(f"\n--- Syncing {len(unique_devices)} devices to Odoo ---")
    
    # Odoo Connection
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
        
        if not uid:
            print("Odoo authentication failed.")
            sys.exit(1)

        for dev in unique_devices:
            mac = dev['mac']
            print(f"Processing MAC: {mac} (IP: {dev['ip']})...", end=" ")
            
            # Check if exists
            existing_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'isp.onu', 'search', [[('mac_address', '=', mac)]])
            
            if existing_ids:
                print("Already exists. Skipping.")
                continue
                
            # Create
            vals = {
                'name': f"ONU {mac}", # Placeholder name
                'serial': f"UNK-{mac.replace(':', '')}", # Placeholder serial
                'mac_address': mac,
                'status': 'stock',
                'notes': f"Auto-detected via {dev['source']} on {INTERFACE}",
                'olt_ref': 'Detected on ether3'
            }
            
            new_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'isp.onu', 'create', [vals])
            print(f"Created (ID: {new_id})")

    except Exception as e:
        print(f"Odoo Sync Error: {e}")

if __name__ == "__main__":
    main()
