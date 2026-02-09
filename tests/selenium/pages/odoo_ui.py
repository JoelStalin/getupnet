from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class OdooUI:
    def __init__(self, driver, timeout=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def open_menu(self, xmlid):
        menu = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[data-menu-xmlid='{xmlid}']")))
        menu.click()

    def click_create(self):
        btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.o_list_button_add")))
        btn.click()

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
