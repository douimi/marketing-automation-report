from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from ..scrapers.santander_scraper import login_santander, scrape_santander_country_data, scrape_santander_economic_political_outline, scrape_santander_foreign_trade_in_figures, scrape_santander_import_export_flows, scrape_santander_trade_shows, scrape_santander_operating_a_business, scrape_santander_tax_system, scrape_santander_legal_environment, scrape_santander_foreign_investment, scrape_santander_business_practices, scrape_santander_entry_requirements, scrape_santander_practical_information, scrape_santander_living_in_country
from ..scrapers.macmap_scraper import scrape_macmap_market_access_conditions
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
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
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

    def generate_santander_economic_political_outline(self, destination_country_code, countries_config):
        """Scrapes the Economic and Political Outline section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            # Do NOT login again, just go directly to the URL and scrape
            print(f"Scraping Economic and Political Outline for {formatted_country_name}...")
            scraped_data = scrape_santander_economic_political_outline(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Economic and Political Outline scraping: {e}")
            return {"error": f"Error during Economic and Political Outline scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_foreign_trade_in_figures(self, destination_country_code, countries_config):
        """Scrapes the Foreign Trade in Figures section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            # Do NOT login again, just go directly to the URL and scrape
            print(f"Scraping Foreign Trade in Figures for {formatted_country_name}...")
            scraped_data = scrape_santander_foreign_trade_in_figures(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Foreign Trade in Figures scraping: {e}")
            return {"error": f"Error during Foreign Trade in Figures scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_import_export_flows(self, product_hs6, origin_code, destination_code):
        """Scrapes the Import/Export Flows tables from SantanderTrade."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}
        try:
            print(f"Scraping Import/Export Flows for product={product_hs6}, origin={origin_code}, destination={destination_code}...")
            flows_data = scrape_santander_import_export_flows(self.driver, product_hs6, origin_code, destination_code)
            return flows_data
        except Exception as e:
            print(f"An error occurred during Import/Export Flows scraping: {e}")
            return {"error": f"Error during Import/Export Flows scraping: {str(e)}"}

    def generate_macmap_market_access_conditions(self, reporter_iso3n, partner_iso3n, product_hs6):
        """Scrapes the Market Access Conditions section from MacMap."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}
        try:
            print(f"Scraping MacMap Market Access Conditions for reporter={reporter_iso3n}, partner={partner_iso3n}, product={product_hs6}...")
            scraped_data = scrape_macmap_market_access_conditions(self.driver, reporter_iso3n, partner_iso3n, product_hs6)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during MacMap Market Access Conditions scraping: {e}")
            return {"error": f"Error during MacMap Market Access Conditions scraping: {str(e)}"}

    def generate_openai_macmap_intro(self, macmap_data, form_data):
        """Generate a short, engaging introduction for the Market Access Conditions section using OpenAI."""
        try:
            prompt = f"""
            Write a concise, business-focused introduction (3-4 sentences) for a report section on Market Access Conditions for {form_data['destination_country_name']} (importing from {form_data['origin_country_name']}, product: {form_data['product_name']}).
            Use the following data for context:

            {macmap_data}

            Focus on the relevance of market access, key challenges, and opportunities. Do not include lists or bullet points. Keep it under 120 words.
            """
            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst introducing market access conditions to executives."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI MacMap introduction: {str(e)}")
            return ""

    def generate_openai_macmap_insights(self, macmap_data, form_data):
        """Generate actionable insights for the Market Access Conditions section using OpenAI."""
        try:
            prompt = f"""
            As a market access expert, provide 3-5 actionable insights or recommendations for a business considering exporting {form_data['product_name']} from {form_data['origin_country_name']} to {form_data['destination_country_name']}, based on the following data:

            {macmap_data}

            Use bullet points. Focus on practical, data-driven advice and highlight any key risks or opportunities.
            """
            """
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a market access expert providing concise, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI MacMap insights: {str(e)}")
            return ""

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

            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a market analysis expert providing concise, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI conclusion: {str(e)}")
            return ""

    def generate_openai_intro(self, market_data, form_data):
        """Generate a short, engaging introduction about the selected country using OpenAI."""
        try:
            prompt = f"""
            Write a short, engaging introduction (3-4 sentences) about {form_data['destination_country_name']} for a business audience. Use the following data for context:

            {market_data}

            Focus on the country's global relevance, economic profile, and any unique characteristics. Do not include lists or bullet points. Keep it under 120 words.
            """
            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst introducing countries to executives."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI introduction: {str(e)}")
            return ""

    def generate_openai_eco_political_intro(self, eco_pol_data, form_data):
        """Generate a short, engaging introduction for the Economic and Political Outline section using OpenAI."""
        try:
            prompt = f"""
            Write a short, engaging introduction (3-4 sentences) about the economic and political context of {form_data['destination_country_name']} for a business audience. Use the following data for context:

            {eco_pol_data}

            Focus on the country's economic and political profile, recent trends, and any unique characteristics. Do not include lists or bullet points. Keep it under 120 words.
            """
            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst introducing countries' economic and political context to executives."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI eco-political introduction: {str(e)}")
            return ""

    def generate_openai_eco_political_insights(self, eco_pol_data, form_data):
        """Generate a concise insights summary for the Economic and Political Outline section using OpenAI."""
        try:
            prompt = f"""
            As a market and political analysis expert, provide a concise and structured summary of the economic and political situation in {form_data['destination_country_name']}. Base your analysis on this data:

            {eco_pol_data}

            Please structure your response in the following format:

            # Key Insights
            [2-3 sentences summarizing the most important economic and political findings]

            ## Economic Highlights
            - [2-3 key economic points, one line each]

            ## Political Highlights
            - [2-3 key political points, one line each]

            Keep each section brief and focused. Avoid general statements and focus on specific, data-backed insights. Total response should not exceed 250 words.
            """
            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a market and political analysis expert providing concise, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI eco-political insights: {str(e)}")
            return ""

    def generate_openai_trade_intro(self, trade_data, form_data):
        """Generate a short, engaging introduction for the Foreign Trade in Figures section using OpenAI."""
        try:
            prompt = f"""
            Write a short, engaging introduction (3-4 sentences) about the foreign trade profile of {form_data['destination_country_name']} for a business audience. Use the following data for context:

            {trade_data}

            Focus on the country's trade position, key partners, and any unique characteristics. Do not include lists or bullet points. Keep it under 120 words.
            """
            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst introducing countries' trade profiles to executives."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI trade introduction: {str(e)}")
            return ""

    def generate_openai_trade_insights(self, trade_data, form_data):
        """Generate a concise insights summary for the Foreign Trade in Figures section using OpenAI."""
        try:
            prompt = f"""
            As a trade analysis expert, provide a concise and structured summary of the foreign trade situation in {form_data['destination_country_name']}. Base your analysis on this data:

            {trade_data}

            Please structure your response in the following format:

            # Key Trade Insights
            [2-3 sentences summarizing the most important trade findings]

            ## Export Highlights
            - [2-3 key export points, one line each]

            ## Import Highlights
            - [2-3 key import points, one line each]

            Keep each section brief and focused. Avoid general statements and focus on specific, data-backed insights. Total response should not exceed 250 words.
            """
            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a trade analysis expert providing concise, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI trade insights: {str(e)}")
            return ""

    def generate_openai_flows_intro(self, flows_data, form_data):
        """Generate a short, engaging introduction for the Import/Export Flows section using OpenAI."""
        try:
            prompt = f"""
            Write a concise, business-focused introduction (3-4 sentences) for a report section on Import/Export Flows for {form_data['product_name']} between {form_data['origin_country_name']} (exporter) and {form_data['destination_country_name']} (importer).
            Use the following HTML tables for context (export and import flows):

            Export Table:
            {flows_data.get('export_table_html', '')}

            Import Table:
            {flows_data.get('import_table_html', '')}

            Focus on the main trends, key partners, and any notable patterns. Do not include lists or bullet points. Keep it under 120 words.
            """
            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst introducing trade flows to executives."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI flows introduction: {str(e)}")
            return ""

    def generate_openai_flows_insights(self, flows_data, form_data):
        """Generate actionable insights for the Import/Export Flows section using OpenAI."""
        try:
            prompt = f"""
            As a trade flows expert, provide 3-5 actionable insights or recommendations for a business considering trading {form_data['product_name']} between {form_data['origin_country_name']} and {form_data['destination_country_name']}, based on the following HTML tables (export and import flows):

            Export Table:
            {flows_data.get('export_table_html', '')}

            Import Table:
            {flows_data.get('import_table_html', '')}

            Use bullet points. Focus on practical, data-driven advice and highlight any key risks or opportunities.
            """
            """
                        response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a trade flows expert providing concise, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content
            """
            return ""
        except Exception as e:
            current_app.logger.error(f"Error generating OpenAI flows insights: {str(e)}")
            return ""

    def generate_santander_trade_shows(self, sector_code, destination_country_iso3n):
        """Scrapes the Trade Shows section from SantanderTrade for the given sector and country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return []
        try:
            print(f"Scraping Trade Shows for sector={sector_code}, country={destination_country_iso3n}...")
            shows = scrape_santander_trade_shows(self.driver, sector_code, destination_country_iso3n)
            return shows
        except Exception as e:
            print(f"An error occurred during Trade Shows scraping: {e}")
            return []

    def generate_santander_operating_a_business(self, destination_country_code, countries_config):
        """Scrapes the Operating a Business section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Scraping Operating a Business for {formatted_country_name}...")
            scraped_data = scrape_santander_operating_a_business(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Operating a Business scraping: {e}")
            return {"error": f"Error during Operating a Business scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_tax_system(self, destination_country_code, countries_config):
        """Scrapes the Tax System section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Scraping Tax System for {formatted_country_name}...")
            scraped_data = scrape_santander_tax_system(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Tax System scraping: {e}")
            return {"error": f"Error during Tax System scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_legal_environment(self, destination_country_code, countries_config):
        """Scrapes the Legal Environment section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Scraping Legal Environment for {formatted_country_name}...")
            scraped_data = scrape_santander_legal_environment(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Legal Environment scraping: {e}")
            return {"error": f"Error during Legal Environment scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_foreign_investment(self, destination_country_code, countries_config):
        """Scrapes the Foreign Investment section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Scraping Foreign Investment for {formatted_country_name}...")
            scraped_data = scrape_santander_foreign_investment(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Foreign Investment scraping: {e}")
            return {"error": f"Error during Foreign Investment scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_business_practices(self, destination_country_code, countries_config):
        """Scrapes the Business Practices section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Scraping Business Practices for {formatted_country_name}...")
            scraped_data = scrape_santander_business_practices(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Business Practices scraping: {e}")
            return {"error": f"Error during Business Practices scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_entry_requirements(self, destination_country_code, countries_config):
        """Scrapes the Entry Requirements section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Scraping Entry Requirements for {formatted_country_name}...")
            scraped_data = scrape_santander_entry_requirements(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Entry Requirements scraping: {e}")
            return {"error": f"Error during Entry Requirements scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_practical_information(self, destination_country_code, countries_config):
        """Scrapes the Practical Information section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Scraping Practical Information for {formatted_country_name}...")
            scraped_data = scrape_santander_practical_information(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Practical Information scraping: {e}")
            return {"error": f"Error during Practical Information scraping for {destination_country_name}: {str(e)}"}

    def generate_santander_living_in_country(self, destination_country_code, countries_config):
        """Scrapes the Living in the Country section for the given country."""
        if not self.driver:
            print("WebDriver not initialized. Cannot generate report.")
            return {"error": "WebDriver not initialized."}

        destination_country_name = get_country_name_from_code(destination_country_code, countries_config)
        if not destination_country_name:
            return {"error": f"Could not find country name for code {destination_country_code}."}

        formatted_country_name = format_country_name_for_url(destination_country_name)

        try:
            print(f"Scraping Living in the Country for {formatted_country_name}...")
            scraped_data = scrape_santander_living_in_country(self.driver, formatted_country_name)
            return scraped_data
        except Exception as e:
            print(f"An error occurred during Living in the Country scraping: {e}")
            return {"error": f"Error during Living in the Country scraping for {destination_country_name}: {str(e)}"}

    def generate_full_report(self, form_data, countries_config, products_config):
        """Orchestrates the full scraping and returns all data for the report."""
        # 1. Santander General Presentation
        santander_data = self.generate_santander_report_data(form_data['destination_country_code'], countries_config)
        # 2. Santander Economic/Political Outline
        eco_pol_data = self.generate_santander_economic_political_outline(form_data['destination_country_code'], countries_config)
        # 3. Santander Foreign Trade in Figures
        trade_data = self.generate_santander_foreign_trade_in_figures(form_data['destination_country_code'], countries_config)
        # 4. Import/Export Flows (NEW)
        flows_data = self.generate_santander_import_export_flows(
            form_data['hs6_product_code'],
            form_data['origin_country_code'],
            form_data['destination_country_code']
        )
        # 5. Trade Shows (NEW)
        trade_shows_data = self.generate_santander_trade_shows(
            form_data['sector_code'],
            form_data['destination_country_iso3n']
        )
        # 6. MacMap
        macmap_data = self.generate_macmap_market_access_conditions(
            get_country_iso_numeric_from_code(form_data['destination_country_code'], countries_config),
            get_country_iso_numeric_from_code(form_data['origin_country_code'], countries_config),
            form_data['hs6_product_code']
        )
        return {
            'santander_data': santander_data,
            'eco_pol_data': eco_pol_data,
            'trade_data': trade_data,
            'flows_data': flows_data,
            'trade_shows_data': trade_shows_data,
            'macmap_data': macmap_data
        }

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