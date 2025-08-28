from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from .. import User, load_users, create_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        from ..services.user_service import get_user_service
        user_service = get_user_service()
        
        authenticated, user_data = user_service.authenticate_user(username, password)
        if authenticated and user_data:
            user = User(username, user_data)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.home'))
        else:
            flash('Please check your login details and try again.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        phone = request.form.get('phone', '')
        company = request.form.get('company', '')
        preferred_target_country = request.form.get('preferred_target_country', '')
        full_name = request.form.get('full_name', '')
        
        # Validation
        if not username or not password or not email:
            flash('Username, password, and email are required.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
        else:
            success, message = create_user(
                username=username,
                password=password,
                email=email,
                phone=phone,
                company=company,
                preferred_target_country=preferred_target_country,
                full_name=full_name
            )
            
            if success:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash(message, 'danger')
    
    # Get countries for dropdown
    config_service = current_app.config.get('CONFIG_SERVICE')
    countries = []
    if config_service:
        countries = config_service.get_countries(limit=50)  # Popular countries for registration
    
    return render_template('auth/register.html', countries=countries)

@auth_bp.route('/profile')
@login_required
def profile():
    """View user profile."""
    return render_template('auth/profile.html')

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile."""
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone', '')
        company = request.form.get('company', '')
        preferred_target_country = request.form.get('preferred_target_country', '')
        full_name = request.form.get('full_name', '')
        
        if not email:
            flash('Email is required.', 'danger')
        else:
            success = current_user.update_profile(
                email=email,
                phone=phone,
                company=company,
                preferred_target_country=preferred_target_country,
                full_name=full_name
            )
            
            if success:
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('auth.profile'))
            else:
                flash('Error updating profile.', 'danger')
    
    # Get countries for dropdown
    config_service = current_app.config.get('CONFIG_SERVICE')
    countries = []
    if config_service:
        countries = config_service.get_countries(limit=50)
    
    return render_template('auth/edit_profile.html', countries=countries)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 