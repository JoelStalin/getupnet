# MikroTik Preloader Guide

## What it does
- Sets RouterOS identity for the sector.
- Creates a management user and firewall allowlist for the API.
- Builds LAN bridge and attaches OLT-facing ports.
- Sets LAN IP + DHCP server.
- Enables NAT to Starlink WAN.
- Configures Hotspot and walled-garden for portal domain.
- Installs DHCP lease-script to notify Odoo when a new MAC appears.

## Required config keys
```
routeros:
  config:
    wan_interface: "ether1"
    lan_bridge: "br-pon"
    lan_ports: ["sfp1", "ether2"]
    lan_address: "10.10.10.1/24"
    dhcp_pool: "pon_pool"
    dhcp_range: "10.10.10.100-10.10.10.200"
    dhcp_server: "pon_dhcp"
    dhcp_network: "10.10.10.0/24"
    enable_hotspot: true
    hotspot_dns_name: "portal.getupsoft.com.do"
    hotspot_walled_garden: "portal.getupsoft.com.do"
```

## Webhook
The DHCP lease-script sends a GET to:
```
/isp/mac_onboarding?token=<TOKEN>&mac=<MAC>&ip=<IP>&bound=<0|1>&sector=<SECTOR_CODE>
```

## Safety
- The script is idempotent.
- If a port does not exist, it skips it.

## SSH tunnel (Option A: run preloader on host)
Use this when MikroTik is reachable only from your local network, but you are running Odoo in Docker
or in a remote server. The tunnel is created on your host machine; the preloader runs on the host
and connects to the MikroTik through the tunnel.

### Linux/macOS
```
ssh -L 8728:<MIKROTIK_LAN_IP>:8728 <user>@<remote_server>
```

### Windows PowerShell
```
ssh -L 8728:<MIKROTIK_LAN_IP>:8728 <user>@<remote_server>
```

Then in `config.yaml` use:
```
mgmt_subnet: "127.0.0.1/32"
routeros:
  api_port: 8728
```

Run preloader on the host:
```
python tools/mikrotik_preloader/preloader.py --config tools/mikrotik_preloader/config.yaml
```
