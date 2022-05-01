from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import io
import requests
import time
import shutil
import os

# email
import creds
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# analytics
import numpy as np
import pandas as pd
import datetime as dt

today = dt.date.today()



chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
# chrome_options.binary_location = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
# driver = webdriver.Chrome(executable_path=os.path.abspath("chromedriver"),   chrome_options=chrome_options)

if not os.path.isdir("tmp"):
    os.mkdir("tmp")




def send_email(sender_email, receiver_email, subject='No Subject!', text='', html=''):
    port = 465  # For SSL

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(creds.GMAIL_NAME, creds.GMAIL_KEY)
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )
    return


def scrape_tcgplayer(url):
    driver.get(url)
    time.sleep(5)

    driver.execute_script("scrollTo(0, 700);")
    time.sleep(2)

    # Get sales history ----------------------------------------
    print('----------------------- Get Historical Sales --------------------------')
    print(url)
    sales_data = driver.find_elements_by_xpath("//h3[@class='price-guide__latest-sales__more']/span")
    print(sales_data)
    try:
        sales_data[0].click()
    except:
        return pd.DataFrame(), pd.DataFrame(), []

    time.sleep(2)

    # sales = driver.find_elements_by_xpath("//ul[@class='is-modal']")
    # sales = driver.find_elements_by_xpath("//div[@class='price-guid-modal__latest-sales-header']//li")
    sales = driver.find_elements_by_xpath("//ul[@class='is-modal']//li")
    # sales = driver.find_elements_by_xpath("/html/body/div[1]/div/div/div/div/section[2]/section[2]/ul/li")
    print(f'Total historical sales {len(sales)}')
    try:


        # Get buylist and market price info
        summary_header = [xx.text.strip() for xx in sales[0].find_elements_by_xpath("//span[@class='price-points__header__price']")]
        print(summary_header)

        if "Foil" in summary_header:
            market_price = sales[0].find_elements_by_xpath("//span[@class='price']")[0].text.strip()
            market_price_foil = sales[0].find_elements_by_xpath("//span[@class='price']")[1].text.strip()

            buylist_price = sales[0].find_elements_by_xpath("//span[@class='price']")[2].text.strip()
            buylist_price_foil = sales[0].find_elements_by_xpath("//span[@class='price']")[3].text.strip()

            list_median_price = sales[0].find_elements_by_xpath("//span[@class='price']")[4].text.strip()
            list_median_price_foil = sales[0].find_elements_by_xpath("//span[@class='price']")[5].text.strip()
            offset = 6
        else:
            market_price = sales[0].find_elements_by_xpath("//span[@class='price']")[0].text.strip()
            buylist_price = sales[0].find_elements_by_xpath("//span[@class='price']")[1].text.strip()
            list_median_price = sales[0].find_elements_by_xpath("//span[@class='price']")[2].text.strip()
            offset = 3

        print(f'market price = {market_price}, buylist price = {buylist_price}, listed median = {list_median_price}')

        loop1 = 0
        historical_sales = []

        for sale in sales:

            try:
                date = sale.find_elements_by_xpath("//span[@class='date']")[loop1].text.strip()
                photo = False
                #print(f"""Total length of sale {len(sale.find_elements_by_xpath("//span[@class='date']"))}""")
            except:
                date = sale.find_elements_by_xpath("//span[@class='date custom-listing']")[loop1].text.strip()
                photo = True

            condition = sale.find_elements_by_xpath("//span[@class='condition']")[loop1].text.strip()
            # Handle Foreign Cards
            if len(condition.split(' ')) > 1 and 'Foil' not in condition:
                condition = condition.split(' ')[0] + ' Foreign'
            quantity = sale.find_elements_by_xpath("//span[@class='quantity']")[loop1].text.strip()
            price = sale.find_elements_by_xpath("//span[@class='price']")[loop1+offset].text.strip()
            loop1 += 1

            historical_sales.append((date, condition, quantity, price, photo))
            print(date, condition, quantity, price, photo)
    except:
        print('Done collecting historical sales data')

    sales_df = pd.DataFrame(historical_sales, columns=['date', 'condition', 'quantity', 'price', 'has_photo'])
    try:
        sales_df.loc[:, 'price'] = sales_df['price'].apply(lambda x: int(round(float(x.strip('$').replace(',', ''))*100)))
    except:
        pass

    #print('--------- Fit Historical Model ----------')
    #from sklearn.linear_model import LinearRegression
    #X = pd.get_dummies(data=sales_df[['condition', 'has_photo']], drop_first=True)
    #y = sales_df['price']
    #clf = LinearRegression()
    #clf.fit(X, y)
    #print(X)
    #print(clf.coef_)

    sales_summary = sales_df[['condition', 'price']].groupby(by='condition').describe()
    print(" ----- Raw sales summary: ----")
    print(sales_summary)

    # Close the sales history snapshot modal
    driver.find_element_by_xpath("//span[@class='modal__close']").click()

    print("------------- Listings --------------")
    driver.execute_script("scrollTo(0, 1500);")
    time.sleep(3)

    listed_items = []
    contin = True
    while contin:
        time.sleep(3)
        loop2 = 0
        # /html/body/div[1]/div/section[2]/section/div[2]/section/section/section/section[1]
        listings = driver.find_elements_by_xpath("//section[@class='listing-item product-details__listings-results']")
        for listing in listings:
            price = listing.find_elements_by_xpath("//div[@class='listing-item__price']")[loop2].text.strip()
            condition = listing.find_elements_by_xpath("//h3[@class='listing-item__condition']")[loop2].text.strip()
            # handle the foreign cards
            if '-' in condition:
                condition = condition.split(' - ')[0] + ' Foreign'
            print(price, condition)

            loop2 += 1

            listed_items.append((price, condition))

        try:
            # Go to next page of listings
            action = webdriver.common.action_chains.ActionChains(driver)
            height = driver.find_element_by_xpath("//a[@class=' nextPage']").location
            driver.execute_script("scrollTo(0, " + str(height["y"]) + ");")
            action.move_to_element(driver.find_element_by_xpath("//a[@class=' nextPage']")).click().perform()

        except:
            contin = False

    listed_items_df = pd.DataFrame(listed_items, columns=['price', 'condition'])
    listed_items_df.loc[:, 'price'] = listed_items_df['price'].apply(lambda x: int(round(float(x.strip('$').replace(',', ''))*100)))

    return sales_df, listed_items_df, (market_price, buylist_price, list_median_price)


