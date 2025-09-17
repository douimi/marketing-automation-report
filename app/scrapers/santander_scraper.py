from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
import json
import os

SANTANDER_LOGIN_URL = "https://santandertrade.com/en/" # As confirmed by user
PRE_LOGIN_FORM_BUTTON_XPATH = "//*[@id='btn_login_menu']" # User provided XPath to reveal login form
SANTANDER_EMAIL_XPATH = "//*[@id='identification_identifiant']"
SANTANDER_PASSWORD_XPATH = "//*[@id='identification_mot_de_passe']"
SANTANDER_LOGIN_BUTTON_XPATH = "//*[@id='identification_go']"
SANTANDER_MARKET_ANALYSIS_URL_TEMPLATE = "https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/general-presentation"
SANTANDER_ECO_POL_URL_TEMPLATE = "https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/economic-political-outline"

def get_santander_country_code(country_code):
    """
    Dynamically look up the Santander country code from countries.json file.
    
    Args:
        country_code (str): The country code to look up (can be 2-letter or 3-letter ISO code)
        
    Returns:
        str: The Santander country code (ISO2 field) or None if not found
    """
    try:
        # Get the path to countries.json (relative to this file)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(current_dir, '..', 'config')
        countries_file = os.path.join(config_dir, 'countries.json')
        
        # Load countries data
        with open(countries_file, 'r', encoding='utf-8') as f:
            countries = json.load(f)
        
        # Search for the country by code (3-letter) or ISO2 (2-letter if applicable)
        for country in countries:
            # Check if the provided code matches either the 'code' field or any other identifier
            if (country.get('code') == country_code or 
                country.get('ISO2') == country_code or
                country.get('name', '').upper() == country_code.upper()):
                
                # Return the ISO2 field which contains the Santander internal ID
                santander_code = country.get('ISO2')
                if santander_code:
                    print(f"Found Santander code for {country_code}: {santander_code} ({country.get('name')})")
                    return santander_code
        
        print(f"No Santander code found for country: {country_code}")
        return None
        
    except Exception as e:
        print(f"Error loading countries.json: {e}")
        return None

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
        time.sleep(2) # Give time for redirection or error message to appear
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

        # Success message
        print(f"Successfully scraped Economic and Political Outline data for {formatted_country_name}")

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


