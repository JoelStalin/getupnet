from selenium.webdriver.common.by import By


class LoginPage:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def open(self):
        self.driver.get(f"{self.base_url}/web/login")

    def login(self, user, password):
        self.driver.find_element(By.NAME, "login").send_keys(user)
        self.driver.find_element(By.NAME, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
