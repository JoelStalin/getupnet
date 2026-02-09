# -*- coding: utf-8 -*-
import argparse
import ipaddress
import os
import socket
import yaml
from xmlrpc import client as xmlrpc_client

from librouteros import connect
from librouteros.exceptions import LibRouterosError


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_env_or_fail(name: str) -> str:
    if not name:
        raise RuntimeError("Missing required env var name")
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def scan_subnet_for_api(subnet: str, port: int, timeout: float = 0.5):
    net = ipaddress.ip_network(subnet, strict=False)
    for ip in net.hosts():
        ip_str = str(ip)
        s = socket.socket()
        s.settimeout(timeout)
        try:
            s.connect((ip_str, port))
            yield ip_str
        except Exception:
            pass
        finally:
            s.close()


def routeros_find(api, path: str, field: str, value: str):
    return list(api(path, **{f"?{field}": value}))


def routeros_interface_exists(api, name: str) -> bool:
    return bool(routeros_find(api, "/interface/print", "name", name))


def routeros_get_id(api, path: str, field: str, value: str):
    items = routeros_find(api, path, field, value)
    if not items:
        return None
    return items[0].get(".id") or items[0].get("id")


def routeros_ensure_group(api, name: str, policy: str):
    if routeros_find(api, "/user/group/print", "name", name):
        return
    api("/user/group/add", name=name, policy=policy)


def routeros_ensure_user(api, name: str, password: str, group: str):
    try:
        api("/user/add", name=name, password=password, group=group)
    except LibRouterosError:
        api("/user/set", **{"numbers": name, "password": password, "group": group})


def routeros_ensure_firewall_allow(api, port: int, src_ip: str, comment: str):
    existing = routeros_find(api, "/ip/firewall/filter/print", "comment", comment)
    if existing:
        return
    api(
        "/ip/firewall/filter/add",
        chain="input",
        **{
            "src-address": src_ip,
            "protocol": "tcp",
            "dst-port": str(port),
            "action": "accept",
            "comment": comment,
        },
    )


def routeros_ensure_firewall_drop(api, port: int, comment: str):
    existing = routeros_find(api, "/ip/firewall/filter/print", "comment", comment)
    if existing:
        return
    api(
        "/ip/firewall/filter/add",
        chain="input",
        protocol="tcp",
        **{
            "dst-port": str(port),
            "action": "drop",
            "comment": comment,
        },
    )


def routeros_ensure_bridge(api, name: str):
    if routeros_find(api, "/interface/bridge/print", "name", name):
        return
    api("/interface/bridge/add", name=name)


def routeros_ensure_bridge_port(api, bridge: str, interface: str):
    if not routeros_interface_exists(api, interface):
        print(f"Skip missing interface: {interface}")
        return
    ports = list(api("/interface/bridge/port/print", **{f"?interface": interface}))
    for p in ports:
        if p.get("bridge") == bridge:
            return
    api("/interface/bridge/port/add", bridge=bridge, interface=interface)


def routeros_ensure_ip_address(api, address: str, interface: str):
    if routeros_find(api, "/ip/address/print", "address", address):
        return
    api("/ip/address/add", address=address, interface=interface)


def routeros_ensure_ip_pool(api, name: str, ranges: str):
    if routeros_find(api, "/ip/pool/print", "name", name):
        api("/ip/pool/set", **{"numbers": name, "ranges": ranges})
        return
    api("/ip/pool/add", name=name, ranges=ranges)


def routeros_ensure_dhcp_server(api, name: str, interface: str, pool: str, lease_time: str):
    if routeros_find(api, "/ip/dhcp-server/print", "name", name):
        server_id = routeros_get_id(api, "/ip/dhcp-server/print", "name", name) or name
        api("/ip/dhcp-server/set", **{"numbers": server_id, "interface": interface, "address-pool": pool, "lease-time": lease_time})
        return
    api(
        "/ip/dhcp-server/add",
        name=name,
        interface=interface,
        **{"address-pool": pool, "lease-time": lease_time},
    )


def routeros_ensure_dhcp_network(api, address: str, gateway: str, dns_server: str):
    existing_id = routeros_get_id(api, "/ip/dhcp-server/network/print", "address", address)
    if existing_id:
        api(
            "/ip/dhcp-server/network/set",
            **{"numbers": existing_id, "gateway": gateway, "dns-server": dns_server},
        )
        return
    api(
        "/ip/dhcp-server/network/add",
        address=address,
        gateway=gateway,
        **{"dns-server": dns_server},
    )


def routeros_ensure_dhcp_client(api, interface: str, comment: str):
    items = list(api("/ip/dhcp-client/print", **{f"?interface": interface}))
    if items:
        return
    api("/ip/dhcp-client/add", interface=interface, disabled="no", **{"add-default-route": "yes", "use-peer-dns": "yes", "comment": comment})


def routeros_ensure_nat_masquerade(api, out_interface: str, comment: str):
    existing = routeros_find(api, "/ip/firewall/nat/print", "comment", comment)
    if existing:
        return
    api(
        "/ip/firewall/nat/add",
        chain="srcnat",
        **{"out-interface": out_interface, "action": "masquerade", "comment": comment},
    )


