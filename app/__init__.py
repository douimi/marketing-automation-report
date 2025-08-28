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
    """Load users using the robust user service."""
    from .services.user_service import get_user_service
    user_service = get_user_service()
    return user_service.get_all_users()

class User:
    def __init__(self, username, user_data=None):
        self.id = username
        self.username = username
        
        if user_data is None:
            users = load_users()
            user_data = users.get(username, {})
        
        self.email = user_data.get('email', '')
        self.phone = user_data.get('phone', '')
        self.company = user_data.get('company', '')
        self.preferred_target_country = user_data.get('preferred_target_country', '')
        self.full_name = user_data.get('full_name', username.title())
        self.created_at = user_data.get('created_at', '')
        self._is_active = user_data.get('is_active', True)

    @staticmethod
    def get(user_id):
        users = load_users()
        if user_id in users and users[user_id].get('is_active', True):
            return User(user_id, users[user_id])
        return None

    def is_authenticated(self):
        return True

    def is_active(self):
        return self._is_active

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id
    
    def get_display_name(self):
        """Get the user's display name (full name or username)."""
        return self.full_name if self.full_name else self.username.title()
    
    def update_profile(self, **kwargs):
        """Update user profile information."""
        from .services.user_service import get_user_service
        user_service = get_user_service()
        
        success = user_service.update_user(self.username, **kwargs)
        if success:
            # Update the current object with new values
            for key, value in kwargs.items():
                if key in ['email', 'phone', 'company', 'preferred_target_country', 'full_name']:
                    setattr(self, key, value)
        return success

def create_user(username, password, email, phone="", company="", preferred_target_country="", full_name=""):
    """Create a new user account."""
    from .services.user_service import get_user_service
    user_service = get_user_service()
    return user_service.create_user(username, password, email, phone, company, preferred_target_country, full_name)

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