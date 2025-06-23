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
        sectors_config = current_app.config.get('SECTORS', [])
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
        # Add sector_code (from sector name)
        selected_sector_name = form_data.get('sector')
        sector_code = None
        for sector in sectors_config:
            if sector.get('name') == selected_sector_name:
                sector_code = sector.get('code')
                break
        form_data['sector_code'] = sector_code or ''
        # Add destination_country_iso3n
        destination_country_iso3n = None
        for country in countries_config:
            if country.get('code') == form_data['destination_country_code']:
                destination_country_iso3n = country.get('iso_numeric')
                break
        form_data['destination_country_iso3n'] = destination_country_iso3n or ''
        # Add destination_country_iso2 (for Trade Shows)
        destination_country_iso2 = None
        for country in countries_config:
            if country.get('code') == form_data['destination_country_code']:
                destination_country_iso2 = country.get('ISO2')
                break
        form_data['destination_country_iso2'] = destination_country_iso2 or ''
        
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
                countries_config = current_app.config.get('COUNTRIES', [])
                print(f'[TIMING] Start report generation: {round(_time.time() - t0, 2)}s')
                report_service = ReportGenerationService()
                if not report_service.driver:
                    reports_cache[report_id]['status'] = 'error'
                    reports_cache[report_id]['error_message'] = 'Failed to initialize Selenium WebDriver.'
                    return
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
                        countries_config
                    )
                    print(f'[TIMING] After scraping economic/political outline: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Economic/Political Outline: {e}")
                    eco_political_data = {}
                # Scrape Foreign Trade in Figures
                try:
                    trade_data = report_service.generate_santander_foreign_trade_in_figures(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping foreign trade in figures: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Foreign Trade in Figures: {e}")
                    trade_data = {}
                # Scrape Operating a Business (NEW)
                try:
                    operating_a_business_data = report_service.generate_santander_operating_a_business(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping operating a business: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Operating a Business: {e}")
                    operating_a_business_data = {}
                # Scrape Tax System (NEW)
                try:
                    tax_system_data = report_service.generate_santander_tax_system(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping tax system: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Tax System: {e}")
                    tax_system_data = {}
                # Scrape Legal Environment (NEW)
                try:
                    legal_environment_data = report_service.generate_santander_legal_environment(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping legal environment: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Legal Environment: {e}")
                    legal_environment_data = {}
                # Scrape Foreign Investment (NEW)
                try:
                    foreign_investment_data = report_service.generate_santander_foreign_investment(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping foreign investment: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Foreign Investment: {e}")
                    foreign_investment_data = {}
                # Scrape Business Practices (NEW)
                try:
                    business_practices_data = report_service.generate_santander_business_practices(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping business practices: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Business Practices: {e}")
                    business_practices_data = {}
                # Scrape Entry Requirements (NEW)
                try:
                    entry_requirements_data = report_service.generate_santander_entry_requirements(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping entry requirements: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Entry Requirements: {e}")
                    entry_requirements_data = {}
                # Scrape Practical Information (NEW)
                try:
                    practical_information_data = report_service.generate_santander_practical_information(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping practical information: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Practical Information: {e}")
                    practical_information_data = {}
                # Scrape Living in the Country (NEW)
                try:
                    living_in_country_data = report_service.generate_santander_living_in_country(
                        form_data['destination_country_code'],
                        countries_config
                    )
                    print(f'[TIMING] After scraping living in the country: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Living in the Country: {e}")
                    living_in_country_data = {}
                # Scrape MacMap Market Access Conditions
                try:
                    reporter_iso3n = get_country_iso_numeric_from_code(form_data['destination_country_code'], countries_config)
                    partner_iso3n = get_country_iso_numeric_from_code(form_data['origin_country_code'], countries_config)
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
                        form_data['destination_country_code']
                    )
                    print(f'[TIMING] After scraping import/export flows: {round(_time.time() - t0, 2)}s')
                except Exception as e:
                    current_app.logger.error(f"Error scraping Import/Export Flows: {e}")
                    flows_data = {}
                # Scrape Trade Shows
                try:
                    trade_shows_data = report_service.generate_santander_trade_shows(
                        form_data['sector_code'],
                        form_data['destination_country_iso2']
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
@login_required
def loading_page():
    """Show loading page while report is being generated."""
    if 'report_id' not in session:
        return redirect(url_for('main.form_page'))
    return render_template('loading.html')

@main_bp.route('/check_status')
@login_required
def check_status():
    """Check the status of report generation for the current user's report_id."""
    from flask import make_response
    report_id = session.get('report_id')
    if not report_id or report_id not in reports_cache:
        resp = make_response(jsonify({'status': 'error', 'message': 'No report in progress.'}))
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