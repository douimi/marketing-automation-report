"""
ChatGPT Fallback Service for generating data when scraping fails.
This service uses OpenAI's GPT model with web search functionality to generate
structured data that matches the expected format of the scraped data.
"""

import openai
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import current_app

load_dotenv()

class ChatGPTFallbackService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
        else:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

    def generate_country_general_information(self, country_name, country_code):
        """
        Generate country general information data using ChatGPT with web search.
        Returns data in the same structure as scrape_santander_country_data.
        
        Expected return structure:
        {
            'donnees1_text': HTML string with basic country info,
            'donnees2_text': HTML string with additional country data,
            'trade_table': List of dicts with trade statistics
        }
        """
        try:
            # Generate donnees1 section (basic country information)
            donnees1_prompt = f"""
            Generate comprehensive basic information about {country_name} in HTML format that matches the structure of Santander Trade's donnees1 section.
            
            Please search the web for current information about {country_name} and provide the following data in HTML format with proper div structure and classes:
            
            - Capital city
            - Total population (latest available data)
            - Area in km²
            - National currency
            - Official language(s)
            - Government type
            - GDP per capita
            - HDI (Human Development Index)
            - Time zone
            - Internet country code
            
            Format the response as HTML with the following structure:
            <div id="donnees1">
                <div class="titre-donnees">
                    <span class="sous-titre-encart">Capital:</span> [value]
                </div>
                <div class="titre-donnees">
                    <span class="sous-titre-encart">Population:</span> [value]
                </div>
                [continue for all fields...]
            </div>
            
            Use current, accurate data from reliable sources. Include proper formatting and ensure all values are up-to-date.
            """
            
            donnees1_response = openai.chat.completions.create(
                model="gpt-3.5-turbo",  # Using GPT-4 for better web search capabilities
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a data researcher with access to current web information. Generate accurate, structured HTML data for country profiles. Always search for the most recent and reliable information."
                    },
                    {"role": "user", "content": donnees1_prompt}
                ],
                temperature=0.3,  # Lower temperature for factual accuracy
                max_tokens=2000
            )
            
            donnees1_text = donnees1_response.choices[0].message.content
            
            # Generate donnees2 section (additional economic and social data)
            donnees2_prompt = f"""
            Generate additional economic and social information about {country_name} in HTML format that matches the structure of Santander Trade's donnees2 section.
            
            Please search the web for current information about {country_name} and provide the following data in HTML format:
            
            - Urban population percentage
            - Population density (people per km²)
            - Life expectancy
            - Literacy rate
            - Access to electricity percentage
            - Mobile phone subscriptions per 100 people
            - Internet users percentage
            - Type of economy (developed, emerging, developing)
            - Main economic sectors
            - Unemployment rate
            
            Format the response as HTML with the following structure:
            <div id="donnees2">
                <div class="titre-donnees">
                    <span class="sous-titre-encart">Urban Population:</span> [value]%
                </div>
                <div class="titre-donnees">
                    <span class="sous-titre-encart">Density:</span> [value] people/km²
                </div>
                [continue for all fields...]
            </div>
            
            Use current, accurate data from reliable sources like World Bank, IMF, UN, etc.
            """
            
            donnees2_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a data researcher with access to current web information. Generate accurate, structured HTML data for country economic and social profiles. Always search for the most recent and reliable information."
                    },
                    {"role": "user", "content": donnees2_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            donnees2_text = donnees2_response.choices[0].message.content
            
            # Generate trade statistics table
            trade_table_prompt = f"""
            Generate foreign trade statistics for {country_name} in a structured format that matches Santander Trade's Foreign Trade in Figures table.
            
            Please search the web for the most recent trade data for {country_name} and provide the following information:
            
            - Total imports (USD billions, latest year available)
            - Total exports (USD billions, latest year available)
            - Trade balance (USD billions)
            - Main import partners (top 5 countries with percentages)
            - Main export partners (top 5 countries with percentages)
            - Main imported products (top 5 categories)
            - Main exported products (top 5 categories)
            
            Return the data as a JSON array of objects with the following structure:
            [
                {"Indicator": "Total Imports", "Value": "$XXX billion", "Year": "2023"},
                {"Indicator": "Total Exports", "Value": "$XXX billion", "Year": "2023"},
                {"Indicator": "Trade Balance", "Value": "$XXX billion", "Year": "2023"},
                {"Indicator": "Main Import Partners", "Value": "Country1 (XX%), Country2 (XX%), Country3 (XX%)", "Year": "2023"},
                {"Indicator": "Main Export Partners", "Value": "Country1 (XX%), Country2 (XX%), Country3 (XX%)", "Year": "2023"},
                {"Indicator": "Main Imports", "Value": "Product1, Product2, Product3", "Year": "2023"},
                {"Indicator": "Main Exports", "Value": "Product1, Product2, Product3", "Year": "2023"}
            ]
            
            Use the most recent data available from reliable sources like WTO, World Bank, country's statistical offices, etc.
            """
            
            trade_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a trade data analyst with access to current web information. Generate accurate trade statistics in JSON format. Always search for the most recent and reliable trade data."
                    },
                    {"role": "user", "content": trade_table_prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Parse the trade table response
            trade_content = trade_response.choices[0].message.content
            try:
                # Extract JSON from the response
                if "```json" in trade_content:
                    json_start = trade_content.find("```json") + 7
                    json_end = trade_content.find("```", json_start)
                    json_content = trade_content[json_start:json_end].strip()
                elif "[" in trade_content and "]" in trade_content:
                    json_start = trade_content.find("[")
                    json_end = trade_content.rfind("]") + 1
                    json_content = trade_content[json_start:json_end]
                else:
                    json_content = trade_content
                
                trade_table_data = json.loads(json_content)
            except (json.JSONDecodeError, Exception) as e:
                current_app.logger.warning(f"Failed to parse trade table JSON: {e}")
                # Fallback to basic structure
                trade_table_data = [
                    {"Indicator": "Total Imports", "Value": "Data not available", "Year": "N/A"},
                    {"Indicator": "Total Exports", "Value": "Data not available", "Year": "N/A"},
                    {"Indicator": "Trade Balance", "Value": "Data not available", "Year": "N/A"}
                ]
            
            return {
                'donnees1_text': donnees1_text,
                'donnees2_text': donnees2_text,
                'trade_table': trade_table_data
            }
            
        except Exception as e:
            print(f"Error generating country information with ChatGPT: {str(e)}")
            if current_app:
                current_app.logger.error(f"Error generating country information with ChatGPT: {str(e)}")
            # Return a basic fallback structure
            return {
                'donnees1_text': f'<div id="donnees1"><div class="titre-donnees"><span class="sous-titre-encart">Country:</span> {country_name}</div><div class="titre-donnees"><span class="sous-titre-encart">Status:</span> Data generation failed - using fallback</div></div>',
                'donnees2_text': f'<div id="donnees2"><div class="titre-donnees"><span class="sous-titre-encart">Note:</span> Additional data for {country_name} could not be generated</div></div>',
                'trade_table': [
                    {"Indicator": "Status", "Value": "ChatGPT data generation failed", "Year": "N/A"}
                ]
            }

    def generate_market_access_conditions(self, exporting_country, importing_country, product_description, hs6_code):
        """
        Generate market access conditions data using ChatGPT with web search.
        Returns data in the same structure as scrape_macmap_market_access_conditions.
        
        Expected return structure matching MacMap data:
        {
            'overview': {
                'exporting_country': str,
                'importing_country': str,
                'product': str
            },
            'customs_tariffs': [
                {
                    'tariff_regime': str,
                    'applied_tariff': str,
                    'ave': str,
                    'note': str
                }
            ],
            'trade_remedies_message': str,
            'regulatory_requirements': [
                {
                    'code': str,
                    'description': str,
                    'count': str
                }
            ],
            'source_info': str
        }
        """
        try:
            prompt = f"""
            Generate comprehensive market access conditions data for exporting {product_description} (HS code: {hs6_code}) from {exporting_country} to {importing_country}.
            
            Please search the web for current trade information and provide the following data in JSON format:
            
            1. Overview information
            2. Customs tariffs and duties
            3. Trade remedies (anti-dumping, countervailing duties, safeguards)
            4. Regulatory requirements (technical barriers, sanitary measures, etc.)
            5. Source information
            
            Return the data in this exact JSON structure:
            {{
                "overview": {{
                    "exporting_country": "{exporting_country}",
                    "importing_country": "{importing_country}",
                    "product": "{product_description}"
                }},
                "customs_tariffs": [
                    {{
                        "tariff_regime": "MFN Applied",
                        "applied_tariff": "X%",
                        "ave": "X%",
                        "note": "Description of tariff conditions"
                    }}
                ],
                "trade_remedies_message": "Information about any trade remedies in place",
                "regulatory_requirements": [
                    {{
                        "code": "TBT",
                        "description": "Technical barriers to trade requirements",
                        "count": "X measures"
                    }},
                    {{
                        "code": "SPS",
                        "description": "Sanitary and phytosanitary measures",
                        "count": "X measures"
                    }}
                ],
                "source_info": "Data sources: WTO, national trade authorities, latest available data"
            }}
            
            Search for the most recent and accurate trade data from reliable sources like WTO, national customs authorities, trade databases, etc.
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a trade compliance expert with access to current web information. Generate accurate market access data in JSON format. Always search for the most recent and reliable trade information."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2500
            )
            
            # Parse the response
            content = response.choices[0].message.content
            try:
                # Extract JSON from the response
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                elif "{" in content and "}" in content:
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    json_content = content[json_start:json_end]
                else:
                    json_content = content
                
                market_access_data = json.loads(json_content)
                return market_access_data
                
            except (json.JSONDecodeError, Exception) as e:
                current_app.logger.warning(f"Failed to parse market access JSON: {e}")
                # Return fallback structure
                return {
                    'overview': {
                        'exporting_country': exporting_country,
                        'importing_country': importing_country,
                        'product': product_description
                    },
                    'customs_tariffs': [
                        {
                            'tariff_regime': 'Data not available',
                            'applied_tariff': 'N/A',
                            'ave': 'N/A',
                            'note': 'Market access data could not be generated'
                        }
                    ],
                    'trade_remedies_message': 'Trade remedies information not available',
                    'regulatory_requirements': [],
                    'source_info': 'Data generation failed - please check manually'
                }
                
        except Exception as e:
            current_app.logger.error(f"Error generating market access conditions with ChatGPT: {str(e)}")
            return {
                'overview': {
                    'exporting_country': exporting_country,
                    'importing_country': importing_country,
                    'product': product_description
                },
                'customs_tariffs': [],
                'trade_remedies_message': 'Error generating trade remedies information',
                'regulatory_requirements': [],
                'source_info': 'Data generation failed due to technical error'
            }

    def generate_operating_business_data(self, country_name):
        """
        Generate Operating a Business data using ChatGPT with web search.
        Returns data in the same structure as scrape_santander_operating_a_business.
        
        Expected return structure:
        {
            'legal_section': HTML string,
            'active_population_section': HTML string,
            'working_conditions_section': HTML string,
            'cost_of_labour_section': HTML string,
            'management_section': HTML string,
            'update_date': string,
            'raw_html': HTML string
        }
        """
        try:
            prompt = f"""
            Generate comprehensive information about operating a business in {country_name}. 
            
            Please search the web for current information about {country_name} and provide detailed content for each of the following sections in HTML format:
            
            1. Legal Framework for Business Operations
            2. Active Population and Labor Market
            3. Working Conditions and Labor Laws
            4. Cost of Labor and Compensation
            5. Management and Human Resources
            
            Return the data in JSON format with this structure:
            {{
                "legal_section": "<div>Detailed HTML content about legal framework for business operations, company registration, business licenses, regulatory compliance, etc.</div>",
                "active_population_section": "<div>Detailed HTML content about active population, workforce demographics, labor market statistics, employment rates, etc.</div>",
                "working_conditions_section": "<div>Detailed HTML content about working conditions, labor laws, working hours, employee rights, workplace safety, etc.</div>",
                "cost_of_labour_section": "<div>Detailed HTML content about labor costs, minimum wages, salary ranges, social security contributions, employment taxes, etc.</div>",
                "management_section": "<div>Detailed HTML content about human resources management, recruitment practices, employee benefits, management culture, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all sections</div>"
            }}
            
            Make sure each section contains detailed, practical information that would be useful for businesses looking to operate in {country_name}. Include specific data, statistics, and practical guidance where possible.
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a business operations expert with access to current web information. Generate comprehensive, accurate business operation guides in JSON format. Always search for the most recent and reliable information."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            try:
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                elif "{" in content and "}" in content:
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    json_content = content[json_start:json_end]
                else:
                    json_content = content
                
                business_data = json.loads(json_content)
                return business_data
                
            except (json.JSONDecodeError, Exception) as e:
                print(f"Failed to parse operating business JSON: {e}")
                return self._get_operating_business_fallback(country_name)
                
        except Exception as e:
            print(f"Error generating operating business data with ChatGPT: {str(e)}")
            return self._get_operating_business_fallback(country_name)

    def _get_operating_business_fallback(self, country_name):
        """Fallback structure for operating business data."""
        from datetime import datetime
        return {
            'legal_section': f'<div><h3>Legal Framework</h3><p>Information about business operations in {country_name} could not be retrieved at this time. Please consult local business advisors or government resources.</p></div>',
            'active_population_section': f'<div><h3>Active Population</h3><p>Labor market data for {country_name} is not available.</p></div>',
            'working_conditions_section': f'<div><h3>Working Conditions</h3><p>Working conditions information for {country_name} is not available.</p></div>',
            'cost_of_labour_section': f'<div><h3>Cost of Labor</h3><p>Labor cost data for {country_name} is not available.</p></div>',
            'management_section': f'<div><h3>Management</h3><p>Human resources management information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Operating business data for {country_name} could not be generated.</p></div>'
        }

    def generate_tax_system_data(self, country_name):
        """
        Generate Tax System data using ChatGPT with web search.
        Returns data in the same structure as scrape_santander_tax_system.
        """
        try:
            prompt = f"""
            Generate comprehensive information about the tax system in {country_name}. 
            
            Please search the web for current tax information about {country_name} and provide detailed content for each of the following sections in HTML format:
            
            1. Corporate Taxes and Business Taxation
            2. Accounting Rules and Financial Reporting
            3. Consumption Taxes (VAT, Sales Tax, etc.)
            4. Other Taxes and Duties
            
            Return the data in JSON format with this structure:
            {{
                "corporate_taxes_section": "<div>Detailed HTML content about corporate tax rates, business tax obligations, tax incentives, deductions, etc.</div>",
                "accounting_rules_section": "<div>Detailed HTML content about accounting standards, financial reporting requirements, audit obligations, etc.</div>",
                "consumption_taxes_section": "<div>Detailed HTML content about VAT/sales tax rates, consumption taxes, import duties, etc.</div>",
                "other_taxes_section": "<div>Detailed HTML content about other taxes like property tax, payroll taxes, withholding taxes, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all tax sections</div>"
            }}
            
            Include specific tax rates, thresholds, and practical guidance for businesses operating in {country_name}.
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a tax expert with access to current web information. Generate comprehensive, accurate tax guides in JSON format. Always search for the most recent tax information."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            try:
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                elif "{" in content and "}" in content:
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    json_content = content[json_start:json_end]
                else:
                    json_content = content
                
                tax_data = json.loads(json_content)
                return tax_data
                
            except (json.JSONDecodeError, Exception) as e:
                print(f"Failed to parse tax system JSON: {e}")
                return self._get_tax_system_fallback(country_name)
                
        except Exception as e:
            print(f"Error generating tax system data with ChatGPT: {str(e)}")
            return self._get_tax_system_fallback(country_name)

    def _get_tax_system_fallback(self, country_name):
        """Fallback structure for tax system data."""
        return {
            'corporate_taxes_section': f'<div><h3>Corporate Taxes</h3><p>Corporate tax information for {country_name} could not be retrieved.</p></div>',
            'accounting_rules_section': f'<div><h3>Accounting Rules</h3><p>Accounting requirements for {country_name} are not available.</p></div>',
            'consumption_taxes_section': f'<div><h3>Consumption Taxes</h3><p>VAT and consumption tax data for {country_name} is not available.</p></div>',
            'other_taxes_section': f'<div><h3>Other Taxes</h3><p>Additional tax information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Tax system data for {country_name} could not be generated.</p></div>'
        }

    def generate_legal_environment_data(self, country_name):
        """Generate Legal Environment data using ChatGPT with web search."""
        try:
            prompt = f"""
            Generate comprehensive information about the legal environment in {country_name} for businesses.
            
            Please search the web for current legal information about {country_name} and provide detailed content for each section in HTML format:
            
            1. Business Contracts and Commercial Law
            2. Intellectual Property Protection
            3. Legal Framework and Regulatory Environment
            
            Return the data in JSON format:
            {{
                "business_contract_section": "<div>Detailed HTML content about business contracts, commercial law, contract enforcement, dispute resolution, etc.</div>",
                "intellectual_property_section": "<div>Detailed HTML content about IP protection, patents, trademarks, copyrights, enforcement mechanisms, etc.</div>",
                "legal_framework_section": "<div>Detailed HTML content about legal system, regulatory framework, court system, legal procedures, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all legal sections</div>"
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a legal expert with access to current web information. Generate comprehensive, accurate legal guides in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content, self._get_legal_environment_fallback(country_name))
                
        except Exception as e:
            print(f"Error generating legal environment data: {str(e)}")
            return self._get_legal_environment_fallback(country_name)

    def _get_legal_environment_fallback(self, country_name):
        """Fallback structure for legal environment data."""
        return {
            'business_contract_section': f'<div><h3>Business Contracts</h3><p>Commercial law information for {country_name} is not available.</p></div>',
            'intellectual_property_section': f'<div><h3>Intellectual Property</h3><p>IP protection data for {country_name} is not available.</p></div>',
            'legal_framework_section': f'<div><h3>Legal Framework</h3><p>Legal system information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Legal environment data for {country_name} could not be generated.</p></div>'
        }

    def generate_foreign_investment_data(self, country_name):
        """Generate Foreign Investment data using ChatGPT with web search."""
        try:
            prompt = f"""
            Generate comprehensive information about foreign investment in {country_name}.
            
            Please search the web for current investment information about {country_name} and provide detailed content for each section in HTML format:
            
            1. FDI Figures and Statistics
            2. Why Invest in this Country
            3. Investment Protection and Incentives
            
            Return the data in JSON format:
            {{
                "fdi_figures_section": "<div>Detailed HTML content about FDI statistics, investment flows, key sectors, major investors, etc.</div>",
                "why_invest_section": "<div>Detailed HTML content about investment advantages, market opportunities, economic benefits, strategic location, etc.</div>",
                "protection_section": "<div>Detailed HTML content about investment protection, bilateral investment treaties, legal safeguards, dispute resolution, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all investment sections</div>"
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an investment expert with access to current web information. Generate comprehensive investment guides in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content, self._get_foreign_investment_fallback(country_name))
                
        except Exception as e:
            print(f"Error generating foreign investment data: {str(e)}")
            return self._get_foreign_investment_fallback(country_name)

    def _get_foreign_investment_fallback(self, country_name):
        """Fallback structure for foreign investment data."""
        return {
            'fdi_figures_section': f'<div><h3>FDI Figures</h3><p>Foreign investment statistics for {country_name} are not available.</p></div>',
            'why_invest_section': f'<div><h3>Why Invest</h3><p>Investment advantages for {country_name} are not available.</p></div>',
            'protection_section': f'<div><h3>Investment Protection</h3><p>Investment protection information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Foreign investment data for {country_name} could not be generated.</p></div>'
        }

    def generate_business_practices_data(self, country_name):
        """Generate Business Practices data using ChatGPT with web search."""
        try:
            prompt = f"""
            Generate comprehensive information about business practices and culture in {country_name}.
            
            Please search the web for current information about {country_name} and provide detailed content for each section in HTML format:
            
            1. Business Culture and Etiquette
            2. Business Hours and Working Practices
            
            Return the data in JSON format:
            {{
                "business_culture_section": "<div>Detailed HTML content about business culture, etiquette, communication styles, meeting practices, relationship building, etc.</div>",
                "opening_hours_section": "<div>Detailed HTML content about business hours, working days, holidays, seasonal variations, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all business practice sections</div>"
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a business culture expert with access to current web information. Generate comprehensive business practice guides in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2500
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content, self._get_business_practices_fallback(country_name))
                
        except Exception as e:
            print(f"Error generating business practices data: {str(e)}")
            return self._get_business_practices_fallback(country_name)

    def _get_business_practices_fallback(self, country_name):
        """Fallback structure for business practices data."""
        return {
            'business_culture_section': f'<div><h3>Business Culture</h3><p>Business culture information for {country_name} is not available.</p></div>',
            'opening_hours_section': f'<div><h3>Business Hours</h3><p>Business hours information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Business practices data for {country_name} could not be generated.</p></div>'
        }

    def generate_entry_requirements_data(self, country_name):
        """Generate Entry Requirements data using ChatGPT with web search."""
        try:
            prompt = f"""
            Generate comprehensive information about entry requirements for {country_name}.
            
            Please search the web for current entry and travel information about {country_name} and provide detailed content for each section in HTML format:
            
            1. Passport and Visa Requirements
            2. Customs and Import Taxes
            3. Health and Vaccination Requirements
            
            Return the data in JSON format:
            {{
                "passport_visa_section": "<div>Detailed HTML content about passport requirements, visa types, application procedures, duration of stay, etc.</div>",
                "customs_taxes_section": "<div>Detailed HTML content about customs procedures, duty-free allowances, import restrictions, taxes on goods, etc.</div>",
                "health_section": "<div>Detailed HTML content about vaccination requirements, health certificates, medical insurance, health risks, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all entry requirement sections</div>"
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a travel and immigration expert with access to current web information. Generate comprehensive entry requirement guides in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content, self._get_entry_requirements_fallback(country_name))
                
        except Exception as e:
            print(f"Error generating entry requirements data: {str(e)}")
            return self._get_entry_requirements_fallback(country_name)

    def _get_entry_requirements_fallback(self, country_name):
        """Fallback structure for entry requirements data."""
        return {
            'passport_visa_section': f'<div><h3>Passport & Visa</h3><p>Entry requirements for {country_name} are not available.</p></div>',
            'customs_taxes_section': f'<div><h3>Customs & Taxes</h3><p>Customs information for {country_name} is not available.</p></div>',
            'health_section': f'<div><h3>Health Requirements</h3><p>Health requirements for {country_name} are not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Entry requirements data for {country_name} could not be generated.</p></div>'
        }

    def generate_practical_information_data(self, country_name):
        """Generate Practical Information data using ChatGPT with web search."""
        try:
            prompt = f"""
            Generate comprehensive practical information for visitors to {country_name}.
            
            Please search the web for current practical information about {country_name} and provide detailed content for each section in HTML format:
            
            1. Eating Out and Dining
            2. Getting Around and Transportation
            3. Time Zone and Local Practices
            
            Return the data in JSON format:
            {{
                "eating_out_section": "<div>Detailed HTML content about restaurants, local cuisine, dining etiquette, food safety, tipping practices, etc.</div>",
                "getting_around_section": "<div>Detailed HTML content about transportation options, public transport, taxis, car rentals, traffic rules, etc.</div>",
                "time_section": "<div>Detailed HTML content about time zone, business hours, cultural practices, local customs, communication, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all practical information sections</div>"
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a travel expert with access to current web information. Generate comprehensive practical travel guides in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content, self._get_practical_information_fallback(country_name))
                
        except Exception as e:
            print(f"Error generating practical information data: {str(e)}")
            return self._get_practical_information_fallback(country_name)

    def _get_practical_information_fallback(self, country_name):
        """Fallback structure for practical information data."""
        return {
            'eating_out_section': f'<div><h3>Eating Out</h3><p>Dining information for {country_name} is not available.</p></div>',
            'getting_around_section': f'<div><h3>Getting Around</h3><p>Transportation information for {country_name} is not available.</p></div>',
            'time_section': f'<div><h3>Time & Customs</h3><p>Local practices information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Practical information for {country_name} could not be generated.</p></div>'
        }

    def generate_living_in_country_data(self, country_name):
        """Generate Living in the Country data using ChatGPT with web search."""
        try:
            prompt = f"""
            Generate comprehensive information about living in {country_name} for expatriates.
            
            Please search the web for current information about {country_name} and provide detailed content for each section in HTML format:
            
            1. Expatriate Communities
            2. City Rankings and Quality of Life
            3. Renting an Apartment
            4. School and Education System
            
            Return the data in JSON format:
            {{
                "expatriates_section": "<div>Detailed HTML content about expatriate communities, international groups, networking, social life, etc.</div>",
                "ranking_section": "<div>Detailed HTML content about city rankings, quality of life, cost of living, safety, amenities, etc.</div>",
                "renting_section": "<div>Detailed HTML content about rental market, housing costs, rental procedures, neighborhoods, utilities, etc.</div>",
                "school_section": "<div>Detailed HTML content about education system, international schools, local schools, enrollment procedures, costs, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all living sections</div>"
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expatriate living expert with access to current web information. Generate comprehensive living guides in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3500
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content, self._get_living_in_country_fallback(country_name))
                
        except Exception as e:
            print(f"Error generating living in country data: {str(e)}")
            return self._get_living_in_country_fallback(country_name)

    def _get_living_in_country_fallback(self, country_name):
        """Fallback structure for living in country data."""
        return {
            'expatriates_section': f'<div><h3>Expatriate Communities</h3><p>Expatriate information for {country_name} is not available.</p></div>',
            'ranking_section': f'<div><h3>City Rankings</h3><p>Quality of life information for {country_name} is not available.</p></div>',
            'renting_section': f'<div><h3>Renting</h3><p>Housing information for {country_name} is not available.</p></div>',
            'school_section': f'<div><h3>Education</h3><p>Education system information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Living in country data for {country_name} could not be generated.</p></div>'
        }

    def generate_reaching_consumers_data(self, country_name):
        """Generate Reaching the Consumer data using ChatGPT with web search."""
        try:
            prompt = f"""
            Generate comprehensive information about reaching consumers in {country_name}.
            
            Please search the web for current market and consumer information about {country_name} and provide detailed content for each section in HTML format:
            
            1. Consumer Profile and Demographics
            2. Marketing Opportunities and Channels
            
            Return the data in JSON format:
            {{
                "anchors_section": "<div>Navigation anchors for the consumer sections</div>",
                "consumer_profile_section": "<div>Detailed HTML content about consumer demographics, behavior, preferences, purchasing power, market segments, etc.</div>",
                "marketing_opportunities_section": "<div>Detailed HTML content about marketing channels, advertising opportunities, digital marketing, traditional media, promotional strategies, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all consumer sections</div>"
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a marketing expert with access to current web information. Generate comprehensive consumer market guides in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content, self._get_reaching_consumers_fallback(country_name))
                
        except Exception as e:
            print(f"Error generating reaching consumers data: {str(e)}")
            return self._get_reaching_consumers_fallback(country_name)

    def _get_reaching_consumers_fallback(self, country_name):
        """Fallback structure for reaching consumers data."""
        return {
            'anchors_section': f'<div><p>Consumer market navigation for {country_name}</p></div>',
            'consumer_profile_section': f'<div><h3>Consumer Profile</h3><p>Consumer information for {country_name} is not available.</p></div>',
            'marketing_opportunities_section': f'<div><h3>Marketing Opportunities</h3><p>Marketing information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Consumer market data for {country_name} could not be generated.</p></div>'
        }

    def generate_distributing_product_data(self, country_name):
        """Generate Distributing a Product data using ChatGPT with web search."""
        try:
            prompt = f"""
            Generate comprehensive information about distributing products in {country_name}.
            
            Please search the web for current distribution and logistics information about {country_name} and provide detailed content for each section in HTML format:
            
            1. Distribution Channels and Networks
            2. Distance Selling and E-commerce
            3. Logistics and Supply Chain
            
            Return the data in JSON format:
            {{
                "anchors_section": "<div>Navigation anchors for the distribution sections</div>",
                "distribution_section": "<div>Detailed HTML content about distribution channels, wholesalers, retailers, partnerships, market access, etc.</div>",
                "distance_selling_section": "<div>Detailed HTML content about e-commerce, online sales, digital platforms, regulations, payment methods, etc.</div>",
                "logistics_section": "<div>Detailed HTML content about logistics, warehousing, transportation, supply chain, delivery options, etc.</div>",
                "update_date": "Latest Update: {datetime.now().strftime('%B %Y')}",
                "raw_html": "<div>Combined HTML content from all distribution sections</div>"
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a distribution and logistics expert with access to current web information. Generate comprehensive distribution guides in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content, self._get_distributing_product_fallback(country_name))
                
        except Exception as e:
            print(f"Error generating distributing product data: {str(e)}")
            return self._get_distributing_product_fallback(country_name)

    def _get_distributing_product_fallback(self, country_name):
        """Fallback structure for distributing product data."""
        return {
            'anchors_section': f'<div><p>Product distribution navigation for {country_name}</p></div>',
            'distribution_section': f'<div><h3>Distribution Channels</h3><p>Distribution information for {country_name} is not available.</p></div>',
            'distance_selling_section': f'<div><h3>E-commerce</h3><p>E-commerce information for {country_name} is not available.</p></div>',
            'logistics_section': f'<div><h3>Logistics</h3><p>Logistics information for {country_name} is not available.</p></div>',
            'update_date': f'Latest Update: {datetime.now().strftime("%B %Y")} (Generated)',
            'raw_html': f'<div><p>Product distribution data for {country_name} could not be generated.</p></div>'
        }

    def _parse_json_response(self, content, fallback_data):
        """Helper method to parse JSON responses with fallback."""
        try:
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_content = content[json_start:json_end].strip()
            elif "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_content = content[json_start:json_end]
            else:
                json_content = content
            
            return json.loads(json_content)
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Failed to parse JSON response: {e}")
            return fallback_data
