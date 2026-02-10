import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginPage:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def open(self):
        url = f"{self.base_url}/web/login"
        db = os.environ.get("ODOO_DB")
        if db:
            parts = urlparse(url)
            query = dict(parse_qsl(parts.query))
            query["db"] = db
            url = urlunparse(parts._replace(query=urlencode(query)))
        self.driver.get(url)

    def login(self, user, password):
        wait = WebDriverWait(self.driver, 15)
        form = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form.oe_login_form")))
        self.driver.execute_script(
            "arguments[0].classList.remove('d-none'); arguments[0].style.display='block';",
            form,
        )
        wait.until(EC.element_to_be_clickable((By.NAME, "login")))
        self.driver.find_element(By.NAME, "login").send_keys(user)
        self.driver.find_element(By.NAME, "password").send_keys(password)
        self.driver.execute_script("arguments[0].submit();", form)
        wait.until(lambda d: "/web" in d.current_url or "/odoo" in d.current_url)
