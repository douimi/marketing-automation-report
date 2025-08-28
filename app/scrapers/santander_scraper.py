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