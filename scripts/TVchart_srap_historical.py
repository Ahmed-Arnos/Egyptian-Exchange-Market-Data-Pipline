from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import requests
import pandas as pd
from datetime import datetime
import json
import os
import boto3
def show_marker(driver, element, x, y):
    driver.execute_script("""
        let marker = document.getElementById('selenium-mouse-marker');
        if (!marker) {
            marker = document.createElement('div');
            marker.id = 'selenium-mouse-marker';
            marker.style.position = 'absolute';
            marker.style.width = '10px';
            marker.style.height = '10px';
            marker.style.borderRadius = '50%';
            marker.style.background = 'red';
            marker.style.zIndex = '999999';
            document.body.appendChild(marker);
        }
        const rect = arguments[0].getBoundingClientRect();
        marker.style.left = (rect.left + arguments[1]) + 'px';
        marker.style.top  = (rect.top + arguments[2]) + 'px';
    """, element, x, y)



df = pd.read_csv("icons2.csv")
thief = webdriver.Chrome()
url = f'https://www.tradingview.com/chart/?symbol=EGX%3AAALR'
thief.get(url)
thief.maximize_window()
try:
    close_btn = WebDriverWait(thief, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH,'/html/body/div[7]/div[2]/div[2]/div/div/div/div[2]')
        )
    )
    close_btn.click()
    print("year selected.")
except:
    print("coulndt close popup.")

try:
    close_btn1 = WebDriverWait(thief, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH,'/html/body/div[2]/div/div[5]/div[2]/div/div[2]/div/div/button[7]')
        )
    )
    close_btn1.click()
    print("year selected.")
except:
    print("coulndt select year.")
time.sleep(1)
try:
    close_btn2 = WebDriverWait(thief, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH,'/html/body/div[2]/div/div[6]/div/div[1]/div/div/div/div/button[3]')
        )
    )
    close_btn2.click()
    print("widget selected.")
except:
    print("coulndt select widget.")
time.sleep(1)
try:
    close_btn3 = WebDriverWait(thief, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH,'/html/body/div[2]/div/div[6]/div/div[2]/div[1]/div[3]/div/div[1]/div/div/div/button[2]')
        )
    )
    close_btn3.click()
    print("widget selected.")
except:
    print("coulndt select widget.")

mouseMove = ActionChains(thief)

for tk in df['symbol']:
    url = f'https://www.tradingview.com/chart/?symbol=EGX%3A{tk}'
    thief.get(url)
    try:
        close_btn1 = WebDriverWait(thief, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH,'/html/body/div[2]/div/div[5]/div[2]/div/div[2]/div/div/button[7]')
            )
        )
        close_btn1.click()
        print("year selected.")
    except:
        print("coulndt select year.")
    time.sleep(1)
    
    chart = WebDriverWait(thief,1).until(
    EC.presence_of_element_located(
        (By.XPATH, "/html/body/div[2]/div/div[5]/div[1]/div[1]/div/div[2]/div[1]/div[2]/div/canvas[1]")
    )
    )
   
    size = chart.size
    width = size['width']
    height = size['height']
    y_offset = height // 2
    mouseMove.move_to_element(chart).perform()
    mouseMove.move_by_offset(-width/2,0).perform()
    # Step horizontally every 10 pixels (adjust as needed)
    data = []
    
    for x_offset in range(0, width,4 ):
       
       date = thief.find_element(By.XPATH,'/html/body/div[2]/div/div[6]/div/div[2]/div[1]/div[3]/div/div[2]/div/div[2]/div/div[1]/div/div/div[2]')
       values = thief.find_elements(By.XPATH,"/html/body/div[2]/div/div[6]/div/div[2]/div[1]/div[3]/div/div[2]/div/div[2]/div/div[3]/div[2]/div/div[2]" )
       values.insert(0,date)
       row =  [el.text for el in values]       
       data.append(row)       
       mouseMove.move_by_offset(4,0).perform()
    
    history = pd.DataFrame(data,columns=["Date","Open","High","Low","close","Change","Volume","Last Day"])
    history.to_csv(f'./TradingView_historical/{tk}.csv',index=False)
       
        # show_marker(thief, chart, x_offset, y_offset)
        # time.sleep(0.2)  # wait for tooltip to update




