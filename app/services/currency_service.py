"""
Currency Service for handling exchange rate API calls and currency conversions.
Uses ExchangeRate-API (free tier) for real-time exchange rates.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CurrencyService:
    """Service for handling currency exchange rates and conversions."""
    
    def __init__(self):
        # Using exchangerate-api.com free tier (no API key required)
        self.base_url = "https://api.exchangerate-api.com/v4/latest"
        self.supported_currencies_url = "https://api.exchangerate-api.com/v4/latest/USD"
        self.cache = {}
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
        
        # Popular currencies for quick access
        self.popular_currencies = [
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 
            'SEK', 'NZD', 'MXN', 'SGD', 'HKD', 'NOK', 'KRW', 'TRY',
            'RUB', 'INR', 'BRL', 'ZAR', 'PLN', 'DKK', 'CZK', 'HUF',
            'ILS', 'CLP', 'PHP', 'AED', 'COP', 'SAR', 'MYR', 'RON'
        ]
        
        # Comprehensive world currencies with names
        self.currency_names = {
            # Major currencies
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound Sterling',
            'JPY': 'Japanese Yen',
            'AUD': 'Australian Dollar',
            'CAD': 'Canadian Dollar',
            'CHF': 'Swiss Franc',
            'CNY': 'Chinese Yuan Renminbi',
            'SEK': 'Swedish Krona',
            'NZD': 'New Zealand Dollar',
            'MXN': 'Mexican Peso',
            'SGD': 'Singapore Dollar',
            'HKD': 'Hong Kong Dollar',
            'NOK': 'Norwegian Krone',
            'KRW': 'South Korean Won',
            'TRY': 'Turkish Lira',
            'RUB': 'Russian Ruble',
            'INR': 'Indian Rupee',
            'BRL': 'Brazilian Real',
            'ZAR': 'South African Rand',
            'PLN': 'Polish Złoty',
            'DKK': 'Danish Krone',
            'CZK': 'Czech Koruna',
            'HUF': 'Hungarian Forint',
            'ILS': 'Israeli New Shekel',
            'CLP': 'Chilean Peso',
            'PHP': 'Philippine Peso',
            'AED': 'UAE Dirham',
            'COP': 'Colombian Peso',
            'SAR': 'Saudi Riyal',
            'MYR': 'Malaysian Ringgit',
            'RON': 'Romanian Leu',
            'THB': 'Thai Baht',
            'TWD': 'Taiwan New Dollar',
            'IDR': 'Indonesian Rupiah',
            'VND': 'Vietnamese Dong',
            
            # African currencies
            'EGP': 'Egyptian Pound',
            'MAD': 'Moroccan Dirham',
            'TND': 'Tunisian Dinar',
            'NGN': 'Nigerian Naira',
            'KES': 'Kenyan Shilling',
            'GHS': 'Ghanaian Cedi',
            'ETB': 'Ethiopian Birr',
            'UGX': 'Ugandan Shilling',
            'TZS': 'Tanzanian Shilling',
            'ZMW': 'Zambian Kwacha',
            'BWP': 'Botswana Pula',
            'NAD': 'Namibian Dollar',
            'SZL': 'Swazi Lilangeni',
            'LSL': 'Lesotho Loti',
            'MWK': 'Malawian Kwacha',
            'RWF': 'Rwandan Franc',
            'BIF': 'Burundian Franc',
            'DJF': 'Djiboutian Franc',
            'SOS': 'Somali Shilling',
            'MGA': 'Malagasy Ariary',
            'MUR': 'Mauritian Rupee',
            'SCR': 'Seychellois Rupee',
            'GMD': 'Gambian Dalasi',
            'SLL': 'Sierra Leonean Leone',
            'LRD': 'Liberian Dollar',
            'GNF': 'Guinean Franc',
            'XOF': 'West African CFA Franc',
            'XAF': 'Central African CFA Franc',
            'KMF': 'Comorian Franc',
            'CVE': 'Cape Verdean Escudo',
            'STN': 'São Tomé and Príncipe Dobra',
            'DZD': 'Algerian Dinar',
            'LYD': 'Libyan Dinar',
            'SDG': 'Sudanese Pound',
            'SSP': 'South Sudanese Pound',
            'ERN': 'Eritrean Nakfa',
            'AOA': 'Angolan Kwanza',
            'MZN': 'Mozambican Metical',
            'ZWL': 'Zimbabwean Dollar',
            'SHP': 'Saint Helena Pound',
            
            # Asian currencies
            'AFN': 'Afghan Afghani',
            'BDT': 'Bangladeshi Taka',
            'BTN': 'Bhutanese Ngultrum',
            'BND': 'Brunei Dollar',
            'KHR': 'Cambodian Riel',
            'FJD': 'Fijian Dollar',
            'GEL': 'Georgian Lari',
            'KZT': 'Kazakhstani Tenge',
            'KGS': 'Kyrgyzstani Som',
            'LAK': 'Lao Kip',
            'MOP': 'Macanese Pataca',
            'MVR': 'Maldivian Rufiyaa',
            'MNT': 'Mongolian Tugrik',
            'MMK': 'Myanmar Kyat',
            'NPR': 'Nepalese Rupee',
            'KPW': 'North Korean Won',
            'PKR': 'Pakistani Rupee',
            'PGK': 'Papua New Guinean Kina',
            'LKR': 'Sri Lankan Rupee',
            'TJS': 'Tajikistani Somoni',
            'TMT': 'Turkmenistani Manat',
            'UZS': 'Uzbekistani Som',
            'VUV': 'Vanuatu Vatu',
            'WST': 'Samoan Tala',
            'TOP': 'Tongan Paʻanga',
            'SBD': 'Solomon Islands Dollar',
            'NCX': 'CFP Franc',
            'TVD': 'Tuvaluan Dollar',
            'KID': 'Kiribati Dollar',
            'NRU': 'Nauruan Dollar',
            'PLW': 'Palauan Dollar',
            'MHL': 'Marshallese Dollar',
            'FSM': 'Micronesian Dollar',
            
            # European currencies
            'ALL': 'Albanian Lek',
            'AMD': 'Armenian Dram',
            'AZN': 'Azerbaijani Manat',
            'BYN': 'Belarusian Ruble',
            'BAM': 'Bosnia-Herzegovina Convertible Mark',
            'BGN': 'Bulgarian Lev',
            'HRK': 'Croatian Kuna',
            'GIP': 'Gibraltar Pound',
            'ISK': 'Icelandic Króna',
            'MDL': 'Moldovan Leu',
            'MKD': 'North Macedonian Denar',
            'RSD': 'Serbian Dinar',
            'UAH': 'Ukrainian Hryvnia',
            'GGP': 'Guernsey Pound',
            'JEP': 'Jersey Pound',
            'IMP': 'Isle of Man Pound',
            'FKP': 'Falkland Islands Pound',
            
            # Middle Eastern currencies
            'BHD': 'Bahraini Dinar',
            'IRR': 'Iranian Rial',
            'IQD': 'Iraqi Dinar',
            'JOD': 'Jordanian Dinar',
            'KWD': 'Kuwaiti Dinar',
            'LBP': 'Lebanese Pound',
            'OMR': 'Omani Rial',
            'QAR': 'Qatari Riyal',
            'SYP': 'Syrian Pound',
            'YER': 'Yemeni Rial',
            
            # North American currencies
            'XCD': 'East Caribbean Dollar',
            'BBD': 'Barbadian Dollar',
            'BZD': 'Belize Dollar',
            'BMD': 'Bermudian Dollar',
            'KYD': 'Cayman Islands Dollar',
            'CRC': 'Costa Rican Colón',
            'CUP': 'Cuban Peso',
            'DOP': 'Dominican Peso',
            'GTQ': 'Guatemalan Quetzal',
            'HTG': 'Haitian Gourde',
            'HNL': 'Honduran Lempira',
            'JMD': 'Jamaican Dollar',
            'NIO': 'Nicaraguan Córdoba',
            'PAB': 'Panamanian Balboa',
            'TTD': 'Trinidad and Tobago Dollar',
            'AWG': 'Aruban Florin',
            'ANG': 'Netherlands Antillean Guilder',
            
            # South American currencies
            'ARS': 'Argentine Peso',
            'BOB': 'Bolivian Boliviano',
            'GYD': 'Guyanese Dollar',
            'PYG': 'Paraguayan Guaraní',
            'PEN': 'Peruvian Sol',
            'SRD': 'Surinamese Dollar',
            'UYU': 'Uruguayan Peso',
            'VED': 'Venezuelan Bolívar Digital',
            'VES': 'Venezuelan Bolívar Soberano',
            
            # Oceania currencies
            'CKD': 'Cook Islands Dollar',
            'NUD': 'Niue Dollar',
            'PND': 'Pitcairn Islands Dollar',
            'TOK': 'Tokelau Dollar',
            
            # Special currencies and commodities
            'XAG': 'Silver Ounce',
            'XAU': 'Gold Ounce',
            'XPD': 'Palladium Ounce',
            'XPT': 'Platinum Ounce',
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'LTC': 'Litecoin',
            'XRP': 'Ripple',
            'BCH': 'Bitcoin Cash',
            'ADA': 'Cardano',
            'DOT': 'Polkadot',
            'BNB': 'Binance Coin',
            'LINK': 'Chainlink',
            'XLM': 'Stellar',
            
            # Additional currencies
            'SVC': 'Salvadoran Colón',
            'BSD': 'Bahamian Dollar',
            'BIF': 'Burundian Franc',
            'CDF': 'Congolese Franc',
            'XDR': 'Special Drawing Rights',
            'CLF': 'Chilean Unit of Account',
            'COU': 'Colombian Real Value Unit',
            'MXV': 'Mexican Investment Unit',
            'USN': 'US Dollar (Next day)',
            'UYI': 'Uruguayan Peso (Indexed Units)',
            'UYW': 'Uruguayan Nominal Wage Index Unit',
            'CHE': 'WIR Euro',
            'CHW': 'WIR Franc',
            'BOV': 'Bolivian Mvdol',
            'XSU': 'Sucre',
            'XUA': 'ADB Unit of Account'
        }

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid."""
        return datetime.now() - timestamp < self.cache_duration

    def _make_api_request(self, url: str) -> Optional[Dict]:
        """Make API request with error handling."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None

    def get_exchange_rates(self, base_currency: str = 'USD') -> Optional[Dict]:
        """
        Get current exchange rates for a base currency.
        
        Args:
            base_currency: The base currency code (e.g., 'USD')
            
        Returns:
            Dictionary with exchange rates or None if failed
        """
        cache_key = f"rates_{base_currency}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.info(f"Using cached rates for {base_currency}")
                return cached_data
        
        # Make API request
        url = f"{self.base_url}/{base_currency}"
        data = self._make_api_request(url)
        
        if data and 'rates' in data:
            # Cache the result
            self.cache[cache_key] = (data, datetime.now())
            logger.info(f"Fetched fresh rates for {base_currency}")
            return data
        
        return None

    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Optional[Dict]:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            
        Returns:
            Dictionary with conversion result or None if failed
        """
        if from_currency == to_currency:
            return {
                'amount': amount,
                'from_currency': from_currency,
                'to_currency': to_currency,
                'converted_amount': amount,
                'exchange_rate': 1.0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Get exchange rates using from_currency as base
        rates_data = self.get_exchange_rates(from_currency)
        
        if not rates_data or 'rates' not in rates_data:
            return None
        
        rates = rates_data['rates']
        
        if to_currency not in rates:
            return None
        
        exchange_rate = rates[to_currency]
        converted_amount = amount * exchange_rate
        
        return {
            'amount': amount,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'converted_amount': converted_amount,
            'exchange_rate': exchange_rate,
            'timestamp': rates_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            'last_updated': datetime.now().isoformat()
        }

    def get_supported_currencies(self) -> List[Dict]:
        """
        Get list of supported currencies with names.
        
        Returns:
            List of currency dictionaries with code and name
        """
        currencies = []
        
        # First, add popular currencies at the top
        for code in self.popular_currencies:
            currencies.append({
                'code': code,
                'name': self.currency_names.get(code, code),
                'popular': True
            })
        
        # Then add all other currencies we have names for, alphabetically
        remaining_currencies = set(self.currency_names.keys()) - set(self.popular_currencies)
        for code in sorted(remaining_currencies):
            currencies.append({
                'code': code,
                'name': self.currency_names.get(code, code),
                'popular': False
            })
        
        # Try to get additional currencies from API if available
        try:
            rates_data = self.get_exchange_rates('USD')
            if rates_data and 'rates' in rates_data:
                api_currencies = set(rates_data['rates'].keys())
                api_currencies.add('USD')  # Add base currency
                
                # Add any API currencies we don't have names for
                existing_codes = set(curr['code'] for curr in currencies)
                for code in sorted(api_currencies - existing_codes):
                    currencies.append({
                        'code': code,
                        'name': code,  # Use code as name if we don't have a proper name
                        'popular': False
                    })
        except Exception as e:
            logger.warning(f"Could not fetch additional currencies from API: {e}")
        
        return currencies

    def get_popular_currencies(self) -> List[Dict]:
        """Get list of popular currencies for quick access."""
        return [
            {
                'code': code,
                'name': self.currency_names.get(code, code),
                'popular': True
            }
            for code in self.popular_currencies
        ]

    def get_currency_trends(self, currency_code: str, days: int = 7) -> Optional[Dict]:
        """
        Get currency trends (mock implementation for demo).
        In a real implementation, you'd use historical data API.
        
        Args:
            currency_code: Currency code to get trends for
            days: Number of days for trend data
            
        Returns:
            Dictionary with trend data or None if failed
        """
        # This is a mock implementation
        # In production, you'd use a historical rates API
        import random
        
        base_rate = 1.0
        rates_data = self.get_exchange_rates('USD')
        
        if rates_data and currency_code in rates_data['rates']:
            base_rate = rates_data['rates'][currency_code]
        
        # Generate mock trend data
        trends = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
            # Add some random variation (±2%)
            variation = random.uniform(-0.02, 0.02)
            rate = base_rate * (1 + variation)
            trends.append({
                'date': date,
                'rate': round(rate, 4)
            })
        
        return {
            'currency': currency_code,
            'base_currency': 'USD',
            'trends': trends,
            'current_rate': base_rate,
            'change_percentage': random.uniform(-5, 5)  # Mock change percentage
        }

    def format_currency(self, amount: float, currency_code: str) -> str:
        """
        Format currency amount for display.
        
        Args:
            amount: Amount to format
            currency_code: Currency code
            
        Returns:
            Formatted currency string
        """
        # Basic formatting - in production you might use locale-specific formatting
        if currency_code in ['JPY', 'KRW']:  # Currencies without decimals
            return f"{currency_code} {amount:,.0f}"
        else:
            return f"{currency_code} {amount:,.2f}"

    def get_api_status(self) -> Dict:
        """Get API status and information."""
        try:
            # Test API with a simple request
            data = self._make_api_request(f"{self.base_url}/USD")
            
            if data:
                return {
                    'status': 'online',
                    'last_updated': data.get('date', 'Unknown'),
                    'base_currency': data.get('base', 'USD'),
                    'available_currencies': len(data.get('rates', {})),
                    'message': 'Currency API is working properly'
                }
            else:
                return {
                    'status': 'offline',
                    'message': 'Currency API is currently unavailable'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error checking API status: {str(e)}'
            }

# Global instance
currency_service = CurrencyService()
