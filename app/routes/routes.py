from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash, session, jsonify, copy_current_request_context, send_from_directory
from flask_login import login_required, current_user
from ..services.report_service import ReportGenerationService, get_country_name_from_code
from ..services.data_processor import MarketDataProcessor
from datetime import datetime
import threading
from flask import g
from werkzeug.local import LocalProxy
import time
import uuid
import os
import json

main_bp = Blueprint('main', __name__, template_folder='../templates')

# Global in-memory cache for reports (keyed by report_id)
reports_cache = {}

@main_bp.route('/health')
def health_check():
    """Simple health check endpoint without authentication."""
    return {'status': 'ok', 'message': 'Application is running'}, 200

@main_bp.route('/test')
def test_page():
    """Simple test page without external dependencies."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Test Page</h1>
            <p>This is a simple test page without external dependencies.</p>
            <p>If you can see this page, the Flask application is working correctly.</p>
            <p>The issue is likely with external resources (CDNs, images, etc.) in the main templates.</p>
        </div>
    </body>
    </html>
    '''

@main_bp.route('/test_session')
def test_session():
    """Test session functionality."""
    import uuid
    if 'test_id' not in session:
        session['test_id'] = str(uuid.uuid4())
        session.modified = True
    
    return jsonify({
        'test_id': session.get('test_id'),
        'session_keys': list(session.keys()),
        'is_authenticated': current_user.is_authenticated if current_user else False
    })

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/markets')
@login_required
def markets_page():
    """Redirect to services page for backward compatibility."""
    return redirect(url_for('main.services_page'))

@main_bp.route('/services')
def services_page():
    """Display the services page with all available services."""
    return render_template('services.html')

@main_bp.route('/financing-operations')
@login_required
def financing_operations():
    """Display the financing operations page."""
    return render_template('financing_operations.html')

@main_bp.route('/payment-means')
@login_required
def payment_means():
    """Display the payment means page."""
    return render_template('payment_means.html')

@main_bp.route('/risk-management')
@login_required
def risk_management():
    """Display the risk management page."""
    return render_template('risk_management.html')

@main_bp.route('/incoterms')
@login_required
def incoterms():
    """Display the incoterms page."""
    return render_template('incoterms.html')

@main_bp.route('/hs-customs-classification')
def hs_customs_classification():
    """Display the HS Customs Classification page."""
    return render_template('hs_customs_classification.html')

@main_bp.route('/currency-converter')
def currency_converter():
    """Display the Currency Converter page."""
    from ..services.currency_service import currency_service
    
    # Get all supported currencies for the dropdown
    currencies = currency_service.get_supported_currencies()
    api_status = currency_service.get_api_status()
    
    return render_template('currency_converter.html', 
                         currencies=currencies, 
                         api_status=api_status)

@main_bp.route('/api/convert-currency', methods=['POST'])
def api_convert_currency():
    """API endpoint for currency conversion."""
    from ..services.currency_service import currency_service
    
    try:
        data = request.get_json()
        
        amount = float(data.get('amount', 0))
        from_currency = data.get('from_currency', 'USD').upper()
        to_currency = data.get('to_currency', 'EUR').upper()
        
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400
        
        result = currency_service.convert_currency(amount, from_currency, to_currency)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': 'Currency conversion failed. Please try again.'}), 500
            
    except ValueError:
        return jsonify({'error': 'Invalid amount. Please enter a valid number.'}), 400
    except Exception as e:
        return jsonify({'error': f'Conversion error: {str(e)}'}), 500

@main_bp.route('/api/exchange-rates/<base_currency>')
def api_exchange_rates(base_currency):
    """API endpoint to get exchange rates for a base currency."""
    from ..services.currency_service import currency_service
    
    try:
        base_currency = base_currency.upper()
        rates_data = currency_service.get_exchange_rates(base_currency)
        
        if rates_data:
            return jsonify(rates_data)
        else:
            return jsonify({'error': 'Unable to fetch exchange rates'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Error fetching rates: {str(e)}'}), 500

@main_bp.route('/api/currencies')
def api_currencies():
    """API endpoint to get supported currencies."""
    from ..services.currency_service import currency_service
    
    try:
        currencies = currency_service.get_supported_currencies()
        return jsonify({'currencies': currencies})
    except Exception as e:
        return jsonify({'error': f'Error fetching currencies: {str(e)}'}), 500

@main_bp.route('/measurement-converter')
def measurement_converter():
    """Display the Measurement Converter page."""
    from ..services.measurement_service import measurement_service
    
    # Get measurement categories and units
    categories = measurement_service.get_measurement_categories()
    
    # Get units for each category
    units_by_category = {}
    for category in categories:
        units_by_category[category['id']] = measurement_service.get_units_for_category(category['id'])
    
    return render_template('measurement_converter.html', 
                         categories=categories,
                         units_by_category=units_by_category)

@main_bp.route('/api/convert-measurement', methods=['POST'])
def api_convert_measurement():
    """API endpoint for measurement conversion."""
    from ..services.measurement_service import measurement_service
    
    try:
        data = request.get_json()
        
        value = float(data.get('value', 0))
        from_unit = data.get('from_unit', '')
        to_unit = data.get('to_unit', '')
        category = data.get('category', '')
        
        if value == 0 and data.get('value') != 0:
            return jsonify({'error': 'Invalid value. Please enter a valid number.'}), 400
        
        if not all([from_unit, to_unit, category]):
            return jsonify({'error': 'Missing required parameters.'}), 400
        
        result = measurement_service.convert_measurement(value, from_unit, to_unit, category)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': 'Measurement conversion failed. Please check your units.'}), 500
            
    except ValueError:
        return jsonify({'error': 'Invalid value. Please enter a valid number.'}), 400
    except Exception as e:
        return jsonify({'error': f'Conversion error: {str(e)}'}), 500

@main_bp.route('/api/measurement-units/<category>')
def api_measurement_units(category):
    """API endpoint to get units for a measurement category."""
    from ..services.measurement_service import measurement_service
    
    try:
        units = measurement_service.get_units_for_category(category)
        info = measurement_service.get_conversion_info(category)
        
        return jsonify({
            'category': category,
            'units': units,
            'info': info
        })
    except Exception as e:
        return jsonify({'error': f'Error fetching units: {str(e)}'}), 500

@main_bp.route('/export-price-calculator')
def export_price_calculator():
    """Display the Export Price Calculator page."""
    from ..services.export_price_service import export_price_service
    
    # Get Incoterms and cost components
    incoterms = export_price_service.get_incoterms_list()
    cost_components = export_price_service.get_cost_components()
    
    return render_template('export_price_calculator.html', 
                         incoterms=incoterms,
                         cost_components=cost_components)

@main_bp.route('/api/calculate-export-price', methods=['POST'])
def api_calculate_export_price():
    """API endpoint for export price calculation."""
    from ..services.export_price_service import export_price_service
    
    try:
        data = request.get_json()
        
        costs = data.get('costs', {})
        target_incoterm = data.get('target_incoterm', 'DDP')
        
        # Validate costs
        is_valid, errors = export_price_service.validate_costs(costs)
        if not is_valid:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        result = export_price_service.calculate_export_price(costs, target_incoterm)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': 'Export price calculation failed. Please check your inputs.'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Calculation error: {str(e)}'}), 500

@main_bp.route('/api/incoterm-comparison', methods=['POST'])
def api_incoterm_comparison():
    """API endpoint for Incoterm comparison."""
    from ..services.export_price_service import export_price_service
    
    try:
        data = request.get_json()
        costs = data.get('costs', {})
        
        # Validate costs
        is_valid, errors = export_price_service.validate_costs(costs)
        if not is_valid:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        comparison = export_price_service.get_incoterm_comparison(costs)
        
        if comparison:
            return jsonify({'comparison': comparison})
        else:
            return jsonify({'error': 'Comparison calculation failed.'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Comparison error: {str(e)}'}), 500

@main_bp.route('/api/cost-explanation/<component>')
def api_cost_explanation(component):
    """API endpoint to get cost component explanation."""
    from ..services.export_price_service import export_price_service
    
    try:
        explanation = export_price_service.get_cost_explanation(component)
        
        if explanation:
            return jsonify(explanation)
        else:
            return jsonify({'error': 'Cost component not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Error fetching explanation: {str(e)}'}), 500

@main_bp.route('/business-trips')
def business_trips():
    """Display the Business Trips page."""
    return render_template('business_trips.html')

@main_bp.route('/trademark-protection')
def trademark_protection():
    """Display the Trademark Protection page."""
    return render_template('trademark_protection.html')

@main_bp.route('/patent-protection')
def patent_protection():
    """Display the Patent Protection page."""
    return render_template('patent_protection.html')

@main_bp.route('/emerging-markets')
def emerging_markets():
    """Display the Exporting to Emerging Markets page."""
    return render_template('emerging_markets.html')

@main_bp.route('/industry-information')
@login_required
def industry_information():
    """Display the Industry Information page with sub-services."""
    return render_template('industry_information.html')

@main_bp.route('/country-information')
def country_information():
    """Display the Country Information selection page."""
    return render_template('country_information.html')

@main_bp.route('/start_country_information', methods=['POST'])
def start_country_information():
    """Initialize country information (general presentation) and redirect to results."""
    try:
        destination_country_code = request.form.get('destination_country')
        
        if not destination_country_code:
            return jsonify({
                'status': 'error',
                'message': 'Please select a country.'
            }), 400
        
        # Build form_data for general presentation
        form_data = {
            'service_type': 'general-presentation',
            'destination_country_code': destination_country_code
        }
        
        # Get config service for country name lookup
        config_service = current_app.config.get('CONFIG_SERVICE')
        country = config_service.find_country_by_code(destination_country_code)
        form_data['destination_country_name'] = country.get('name') if country else None
        
        # Generate report ID and store form data
        report_id = str(uuid.uuid4())
        session['report_id'] = report_id
        session['report_form_data'] = form_data
        session['country_context'] = True  # Flag to indicate this is country information context
        session.modified = True
        
        global reports_cache
        reports_cache[report_id] = {
            'status': 'processing',
            'error_message': None,
            'service_type': 'general-presentation'
        }
        
        # Create a copy of the application context for the background thread
        @copy_current_request_context
        def generate_country_info_with_context():
            import time as _time
            t0 = _time.time()
            try:
                report_service = None
                print(f'[TIMING] Start country information generation: {round(_time.time() - t0, 2)}s')
                
                report_service = ReportGenerationService()
                if not report_service.driver:
                    reports_cache[report_id]['status'] = 'error'
                    reports_cache[report_id]['error_message'] = 'Failed to initialize Selenium WebDriver.'
                    return
                
                # Generate general presentation data
                raw_data = report_service.generate_santander_report_data(form_data['destination_country_code'], None)
                from ..services.data_processor import MarketDataProcessor
                data_processor = MarketDataProcessor()
                service_data = {
                    'market_data': data_processor.parse_raw_data(raw_data),
                    'openai_intro': report_service.generate_openai_intro(raw_data, form_data),
                    'openai_conclusion': report_service.generate_openai_conclusion(raw_data, form_data)
                }
                
                # Update the report with service data
                reports_cache[report_id].update({
                    'form_data': form_data,
                    'status': 'complete',
                    'error_message': None,
                    **service_data
                })
                
                print(f'[TIMING] Country information generation completed: {round(_time.time() - t0, 2)}s')
                current_app.logger.info(f"Country information generation completed")
                
            except Exception as e:
                current_app.logger.error(f"Country information generation failed: {e}", exc_info=True)
                reports_cache[report_id]['status'] = 'error'
                reports_cache[report_id]['error_message'] = str(e)
            finally:
                if report_service:
                    report_service.close_driver()
        
        # Start background task
        thread = threading.Thread(target=generate_country_info_with_context)
        thread.daemon = True
        thread.start()
        
        # Handle AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'success',
                'redirect_url': url_for('main.loading_page')
            })
        else:
            return redirect(url_for('main.loading_page'))
        
    except Exception as e:
        current_app.logger.error(f"Failed to start country information generation: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to start country information generation'
        })

@main_bp.route('/country/<country_code>/<service_type>')
def country_service(country_code, service_type):
    """Display individual service for a specific country."""
    # Check if service requires authentication (all except general-presentation)
    is_locked = service_type != 'general-presentation' and not current_user.is_authenticated
    
    # Get country name
    config_service = current_app.config.get('CONFIG_SERVICE')
    country = config_service.find_country_by_code(country_code)
    if not country:
        flash('Country not found.', 'error')
        return redirect(url_for('main.country_information'))
    
    # Build form_data for the specific service with pre-selected country
    form_data = {
        'service_type': service_type,
        'destination_country_code': country_code,
        'destination_country_name': country.get('name')
    }
    
    # Generate report ID and store form data
    report_id = str(uuid.uuid4())
    session['report_id'] = report_id
    session['report_form_data'] = form_data
    session['country_context'] = True  # Flag to indicate this is country information context
    session.modified = True
    
    global reports_cache
    
    # Initialize cache entry
    reports_cache[report_id] = {
        'status': 'processing',
        'error_message': None,
        'service_type': service_type
    }
    
    # If service is locked, return immediately with locked state
    if is_locked:
        reports_cache[report_id].update({
            'status': 'complete',
            'form_data': form_data,
            'is_locked': True
        })
        return redirect(url_for('main.report_page'))
    
    # Otherwise, proceed with normal processing
    # Create a copy of the application context for the background thread
    @copy_current_request_context
    def generate_country_service_with_context():
        import time as _time
        t0 = _time.time()
        try:
            report_service = None
            print(f'[TIMING] Start country service generation ({service_type}): {round(_time.time() - t0, 2)}s')
            
            report_service = ReportGenerationService()
            if not report_service.driver:
                reports_cache[report_id]['status'] = 'error'
                reports_cache[report_id]['error_message'] = 'Failed to initialize Selenium WebDriver.'
                return
            
            # Generate specific service data
            service_data = {}
            
            # Add default sector for services that don't require it but OpenAI might need it
            if 'sector' not in form_data:
                form_data['sector'] = 'General Business'
            
            if service_type == 'operating-business':
                service_data['operating_a_business_data'] = report_service.generate_santander_operating_a_business(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'tax-system':
                service_data['tax_system_data'] = report_service.generate_santander_tax_system(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'legal-environment':
                service_data['legal_environment_data'] = report_service.generate_santander_legal_environment(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'foreign-investment':
                service_data['foreign_investment_data'] = report_service.generate_santander_foreign_investment(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'business-practices':
                service_data['business_practices_data'] = report_service.generate_santander_business_practices(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'entry-requirements':
                service_data['entry_requirements_data'] = report_service.generate_santander_entry_requirements(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'practical-information':
                service_data['practical_information_data'] = report_service.generate_santander_practical_information(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'living-in-country':
                service_data['living_in_country_data'] = report_service.generate_santander_living_in_country(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'reaching-consumers':
                service_data['consumer_data'] = report_service.generate_santander_reaching_consumers(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'distributing-product':
                service_data['distribution_data'] = report_service.generate_santander_distributing_product(form_data['destination_country_code'], None, login_required=True)
            elif service_type == 'general-presentation':
                # Generate general presentation data for country context
                raw_data = report_service.generate_santander_report_data(form_data['destination_country_code'], None)
                from ..services.data_processor import MarketDataProcessor
                data_processor = MarketDataProcessor()
                service_data = {
                    'market_data': data_processor.parse_raw_data(raw_data),
                    'openai_intro': report_service.generate_openai_intro(raw_data, form_data),
                    'openai_conclusion': report_service.generate_openai_conclusion(raw_data, form_data)
                }
            
            # Update the report with service data
            reports_cache[report_id].update({
                'form_data': form_data,
                'status': 'complete',
                'error_message': None,
                **service_data
            })
            
            print(f'[TIMING] Country service generation completed: {round(_time.time() - t0, 2)}s')
            current_app.logger.info(f"Country service generation completed for {service_type}")
            
        except Exception as e:
            current_app.logger.error(f"Country service generation failed: {e}", exc_info=True)
            reports_cache[report_id]['status'] = 'error'
            reports_cache[report_id]['error_message'] = str(e)
        finally:
            if report_service:
                report_service.close_driver()
    
    # Start background task
    thread = threading.Thread(target=generate_country_service_with_context)
    thread.daemon = True
    thread.start()
    
    # Redirect to loading page
    return redirect(url_for('main.loading_page'))

@main_bp.route('/form', methods=['GET'])
@login_required
def form_page():
    # Only load sectors - countries and products use AJAX
    config_service = current_app.config.get('CONFIG_SERVICE')
    sectors = config_service.get_sectors()
    return render_template('form.html', sectors=sectors)

@main_bp.route('/service/<service_type>', methods=['GET'])
def service_form(service_type):
    """Display form for individual service generation."""
    # Check if service requires authentication (all except general-presentation)
    if service_type != 'general-presentation' and not current_user.is_authenticated:
        flash('Please login to access this service.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Define service configurations
    service_config = {
        'general-presentation': {
            'title': 'General Presentation',
            'description': 'Country overview with key demographics, economic indicators, and general market characteristics.',
            'icon': 'fas fa-info-circle',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'economic-political': {
            'title': 'Economic and Political Outline',
            'description': 'In-depth analysis of economic trends, political stability, and government policies.',
            'icon': 'fas fa-balance-scale',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'operating-business': {
            'title': 'Operating a Business',
            'description': 'Business setup procedures, legal forms, labor costs, and HR management requirements.',
            'icon': 'fas fa-briefcase',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'tax-system': {
            'title': 'Tax System',
            'description': 'Comprehensive tax information including corporate, individual, and consumption taxes.',
            'icon': 'fas fa-file-invoice-dollar',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'legal-environment': {
            'title': 'Legal Environment',
            'description': 'Legal framework, contract law, intellectual property protection, and dispute resolution.',
            'icon': 'fas fa-gavel',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'foreign-investment': {
            'title': 'Foreign Investment',
            'description': 'FDI regulations, investment protection, opportunities, and administrative procedures.',
            'icon': 'fas fa-globe-americas',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'business-practices': {
            'title': 'Business Practices',
            'description': 'Business culture, etiquette, working hours, and local business customs.',
            'icon': 'fas fa-handshake',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'entry-requirements': {
            'title': 'Entry Requirements',
            'description': 'Visa requirements, customs procedures, health precautions, and safety conditions.',
            'icon': 'fas fa-id-card',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'practical-information': {
            'title': 'Practical Information',
            'description': 'Transportation, dining, climate, electrical standards, and communication systems.',
            'icon': 'fas fa-info',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'living-in-country': {
            'title': 'Living in the Country',
            'description': 'Expatriate communities, housing, education, healthcare, and quality of life indicators.',
            'icon': 'fas fa-home',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'foreign-trade': {
            'title': 'Foreign Trade in Figures',
            'description': 'Trade statistics, main partners, export/import data, and monetary indicators.',
            'icon': 'fas fa-exchange-alt',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'reaching-consumers': {
            'title': 'Reaching the Consumer',
            'description': 'Consumer profile, purchasing behavior, marketing opportunities, and advertising regulations.',
            'icon': 'fas fa-users',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'distributing-product': {
            'title': 'Distributing a Product',
            'description': 'Distribution channels, retail sector evolution, e-commerce trends, and distance selling opportunities.',
            'icon': 'fas fa-truck',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'identify-suppliers': {
            'title': 'Identify a Supplier',
            'description': 'Production types, professional associations, marketplaces, trade shows, and manufacturer directories.',
            'icon': 'fas fa-search',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'trade-compliance': {
            'title': 'International Trade Compliance',
            'description': 'International conventions, trade regulations, customs procedures, and compliance requirements.',
            'icon': 'fas fa-gavel',
            'requires': ['destination_country'],
            'form_template': 'service_form_country_only.html'
        },
        'business-directories': {
            'title': 'Business Directories',
            'description': 'Find industry-specific business directories and commercial partners in your target country.',
            'icon': 'fas fa-building',
            'requires': ['industry', 'geographical_area'],
            'form_template': 'service_form_industry_country.html'
        },
        'import-export-flows': {
            'title': 'Import/Export Flows',
            'description': 'Product-specific trade flows between origin and destination countries with trend analysis.',
            'icon': 'fas fa-random',
            'requires': ['origin_country', 'destination_country', 'product'],
            'form_template': 'service_form_full.html'
        },
        'trade-shows': {
            'title': 'Trade Shows',
            'description': 'Upcoming trade shows and exhibitions in your target market and industry sector.',
            'icon': 'fas fa-calendar-alt',
            'requires': ['destination_country', 'sector'],
            'form_template': 'service_form_country_sector.html'
        },
        'market-access': {
            'title': 'Market Access Conditions',
            'description': 'Tariffs, trade remedies, and regulatory requirements for specific products and markets.',
            'icon': 'fas fa-door-open',
            'requires': ['origin_country', 'destination_country', 'product'],
            'form_template': 'service_form_full.html'
        },
        'online-marketplaces': {
            'title': 'Online Marketplaces',
            'description': 'Discover relevant online trading platforms and marketplaces for your industry and target market.',
            'icon': 'fas fa-shopping-cart',
            'requires': ['industry', 'geographical_area'],
            'form_template': 'service_form_online_marketplaces.html'
        },
        'professional-associations': {
            'title': 'Professional Associations',
            'description': 'Find professional associations and industry organizations in your target market and sector.',
            'icon': 'fas fa-certificate',
            'requires': ['industry', 'geographical_area'],
            'form_template': 'service_form_industry_country.html'
        },
        'blacklisted-companies': {
            'title': 'Blacklisted Companies and Vessels',
            'description': 'Search for companies and vessels that have been blacklisted by various countries and organizations.',
            'icon': 'fas fa-ban',
            'requires': ['entity_name'],
            'form_template': 'service_form_blacklisted_companies.html'
        },
        'shipping-documents': {
            'title': 'Shipping Documents',
            'description': 'Find the required documents for importing and exporting goods between countries.',
            'icon': 'fas fa-file-contract',
            'requires': ['import_country', 'export_country', 'manufacture_country', 'transport_mode', 'shipment_date'],
            'form_template': 'service_form_shipping_documents.html'
        }
    }
    
    if service_type not in service_config:
        flash('Service not found.', 'error')
        return redirect(url_for('main.services_page'))
    
    config = service_config[service_type]
    config_service = current_app.config.get('CONFIG_SERVICE')
    
    # Only load sectors for services that need them
    template_vars = {
        'service': config,
        'service_type': service_type
    }
    
    # Add sectors only for services that require them
    if 'industry' in config.get('requires', []):
        sectors = config_service.get_sectors()
        template_vars['sectors'] = sectors
    
    return render_template(config['form_template'], **template_vars)

@main_bp.route('/start_individual_service', methods=['POST'])
def start_individual_service():
    """Initialize individual service generation and return loading page."""
    try:
        service_type = request.form.get('service_type')
        
        # Check if service requires authentication (all except general-presentation)
        if service_type != 'general-presentation' and not current_user.is_authenticated:
            return jsonify({
                'status': 'error',
                'message': 'Please login to access this service.'
            }), 401
        
        # Build form_data based on service requirements
        form_data = {
            'service_type': service_type
        }
        
        # Add required fields based on service type
        if 'origin_country' in request.form:
            form_data['origin_country_code'] = request.form.get('origin_country')
        
        if 'destination_country' in request.form:
            form_data['destination_country_code'] = request.form.get('destination_country')
        
        if 'hs6_product_code' in request.form:
            form_data['hs6_product_code'] = request.form.get('hs6_product_code')
        
        if 'sector' in request.form:
            form_data['sector'] = request.form.get('sector')
        
        # Get config service for optimized lookups
        config_service = current_app.config.get('CONFIG_SERVICE')
        
        # Handle business directories and online marketplaces specific fields
        if 'industry' in request.form:
            form_data['industry_code'] = request.form.get('industry')
            # Get industry name from code for online marketplaces
            industry_code = request.form.get('industry')
            sector = config_service.find_sector_by_code(industry_code)
            form_data['industry_name'] = sector.get('name') if sector else industry_code
        
        if 'geographical_area' in request.form:
            form_data['geographical_area_code'] = request.form.get('geographical_area')
            # For business directories and online marketplaces, the geographical_area is actually a country
            # Add it as destination_country_code for consistency with other services
            form_data['destination_country_code'] = request.form.get('geographical_area')
        
        if 'entity_name' in request.form:
            form_data['entity_name'] = request.form.get('entity_name')
        
        # Handle shipping documents specific fields
        if 'import_country' in request.form:
            form_data['import_country'] = request.form.get('import_country')
        
        if 'export_country' in request.form:
            form_data['export_country'] = request.form.get('export_country')
        
        if 'manufacture_country' in request.form:
            form_data['manufacture_country'] = request.form.get('manufacture_country')
        
        if 'transport_mode' in request.form:
            form_data['transport_mode'] = request.form.get('transport_mode')
        
        if 'shipment_date' in request.form:
            form_data['shipment_date'] = request.form.get('shipment_date')
        
        # Document type - always default to country_specific
        form_data['document_type'] = request.form.get('document_type', 'country_specific')
        
        # Enrich form_data with names using optimized lookups
        if 'origin_country_code' in form_data:
            country = config_service.find_country_by_code(form_data['origin_country_code'])
            form_data['origin_country_name'] = country.get('name') if country else None
        
        if 'destination_country_code' in form_data:
            country = config_service.find_country_by_code(form_data['destination_country_code'])
            form_data['destination_country_name'] = country.get('name') if country else None
        
        if 'hs6_product_code' in form_data:
            product = config_service.find_product_by_hs6(form_data['hs6_product_code'])
            form_data['product_name'] = product.get('description') if product else form_data['hs6_product_code'] or ''
        
        if 'sector' in form_data:
            sector = config_service.find_sector_by_name(form_data.get('sector'))
            form_data['sector_code'] = sector.get('code') if sector else ''
        
        # Add additional country data if needed
        if 'destination_country_code' in form_data:
            country = config_service.find_country_by_code(form_data['destination_country_code'])
            if country:
                form_data['destination_country_iso3n'] = country.get('iso_numeric', '')
                form_data['destination_country_iso2'] = country.get('ISO2', '')
        
        # Set per-report status in reports_cache
        report_id = str(uuid.uuid4())
        session['report_id'] = report_id
        session['report_form_data'] = form_data
        session.modified = True
        
        global reports_cache
        reports_cache[report_id] = {
            'status': 'processing',
            'error_message': None,
            'service_type': service_type
        }
        
        # Create a copy of the application context for the background thread
        @copy_current_request_context
        def generate_individual_service_with_context():
            import time as _time
            t0 = _time.time()
            try:
                report_service = None
                print(f'[TIMING] Start individual service generation ({service_type}): {round(_time.time() - t0, 2)}s')
                
                report_service = ReportGenerationService()
                if not report_service.driver:
                    reports_cache[report_id]['status'] = 'error'
                    reports_cache[report_id]['error_message'] = 'Failed to initialize Selenium WebDriver.'
                    return
                
                # Generate specific service data
                service_data = {}
                
                # Add default sector for services that don't require it but OpenAI might need it
                if 'sector' not in form_data:
                    form_data['sector'] = 'General Business'
                
                if service_type == 'general-presentation':
                    raw_data = report_service.generate_santander_report_data(form_data['destination_country_code'], None)
                    from ..services.data_processor import MarketDataProcessor
                    data_processor = MarketDataProcessor()
                    service_data = {
                        'market_data': data_processor.parse_raw_data(raw_data),
                        'openai_intro': report_service.generate_openai_intro(raw_data, form_data),
                        'openai_conclusion': report_service.generate_openai_conclusion(raw_data, form_data)
                    }
                elif service_type == 'economic-political':
                    service_data['eco_political_data'] = report_service.generate_santander_economic_political_outline(form_data['destination_country_code'], None, login_required=True)
                    service_data['eco_political_intro'] = report_service.generate_openai_eco_political_intro(service_data['eco_political_data'], form_data)
                    service_data['eco_political_insights'] = report_service.generate_openai_eco_political_insights(service_data['eco_political_data'], form_data)
                elif service_type == 'operating-business':
                    service_data['operating_a_business_data'] = report_service.generate_santander_operating_a_business(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'tax-system':
                    service_data['tax_system_data'] = report_service.generate_santander_tax_system(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'legal-environment':
                    service_data['legal_environment_data'] = report_service.generate_santander_legal_environment(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'foreign-investment':
                    service_data['foreign_investment_data'] = report_service.generate_santander_foreign_investment(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'business-practices':
                    service_data['business_practices_data'] = report_service.generate_santander_business_practices(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'entry-requirements':
                    service_data['entry_requirements_data'] = report_service.generate_santander_entry_requirements(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'practical-information':
                    service_data['practical_information_data'] = report_service.generate_santander_practical_information(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'living-in-country':
                    service_data['living_in_country_data'] = report_service.generate_santander_living_in_country(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'foreign-trade':
                    service_data['trade_data'] = report_service.generate_santander_foreign_trade_in_figures(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'reaching-consumers':
                    service_data['consumer_data'] = report_service.generate_santander_reaching_consumers(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'distributing-product':
                    service_data['distribution_data'] = report_service.generate_santander_distributing_product(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'identify-suppliers':
                    service_data['supplier_data'] = report_service.generate_santander_identify_suppliers(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'trade-compliance':
                    service_data['trade_compliance_data'] = report_service.generate_santander_trade_compliance(form_data['destination_country_code'], None, login_required=True)
                elif service_type == 'business-directories':
                    # For business directories, we need to pass the industry name and country name
                    industry_name = form_data.get('industry_name')  # This contains the industry name
                    country_name = form_data.get('destination_country_name')
                    
                    service_data['business_directories_data'] = report_service.generate_santander_business_directories(
                        industry_name, 
                        country_name, 
                        login_required=True
                    )
                elif service_type == 'import-export-flows':
                    service_data['flows_data'] = report_service.generate_santander_import_export_flows(
                        form_data['hs6_product_code'],
                        form_data['origin_country_code'],
                        form_data['destination_country_code'],
                        login_required=True
                    )
                    service_data['flows_intro'] = report_service.generate_openai_flows_intro(service_data['flows_data'], form_data)
                    service_data['flows_insights'] = report_service.generate_openai_flows_insights(service_data['flows_data'], form_data)
                elif service_type == 'trade-shows':
                    service_data['trade_shows_data'] = report_service.generate_santander_trade_shows(
                        form_data['sector_code'],
                        form_data['destination_country_iso2'],
                        login_required=True
                    )
                elif service_type == 'market-access':
                    reporter_iso3n = get_country_iso_numeric_from_code(form_data['destination_country_code'])
                    partner_iso3n = get_country_iso_numeric_from_code(form_data['origin_country_code'])
                    service_data['macmap_data'] = report_service.generate_macmap_market_access_conditions(
                        reporter_iso3n,
                        partner_iso3n,
                        form_data['hs6_product_code']
                    )
                    service_data['macmap_intro'] = report_service.generate_openai_macmap_intro(service_data['macmap_data'], form_data)
                    service_data['macmap_insights'] = report_service.generate_openai_macmap_insights(service_data['macmap_data'], form_data)
                elif service_type == 'online-marketplaces':
                    # For online marketplaces, we need to pass the industry name and country name
                    industry_name = form_data.get('industry_name')  # This contains the industry name
                    country_name = form_data.get('destination_country_name')
                    
                    service_data['online_marketplaces_data'] = report_service.generate_santander_online_marketplaces(
                        industry_name, 
                        country_name, 
                        login_required=True
                    )
                elif service_type == 'professional-associations':
                    # For professional associations, we need to pass the industry name and country name
                    industry_name = form_data.get('industry_name')  # This contains the industry name
                    country_name = form_data.get('destination_country_name')
                    
                    service_data['professional_associations_data'] = report_service.generate_santander_professional_associations(
                        industry_name, 
                        country_name, 
                        login_required=True
                    )
                elif service_type == 'blacklisted-companies':
                    # For blacklisted companies, we need the entity name
                    entity_name = form_data.get('entity_name')
                    
                    service_data['blacklisted_companies_data'] = report_service.generate_santander_blacklisted_companies(
                        entity_name, 
                        login_required=True
                    )
                elif service_type == 'shipping-documents':
                    # Debug: Print all form data
                    print(f"Debug: All form_data = {dict(form_data)}")
                    
                    # For shipping documents, we need multiple parameters
                    import_country_code = form_data.get('import_country')
                    export_country_code = form_data.get('export_country')
                    manufacture_country_code = form_data.get('manufacture_country')
                    transport_mode = form_data.get('transport_mode')
                    shipment_date = form_data.get('shipment_date')
                    document_type = form_data.get('document_type')
                    
                    # Get country names from codes
                    config_service = current_app.config.get('CONFIG_SERVICE')
                    
                    # Debug logging
                    print(f"Debug: import_country_code = {import_country_code}")
                    print(f"Debug: export_country_code = {export_country_code}")
                    print(f"Debug: manufacture_country_code = {manufacture_country_code}")
                    
                    import_country = config_service.find_country_by_code(import_country_code) if import_country_code else None
                    export_country = config_service.find_country_by_code(export_country_code) if export_country_code else None
                    manufacture_country = config_service.find_country_by_code(manufacture_country_code) if manufacture_country_code else None
                    
                    import_country_name = import_country.get('name') if import_country else None
                    export_country_name = export_country.get('name') if export_country else None
                    manufacture_country_name = manufacture_country.get('name') if manufacture_country else None
                    
                    print(f"Debug: import_country_name = {import_country_name}")
                    print(f"Debug: export_country_name = {export_country_name}")
                    print(f"Debug: manufacture_country_name = {manufacture_country_name}")
                    
                    service_data['shipping_documents_data'] = report_service.generate_santander_shipping_documents(
                        import_country_name,
                        export_country_name,
                        manufacture_country_name,
                        transport_mode,
                        shipment_date,
                        document_type,
                        login_required=True
                    )
                
                # Update the report with service data
                reports_cache[report_id].update({
                    'form_data': form_data,
                    'status': 'complete',
                    'error_message': None,
                    **service_data
                })
                
                print(f'[TIMING] Individual service generation completed: {round(_time.time() - t0, 2)}s')
                current_app.logger.info(f"Individual service generation completed for {service_type}")
                current_app.logger.info(f"Report {report_id} marked as complete in cache")
                
            except Exception as e:
                current_app.logger.error(f"Individual service generation failed: {e}", exc_info=True)
                reports_cache[report_id]['status'] = 'error'
                reports_cache[report_id]['error_message'] = str(e)
            finally:
                if report_service:
                    report_service.close_driver()
        
        # Start background task
        thread = threading.Thread(target=generate_individual_service_with_context)
        thread.daemon = True
        thread.start()
        
        # Handle regular form submission vs AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request - return JSON for JavaScript to handle redirect
            return jsonify({
                'status': 'success',
                'redirect_url': url_for('main.loading_page')
            })
        else:
            # Regular form submission - redirect directly (homepage)
            return redirect(url_for('main.loading_page'))
        
    except Exception as e:
        current_app.logger.error(f"Failed to start individual service generation: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to start service generation'
        })

@main_bp.route('/start_report', methods=['POST'])
@login_required
def start_report():
    """Initialize report generation and return loading page."""
    try:
        form_data = {
            'origin_country_code': request.form.get('origin_country'),
            'destination_country_code': request.form.get('destination_country'),
            'hs6_product_code': request.form.get('hs6_product_code'),
            'sector': request.form.get('sector')
        }
        
        config_service = current_app.config.get('CONFIG_SERVICE')
        # Use optimized lookups
        origin_country = config_service.find_country_by_code(form_data['origin_country_code'])
        form_data['origin_country_name'] = origin_country.get('name') if origin_country else None
        
        destination_country = config_service.find_country_by_code(form_data['destination_country_code'])
        form_data['destination_country_name'] = destination_country.get('name') if destination_country else None
        
        # Map hs6_product_code to product_name (description)
        product = config_service.find_product_by_hs6(form_data.get('hs6_product_code'))
        form_data['product_name'] = product.get('description') if product else form_data.get('hs6_product_code', '')
        
        # Add sector_code (from sector name)
        sector = config_service.find_sector_by_name(form_data.get('sector'))
        form_data['sector_code'] = sector.get('code') if sector else ''
        
        # Add destination_country_iso3n and iso2
        form_data['destination_country_iso3n'] = destination_country.get('iso_numeric') if destination_country else ''
        form_data['destination_country_iso2'] = destination_country.get('ISO2') if destination_country else ''
        
        # Set per-report status in reports_cache
        report_id = str(uuid.uuid4())
        session['report_id'] = report_id
        session['report_form_data'] = form_data
        session.modified = True
        global reports_cache
        reports_cache[report_id] = {
            'status': 'processing',
            'error_message': None
        }
        
        # Create a copy of the application context for the background thread
        @copy_current_request_context
        def generate_report_with_context():
            import time as _time
            t0 = _time.time()
            try:
                report_service = None
                print(f'[TIMING] Start report generation: {round(_time.time() - t0, 2)}s')
                report_service = ReportGenerationService()
                if not report_service.driver:
                    reports_cache[report_id]['status'] = 'error'
                    reports_cache[report_id]['error_message'] = 'Failed to initialize Selenium WebDriver.'
                    return
                
                # Get countries config from service
                config_service = current_app.config.get('CONFIG_SERVICE')
                countries_config = config_service.get_countries()
                # Scrape Santander General Presentation
                try:
                    raw_santander_data = report_service.generate_santander_report_data(
                        form_data['destination_country_code'], 
                        countries_config
                    )
                    print(f'[TIMING] After scraping santander country data: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Santander General Presentation: {e}")
                    raw_santander_data = {}
                # Scrape Economic and Political Outline
                try:
                    eco_political_data = report_service.generate_santander_economic_political_outline(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping economic/political outline: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Economic/Political Outline: {e}")
                    eco_political_data = {}
                # Scrape Foreign Trade in Figures
                try:
                    trade_data = report_service.generate_santander_foreign_trade_in_figures(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping foreign trade in figures: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Foreign Trade in Figures: {e}")
                    trade_data = {}
                # Scrape Operating a Business (NEW)
                try:
                    operating_a_business_data = report_service.generate_santander_operating_a_business(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping operating a business: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Operating a Business: {e}")
                    operating_a_business_data = {}
                # Scrape Tax System (NEW)
                try:
                    tax_system_data = report_service.generate_santander_tax_system(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping tax system: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Tax System: {e}")
                    tax_system_data = {}
                # Scrape Legal Environment (NEW)
                try:
                    legal_environment_data = report_service.generate_santander_legal_environment(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping legal environment: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Legal Environment: {e}")
                    legal_environment_data = {}
                # Scrape Foreign Investment (NEW)
                try:
                    foreign_investment_data = report_service.generate_santander_foreign_investment(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping foreign investment: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Foreign Investment: {e}")
                    foreign_investment_data = {}
                # Scrape Business Practices (NEW)
                try:
                    business_practices_data = report_service.generate_santander_business_practices(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping business practices: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Business Practices: {e}")
                    business_practices_data = {}
                # Scrape Entry Requirements (NEW)
                try:
                    entry_requirements_data = report_service.generate_santander_entry_requirements(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping entry requirements: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Entry Requirements: {e}")
                    entry_requirements_data = {}
                # Scrape Practical Information (NEW)
                try:
                    practical_information_data = report_service.generate_santander_practical_information(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping practical information: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Practical Information: {e}")
                    practical_information_data = {}
                # Scrape Living in the Country (NEW)
                try:
                    living_in_country_data = report_service.generate_santander_living_in_country(
                        form_data['destination_country_code'],
                        countries_config,
                        login_required=False
                    )
                    print(f'[TIMING] After scraping living in the country: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Living in the Country: {e}")
                    living_in_country_data = {}
                # Scrape MacMap Market Access Conditions
                try:
                    reporter_iso3n = get_country_iso_numeric_from_code(form_data['destination_country_code'])
                    partner_iso3n = get_country_iso_numeric_from_code(form_data['origin_country_code'])
                    macmap_data = report_service.generate_macmap_market_access_conditions(
                        reporter_iso3n,
                        partner_iso3n,
                        form_data['hs6_product_code']
                    )
                    print(f'[TIMING] After scraping MacMap: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping MacMap: {e}")
                    macmap_data = {}
                # Scrape Import/Export Flows
                try:
                    flows_data = report_service.generate_santander_import_export_flows(
                        form_data['hs6_product_code'],
                        form_data['origin_country_code'],
                        form_data['destination_country_code'],
                        login_required=False
                    )
                    print(f'[TIMING] After scraping import/export flows: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Import/Export Flows: {e}")
                    flows_data = {}
                # Scrape Trade Shows
                try:
                    trade_shows_data = report_service.generate_santander_trade_shows(
                        form_data['sector_code'],
                        form_data['destination_country_iso2'],
                        login_required=False
                    )
                    print(f'[TIMING] After scraping trade shows: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Trade Shows: {e}")
                    trade_shows_data = []
                # Data processing and OpenAI calls (optional, wrap in try/except for each)
                try:
                    data_processor = MarketDataProcessor()
                    market_data = data_processor.parse_raw_data(raw_santander_data)
                    print(f'[TIMING] After parsing market data: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error processing market data: {e}")
                    market_data = {}
                def safe_openai_call(fn, *args, **kwargs):
                    try:
                        return fn(*args, **kwargs)
                    except Exception as e:
                        current_app.logger.error(f"OpenAI error: {e}")
                        return ''
                openai_intro = safe_openai_call(report_service.generate_openai_intro, raw_santander_data, form_data)
                print(f'[TIMING] After OpenAI intro: {round(_time.time() - t0, 2)}s')
                openai_conclusion = safe_openai_call(report_service.generate_openai_conclusion, raw_santander_data, form_data)
                print(f'[TIMING] After OpenAI conclusion: {round(_time.time() - t0, 2)}s')
                eco_political_intro = safe_openai_call(report_service.generate_openai_eco_political_intro, eco_political_data, form_data)
                print(f'[TIMING] After OpenAI eco_political_intro: {round(_time.time() - t0, 2)}s')
                eco_political_insights = safe_openai_call(report_service.generate_openai_eco_political_insights, eco_political_data, form_data)
                print(f'[TIMING] After OpenAI eco_political_insights: {round(_time.time() - t0, 2)}s')
                macmap_intro = safe_openai_call(report_service.generate_openai_macmap_intro, macmap_data, form_data)
                print(f'[TIMING] After OpenAI macmap_intro: {round(_time.time() - t0, 2)}s')
                macmap_insights = safe_openai_call(report_service.generate_openai_macmap_insights, macmap_data, form_data)
                print(f'[TIMING] After OpenAI macmap_insights: {round(_time.time() - t0, 2)}s')
                flows_intro = safe_openai_call(report_service.generate_openai_flows_intro, flows_data, form_data)
                print(f'[TIMING] After OpenAI flows_intro: {round(_time.time() - t0, 2)}s')
                flows_insights = safe_openai_call(report_service.generate_openai_flows_insights, flows_data, form_data)
                print(f'[TIMING] After OpenAI flows_insights: {round(_time.time() - t0, 2)}s')
                # Always update the report as complete, even if some sections are missing
                reports_cache[report_id].update({
                    'form_data': form_data,
                    'market_data': market_data,
                    'openai_intro': openai_intro,
                    'openai_conclusion': openai_conclusion,
                    'eco_political_data': eco_political_data,
                    'eco_political_intro': eco_political_intro,
                    'eco_political_insights': eco_political_insights,
                    'trade_data': trade_data,
                    'operating_a_business_data': operating_a_business_data,
                    'tax_system_data': tax_system_data,
                    'legal_environment_data': legal_environment_data,
                    'foreign_investment_data': foreign_investment_data,
                    'business_practices_data': business_practices_data,
                    'entry_requirements_data': entry_requirements_data,
                    'practical_information_data': practical_information_data,
                    'living_in_country_data': living_in_country_data,
                    'flows_data': flows_data,
                    'flows_intro': flows_intro,
                    'flows_insights': flows_insights,
                    'trade_shows_data': trade_shows_data,
                    'macmap_data': macmap_data,
                    'macmap_intro': macmap_intro,
                    'macmap_insights': macmap_insights,
                    'datetime': datetime,
                    'status': 'complete',
                    'error_message': None
                })
                current_app.logger.info("Report generation completed (with possible missing sections)")
            except Exception as e:
                current_app.logger.error(f"Report generation failed: {e}", exc_info=True)
                reports_cache[report_id]['status'] = 'error'
                reports_cache[report_id]['error_message'] = str(e)
            finally:
                if report_service:
                    report_service.close_driver()
        
        # Start background task
        thread = threading.Thread(target=generate_report_with_context)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'redirect_url': url_for('main.loading_page')
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to start report generation: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to start report generation'
        })

@main_bp.route('/loading')
def loading_page():
    """Show loading page while report is being generated."""
    if 'report_id' not in session:
        # For non-authenticated users, redirect to home instead of form page
        if not current_user.is_authenticated:
            return redirect(url_for('main.home'))
        return redirect(url_for('main.form_page'))
    return render_template('loading.html')

@main_bp.route('/check_status')
def check_status():
    """Check the status of report generation for the current user's report_id."""
    from flask import make_response
    report_id = session.get('report_id')
    current_app.logger.info(f"Check status called. Session report_id: {report_id}")
    current_app.logger.info(f"Available reports in cache: {list(reports_cache.keys())}")
    
    if not report_id:
        current_app.logger.warning("No report_id in session")
        resp = make_response(jsonify({'status': 'error', 'message': 'No report ID in session.'}))
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp
        
    if report_id not in reports_cache:
        current_app.logger.warning(f"Report ID {report_id} not found in cache")
        resp = make_response(jsonify({'status': 'error', 'message': 'Report not found in cache.'}))
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp
    status = reports_cache[report_id].get('status', 'processing')
    current_app.logger.info(f"Checking status for report_id {report_id}. Current status: {status}")
    if status == 'complete':
        session.modified = True
        current_app.logger.info("Status check: Report is complete")
        resp = make_response(jsonify({
            'status': 'complete',
            'redirect_url': url_for('main.show_report')
        }))
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp
    elif status == 'error':
        current_app.logger.info(f"Status check: Error - {reports_cache[report_id].get('error_message')}")
        resp = make_response(jsonify({
            'status': 'error',
            'message': reports_cache[report_id].get('error_message', 'Unknown error')
        }))
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp
    current_app.logger.info("Status check: Still processing")
    resp = make_response(jsonify({'status': 'processing'}))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

