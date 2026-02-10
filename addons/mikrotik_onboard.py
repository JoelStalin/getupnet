import sys
import os
import time
import ssl
# Use librouteros from the environment (installed in Docker)
try:
    from librouteros import connect
except ImportError:
    print("Error: librouteros not found. Run this inside the Odoo container.")
    sys.exit(1)

def main():
    # Configuration
    ROUTER_IP = os.environ.get('ROUTER_IP', '192.168.88.1') # Default MikroTik IP
    ROUTER_USER = os.environ.get('ROUTER_USER', 'admin')
    ROUTER_PASS = os.environ.get('ROUTER_PASS', '')
    
    HOTSPOT_USER = "admin@getupsoft.com"
    HOTSPOT_PASS = "Admin1234"
    
    LAN_INTERFACE = "ether2"
    OLT_INTERFACE = "ether3"
    
    print(f"Connecting to MikroTik at {ROUTER_IP}...")
    
    creds = [
        ('admin', 'getupsoft'),
        ('admin', 'Getupsoft'),
    ]
    
    ports = [8728]
    
    api = None
    for user, password in creds:
        for port in ports:
            try:
                print(f"Trying {user}:{password} on port {port}...", end=" ")
                if port == 8729:
                    # ssl context if needed
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    api = connect(username=user, password=password, host=ROUTER_IP, port=port, ssl_wrapper=ctx)
                else:
                    api = connect(username=user, password=password, host=ROUTER_IP, port=port)
                
                print("SUCCESS!")
                break
            except Exception as e:
                print(f"Failed: {e}")
        if api:
            break
            
    if not api:
        print("Could not connect with any credential/port combination.")
        return

    print("Connected successfully.")

    # 1. Validate OLT Stick on ether3
    print(f"\n--- Checking OLT Stick on {OLT_INTERFACE} ---")
    try:
        # Fetch all interfaces and filter manually
        all_ifaces = list(api(cmd='/interface/print'))
        interfaces = [i for i in all_ifaces if i.get('name') == OLT_INTERFACE]
        
        if not interfaces:
            print(f"Error: Interface {OLT_INTERFACE} not found.")
        else:
            iface = interfaces[0]
            print(f"Interface Status: {'RUNNING' if iface.get('running') else 'DOWN'}")
            print(f"Type: {iface.get('type')}")
            
            # Check SFP Monitor
            try:
                # 'monitor' command might need interface ID or name as argument or .id
                # Providing 'numbers' argument as passed might work if library supports it
                # Converting generator to list immediately
                monitor = list(api(cmd='/interface/ethernet/monitor', numbers=OLT_INTERFACE, once=True))
                for item in monitor:
                    if 'sfp-module-present' in item:
                         print(f"SFP Module Present: {item['sfp-module-present']}")
            except Exception as e:
                print(f"Could not monitor SFP: {e}")

    except Exception as e:
        print(f"Error checking OLT: {e}")

    # 2. Setup Hotspot on ether2
    print(f"\n--- Configuring Hotspot on {LAN_INTERFACE} ---")
    
    try:
        # Check IP
        all_ips = list(api(cmd='/ip/address/print'))
        ips = [i for i in all_ips if i.get('interface') == LAN_INTERFACE]
        
        if not ips:
            print(f"Adding IP 10.5.50.1/24 to {LAN_INTERFACE}...")
            api(cmd='/ip/address/add', address='10.5.50.1/24', interface=LAN_INTERFACE)
        else:
            print(f"IP Configuration exists on {LAN_INTERFACE}: {ips[0].get('address')}")
            
        # Ensure Pool
        all_pools = list(api(cmd='/ip/pool/print'))
        has_pool = any(p.get('name') == 'hs-pool-1' for p in all_pools)
        if not has_pool:
            api(cmd='/ip/pool/add', name='hs-pool-1', ranges='10.5.50.10-10.5.50.254')
            
        # Ensure Profile
        all_profiles = list(api(cmd='/ip/hotspot/profile/print'))
        has_hsprof = any(p.get('name') == 'hsprof1' for p in all_profiles)
        if not has_hsprof:
            api(cmd='/ip/hotspot/profile/add', name='hsprof1', hotspot_address='10.5.50.1', dns_name='hotspot.getupnet.local', html_directory='hotspot')

        # Ensure Server
        all_servers = list(api(cmd='/ip/hotspot/print'))
        has_server = any(s.get('interface') == LAN_INTERFACE for s in all_servers)
        
        if not has_server:
            api(cmd='/ip/hotspot/add', name='hs-server1', interface=LAN_INTERFACE, address_pool='hs-pool-1', profile='hsprof1')
            print("Hotspot Server created.")
        else:
            print("Hotspot Server already exists.")

        # 3. Create Hotspot User
        print(f"\n--- Creating User {HOTSPOT_USER} ---")
        all_users = list(api(cmd='/ip/hotspot/user/print'))
        existing_user = next((u for u in all_users if u.get('name') == HOTSPOT_USER), None)
        
        if existing_user:
            print("User already exists. Updating password...")
            # Updating requires .id which is usually returned in print
            api(cmd='/ip/hotspot/user/set', **{'.id': existing_user['.id'], 'password': HOTSPOT_PASS})
        else:
            api(cmd='/ip/hotspot/user/add', name=HOTSPOT_USER, password=HOTSPOT_PASS, profile='default')
            print("User created.")

    except Exception as e:
        print(f"Error configuring Hotspot: {e}")
        
    print("\n--- MikroTik Onboarding Completed ---")

if __name__ == "__main__":
    main()
