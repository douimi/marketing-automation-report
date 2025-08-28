# This file can be initially empty or used for Flask app initialization 

from flask import Flask
from flask_session import Session
from redis import Redis
from flask_login import LoginManager
import json
import os
import markdown2
from bs4 import BeautifulSoup
import re

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
    # Core security and session config (env-overridable)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me-in-prod')
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True

    # Server-side session using Redis for multi-user, multi-worker deployments
    redis_url = os.getenv('REDIS_URL') or os.getenv('SESSION_REDIS_URL')
    if redis_url:
        app.config['SESSION_TYPE'] = 'redis'
        app.config['SESSION_REDIS'] = Redis.from_url(redis_url)
    else:
        # Fallback to filesystem (local dev)
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_FILE_DIR'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'flask_session'))
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

    Session(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Initialize config service for lazy loading
    from .services.config_service import get_config_service
    app.config['CONFIG_SERVICE'] = get_config_service()

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

    def strip_html_and_markdown(text):
        if not text:
            return ''
        # Remove HTML tags
        text = BeautifulSoup(text, 'html.parser').get_text()
        # Remove Markdown formatting (basic)
        text = re.sub(r'[#*_`>\-\[\]()]', '', text)
        text = re.sub(r'\n{2,}', '\n', text)
        return text.strip()

    @app.template_filter('plain_text')
    def plain_text_filter(text):
        return strip_html_and_markdown(text)

    return app

# Old load_config function removed - now using ConfigService for lazy loading 