import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from tests.isp_selenium.pages.login_page import LoginPage
from tests.isp_selenium.pages.odoo_ui import OdooUI
from tests.isp_selenium.odoo_rpc import OdooRPC


@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    remote_url = os.environ.get("SELENIUM_REMOTE_URL")
    if remote_url:
        d = webdriver.Remote(command_executor=remote_url, options=options)
    else:
        chrome_bin = os.environ.get("CHROME_BIN")
        if chrome_bin:
            options.binary_location = chrome_bin
        driver_path = os.environ.get("CHROMEDRIVER_PATH") or ChromeDriverManager().install()
        service = Service(driver_path)
        d = webdriver.Chrome(service=service, options=options)
    yield d
    d.quit()


def test_login_admin(driver):
    base_url = os.environ.get("ODOO_BASE_URL", "http://localhost:8069")
    user = os.environ.get("ODOO_ADMIN_USER", "admin")
    password = os.environ.get("ODOO_ADMIN_PASS", "admin")

    page = LoginPage(driver, base_url)
    page.open()
    page.login(user, password)

    assert "/web" in driver.current_url or "/odoo" in driver.current_url


@pytest.mark.skipif(not os.environ.get("ISP_E2E"), reason="Set ISP_E2E=1 to run UI flows")
def test_01_create_sector_and_mikrotik_device(driver):
    base_url = os.environ.get("ODOO_BASE_URL", "http://localhost:8069")
    user = os.environ.get("ODOO_ADMIN_USER", "admin")
    password = os.environ.get("ODOO_ADMIN_PASS", "admin")

    page = LoginPage(driver, base_url)
    page.open()
    page.login(user, password)

    rpc = OdooRPC()
    rpc.ensure_user_in_group(user, "isp_core.group_isp_admin")
    ui = OdooUI(driver, base_url=base_url, rpc=rpc)
    suffix = str(int(time.time()))

    ui.open_menu("isp_core.menu_isp_sector")
    ui.click_create()
    sector_name = f"Selenium Sector {suffix}"
    sector_code = f"SEL-{suffix}"
    ui.set_field("name", sector_name)
    ui.set_field("code", sector_code)
    ui.click_save()

    ui.open_menu("isp_core.menu_isp_device")
    ui.click_create()
    ui.set_field("name", f"MT-{suffix}")
    ui.set_m2o("sector_id", sector_name)
    ui.set_field("mgmt_ip", "192.168.88.250")
    ui.click_save()

    assert ui.get_field_value("name").startswith("MT-")


@pytest.mark.skipif(not os.environ.get("ISP_E2E"), reason="Set ISP_E2E=1 to run UI flows")
def test_02_create_plan_and_subscription_draft(driver):
    base_url = os.environ.get("ODOO_BASE_URL", "http://localhost:8069")
    user = os.environ.get("ODOO_ADMIN_USER", "admin")
    password = os.environ.get("ODOO_ADMIN_PASS", "admin")

    page = LoginPage(driver, base_url)
    page.open()
    page.login(user, password)

    rpc = OdooRPC()
    rpc.ensure_user_in_group(user, "isp_core.group_isp_admin")
    ui = OdooUI(driver, base_url=base_url, rpc=rpc)
    suffix = str(int(time.time()))

    ui.open_menu("isp_core.menu_isp_service_plan")
    ui.click_create()
    plan_name = f"Plan {suffix}"
    ui.set_field("name", plan_name)
    ui.set_field("down_mbps", "20")
    ui.set_field("up_mbps", "5")
    ui.set_field("price", "15")
    ui.click_save()

    sector_id = rpc.ensure(
        "isp.sector",
        [("code", "=", f"SEL-{suffix}")],
        {"name": f"Selenium Sector {suffix}", "code": f"SEL-{suffix}"},
    )
    partner_id = rpc.ensure(
        "res.partner",
        [("email", "=", f"selenium{suffix}@example.com")],
        {"name": f"Selenium Customer {suffix}", "email": f"selenium{suffix}@example.com", "is_isp_customer": True},
    )

    ui.open_menu("isp_core.menu_isp_subscription")
    ui.click_create()
    ui.set_m2o("partner_id", f"Selenium Customer {suffix}")
    ui.set_m2o("plan_id", plan_name)
    ui.set_m2o("sector_id", f"Selenium Sector {suffix}")
    ui.click_save()

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    status = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.o_statusbar_status"))
    )
    assert "Draft" in status.text or "draft" in status.text
