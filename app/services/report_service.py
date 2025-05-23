from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from ..scrapers.santander_scraper import login_santander, scrape_santander_country_data
import os
import openai
from dotenv import load_dotenv
from flask import current_app

load_dotenv()

SANTANDER_EMAIL = "edgarcayuelas@indegate.com"
SANTANDER_PASSWORD = "Indegate@2020"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("WARNING: OPENAI_API_KEY not found in environment variables. OpenAI features will be disabled.")

def format_country_name_for_url(country_name):
    """Converts country name to lowercase and replaces spaces with hyphens."""
    return country_name.lower().replace(" ", "-")

def get_country_name_from_code(country_code, countries_config):
    """Retrieves the country name from its code using the loaded config."""
    for country in countries_config:
        if country.get("code") == country_code:
            return country.get("name")
    return None # Or raise an error

class ReportGenerationService:
    def __init__(self):
        self.driver = None
        self._initialize_driver()

    def _initialize_driver(self):
        """Initializes the Selenium WebDriver."""
        chrome_options = Options()
        # Add any desired options like headless mode, etc.
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        
        # Try to use WebDriverManager to automatically get the correct ChromeDriver
        try:
            print("Initializing WebDriver with ChromeDriverManager...")
            self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
            print("WebDriver initialized successfully with ChromeDriverManager.")
        except Exception as e:
            print(f"Error initializing WebDriver with ChromeDriverManager: {e}")
            print("Attempting to initialize WebDriver with default ChromeDriver path...")
            # Fallback or specific path if WebDriverManager fails or is not preferred
            try:
                 self.driver = webdriver.Chrome(options=chrome_options)
                 print("WebDriver initialized successfully with default ChromeDriver path.")
            except Exception as e2:
                print(f"Error initializing WebDriver with default path: {e2}")
                print("Please ensure ChromeDriver is in your PATH or specify its location.")
                self.driver = None # Ensure driver is None if initialization fails

    def generate_santander_report_data(self, destination_country_code, countries_config):
        """Generates the report data from Santander Trade."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return "Error: WebDriver not initialized."

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return f"Error: Could not find country name for code {destination_country_code}."

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Attempting to log in to Santander for {destination_country_name}...")
            login_santander(self.driver, SANTANDER_EMAIL, SANTANDER_PASSWORD)
            print("Login attempt finished.")
            
            print(f"Scraping data for {formatted_country_name}...")
            scraped_data = scrape_santander_country_data(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Santander report generation: {e}")
            return f"Error during Santander report generation for {destination_country_name}: {str(e)}"

    def generate_openai_conclusion(self, market_data, form_data):
        """Generate a concise market analysis conclusion using OpenAI."""
        try:
            prompt = f"""
            As a market analysis expert, provide a concise and structured analysis for {form_data['destination_country_name']}'s market, 
            focusing on the {form_data['sector']} sector. Base your analysis on this market data:

            {market_data}

            Please structure your response in the following format:

            # Executive Summary
            [2-3 sentences highlighting the most important findings and overall market attractiveness]

            ## Market Strengths
            - [3 key strengths, one line each]

            ## Market Challenges
            - [3 key challenges, one line each]

            ## Strategic Recommendations
            - [3 actionable recommendations, one line each]

            Keep each section brief and focused. Avoid general statements and focus on specific, data-backed insights.
            Total response should not exceed 300 words.
            """

            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a market analysis expert providing concise, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            return response.choices[0].message.content

        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI conclusion: {str(e)}")
            return "Error generating market insights. Please try again later."

    def close_driver(self):
        """Closes the Selenium WebDriver."""
        if self.driver:
            print("Closing WebDriver...")
            self.driver.quit()
            self.driver = None
            print("WebDriver closed.")

# Example usage (for testing purposes, will be called from routes):
# if __name__ == '__main__':
#     # This would typically be loaded from app.config in a Flask context
#     sample_countries_config = [
#         {"name": "United States", "code": "US", "iso_numeric": "840"},
#         {"name": "United Arab Emirates", "code": "AE", "iso_numeric": "784"}
#     ]
#     service = ReportGenerationService()
#     if service.driver: # Check if driver initialized successfully
#         # Test with a country that exists in the config
#         country_data = service.generate_santander_report_data("US", sample_countries_config)
#         print("\n--- Santander Report Data (US) ---")
#         print(country_data)
#         # Test with another country
#         country_data_ae = service.generate_santander_report_data("AE", sample_countries_config)
#         print("\n--- Santander Report Data (AE) ---")
#         print(country_data_ae)
#         service.close_driver()
#     else:
#         print("Could not run example: WebDriver failed to initialize.") 