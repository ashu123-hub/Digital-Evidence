from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from database import get_db
from routes.auth import login_required, role_required
from datetime import datetime
from security.crypto_utils import hash_password

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    db = get_db()
    total_cases = db.cases.count_documents({})
    total_evidence = db.evidence.count_documents({})
    verified_evidence = db.evidence.count_documents({'status': 'verified'})
    pending_evidence = db.evidence.count_documents({'status': 'pending_verification'})
    tampered_evidence = db.evidence.count_documents({'status': 'tampered'})
    total_users = db.users.count_documents({})

    # Recent evidence
    recent_evidence = list(db.evidence.find().sort('uploaded_at', -1).limit(5))
    for e in recent_evidence:
        e['_id'] = str(e['_id'])

    # Recent audit logs
    recent_logs = list(db.audit_logs.find().sort('timestamp', -1).limit(10))
    for l in recent_logs:
        l['_id'] = str(l['_id'])

    # Recent cases
    recent_cases = list(db.cases.find().sort('created_at', -1).limit(5))
    for c in recent_cases:
        c['_id'] = str(c['_id'])

    # Statistics for chart: evidence per case (top 5)
    pipeline = [
        {'$group': {'_id': '$case_id', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 5}
    ]
    ev_per_case = list(db.evidence.aggregate(pipeline))

    stats = {
        'total_cases': total_cases,
        'total_evidence': total_evidence,
        'verified_evidence': verified_evidence,
        'pending_evidence': pending_evidence,
        'tampered_evidence': tampered_evidence,
        'total_users': total_users,
    }

    return render_template('dashboard.html', stats=stats,
                           recent_evidence=recent_evidence,
                           recent_cases=recent_cases,
                           recent_logs=recent_logs,
                           ev_per_case=ev_per_case)

@main_bp.route('/audit-logs')
@login_required
def audit_logs():
    db = get_db()
    page = int(request.args.get('page', 1))
    per_page = 25
    skip = (page - 1) * per_page
    total = db.audit_logs.count_documents({})
    logs = list(db.audit_logs.find().sort('timestamp', -1).skip(skip).limit(per_page))
    for l in logs:
        l['_id'] = str(l['_id'])
    total_pages = (total + per_page - 1) // per_page
    return render_template('audit_logs.html', logs=logs,
                           page=page, total_pages=total_pages, total=total)

@main_bp.route('/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_users():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = (data.get('password') or '').strip()
        role = (data.get('role') or 'investigator').strip()

        if not name or not email or not password:
            return jsonify({'success': False, 'message': 'Name, email, and password are required.'}), 400

        if db.users.find_one({'email': email}):
            return jsonify({'success': False, 'message': 'Email already registered.'}), 409

        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'}), 400

        db.users.insert_one({
            'name': name,
            'email': email,
            'password_hash': hash_password(password),
            'role': role,
            'status': 'active',
            'created_at': datetime.utcnow()
        })
        # Audit log
        db.audit_logs.insert_one({
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'evidence_id': None,
            'action': 'USER_CREATED',
            'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow(),
            'status': 'SUCCESS',
            'details': f"New user '{name}' ({email}) created with role '{role}' by {session['user_name']}."
        })
        return jsonify({'success': True, 'message': f"User '{name}' created successfully."})

    users = list(db.users.find({}, {'password_hash': 0}).sort('created_at', -1))
    for u in users:
        u['_id'] = str(u['_id'])
    return render_template('users.html', users=users)


@main_bp.route('/users/<user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user_status(user_id):
    from bson import ObjectId
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
    if str(user['_id']) == session['user_id']:
        return jsonify({'success': False, 'message': 'You cannot deactivate your own account.'}), 400

    new_status = 'inactive' if user.get('status') == 'active' else 'active'
    db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'status': new_status}})
    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': None,
        'action': 'USER_STATUS_CHANGED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"User '{user['name']}' status changed to '{new_status}' by {session['user_name']}."
    })
    return jsonify({'success': True, 'new_status': new_status, 'message': f"User status changed to {new_status}."})


@main_bp.route('/users/<user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    from bson import ObjectId
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
    if str(user['_id']) == session['user_id']:
        return jsonify({'success': False, 'message': 'You cannot delete your own account.'}), 400

    db.users.delete_one({'_id': ObjectId(user_id)})
    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': None,
        'action': 'USER_DELETED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"User '{user['name']}' ({user['email']}) deleted by {session['user_name']}."
    })
    return jsonify({'success': True, 'message': f"User '{user['name']}' deleted successfully."})
