import os
from flask import Flask, redirect, url_for
from config import Config
from database import init_db
from routes.auth import auth_bp
from routes.main import main_bp
from routes.cases import cases_bp
from routes.evidence import evidence_bp
from routes.verification import verification_bp
from routes.reports import reports_bp
from security.crypto_utils import hash_password
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure folders exist
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.ENCRYPTED_FOLDER, exist_ok=True)
    os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)
    os.makedirs('flask_session', exist_ok=True)

    # Initialize MongoDB
    db = init_db(app)

    # Seed default admin user if not exists
    seed_admin(db)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(reports_bp)

    @app.route('/')
    def index():
        return redirect(url_for('main.dashboard'))

    # Template filter for datetime formatting
    @app.template_filter('datefmt')
    def datefmt(value, fmt='%Y-%m-%d %H:%M'):
        if not value:
            return '-'
        if isinstance(value, str):
            return value[:16]
        try:
            return value.strftime(fmt)
        except Exception:
            return str(value)[:16]

    @app.template_filter('enumerate')
    def enumerate_filter(iterable, start=0):
        return enumerate(iterable, start)

    app.jinja_env.globals['enumerate'] = enumerate

    @app.template_filter('filesizefmt')
    def filesizefmt(value):
        try:
            value = int(value)
            if value < 1024:
                return f"{value} B"
            elif value < 1024 * 1024:
                return f"{value / 1024:.1f} KB"
            else:
                return f"{value / (1024*1024):.2f} MB"
        except Exception:
            return str(value)

    return app

def seed_admin(db):
    """Create default admin, investigator, and analyst accounts."""
    users = [
        {'name': 'System Admin', 'email': 'admin@dems.gov', 'password': 'Admin@123', 'role': 'admin'},
        {'name': 'John Investigator', 'email': 'investigator@dems.gov', 'password': 'Inv@123', 'role': 'investigator'},
        {'name': 'Lisa Analyst', 'email': 'analyst@dems.gov', 'password': 'Analyst@123', 'role': 'analyst'},
    ]
    for u in users:
        if not db.users.find_one({'email': u['email']}):
            db.users.insert_one({
                'name': u['name'],
                'email': u['email'],
                'password_hash': hash_password(u['password']),
                'role': u['role'],
                'status': 'active',
                'created_at': datetime.utcnow()
            })
    # Seed sample cases
    if db.cases.count_documents({}) == 0:
        import uuid
        sample_cases = [
            {'case_id': 'CASE-001', 'case_number': 'CYBER-2026-001', 'case_title': 'Phishing Investigation', 'crime_type': 'Phishing', 'description': 'Large scale phishing campaign targeting corporate emails.'},
            {'case_id': 'CASE-002', 'case_number': 'CYBER-2026-002', 'case_title': 'Ransomware Attack', 'crime_type': 'Ransomware', 'description': 'Ransomware attack on municipal systems.'},
            {'case_id': 'CASE-003', 'case_number': 'CYBER-2026-003', 'case_title': 'Data Breach Investigation', 'crime_type': 'Data Theft', 'description': 'Unauthorized exfiltration of customer PII data.'},
            {'case_id': 'CASE-004', 'case_number': 'CYBER-2026-004', 'case_title': 'Unauthorized System Access', 'crime_type': 'Unauthorized Access', 'description': 'Intrusion detected in financial systems.'},
            {'case_id': 'CASE-005', 'case_number': 'CYBER-2026-005', 'case_title': 'Email Spoofing Fraud', 'crime_type': 'Email Spoofing', 'description': 'CFO impersonation email fraud resulting in wire transfer.'},
        ]
        for c in sample_cases:
            admin = db.users.find_one({'role': 'admin'})
            c.update({
                'investigator_id': str(admin['_id']) if admin else '',
                'investigator_name': admin['name'] if admin else 'Admin',
                'status': 'active',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            db.cases.insert_one(c)

app = create_app()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  DIGITAL EVIDENCE MANAGEMENT SYSTEM (DEMS)")
    print("  Running at: http://127.0.0.1:5000")
    print("="*60)
    print("\n  Default Login Credentials:")
    print("  Admin:       admin@dems.gov       | Admin@123")
    print("  Investigator: investigator@dems.gov | Inv@123")
    print("  Analyst:     analyst@dems.gov     | Analyst@123")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

