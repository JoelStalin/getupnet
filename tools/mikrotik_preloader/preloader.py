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
