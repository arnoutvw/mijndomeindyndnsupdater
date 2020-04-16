import sys
from time import sleep
from typing import List

from requests import get
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

import configparser
import argparse

parser = argparse.ArgumentParser(description='Update mijndomein DNS records')
parser.add_argument('--config', type=str, help='The path to the config file', default="config.ini")

args = parser.parse_args()
config = configparser.ConfigParser()
config.read(args.config)

usernameValue = config['mijndomein']['username']
passwordValue = config['mijndomein']['password']
domainValue = config['mijndomein']['domain']
mainDomain = domainValue
subdomainValue = ''
domain_value_split = domainValue.split(".")
if len(domain_value_split) > 1:
    subdomainValue = domain_value_split[0]
    mainDomain = domain_value_split[1] + "." + domain_value_split[2]

opts = Options()
opts.headless = False
browser = Firefox(options=opts)

ip = get('https://api.ipify.org').text
print('My public IP address is:', ip)

browser.get('https://auth.mijndomein.nl/login')
username = browser.find_element_by_css_selector("body > div > div > div > div > div:nth-child(3) > form > div:nth-child(3) > input")
password = browser.find_element_by_css_selector("body > div > div > div > div > div:nth-child(3) > form > div:nth-child(4) > input")
username.send_keys(usernameValue)
password.send_keys(passwordValue)
submit = browser.find_element_by_css_selector("body > div > div > div > div > div:nth-child(3) > form > div:nth-child(5) > button")
submit.click()

WebDriverWait(browser, 30).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "#my-packages > div.panel > ul > li > a > span.align-middle.ng-binding")))

products: List[WebElement] = browser.find_elements_by_class_name("product-list-item")

productid = None
for product in products:
    for spans in product.find_elements_by_tag_name("span"):
        if spans.text == mainDomain:
            beherenLink = product.find_element_by_link_text("beheren")
            # /pakketten/{id}/producten/dmp/instellingen
            link = beherenLink.get_attribute("href")
            productid = link.split("/")[4]

if productid is None:
    sys.exit("Product is not found on page.")

browser.get('https://mijnaccount.mijndomein.nl/portaal/dns-instellingen?packageId=' + productid)

iframe = WebDriverWait(browser, 30).until(expected_conditions.presence_of_element_located((By.ID, "portal-frame")))
browser.switch_to.frame(iframe)

WebDriverWait(browser, 30).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "Form_Table_Cell_title")))

rows: List[WebElement] = browser.find_elements_by_xpath("//tr[contains(@class, 'row_')]")

changed = False
for row in rows:
    columns: List[WebElement] = row.find_elements_by_tag_name("td")
    typerecord = columns[1]
    subdomainrecord = columns[2]
    if (typerecord.text == "A") and \
            (subdomainrecord.text == subdomainValue):
        editRecord = columns[9]
        editRecord.find_element_by_class_name("ICON3_edit").click()

        ipInputField = columns[4].find_element_by_tag_name("input")
        ipCurrentValue = ipInputField.get_attribute("value")
        if ipCurrentValue != ip:
            ipInputField.clear()
            ipInputField.send_keys(ip)

            editRecord.find_element_by_class_name("ICON3_diskette").click()
            changed = True
            break
# endfor

if changed:
    browser.find_element_by_tag_name("form").submit()
    sleep(30)

browser.close()