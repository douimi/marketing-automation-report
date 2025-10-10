"""
Configuration service for lazy loading and caching of large JSON files.
This service prevents memory issues by loading data on-demand.
"""
import json
import os
import threading
from typing import List, Dict, Optional, Any
from functools import lru_cache

class ConfigService:
    """Service for lazy loading and caching configuration data."""
    
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self._cache = {}
        self._cache_lock = threading.Lock()
    
    def _get_config_path(self, filename: str) -> str:
        """Get the full path to a config file."""
        return os.path.join(self.config_dir, filename)
    
    def _load_file(self, filename: str) -> List[Dict[str, Any]]:
        """Load a JSON config file with memory-efficient handling."""
        config_path = self._get_config_path(filename)
        
        if not os.path.exists(config_path):
            # Return default data for missing files
            return self._get_default_data(filename)
        
        try:
            # Check file size first
            file_size = os.path.getsize(config_path)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                print(f"Warning: {config_path} is very large ({file_size} bytes). Using memory-efficient loading.")
                return self._load_large_file(config_path)
            
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except MemoryError as e:
            print(f"Memory error loading {config_path}: {e}. Trying memory-efficient approach.")
            return self._load_large_file(config_path)
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"Error loading {config_path}: {e}. Returning expanded default data.")
            # Use expanded defaults for better functionality
            return self._get_expanded_default_data(filename)
    
    def _load_large_file(self, config_path: str) -> List[Dict[str, Any]]:
        """Load large JSON files in a memory-efficient way."""
        try:
            import ijson  # Stream JSON parser
            items = []
            with open(config_path, 'rb') as f:
                for item in ijson.items(f, 'item'):
                    items.append(item)
                    # Limit the number of items to prevent memory issues
                    if len(items) >= 1000:  # Reasonable limit
                        break
            return items
        except ImportError:
            # Fallback: Load file in chunks and parse manually
            print(f"ijson not available. Using fallback for {config_path}")
            return self._load_file_fallback(config_path)
        except Exception as e:
            print(f"Error in memory-efficient loading for {config_path}: {e}")
            # Return expanded default data for better functionality
            filename = os.path.basename(config_path)
            return self._get_expanded_default_data(filename)
    
    def _load_file_fallback(self, config_path: str) -> List[Dict[str, Any]]:
        """Fallback method for loading files without ijson."""
        try:
            # Read file in smaller chunks
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read(1024 * 1024)  # Read 1MB at a time
                if content.startswith('['):
                    # Try to parse a partial JSON array
                    # This is a basic implementation - in production you'd want more robust parsing
                    data = json.loads(content)
                    return data[:100] if isinstance(data, list) else [data]
        except Exception as e:
            print(f"Fallback loading failed for {config_path}: {e}")
        
        # Return expanded defaults if all else fails
        filename = os.path.basename(config_path)
        return self._get_expanded_default_data(filename)
    
    def _get_default_data(self, filename: str) -> List[Dict[str, Any]]:
        """Get default data for a config file."""
        defaults = {
            'countries.json': [{"name": "United States", "code": "US", "iso_numeric": "840"}],
            'products.json': [{"hs6": "010101", "description": "Live horses"}],
            'sectors.json': [{"name": "Agriculture"}]
        }
        return defaults.get(filename, [])
    
    def _get_expanded_default_data(self, filename: str) -> List[Dict[str, Any]]:
        """Get expanded default data for better functionality when full file can't be loaded."""
        expanded_defaults = {
            'countries.json': [
                {"name": "United States", "code": "US", "iso_numeric": "840", "ISO2": "US"},
                {"name": "France", "code": "FR", "iso_numeric": "250", "ISO2": "FR"},
                {"name": "Germany", "code": "DE", "iso_numeric": "276", "ISO2": "DE"},
                {"name": "United Kingdom", "code": "GB", "iso_numeric": "826", "ISO2": "GB"},
                {"name": "China", "code": "CN", "iso_numeric": "156", "ISO2": "CN"},
                {"name": "Japan", "code": "JP", "iso_numeric": "392", "ISO2": "JP"},
                {"name": "Canada", "code": "CA", "iso_numeric": "124", "ISO2": "CA"},
                {"name": "Australia", "code": "AU", "iso_numeric": "036", "ISO2": "AU"},
                {"name": "Spain", "code": "ES", "iso_numeric": "724", "ISO2": "ES"},
                {"name": "Italy", "code": "IT", "iso_numeric": "380", "ISO2": "IT"},
                {"name": "Brazil", "code": "BR", "iso_numeric": "076", "ISO2": "BR"},
                {"name": "India", "code": "IN", "iso_numeric": "356", "ISO2": "IN"},
                {"name": "Mexico", "code": "MX", "iso_numeric": "484", "ISO2": "MX"},
                {"name": "South Korea", "code": "KR", "iso_numeric": "410", "ISO2": "KR"},
                {"name": "Netherlands", "code": "NL", "iso_numeric": "528", "ISO2": "NL"}
            ],
            'products.json': [
                {"hs6": "010101", "description": "Live horses"},
                {"hs6": "010110", "description": "Pure-bred breeding horses"},
                {"hs6": "010190", "description": "Other live horses"},
                {"hs6": "020110", "description": "Carcasses and half-carcasses of bovine animals, fresh or chilled"},
                {"hs6": "020120", "description": "Other cuts of bovine animals, fresh or chilled"}
            ],
            'sectors.json': [
                {"name": "Agriculture", "code": "AG001"},
                {"name": "Manufacturing", "code": "MF001"},
                {"name": "Technology", "code": "TC001"},
                {"name": "Services", "code": "SV001"},
                {"name": "Energy", "code": "EN001"}
            ]
        }
        return expanded_defaults.get(filename, [])
    
    def get_countries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get countries data with optional limit."""
        with self._cache_lock:
            if 'countries' not in self._cache:
                self._cache['countries'] = self._load_file('countries.json')
            
            data = self._cache['countries']
            return data[:limit] if limit else data
    
    def get_products(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get products data with optional limit."""
        with self._cache_lock:
            if 'products' not in self._cache:
                self._cache['products'] = self._load_file('products.json')
            
            data = self._cache['products']
            return data[:limit] if limit else data
    
    def get_sectors(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get sectors data with optional limit."""
        with self._cache_lock:
            if 'sectors' not in self._cache:
                self._cache['sectors'] = self._load_file('sectors.json')
            
            data = self._cache['sectors']
            return data[:limit] if limit else data
    
    @lru_cache(maxsize=1000)
    def find_country_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Find a country by its code."""
        countries = self.get_countries()
        for country in countries:
            if country.get('code') == code or country.get('ISO2') == code:
                return country
        return None
    
    @lru_cache(maxsize=1000)
    def find_product_by_hs6(self, hs6_code: str) -> Optional[Dict[str, Any]]:
        """Find a product by its HS6 code."""
        products = self.get_products()
        for product in products:
            if product.get('hs6') == hs6_code:
                return product
        return None
    
    @lru_cache(maxsize=1000)
    def find_sector_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a sector by its name."""
        sectors = self.get_sectors()
        for sector in sectors:
            if sector.get('name') == name:
                return sector
        return None
    
    @lru_cache(maxsize=1000)
    def find_sector_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Find a sector by its code."""
        sectors = self.get_sectors()
        for sector in sectors:
            if sector.get('code') == code:
                return sector
        return None
    
    def search_countries(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search countries by name or code."""
        countries = self.get_countries()
        query = query.lower()
        results = []
        
        for country in countries:
            name = country.get('name', '').lower()
            code = country.get('code', '').lower()
            iso2 = country.get('ISO2', '').lower()
            
            if (query in name or query in code or query in iso2):
                results.append(country)
                if len(results) >= limit:
                    break
        
        return results
    
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search products by HS6 code or description."""
        products = self.get_products()
        query = query.lower()
        results = []
        
        for product in products:
            hs6 = product.get('hs6', '').lower()
            description = product.get('description', '').lower()
            
            if query in hs6 or query in description:
                results.append(product)
                if len(results) >= limit:
                    break
        
        return results
    
    def clear_cache(self):
        """Clear all cached data."""
        with self._cache_lock:
            self._cache.clear()
        # Clear LRU caches
        self.find_country_by_code.cache_clear()
        self.find_product_by_hs6.cache_clear()
        self.find_sector_by_name.cache_clear()
        self.find_sector_by_code.cache_clear()

# Global config service instance
_config_service = None

def get_config_service() -> ConfigService:
    """Get the global config service instance."""
    global _config_service
    if _config_service is None:
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        _config_service = ConfigService(config_dir)
    return _config_service
