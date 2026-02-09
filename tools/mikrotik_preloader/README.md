# MikroTik preloader

## Purpose
Auto-onboard MikroTik devices and register them in Odoo.

## Setup
1. Copy config.example.yaml to config.yaml
2. Export secrets:
   - MIKROTIK_MGMT_PASS
   - ODOO_ADMIN_PASS
3. Install deps:
   - pip install -r requirements.txt

## Run
python preloader.py --config config.yaml
