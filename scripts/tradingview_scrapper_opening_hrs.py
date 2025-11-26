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

while True:

    url = 'https://www.tradingview.com/markets/stocks-egypt/market-movers-all-stocks/'

    snitch = webdriver.Chrome()
    snitch.get(url)

    # Close popup if it exists
    try:
        close_btn = WebDriverWait(snitch, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH,'/html/body/div[7]/div[2]/div[2]/div/div/div/div[2]')
            )
        )
        close_btn.click()
        print("Popup closed.")
    except:
        print("Popup not found OR already closed.")

    time.sleep(2)

    # Click "Load more" button
    while True:
        try:
            # Wait for the "Load more" button to appear
            load_more = WebDriverWait(snitch, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '/html/body/div[2]/main/div/div[2]/div/div[4]/div/div[3]/button')
                )
            )
            load_more.click()
            print("Load more clicked. Waiting for new rows...")
            time.sleep(2)  # wait for new rows to load

        except:
            # No more buttons found → exit loop
            print("No more 'Load more' button found. All rows loaded.")
            break

    try:
        headers = snitch.find_elements(By.XPATH,'/html/body/div[2]/main/div/div[2]/div/div[4]/div/div[2]/div[1]/div/table/thead/tr/th[@data-field]')
        metaData= []
        snitch.execute_script("document.body.style.zoom='50%'")
        time.sleep(1)
        for head in headers:
            metaData.append(head.text.replace("\n", " "))
        time.sleep(1)
        print(metaData)
    
    except:
        print('couldnt fetch metadata')
    try:
        data = []
        rows = snitch.find_elements(By.XPATH,'/html/body/div[2]/main/div/div[2]/div/div[4]/div/div[2]/div[2]/div/div/div/table/tbody/tr')
        for row in rows :
            cells = row.find_elements(By.TAG_NAME,'td')
            rowData = [cell.text.replace("\n"," ") for cell in cells]  
            if rowData:
                data.append(rowData)
        
        DF = pd.DataFrame(data,columns=metaData)
        print(DF) 

        
    except:
        print('couldnt fetch anything')

    #fetching icons
    # Folder name based on Y-M-D
    folder_name = datetime.now().strftime("%Y-%m-%d")

    # Create the folder if it doesn't exist
    os.makedirs(folder_name, exist_ok=True)


    # Get current date as string, e.g., 2025-11-24
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create dynamic filename
    filename = f"tradingview_table_{date_str}.csv"
    # Full path: folder + file
    file_path = os.path.join(folder_name, filename)

    # Save the CSV
    DF.to_csv(file_path, index=False)
    snitch.close()

    time.sleep(60)