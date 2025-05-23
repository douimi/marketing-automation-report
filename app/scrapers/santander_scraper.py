from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup

SANTANDER_LOGIN_URL = "https://santandertrade.com/en/" # As confirmed by user
PRE_LOGIN_FORM_BUTTON_XPATH = "//*[@id='btn_login_menu']" # User provided XPath to reveal login form
SANTANDER_EMAIL_XPATH = "//*[@id='identification_identifiant']"
SANTANDER_PASSWORD_XPATH = "//*[@id='identification_mot_de_passe']"
SANTANDER_LOGIN_BUTTON_XPATH = "//*[@id='identification_go']"
SANTANDER_MARKET_ANALYSIS_URL_TEMPLATE = "https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/general-presentation"
SANTANDER_ECO_POL_URL_TEMPLATE = "https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/economic-political-outline"

def login_santander(driver, email, password):
    """
    Logs into Santander Trade using JavaScript execution.
    Clicks a specific button to reveal the login form first.
    """
    driver.get(SANTANDER_LOGIN_URL)
    print(f"Navigated to {SANTANDER_LOGIN_URL}")
    time.sleep(1) # Allow initial page elements to settle slightly

    # Click the button to reveal the login form
    try:
        print(f"Attempting to find and click button to reveal login form: {PRE_LOGIN_FORM_BUTTON_XPATH}")
        pre_login_form_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, PRE_LOGIN_FORM_BUTTON_XPATH))
        )
        print(f"Found button to reveal login form. Clicking it...")
        driver.execute_script("arguments[0].click();", pre_login_form_button)
        print("Button to reveal login form clicked.")
        time.sleep(2) # Wait for form to appear after click
    except Exception as e:
        print(f"Could not find or click button to reveal login form ({PRE_LOGIN_FORM_BUTTON_XPATH}). Error: {e}")
        return # Cannot proceed if this fails

    # Now, wait for the actual email field to be present
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, SANTANDER_EMAIL_XPATH)))
        print("Email field is present.")
    except Exception as e:
        print(f"Email field ({SANTANDER_EMAIL_XPATH}) not found after attempting to reveal form. Login cannot proceed. Error: {e}")
        return # Cannot proceed if email field isn't found

    # Use JavaScript to fill forms
    set_value_script = "document.evaluate(arguments[0], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.value = arguments[1];"
    driver.execute_script(set_value_script, SANTANDER_EMAIL_XPATH, email)
    driver.execute_script(set_value_script, SANTANDER_PASSWORD_XPATH, password)
    print("Email and password fields filled.")

    # Click the final login button
    try:
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, SANTANDER_LOGIN_BUTTON_XPATH))
        )
        driver.execute_script("arguments[0].click();", login_button)
        print("Login button clicked.")
    except Exception as e:
        print(f"Could not find or click final login button ({SANTANDER_LOGIN_BUTTON_XPATH}). Error: {e}")
        return

    # Wait for login to complete
    try:
        print(f"Waiting for URL to change from {driver.current_url} or for a known post-login element...")
        time.sleep(5) # Give time for redirection or error message to appear
        current_page_url = driver.current_url
        if SANTANDER_LOGIN_URL in current_page_url and current_page_url.endswith("#identification"): # Often hash is added for on-page forms
             print(f"Still on {current_page_url}. Checking if login form elements are still present...")
             try:
                driver.find_element(By.XPATH, SANTANDER_EMAIL_XPATH) # Check if email field is still present
                print("Login likely failed: Still on login page/modal and email field is visible.")
             except:
                print("Login may have succeeded (modal closed) or structure changed. Current URL: {current_page_url}")
        elif SANTANDER_LOGIN_URL == current_page_url: # Exactly the same URL, no hash
             print("Login likely failed: URL did not change from the initial login page.")
        else:
            print(f"Login successful or navigated away. Current URL: {current_page_url}")

    except Exception as e:
        print(f"Error during post-login check: {e}")


