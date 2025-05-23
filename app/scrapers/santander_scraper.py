from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

SANTANDER_LOGIN_URL = "https://santandertrade.com/en/" # As confirmed by user
PRE_LOGIN_FORM_BUTTON_XPATH = "//*[@id='btn_login_menu']" # User provided XPath to reveal login form
SANTANDER_EMAIL_XPATH = "//*[@id='identification_identifiant']"
SANTANDER_PASSWORD_XPATH = "//*[@id='identification_mot_de_passe']"
SANTANDER_LOGIN_BUTTON_XPATH = "//*[@id='identification_go']"
SANTANDER_MARKET_ANALYSIS_URL_TEMPLATE = "https://santandertrade.com/en/portal/analyse-markets/{formatted_country_name}/general-presentation"

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
        # driver.save_screenshot("debug_reveal_button_error.png")
        # with open("debug_reveal_button_error.html", "w", encoding="utf-8") as f:
        #     f.write(driver.page_source)
        return # Cannot proceed if this fails

    # Now, wait for the actual email field to be present
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, SANTANDER_EMAIL_XPATH)))
        print("Email field is present.")
    except Exception as e:
        print(f"Email field ({SANTANDER_EMAIL_XPATH}) not found after attempting to reveal form. Login cannot proceed. Error: {e}")
        # driver.save_screenshot("debug_email_field_not_found.png")
        # with open("debug_email_field_not_found.html", "w", encoding="utf-8") as f:
        #     f.write(driver.page_source)
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
        # driver.save_screenshot("debug_login_button_error.png")
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
    Navigates to the country's general presentation page and scrapes data.
    """
    target_url = SANTANDER_MARKET_ANALYSIS_URL_TEMPLATE.format(formatted_country_name=formatted_country_name)
    print(f"Navigating to: {target_url}")
    driver.get(target_url)

    try:
        # Wait for the main content div to be present
        content_div_xpath = "//*[@id='contenu-contenu']"
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, content_div_xpath)))
        
        # Extract all text from the content div
        # More specific XPaths can be used for structured data
        content_element = driver.find_element(By.XPATH, content_div_xpath)
        data = content_element.text
        
        if not data:
            print(f"No data extracted from {target_url}. The content div might be empty or structure changed.")
            # Attempt to get page source for debugging if data is empty
            page_source = driver.page_source
            if "entry of this content is reserved for subscribers" in page_source.lower() or "please log on" in page_source.lower():
                print("Content is restricted or login was not successful.")
                return "Error: Content is restricted or login was not successful. Please check credentials and subscription."

            return f"No text data found in #contenu-contenu for {formatted_country_name}. Check page structure."
            
        print(f"Successfully scraped data for {formatted_country_name}")
        return data
    except Exception as e:
        print(f"Error scraping Santander country data for {formatted_country_name}: {e}")
        # Try to get page title or current URL for context
        current_url = driver.current_url
        page_title = driver.title
        print(f"Current URL during error: {current_url}")
        print(f"Page title during error: {page_title}")
        # Check if it's a known error page
        if "page not found" in page_title.lower() or "error 404" in driver.page_source.lower():
             return f"Error: Page not found for country {formatted_country_name} at {target_url}."
        return f"Error scraping Santander data for {formatted_country_name}. Details: {str(e)}" 