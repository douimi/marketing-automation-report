"""
User management service with robust error handling and fallback storage.
"""
import json
import os
import datetime
from typing import Dict, Any, Tuple, Optional

class UserService:
    """Service for managing user data with fallback mechanisms."""
    
    def __init__(self):
        self._users_cache = {}
        self._cache_loaded = False
        self.users_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'users.json')
    
    def _ensure_cache_loaded(self):
        """Load users into cache if not already loaded."""
        if not self._cache_loaded:
            self._load_users_to_cache()
            self._cache_loaded = True
    
    def _load_users_to_cache(self):
        """Load users from file into memory cache."""
        # Ensure config directory exists
        config_dir = os.path.dirname(self.users_path)
        os.makedirs(config_dir, exist_ok=True)
        
        if not os.path.exists(self.users_path):
            # Create default admin user
            self._users_cache = {
                "admin": {
                    "password": "securepassword123",
                    "email": "admin@example.com",
                    "phone": "",
                    "company": "Indegate Consulting",
                    "preferred_target_country": "US",
                    "full_name": "Administrator",
                    "created_at": "2024-01-01T00:00:00Z",
                    "is_active": True
                }
            }
            self._save_to_file()
            return
        
        try:
            with open(self.users_path, 'r') as f:
                users_data = json.load(f)
            
            # Handle backward compatibility
            for username, user_info in users_data.items():
                if isinstance(user_info, str):  # Old format: username -> password
                    users_data[username] = {
                        "password": user_info,
                        "email": f"{username}@example.com",
                        "phone": "",
                        "company": "",
                        "preferred_target_country": "",
                        "full_name": username.title(),
                        "created_at": "2024-01-01T00:00:00Z",
                        "is_active": True
                    }
            
            self._users_cache = users_data
            self._save_to_file()  # Save updated format
            
        except (IOError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load users.json: {e}. Using default admin user.")
            self._users_cache = {
                "admin": {
                    "password": "securepassword123",
                    "email": "admin@example.com",
                    "phone": "",
                    "company": "Indegate Consulting",
                    "preferred_target_country": "US",
                    "full_name": "Administrator",
                    "created_at": "2024-01-01T00:00:00Z",
                    "is_active": True
                }
            }
    
    def _save_to_file(self):
        """Save users cache to file (best effort, won't crash if it fails)."""
        try:
            # Try to set file permissions if needed
            if os.path.exists(self.users_path):
                import stat
                current_permissions = os.stat(self.users_path).st_mode
                if not (current_permissions & stat.S_IWUSR):
                    try:
                        os.chmod(self.users_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                    except (OSError, PermissionError):
                        pass  # Ignore permission errors
            
            with open(self.users_path, 'w') as f:
                json.dump(self._users_cache, f, indent=4)
        except (IOError, PermissionError) as e:
            print(f"Warning: Could not save users.json: {e}. Data will persist in memory during session.")
    
    def get_all_users(self) -> Dict[str, Dict[str, Any]]:
        """Get all users."""
        self._ensure_cache_loaded()
        return self._users_cache.copy()
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a specific user by username."""
        self._ensure_cache_loaded()
        return self._users_cache.get(username)
    
    def create_user(self, username: str, password: str, email: str, 
                   phone: str = "", company: str = "", 
                   preferred_target_country: str = "", full_name: str = "") -> Tuple[bool, str]:
        """Create a new user."""
        self._ensure_cache_loaded()
        
        if username in self._users_cache:
            return False, "Username already exists"
        
        self._users_cache[username] = {
            "password": password,
            "email": email,
            "phone": phone,
            "company": company,
            "preferred_target_country": preferred_target_country,
            "full_name": full_name if full_name else username.title(),
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "is_active": True
        }
        
        self._save_to_file()
        return True, "User created successfully"
    
    def update_user(self, username: str, **kwargs) -> bool:
        """Update user information."""
        self._ensure_cache_loaded()
        
        if username not in self._users_cache:
            return False
        
        allowed_fields = ['email', 'phone', 'company', 'preferred_target_country', 'full_name']
        for key, value in kwargs.items():
            if key in allowed_fields:
                self._users_cache[username][key] = value
        
        self._save_to_file()
        return True
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Authenticate a user."""
        self._ensure_cache_loaded()
        
        if username not in self._users_cache:
            return False, None
        
        user_data = self._users_cache[username]
        if user_data.get('password') == password and user_data.get('is_active', True):
            return True, user_data
        
        return False, None

# Global instance
_user_service = None

def get_user_service() -> UserService:
    """Get the global user service instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
