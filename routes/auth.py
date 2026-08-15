from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db
from security.crypto_utils import hash_password, verify_password
from datetime import datetime
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        db = get_db()
        user = db.users.find_one({'email': email, 'status': 'active'})
        if user and verify_password(password, user['password_hash']):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            # Audit log
            db.audit_logs.insert_one({
                'user_id': str(user['_id']),
                'user_name': user['name'],
                'evidence_id': None,
                'action': 'LOGIN',
                'ip_address': request.remote_addr,
                'timestamp': datetime.utcnow(),
                'status': 'SUCCESS',
                'details': f"User {user['name']} logged in."
            })
            flash(f"Welcome back, {user['name']}!", 'success')
            return redirect(url_for('main.dashboard'))
        else:
            # Log failed attempt
            db.audit_logs.insert_one({
                'user_id': None,
                'user_name': email,
                'evidence_id': None,
                'action': 'LOGIN_FAILED',
                'ip_address': request.remote_addr,
                'timestamp': datetime.utcnow(),
                'status': 'FAILED',
                'details': f"Failed login attempt for {email}."
            })
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    db = get_db()
    db.audit_logs.insert_one({
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'evidence_id': None,
        'action': 'LOGOUT',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"User {session.get('user_name')} logged out."
    })
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'investigator')
        db = get_db()
        if db.users.find_one({'email': email}):
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        db.users.insert_one({
            'name': name,
            'email': email,
            'password_hash': hash_password(password),
            'role': role,
            'status': 'active',
            'created_at': datetime.utcnow()
        })
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')
