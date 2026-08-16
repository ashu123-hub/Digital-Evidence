from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db
from routes.auth import login_required, role_required
from datetime import datetime
import uuid

cases_bp = Blueprint('cases', __name__)

@cases_bp.route('/cases')
@login_required
def list_cases():
    db = get_db()
    role = session.get('role')
    if role == 'admin':
        cases = list(db.cases.find().sort('created_at', -1))
    else:
        cases = list(db.cases.find({'investigator_id': session['user_id']}).sort('created_at', -1))
        # Also show shared cases for analyst
        if role == 'analyst':
            all_cases = list(db.cases.find().sort('created_at', -1))
            cases = all_cases

    for c in cases:
        c['_id'] = str(c['_id'])
        ev_count = db.evidence.count_documents({'case_id': c['case_id']})
        c['evidence_count'] = ev_count

    return render_template('cases.html', cases=cases)

@cases_bp.route('/cases/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'investigator')
def new_case():
    if request.method == 'POST':
        db = get_db()
        case_number = f"CYBER-{datetime.utcnow().year}-{str(uuid.uuid4().int)[:4]:0>4}"
        case_id = f"CASE-{str(uuid.uuid4())[:8].upper()}"
        case = {
            'case_id': case_id,
            'case_number': case_number,
            'case_title': request.form.get('case_title', '').strip(),
            'crime_type': request.form.get('crime_type', '').strip(),
            'description': request.form.get('description', '').strip(),
            'investigator_id': session['user_id'],
            'investigator_name': session['user_name'],
            'status': 'active',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        db.cases.insert_one(case)
        db.audit_logs.insert_one({
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'evidence_id': None,
            'action': 'CASE_CREATED',
            'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow(),
            'status': 'SUCCESS',
            'details': f"Case {case_id} created: {case['case_title']}"
        })
        flash(f'Case {case_id} created successfully!', 'success')
        return redirect(url_for('cases.list_cases'))
    return render_template('new_case.html')

@cases_bp.route('/cases/<case_id>')
@login_required
def view_case(case_id):
    db = get_db()
    case = db.cases.find_one({'case_id': case_id})
    if not case:
        flash('Case not found.', 'danger')
        return redirect(url_for('cases.list_cases'))
    case['_id'] = str(case['_id'])
    IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'}
    evidence_list = list(db.evidence.find({'case_id': case_id}).sort('uploaded_at', -1))
    unlocked_set = set(session.get('unlocked_evidence', []))
    for e in evidence_list:
        e['_id'] = str(e['_id'])
        ext = e.get('file_name', '').rsplit('.', 1)[-1].lower() if '.' in e.get('file_name', '') else ''
        e['is_image'] = ext in IMAGE_EXTS
        e['has_access_code'] = bool(e.get('access_code_hash'))
        e['is_unlocked'] = not e['has_access_code'] or (e['evidence_id'] in unlocked_set)
    return render_template('case_detail.html', case=case, evidence_list=evidence_list)

@cases_bp.route('/cases/<case_id>/close', methods=['POST'])
@login_required
@role_required('admin', 'investigator')
def close_case(case_id):
    db = get_db()
    db.cases.update_one({'case_id': case_id}, {'$set': {'status': 'closed', 'updated_at': datetime.utcnow()}})
    flash('Case closed.', 'info')
    return redirect(url_for('cases.view_case', case_id=case_id))

@cases_bp.route('/cases/<case_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_case(case_id):
    db = get_db()
    case = db.cases.find_one({'case_id': case_id})
    if not case:
        flash('Case not found.', 'danger')
        return redirect(url_for('cases.list_cases'))

    # Delete all associated evidence files and records
    import os
    from config import Config
    evidence_list = list(db.evidence.find({'case_id': case_id}))
    for ev in evidence_list:
        # Remove encrypted file
        enc_path = os.path.join(Config.ENCRYPTED_FOLDER, ev.get('encrypted_file', ''))
        if ev.get('encrypted_file') and os.path.exists(enc_path):
            try:
                os.remove(enc_path)
            except Exception:
                pass
        # Remove original uploaded file (if still present)
        orig_path = os.path.join(Config.UPLOAD_FOLDER, ev.get('file_name', ''))
        if ev.get('file_name') and os.path.exists(orig_path):
            try:
                os.remove(orig_path)
            except Exception:
                pass
        # Remove chain of custody records for each evidence
        db.chain_of_custody.delete_many({'evidence_id': ev.get('evidence_id')})

    # Delete all evidence records for this case
    db.evidence.delete_many({'case_id': case_id})

    # Audit log
    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': None,
        'action': 'CASE_DELETED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"Case {case_id} permanently deleted with {len(evidence_list)} evidence item(s)"
    })

    # Delete the case itself
    db.cases.delete_one({'case_id': case_id})

    flash(f'Case {case_id} and all associated evidence permanently deleted.', 'danger')
    return redirect(url_for('cases.list_cases'))
