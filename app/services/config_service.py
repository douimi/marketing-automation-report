"""
Configuration service for lazy loading and caching of large JSON files.
This service prevents memory issues by loading data on-demand.
"""
import json
import os
from typing import List, Dict, Optional, Any
from functools import lru_cache
import threading

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
        """Load a JSON config file."""
        config_path = self._get_config_path(filename)
        
        if not os.path.exists(config_path):
            # Return default data for missing files
            return self._get_default_data(filename)
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {config_path}: {e}. Returning default data.")
            return self._get_default_data(filename)
    
    def _get_default_data(self, filename: str) -> List[Dict[str, Any]]:
        """Get default data for a config file."""
        defaults = {
            'countries.json': [{"name": "United States", "code": "US", "iso_numeric": "840"}],
            'products.json': [{"hs6": "010101", "description": "Live horses"}],
            'sectors.json': [{"name": "Agriculture"}]
        }
        return defaults.get(filename, [])
    
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

# Global config service instance
_config_service = None

def get_config_service() -> ConfigService:
    """Get the global config service instance."""
    global _config_service
    if _config_service is None:
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        _config_service = ConfigService(config_dir)
    return _config_service
