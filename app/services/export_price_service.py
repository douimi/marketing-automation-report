"""
Export Price Service for calculating export costs with different Incoterms.
Handles EXW, FOB/FCA, CIF, and DDP pricing calculations.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExportPriceService:
    """Service for handling export price calculations with Incoterms."""
    
    def __init__(self):
        # Define Incoterms and their responsibilities
        self.incoterms = {
            'EXW': {
                'name': 'Ex Works',
                'description': 'Seller delivers when it places the goods at the disposal of the buyer at the seller\'s premises',
                'seller_costs': ['value_of_goods'],
                'buyer_costs': ['handling_carriage_before', 'export_customs', 'loading_costs', 'main_transport', 
                               'transport_insurance', 'insurance_freight', 'handling_arrival', 'customs_duties', 
                               'import_taxes', 'import_customs', 'carriage_after']
            },
            'FOB': {
                'name': 'Free On Board',
                'description': 'Seller delivers when the goods pass the ship\'s rail at the named port of shipment',
                'seller_costs': ['value_of_goods', 'handling_carriage_before', 'export_customs', 'loading_costs'],
                'buyer_costs': ['main_transport', 'transport_insurance', 'insurance_freight', 'handling_arrival', 
                               'customs_duties', 'import_taxes', 'import_customs', 'carriage_after']
            },
            'FCA': {
                'name': 'Free Carrier',
                'description': 'Seller delivers the goods to the carrier nominated by the buyer at the seller\'s premises',
                'seller_costs': ['value_of_goods', 'handling_carriage_before', 'export_customs', 'loading_costs'],
                'buyer_costs': ['main_transport', 'transport_insurance', 'insurance_freight', 'handling_arrival', 
                               'customs_duties', 'import_taxes', 'import_customs', 'carriage_after']
            },
            'CIF': {
                'name': 'Cost, Insurance and Freight',
                'description': 'Seller delivers when the goods pass the ship\'s rail in the port of shipment',
                'seller_costs': ['value_of_goods', 'handling_carriage_before', 'export_customs', 'loading_costs', 
                                'main_transport', 'transport_insurance', 'insurance_freight'],
                'buyer_costs': ['handling_arrival', 'customs_duties', 'import_taxes', 'import_customs', 'carriage_after']
            },
            'DDP': {
                'name': 'Delivered Duty Paid',
                'description': 'Seller delivers when the goods are placed at the disposal of the buyer, cleared for import',
                'seller_costs': ['value_of_goods', 'handling_carriage_before', 'export_customs', 'loading_costs', 
                                'main_transport', 'transport_insurance', 'insurance_freight', 'handling_arrival', 
                                'customs_duties', 'import_taxes', 'import_customs', 'carriage_after'],
                'buyer_costs': []
            }
        }
        
        # Cost component definitions
        self.cost_components = {
            'value_of_goods': {
                'name': 'Value of the goods (loaded on leaving the factory)',
                'type': 'fixed',
                'required': True,
                'description': 'Base value of goods at factory'
            },
            'handling_carriage_before': {
                'name': 'Cost of handling carriage before (from the factory to the port or to the airport)',
                'type': 'fixed',
                'required': False,
                'description': 'Pre-carriage costs'
            },
            'export_customs': {
                'name': 'Fixed cost of export Customs formalities',
                'type': 'fixed',
                'required': False,
                'description': 'Export customs clearance fees'
            },
            'loading_costs': {
                'name': 'Handling costs (loading onto the airplane, the vessel or the truck in the case of groupage) in originating terminal',
                'type': 'fixed',
                'required': False,
                'description': 'Terminal handling charges at origin'
            },
            'main_transport': {
                'name': 'Total cost of the main transport (by air, sea or land)',
                'type': 'fixed',
                'required': False,
                'description': 'Main freight charges'
            },
            'transport_insurance': {
                'name': 'Cost of insurance for the main transport',
                'type': 'fixed',
                'required': False,
                'description': 'Transit insurance premium'
            },
            'insurance_freight': {
                'name': 'Cost of the Insurance and Freight',
                'type': 'fixed',
                'required': False,
                'description': 'Combined insurance and freight cost'
            },
            'handling_arrival': {
                'name': 'Cost of handling on arrival at the (air)port or bulk-breaking platform',
                'type': 'fixed',
                'required': False,
                'description': 'Terminal handling charges at destination'
            },
            'customs_duties': {
                'name': 'Customs Duties',
                'type': 'percentage',
                'required': False,
                'description': 'Import duties as percentage of CIF value'
            },
            'import_taxes': {
                'name': 'Import taxes',
                'type': 'percentage',
                'required': False,
                'description': 'Import taxes as percentage of CIF value'
            },
            'import_customs': {
                'name': 'Cost of import Customs formalities (flat rate)',
                'type': 'fixed',
                'required': False,
                'description': 'Import customs clearance fees'
            },
            'carriage_after': {
                'name': 'Cost of carriage after (from the port (airport) to the buyer)',
                'type': 'fixed',
                'required': False,
                'description': 'On-carriage costs to final destination'
            }
        }

    def get_incoterms_list(self) -> List[Dict]:
        """Get list of available Incoterms."""
        return [
            {
                'code': code,
                'name': data['name'],
                'description': data['description']
            }
            for code, data in self.incoterms.items()
        ]

    def get_cost_components(self) -> Dict:
        """Get all cost components with their definitions."""
        return self.cost_components

    def calculate_export_price(self, costs: Dict, target_incoterm: str = 'DDP') -> Optional[Dict]:
        """
        Calculate export price breakdown for different Incoterms.
        
        Args:
            costs: Dictionary of cost values
            target_incoterm: Target Incoterm for calculation
            
        Returns:
            Dictionary with price breakdown or None if failed
        """
        try:
            if target_incoterm not in self.incoterms:
                return None
            
            # Validate and process input costs
            processed_costs = self._process_costs(costs)
            
            # Calculate prices for all Incoterms
            incoterm_prices = {}
            
            for incoterm_code in ['EXW', 'FOB', 'CIF', 'DDP']:
                price = self._calculate_incoterm_price(processed_costs, incoterm_code)
                incoterm_prices[incoterm_code] = {
                    'price': price,
                    'name': self.incoterms[incoterm_code]['name'],
                    'breakdown': self._get_cost_breakdown(processed_costs, incoterm_code)
                }
            
            # Calculate detailed breakdown
            detailed_breakdown = self._get_detailed_breakdown(processed_costs)
            
            return {
                'input_costs': processed_costs,
                'incoterm_prices': incoterm_prices,
                'detailed_breakdown': detailed_breakdown,
                'target_incoterm': target_incoterm,
                'target_price': incoterm_prices[target_incoterm]['price'],
                'calculation_date': datetime.now().isoformat(),
                'currency': 'USD'  # Default currency, can be made configurable
            }
            
        except Exception as e:
            logger.error(f"Export price calculation error: {e}")
            return None

    def _process_costs(self, costs: Dict) -> Dict:
        """Process and validate input costs."""
        processed = {}
        
        for component, definition in self.cost_components.items():
            value = costs.get(component, 0)
            
            if definition['type'] == 'percentage':
                # Ensure percentage values are in decimal form (e.g., 10% = 0.10)
                if isinstance(value, str) and value.endswith('%'):
                    value = float(value.rstrip('%')) / 100
                else:
                    value = float(value) if value else 0
                    # If value is > 1, assume it's a percentage and convert
                    if value > 1:
                        value = value / 100
            else:
                value = float(value) if value else 0
            
            processed[component] = value
        
        return processed

    def _calculate_incoterm_price(self, costs: Dict, incoterm: str) -> float:
        """Calculate price for a specific Incoterm."""
        if incoterm not in self.incoterms:
            return 0
        
        total_price = 0
        seller_costs = self.incoterms[incoterm]['seller_costs']
        
        # Add all seller costs
        for cost_component in seller_costs:
            if cost_component in costs:
                if self.cost_components[cost_component]['type'] == 'percentage':
                    # For percentage costs, calculate based on appropriate base
                    base_value = self._get_percentage_base(costs, cost_component, incoterm)
                    total_price += base_value * costs[cost_component]
                else:
                    total_price += costs[cost_component]
        
        return total_price

    def _get_percentage_base(self, costs: Dict, cost_component: str, incoterm: str) -> float:
        """Get the base value for percentage calculations."""
        if cost_component in ['customs_duties', 'import_taxes']:
            # Customs duties and import taxes are typically calculated on CIF value
            cif_value = self._calculate_incoterm_price(costs, 'CIF')
            return cif_value if cif_value > 0 else (
                costs['value_of_goods'] + 
                costs.get('handling_carriage_before', 0) + 
                costs.get('export_customs', 0) + 
                costs.get('loading_costs', 0) + 
                costs.get('main_transport', 0) + 
                costs.get('transport_insurance', 0) + 
                costs.get('insurance_freight', 0)
            )
        else:
            # Default to goods value
            return costs.get('value_of_goods', 0)

    def _get_cost_breakdown(self, costs: Dict, incoterm: str) -> Dict:
        """Get detailed cost breakdown for an Incoterm."""
        breakdown = {
            'seller_costs': {},
            'buyer_costs': {},
            'seller_total': 0,
            'buyer_total': 0
        }
        
        incoterm_data = self.incoterms[incoterm]
        
        # Calculate seller costs
        for cost_component in incoterm_data['seller_costs']:
            if cost_component in costs and costs[cost_component] > 0:
                if self.cost_components[cost_component]['type'] == 'percentage':
                    base_value = self._get_percentage_base(costs, cost_component, incoterm)
                    cost_value = base_value * costs[cost_component]
                else:
                    cost_value = costs[cost_component]
                
                breakdown['seller_costs'][cost_component] = {
                    'value': cost_value,
                    'name': self.cost_components[cost_component]['name'],
                    'type': self.cost_components[cost_component]['type']
                }
                breakdown['seller_total'] += cost_value
        
        # Calculate buyer costs
        for cost_component in incoterm_data['buyer_costs']:
            if cost_component in costs and costs[cost_component] > 0:
                if self.cost_components[cost_component]['type'] == 'percentage':
                    base_value = self._get_percentage_base(costs, cost_component, incoterm)
                    cost_value = base_value * costs[cost_component]
                else:
                    cost_value = costs[cost_component]
                
                breakdown['buyer_costs'][cost_component] = {
                    'value': cost_value,
                    'name': self.cost_components[cost_component]['name'],
                    'type': self.cost_components[cost_component]['type']
                }
                breakdown['buyer_total'] += cost_value
        
        return breakdown

    def _get_detailed_breakdown(self, costs: Dict) -> Dict:
        """Get detailed breakdown of all costs."""
        breakdown = {}
        
        for component, value in costs.items():
            if value > 0:
                breakdown[component] = {
                    'value': value,
                    'name': self.cost_components[component]['name'],
                    'type': self.cost_components[component]['type'],
                    'description': self.cost_components[component]['description']
                }
        
        return breakdown

    def get_incoterm_comparison(self, costs: Dict) -> Dict:
        """Get comparison of all Incoterms for given costs."""
        calculation = self.calculate_export_price(costs)
        
        if not calculation:
            return {}
        
        comparison = {}
        for incoterm, data in calculation['incoterm_prices'].items():
            comparison[incoterm] = {
                'code': incoterm,
                'name': data['name'],
                'price': data['price'],
                'seller_total': data['breakdown']['seller_total'],
                'buyer_total': data['breakdown']['buyer_total']
            }
        
        return comparison

    def validate_costs(self, costs: Dict) -> Tuple[bool, List[str]]:
        """Validate input costs and return errors if any."""
        errors = []
        
        # Check if value of goods is provided (required)
        if not costs.get('value_of_goods', 0):
            errors.append("Value of goods is required")
        
        # Check for negative values
        for component, value in costs.items():
            if component in self.cost_components:
                try:
                    float_value = float(value) if value else 0
                    if float_value < 0:
                        errors.append(f"{self.cost_components[component]['name']} cannot be negative")
                except (ValueError, TypeError):
                    errors.append(f"Invalid value for {self.cost_components[component]['name']}")
        
        # Check percentage values
        for component, value in costs.items():
            if component in self.cost_components and self.cost_components[component]['type'] == 'percentage':
                try:
                    float_value = float(value) if value else 0
                    if float_value > 100:  # Assuming input as percentage, not decimal
                        errors.append(f"{self.cost_components[component]['name']} cannot exceed 100%")
                except (ValueError, TypeError):
                    pass  # Already caught above
        
        return len(errors) == 0, errors

    def get_cost_explanation(self, component: str) -> Dict:
        """Get detailed explanation of a cost component."""
        if component not in self.cost_components:
            return {}
        
        comp_data = self.cost_components[component]
        
        # Determine which Incoterms include this cost for seller
        seller_incoterms = []
        buyer_incoterms = []
        
        for incoterm, data in self.incoterms.items():
            if component in data['seller_costs']:
                seller_incoterms.append(incoterm)
            if component in data['buyer_costs']:
                buyer_incoterms.append(incoterm)
        
        return {
            'name': comp_data['name'],
            'description': comp_data['description'],
            'type': comp_data['type'],
            'required': comp_data['required'],
            'seller_responsible': seller_incoterms,
            'buyer_responsible': buyer_incoterms
        }

    def format_price(self, price: float, currency: str = 'USD') -> str:
        """Format price for display."""
        return f"{currency} {price:,.2f}"

    def export_calculation_summary(self, calculation: Dict) -> str:
        """Export calculation summary as formatted text."""
        if not calculation:
            return "No calculation data available"
        
        summary = f"Export Price Calculation Summary\n"
        summary += f"Generated: {calculation['calculation_date']}\n"
        summary += f"Currency: {calculation['currency']}\n\n"
        
        summary += "Incoterm Prices:\n"
        for incoterm, data in calculation['incoterm_prices'].items():
            summary += f"  {incoterm} ({data['name']}): {self.format_price(data['price'], calculation['currency'])}\n"
        
        summary += f"\nTarget Incoterm: {calculation['target_incoterm']}\n"
        summary += f"Target Price: {self.format_price(calculation['target_price'], calculation['currency'])}\n"
        
        return summary

# Global instance
export_price_service = ExportPriceService()
