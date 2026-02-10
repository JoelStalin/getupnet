# -*- coding: utf-8 -*-
import os
import urllib.request


def main():
    base_url = os.environ.get("ODOO_URL", "http://localhost:8069")
    url = base_url.rstrip("/") + "/captive"
    print(f"Request: {url}")
    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode("utf-8")
        print(f"Status: {resp.status}")
        print(body[:200])


if __name__ == "__main__":
    main()