def scrape_santander_operating_a_business(driver, formatted_country_name):
    """
    Navigates to the country's 'Operating a Business' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/establish-overseas/{formatted_country_name}/operating-a-business"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        # Wait for the main content div to be present
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            # Remove 'Return to top' links from the concatenated HTML
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            # Remove feedback and footer elements
            # Remove <span class="remarque-atlas"> and its parent <p class="contact-atlas">
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            # Remove <p class="droits">
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            # Remove <span> with 'All Rights Reserved' or 'Latest Update'
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        # Legal Forms of Companies & Business Setup Procedures
        legal_section = get_section_by_anchor('legal')
        # The Active Population in Figures
        active_population_section = get_section_by_anchor('active')
        # Working Conditions
        working_conditions_section = get_section_by_anchor('working')
        # The Cost of Labour
        cost_of_labour_section = get_section_by_anchor('cost')
        # Management of Human Resources
        management_section = get_section_by_anchor('management')

        # Extract update date if present
        update_span = main.find('span', string=lambda t: t and 'Latest Update' in t)
        update_date = ''
        if update_span:
            update_date = update_span.find_next(string=True)
        else:
            droits = main.find('p', class_='droits')
            if droits:
                update_date = droits.get_text(strip=True)

        return {
            'legal_section': legal_section,
            'active_population_section': active_population_section,
            'working_conditions_section': working_conditions_section,
            'cost_of_labour_section': cost_of_labour_section,
            'management_section': management_section,
            'update_date': update_date,
            'raw_html': str(main)  # Optionally, for debugging or further parsing
        }
    except Exception as e:
        print(f"Error scraping Santander Operating a Business for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Operating a Business for {formatted_country_name}: {str(e)}'}


def scrape_santander_tax_system(driver, formatted_country_name):
    """
    Navigates to the country's 'Tax System' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/establish-overseas/{formatted_country_name}/tax-system"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        corporate_taxes_section = get_section_by_anchor('company')
        accounting_rules_section = get_section_by_anchor('accounting')
        consumption_taxes_section = get_section_by_anchor('consumption')
        individual_taxes_section = get_section_by_anchor('individual')
        double_taxation_section = get_section_by_anchor('international')
        sources_section = get_section_by_anchor('sources')

        return {
            'corporate_taxes_section': corporate_taxes_section,
            'accounting_rules_section': accounting_rules_section,
            'consumption_taxes_section': consumption_taxes_section,
            'individual_taxes_section': individual_taxes_section,
            'double_taxation_section': double_taxation_section,
            'sources_section': sources_section,
            'raw_html': str(main)
        }
    except Exception as e:
        print(f"Error scraping Santander Tax System for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Tax System for {formatted_country_name}: {str(e)}'}


def scrape_santander_legal_environment(driver, formatted_country_name):
    """
    Navigates to the country's 'Legal Environment' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/establish-overseas/{formatted_country_name}/legal-environment"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        business_contract_section = get_section_by_anchor('business')
        intellectual_property_section = get_section_by_anchor('intellectual')
        legal_framework_section = get_section_by_anchor('legal')
        dispute_resolution_section = get_section_by_anchor('idr')

        return {
            'business_contract_section': business_contract_section,
            'intellectual_property_section': intellectual_property_section,
            'legal_framework_section': legal_framework_section,
            'dispute_resolution_section': dispute_resolution_section,
            'raw_html': str(main)
        }
    except Exception as e:
        print(f"Error scraping Santander Legal Environment for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Legal Environment for {formatted_country_name}: {str(e)}'}


def scrape_santander_foreign_investment(driver, formatted_country_name):
    """
    Navigates to the country's 'Foreign Investment' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/establish-overseas/{formatted_country_name}/foreign-investment"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        fdi_figures_section = get_section_by_anchor('fdi')
        why_invest_section = get_section_by_anchor('why')
        protection_section = get_section_by_anchor('protection')
        administrative_section = get_section_by_anchor('administrative')
        office_section = get_section_by_anchor('office')
        aid_section = get_section_by_anchor('aid')
        opportunities_section = get_section_by_anchor('opportunities')
        sectors_section = get_section_by_anchor('sectors')
        finding_section = get_section_by_anchor('finding')

        return {
            'fdi_figures_section': fdi_figures_section,
            'why_invest_section': why_invest_section,
            'protection_section': protection_section,
            'administrative_section': administrative_section,
            'office_section': office_section,
            'aid_section': aid_section,
            'opportunities_section': opportunities_section,
            'sectors_section': sectors_section,
            'finding_section': finding_section,
            'raw_html': str(main)
        }
    except Exception as e:
        print(f"Error scraping Santander Foreign Investment for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Foreign Investment for {formatted_country_name}: {str(e)}'}


def scrape_santander_business_practices(driver, formatted_country_name):
    """
    Navigates to the country's 'Business Practices' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/establish-overseas/{formatted_country_name}/business-practices"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        business_culture_section = get_section_by_anchor('business-relations')
        opening_hours_section = get_section_by_anchor('working-hours')

        return {
            'business_culture_section': business_culture_section,
            'opening_hours_section': opening_hours_section,
            'raw_html': str(main)
        }
    except Exception as e:
        print(f"Error scraping Santander Business Practices for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Business Practices for {formatted_country_name}: {str(e)}'}


def scrape_santander_entry_requirements(driver, formatted_country_name):
    """
    Navigates to the country's 'Entry Requirements' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/establish-overseas/{formatted_country_name}/entry-requirements"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        passport_visa_section = get_section_by_anchor('passeport')
        customs_taxes_section = get_section_by_anchor('taxes')
        health_section = get_section_by_anchor('health')
        safety_section = get_section_by_anchor('safety')

        return {
            'passport_visa_section': passport_visa_section,
            'customs_taxes_section': customs_taxes_section,
            'health_section': health_section,
            'safety_section': safety_section,
            'raw_html': str(main)
        }
    except Exception as e:
        print(f"Error scraping Santander Entry Requirements for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Entry Requirements for {formatted_country_name}: {str(e)}'}


def scrape_santander_practical_information(driver, formatted_country_name):
    """
    Navigates to the country's 'Practical Information' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/establish-overseas/{formatted_country_name}/practical-information"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        eating_out_section = get_section_by_anchor('eating')
        getting_around_section = get_section_by_anchor('getting')
        time_section = get_section_by_anchor('time')
        climate_section = get_section_by_anchor('climate')
        electrical_section = get_section_by_anchor('electrical')
        paying_section = get_section_by_anchor('paying')
        speaking_section = get_section_by_anchor('speaking')
        emergency_section = get_section_by_anchor('emergency')
        communications_section = get_section_by_anchor('communications')

        return {
            'eating_out_section': eating_out_section,
            'getting_around_section': getting_around_section,
            'time_section': time_section,
            'climate_section': climate_section,
            'electrical_section': electrical_section,
            'paying_section': paying_section,
            'speaking_section': speaking_section,
            'emergency_section': emergency_section,
            'communications_section': communications_section,
            'raw_html': str(main)
        }
    except Exception as e:
        print(f"Error scraping Santander Practical Information for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Practical Information for {formatted_country_name}: {str(e)}'}


def scrape_santander_living_in_country(driver, formatted_country_name):
    """
    Navigates to the country's 'Living in the Country' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/establish-overseas/{formatted_country_name}/living-in-the-country"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        expatriates_section = get_section_by_anchor('expatriates')
        ranking_section = get_section_by_anchor('ranking')
        renting_section = get_section_by_anchor('renting')
        school_section = get_section_by_anchor('school')
        health_section = get_section_by_anchor('health')
        tourism_section = get_section_by_anchor('tourism')
        individual_section = get_section_by_anchor('individual')
        religion_section = get_section_by_anchor('religion')

        return {
            'expatriates_section': expatriates_section,
            'ranking_section': ranking_section,
            'renting_section': renting_section,
            'school_section': school_section,
            'health_section': health_section,
            'tourism_section': tourism_section,
            'individual_section': individual_section,
            'religion_section': religion_section,
            'raw_html': str(main)
        }
    except Exception as e:
        print(f"Error scraping Santander Living in the Country for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Living in the Country for {formatted_country_name}: {str(e)}'}


def scrape_santander_foreign_trade_in_figures(driver, formatted_country_name):
    """
    Navigates to the country's foreign-trade-in-figures page, clicks all 'See More' links for countries/products/services,
    scrapes all relevant data, and removes the last row from each relevant table. All links in tables are converted to plain text.
    """
    target_url = f"https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/foreign-trade-in-figures"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    # Helper to click a link by id if present
    def click_link_by_id(link_id):
        try:
            link = driver.find_element(By.ID, link_id)
            driver.execute_script("arguments[0].click();", link)
            time.sleep(1)  # Wait for table to expand
        except Exception as e:
            print(f"Could not click link with id {link_id}: {e}")

    # Click all 'See More' links for countries, products, services
    click_link_by_id('atlas_pays_export_lien')   # Main Customers
    click_link_by_id('atlas_pays_import_lien')   # Main Suppliers
    click_link_by_id('atlas_export_lien')        # Products Exported
    click_link_by_id('atlas_import_lien')        # Products Imported
    #click_link_by_id('plus_export_236')          # Services Exported
    #click_link_by_id('plus_import_236')          # Services Imported

    # Re-parse the page after all clicks
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    # Helper to clean table: remove last row, convert <a> to plain text
    def clean_table(table):
        if not table:
            return ''
        # Remove last row
        rows = table.find_all('tr')
        if len(rows) > 1:
            rows[-1].decompose()
        # Convert all <a> to plain text
        for a in table.find_all('a'):
            a.replace_with(a.get_text(strip=True))
        return str(table)

    # 1. Intro paragraph (first <p> in main content)
    intro_p = soup.find('p')
    intro_text = str(intro_p) if intro_p else ''

    # 2. All main tables (Foreign Trade Values, Indicators, Forecasts, Monetary Indicators)
    tables = soup.find_all('table')
    tables_html = [str(table) for table in tables]

    # 3. Main Partner Countries (tables with class 'tableau1' and 'tableau2' after 'Main Partner Countries' h2)
    main_partners_section = soup.find('h2', string=lambda t: t and 'Main Partner Countries' in t)
    main_customers_table = main_suppliers_table = ''
    if main_partners_section:
        double_tableau = main_partners_section.find_next('div', id='doubletableau')
        if double_tableau:
            tables = double_tableau.find_all('table')
            if len(tables) >= 2:
                main_customers_table = clean_table(tables[0])
                main_suppliers_table = clean_table(tables[1])

    # 4. Main Products (tables with class 'tableau1' and 'tableau2' after 'Main products' h3)
    main_products_section = soup.find('h3', string=lambda t: t and 'Main products' in t)
    main_export_products_table = main_import_products_table = ''
    if main_products_section:
        double_tableau = main_products_section.find_next('div', id='doubletableau')
        if double_tableau:
            tables = double_tableau.find_all('table')
            if len(tables) >= 2:
                main_export_products_table = clean_table(tables[0])
                main_import_products_table = clean_table(tables[1])

    # 5. Main Services (tables with class 'tableau1' and 'tableau2' after 'Main Services' h2)
    main_services_section = soup.find('h2', string=lambda t: t and 'Main Services' in t)
    main_export_services_table = main_import_services_table = ''
    if main_services_section:
        double_tableau = main_services_section.find_next('div', id='doubletableau')
        if double_tableau:
            tables = double_tableau.find_all('table')
            if len(tables) >= 2:
                main_export_services_table = clean_table(tables[0])
                main_import_services_table = clean_table(tables[1])

    # 6. Exchange Rate System (dl.informations after 'Exchange Rate System' h2)
    exchange_rate_section = soup.find('h2', string=lambda t: t and 'Exchange Rate System' in t)
    exchange_rate_dl = ''
    if exchange_rate_section:
        dl = exchange_rate_section.find_next('dl', class_='informations')
        if dl:
            exchange_rate_dl = str(dl)

    # 7. Monetary Indicators Table (last table on the page)
    monetary_indicators_table = ''
    all_tables = soup.find_all('table')
    if all_tables:
        monetary_indicators_table = str(all_tables[-1])

    return {
        'intro_text': intro_text,
        'tables_html': tables_html,
        'main_customers_table': main_customers_table,
        'main_suppliers_table': main_suppliers_table,
        'main_export_products_table': main_export_products_table,
        'main_import_products_table': main_import_products_table,
        'main_export_services_table': main_export_services_table,
        'main_import_services_table': main_import_services_table,
        'exchange_rate_dl': exchange_rate_dl,
        'monetary_indicators_table': monetary_indicators_table
    }


def scrape_santander_import_export_flows(driver, product_hs6, origin_code, destination_code):
    """
    Scrapes the Import and Export Flows tables from SantanderTrade for the given product and country codes.
    Returns a dict with 'export_table_html' and 'import_table_html'.
    """
    import time
    from bs4 import BeautifulSoup
    base_url = (
        "https://santandertrade.com/en/portal/analyse-markets/import-export-flow?"
        "flow={flow}&code={product_hs6}&csrf=1d983ea59d8173deee811d9540338a83&reporter={origin}&partners={destination}"
    )
    results = {}
    for flow in ["export", "import"]:
        url = base_url.format(
            flow=flow,
            product_hs6=product_hs6,
            origin=origin_code,
            destination=destination_code
        )
        print(f"Navigating to {flow} flow URL: {url}")
        driver.get(url)
        try:
            # Wait for the table to be present
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="ief_wrapper"]/div[2]/div[1]/div[2]/table'))
            )
            time.sleep(1)  # Let the table fully render
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            table = soup.select_one('#ief_wrapper > div:nth-of-type(2) > div:nth-of-type(1) > div:nth-of-type(2) > table')
            if table:
                # Clean table: remove last row if it's a summary, convert <a> to plain text
                rows = table.find_all('tr')
                if len(rows) > 1:
                    last_row = rows[-1]
                    if 'Total' in last_row.get_text() or 'total' in last_row.get_text():
                        last_row.decompose()
                for a in table.find_all('a'):
                    a.replace_with(a.get_text(strip=True))
                results[f'{flow}_table_html'] = str(table)
            else:
                results[f'{flow}_table_html'] = '<p>No data table found for this flow.</p>'
        except Exception as e:
            print(f"Error scraping {flow} flow table: {e}")
            results[f'{flow}_table_html'] = f'<p>Error scraping {flow} flow table: {e}</p>'
    return results


def scrape_santander_reaching_consumers(driver, formatted_country_name):
    """
    Navigates to the country's 'reaching-the-consumers' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/reaching-the-consumers"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        # Get navigation anchors section if present
        anchors_section = ""
        anchors_p = main.find('p', id='ancres')
        if anchors_p:
            anchors_section = str(anchors_p)

        # Consumer Profile section (anchor id: consumer or reaching)
        consumer_profile_section = get_section_by_anchor('consumer')
        if not consumer_profile_section:
            consumer_profile_section = get_section_by_anchor('reaching')

        # Marketing opportunities section (anchor id: marketing)
        marketing_opportunities_section = get_section_by_anchor('marketing')

        # Extract update date if present
        update_span = main.find('span', string=lambda t: t and 'Latest Update' in t)
        update_date = ''
        if update_span:
            update_date = update_span.find_next(string=True)
        else:
            droits = main.find('p', class_='droits')
            if droits:
                update_date = droits.get_text(strip=True)

        return {
            'anchors_section': anchors_section,
            'consumer_profile_section': consumer_profile_section,
            'marketing_opportunities_section': marketing_opportunities_section,
            'update_date': update_date,
            'raw_html': str(main)  # For debugging or further parsing
        }
    except Exception as e:
        print(f"Error scraping Santander Reaching the Consumer for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Reaching the Consumer for {formatted_country_name}: {str(e)}'}


def scrape_santander_distributing_product(driver, formatted_country_name):
    """
    Navigates to the country's 'distributing-a-product' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/distributing-a-product"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        # Get navigation anchors section if present
        anchors_section = ""
        anchors_p = main.find('p', id='ancres')
        if anchors_p:
            anchors_section = str(anchors_p)

        # Distribution section (anchor id: distribution)
        distribution_section = get_section_by_anchor('distribution')

        # Distance selling section (anchor id: distance_selling)
        distance_selling_section = get_section_by_anchor('distance_selling')

        # Extract update date if present
        update_span = main.find('span', string=lambda t: t and 'Latest Update' in t)
        update_date = ''
        if update_span:
            update_date = update_span.find_next(string=True)
        else:
            droits = main.find('p', class_='droits')
            if droits:
                update_date = droits.get_text(strip=True)

        return {
            'anchors_section': anchors_section,
            'distribution_section': distribution_section,
            'distance_selling_section': distance_selling_section,
            'update_date': update_date,
            'raw_html': str(main)  # For debugging or further parsing
        }
    except Exception as e:
        print(f"Error scraping Santander Distributing a Product for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Distributing a Product for {formatted_country_name}: {str(e)}'}


def scrape_santander_identify_suppliers(driver, formatted_country_name):
    """
    Navigates to the country's 'identify-suppliers' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/indentify-suppliers"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            for span in section_soup.find_all('span'):
                if span.string and ('All Rights Reserved' in span.string or 'Latest Update' in span.string):
                    span.decompose()
            return str(section_soup)

        # Get the main module section - this contains all the supplier identification data
        main_module_section = ""
        main_module = main.find('a', id='atlas__doing-business__1-acheter_industrie')
        if main_module:
            # Get all content following this anchor until the end
            content_parts = []
            current = main_module.find_next_sibling()
            while current:
                # Stop if we hit another major anchor or section
                if current.name == 'a' and current.has_attr('id') and 'atlas__' in current.get('id', ''):
                    break
                content_parts.append(str(current))
                current = current.find_next_sibling()
            
            main_module_section = ''.join(content_parts)
            # Clean up the section
            section_soup = BeautifulSoup(main_module_section, 'html.parser')
            # Remove scripts, feedback forms, and footer elements
            for script in section_soup.find_all('script'):
                script.decompose()
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            main_module_section = str(section_soup)

        # Extract specific subsections from the main content
        production_types_section = ""
        marketplaces_section = ""
        trade_shows_section = ""
        manufacturers_section = ""

        # Parse the main module to extract subsections
        if main_module_section:
            section_soup = BeautifulSoup(main_module_section, 'html.parser')
            
            # Find sections by their dt/dd structure or headings
            for dl in section_soup.find_all('dl', class_='informations'):
                for dt in dl.find_all('dt'):
                    dt_text = dt.get_text().lower()
                    if 'type of production' in dt_text:
                        # Get this dt and its dd
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            production_types_section = str(dt) + str(dd)
                    elif 'marketplaces' in dt_text:
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            marketplaces_section = str(dt) + str(dd)
                    elif 'trade shows' in dt_text or 'upcoming' in dt_text:
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            trade_shows_section += str(dt) + str(dd)
            
            # Find manufacturers section by h2 heading
            for h2 in section_soup.find_all('h2'):
                if 'manufacturer' in h2.get_text().lower():
                    # Get content after this heading
                    content_parts = [str(h2)]
                    current = h2.find_next_sibling()
                    while current and current.name != 'h2':
                        content_parts.append(str(current))
                        current = current.find_next_sibling()
                    manufacturers_section = ''.join(content_parts)

        # Extract update date if present
        update_span = main.find('span', string=lambda t: t and 'Latest Update' in t)
        update_date = ''
        if update_span:
            update_date = update_span.find_next(string=True)
        else:
            droits = main.find('p', class_='droits')
            if droits:
                update_date = droits.get_text(strip=True)

        return {
            'main_module_section': main_module_section,
            'production_types_section': production_types_section,
            'marketplaces_section': marketplaces_section,
            'trade_shows_section': trade_shows_section,
            'manufacturers_section': manufacturers_section,
            'update_date': update_date,
            'raw_html': str(main)  # For debugging or further parsing
        }
    except Exception as e:
        print(f"Error scraping Santander Identify Suppliers for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Identify Suppliers for {formatted_country_name}: {str(e)}'}


def scrape_santander_trade_compliance(driver, formatted_country_name):
    """
    Navigates to the country's 'trade-compliance' page and scrapes all major sections as structured data.
    Returns a dict with all fields needed for the report.
    """
    target_url = f"https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/trade-compliance"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")

        def get_section_by_anchor(anchor_id):
            anchor = main.find('a', id=anchor_id)
            if not anchor:
                return ''
            html_parts = []
            sib = anchor.find_next_sibling()
            while sib and not (sib.name == 'a' and sib.has_attr('id')):
                html_parts.append(str(sib))
                sib = sib.find_next_sibling()
            section_html = ''.join(html_parts)
            section_soup = BeautifulSoup(section_html, 'html.parser')
            # Remove <p class="retour"> and <a href="#top"> and <a href="#haut">
            for retour in section_soup.find_all('p', class_='retour'):
                retour.decompose()
            for a in section_soup.find_all('a', href='#top'):
                a.decompose()
            for a in section_soup.find_all('a', href='#haut'):
                a.decompose()
            # Remove feedback and footer elements
            for remarque in section_soup.find_all('span', class_='remarque-atlas'):
                parent = remarque.find_parent('p', class_='contact-atlas')
                if parent:
                    parent.decompose()
                else:
                    remarque.decompose()
            for droits in section_soup.find_all('p', class_='droits'):
                droits.decompose()
            # Remove any script tags
            for script in section_soup.find_all('script'):
                script.decompose()
            # Remove any form elements
            for form in section_soup.find_all('div', id='formulaire_remarque'):
                form.decompose()
            for contact in section_soup.find_all('div', id='contient-contact-atlas'):
                contact.decompose()
            return str(section_soup).strip()

        # Extract the main trade compliance section
        trade_compliance_section = get_section_by_anchor('atlas__doing-business__1-commerce_regles')

        # Get update date
        update_date = ''
        droits_p = main.find('p', class_='droits')
        if droits_p:
            date_span = droits_p.find('span')
            if date_span:
                update_date = date_span.get_text(strip=True)

        return {
            'trade_compliance_section': trade_compliance_section,
            'update_date': update_date
        }

    except Exception as e:
        print(f"Error scraping Trade Compliance for {formatted_country_name}: {e}")
        return {'error': f'Error scraping Trade Compliance for {formatted_country_name}: {str(e)}'}


def scrape_santander_business_directories(driver, industry_name, country_name):
    """
    Navigates to the business directories page, fills the form with industry and country,
    and scrapes all business directory results.
    Returns a dict with all directories data.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    target_url = "https://santandertrade.com/en/portal/reach-business-counterparts/business-directories"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        # Wait for the form to be present
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "code_secteur")))
        
        # Select industry by visible text
        industry_select = Select(driver.find_element(By.ID, "code_secteur"))
        try:
            industry_select.select_by_visible_text(industry_name)
            print(f"Selected industry by name: {industry_name}")
        except Exception as e:
            print(f"Could not select industry '{industry_name}': {e}")
            return {'error': f'Could not find industry option for: {industry_name}'}
        
        # Select country/geographical area by visible text
        country_select = Select(driver.find_element(By.ID, "pays_recherche"))
        try:
            country_select.select_by_visible_text(country_name)
            print(f"Selected country by name: {country_name}")
        except Exception:
            # If exact match doesn't work, try to find by partial text match
            found = False
            for option in country_select.options:
                if country_name.upper() in option.text.upper():
                    country_select.select_by_visible_text(option.text)
                    print(f"Selected country by partial match: {option.text}")
                    found = True
                    break
            if not found:
                # Fallback: select "World" if specific country not found
                try:
                    country_select.select_by_visible_text('World')
                    print(f"Could not find country '{country_name}', selected 'World' as fallback")
                except:
                    print(f"Could not find country option for: {country_name}")
                    return {'error': f'Could not find country option for: {country_name}'}
        
        # Click search button
        search_button = driver.find_element(By.ID, "bouton")
        search_button.click()
        print("Search button clicked")
        
        # Wait for results to load
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "zone_de_resultats")))
        time.sleep(3)  # Additional wait for dynamic content
        
        # Get page source and parse with BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract results summary
        results_summary = ""
        summary_elem = soup.find('h2', class_='no-bg-bd')
        if summary_elem:
            results_summary = summary_elem.get_text(strip=True)
        
        # Extract all business directories
        directories = []
        directory_cards = soup.find_all('div', class_='card-service-result')
        
        for card in directory_cards:
            directory = {}
            
            # Extract name and URL
            link_elem = card.find('a', class_='lien-externe')
            if link_elem:
                directory['name'] = link_elem.get_text(strip=True)
                directory['url'] = link_elem.get('href', '')
            
            # Extract geographical coverage
            geo_elem = card.find('div', class_='text-right')
            if geo_elem:
                geo_text = geo_elem.get_text(strip=True)
                directory['geographical_coverage'] = geo_text.replace('🌐', '').strip()
            
            # Extract description (text between name and sectors line)
            description_parts = []
            for elem in card.children:
                if hasattr(elem, 'get_text'):
                    text = elem.get_text(strip=True)
                    if text and not elem.find('a') and not elem.find('i', class_='fa-industry'):
                        if text not in [directory.get('name', ''), directory.get('geographical_coverage', '')]:
                            description_parts.append(text)
            directory['description'] = ' '.join(description_parts)
            
            # Extract sector
            sector_elem = card.find('div', class_='sectors-line')
            if sector_elem:
                directory['sector'] = sector_elem.get_text(strip=True).replace('🏭', '').strip()
            
            # Extract tags/categories
            tags = []
            tag_elems = card.find_all('div', class_='tag-style')
            for tag_elem in tag_elems:
                spans = tag_elem.find_all('span')
                for span in spans:
                    tags.append(span.get_text(strip=True))
            directory['tags'] = tags
            
            if directory.get('name'):  # Only add if we have a name
                directories.append(directory)
        
        # No longer extracting section headers (categories) as requested
        
        # Extract navigation/pagination info
        pagination = []
        pagination_elem = soup.find('div', class_='ordre-affichage')
        if pagination_elem:
            pagination_links = pagination_elem.find_all('a', class_='pagination-lien')
            for link in pagination_links:
                pagination.append(link.get_text(strip=True))
        
        return {
            'results_summary': results_summary,
            'total_directories': len(directories),
            'directories': directories,
            'pagination': pagination,
            'search_params': {
                'industry_name': industry_name,
                'country_name': country_name
            }
        }

    except Exception as e:
        print(f"Error scraping Business Directories: {e}")
        return {'error': f'Error scraping Business Directories: {str(e)}'}


