#!/usr/bin/env python3
"""
Quick test script to verify the dynamic country lookup function works correctly.
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from scrapers.santander_scraper import get_santander_country_code

def test_country_lookup():
    """Test the dynamic country lookup function."""
    print("Testing dynamic country lookup function...")
    
    # Test cases
    test_cases = [
        ("ESP", "Spain (3-letter code)"),
        ("ES", "Spain (2-letter code if exists)"),
        ("Spain", "Spain (by name)"),
        ("USA", "United States (3-letter code)"),
        ("FR", "France"),
        ("DEU", "Germany"),
        ("INVALID", "Invalid country code"),
    ]
    
    for country_code, description in test_cases:
        print(f"\n🔍 Testing {description}: '{country_code}'")
        result = get_santander_country_code(country_code)
        if result:
            print(f"✅ Found Santander code: {result}")
        else:
            print(f"❌ No mapping found")
    
    print(f"\n{'='*50}")
    print("Test completed!")

if __name__ == "__main__":
    test_country_lookup()
