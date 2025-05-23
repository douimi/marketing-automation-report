from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash, session, jsonify, copy_current_request_context, send_from_directory
from flask_login import login_required
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

# Global variable to store report status
report_status = {
    'status': 'processing',
    'market_data': None,
    'openai_intro': None,
    'openai_conclusion': None,
    'eco_political_data': None,
    'eco_political_intro': None,
    'eco_political_insights': None,
    'error_message': None
}

# Global in-memory cache for reports (keyed by report_id)
reports_cache = {}

@main_bp.route('/')
@login_required
def home():
    return redirect(url_for('main.form_page'))

@main_bp.route('/form', methods=['GET'])
@login_required
def form_page():
    countries = current_app.config.get('COUNTRIES', [])
    products = current_app.config.get('PRODUCTS', [])
    sectors = current_app.config.get('SECTORS', [])
    return render_template('form.html', countries=countries, products=products, sectors=sectors)

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
        
        countries_config = current_app.config.get('COUNTRIES', [])
        products_config = current_app.config.get('PRODUCTS', [])
        form_data['origin_country_name'] = get_country_name_from_code(form_data['origin_country_code'], countries_config)
        form_data['destination_country_name'] = get_country_name_from_code(form_data['destination_country_code'], countries_config)
        # Map hs6_product_code to product_name (description)
        hs6_code = form_data.get('hs6_product_code')
        product_name = None
        for product in products_config:
            if product.get('hs6') == hs6_code:
                product_name = product.get('description')
                break
        form_data['product_name'] = product_name or hs6_code or ''
        
        # Reset global status
        global report_status
        report_status = {
            'status': 'processing',
            'market_data': None,
            'openai_intro': None,
            'openai_conclusion': None,
            'eco_political_data': None,
            'eco_political_intro': None,
            'eco_political_insights': None,
            'error_message': None
        }
        
        # Generate a unique report_id and store in session
        report_id = str(uuid.uuid4())
        session['report_id'] = report_id
        session['report_form_data'] = form_data
        session.modified = True
        
        # Create a copy of the application context for the background thread
        @copy_current_request_context
        def generate_report_with_context():
            try:
                report_service = None
                countries_config = current_app.config.get('COUNTRIES', [])
                
                report_service = ReportGenerationService()
                raw_santander_data = report_service.generate_santander_report_data(
                    form_data['destination_country_code'], 
                    countries_config
                )
                
                # Updated error check for dict or string
                error_found = False
                error_message = None
                if isinstance(raw_santander_data, dict) and 'error' in raw_santander_data:
                    error_found = True
                    error_message = raw_santander_data['error']
                elif isinstance(raw_santander_data, str) and raw_santander_data.startswith("Error:"):
                    error_found = True
                    error_message = raw_santander_data

                # --- Economic and Political Outline scraping ---
                eco_political_data = None
                eco_political_intro = None
                eco_political_insights = None
                trade_data = None
                trade_intro = None
                trade_insights = None
                if not error_found:
                    eco_political_data = report_service.generate_santander_economic_political_outline(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    if isinstance(eco_political_data, dict) and 'error' in eco_political_data:
                        error_found = True
                        error_message = eco_political_data['error']
                # --- Foreign Trade in Figures scraping ---
                if not error_found:
                    trade_data = report_service.generate_santander_foreign_trade_in_figures(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    if isinstance(trade_data, dict) and 'error' in trade_data:
                        error_found = True
                        error_message = trade_data['error']
                # --- MacMap Market Access Conditions scraping ---
                macmap_data = None
                macmap_intro = None
                macmap_insights = None
                if not error_found:
                    reporter_iso3n = get_country_iso_numeric_from_code(form_data['destination_country_code'], countries_config)
                    partner_iso3n = get_country_iso_numeric_from_code(form_data['origin_country_code'], countries_config)
                    macmap_data = report_service.generate_macmap_market_access_conditions(
                        reporter_iso3n,
                        partner_iso3n,
                        form_data['hs6_product_code']
                    )
                    if isinstance(macmap_data, dict) and 'error' in macmap_data:
                        error_found = True
                        error_message = macmap_data['error']
                if raw_santander_data and not error_found:
                    # Process the raw data into structured format
                    data_processor = MarketDataProcessor()
                    market_data = data_processor.parse_raw_data(raw_santander_data)
                    # Generate OpenAI introduction
                    openai_intro = report_service.generate_openai_intro(raw_santander_data, form_data)
                    # Generate OpenAI conclusion
                    openai_conclusion = report_service.generate_openai_conclusion(raw_santander_data, form_data)
                    # Generate OpenAI intro/insights for eco-political section
                    eco_political_intro = report_service.generate_openai_eco_political_intro(eco_political_data, form_data)
                    eco_political_insights = report_service.generate_openai_eco_political_insights(eco_political_data, form_data)
                    # Generate OpenAI intro/insights for MacMap section
                    macmap_intro = report_service.generate_openai_macmap_intro(macmap_data, form_data)
                    macmap_insights = report_service.generate_openai_macmap_insights(macmap_data, form_data)
                    # Store all report data in the global cache
                    global reports_cache
                    reports_cache[report_id] = {
                        'form_data': form_data,
                        'market_data': market_data,
                        'openai_intro': openai_intro,
                        'openai_conclusion': openai_conclusion,
                        'eco_political_data': eco_political_data,
                        'eco_political_intro': eco_political_intro,
                        'eco_political_insights': eco_political_insights,
                        'trade_data': trade_data,
                        'macmap_data': macmap_data,
                        'macmap_intro': macmap_intro,
                        'macmap_insights': macmap_insights,
                        'datetime': datetime
                    }
                    global report_status
                    report_status['status'] = 'complete'
                    current_app.logger.info("Report generation completed successfully")
                else:
                    report_status['status'] = 'error'
                    report_status['error_message'] = error_message or raw_santander_data
                    current_app.logger.error(f"Error in report generation: {error_message or raw_santander_data}")
                    
            except Exception as e:
                current_app.logger.error(f"Report generation failed: {e}", exc_info=True)
                report_status['status'] = 'error'
                report_status['error_message'] = str(e)
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
@login_required
def loading_page():
    """Show loading page while report is being generated."""
    if 'report_id' not in session:
        return redirect(url_for('main.form_page'))
    return render_template('loading.html')

@main_bp.route('/check_status')
@login_required
def check_status():
    """Check the status of report generation."""
    global report_status
    current_app.logger.info(f"Checking status. Current status: {report_status['status']}")
    
    if report_status['status'] == 'complete':
        # Store only the report_id in session when complete
        session.modified = True
        current_app.logger.info("Status check: Report is complete")
        return jsonify({
            'status': 'complete',
            'redirect_url': url_for('main.show_report')
        })
    elif report_status['status'] == 'error':
        current_app.logger.info(f"Status check: Error - {report_status['error_message']}")
        return jsonify({
            'status': 'error',
            'message': report_status['error_message']
        })
    
    current_app.logger.info("Status check: Still processing")
    return jsonify({'status': 'processing'})

@main_bp.route('/report')
@login_required
def show_report():
    """Display the generated report."""
    if 'report_id' not in session:
        flash('No report data available. Please generate a report first.', 'warning')
        return redirect(url_for('main.form_page'))
    report_id = session.get('report_id')
    report = reports_cache.get(report_id)
    if not report:
        flash('No report data available. Please generate a report first.', 'warning')
        return redirect(url_for('main.form_page'))
    eco_political_data = report.get('eco_political_data') or {}
    trade_data = report.get('trade_data') or {}
    macmap_data = report.get('macmap_data') or {}
    print('DEBUG: macmap_data =', macmap_data)
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
                         **eco_political_data,
                         **trade_data,
                         macmap_data=macmap_data
                         )

def get_country_iso_numeric_from_code(country_code, countries_config):
    """Retrieves the iso_numeric code from its alpha-2 code using the loaded config."""
    for country in countries_config:
        if country.get("code") == country_code:
            return country.get("iso_numeric")
    return None

@main_bp.route('/api/countries')
@login_required
def api_countries():
    search = request.args.get('search', '').lower()
    countries_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/countries.json'))
    with open(countries_path, encoding='utf-8') as f:
        countries = json.load(f)
    filtered = [c for c in countries if search in c['name'].lower() or search in c['code'].lower() or search in c.get('ISO2', '').lower()]
    results = [{
        'id': c['code'],
        'text': f"{c['name']} ({c['code']})"
    } for c in filtered[:30]]  # Limit results for performance
    return jsonify(items=results)

@main_bp.route('/api/products')
@login_required
def api_products():
    search = request.args.get('search', '').lower()
    products_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/products.json'))
    with open(products_path, encoding='utf-8') as f:
        products = json.load(f)
    filtered = [p for p in products if search in p['description'].lower() or search in p['hs6'].lower()]
    results = [{
        'id': p['hs6'],
        'text': f"{p['hs6']} - {p['description']}"
    } for p in filtered[:30]]  # Limit results for performance
    return jsonify(items=results) 