@main_bp.route('/report')
def show_report():
    """Display the generated report."""
    if 'report_id' not in session:
        flash('No report data available. Please generate a report first.', 'warning')
        # For non-authenticated users, redirect to home instead of services page
        if not current_user.is_authenticated:
            return redirect(url_for('main.home'))
        return redirect(url_for('main.services_page'))
    report_id = session.get('report_id')
    report = reports_cache.get(report_id)
    if not report:
        flash('No report data available. Please generate a report first.', 'warning')
        return redirect(url_for('main.services_page'))
    
    # Check if this is a country information context (general presentation from country selection)
    if session.get('country_context') and report.get('service_type') == 'general-presentation':
        # Render country information results template with sidebar navigation
        template_data = dict(report)
        template_data['datetime'] = datetime
        return render_template('country_information_results.html', **template_data)
    
    # Check if this is an individual service report
    service_type = report.get('service_type')
    if service_type:
        # Check if this came from country service navigation
        if session.get('country_context'):
            # Create a country-specific template that extends the country base template
            template_data = dict(report)
            template_data['datetime'] = datetime
            template_data['country_context'] = True
            
            # Get the service title and icon for the template
            service_config = {
                'operating-business': {'title': 'Operating a Business', 'icon': 'fas fa-briefcase'},
                'tax-system': {'title': 'Tax System', 'icon': 'fas fa-file-invoice-dollar'},
                'legal-environment': {'title': 'Legal Environment', 'icon': 'fas fa-gavel'},
                'foreign-investment': {'title': 'Foreign Investment', 'icon': 'fas fa-globe-americas'},
                'business-practices': {'title': 'Business Practices', 'icon': 'fas fa-handshake'},
                'entry-requirements': {'title': 'Entry Requirements', 'icon': 'fas fa-id-card'},
                'practical-information': {'title': 'Practical Information', 'icon': 'fas fa-info'},
                'living-in-country': {'title': 'Living in the Country', 'icon': 'fas fa-home'},
                'general-presentation': {'title': 'General Information', 'icon': 'fas fa-info-circle'},
                'foreign-trade': {'title': 'Foreign Trade in Figures', 'icon': 'fas fa-exchange-alt'},
                'reaching-consumers': {'title': 'Reaching the Consumer', 'icon': 'fas fa-users'},
                'distributing-product': {'title': 'Distributing a Product', 'icon': 'fas fa-truck'}
            }
            
            config = service_config.get(service_type, {'title': service_type.replace('-', ' ').title(), 'icon': 'fas fa-file'})
            template_data['service_title'] = config['title']
            template_data['service_icon'] = config['icon']
            
            # Check if this is a locked service
            if report.get('is_locked'):
                template_data['is_locked'] = True
                template_name = 'individual_reports/locked_service_country.html'
                return render_template(template_name, **template_data)
            
            # Render the specific service template but it will extend the country base template
            template_name = f'individual_reports/{service_type.replace("-", "_")}_country.html'
            
            # Check if country-specific template exists, if not use the regular template
            try:
                return render_template(template_name, **template_data)
            except:
                # Fall back to regular template with country context flag
                template_name = f'individual_reports/{service_type.replace("-", "_")}.html'
                return render_template(template_name, **template_data)
        else:
            # Regular individual service template
            template_name = f'individual_reports/{service_type.replace("-", "_")}.html'
            template_data = dict(report)
            template_data['datetime'] = datetime
            return render_template(template_name, **template_data)
    
    # Render full report template
    eco_political_data = report.get('eco_political_data') or {}
    trade_data = report.get('trade_data') or {}
    macmap_data = report.get('macmap_data') or {}
    flows_data = report.get('flows_data') or {}
    flows_intro = report.get('flows_intro')
    flows_insights = report.get('flows_insights')
    trade_shows_data = report.get('trade_shows_data') or []
    operating_a_business_data = report.get('operating_a_business_data') or {}
    tax_system_data = report.get('tax_system_data') or {}
    legal_environment_data = report.get('legal_environment_data') or {}
    foreign_investment_data = report.get('foreign_investment_data') or {}
    business_practices_data = report.get('business_practices_data') or {}
    entry_requirements_data = report.get('entry_requirements_data') or {}
    practical_information_data = report.get('practical_information_data') or {}
    living_in_country_data = report.get('living_in_country_data') or {}
    return render_template('report.html',
                         form_data=report.get('form_data'),
                         market_data=report.get('market_data'),
                         openai_intro=report.get('openai_intro'),
                         openai_conclusion=report.get('openai_conclusion'),
                         eco_political_intro=report.get('eco_political_intro'),
                         eco_political_insights=report.get('eco_political_insights'),
                         macmap_intro=report.get('macmap_intro'),
                         macmap_insights=report.get('macmap_insights'),
                         datetime=datetime,
                         flows_data=flows_data,
                         flows_intro=flows_intro,
                         flows_insights=flows_insights,
                         trade_shows_data=trade_shows_data,
                         operating_a_business_data=operating_a_business_data,
                         tax_system_data=tax_system_data,
                         legal_environment_data=legal_environment_data,
                         foreign_investment_data=foreign_investment_data,
                         business_practices_data=business_practices_data,
                         entry_requirements_data=entry_requirements_data,
                         practical_information_data=practical_information_data,
                         living_in_country_data=living_in_country_data,
                         **eco_political_data,
                         **trade_data,
                         macmap_data=macmap_data
                         )

