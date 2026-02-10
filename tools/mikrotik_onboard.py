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
    
    try:
        api = connect(username=ROUTER_USER, password=ROUTER_PASS, host=ROUTER_IP)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("Connected successfully.")

    # 1. Validate OLT Stick on ether3
    print(f"\n--- Checking OLT Stick on {OLT_INTERFACE} ---")
    try:
        interfaces = api(cmd='/interface/print', where={'name': OLT_INTERFACE})
        if not interfaces:
            print(f"Error: Interface {OLT_INTERFACE} not found.")
        else:
            iface = interfaces[0]
            print(f"Interface Status: {'RUNNING' if iface.get('running') else 'DOWN'}")
            print(f"Type: {iface.get('type')}")
            
            # Check SFP Monitor if possible (might fail if not SFP)
            try:
                monitor = api(cmd='/interface/ethernet/monitor', numbers=OLT_INTERFACE, once=True)
                for item in monitor:
                    if 'sfp-module-present' in item:
                         print(f"SFP Module Present: {item['sfp-module-present']}")
            except Exception as e:
                print(f"Could not monitor SFP: {e}")

    except Exception as e:
        print(f"Error checking OLT: {e}")

    # 2. Setup Hotspot on ether2
    print(f"\n--- Configuring Hotspot on {LAN_INTERFACE} ---")
    
    # Check if IP exists on ether2, if not adding one
    # Note: Creating a hotspot usually requires an IP on the interface
    try:
        ips = api(cmd='/ip/address/print', where={'interface': LAN_INTERFACE})
        if not ips:
            print(f"Adding IP 10.5.50.1/24 to {LAN_INTERFACE}...")
            api(cmd='/ip/address/add', address='10.5.50.1/24', interface=LAN_INTERFACE)
        else:
            print(f"IP Configuration exists on {LAN_INTERFACE}: {ips[0].get('address')}")
            
        # Create Hotspot Setup
        # Providing a simpler way: Just add Hotspot Server, User Profile, User
        
        # Ensure Pool
        has_pool = api(cmd='/ip/pool/print', where={'name': 'hs-pool-1'})
        if not has_pool:
            api(cmd='/ip/pool/add', name='hs-pool-1', ranges='10.5.50.10-10.5.50.254')
            
        # Ensure Profile
        has_hsprof = api(cmd='/ip/hotspot/profile/print', where={'name': 'hsprof1'})
        if not has_hsprof:
            api(cmd='/ip/hotspot/profile/add', name='hsprof1', hotspot_address='10.5.50.1', dns_name='hotspot.getupnet.local', html_directory='hotspot')

        # Ensure Server
        has_server = api(cmd='/ip/hotspot/print', where={'interface': LAN_INTERFACE})
        if not has_server:
            api(cmd='/ip/hotspot/add', name='hs-server1', interface=LAN_INTERFACE, address_pool='hs-pool-1', profile='hsprof1')
            print("Hotspot Server created.")
        else:
            print("Hotspot Server already exists.")

        # 3. Create Hotspot User
        print(f"\n--- Creating User {HOTSPOT_USER} ---")
        users = api(cmd='/ip/hotspot/user/print', where={'name': HOTSPOT_USER})
        if users:
            print("User already exists. Updating password...")
            api(cmd='/ip/hotspot/user/set', **{'.id': users[0]['.id'], 'password': HOTSPOT_PASS})
        else:
            api(cmd='/ip/hotspot/user/add', name=HOTSPOT_USER, password=HOTSPOT_PASS, profile='default')
            print("User created.")

    except Exception as e:
        print(f"Error configuring Hotspot: {e}")
        
    print("\n--- MikroTik Onboarding Completed ---")

if __name__ == "__main__":
    main()
