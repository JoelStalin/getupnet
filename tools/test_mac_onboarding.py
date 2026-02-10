# -*- coding: utf-8 -*-
import os
import random
import urllib.parse
import urllib.request


def random_mac():
    return "02:%02x:%02x:%02x:%02x:%02x" % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
    )


def main():
    base_url = os.environ.get("ODOO_URL", "http://localhost:8069")
    token = os.environ.get("ISP_MAC_TOKEN")
    if not token:
        raise SystemExit("Missing ISP_MAC_TOKEN env var")

    mac = os.environ.get("TEST_MAC", random_mac())
    ip = os.environ.get("TEST_IP", "10.10.10.200")
    sector = os.environ.get("SECTOR_CODE", "SEC-001-los_cacaos")

    params = {
        "token": token,
        "mac": mac,
        "ip": ip,
        "bound": "1",
        "sector": sector,
    }
    url = base_url.rstrip("/") + "/isp/mac_onboarding?" + urllib.parse.urlencode(params)
    print(f"Request: {url}")

    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode("utf-8")
        print(f"Status: {resp.status}")
        print(f"Body: {body}")


if __name__ == "__main__":
    main()
