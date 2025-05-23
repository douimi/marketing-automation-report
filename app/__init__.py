# This file can be initially empty or used for Flask app initialization 

from flask import Flask
from flask_login import LoginManager
import json
import os
import markdown2

login_manager = LoginManager()

def load_users():
    users_path = os.path.join(os.path.dirname(__file__), 'config', 'users.json')
    if not os.path.exists(users_path):
        # Create a default users.json if it doesn't exist
        default_users = {"admin": "password123"} # Example user
        with open(users_path, 'w') as f:
            json.dump(default_users, f)
        return default_users
    with open(users_path, 'r') as f:
        return json.load(f)

class User:
    def __init__(self, username):
        self.id = username

    @staticmethod
    def get(user_id):
        users = load_users()
        if user_id in users:
            return User(user_id)
        return None

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to a secure secret key

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Load configuration for dropdowns
    app.config['COUNTRIES'] = load_config('countries.json')
    app.config['PRODUCTS'] = load_config('products.json')
    app.config['SECTORS'] = load_config('sectors.json')

    # Register blueprints
    from .auth.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .routes.routes import main_bp
    app.register_blueprint(main_bp)

    # Add custom filters
    @app.template_filter('markdown')
    def markdown_filter(text):
        if text:
            return markdown2.markdown(text, extras=['fenced-code-blocks', 'tables'])
        return ''
    
    @app.template_filter('format_number')
    def format_number_filter(value):
        """Format numbers with commas."""
        if isinstance(value, (int, float)):
            return "{:,}".format(value)
        return value

    return app

def load_config(filename):
    config_path = os.path.join(os.path.dirname(__file__), 'config', filename)
    if not os.path.exists(config_path):
        # Create default empty config if it doesn't exist
        if filename == 'countries.json':
            default_data = [{"name": "United States", "code": "US", "iso_numeric": "840"}]
        elif filename == 'products.json':
            default_data = [{"hs6": "010101", "description": "Live horses"}]
        elif filename == 'sectors.json':
            default_data = [{"name": "Agriculture"}]
        else:
            default_data = []
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data
        
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {config_path}. Returning empty list.")
        # Create default empty config if it's corrupted
        if filename == 'countries.json':
            default_data = [{"name": "United States", "code": "US", "iso_numeric": "840"}]
        elif filename == 'products.json':
            default_data = [{"hs6": "010101", "description": "Live horses"}]
        elif filename == 'sectors.json':
            default_data = [{"name": "Agriculture"}]
        else:
            default_data = []
        
        with open(config_path, 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data 