def get_country_iso_numeric_from_code(country_code, countries_config=None):
    """Retrieves the iso_numeric code from its alpha-2 code using the loaded config."""
    # For backward compatibility, still accept countries_config parameter
    # But prefer using the config service for better performance
    if countries_config:
        for country in countries_config:
            if country.get("code") == country_code:
                return country.get("iso_numeric")
        return None
    
    # Use config service if available
    from flask import current_app
    config_service = current_app.config.get('CONFIG_SERVICE')
    if config_service:
        country = config_service.find_country_by_code(country_code)
        return country.get("iso_numeric") if country else None
    return None

@main_bp.route('/api/countries')
def api_countries():
    search = request.args.get('search', '').lower()
    config_service = current_app.config.get('CONFIG_SERVICE')
    
    if search:
        filtered = config_service.search_countries(search, 30)
    else:
        filtered = config_service.get_countries(30)
    
    results = [{
        'id': c['code'],
        'text': f"{c['name']} ({c['code']})"
    } for c in filtered]  # Already limited by config service
    return jsonify(items=results)

@main_bp.route('/api/products')
@login_required
def api_products():
    search = request.args.get('search', '').lower()
    config_service = current_app.config.get('CONFIG_SERVICE')
    
    if search:
        filtered = config_service.search_products(search, 30)
    else:
        filtered = config_service.get_products(30)
    
    results = [{
        'id': p['hs6'],
        'text': f"{p['hs6']} - {p['description']}"
    } for p in filtered]  # Already limited by config service
    return jsonify(items=results)

