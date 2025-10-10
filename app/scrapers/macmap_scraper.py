from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
import re
from flask import current_app

MACMAP_URL_TEMPLATE = "https://www.macmap.org/en//query/results?reporter={reporter}&partner={partner}&product={product}&level=6"

# Utility to clean MacMap HTML: remove <a>, <img>, and empty divs
def clean_macmap_html(html):
    if not html:
        return ''
    # Remove all <a ...>...</a> (See More, Learn more, and others)
    html = re.sub(r'<a [^>]*>.*?</a>', '', html, flags=re.DOTALL)
    # Remove all <div class="action-bar">...</div> (Learn more wrappers)
    html = re.sub(r'<div[^>]*class="[^"]*action-bar[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    # Remove all <img ...>
    html = re.sub(r'<img [^>]*>', '', html)
    # Remove all <i ...>...</i> that are not FontAwesome (i.e., not class="fa ...")
    html = re.sub(r'<i(?![^>]*fa)[^>]*>.*?</i>', '', html, flags=re.DOTALL)
    # Remove empty divs (divs with only whitespace or no content)
    html = re.sub(r'<div[^>]*>\s*</div>', '', html)
    # Remove multiple consecutive <br> tags
    html = re.sub(r'(<br\s*/?>\s*){2,}', '<br>', html)
    # Remove excessive whitespace
    html = re.sub(r'\s{2,}', ' ', html)
    return html.strip()

def parse_customs_tariffs_table(table):
    """Parse the customs tariffs table into a list of dicts."""
    tariffs = []
    if not table:
        return tariffs
    rows = table.find_all('tr')
    headers = [th.get_text(strip=True) for th in rows[0].find_all('th')] if rows else []
    for row in rows[1:]:
        cells = row.find_all(['td', 'th'])
        if not cells or len(cells) < 4:
            continue
        tariffs.append({
            'tariff_regime': cells[0].get_text(strip=True),
            'applied_tariff': cells[1].get_text(strip=True),
            'ave': cells[2].get_text(strip=True),
            'note': cells[3].get_text(strip=True)
        })
    return tariffs

def parse_regulatory_requirements_table(table):
    """Parse the regulatory requirements table into a list of dicts."""
    requirements = []
    if not table:
        return requirements
    rows = table.find_all('tr')
    for row in rows:
        wrapper = row.find('div', class_='measure-summary-wrapper')
        if not wrapper:
            continue
        code_span = wrapper.find('span')
        desc_div = wrapper.find('div', class_='measure-summary')
        count_div = row.find('div', class_='measure-count')
        code = code_span.get_text(strip=True) if code_span else ''
        desc = desc_div.get_text(strip=True) if desc_div else ''
        count = count_div.get_text(strip=True) if count_div else ''
        requirements.append({'code': code, 'description': desc, 'count': count})
    return requirements

def scrape_macmap_market_access_conditions(driver, reporter_iso3n, partner_iso3n, product_hs6):
    """
    Navigates to the MacMap Market Access Conditions page and scrapes all relevant data for the section.
    Returns a dict with all fields needed for the template (overview, customs tariffs, trade remedies, regulatory requirements, etc.).
    """
    url = MACMAP_URL_TEMPLATE.format(reporter=reporter_iso3n, partner=partner_iso3n, product=product_hs6)
    print(f"Navigating to: {url}")
    driver.get(url)
    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "results")))
        time.sleep(5)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Overview
        overview = soup.find('div', class_='overview-content')
        exporting_country = ''
        importing_country = ''
        product = ''
        if overview:
            summary = overview.find('div', class_='summary-row')
            if summary:
                groups = summary.find_all('div', class_='summary-group')
                for group in groups:
                    heading = group.find('div', class_='summary-heading')
                    value = group.find('div', class_='summary-text')
                    if heading and value:
                        heading_text = heading.get_text(strip=True).upper()
                        if 'EXPORTING COUNTRY' in heading_text:
                            exporting_country = value.get_text(strip=True)
                        elif 'IMPORTING COUNTRY' in heading_text:
                            importing_country = value.get_text(strip=True)
                        elif 'PRODUCT' in heading_text:
                            product = value.get_text(strip=True)

        # Customs Tariffs (table)
        custom_duties_table = soup.find('div', id='custom-duties')
        customs_tariffs = []
        if custom_duties_table:
            table = custom_duties_table.find('table')
            if table:
                customs_tariffs = parse_customs_tariffs_table(table)

        # Trade Remedies (message)
        trade_remedies_message = ''
        trade_remedy_content = soup.find('div', id='trade-remedy')
        if trade_remedy_content:
            alert = trade_remedy_content.find('div', class_='alert')
            if alert:
                trade_remedies_message = alert.get_text(strip=True)
            else:
                trade_remedies_message = trade_remedy_content.get_text(strip=True)

        # Regulatory Requirements (table)
        ntm_summary = soup.find('div', id='ntm-summary')
        regulatory_requirements = []
        if ntm_summary:
            table = ntm_summary.find('table')
            if table:
                regulatory_requirements = parse_regulatory_requirements_table(table)

        # Source info
        source_info = ''
        source_div = soup.find('div', id='custom-duties-source')
        if source_div:
            source_info = source_div.get_text(strip=True)
        ntm_source_div = soup.find('div', id='ntm-source')
        if ntm_source_div:
            ntm_source_text = ntm_source_div.get_text(strip=True)
            if ntm_source_text and ntm_source_text not in source_info:
                source_info = (source_info + '\n' if source_info else '') + ntm_source_text

        # Add products config import
        products_config = current_app.config.get('PRODUCTS', [])
        if not product or product.strip() == product_hs6 or product.strip().isdigit():
            for prod in products_config:
                if prod.get('hs6') == product_hs6:
                    product = prod.get('description', product_hs6)
                    break

        return {
            'overview': {
                'exporting_country': exporting_country,
                'importing_country': importing_country,
                'product': product
            },
            'customs_tariffs': customs_tariffs,
            'trade_remedies_message': trade_remedies_message,
            'regulatory_requirements': regulatory_requirements,
            'source_info': source_info
        }
    except Exception as e:
        print(f"Error scraping MacMap Market Access Conditions: {e}")
        
        # Try ChatGPT fallback when scraping fails
        try:
            print(f"Attempting ChatGPT fallback for market access conditions")
            from ..services.chatgpt_fallback_service import ChatGPTFallbackService
            from flask import current_app
            
            # Get country and product information for the fallback
            countries_config = current_app.config.get('COUNTRIES', [])
            products_config = current_app.config.get('PRODUCTS', [])
            
            # Find country names from ISO codes
            exporting_country = "Unknown"
            importing_country = "Unknown"
            for country in countries_config:
                if country.get('iso3n') == reporter_iso3n:
                    exporting_country = country.get('name', 'Unknown')
                if country.get('iso3n') == partner_iso3n:
                    importing_country = country.get('name', 'Unknown')
            
            # Find product description from HS6 code
            product_description = product_hs6
            for product in products_config:
                if product.get('hs6') == product_hs6:
                    product_description = product.get('description', product_hs6)
                    break
            
            fallback_service = ChatGPTFallbackService()
            generated_data = fallback_service.generate_market_access_conditions(
                exporting_country, importing_country, product_description, product_hs6
            )
            
            print(f"Successfully generated market access conditions using ChatGPT")
            return generated_data
            
        except Exception as fallback_error:
            print(f"ChatGPT fallback also failed: {fallback_error}")
        
        # If both scraping and ChatGPT fail, return error
        return {'error': f'Error scraping MacMap Market Access Conditions: {str(e)}. ChatGPT fallback also failed.'} 