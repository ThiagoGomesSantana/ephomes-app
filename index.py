
from waitress import serve
from flask import Flask, render_template
from selenium import webdriver
import selenium.webdriver.chrome.service as chrome_service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import time
from base import Conn
from os import path

HOME = path.dirname(path.realpath(__file__))

app = Flask(__name__)

@app.route("/")
def home():
    database=Conn()
    data = get_data_table(database)
    return render_template('index.html', data=data)

@app.route("/start")
def start():
    service = chrome_service.Service('/usr/bin/chromedriver/chromedriver')
    service.start()
    options =  webdriver.ChromeOptions()
    options.binary_location='usr/bin/chrome/chrome'

    #options.add_argument('--disable-dev-shm-usage')
    #options.add_argument('--no-sandbox')

    driver = webdriver.Remote(service.service_url, options=options)

    fetch_redfin(driver)
    database=Conn()
    data = get_data_table(database)
    return render_template('display.html', data=data)

@app.route("/update")
def update():
    return render_template('display.html', data=[])

def fetch_redfin(driver, fresh=True):
    redfin_url = r"https://www.redfin.com/city/30772/OR/Portland/filter/sort=lo-days,max-days-on-market=1d"

    driver.get(redfin_url)
    print('redfin.com accessed')
    WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.XPATH, "//span[@class='modeOptionInnard table']/parent::button"))).click()
    print('table mode activated')
    time.sleep(2)
    database = Conn()
    fetch_table(driver, database, fresh=fresh)

    try:
        pagingControls = driver.find_element(By.XPATH, "//div[@class='PagingControls']")
        paging_buttons = pagingControls.find_elements(By.CLASS_NAME, 'goToPage')
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'banner-close-button'))).click()
            time.sleep(2)
        except:
            pass

        for button in paging_buttons[1:]:
            button.click()
            print('going to next page')
            fetch_table(driver, database)
    except:
        print('single page table, going now to portland')

    connect_portland(driver, database)
    database.close(reset=False)

def fetch_table(driver, database, fresh=False):
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, 'tableList')))
        table = driver.find_element(By.XPATH, "//*[@id='results-display']/div[4]/div/div[3]/table/tbody")
        print(' table found')
        rows = table.find_elements(By.TAG_NAME, 'tr')
        print('     table elements found')
        
        data=[]

        for row in rows:
            address = row.find_element(By.CLASS_NAME, "address").text
            lot_area = row.find_element(By.CLASS_NAME, "col_sqft").text
            price = row.find_element(By.CLASS_NAME, "col_price").text

            icon = row.find_element(By.CLASS_NAME, "property-icon")
            kind = icon.get_attribute('class').split(' ')[1]
            if kind == 'logo-R':
                kind = 'Redfin Home'

            data.append([address, lot_area, price, kind])

        database.insert_redfin(data, fresh=fresh)
        
def connect_portland(driver, database):
    portland_url = r"https://www.portlandmaps.com/" 
    driver.get(portland_url)
    print('portlandmaps.com accessed')
    time.sleep(3)

    # dismiss splash 
    try:
        dismiss_splash = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.ID, 'splash-dismiss')))
        dismiss_splash.click()
        print('splash dismissed')
    except Exception as e:
            print(e)

    address_list = database.get_address()
    print('processing redfin address list')
    for address in address_list:
        portland_get_normal(driver, database, address)

def portland_get_normal(driver, database, address, last_call=False):
    if not last_call:
        address_input = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'search_input')))
        address_input.clear()
        address_input.send_keys(address)
        address_input.send_keys(Keys.RETURN)
        print(f' processing {address}..')
        time.sleep(2)

    try:
        datalist = WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.CLASS_NAME, 'dl-horizontal')))
        print('     property details found')
        owner = datalist.find_element(By.XPATH, "//dt[text()='Owner']//following::dd").text
        zoning = datalist.find_element(By.XPATH, "//a[@detail-type='zoning']/following::dd/a").text.split(' ')[0]
        url = driver.current_url
        if zoning.upper() in ['R2.5', 'R2,5', 'R5', 'R7', 'R10', 'R20']:
            property_type = 'residential'
        else:
            property_type = 'commercial'

        database.insert_portland(address, owner=owner, zoning=zoning, url=url, property_type=property_type)

        print(f'    Updated: {address} - Owner: {owner}, Zoning: {zoning}')

    except Exception as e:
        print(f'    property details not found: {e}')
        database.insert_portland_url(address, driver.current_url)
        print('     updating url of the address')
        try:
            WebDriverWait(driver, 2).until(EC.visibility_of((By.CLASS_NAME, 'ic ic-warning')))
            print('     property outbounds portland, going to next')
        except:
            if not last_call:
                portland_get_listed(driver, database, address)
        
def portland_get_listed(driver, database, address):
    try:
        if address.strip().split(' ')[0].isdigit():
            properties = driver.find_elements(By.XPATH, '//a[@detail-type="property"]')
            print('     looking for address in the list of properties')
            for prop in properties:
                if prop.text.strip().split(' ')[0] == address.strip().split(' ')[0]:
                    prop.click()
                    print('     property found')
                    time.sleep(2)
                    portland_get_normal(driver, database, address, last_call=True)
                    print(      'last call for the current property')
        
    except:
        pass

def get_data(database):
    data = database.get_data()
    return data

def get_data_table(database):
    data = database.get_data_table()
    return data

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)