def scrape_santander_country_data(driver, formatted_country_name):
    """
    Navigates to the country's general presentation page and scrapes data from 'donnees1' and the Foreign Trade in Figures table.
    Returns a dict with clean plain text for both sections.
    """
    target_url = SANTANDER_MARKET_ANALYSIS_URL_TEMPLATE.format(formatted_country_name=formatted_country_name)
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        # Wait for the main content div to be present
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Extract donnees1 section
        donnees1 = soup.find(id="donnees1")
        donnees1_text = ""
        if donnees1:
            donnees1_text = str(donnees1)

        # Extract donnees2 section
        donnees2 = soup.find(id="donnees2")
        donnees2_text = ""
        if donnees2:
            donnees2_text = str(donnees2)

        # Extract Foreign Trade in Figures table
        trade_table = soup.select_one('#contenu-contenu > div:nth-of-type(2) > div:nth-of-type(6) > div:nth-of-type(1) > table')
        trade_table_data = []
        if trade_table:
            headers = [th.get_text(strip=True) for th in trade_table.find_all('th')]
            for row in trade_table.find_all('tr')[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if len(cells) == len(headers):
                    trade_table_data.append(dict(zip(headers, cells)))
                else:
                    trade_table_data.append(cells)

        # Return both sections as structured data
        return {
            'donnees1_text': donnees1_text,
            'donnees2_text': donnees2_text,
            'trade_table': trade_table_data
        }
    except Exception as e:
        print(f"Error scraping Santander country data for {formatted_country_name}: {e}")
        current_url = driver.current_url
        page_title = driver.title
        print(f"Current URL during error: {current_url}")
        print(f"Page title during error: {page_title}")
        if "page not found" in page_title.lower() or "error 404" in driver.page_source.lower():
            return {"error": f"Error: Page not found for country {formatted_country_name} at {target_url}."}
        return {"error": f"Error scraping Santander data for {formatted_country_name}. Details: {str(e)}"}


def scrape_santander_economic_political_outline(driver, formatted_country_name):
    """
    Navigates to the country's economic-political-outline page and scrapes all required data for the Economic and Political Outline section.
    Returns a dict with all fields needed for the template.
    """
    target_url = SANTANDER_ECO_POL_URL_TEMPLATE.format(formatted_country_name=formatted_country_name)
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        # Wait for the main content to load
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//*[@class="fond-theme-atlas "]')))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Economic Outline
        eco_outline = soup.find('div', id='economique')
        eco_outline_overview = ""
        eco_outline_main_indicators_table = ""
        eco_outline_main_sectors = ""
        eco_outline_breakdown_table = ""
        eco_outline_economic_freedom = ""
        eco_outline_business_env = ""
        if eco_outline:
            # Economic Overview (all <p> under Economic Overview h3)
            eco_overview_h3 = eco_outline.find('h3', string=lambda t: t and 'Economic Overview' in t)
            if eco_overview_h3:
                overview_ps = []
                sib = eco_overview_h3.find_next_sibling()
                while sib and sib.name == 'p':
                    overview_ps.append(str(sib))
                    sib = sib.find_next_sibling()
                eco_outline_overview = "\n".join(overview_ps)
            # Main Indicators Table
            main_ind_table = eco_outline.find('table')
            if main_ind_table and main_ind_table.find('th', string=lambda t: t and 'Main Indicators' in t):
                eco_outline_main_indicators_table = str(main_ind_table)
            # Main Sectors of Industry (after h3)
            main_sectors_h3 = eco_outline.find('h3', string=lambda t: t and 'Main Sectors of Industry' in t)
            if main_sectors_h3:
                main_sectors_p = main_sectors_h3.find_next_sibling('p')
                if main_sectors_p:
                    eco_outline_main_sectors = str(main_sectors_p)
            # Breakdown Table (after Main Sectors)
            breakdown_table = None
            for table in eco_outline.find_all('table'):
                th = table.find('th')
                if th and 'Breakdown of Economic Activity By Sector' in th.get_text():
                    breakdown_table = table
                    break
            if breakdown_table:
                eco_outline_breakdown_table = str(breakdown_table)
            # Economic Freedom
            eco_freedom_h3 = eco_outline.find('h3', string=lambda t: t and 'Economic Freedom' in t)
            if eco_freedom_h3:
                eco_freedom_dl = eco_freedom_h3.find_next_sibling('dl')
                if eco_freedom_dl:
                    eco_outline_economic_freedom = str(eco_freedom_dl)
            # Business Environment Ranking
            business_env_h3 = eco_outline.find('h3', string=lambda t: t and 'Business environment ranking' in t)
            if business_env_h3:
                business_env_dl = business_env_h3.find_next_sibling('dl')
                if business_env_dl:
                    eco_outline_business_env = str(business_env_dl)

        # Political Outline
        # Find the div after <a id="political">
        political_anchor = soup.find('a', id='political')
        political_outline = ""
        political_press_freedom = ""
        political_freedom = ""
        if political_anchor:
            pol_div = political_anchor.find_next_sibling('div')
            if pol_div:
                # Main political outline (first dl.informations)
                pol_dl = pol_div.find('dl', class_='informations')
                if pol_dl:
                    political_outline = str(pol_dl)
                # Freedom of the Press
                press_h3 = pol_div.find('h3', string=lambda t: t and 'Freedom of the Press' in t)
                if press_h3:
                    press_dl = press_h3.find_next_sibling('dl')
                    if press_dl:
                        political_press_freedom = str(press_dl)
                # Political Freedom
                polfree_h3 = pol_div.find('h3', string=lambda t: t and 'Political Freedom' in t)
                if polfree_h3:
                    polfree_dl = polfree_h3.find_next_sibling('dl')
                    if polfree_dl:
                        political_freedom = str(polfree_dl)

        return {
            'eco_outline_overview': eco_outline_overview,
            'eco_outline_main_indicators_table': eco_outline_main_indicators_table,
            'eco_outline_main_sectors': eco_outline_main_sectors,
            'eco_outline_breakdown_table': eco_outline_breakdown_table,
            'eco_outline_economic_freedom': eco_outline_economic_freedom,
            'eco_outline_business_env': eco_outline_business_env,
            'political_outline': political_outline,
            'political_press_freedom': political_press_freedom,
            'political_freedom': political_freedom
        }
    except Exception as e:
        print(f"Error scraping Santander Economic and Political Outline for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Economic and Political Outline for {formatted_country_name}: {str(e)}'} 