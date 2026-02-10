# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IspMikrotikPreconfig(models.Model):
    _name = "isp.mikrotik.preconfig"
    _description = "MikroTik Preconfiguration Profile"
    _order = "sequence, id desc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    sector_id = fields.Many2one("isp.sector", ondelete="set null")
    is_default = fields.Boolean(
        default=False,
        help="Si no existe una configuración para el sector, se usa la marcada como default.",
    )

    # Local / preloader settings
    mgmt_subnet = fields.Char(help="Subnet para buscar MikroTik (ej: 192.168.88.0/24).")
    target_mac = fields.Char(help="MAC objetivo para filtrar el router (opcional).")
    bootstrap_user = fields.Char(default="admin")
    bootstrap_pass = fields.Char(password=True)

    # RouterOS management / preloader settings
    api_port = fields.Integer(default=8728)
    routeros_mgmt_user = fields.Char(default="odoo_noc")
    routeros_mgmt_pass_env = fields.Char(default="MIKROTIK_MGMT_PASS")
    routeros_mgmt_pass_value = fields.Char(password=True)
    discovery_interfaces = fields.Char(
        default="ether2,ether3,ether4,wlan1",
        help="Interfaces para descubrimiento/MAC server (comma-separated).",
    )
    allowed_mgmt_ips = fields.Char(
        help="IPs permitidas para API (comma-separated)."
    )
    apply_sector_config = fields.Boolean(default=True)

    # RouterOS config fields
    wan_interface = fields.Char(required=True, default="ether2")
    lan_bridge = fields.Char(required=True, default="br-pon")
    lan_ports = fields.Char(
        default="ether3,ether4,wlan1",
        help="Lista separada por comas. Ej: ether3,ether4,wlan1",
    )
    lan_address = fields.Char(required=True, default="10.10.10.1/24")
    dhcp_pool = fields.Char(required=True, default="pon_pool")
    dhcp_range = fields.Char(required=True, default="10.10.10.100-10.10.10.200")
    dhcp_server = fields.Char(required=True, default="pon_dhcp")
    dhcp_lease_time = fields.Char(default="1h")
    dhcp_network = fields.Char(required=True, default="10.10.10.0/24")
    dns_server = fields.Char(default="10.10.10.1")
    enable_dhcp_client_wan = fields.Boolean(default=True)
    enable_nat = fields.Boolean(default=True)

    enable_hotspot = fields.Boolean(default=False)
    hotspot_profile = fields.Char(default="hs_prof")
    hotspot_server = fields.Char(default="hs1")
    hotspot_dns_name = fields.Char()
    hotspot_walled_garden = fields.Char()
    hotspot_login_by = fields.Char(default="http-pap")
    hotspot_html_dir = fields.Char(default="hotspot")

    # Call-home
    call_home_enabled = fields.Boolean(default=True)
    call_home_url = fields.Char()
    call_home_token_value = fields.Char()
    call_home_interval = fields.Char(default="5m")
    call_home_ip_lookup_url = fields.Char(default="http://api.ipify.org")
    call_home_script_name = fields.Char(default="isp_checkin")
    call_home_scheduler_name = fields.Char(default="isp_checkin")
    call_home_check_certificate = fields.Boolean(default=False)
    call_home_mac_interface = fields.Char(help="Interface usada para MAC en call-home.")

    # Webhook
    webhook_enabled = fields.Boolean(default=False)
    webhook_url = fields.Char()
    webhook_token_value = fields.Char()
    webhook_clear_lease_script_on_disable = fields.Boolean(default=True)

    # Naming
    identity_prefix = fields.Char(default="MT-")
    identity_format = fields.Char(default="{prefix}{sector}-{ip_last_octet}")

    @api.constrains("is_default", "sector_id")
    def _check_default(self):
        for rec in self:
            if rec.is_default and rec.sector_id:
                raise ValidationError(_("El perfil default no debe estar asociado a un sector."))

    def _lan_ports_list(self):
        ports = [p.strip() for p in (self.lan_ports or "").split(",") if p.strip()]
        return ports

    def _parse_csv(self, value):
        return [v.strip() for v in (value or "").split(",") if v.strip()]

    def _parse_csv_or_none(self, value):
        items = self._parse_csv(value)
        return items if items else None

    def to_routeros_config(self):
        self.ensure_one()
        return {
            "wan_interface": self.wan_interface,
            "lan_bridge": self.lan_bridge,
            "lan_ports": self._lan_ports_list(),
            "lan_address": self.lan_address,
            "dhcp_pool": self.dhcp_pool,
            "dhcp_range": self.dhcp_range,
            "dhcp_server": self.dhcp_server,
            "dhcp_lease_time": self.dhcp_lease_time,
            "dhcp_network": self.dhcp_network,
            "dns_server": self.dns_server,
            "enable_dhcp_client_wan": self.enable_dhcp_client_wan,
            "enable_nat": self.enable_nat,
            "enable_hotspot": self.enable_hotspot,
            "hotspot_profile": self.hotspot_profile,
            "hotspot_server": self.hotspot_server,
            "hotspot_dns_name": self.hotspot_dns_name,
            "hotspot_walled_garden": self.hotspot_walled_garden,
            "hotspot_login_by": self.hotspot_login_by,
            "hotspot_html_dir": self.hotspot_html_dir,
        }

    def to_preloader_payload(self):
        self.ensure_one()
        payload = {
            "mgmt_subnet": self.mgmt_subnet or None,
            "target_mac": self.target_mac or None,
            "bootstrap": {
                "user": self.bootstrap_user or None,
                "pass": self.bootstrap_pass or None,
            },
            "routeros": {
                "api_port": self.api_port,
                "mgmt_user": self.routeros_mgmt_user or None,
                "mgmt_pass_env": self.routeros_mgmt_pass_env or None,
                "mgmt_pass_value": self.routeros_mgmt_pass_value or None,
                "discovery_interfaces": self._parse_csv_or_none(self.discovery_interfaces),
                "allowed_mgmt_ips": self._parse_csv_or_none(self.allowed_mgmt_ips),
                "apply_sector_config": self.apply_sector_config,
                "config": self.to_routeros_config(),
            },
            "call_home": {
                "enabled": self.call_home_enabled,
                "url": self.call_home_url or None,
                "token_value": self.call_home_token_value or None,
                "interval": self.call_home_interval or None,
                "ip_lookup_url": self.call_home_ip_lookup_url or None,
                "script_name": self.call_home_script_name or None,
                "scheduler_name": self.call_home_scheduler_name or None,
                "check_certificate": self.call_home_check_certificate,
                "mac_interface": self.call_home_mac_interface or None,
            },
            "webhook": {
                "enabled": self.webhook_enabled,
                "url": self.webhook_url or None,
                "token_value": self.webhook_token_value or None,
                "clear_lease_script_on_disable": self.webhook_clear_lease_script_on_disable,
            },
            "naming": {
                "identity_prefix": self.identity_prefix or None,
                "identity_format": self.identity_format or None,
            },
        }
        return payload

    @api.model
    def get_preconfig_for_sector(self, sector_code):
        sector_id = False
        if sector_code:
            sector = self.env["isp.sector"].sudo().search([("code", "=", sector_code)], limit=1)
            sector_id = sector.id

        domain = [("active", "=", True)]
        record = False
        if sector_id:
            record = self.sudo().search(domain + [("sector_id", "=", sector_id)], limit=1)
        if not record:
            record = self.sudo().search(domain + [("is_default", "=", True)], limit=1)
        if not record:
            return {}
        return record.to_preloader_payload()
