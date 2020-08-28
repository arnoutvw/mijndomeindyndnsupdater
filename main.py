import sys
from time import sleep
from typing import List

from requests import get
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver import Firefox, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

import argparse
import confuse
import logging

def get_product_id(maindomain):
    productid_domain = None

    products: List[WebElement] = browser.find_elements_by_class_name("product-list-item")

    for product in products:
        for spans in product.find_elements_by_tag_name("span"):
            if spans.text == maindomain:
                beheren_link = product.find_element_by_link_text("beheren")
                # /pakketten/{id}/producten/dmp/instellingen
                link = beheren_link.get_attribute("href")
                productid_domain = link.split("/")[4]
    return productid_domain

parser = argparse.ArgumentParser(description='Update mijndomein DNS records')
parser.add_argument('--config', type=str, help='The path to the config file', default="config.yml")

args = parser.parse_args()
config = confuse.load_yaml(args.config)

usernameValue = config['mijndomein']['username']
passwordValue = config['mijndomein']['password']

opts = Options()
opts.headless = True
browser = Firefox(options=opts)
browser.maximize_window()

ip = get('https://api.ipify.org').text
print('My public IP address is:', ip)

try:
    browser.get('https://auth.mijndomein.nl/login')
    username = browser.find_element_by_css_selector("body > div > div > div > div > div:nth-child(3) > form > div:nth-child(3) > input")
    password = browser.find_element_by_css_selector("body > div > div > div > div > div:nth-child(3) > form > div:nth-child(4) > input")
    username.send_keys(usernameValue)
    password.send_keys(passwordValue)
    submit = browser.find_element_by_css_selector("body > div > div > div > div > div:nth-child(3) > form > div:nth-child(5) > button")
    submit.click()

    WebDriverWait(browser, 30).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "#my-packages > div.panel > ul > li > a > span.align-middle.ng-binding")))

    for domainConfig in config['domains']:
        mainDomain = domainConfig['domeinnaam']
        print("Running main domain: ", mainDomain.strip())
        productid = get_product_id(mainDomain)

        if productid is None:
            sys.exit("Product is not found on page.")

        changed = False
        browser.get('https://mijnaccount.mijndomein.nl/portaal/dns-instellingen?packageId=' + productid)

        iframe = WebDriverWait(browser, 30).until(
            expected_conditions.presence_of_element_located((By.ID, "portal-frame")))
        browser.switch_to.frame(iframe)

        WebDriverWait(browser, 30).until(
            expected_conditions.presence_of_element_located((By.CLASS_NAME, "Form_Table_Cell_title")))

        for subdomain in domainConfig['subdomeins']:
            print("Running for subdomain: " + subdomain)
            subdomainDivElements: List[WebElement] = browser.find_elements_by_xpath("//div[.='" + subdomain + "']")

            for subdomainDivElement in subdomainDivElements:
                trElement: WebElement = subdomainDivElement.find_element_by_xpath("../..")
                columns: List[WebElement] = trElement.find_elements_by_tag_name("td")
                typerecord = columns[1]
                browser.execute_script("arguments[0].scrollIntoView(true);", typerecord)
                sleep(0.5)
                if typerecord.text == "A":
                    editRecord = columns[9]
                    editRecord.find_element_by_class_name("ICON3_edit").click()

                    sleep(5)
                    ipInputField = columns[4].find_element_by_tag_name("input")
                    ipCurrentValue = ipInputField.get_attribute("value")
                    if ipCurrentValue != ip:
                        ipInputField.clear()
                        ipInputField.send_keys(ip)

                        editRecord.find_element_by_class_name("ICON3_diskette").click()
                        changed = True
                    else:
                        columns[8].find_element_by_class_name("ICON3_undo").click()
        #endfor

        if changed:
            browser.find_element_by_tag_name("form").submit()
            sleep(30)

        browser.switch_to.parent_frame()
        browser.get("https://mijnaccount.mijndomein.nl/pakketten")
        WebDriverWait(browser, 30).until(expected_conditions.presence_of_element_located(
            (By.CSS_SELECTOR, "#my-packages > div.panel > ul > li > a > span.align-middle.ng-binding")))
    #endfor
except Exception:
    logging.exception("Fatal error in main loop", exc_info=True)
finally:
    browser.close()