import os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class OdooUI:
    def __init__(self, driver, base_url=None, rpc=None, timeout=20):
        self.driver = driver
        self.base_url = base_url or os.environ.get("ODOO_BASE_URL", "http://localhost:8069")
        self.rpc = rpc
        self.wait = WebDriverWait(driver, timeout)

    def open_menu(self, xmlid):
        if self.rpc:
            menu_id, action_id = self.rpc.menu_action(xmlid)
            url = f"{self.base_url}/web#menu_id={menu_id}"
            if action_id:
                url = f"{url}&action={action_id}"
            self.driver.get(url)
            return
        menu = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[data-menu-xmlid='{xmlid}']")))
        menu.click()

    def click_create(self):
        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.o_control_panel")))
        except TimeoutException:
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.o_action_manager, div.o_list_view, div.o_kanban_view, div.o_form_view")
                )
            )
        selectors = [
            (By.CSS_SELECTOR, "button.o_list_button_add"),
            (By.CSS_SELECTOR, "a.o_list_button_add"),
            (By.CSS_SELECTOR, "button.o-kanban-button-new"),
            (By.CSS_SELECTOR, "a.o-kanban-button-new"),
            (By.CSS_SELECTOR, "button.o_kanban_button_new"),
            (By.CSS_SELECTOR, "a.o_kanban_button_new"),
            (By.CSS_SELECTOR, "button.o_form_button_create"),
            (By.CSS_SELECTOR, "button[data-hotkey='c']"),
            (By.CSS_SELECTOR, "a[data-hotkey='c']"),
            (By.XPATH, "//*[self::button or self::a][normalize-space()='Create' or normalize-space()='New']"),
        ]
        short_wait = WebDriverWait(self.driver, 5)
        for locator in selectors:
            try:
                btn = short_wait.until(EC.element_to_be_clickable(locator))
                btn.click()
                return
            except TimeoutException:
                continue
        raise TimeoutException("Create button not found")

    def click_save(self):
        btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.o_form_button_save")))
        btn.click()

    def set_field(self, name, value):
        locator = (By.XPATH, f"//div[contains(@class,'o_field_widget')][@name='{name}']//input")
        field = self.wait.until(EC.element_to_be_clickable(locator))
        field.clear()
        field.send_keys(value)

    def set_m2o(self, name, value):
        locator = (By.XPATH, f"//div[contains(@class,'o_field_widget')][@name='{name}']//input")
        field = self.wait.until(EC.element_to_be_clickable(locator))
        field.clear()
        field.send_keys(value)
        field.send_keys(Keys.ENTER)

    def get_field_value(self, name):
        locator = (By.XPATH, f"//div[contains(@class,'o_field_widget')][@name='{name}']//input")
        field = self.wait.until(EC.presence_of_element_located(locator))
        return field.get_attribute("value")
