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
    try:
        return list(api(path, **{f"?{field}": value}))
    except LibRouterosError as exc:
        if "unknown parameter" not in str(exc):
            raise
        items = list(api(path))
        matched = []
        for item in items:
            if str(item.get(field)) == str(value):
                matched.append(item)
        return matched


def api_exec(api, path: str, **kwargs):
    # librouteros executes commands when the response is consumed.
    return list(api(path, **kwargs))


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
    api_exec(api, "/user/group/add", name=name, policy=policy)


def routeros_ensure_user(api, name: str, password: str, group: str):
    try:
        api_exec(api, "/user/add", name=name, password=password, group=group)
    except LibRouterosError:
        api_exec(api, "/user/set", **{"numbers": name, "password": password, "group": group})


def routeros_ensure_interface_list(api, name: str):
    if routeros_find(api, "/interface/list/print", "name", name):
        return
    api_exec(api, "/interface/list/add", name=name)


def routeros_ensure_interface_list_member(api, list_name: str, interface: str):
    if not routeros_interface_exists(api, interface):
        print(f"Skip discovery interface missing: {interface}")
        return
    existing = routeros_find(api, "/interface/list/member/print", "interface", interface)
    for item in existing:
        if item.get("list") == list_name:
            return
    api_exec(api, "/interface/list/member/add", **{"list": list_name, "interface": interface})


def routeros_ensure_neighbor_discovery(api, interfaces: list[str]):
    if not interfaces:
        return
    list_name = "LAN"
    routeros_ensure_interface_list(api, list_name)
    for iface in interfaces:
        routeros_ensure_interface_list_member(api, list_name, iface)
    try:
        api_exec(api, "/ip/neighbor/discovery-settings/set", **{"discover-interface-list": list_name})
    except LibRouterosError:
        pass
    try:
        api_exec(api, "/tool/mac-server/set", **{"allowed-interface-list": list_name})
    except LibRouterosError:
        pass
    try:
        api_exec(api, "/tool/mac-server/mac-winbox/set", **{"allowed-interface-list": list_name})
    except LibRouterosError:
        pass