def scrape_santander_professional_associations(driver, industry_name, country_name):
    """
    Navigates to the professional associations page, fills the form with industry and country,
    and scrapes all professional association results.
    Returns a dict with all associations data.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    target_url = "https://santandertrade.com/en/portal/reach-business-counterparts/professional-associations"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        # Wait for the form to be present
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//*[@id='federation_secteur']")))
        
        # Select industry by visible text
        industry_select = Select(driver.find_element(By.XPATH, "//*[@id='federation_secteur']"))
        try:
            industry_select.select_by_visible_text(industry_name)
            print(f"Selected industry by name: {industry_name}")
        except Exception as e:
            print(f"Could not select industry '{industry_name}': {e}")
            return {'error': f'Could not find industry option for: {industry_name}'}
        
        # Select country/geographical area by visible text
        country_select = Select(driver.find_element(By.XPATH, "//*[@id='critere_pays']"))
        try:
            country_select.select_by_visible_text(country_name)
            print(f"Selected country by name: {country_name}")
        except Exception:
            # If exact match doesn't work, try to find by partial text match
            found = False
            for option in country_select.options:
                if country_name.upper() in option.text.upper():
                    country_select.select_by_visible_text(option.text)
                    print(f"Selected country by partial match: {option.text}")
                    found = True
                    break
            if not found:
                print(f"Could not find country option for: {country_name}")
                return {'error': f'Could not find country option for: {country_name}'}
        
        # Click search button
        search_button = driver.find_element(By.XPATH, "//*[@id='bouton']")
        search_button.click()
        print("Search button clicked")
        
        # Wait for results to load
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "contenu-contenu")))
        time.sleep(4)  # Additional wait for dynamic content
        
        # Parse the results
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")
        
        if not main:
            return {'error': 'Could not find main content area'}
        
        # Extract results summary
        results_summary = ""
        summary_elem = soup.find('h2', class_='no-bg-bd')
        if summary_elem:
            results_summary = summary_elem.get_text(strip=True)
        
        # Extract all professional associations
        associations = []
        association_cards = soup.find_all('div', class_='card-service-result')
        
        for card in association_cards:
            association = {}
            
            # Extract name and URL
            link_elem = card.find('a', class_='lien-externe')
            if link_elem:
                association['name'] = link_elem.get_text(strip=True)
                association['url'] = link_elem.get('href', '')
            
            # Extract geographical coverage
            geo_elem = card.find('div', class_='text-right')
            if geo_elem:
                geo_text = geo_elem.get_text(strip=True)
                # Remove the globe icon and clean up
                association['geographical_coverage'] = geo_text.replace('🌐', '').strip()
            
            # Extract full name/description (text between name and sectors line)
            description_parts = []
            for elem in card.children:
                if hasattr(elem, 'get_text'):
                    text = elem.get_text(strip=True)
                    # Skip if it's the name, geographical coverage, or sectors line
                    if (text and 
                        not elem.find('a') and 
                        not elem.find('i', class_='fa-industry') and
                        not elem.find('i', class_='fa-globe') and
                        text not in [association.get('name', ''), association.get('geographical_coverage', '')]):
                        description_parts.append(text)
            association['description'] = ' '.join(description_parts)
            
            # Extract sector
            sector_elem = card.find('div', class_='sectors-line')
            if sector_elem:
                sector_text = sector_elem.get_text(strip=True)
                # Remove the industry icon and clean up
                association['sector'] = sector_text.replace('🏭', '').strip()
            
            if association.get('name'):  # Only add if we have a name
                associations.append(association)
        
        # Extract navigation/pagination info
        pagination = []
        pagination_elem = soup.find('div', class_='ordre-affichage')
        if pagination_elem:
            pagination_links = pagination_elem.find_all('a', class_='pagination-lien')
            for link in pagination_links:
                pagination.append(link.get_text(strip=True))
        
        return {
            'results_summary': results_summary,
            'total_associations': len(associations),
            'associations': associations,
            'pagination': pagination,
            'search_params': {
                'industry_name': industry_name,
                'country_name': country_name
            }
        }

    except Exception as e:
        print(f"Error scraping Professional Associations: {e}")
        return {'error': f'Error scraping Professional Associations: {str(e)}'}


def scrape_santander_online_marketplaces(driver, industry_name, country_name):
    """
    Navigates to the online marketplaces page, fills the form with industry and country,
    and scrapes all online marketplace results.
    Returns a dict with all marketplaces data.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    target_url = "https://santandertrade.com/en/portal/reach-business-counterparts/online-marketplaces"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        # Wait for the form to be present
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//*[@id='place_de_marche_secteur']")))
        
        # Select industry by visible text
        industry_select = Select(driver.find_element(By.XPATH, "//*[@id='place_de_marche_secteur']"))
        try:
            industry_select.select_by_visible_text(industry_name)
            print(f"Selected industry by name: {industry_name}")
        except Exception as e:
            print(f"Could not select industry '{industry_name}': {e}")
            return {'error': f'Could not find industry option for: {industry_name}'}
        
        # Select country/geographical area by visible text
        country_select = Select(driver.find_element(By.XPATH, "//*[@id='place_de_marche_zone']"))
        try:
            country_select.select_by_visible_text(country_name)
            print(f"Selected country by name: {country_name}")
        except Exception:
            # If exact match doesn't work, try to find by partial text match
            found = False
            for option in country_select.options:
                if country_name.upper() in option.text.upper():
                    country_select.select_by_visible_text(option.text)
                    print(f"Selected country by partial match: {option.text}")
                    found = True
                    break
            if not found:
                print(f"Could not find country option for: {country_name}")
                return {'error': f'Could not find country option for: {country_name}'}
        
        # Click search button
        search_button = driver.find_element(By.XPATH, "//*[@id='form-submit']")
        search_button.click()
        print("Search button clicked")
        
        # Wait for results to load
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "contenu-contenu")))
        time.sleep(4)  # Additional wait for dynamic content
        
        # Parse the results
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        main = soup.find(id="contenu-contenu")
        
        if not main:
            return {'error': 'Could not find main content area'}
        
        # Extract results summary
        results_summary = ""
        summary_elem = soup.find('h2', class_='no-bg-bd')
        if summary_elem:
            results_summary = summary_elem.get_text(strip=True)
        
        # Extract all online marketplaces
        marketplaces = []
        marketplace_cards = soup.find_all('div', class_='card-service-result')
        
        for card in marketplace_cards:
            marketplace = {}
            
            # Extract name and URL
            link_elem = card.find('a', class_='lien-externe')
            if link_elem:
                marketplace['name'] = link_elem.get_text(strip=True)
                marketplace['url'] = link_elem.get('href', '')
            
            # Extract geographical coverage
            geo_elem = card.find('div', class_='text-right')
            if geo_elem:
                geo_text = geo_elem.get_text(strip=True)
                marketplace['geographical_coverage'] = geo_text.replace('🌐', '').strip()
            
            # Extract description (text between name and sectors line)
            description_parts = []
            for elem in card.children:
                if hasattr(elem, 'get_text'):
                    text = elem.get_text(strip=True)
                    if text and not elem.find('a') and not elem.find('i', class_='fa-industry'):
                        if text not in [marketplace.get('name', ''), marketplace.get('geographical_coverage', '')]:
                            description_parts.append(text)
            marketplace['description'] = ' '.join(description_parts)
            
            # Extract sector
            sector_elem = card.find('div', class_='sectors-line')
            if sector_elem:
                marketplace['sector'] = sector_elem.get_text(strip=True).replace('🏭', '').strip()
            
            # Extract tags/categories
            tags = []
            tag_elems = card.find_all('div', class_='tag-style')
            for tag_elem in tag_elems:
                spans = tag_elem.find_all('span')
                for span in spans:
                    tags.append(span.get_text(strip=True))
            marketplace['tags'] = tags
            
            # Extract additional marketplace-specific information
            # Look for language information
            lang_elem = card.find('span', class_='language')
            if lang_elem:
                marketplace['language'] = lang_elem.get_text(strip=True)
            
            # Look for marketplace type (B2B, B2C, etc.)
            type_elem = card.find('span', class_='marketplace-type')
            if type_elem:
                marketplace['type'] = type_elem.get_text(strip=True)
            
            if marketplace.get('name'):  # Only add if we have a name
                marketplaces.append(marketplace)
        
        # Extract navigation/pagination info
        pagination = []
        pagination_elem = soup.find('div', class_='ordre-affichage')
        if pagination_elem:
            pagination_links = pagination_elem.find_all('a', class_='pagination-lien')
            for link in pagination_links:
                pagination.append(link.get_text(strip=True))
        
        return {
            'results_summary': results_summary,
            'total_marketplaces': len(marketplaces),
            'marketplaces': marketplaces,
            'pagination': pagination,
            'search_params': {
                'industry_name': industry_name,
                'country_name': country_name
            }
        }

    except Exception as e:
        print(f"Error scraping Online Marketplaces: {e}")
        return {'error': f'Error scraping Online Marketplaces: {str(e)}'}


