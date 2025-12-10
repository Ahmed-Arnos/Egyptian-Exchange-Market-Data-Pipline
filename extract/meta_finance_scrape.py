from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
import time
import requests
import pandas as pd
from datetime import datetime
import json
import random

def extract_financial_metric(driver, wait, metric_name, quarters):
    """
    Extracts a metric (e.g., Gross profit) safely from TradingView.
    Handles:
      - missing rows
      - missing values (dashes)
      - Unicode cleanup
      - TTM trimming
    """

    # 1. Find the row
    value_xpath = (
        # CONDITION 1: Numeric Value with Positive Change (Two-div structure)
        f"(//div[@data-name='{metric_name}']//div["
            "./div[contains(@class, 'value-OxVAcLqi')]"
        "]/div[@class='value-OxVAcLqi'])"
        
        " | "
        
        # CONDITION 2: Missing Value Hyphen (Single-div structure)
        f"(//div[@data-name='{metric_name}']//div["
            "not(./div[contains(@class, 'change-OxVAcLqi')])" # Ensure no change div is present
        "]/div[@class='value-OxVAcLqi'])"
        )
    
    row_xpath = f"//div[@data-name='{metric_name}']"

    # Check if row exists without waiting (to avoid timeout for missing metrics)
    row_exists = driver.find_elements(By.XPATH, row_xpath)

    if not row_exists:
        # Metric not available for this company
        return [None] * len(quarters)

    # 2. Extract the values
    wait.until(EC.presence_of_element_located((By.XPATH, value_xpath)))

    elements = driver.find_elements(By.XPATH, value_xpath)
    raw_values = [el.text.strip() for el in elements]

    # 3. Clean unicode + convert dashes
    cleaned_values = []
    for v in raw_values:
        for ch in ("\u202a", "\u202b", "\u202c", "\u202e", "\u202f"):
            v = v.replace(ch, "")
        if v in ["—", "–", "-"]:
            v = None   # represent missing numeric
        cleaned_values.append(v)

    # 4. TTM trimming (TradingView often includes 1 extra left column)
    if len(cleaned_values) > len(quarters):
        cleaned_values = cleaned_values[:-1]

    return cleaned_values


df = pd.read_csv('./ticks_urls.csv')
df

# companies_metadata=[]


exp_urls= df
snitch = webdriver.Firefox()
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
wait = WebDriverWait(snitch, 15)
short_wait = WebDriverWait(snitch, 3)

# time.sleep(30)