def routeros_ensure_dns(api, servers: str):
    api("/ip/dns/set", servers=servers, **{"allow-remote-requests": "yes"})


def routeros_ensure_hotspot_profile(api, name: str, dns_name: str, login_by: str, html_dir: str):
    if routeros_find(api, "/ip/hotspot/profile/print", "name", name):
        profile_id = routeros_get_id(api, "/ip/hotspot/profile/print", "name", name) or name
        api(
            "/ip/hotspot/profile/set",
            **{"numbers": profile_id, "dns-name": dns_name, "login-by": login_by, "html-directory": html_dir},
        )
        return
    api(
        "/ip/hotspot/profile/add",
        name=name,
        **{"dns-name": dns_name, "login-by": login_by, "html-directory": html_dir},
    )


def routeros_ensure_hotspot_server(api, name: str, interface: str, pool: str, profile: str):
    if routeros_find(api, "/ip/hotspot/print", "name", name):
        server_id = routeros_get_id(api, "/ip/hotspot/print", "name", name) or name
        api(
            "/ip/hotspot/set",
            **{"numbers": server_id, "interface": interface, "address-pool": pool, "profile": profile},
        )
        return
    api(
        "/ip/hotspot/add",
        name=name,
        interface=interface,
        **{"address-pool": pool, "profile": profile},
    )


def routeros_ensure_walled_garden(api, domain: str, comment: str):
    existing = routeros_find(api, "/ip/hotspot/walled-garden/print", "comment", comment)
    if existing:
        return
    api(
        "/ip/hotspot/walled-garden/add",
        **{"dst-host": domain, "comment": comment},
    )


def routeros_set_dhcp_lease_script(api, dhcp_server: str, script: str):
    if not script:
        return
    server_id = routeros_get_id(api, "/ip/dhcp-server/print", "name", dhcp_server) or dhcp_server
    api(
        "/ip/dhcp-server/set",
        **{"numbers": server_id, "lease-script": script},
    )


def build_lease_script(cfg: dict):
    webhook = cfg.get("webhook", {})
    if not webhook.get("enabled"):
        return None

    token_env = webhook.get("token_env")
    token = get_env_or_fail(token_env)
    url = webhook.get("url") or (cfg["odoo"]["url"].rstrip("/") + "/isp/mac_onboarding")
    sector = webhook.get("sector_code") or cfg.get("sector_code", "")

    script = (
        f":local mac $leaseActMAC; :local ip $leaseActIP; :local bound $leaseBound; "
        f"/tool fetch url=\"{url}?token={token}&mac=$mac&ip=$ip&bound=$bound&sector={sector}\" keep-result=no"
    )
    return script


def routeros_apply_sector_config(api, cfg: dict):
    rcfg = cfg.get("routeros", {}).get("config", {})
    if not rcfg:
        return

    wan_iface = rcfg.get("wan_interface")
    lan_bridge = rcfg.get("lan_bridge")
    lan_ports = rcfg.get("lan_ports", [])
    lan_address = rcfg.get("lan_address")
    dhcp_pool = rcfg.get("dhcp_pool")
    dhcp_range = rcfg.get("dhcp_range")
    dhcp_server = rcfg.get("dhcp_server")
    dhcp_lease_time = rcfg.get("dhcp_lease_time", "1h")
    dhcp_network = rcfg.get("dhcp_network")
    dns_server = rcfg.get("dns_server")

    if not all([wan_iface, lan_bridge, lan_address, dhcp_pool, dhcp_range, dhcp_server, dhcp_network]):
        raise RuntimeError("Missing routeros.config required values")

    if rcfg.get("enable_dhcp_client_wan", True):
        routeros_ensure_dhcp_client(api, wan_iface, "ISP-WAN")

    routeros_ensure_bridge(api, lan_bridge)
    for port in lan_ports:
        routeros_ensure_bridge_port(api, lan_bridge, port)

    routeros_ensure_ip_address(api, lan_address, lan_bridge)
    routeros_ensure_ip_pool(api, dhcp_pool, dhcp_range)
    routeros_ensure_dhcp_server(api, dhcp_server, lan_bridge, dhcp_pool, dhcp_lease_time)
    routeros_ensure_dhcp_network(api, dhcp_network, lan_address.split("/")[0], dns_server or lan_address.split("/")[0])

    if dns_server:
        routeros_ensure_dns(api, dns_server)

    if rcfg.get("enable_nat", True):
        routeros_ensure_nat_masquerade(api, wan_iface, "ISP-NAT")

    if rcfg.get("enable_hotspot"):
        hs_profile = rcfg.get("hotspot_profile", "hs-prof")
        hs_server = rcfg.get("hotspot_server", "hs1")
        hs_dns_name = rcfg.get("hotspot_dns_name")
        hs_login_by = rcfg.get("hotspot_login_by", "http-chap")
        hs_html_dir = rcfg.get("hotspot_html_dir", "hotspot")
        hs_wg_domain = rcfg.get("hotspot_walled_garden")

        if not hs_dns_name:
            raise RuntimeError("hotspot_dns_name is required when enable_hotspot is true")

        routeros_ensure_hotspot_profile(api, hs_profile, hs_dns_name, hs_login_by, hs_html_dir)
        routeros_ensure_hotspot_server(api, hs_server, lan_bridge, dhcp_pool, hs_profile)
        if hs_wg_domain:
            routeros_ensure_walled_garden(api, hs_wg_domain, "ISP-WALLED-GARDEN")

    lease_script = build_lease_script(cfg)
    routeros_set_dhcp_lease_script(api, dhcp_server, lease_script)


