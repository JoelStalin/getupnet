#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description="Run ISP Selenium Tests")
    parser.add_argument("--url", default="http://localhost:8069", help="Odoo Base URL")
    parser.add_argument("--remote", help="Selenium Remote URL (e.g., http://localhost:4444/wd/hub)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (default usually handled by test)")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Arguments to pass to pytest")
    
    args = parser.parse_args()

    env = os.environ.copy()
    env["ISP_E2E"] = "1"
    env["ODOO_BASE_URL"] = args.url
    
    if args.remote:
        env["SELENIUM_REMOTE_URL"] = args.remote
    
    # Check if inside docker
    if os.path.exists("/.dockerenv"):
        print("Running inside Docker container...")
    else:
        print("Running on Host machine...")

    cmd = [sys.executable, "-m", "pytest", "tests/isp_selenium"] + args.pytest_args
    
    print(f"Executing: {' '.join(cmd)}")
    print(f"Target URL: {args.url}")
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        sys.exit(130)

if __name__ == "__main__":
    main()