def scrape_santander_trade_shows(driver, sector_code, destination_country_iso3n):
    """
    Scrapes the Trade Shows section from SantanderTrade for the given sector and country ISO3N code.
    Returns a list of trade shows, each as a dict with keys: 'name', 'url', 'location', 'date', 'description', 'sectors'.
    """
    import os
    import json
    from bs4 import BeautifulSoup
    import urllib.parse
    import time

    base_url = (
        "https://santandertrade.com/en/portal/reach-business-counterparts/trade-shows?"
        "todo=valider&csrf=1e9e01a18167ba7a1908d67985cb0d4d&keyword=&code_secteur={sector_code}&pays_recherche={country_code}#result"
    )
    url = base_url.format(sector_code=sector_code, country_code=destination_country_iso3n)
    print(f"Navigating to Trade Shows URL: {url}")
    driver.get(url)
    # Click the form-submit button if present
    try:
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="form-submit"]'))
        )
        driver.execute_script("arguments[0].click();", submit_button)
        time.sleep(2)
    except Exception as e:
        print(f"Could not find or click the Trade Shows submit button: {e}")
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    shows = []
    results_div = soup.find('div', id='resultats')
    if not results_div:
        print("No trade shows found on the page.")
        return shows

    for card in results_div.find_all('div', class_='desc-resultats'):
        # Name and URL
        name_tag = card.find('div', class_='titre-haut-salon').find('a')
        name = name_tag.get_text(strip=True) if name_tag else ''
        url = urllib.parse.urljoin("https://santandertrade.com", name_tag['href']) if name_tag and name_tag.has_attr('href') else ''
        # Location
        country_tag = card.find('div', class_='country')
        location = country_tag.get_text(strip=True) if country_tag else ''
        # Date
        type_tag = card.find('div', class_='type')
        date = type_tag.get_text(strip=True) if type_tag else ''
        # Description
        desc_tag = card.find('div', class_='resumer')
        description = desc_tag.get_text(strip=True) if desc_tag else ''
        # Sectors
        sectors_tag = card.find('div', class_='sectors-line')
        sectors = ''
        if sectors_tag:
            sectors_span = sectors_tag.find('span', itemprop='name')
            if sectors_span:
                sectors = sectors_span.get_text(strip=True)
        shows.append({
            'name': name,
            'url': url,
            'location': location,
            'date': date,
            'description': description,
            'sectors': sectors
        })
    return shows