def analyze_listings_vs_historicals(past_sales, listings, market_summary):
    # Listings have long condition, historical sales have short condition
    conditions = {'Damaged': 'DMG', 'Heavily Played': 'HP',
                  'Moderately Played': 'MP', 'Lightly Played': 'LP',
                  'Near Mint': 'NM', 'Unopened': 'Unopened'}
    conditions_foil = {cc+' Foil': conditions[cc]+' Foil' for cc in conditions}
    conditions_foreign = {cc+' Foreign': conditions[cc]+' Foreign' for cc in conditions}
    conditions_foil_foreign = {cc+' Foil Foreign': conditions[cc]+' Foil Foreign' for cc in conditions}

    conditions = {**conditions, **conditions_foil, **conditions_foreign, **conditions_foil_foreign}

    market, buylist, list_med = market_summary
    try:
        buylist = float(buylist)
    except:
        buylist = 0

    conditions_short = [conditions[cc] for cc in conditions]
    print(past_sales)
    # past_sales = past_sales[pd.to_numeric(past_sales['price'], errors='coerce').notnull()].to_frame()
    past_sales = past_sales[past_sales.price.apply(lambda x: x.isnumeric() if type(x)==str else True)]
    if not isinstance(past_sales, pd.DataFrame):
        past_sales = past_sales.to_frame()
    print('Cleaned past sales:')
    print(past_sales)

    sales_summary = past_sales[['condition', 'price']].groupby(by='condition').describe(percentiles=[.25, .5, .75])

    # Need to create a curve for the condition/price curve
    past_conditions = sales_summary.index

    # see which conditions are not covered in the past data, add to the summary
    conditions_to_add = [cc for cc in conditions_short if cc not in past_conditions]
    print(past_conditions)
    print(conditions_to_add)
    print(sales_summary)

    for condition in conditions_to_add:
        sales_summary.loc[condition, :] = [np.nan]*len(sales_summary.columns)

    # Reorder summary df in increasing conditions
    sales_summary = sales_summary.loc[conditions_short, :]

    # Now need to interpolate any of the missing points
    sales_summary.loc[:, ('price', '25%')] = sales_summary.loc[:, ('price', '25%')].interpolate(method='linear')
    sales_summary.loc[:, ('price', 'min')] = sales_summary.loc[:, ('price', 'min')].interpolate(method='linear')
    print(sales_summary)

    THRESHOLD = 0.8
    flagged_listings = []
    # Now evaluate the listings according to our rules
    for ii, listing in listings.iterrows():
        list_cond = listing.condition
        list_px = listing.price
        
        print('List condition & price: ', list_cond, list_px)

        list_cond_short = conditions[list_cond]

        comp_25p = sales_summary.loc[list_cond_short, ('price', '25%')]
        comp_min = sales_summary.loc[list_cond_short, ('price', 'min')]
        
        print(comp_25p)

        if list_px < THRESHOLD * comp_25p:
            flagged_listings.append([f'${list_px/100}', list_cond, f'${comp_min/100}', f'${comp_25p/100}', '80%ofQuart'])
        elif list_px < 0.9 * comp_min:
            flagged_listings.append([f'${list_px/100}', list_cond, f'${comp_min/100}', f'${comp_25p/100}', 'below90%Min'])
        elif (list_cond in ['Lightly Played', 'Near Mint']) and (list_px < buylist):
            flagged_listings.append([f'${list_px/100}', list_cond, f'${comp_min/100}', f'${comp_25p/100}', 'belowBuylist'])
        elif (list_cond in ['Moderately Played']) and (list_px < 0.7*buylist):
            flagged_listings.append([f'${list_px/100}', list_cond, f'${comp_min/100}', f'${comp_25p/100}', 'belowMPbuylist'])
        elif (list_cond in ['Heavily Played']) and (list_px < 0.5*buylist):
            flagged_listings.append([f'${list_px/100}', list_cond, f'${comp_min/100}', f'${comp_25p/100}', 'belowHPbuylist'])

    flagged_listings_df = pd.DataFrame(flagged_listings, columns = ['List Price', 'List Condition', 'Sales Min', 'Sales 25% Q', 'Flag Reason'])

    return flagged_listings_df


def construct_email(flagged):

    body = ''
    for url in flagged:
        data = flagged[url]

        if not data.empty:
            body += f'<a href={url}>{url}</a>' + '\n'
            body += data.to_html()
            body += '\n <br>'

    if not body:
        body = 'No listings flagged'

    return body


if __name__ == "__main__":
    with open("searchUrls.txt", 'r') as obj:
        urls = obj.readlines()

    flagged_listings = {}
    for url in urls:
    #if True:
     #   url = 'https://www.tcgplayer.com/product/7118/magic-urzas-saga-yawgmoths-will?page=1&Language=all'
        past_sales, current_listings, market_summary = scrape_tcgplayer(url.replace("\n", ""))

        if not past_sales.empty:
            flagged = analyze_listings_vs_historicals(past_sales, current_listings, market_summary)
            flagged_listings[url] = flagged

    email_body = construct_email(flagged_listings)

    send_email(creds.GMAIL_NAME, creds.GMAIL_TO, subject='Cheap TCG Player Listings',
               text='', html=email_body)

    #workbook.close()
    driver.quit()

    shutil.rmtree("tmp")
