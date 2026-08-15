from flask import Blueprint, render_template, request, session
from database import get_db
from routes.auth import login_required, role_required
from datetime import datetime, timedelta

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

@main_bp.route('/users')
@login_required
@role_required('admin')
def manage_users():
    db = get_db()
    users = list(db.users.find({}, {'password_hash': 0}).sort('created_at', -1))
    for u in users:
        u['_id'] = str(u['_id'])
    return render_template('users.html', users=users)