# API endpoints for configuration data searching (for AJAX dropdowns)
@main_bp.route('/api/search/countries', methods=['GET'])
def search_countries_api():
    """Search countries for AJAX dropdown."""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    
    config_service = current_app.config.get('CONFIG_SERVICE')
    if query:
        results = config_service.search_countries(query, limit)
    else:
        results = config_service.get_countries(limit)
    
    # Format for Select2 or similar dropdown libraries
    formatted_results = [
        {
            'id': country.get('code'),
            'text': f"{country.get('name')} ({country.get('code')})",
            'name': country.get('name'),
            'code': country.get('code'),
            'iso2': country.get('ISO2'),
            'iso_numeric': country.get('iso_numeric')
        }
        for country in results
    ]
    
    return jsonify({'results': formatted_results})

@main_bp.route('/api/search/products', methods=['GET'])
@login_required
def search_products_api():
    """Search products for AJAX dropdown."""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    
    config_service = current_app.config.get('CONFIG_SERVICE')
    if query:
        results = config_service.search_products(query, limit)
    else:
        results = config_service.get_products(limit)
    
    # Format for Select2 or similar dropdown libraries
    formatted_results = [
        {
            'id': product.get('hs6'),
            'text': f"{product.get('hs6')} - {product.get('description', '')[:100]}{'...' if len(product.get('description', '')) > 100 else ''}",
            'hs6': product.get('hs6'),
            'description': product.get('description')
        }
        for product in results
    ]
    
    return jsonify({'results': formatted_results})

@main_bp.route('/api/search/sectors', methods=['GET'])
@login_required
def search_sectors_api():
    """Get all sectors (usually small dataset)."""
    config_service = current_app.config.get('CONFIG_SERVICE')
    results = config_service.get_sectors()
    
    # Format for Select2 or similar dropdown libraries
    formatted_results = [
        {
            'id': sector.get('name'),
            'text': sector.get('name'),
            'name': sector.get('name'),
            'code': sector.get('code')
        }
        for sector in results
    ]
    
    return jsonify({'results': formatted_results}) 