for _, rows in exp_urls[["Link Text", "URL"]].iloc[227:].iterrows():
    company_metadata=[]
    exp_url=rows["URL"]
    ticker_name= rows["Link Text"]

    time.sleep(random.uniform(1.8, 4.3))

    snitch.get(exp_url)

    # try:
    #     close_btn = WebDriverWait(snitch, 10).until(
    #         EC.element_to_be_clickable(
    #             (By.XPATH,'/html/body/div[7]/div[2]/div[2]/div/div/div/div[2]')
    #         )
    #     )
    #     close_btn.click()
    #     print("Popup closed.")
    # except:
    #     print("Popup not found OR already closed.")
    # time.sleep(2)
    
    try:
        captcha_h1 = short_wait.until(
            EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Just one more step']"))
        )

        print("Captcha detected")

        WebDriverWait(snitch, 60).until(
            EC.invisibility_of_element(captcha_h1)
        )
        
        print("Captcha solved")
        
        time.sleep(10)
    except:
        pass


    snitch.execute_script("document.body.style.zoom='20%'")


    try:
        company_name_selector = 'h1[class*="apply-overflow-tooltip title-HDE_EEoW"]'
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, company_name_selector)))
        company_name= snitch.find_element(By.CSS_SELECTOR, company_name_selector).text

    except:
        company_name=None


    try:
        currency_selector = 'span[data-qa-id*="symbol-currency"]'
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, currency_selector)))
        currency= snitch.find_element(By.CSS_SELECTOR, currency_selector).text
    except:
        currency=None

    try:
        sec_selector = 'a[href*="/markets/stocks-egypt/sectorandindustry-sector/"]'
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sec_selector)))
        sec_ind= snitch.find_element(By.CSS_SELECTOR, sec_selector).text
    except:
        sec_ind=None


    try:
        prc_selector = 'a[href*="/markets/stocks-egypt/sectorandindustry-industry/"]'
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, prc_selector)))
        prc_ind= snitch.find_element(By.CSS_SELECTOR, prc_selector).text
    except:
        prc_ind=None


    try:
        ceo_selector = "//div[./div[text()='CEO']]/following-sibling::div//div[contains(@class, 'value-QCJM7wcY')]"
        wait.until(EC.presence_of_element_located((By.XPATH, ceo_selector)))
        ceo_name = snitch.find_element(By.XPATH, ceo_selector).text
    except:
        ceo_name=None


    try:
        website_selector= "//div[./div[text()='Website']]/following-sibling::div//a"
        wait.until(EC.presence_of_element_located((By.XPATH, website_selector)))
        website= snitch.find_element(By.XPATH, website_selector).text
    except:
        website=None


    try:
        headquarters_selector= "//div[./div[text()='Headquarters']]/following-sibling::div//div[contains(@class, 'value-QCJM7wcY')]"
        wait.until(EC.presence_of_element_located((By.XPATH, headquarters_selector)))
        headquarters= snitch.find_element(By.XPATH, headquarters_selector).text
    except:
        headquarters=None


    try:
        founded_selector= "//div[./div[text()='Founded']]/following-sibling::div//div[contains(@class, 'value-QCJM7wcY')]"
        wait.until(EC.presence_of_element_located((By.XPATH, founded_selector)))
        founded_date= snitch.find_element(By.XPATH, founded_selector).text
    except:
        founded_date=None


    try:
        isin_selector= "//div[./div[text()='ISIN']]/following-sibling::div//div[contains(@class, 'value-QCJM7wcY')]"
        wait.until(EC.presence_of_element_located((By.XPATH, isin_selector)))
        isin= snitch.find_element(By.XPATH, isin_selector).text
    except:
        isin=None


    print(company_name)
    print(currency)
    print(sec_ind)
    print(prc_ind)
    print(ceo_name)
    print(website)
    print(headquarters)
    print(founded_date)
    print(isin)
    company_metadata.append({
        "symbol": ticker_name,
        "company_name": company_name,
        "currency": currency,
        "sector": sec_ind,
        "industry": prc_ind,
        "ceo_name": ceo_name,
        "website": website,
        "headquarters": headquarters,
        "founded_date": founded_date,
        "isin":isin
    })

    exp_url= exp_url+"financials-income-statement/"

    time.sleep(random.uniform(1.8, 4.3))
    snitch.get(exp_url)


    try:
        captcha_h1 = short_wait.until(
            EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Just one more step']"))
        )

        print("Captcha detected")

        WebDriverWait(snitch, 60).until(
            EC.invisibility_of_element(captcha_h1)
        )
        
        print("Captcha solved")
        
        time.sleep(10)
    except:
        pass

    #extract quarters
    quarters=[]
    try:
        quarters_selector= 'div[class="value-OxVAcLqi"]'
        snitch.execute_script("document.body.style.zoom='20%'")
        wait.until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, quarters_selector)))

        quarters_items= snitch.find_elements(By.CSS_SELECTOR, quarters_selector)
        for element in quarters_items:
            if "Q" in element.text:
                quarters.append(element.text)
        quarters= quarters[-8:]
        print(quarters)
    except Exception as e:
        print(e)

    #extract total revenue
    total_revenue= extract_financial_metric(snitch, wait, "Total revenue", quarters )


    #extract gross profit
    gross_profit= extract_financial_metric(snitch, wait, "Gross profit", quarters)


    #extract net income
    net_income= extract_financial_metric(snitch, wait, "Net income", quarters)

    #extract eps
    eps= extract_financial_metric(snitch, wait, "Basic earnings per share (basic EPS)", quarters)


    #extract operating expenses
    op_expense= extract_financial_metric(snitch, wait, "Total operating expenses", quarters)
    

    time.sleep(random.uniform(1.8, 4.3))

    #Click balance sheet
    try:

        link_id = "balance sheet"
        balance_sheet_link = snitch.find_element(By.ID, link_id)
        balance_sheet_link.click()

    except Exception as e:
        print(e)


    try:
        captcha_h1 = short_wait.until(
            EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Just one more step']"))
        )

        print("Captcha detected")

        WebDriverWait(snitch, 60).until(
            EC.invisibility_of_element(captcha_h1)
        )
        
        print("Captcha solved")
        
        time.sleep(10)
    except:
        pass

    snitch.execute_script("document.body.style.zoom='20%'")

    #extract assets
    assets_expense= extract_financial_metric(snitch, wait, "Total assets", quarters)
    
    #extract Total liabilities
    liabilities= extract_financial_metric(snitch, wait, "Total liabilities", quarters)


    time.sleep(random.uniform(1.8, 4.3))

    #Click cash flow
    try:

        link_id = "cash flow"
        balance_sheet_link = snitch.find_element(By.ID, link_id)
        balance_sheet_link.click()

    except Exception as e:
        print(e)


    try:
        captcha_h1 = short_wait.until(
            EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Just one more step']"))
        )

        print("Captcha detected")

        WebDriverWait(snitch, 60).until(
            EC.invisibility_of_element(captcha_h1)
        )
        
        print("Captcha solved")
        
        time.sleep(10)
    except:
        pass

    snitch.execute_script("document.body.style.zoom='20%'")

    #extract Free cash flow
    free_cash_flow= extract_financial_metric(snitch, wait, "Free cash flow", quarters)

    print(len(total_revenue))
    print(len(gross_profit))
    print(len(quarters))
    print(quarters)

    financials= []
    for i in range(len(quarters)):
        financials.append({quarters[i]:{
            "total_revenue": total_revenue[i],
            "gross_profit": gross_profit[i],
            "net_income": net_income[i],
            "eps": eps[i],
            "operating_expense": op_expense[i],
            "total_assets": assets_expense[i],
            "total_liabilities": liabilities[i],
            "free_cash_flow": free_cash_flow[i]
        }})

    df_ready_data = []
    


    for i in range(len(quarters)):
        # Create one dictionary per quarter (per row)
        row_data = {
            "Quarter": quarters[i],
            "total_revenue": total_revenue[i],
            "gross_profit": gross_profit[i],
            "net_income": net_income[i],
            "eps": eps[i],
            "operating_expense": op_expense[i],
            "total_assets": assets_expense[i],
            "total_liabilities": liabilities[i],
            "free_cash_flow": free_cash_flow[i]
        }
        df_ready_data.append(row_data)

    # print(df_ready_data[0]) 

    df = pd.DataFrame(df_ready_data)

    df.to_csv(f"./finances/{ticker_name}_finance.csv")
    company_df= pd.DataFrame(company_metadata)
    company_df.to_csv("./companies/company_meta.csv", mode="a", header=False, index=False)

snitch.quit()
# companies_df= pd.DataFrame(companies_metadata)
# print(companies_df)
# companies_df.to_csv("./companies/company_meta.csv")