def routeros_ensure_firewall_allow(api, port: int, src_ip: str, comment: str):
    existing = routeros_find(api, "/ip/firewall/filter/print", "comment", comment)
    if existing:
        rule_id = existing[0].get(".id") or existing[0].get("id")
        if rule_id:
            try:
                api_exec(api, "/ip/firewall/filter/move", **{"numbers": rule_id, "destination": "0"})
            except LibRouterosError:
                pass
        return
    api_exec(
        api,
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
    try:
        added = routeros_find(api, "/ip/firewall/filter/print", "comment", comment)
        if added:
            rule_id = added[0].get(".id") or added[0].get("id")
            if rule_id:
                api_exec(api, "/ip/firewall/filter/move", **{"numbers": rule_id, "destination": "0"})
    except LibRouterosError:
        pass


def routeros_ensure_firewall_drop(api, port: int, comment: str):
    existing = routeros_find(api, "/ip/firewall/filter/print", "comment", comment)
    if existing:
        return
    api_exec(
        api,
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
    api_exec(api, "/interface/bridge/add", name=name)


def routeros_ensure_bridge_port(api, bridge: str, interface: str):
    if not routeros_interface_exists(api, interface):
        print(f"Skip missing interface: {interface}")
        return
    ports = routeros_find(api, "/interface/bridge/port/print", "interface", interface)
    for p in ports:
        if p.get("bridge") == bridge:
            return
    api_exec(api, "/interface/bridge/port/add", bridge=bridge, interface=interface)


def routeros_ensure_ip_address(api, address: str, interface: str):
    if routeros_find(api, "/ip/address/print", "address", address):
        return
    api_exec(api, "/ip/address/add", address=address, interface=interface)


def routeros_ensure_ip_pool(api, name: str, ranges: str):
    if routeros_find(api, "/ip/pool/print", "name", name):
        api_exec(api, "/ip/pool/set", **{"numbers": name, "ranges": ranges})
        return
    api_exec(api, "/ip/pool/add", name=name, ranges=ranges)


def routeros_ensure_dhcp_server(api, name: str, interface: str, pool: str, lease_time: str):
    if routeros_find(api, "/ip/dhcp-server/print", "name", name):
        server_id = routeros_get_id(api, "/ip/dhcp-server/print", "name", name) or name
        api_exec(api, "/ip/dhcp-server/set", **{"numbers": server_id, "interface": interface, "address-pool": pool, "lease-time": lease_time})
        return
    api_exec(
        api,
        "/ip/dhcp-server/add",
        name=name,
        interface=interface,
        **{"address-pool": pool, "lease-time": lease_time},
    )


def routeros_ensure_dhcp_network(api, address: str, gateway: str, dns_server: str):
    existing_id = routeros_get_id(api, "/ip/dhcp-server/network/print", "address", address)
    if existing_id:
        api_exec(
            api,
            "/ip/dhcp-server/network/set",
            **{"numbers": existing_id, "gateway": gateway, "dns-server": dns_server},
        )
        return
    api_exec(
        api,
        "/ip/dhcp-server/network/add",
        address=address,
        gateway=gateway,
        **{"dns-server": dns_server},
    )


def routeros_ensure_dhcp_client(api, interface: str, comment: str):
    items = routeros_find(api, "/ip/dhcp-client/print", "interface", interface)
    if items:
        return
    api_exec(api, "/ip/dhcp-client/add", interface=interface, disabled="no", **{"add-default-route": "yes", "use-peer-dns": "yes", "comment": comment})


def routeros_ensure_nat_masquerade(api, out_interface: str, comment: str):
    existing = routeros_find(api, "/ip/firewall/nat/print", "comment", comment)
    if existing:
        return
    api_exec(
        api,
        "/ip/firewall/nat/add",
        chain="srcnat",
        **{"out-interface": out_interface, "action": "masquerade", "comment": comment},
    )


def routeros_ensure_dns(api, servers: str):
    api_exec(api, "/ip/dns/set", servers=servers, **{"allow-remote-requests": "yes"})


def routeros_ensure_hotspot_profile(api, name: str, dns_name: str, login_by: str, html_dir: str):
    if routeros_find(api, "/ip/hotspot/profile/print", "name", name):
        profile_id = routeros_get_id(api, "/ip/hotspot/profile/print", "name", name) or name
        api_exec(
            api,
            "/ip/hotspot/profile/set",
            **{"numbers": profile_id, "dns-name": dns_name, "login-by": login_by, "html-directory": html_dir},
        )
        return
    api_exec(
        api,
        "/ip/hotspot/profile/add",
        name=name,
        **{"dns-name": dns_name, "login-by": login_by, "html-directory": html_dir},
    )


def routeros_ensure_hotspot_server(api, name: str, interface: str, pool: str, profile: str):
    if routeros_find(api, "/ip/hotspot/print", "name", name):
        server_id = routeros_get_id(api, "/ip/hotspot/print", "name", name) or name
        api_exec(
            api,
            "/ip/hotspot/set",
            **{"numbers": server_id, "interface": interface, "address-pool": pool, "profile": profile},
        )
        return
    api_exec(
        api,
        "/ip/hotspot/add",
        name=name,
        interface=interface,
        **{"address-pool": pool, "profile": profile},
    )


def routeros_ensure_walled_garden(api, domain: str, comment: str):
    existing = routeros_find(api, "/ip/hotspot/walled-garden/print", "comment", comment)
    if existing:
        return
    api_exec(
        api,
        "/ip/hotspot/walled-garden/add",
        **{"dst-host": domain, "comment": comment},
    )


def routeros_set_dhcp_lease_script(api, dhcp_server: str, script: str, clear_if_empty: bool = False):
    if not script and not clear_if_empty:
        return
    server_id = routeros_get_id(api, "/ip/dhcp-server/print", "name", dhcp_server) or dhcp_server
    api_exec(
        api,
        "/ip/dhcp-server/set",
        **{"numbers": server_id, "lease-script": script or ""},
    )


def routeros_ensure_script(api, name: str, source: str, policy: str = "read,write,test"):
    if not source:
        return
    existing_id = routeros_get_id(api, "/system/script/print", "name", name)
    if existing_id:
        api_exec(api, "/system/script/set", **{"numbers": existing_id, "source": source, "policy": policy})
        return
    api_exec(api, "/system/script/add", name=name, source=source, policy=policy)


def routeros_ensure_scheduler(api, name: str, interval: str, on_event: str, start_time: str = "startup"):
    existing_id = routeros_get_id(api, "/system/scheduler/print", "name", name)
    if existing_id:
        api_exec(
            api,
            "/system/scheduler/set",
            **{"numbers": existing_id, "interval": interval, "on-event": on_event, "start-time": start_time, "disabled": "no"},
        )
        return
    api_exec(
        api,
        "/system/scheduler/add",
        name=name,
        interval=interval,
        **{"on-event": on_event, "start-time": start_time, "disabled": "no"},
    )


def routeros_get_mgmt_interface(api, ip: str):
    try:
        for addr in api("/ip/address/print"):
            addr_value = addr.get("address") or ""
            if addr_value.startswith(f"{ip}/"):
                return addr.get("interface")
    except LibRouterosError:
        return None
    return None


def build_lease_script(cfg: dict):
    webhook = cfg.get("webhook", {})
    if not webhook.get("enabled"):
        return None

    token_env = webhook.get("token_env")
    token = os.environ.get(token_env) if token_env else None
    if not token:
        token = webhook.get("token_value")
    if not token:
        raise RuntimeError("webhook token missing: set webhook.token_env or webhook.token_value")
    url = webhook.get("url") or (cfg["odoo"]["url"].rstrip("/") + "/isp/mac_onboarding")
    sector = webhook.get("sector_code") or cfg.get("sector_code", "")

    script = (
        f":local mac $leaseActMAC; :local ip $leaseActIP; :local bound $leaseBound; "
        f"/tool fetch url=\"{url}?token={token}&mac=$mac&ip=$ip&bound=$bound&sector={sector}\" keep-result=no"
    )
    return script


def build_call_home_script(cfg: dict):
    call_home = cfg.get("call_home", {})
    if not call_home.get("enabled"):
        return None

    token_env = call_home.get("token_env")
    token = os.environ.get(token_env) if token_env else None
    if not token:
        token = call_home.get("token_value")
    if not token:
        raise RuntimeError("call_home token missing: set call_home.token_env or call_home.token_value")
    url = call_home.get("url")
    if not url:
        raise RuntimeError("call_home.url is required when call_home.enabled is true")

    ip_lookup_url = call_home.get("ip_lookup_url", "http://api.ipify.org")
    mac_iface = call_home.get("mac_interface") or ""
    check_cert = "yes" if call_home.get("check_certificate", False) else "no"

    lines = [
        f":local token \"{token}\";",
        f":local url \"{url}\";",
        ":local ident [/system/identity get name];",
        ":local serial \"\";",
        ":do { :set serial [/system/routerboard get serial-number] } on-error={};",
        ":local mac \"\";",
    ]

    if mac_iface:
        lines.append(
            f":do {{ :set mac [/interface get [find name=\"{mac_iface}\"] mac-address] }} on-error={{}};"
        )
    else:
        lines.append(
            ":foreach i in=[/interface/ethernet find] do={ :set mac [/interface/ethernet get $i mac-address]; :break; };"
        )

    lines.extend(
        [
            ":local public \"\";",
            f":do {{ :local r [/tool fetch url=\"{ip_lookup_url}\" as-value output=user]; :set public ($r->\"data\") }} on-error={{}};",
            ":if ($public = \"\") do={ :do { :set public [/ip cloud get public-address] } on-error={}; };",
            ":local full ($url . \"?token=\" . $token . \"&identity=\" . $ident . \"&serial=\" . $serial . \"&mac=\" . $mac . \"&public_ip=\" . $public);",
            f"/tool fetch url=$full keep-result=no check-certificate={check_cert};",
        ]
    )

    return "\n".join(lines)


def routeros_apply_call_home(api, cfg: dict):
    call_home = cfg.get("call_home", {})
    if not call_home.get("enabled"):
        return

    script_name = call_home.get("script_name", "isp_checkin")
    scheduler_name = call_home.get("scheduler_name", script_name)
    interval = call_home.get("interval", "5m")

    script = build_call_home_script(cfg)
    routeros_ensure_script(api, script_name, script)
    routeros_ensure_scheduler(
        api,
        scheduler_name,
        interval,
        on_event=f"/system/script/run name={script_name}",
        start_time="startup",
    )
    try:
        api_exec(api, "/system/script/run", name=script_name)
    except LibRouterosError:
        pass


def print_manual_winbox_instructions(cfg: dict, mgmt_iface: str | None = None):
    rcfg = cfg.get("routeros", {}).get("config", {})
    if not rcfg:
        print("Manual (Winbox): no hay configuración definida en routeros.config.")
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
    dns_server = rcfg.get("dns_server") or (lan_address.split("/")[0] if lan_address else "")
    enable_hotspot = rcfg.get("enable_hotspot")

    print("\nMANUAL (Winbox) - Configuración requerida")
    print("1) WAN (Internet)")
    if wan_iface:
        print(f"   - Interface WAN: {wan_iface}")
        print("   - IP > DHCP Client: añadir en WAN, Add Default Route = yes, Use Peer DNS = yes")
    print("2) Bridge LAN")
    if lan_bridge:
        print(f"   - Bridge: crear {lan_bridge}")
    if lan_ports:
        ports_text = ", ".join(lan_ports)
        if mgmt_iface and mgmt_iface in lan_ports:
            print(f"   - Bridge Ports: añadir {ports_text} (excepto {mgmt_iface} si es gestión)")
        else:
            print(f"   - Bridge Ports: añadir {ports_text}")
    print("3) Dirección IP LAN")
    if lan_address and lan_bridge:
        print(f"   - IP > Addresses: {lan_address} en {lan_bridge}")
    print("4) DHCP Server")
    if dhcp_pool and dhcp_range:
        print(f"   - IP > Pool: {dhcp_pool} = {dhcp_range}")
    if dhcp_server and lan_bridge:
        print(f"   - IP > DHCP Server: {dhcp_server} en {lan_bridge}, pool {dhcp_pool}, lease {dhcp_lease_time}")
    if dhcp_network and dns_server:
        print(f"   - IP > DHCP Server > Networks: {dhcp_network} gw {dns_server} dns {dns_server}")
    print("5) DNS")
    if dns_server:
        print(f"   - IP > DNS: Servers {dns_server}, Allow Remote Requests = yes")
    print("6) NAT")
    if wan_iface:
        print(f"   - IP > Firewall > NAT: srcnat, out-interface {wan_iface}, action masquerade")

    if enable_hotspot:
        hs_profile = rcfg.get("hotspot_profile", "hs-prof")
        hs_server = rcfg.get("hotspot_server", "hs1")
        hs_dns_name = rcfg.get("hotspot_dns_name")
        hs_login_by = rcfg.get("hotspot_login_by", "http-chap")
        hs_html_dir = rcfg.get("hotspot_html_dir", "hotspot")
        hs_wg_domain = rcfg.get("hotspot_walled_garden")
        print("7) Hotspot")
        print(f"   - IP > Hotspot > Profiles: {hs_profile} (dns-name={hs_dns_name}, login-by={hs_login_by}, html={hs_html_dir})")
        print(f"   - IP > Hotspot: {hs_server} en {lan_bridge}, pool {dhcp_pool}, profile {hs_profile}")
        if hs_wg_domain:
            print(f"   - IP > Hotspot > Walled Garden: permitir {hs_wg_domain}")
    else:
        print("7) Hotspot")
        print("   - Deshabilitado (sin portal cautivo).")

    call_home = cfg.get("call_home", {})
    if call_home.get("enabled"):
        print("8) Call-home (script + scheduler)")
        print("   - System > Scripts: crear script 'isp_checkin'")
        print(f"   - Scheduler: ejecutar cada {call_home.get('interval', '5m')}")
        print(f"   - URL destino: {call_home.get('url')}")
        print("   - Token: usar el token definido en call_home (temporal o producción).")

    print("9) API (si se requiere Odoo)")
    api_port = cfg.get("routeros", {}).get("api_port", 8728)
    allow_ips = cfg.get("routeros", {}).get("allowed_mgmt_ips", [])
    if allow_ips:
        print(f"   - IP > Firewall > Filter: permitir TCP {api_port} desde {', '.join(allow_ips)}")
        print(f"   - IP > Firewall > Filter: luego regla DROP TCP {api_port} para el resto")


def routeros_apply_sector_config(api, cfg: dict, mgmt_iface: str | None = None):
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
        print("  - ensure DHCP client on WAN")
        routeros_ensure_dhcp_client(api, wan_iface, "ISP-WAN")

    print("  - ensure LAN bridge and ports")
    routeros_ensure_bridge(api, lan_bridge)
    for port in lan_ports:
        if mgmt_iface and port == mgmt_iface:
            print(f"Skip bridge port {port}: management interface in use")
            continue
        routeros_ensure_bridge_port(api, lan_bridge, port)

    print("  - ensure LAN IP and DHCP")
    routeros_ensure_ip_address(api, lan_address, lan_bridge)
    routeros_ensure_ip_pool(api, dhcp_pool, dhcp_range)
    routeros_ensure_dhcp_server(api, dhcp_server, lan_bridge, dhcp_pool, dhcp_lease_time)
    routeros_ensure_dhcp_network(api, dhcp_network, lan_address.split("/")[0], dns_server or lan_address.split("/")[0])

    if dns_server:
        print("  - ensure DNS")
        routeros_ensure_dns(api, dns_server)

    if rcfg.get("enable_nat", True):
        print("  - ensure NAT masquerade")
        routeros_ensure_nat_masquerade(api, wan_iface, "ISP-NAT")

    if rcfg.get("enable_hotspot"):
        print("  - ensure Hotspot")
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

    print("  - ensure DHCP lease script")
    lease_script = build_lease_script(cfg)
    clear_lease_script = cfg.get("webhook", {}).get("clear_lease_script_on_disable", True)
    routeros_set_dhcp_lease_script(api, dhcp_server, lease_script, clear_if_empty=clear_lease_script)


def routeros_onboard(ip: str, cfg: dict):
    api_port = cfg["routeros"]["api_port"]
    bootstrap_cfg = cfg.get("bootstrap", {})
    boot_user = bootstrap_cfg.get("user") or "admin"
    boot_pass = bootstrap_cfg.get("pass") or ""
    pass_env = bootstrap_cfg.get("pass_env")
    if not boot_pass and pass_env:
        boot_pass = os.environ.get(pass_env, boot_pass)

    mgmt_user = cfg["routeros"]["mgmt_user"]
    mgmt_pass = cfg["routeros"].get("mgmt_pass_value") or ""
    if not mgmt_pass:
        mgmt_pass = get_env_or_fail(cfg["routeros"].get("mgmt_pass_env"))
    allowed_ips = list(cfg["routeros"].get("allowed_mgmt_ips", []))
    allowed_env = cfg["routeros"].get("allowed_mgmt_ips_env")
    if allowed_env:
        extra_raw = os.environ.get(allowed_env, "")
        extra = [ip.strip() for ip in extra_raw.split(",") if ip.strip()]
        allowed_ips.extend(extra)

    api = connect(host=ip, username=boot_user, password=boot_pass, port=api_port)
    print(f"Connected to {ip} via API")

    target_mac = (cfg.get("target_mac") or "").lower()
    if target_mac:
        mac = target_mac.replace("-", ":").lower()
        def _has_mac(entries):
            for entry in entries:
                if (entry.get("mac-address") or "").lower() == mac:
                    return True
            return False
        entries = list(api("/interface/ethernet/print"))
        if not _has_mac(entries):
            entries = list(api("/interface/print"))
        if not _has_mac(entries):
            print(f"Skip {ip}: MAC {target_mac} not found")
            return None

    identity_prefix = cfg["naming"]["identity_prefix"]
    sector = cfg["sector_code"]
    last_octet = ip.split(".")[-1]
    identity = cfg["naming"]["identity_format"].format(
        prefix=identity_prefix, sector=sector, ip_last_octet=last_octet
    )

    print("Step: set identity")
    api_exec(api, "/system/identity/set", name=identity)
    print("Step: ensure API service enabled")
    api_exec(api, "/ip/service/set", **{"numbers": "api", "disabled": "no"})

    print("Step: ensure management group/user")
    routeros_ensure_group(
        api,
        name="odoo_noc_group",
        policy="read,write,api,!local,!telnet,!ssh,!ftp,!reboot,!policy,!password,!sniff,!sensitive",
    )
    routeros_ensure_user(api, name=mgmt_user, password=mgmt_pass, group="odoo_noc_group")

    print("Step: neighbor discovery")
    discovery_interfaces = cfg.get("routeros", {}).get("discovery_interfaces") or []
    if not discovery_interfaces:
        mgmt_iface_guess = routeros_get_mgmt_interface(api, ip)
        if mgmt_iface_guess:
            discovery_interfaces = [mgmt_iface_guess]
    routeros_ensure_neighbor_discovery(api, discovery_interfaces)

    print("Step: firewall allowlist")
    for allow_ip in allowed_ips:
        routeros_ensure_firewall_allow(api, api_port, allow_ip, "ALLOW ODOO/NOC API")

    print("Step: firewall drop others")
    routeros_ensure_firewall_drop(api, api_port, "DROP API OTHERS")

    if cfg.get("routeros", {}).get("apply_sector_config", True):
        print("Step: apply sector config")
        mgmt_iface = routeros_get_mgmt_interface(api, ip)
        try:
            routeros_apply_sector_config(api, cfg, mgmt_iface)
        except Exception as exc:
            print(f"Sector config interrupted, retrying: {exc}")
            api = connect(host=ip, username=mgmt_user, password=mgmt_pass, port=api_port)
            mgmt_iface = routeros_get_mgmt_interface(api, ip)
            try:
                routeros_apply_sector_config(api, cfg, mgmt_iface)
            except Exception as exc2:
                print(f"Sector config failed again: {exc2}")
                print_manual_winbox_instructions(cfg, mgmt_iface)
                raise

    if cfg.get("call_home", {}).get("enabled"):
        print("Step: configure call-home")
        try:
            routeros_apply_call_home(api, cfg)
        except Exception as exc:
            print(f"Call-home config failed: {exc}")
            print_manual_winbox_instructions(cfg, mgmt_iface)
            raise

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


def odoo_fetch_preconfig(cfg: dict):
    odoo_cfg = cfg.get("odoo", {})
    if not odoo_cfg.get("fetch_preconfig"):
        return None

    odoo_url = odoo_cfg["url"]
    db = odoo_cfg["db"]
    user = odoo_cfg["user"]
    pwd = get_env_or_fail(odoo_cfg["pass_env"])
    sector_code = cfg.get("sector_code")

    common = xmlrpc_client.ServerProxy(f"{odoo_url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, pwd, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed.")

    models = xmlrpc_client.ServerProxy(f"{odoo_url}/xmlrpc/2/object")
    try:
        preconfig = models.execute_kw(
            db,
            uid,
            pwd,
            "isp.mikrotik.preconfig",
            "get_preconfig_for_sector",
            [sector_code],
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch preconfig from Odoo: {exc}")
    return preconfig


def _merge_dict(dst: dict, src: dict):
    for key, value in (src or {}).items():
        if value is None:
            continue
        if isinstance(value, dict):
            node = dst.setdefault(key, {})
            _merge_dict(node, value)
        else:
            dst[key] = value


def merge_preconfig(cfg: dict, preconfig: dict):
    if not preconfig:
        return
    if preconfig.get("mgmt_subnet"):
        cfg["mgmt_subnet"] = preconfig.get("mgmt_subnet")
    if preconfig.get("target_mac") is not None:
        cfg["target_mac"] = preconfig.get("target_mac")
    if preconfig.get("bootstrap") is not None:
        cfg.setdefault("bootstrap", {})
        _merge_dict(cfg["bootstrap"], preconfig.get("bootstrap"))
    # RouterOS
    routeros = preconfig.get("routeros") or {}
    if routeros:
        cfg.setdefault("routeros", {})
        _merge_dict(cfg["routeros"], routeros)
        if "config" in routeros:
            cfg["routeros"]["config"] = routeros["config"]

    # Call-home / Webhook / Naming
    if preconfig.get("call_home") is not None:
        cfg.setdefault("call_home", {})
        _merge_dict(cfg["call_home"], preconfig.get("call_home"))
    if preconfig.get("webhook") is not None:
        cfg.setdefault("webhook", {})
        _merge_dict(cfg["webhook"], preconfig.get("webhook"))
    if preconfig.get("naming") is not None:
        cfg.setdefault("naming", {})
        _merge_dict(cfg["naming"], preconfig.get("naming"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    api_port = cfg["routeros"]["api_port"]

    try:
        preconfig = odoo_fetch_preconfig(cfg)
        if preconfig:
            merge_preconfig(cfg, preconfig)
            print("Loaded preconfig from Odoo.")
        else:
            print("No preconfig found in Odoo. Using local config.")
    except Exception as exc:
        print(f"Odoo preconfig fetch failed, using local config: {exc}")

    candidates = list(scan_subnet_for_api(cfg["mgmt_subnet"], api_port))
    print(f"Found candidates: {candidates}")

    register_device = cfg.get("odoo", {}).get("register_device", True)

    for ip in candidates:
        try:
            onboarded = routeros_onboard(ip, cfg)
            if not onboarded:
                continue
            if register_device:
                created = odoo_register_device(cfg, onboarded)
                print(f"Onboarded {ip}: {onboarded['identity']} => Odoo {created}")
            else:
                print(f"Onboarded {ip}: {onboarded['identity']} (Odoo registration skipped)")
        except Exception as e:
            print(f"Failed {ip}: {e}")


if __name__ == "__main__":
    main()
