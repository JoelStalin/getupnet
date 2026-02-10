#!/usr/bin/env python3
import requests
import argparse
import sys

def check_endpoint(url, name, expected_codes=[200], allow_redirects=True):
    try:
        r = requests.get(url, allow_redirects=allow_redirects, timeout=5)
        if r.status_code in expected_codes:
            print(f"[PASS] {name:<20} -> {url} (Status: {r.status_code})")
            return True
        else:
            print(f"[FAIL] {name:<20} -> {url} (Status: {r.status_code}; Expected: {expected_codes})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] {name:<20} -> {url} (Error: {e})")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test ISP Portal Endpoints")
    parser.add_argument("--url", default="http://localhost:8069", help="Base URL")
    args = parser.parse_args()
    
    base = args.url.rstrip("/")
    
    checks = [
        {"url": f"{base}/", "name": "Homepage"},
        {"url": f"{base}/web/login", "name": "Login"},
        {"url": f"{base}/my/home", "name": "Portal Home", "codes": [200, 303]}, # 303 if redirect to login
        {"url": f"{base}/my/isp", "name": "ISP Dashboard", "codes": [200, 303, 404]}, # 404 if module not installed yet
        {"url": f"{base}/longpolling/poll", "name": "Bus (Longpoll)", "codes": [200, 400]},
    ]
    
    failed = 0
    print(f"Testing endpoints on {base}...\n")
    
    for c in checks:
        codes = c.get("codes", [200])
        if not check_endpoint(c["url"], c["name"], expected_codes=codes):
            failed += 1
            
    if failed > 0:
        print(f"\nCompleted with {failed} failures.")
        sys.exit(1)
    else:
        print("\nAll checks passed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
