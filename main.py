import json
import time
import schedule
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
from selenium.webdriver.common.by import By

# Start up perf counter
tic = time.perf_counter()


def login(driver: webdriver.Firefox):
    driver.get("https://ouka.inschool.fi/")

    # Hanki kirjautumistiedot
    with open('tiedot/creds.json', 'r') as json_string:
        data = json.load(json_string)
    emaildata = data["email"]
    passworddata = data["password"]

    # Kirjaudu sisään wilmaan automaagisesti
    email = driver.find_element(By.ID, "login-frontdoor")
    email.send_keys(emaildata)
    password = driver.find_element(By.ID, "password")
    password.send_keys(passworddata)
    loginbtn = driver.find_element(By.CSS_SELECTOR, ".btn")
    loginbtn.click()


def open_trays(driver: webdriver.Firefox):
    trays_url = driver.current_url + "selection/view?"
    driver.get(trays_url)
    driver.find_element("id", "tray-selection-on-first-click").click()

def select_courses(driver: webdriver.Firefox, tray):
    open_tray_button = driver.find_element("xpath", f'//a[normalize-space()="{tray["name"]}"]')
    open_tray_button.click()

    def course_click(course_elem):
        try:
            course_elem.click()
            return True
        except ElementClickInterceptedException:
            return False

    driver.implicitly_wait(0.25)

    for course in tray["courses"]:
        if course['name'].isspace() or course['name'] == "":
            continue

        print(f"    ilmoittaudutaan kurssille {course['name']:<20}... ", end="")

        try:
            course_element = driver.find_element("xpath",
                                                 f'//li[@class="palkki"]/a[starts-with(normalize-space(),"{course["name"]}")]')
        except NoSuchElementException:
            print(f"kurssia {course['name']} ei löytynyt")
            continue

        for klass in course_element.get_attribute("class").split():
            clean_klass = klass.strip()

            if klass.strip().startswith("ksuor-") or clean_klass == "disa":
                print("kurssi suoritettu tai ryhmä lukittu/täynnä")
                break
            if clean_klass.endswith("-on"):
                course['status'] = True
                print("kurssi on jo valittu")
                break
        else:
            course_click(course_element)

            try:
                driver.find_element("css selector", ".error-bubble")
                print("epäonnistui")

            except NoSuchElementException:
                print("onnistui")
                course['status'] = True

    open_tray_button.click()


def load_trays():
    trays = []
    with open('tiedot/kurssit.json', encoding='utf-8') as f:
        raw_trays = json.loads(f.read())['trays']
        for raw_tray in raw_trays:
            tray = {
                "name": raw_tray['name'],
                "courses": [
                    {
                        "name": course,
                        "status": False
                    } for course in raw_tray['courses']
                ]
            }

            trays.append(tray)

    return trays


def print_trays(trays, only_not_confirmed=False):
    for tray in trays:
        print(tray['name'])

        courses_to_print = []

        for course in tray['courses']:
            if (only_not_confirmed and not course['status']) or not only_not_confirmed:
                courses_to_print.append(course['name'])

        print(", ".join(courses_to_print))


def count_confirmed(trays):
    courses = 0
    confirmed = 0

    for tray in trays:
        for course in tray['courses']:
            courses += 1
            if course['status']:
                confirmed += 1

    return courses, confirmed


def main(driver, trays):
    open_trays(driver)

    while True:
        print('Yritetään valintoja...')
        for tray in trays:
            print(f"\nTarjotin: {tray['name']}")
            select_courses(driver, tray)

        courses, confirmed = count_confirmed(trays)
        print(f"\n{confirmed}/{courses} kurssia valittua")
        print("Kurssit joita ei saatu valittua: \n")
        print_trays(trays, True)

        if courses == confirmed:
            print("kaikki kurssit valittu")
            break

        toc = time.perf_counter()
        global tic
        print(f"Valinnat suoritettu {toc - tic:0.4f} sekuntissa")
        tic = time.perf_counter()
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
