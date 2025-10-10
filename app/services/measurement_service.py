"""
Measurement Service for handling unit conversions.
Supports length, mass, volume, area, and temperature conversions.
"""

import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MeasurementService:
    """Service for handling measurement unit conversions."""
    
    def __init__(self):
        # Define conversion factors to base units
        self.conversions = {
            'length': {
                'base_unit': 'meters',
                'units': {
                    # Metric
                    'millimeters': 0.001,
                    'centimeters': 0.01,
                    'meters': 1.0,
                    'kilometers': 1000.0,
                    # Imperial/US
                    'inches': 0.0254,
                    'feet': 0.3048,
                    'yards': 0.9144,
                    'miles': 1609.344,
                    # Nautical
                    'nautical_miles': 1852.0,
                    # Other
                    'micrometers': 0.000001,
                    'nanometers': 0.000000001,
                    'angstroms': 0.0000000001,
                    'light_years': 9.461e15,
                    'parsecs': 3.086e16,
                    'astronomical_units': 1.496e11,
                }
            },
            'mass': {
                'base_unit': 'kilograms',
                'units': {
                    # Metric
                    'milligrams': 0.000001,
                    'grams': 0.001,
                    'kilograms': 1.0,
                    'metric_tons': 1000.0,
                    # Imperial/US
                    'ounces': 0.0283495,
                    'pounds': 0.453592,
                    'stones': 6.35029,
                    'tons_us': 907.185,
                    'tons_uk': 1016.05,
                    # Other
                    'carats': 0.0002,
                    'grains': 0.0000647989,
                    'troy_ounces': 0.0311035,
                    'troy_pounds': 0.373242,
                }
            },
            'volume': {
                'base_unit': 'liters',
                'units': {
                    # Metric
                    'milliliters': 0.001,
                    'liters': 1.0,
                    'cubic_centimeters': 0.001,
                    'cubic_meters': 1000.0,
                    # US Liquid
                    'fluid_ounces_us': 0.0295735,
                    'cups_us': 0.236588,
                    'pints_us': 0.473176,
                    'quarts_us': 0.946353,
                    'gallons_us': 3.78541,
                    # UK Imperial
                    'fluid_ounces_uk': 0.0284131,
                    'pints_uk': 0.568261,
                    'quarts_uk': 1.13652,
                    'gallons_uk': 4.54609,
                    # Other
                    'cubic_inches': 0.0163871,
                    'cubic_feet': 28.3168,
                    'cubic_yards': 764.555,
                    'tablespoons': 0.0147868,
                    'teaspoons': 0.00492892,
                }
            },
            'area': {
                'base_unit': 'square_meters',
                'units': {
                    # Metric
                    'square_millimeters': 0.000001,
                    'square_centimeters': 0.0001,
                    'square_meters': 1.0,
                    'square_kilometers': 1000000.0,
                    'hectares': 10000.0,
                    'ares': 100.0,
                    # Imperial/US
                    'square_inches': 0.00064516,
                    'square_feet': 0.092903,
                    'square_yards': 0.836127,
                    'square_miles': 2589988.11,
                    'acres': 4046.86,
                    # Other
                    'square_rods': 25.2929,
                    'square_perches': 25.2929,
                }
            },
            'temperature': {
                'base_unit': 'celsius',
                'special': True  # Temperature requires special conversion formulas
            }
        }
        
        # Unit display names
        self.unit_names = {
            # Length
            'millimeters': 'Millimeters (mm)',
            'centimeters': 'Centimeters (cm)',
            'meters': 'Meters (m)',
            'kilometers': 'Kilometers (km)',
            'inches': 'Inches (in)',
            'feet': 'Feet (ft)',
            'yards': 'Yards (yd)',
            'miles': 'Miles (mi)',
            'nautical_miles': 'Nautical Miles',
            'micrometers': 'Micrometers (μm)',
            'nanometers': 'Nanometers (nm)',
            'angstroms': 'Angstroms (Å)',
            'light_years': 'Light Years',
            'parsecs': 'Parsecs',
            'astronomical_units': 'Astronomical Units (AU)',
            
            # Mass
            'milligrams': 'Milligrams (mg)',
            'grams': 'Grams (g)',
            'kilograms': 'Kilograms (kg)',
            'metric_tons': 'Metric Tons (t)',
            'ounces': 'Ounces (oz)',
            'pounds': 'Pounds (lb)',
            'stones': 'Stones (st)',
            'tons_us': 'US Tons',
            'tons_uk': 'UK Tons',
            'carats': 'Carats',
            'grains': 'Grains',
            'troy_ounces': 'Troy Ounces',
            'troy_pounds': 'Troy Pounds',
            
            # Volume
            'milliliters': 'Milliliters (ml)',
            'liters': 'Liters (l)',
            'cubic_centimeters': 'Cubic Centimeters (cm³)',
            'cubic_meters': 'Cubic Meters (m³)',
            'fluid_ounces_us': 'US Fluid Ounces (fl oz)',
            'cups_us': 'US Cups',
            'pints_us': 'US Pints (pt)',
            'quarts_us': 'US Quarts (qt)',
            'gallons_us': 'US Gallons (gal)',
            'fluid_ounces_uk': 'UK Fluid Ounces (fl oz)',
            'pints_uk': 'UK Pints (pt)',
            'quarts_uk': 'UK Quarts (qt)',
            'gallons_uk': 'UK Gallons (gal)',
            'cubic_inches': 'Cubic Inches (in³)',
            'cubic_feet': 'Cubic Feet (ft³)',
            'cubic_yards': 'Cubic Yards (yd³)',
            'tablespoons': 'Tablespoons (tbsp)',
            'teaspoons': 'Teaspoons (tsp)',
            
            # Area
            'square_millimeters': 'Square Millimeters (mm²)',
            'square_centimeters': 'Square Centimeters (cm²)',
            'square_meters': 'Square Meters (m²)',
            'square_kilometers': 'Square Kilometers (km²)',
            'hectares': 'Hectares (ha)',
            'ares': 'Ares (a)',
            'square_inches': 'Square Inches (in²)',
            'square_feet': 'Square Feet (ft²)',
            'square_yards': 'Square Yards (yd²)',
            'square_miles': 'Square Miles (mi²)',
            'acres': 'Acres (ac)',
            'square_rods': 'Square Rods',
            'square_perches': 'Square Perches',
            
            # Temperature
            'celsius': 'Celsius (°C)',
            'fahrenheit': 'Fahrenheit (°F)',
            'kelvin': 'Kelvin (K)',
            'rankine': 'Rankine (°R)',
            'reaumur': 'Réaumur (°Ré)',
        }
        
        # Popular units for each category
        self.popular_units = {
            'length': ['meters', 'feet', 'centimeters', 'inches', 'kilometers', 'miles'],
            'mass': ['kilograms', 'pounds', 'grams', 'ounces', 'metric_tons', 'tons_us'],
            'volume': ['liters', 'gallons_us', 'milliliters', 'fluid_ounces_us', 'cubic_meters', 'cubic_feet'],
            'area': ['square_meters', 'square_feet', 'square_kilometers', 'square_miles', 'hectares', 'acres'],
            'temperature': ['celsius', 'fahrenheit', 'kelvin']
        }

    def get_measurement_categories(self) -> List[Dict]:
        """Get list of measurement categories."""
        return [
            {'id': 'length', 'name': 'Length', 'icon': 'fa-ruler'},
            {'id': 'mass', 'name': 'Mass/Weight', 'icon': 'fa-weight'},
            {'id': 'volume', 'name': 'Volume', 'icon': 'fa-flask'},
            {'id': 'area', 'name': 'Area/Surface', 'icon': 'fa-square'},
            {'id': 'temperature', 'name': 'Temperature', 'icon': 'fa-thermometer-half'}
        ]

    def get_units_for_category(self, category: str) -> List[Dict]:
        """Get list of units for a specific category."""
        if category not in self.conversions:
            return []
        
        units = []
        popular = self.popular_units.get(category, [])
        
        if category == 'temperature':
            # Special handling for temperature
            temp_units = ['celsius', 'fahrenheit', 'kelvin', 'rankine', 'reaumur']
            for unit in temp_units:
                units.append({
                    'code': unit,
                    'name': self.unit_names.get(unit, unit),
                    'popular': unit in popular
                })
        else:
            # Regular units with conversion factors
            category_data = self.conversions[category]
            
            # Add popular units first
            for unit in popular:
                if unit in category_data['units']:
                    units.append({
                        'code': unit,
                        'name': self.unit_names.get(unit, unit),
                        'popular': True
                    })
            
            # Add remaining units
            remaining_units = set(category_data['units'].keys()) - set(popular)
            for unit in sorted(remaining_units):
                units.append({
                    'code': unit,
                    'name': self.unit_names.get(unit, unit),
                    'popular': False
                })
        
        return units

    def convert_measurement(self, value: float, from_unit: str, to_unit: str, category: str) -> Optional[Dict]:
        """
        Convert a measurement from one unit to another.
        
        Args:
            value: The value to convert
            from_unit: Source unit code
            to_unit: Target unit code
            category: Measurement category (length, mass, volume, area, temperature)
            
        Returns:
            Dictionary with conversion result or None if failed
        """
        try:
            if category not in self.conversions:
                return None
            
            if from_unit == to_unit:
                return {
                    'original_value': value,
                    'original_unit': from_unit,
                    'converted_value': value,
                    'converted_unit': to_unit,
                    'category': category,
                    'formula': f"{value} {from_unit} = {value} {to_unit}",
                    'timestamp': datetime.now().isoformat()
                }
            
            if category == 'temperature':
                converted_value = self._convert_temperature(value, from_unit, to_unit)
            else:
                converted_value = self._convert_regular_unit(value, from_unit, to_unit, category)
            
            if converted_value is None:
                return None
            
            return {
                'original_value': value,
                'original_unit': from_unit,
                'converted_value': converted_value,
                'converted_unit': to_unit,
                'category': category,
                'formula': self._get_conversion_formula(value, from_unit, to_unit, category),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return None

    def _convert_regular_unit(self, value: float, from_unit: str, to_unit: str, category: str) -> Optional[float]:
        """Convert between regular units using conversion factors."""
        category_data = self.conversions[category]
        
        if from_unit not in category_data['units'] or to_unit not in category_data['units']:
            return None
        
        # Convert to base unit first
        base_value = value * category_data['units'][from_unit]
        
        # Convert from base unit to target unit
        converted_value = base_value / category_data['units'][to_unit]
        
        return converted_value

    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """Convert temperature between different scales."""
        # First convert to Celsius
        if from_unit == 'celsius':
            celsius = value
        elif from_unit == 'fahrenheit':
            celsius = (value - 32) * 5/9
        elif from_unit == 'kelvin':
            celsius = value - 273.15
        elif from_unit == 'rankine':
            celsius = (value - 491.67) * 5/9
        elif from_unit == 'reaumur':
            celsius = value * 5/4
        else:
            return None
        
        # Then convert from Celsius to target unit
        if to_unit == 'celsius':
            return celsius
        elif to_unit == 'fahrenheit':
            return celsius * 9/5 + 32
        elif to_unit == 'kelvin':
            return celsius + 273.15
        elif to_unit == 'rankine':
            return (celsius + 273.15) * 9/5
        elif to_unit == 'reaumur':
            return celsius * 4/5
        else:
            return None

    def _get_conversion_formula(self, value: float, from_unit: str, to_unit: str, category: str) -> str:
        """Generate a conversion formula string."""
        if category == 'temperature':
            return self._get_temperature_formula(value, from_unit, to_unit)
        else:
            category_data = self.conversions[category]
            if from_unit in category_data['units'] and to_unit in category_data['units']:
                factor = category_data['units'][from_unit] / category_data['units'][to_unit]
                return f"{value} {from_unit} × {factor:.6f} = {value * factor:.6f} {to_unit}"
            return f"{value} {from_unit} = ? {to_unit}"

    def _get_temperature_formula(self, value: float, from_unit: str, to_unit: str) -> str:
        """Generate temperature conversion formula."""
        formulas = {
            ('celsius', 'fahrenheit'): f"({value}°C × 9/5) + 32 = {(value * 9/5 + 32):.2f}°F",
            ('fahrenheit', 'celsius'): f"({value}°F - 32) × 5/9 = {((value - 32) * 5/9):.2f}°C",
            ('celsius', 'kelvin'): f"{value}°C + 273.15 = {(value + 273.15):.2f}K",
            ('kelvin', 'celsius'): f"{value}K - 273.15 = {(value - 273.15):.2f}°C",
            ('fahrenheit', 'kelvin'): f"({value}°F - 32) × 5/9 + 273.15 = {((value - 32) * 5/9 + 273.15):.2f}K",
            ('kelvin', 'fahrenheit'): f"({value}K - 273.15) × 9/5 + 32 = {((value - 273.15) * 9/5 + 32):.2f}°F",
        }
        
        key = (from_unit, to_unit)
        return formulas.get(key, f"{value} {from_unit} = ? {to_unit}")

    def get_conversion_info(self, category: str) -> Dict:
        """Get information about a measurement category."""
        info = {
            'length': {
                'description': 'Length measurements including metric, imperial, and astronomical units',
                'base_unit': 'meters',
                'examples': ['Converting meters to feet', 'Miles to kilometers', 'Inches to centimeters']
            },
            'mass': {
                'description': 'Mass and weight measurements including metric, imperial, and specialty units',
                'base_unit': 'kilograms',
                'examples': ['Converting kilograms to pounds', 'Grams to ounces', 'Tons to metric tons']
            },
            'volume': {
                'description': 'Volume and capacity measurements including liquid and dry measures',
                'base_unit': 'liters',
                'examples': ['Converting liters to gallons', 'Milliliters to fluid ounces', 'Cubic meters to cubic feet']
            },
            'area': {
                'description': 'Area and surface measurements including metric, imperial, and land units',
                'base_unit': 'square_meters',
                'examples': ['Converting square meters to square feet', 'Hectares to acres', 'Square kilometers to square miles']
            },
            'temperature': {
                'description': 'Temperature measurements between different scales',
                'base_unit': 'celsius',
                'examples': ['Converting Celsius to Fahrenheit', 'Kelvin to Celsius', 'Fahrenheit to Kelvin']
            }
        }
        
        return info.get(category, {})

    def format_result(self, result: Dict) -> str:
        """Format conversion result for display."""
        if not result:
            return "Conversion failed"
        
        original_unit_name = self.unit_names.get(result['original_unit'], result['original_unit'])
        converted_unit_name = self.unit_names.get(result['converted_unit'], result['converted_unit'])
        
        # Format numbers appropriately
        original_value = result['original_value']
        converted_value = result['converted_value']
        
        # Use appropriate decimal places
        if abs(converted_value) >= 1000:
            converted_str = f"{converted_value:,.2f}"
        elif abs(converted_value) >= 1:
            converted_str = f"{converted_value:.4f}"
        else:
            converted_str = f"{converted_value:.6f}"
        
        if abs(original_value) >= 1000:
            original_str = f"{original_value:,.2f}"
        elif abs(original_value) >= 1:
            original_str = f"{original_value:.4f}"
        else:
            original_str = f"{original_value:.6f}"
        
        return f"{original_str} {original_unit_name} = {converted_str} {converted_unit_name}"

# Global instance
measurement_service = MeasurementService()