def scrape_santander_blacklisted_companies(driver, entity_name):
    """
    Scrapes blacklisted companies and vessels data from Santander Trade
    """
    target_url = "https://santandertrade.com/en/portal/reach-business-counterparts/black-listed-companies"
    print(f"Navigating to: {target_url}")
    driver.get(target_url)
    
    try:
        # Wait for the form to be present
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//*[@id='nom_contact']")))
        
        # Get the entity name input field
        entity_element = driver.find_element(By.XPATH, "//*[@id='nom_contact']")
        
        # Clear and enter the entity name
        try:
            entity_element.clear()
            entity_element.send_keys(entity_name)
            print(f"Entered entity name: {entity_name}")
            
            # Wait a moment for any autocomplete to appear
            time.sleep(2)
            
            # Try to find and click on autocomplete suggestion if available
            try:
                # Look for common autocomplete dropdown patterns
                suggestions = driver.find_elements(By.CSS_SELECTOR, ".ui-menu-item, .autocomplete-item, .suggestion-item")
                if suggestions:
                    for suggestion in suggestions:
                        if entity_name.upper() in suggestion.text.upper():
                            suggestion.click()
                            print(f"Clicked autocomplete suggestion: {suggestion.text}")
                            break
                else:
                    print("No autocomplete suggestions found, proceeding with typed value")
            except:
                # If no autocomplete found, just proceed with typed value
                print("No autocomplete suggestions found, proceeding with typed value")
                
        except Exception as e:
            print(f"Could not enter entity name: {e}")
            return {'error': f'Could not enter entity name: {str(e)}'}
        
        # Click search button
        search_button = driver.find_element(By.XPATH, "//*[@id='bouton']")
        search_button.click()
        print("Search button clicked")
        search_button = driver.find_element(By.XPATH, "//*[@id='bouton']")
        search_button.click()
        print("need to click the button again inside the container")
        
        # Wait for results to load - this takes time so we wait for the specific element
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//*[@id='resultats_gtm']")))
        time.sleep(5)  # Additional wait for dynamic content to fully load
        
        # Get page source and parse with BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find the results container
        results_container = soup.find(id="resultats_gtm")
        if not results_container:
            print("Could not find results container")
            return {'error': 'Could not find results content'}
        
        # Extract results summary from header
        results_summary = ""
        header_elem = results_container.find('li', class_='fond-titre')
        if header_elem:
            # Get the column headers
            titre_spans = header_elem.find_all('span', class_=['titre-1', 'titre-2'])
            if titre_spans:
                headers = [span.get_text(strip=True) for span in titre_spans]
                results_summary = f"Results showing columns: {' | '.join(headers)}"
        
        # Extract blacklisted entities data
        blacklisted_entities = []
        
        # Look for entity items in the results
        entity_items = results_container.find_all('li', class_='liste-titre')
        
        for item in entity_items:
            entity_data = {}
            
            # Get the link element
            link_elem = item.find('a')
            if link_elem:
                # Build full URL if it's relative
                href = link_elem.get('href', '')
                if href.startswith('/'):
                    entity_data['url'] = f"https://santandertrade.com{href}"
                else:
                    entity_data['url'] = href
                
                # Extract data-entity attribute (can contain multiple IDs separated by commas)
                entity_data['data_entity'] = link_elem.get('data-entity', '')
                
                # Extract entity name
                name_span = link_elem.find('span', class_='nom-desc')
                if name_span:
                    entity_data['name'] = name_span.get_text(strip=True)
                
                # Extract blacklisted by information
                blacklisted_by_span = link_elem.find('span', class_='pays-desc')
                if blacklisted_by_span:
                    # Create a copy to avoid modifying the original
                    blacklisted_by_copy = blacklisted_by_span.__copy__()
                    # Remove mobile title if present
                    mobile_title = blacklisted_by_copy.find('span', class_='titre-mobile')
                    if mobile_title:
                        mobile_title.decompose()
                    entity_data['blacklisted_by'] = blacklisted_by_copy.get_text(strip=True)
                
                # Extract tracking ID attribute
                tracking_id = link_elem.get('id_tracking', '')
                if tracking_id:
                    entity_data['tracking_id'] = tracking_id
            
            if entity_data.get('name'):
                blacklisted_entities.append(entity_data)
        
        print(f"Found {len(blacklisted_entities)} blacklisted entities")
        
        # Check for pagination
        pagination = {}
        pagination_elem = results_container.find('div', class_='pagination') or soup.find('div', class_='pagination')
        if pagination_elem:
            pagination['has_pagination'] = True
            page_links = pagination_elem.find_all('a')
            pagination['total_pages'] = len(page_links)
        else:
            pagination['has_pagination'] = False
        
        return {
            'results_summary': results_summary,
            'total_entities': len(blacklisted_entities),
            'blacklisted_entities': blacklisted_entities,
            'pagination': pagination,
            'search_params': {
                'entity_name': entity_name
            }
        }
        
    except Exception as e:
        driver.save_screenshot("/tmp/blacklisted_companies.png")
        print(f"Error scraping Blacklisted Companies: {e}")
        return {'error': f'Error scraping Blacklisted Companies: {str(e)}'}

