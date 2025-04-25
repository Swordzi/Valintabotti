import json
import time
import schedule
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
from selenium.webdriver.common.by import By

def login(driver: webdriver.Firefox):
    driver.get("https://ouka.inschool.fi/")
    with open('tiedot/creds.json', 'r') as json_file:
        data = json.load(json_file)
    email = driver.find_element(By.ID, "login-frontdoor")
    email.send_keys(data["email"])
    password = driver.find_element(By.ID, "password")
    password.send_keys(data["password"])
    driver.find_element(By.CSS_SELECTOR, ".btn").click()

def open_trays(driver: webdriver.Firefox):
    driver.get(driver.current_url + "selection/view?")
    driver.find_element("id", "tray-selection-on-first-click").click()

def select_courses(driver: webdriver.Firefox, tray):
    open_btn = driver.find_element("xpath", tray["name"])
    open_btn.click()
    driver.implicitly_wait(0.25)

    def course_click(element):
        try:
            element.click()
            return True
        except ElementClickInterceptedException:
            return False

    for course in tray["courses"]:
        if not course['name'].strip():
            continue
        print(f"    ilmoittaudutaan kurssille {course['name']:<20}... ", end="")
        try:
            course_elem = driver.find_element("xpath",
                                              f'//li[@class="palkki"]/a[starts-with(normalize-space(),"{course["name"]}")]')
        except NoSuchElementException:
            print(f"kurssia {course['name']} ei löytynyt")
            continue
        classes = [c.strip() for c in course_elem.get_attribute("class").split()]
        if any(cls.startswith("ksuor-") or cls == "disa" for cls in classes):
            print("kurssi suoritettu tai ryhmä lukittu/täynnä")
            continue
        if any(cls.endswith("-on") for cls in classes):
            course["status"] = True
            print("kurssi on jo valittu")
            continue
        if course_click(course_elem):
            try:
                driver.find_element("css selector", ".error-bubble")
                print("epäonnistui")
            except NoSuchElementException:
                print("onnistui")
                course["status"] = True
    open_btn.click()

def load_trays():
    with open('tiedot/kurssit.json', encoding='utf-8') as f:
        raw_trays = json.load(f)["trays"]
    return [
        {
            "name": t["name"],
            "courses": [{"name": c, "status": False} for c in t["courses"]]
        } for t in raw_trays
    ]

def print_trays(trays, only_not_confirmed=False):
    for tray in trays:
        print(tray["name"])
        filtered = [c["name"] for c in tray["courses"] if not only_not_confirmed or not c["status"]]
        print(", ".join(filtered))

def count_confirmed(trays):
    total = sum(len(tray["courses"]) for tray in trays)
    confirmed = sum(c["status"] for tray in trays for c in tray["courses"])
    return total, confirmed

def main(driver, trays):
    start_time = time.perf_counter()
    open_trays(driver)
    while True:
        print("Yritetään valintoja...")
        for tray in trays:
            print(f"\nTarjotin: {tray['name']}")
            select_courses(driver, tray)
        total, confirmed = count_confirmed(trays)
        print(f"\n{confirmed}/{total} kurssia valittua")
        print("Kurssit joita ei saatu valittua: \n")
        print_trays(trays, True)
        if total == confirmed:
            print("kaikki kurssit valittu")
            break
        elapsed = time.perf_counter() - start_time
        print(f"Valinnat suoritettu {elapsed:0.4f} sekuntissa")
        start_time = time.perf_counter()
        driver.refresh()
    return schedule.CancelJob

def loader():
    driver = webdriver.Firefox()
    login(driver)
    print("sisäänkirjautuminen onnistui")
    trays = load_trays()
    print("Tarjotin: ")
    print_trays(trays)
    main(driver, trays)

loader()