def routeros_onboard(ip: str, cfg: dict):
    api_port = cfg["routeros"]["api_port"]
    boot_user = cfg["bootstrap"]["user"]
    boot_pass = cfg["bootstrap"]["pass"]

    mgmt_user = cfg["routeros"]["mgmt_user"]
    mgmt_pass = get_env_or_fail(cfg["routeros"]["mgmt_pass_env"])
    allowed_ips = cfg["routeros"].get("allowed_mgmt_ips", [])

    api = connect(host=ip, username=boot_user, password=boot_pass, port=api_port)

    identity_prefix = cfg["naming"]["identity_prefix"]
    sector = cfg["sector_code"]
    last_octet = ip.split(".")[-1]
    identity = cfg["naming"]["identity_format"].format(
        prefix=identity_prefix, sector=sector, ip_last_octet=last_octet
    )

    api("/system/identity/set", name=identity)
    api("/ip/service/set", **{"numbers": "api", "disabled": "no"})

    routeros_ensure_group(
        api,
        name="odoo_noc_group",
        policy="read,write,api,!local,!telnet,!ssh,!ftp,!reboot,!policy,!password,!sniff,!sensitive",
    )
    routeros_ensure_user(api, name=mgmt_user, password=mgmt_pass, group="odoo_noc_group")

    for allow_ip in allowed_ips:
        routeros_ensure_firewall_allow(api, api_port, allow_ip, "ALLOW ODOO/NOC API")

    routeros_ensure_firewall_drop(api, api_port, "DROP API OTHERS")

    if cfg.get("routeros", {}).get("apply_sector_config", True):
        routeros_apply_sector_config(api, cfg)

    return {"identity": identity, "ip": ip, "api_port": api_port}


def odoo_register_device(cfg: dict, onboarded: dict):
    odoo_url = cfg["odoo"]["url"]
    db = cfg["odoo"]["db"]
    user = cfg["odoo"]["user"]
    pwd = get_env_or_fail(cfg["odoo"]["pass_env"])

    common = xmlrpc_client.ServerProxy(f"{odoo_url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, pwd, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed.")

    models = xmlrpc_client.ServerProxy(f"{odoo_url}/xmlrpc/2/object")

    sector_ids = models.execute_kw(db, uid, pwd, "isp.sector", "search", [[("code", "=", cfg["sector_code"]) ]], {"limit": 1})
    if not sector_ids:
        raise RuntimeError(f"Sector not found: {cfg['sector_code']}")
    sector_id = sector_ids[0]

    device_ids = models.execute_kw(db, uid, pwd, "isp.device", "search", [[("mgmt_ip", "=", onboarded["ip"]), ("device_type", "=", "mikrotik")]], {"limit": 1})
    if device_ids:
        device_id = device_ids[0]
        models.execute_kw(db, uid, pwd, "isp.device", "write", [[device_id], {
            "name": onboarded["identity"],
            "sector_id": sector_id,
            "mgmt_port": onboarded["api_port"],
            "status": "active",
        }])
    else:
        device_id = models.execute_kw(db, uid, pwd, "isp.device", "create", [{
            "name": onboarded["identity"],
            "device_type": "mikrotik",
            "sector_id": sector_id,
            "mgmt_ip": onboarded["ip"],
            "mgmt_port": onboarded["api_port"],
            "status": "active",
        }])

    router_ids = models.execute_kw(db, uid, pwd, "isp.mikrotik.router", "search", [[("device_id", "=", device_id)]], {"limit": 1})
    if router_ids:
        router_id = router_ids[0]
    else:
        router_id = models.execute_kw(db, uid, pwd, "isp.mikrotik.router", "create", [{
            "device_id": device_id,
            "auth_method": "api",
        }])

    return {"device_id": device_id, "router_id": router_id}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    api_port = cfg["routeros"]["api_port"]

    candidates = list(scan_subnet_for_api(cfg["mgmt_subnet"], api_port))
    print(f"Found candidates: {candidates}")

    for ip in candidates:
        try:
            onboarded = routeros_onboard(ip, cfg)
            created = odoo_register_device(cfg, onboarded)
            print(f"Onboarded {ip}: {onboarded['identity']} => Odoo {created}")
        except Exception as e:
            print(f"Failed {ip}: {e}")


if __name__ == "__main__":
    main()