def scrape_santander_shipping_documents(driver, import_country_name, export_country_name, manufacture_country_name, transport_mode, shipment_date, document_type):
    """
    Scrapes Santander Trade shipping documents data.
    
    Args:
        driver: Selenium WebDriver instance
        import_country_name: Name of the import country
        export_country_name: Name of the export country  
        manufacture_country_name: Name of the manufacture country
        transport_mode: Transport mode ('Air', 'Sea', or 'Land')
        shipment_date: Shipment date in dd/MM/YYYY format
        document_type: Document type ('country_specific' or 'country_product_specific')
    
    Returns:
        dict: Scraped shipping documents data
    """
    try:
        print("Navigating to Santander Trade shipping documents page...")
        driver.get("https://santandertrade.com/en/portal/international-shipments/shipping-documents")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='pays_import']"))
        )
        
        print("Selecting import country...")
        import_dropdown = Select(driver.find_element(By.XPATH, "//*[@id='pays_import']"))
        try:
            import_dropdown.select_by_visible_text(import_country_name)
            print(f"Selected import country: {import_country_name}")
        except:
            # Try partial match
            for option in import_dropdown.options:
                if import_country_name.lower() in option.text.lower():
                    import_dropdown.select_by_visible_text(option.text)
                    print(f"Selected import country (partial match): {option.text}")
                    break
            else:
                print(f"Could not find import country: {import_country_name}")
        
        print("Selecting export country...")
        export_dropdown = Select(driver.find_element(By.XPATH, "//*[@id='pays_export']"))
        try:
            export_dropdown.select_by_visible_text(export_country_name)
            print(f"Selected export country: {export_country_name}")
        except:
            # Try partial match
            for option in export_dropdown.options:
                if export_country_name.lower() in option.text.lower():
                    export_dropdown.select_by_visible_text(option.text)
                    print(f"Selected export country (partial match): {option.text}")
                    break
            else:
                print(f"Could not find export country: {export_country_name}")
        
        print("Selecting manufacture country...")
        # Note: User mentioned XPath was //*[@id="pays_export"] but this seems wrong for manufacture
        # Using //*[@id="pays_manufacture"] as it makes more sense, but may need correction based on actual page
        try:
            manufacture_dropdown = Select(driver.find_element(By.XPATH, '//*[@id="pays_origine"]'))
        except:
            # Fallback to the XPath mentioned in user requirements (which may be incorrect)
            print("Warning: //*[@id='pays_manufacture'] not found, trying //*[@id='pays_export'] as fallback")
            manufacture_dropdown = Select(driver.find_element(By.XPATH, "//*[@id='pays_export']"))
        try:
            manufacture_dropdown.select_by_visible_text(manufacture_country_name)
            print(f"Selected manufacture country: {manufacture_country_name}")
        except:
            # Try partial match
            for option in manufacture_dropdown.options:
                if manufacture_country_name.lower() in option.text.lower():
                    manufacture_dropdown.select_by_visible_text(option.text)
                    print(f"Selected manufacture country (partial match): {option.text}")
                    break
            else:
                print(f"Could not find manufacture country: {manufacture_country_name}")
        
        print(f"Selecting transport mode: {transport_mode}")
        if transport_mode.lower() == 'air':
            driver.find_element(By.XPATH, "//*[@id='mot_air']").click()
        elif transport_mode.lower() == 'sea':
            driver.find_element(By.XPATH, "//*[@id='mot_sea']").click()
        elif transport_mode.lower() == 'land':
            driver.find_element(By.XPATH, "//*[@id='mot_land']").click()
        
        print(f"Entering shipment date: {shipment_date}")
        date_input = driver.find_element(By.XPATH, "//*[@id='date_requete']")
        date_input.clear()
        date_input.send_keys(shipment_date)
        
        print(f"Selecting document type: {document_type}")
        if document_type == 'country_specific':
            driver.find_element(By.XPATH, "//*[@id='type_recherche_1']").click()
        else:  # country_product_specific
            driver.find_element(By.XPATH, "//*[@id='type_recherche_2']").click()
        
        print("Clicking search button...")
        search_button = driver.find_element(By.XPATH, "//*[@id='bouton']")
        driver.execute_script("arguments[0].click();", search_button)
        
        # Wait for results to load
        print("Waiting for results to load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "encart-produit"))
        )
        
        # Scrape export documents first
        print("Scraping export documents...")
        time.sleep(2)
        
        # Expand all export document categories by clicking on headers
        try:
            export_headers = driver.find_elements(By.XPATH, "//div[@id='choix_hs']//thead//th")
            print(f"Found {len(export_headers)} export category headers to expand")
            for header in export_headers:
                try:
                    driver.execute_script("arguments[0].click();", header)
                    time.sleep(0.5)  # Small delay between clicks
                except:
                    pass
        except Exception as e:
            print(f"Warning: Could not expand export categories: {e}")
        
        export_documents = scrape_document_section(driver, "export")

        
        # Click on import documents tab
        print("Switching to import documents tab...")
        import_tab = driver.find_element(By.XPATH, '//*[@id="lien-onglet-keyword"]')
        import_tab.click()
        
        # Wait for import section to load and become visible
        print("Waiting for import section to become visible...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "choix_keyword"))
        )
        time.sleep(3)  # Additional wait for content to fully load
        
        # Expand all import document categories by clicking on headers
        try:
            import_headers = driver.find_elements(By.XPATH, "//div[@id='choix_keyword']//thead//th")
            print(f"Found {len(import_headers)} import category headers to expand")
            for header in import_headers:
                try:
                    driver.execute_script("arguments[0].click();", header)
                    time.sleep(0.5)  # Small delay between clicks
                except:
                    pass
        except Exception as e:
            print(f"Warning: Could not expand import categories: {e}")
        
        # Scrape import documents
        print("Scraping import documents...")
        import_documents = scrape_document_section(driver, "import")
        
        return {
            'results_summary': f'Found {len(export_documents)} export documents and {len(import_documents)} import documents',
            'total_export_documents': len(export_documents),
            'total_import_documents': len(import_documents),
            'export_documents': export_documents,
            'import_documents': import_documents,
            'search_params': {
                'import_country_name': import_country_name,
                'export_country_name': export_country_name,
                'manufacture_country_name': manufacture_country_name,
                'transport_mode': transport_mode,
                'shipment_date': shipment_date,
                'document_type': document_type
            }
        }
        
    except Exception as e:
        print(f"Error scraping Shipping Documents: {e}")
        return {
            'error': str(e),
            'results_summary': 'Error occurred during scraping',
            'total_export_documents': 0,
            'total_import_documents': 0,
            'export_documents': [],
            'import_documents': [],
            'search_params': {
                'import_country_name': import_country_name,
                'export_country_name': export_country_name,
                'manufacture_country_name': manufacture_country_name,
                'transport_mode': transport_mode,
                'shipment_date': shipment_date,
                'document_type': document_type
            }
        }

def scrape_document_section(driver, section_type):
    """
    Helper function to scrape documents from export or import section.
    
    Args:
        driver: Selenium WebDriver instance
        section_type: 'export' or 'import'
        
    Returns:
        list: List of scraped documents
    """
    documents = []
    
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find the specific section based on section_type
        if section_type == 'export':
            # Look for export section div
            section_div = soup.find('div', {'id': 'choix_hs'})
        else:  # import
            # Look for import section div
            section_div = soup.find('div', {'id': 'choix_keyword'})
        
        if not section_div:
            print(f"Warning: Could not find {section_type} section div")
            return documents
        
        # Check if the section is visible (not hidden)
        section_style = section_div.get('style', '')
        if 'display: none' in section_style:
            print(f"Warning: {section_type} section is hidden")
            return documents
        
        # Find tables within the specific section
        tables = section_div.find_all('table', class_='tableau_methode')
        print(f"Found {len(tables)} tables in {section_type} section")
        
        for table in tables:
            # Get the category header
            thead = table.find('thead')
            if thead:
                category_header = thead.find('th')
                category = category_header.get_text(strip=True) if category_header else 'Unknown Category'
            else:
                category = 'Unknown Category'
            
            print(f"Processing category: {category}")
            
            # Find all document rows in this table
            tbody = table.find('tbody')
            if tbody:
                # Don't skip hidden tbody - the content is there but hidden by CSS/JS
                # The page uses JavaScript to show/hide content dynamically
                rows = tbody.find_all('tr')
                
                for row in rows:
                    td = row.find('td', class_='agauche')
                    if td and td.get_text(strip=True):  # Skip empty rows
                        # Extract document name
                        doc_name_elem = td.find('strong')
                        doc_name = doc_name_elem.get_text(strip=True) if doc_name_elem else 'Unknown Document'
                        
                        # Skip if no document name found
                        if not doc_name or doc_name == 'Unknown Document':
                            continue
                        
                        # Extract download link
                        download_link = None
                        link_elem = td.find('a', class_='link-download')
                        if link_elem:
                            download_link = link_elem.get('href')
                        
                        # Extract description
                        description_elem = td.find('p', class_='doc-description-gtm')
                        description = description_elem.get_text(strip=True) if description_elem else ''
                        
                        # Extract source
                        source = ''
                        source_elem = td.find('em')
                        if source_elem:
                            source = source_elem.get_text(strip=True).replace('Source: ', '')
                        
                        documents.append({
                            'category': category,
                            'name': doc_name,
                            'description': description,
                            'download_link': download_link,
                            'source': source,
                            'section': section_type
                        })
                        
                        print(f"Found document: {doc_name}")
        
        print(f"Total found {len(documents)} documents in {section_type} section")
        return documents
        
    except Exception as e:
        print(f"Error scraping {section_type} documents: {e}")
        import traceback
        traceback.print_exc()
        return documents 