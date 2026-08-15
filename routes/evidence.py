import os
import uuid
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, send_file)
from werkzeug.utils import secure_filename
from database import get_db
from routes.auth import login_required, role_required
from security.crypto_utils import (compute_sha256, encrypt_file,
                                    decrypt_file, hash_custody_record)
from config import Config
from datetime import datetime
import tempfile

evidence_bp = Blueprint('evidence', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@evidence_bp.route('/evidence')
@login_required
def list_evidence():
    db = get_db()
    role = session.get('role')
    query = {}
    search = request.args.get('search', '')
    case_filter = request.args.get('case_id', '')
    status_filter = request.args.get('status', '')
    if search:
        query['$or'] = [
            {'evidence_id': {'$regex': search, '$options': 'i'}},
            {'file_name': {'$regex': search, '$options': 'i'}},
            {'file_type': {'$regex': search, '$options': 'i'}},
            {'uploaded_by_name': {'$regex': search, '$options': 'i'}}
        ]
    if case_filter:
        query['case_id'] = case_filter
    if status_filter:
        query['status'] = status_filter

    evidence_list = list(db.evidence.find(query).sort('uploaded_at', -1))
    for e in evidence_list:
        e['_id'] = str(e['_id'])
    cases = list(db.cases.find({}, {'case_id': 1, 'case_title': 1}))
    return render_template('evidence.html', evidence_list=evidence_list,
                           cases=cases, search=search,
                           case_filter=case_filter, status_filter=status_filter)

@evidence_bp.route('/evidence/upload', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'investigator', 'analyst')
def upload_evidence():
    db = get_db()
    cases = list(db.cases.find({'status': 'active'}, {'case_id': 1, 'case_title': 1, 'case_number': 1}))
    if request.method == 'POST':
        case_id = request.form.get('case_id')
        evidence_type = request.form.get('evidence_type', '').strip()
        remarks = request.form.get('remarks', '').strip()
        file = request.files.get('file')

        if not file or file.filename == '':
            flash('No file selected.', 'danger')
            return render_template('upload.html', cases=cases)

        if not allowed_file(file.filename):
            flash('File type not allowed.', 'danger')
            return render_template('upload.html', cases=cases)

        if not case_id:
            flash('Please select a case.', 'danger')
            return render_template('upload.html', cases=cases)

        evidence_id = f"EV-{str(uuid.uuid4())[:8].upper()}"
        original_filename = secure_filename(file.filename)
        ext = original_filename.rsplit('.', 1)[-1].lower()
        stored_filename = f"{evidence_id}_{original_filename}"
        upload_path = os.path.join(Config.UPLOAD_FOLDER, stored_filename)
        encrypted_filename = f"{evidence_id}.enc"
        encrypted_path = os.path.join(Config.ENCRYPTED_FOLDER, encrypted_filename)

        # Save original temporarily
        file.save(upload_path)

        # Compute SHA-256 hash
        sha256_hash = compute_sha256(upload_path)

        # Encrypt and store
        encrypt_file(upload_path, encrypted_path)

        # Remove original (keep only encrypted)
        os.remove(upload_path)

        file_size = os.path.getsize(encrypted_path)

        evidence_doc = {
            'evidence_id': evidence_id,
            'case_id': case_id,
            'file_name': original_filename,
            'file_type': evidence_type or ext.upper(),
            'file_size': file_size,
            'encrypted_path': encrypted_path,
            'sha256_hash': sha256_hash,
            'encrypted': True,
            'uploaded_by': session['user_id'],
            'uploaded_by_name': session['user_name'],
            'uploaded_at': datetime.utcnow(),
            'status': 'pending_verification',
            'remarks': remarks
        }
        db.evidence.insert_one(evidence_doc)

        # Create first chain-of-custody entry
        record_data = {
            'evidence_id': evidence_id,
            'user_id': session['user_id'],
            'action': 'UPLOADED',
            'timestamp': str(datetime.utcnow())
        }
        record_hash = hash_custody_record(record_data, '0' * 64)
        db.chain_of_custody.insert_one({
            'custody_id': str(uuid.uuid4()),
            'evidence_id': evidence_id,
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'action': 'UPLOADED',
            'timestamp': datetime.utcnow(),
            'previous_hash': '0' * 64,
            'record_hash': record_hash,
            'remarks': f"Evidence uploaded: {original_filename}"
        })

        # Audit log
        db.audit_logs.insert_one({
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'evidence_id': evidence_id,
            'action': 'EVIDENCE_UPLOADED',
            'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow(),
            'status': 'SUCCESS',
            'details': f"Uploaded {original_filename} for case {case_id}"
        })

        flash(f'Evidence {evidence_id} uploaded successfully! SHA-256: {sha256_hash[:16]}...', 'success')
        return redirect(url_for('evidence.view_evidence', evidence_id=evidence_id))

    return render_template('upload.html', cases=cases)

@evidence_bp.route('/evidence/<evidence_id>')
@login_required
def view_evidence(evidence_id):
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        flash('Evidence not found.', 'danger')
        return redirect(url_for('evidence.list_evidence'))
    ev['_id'] = str(ev['_id'])

    # Chain of custody
    custody_chain = list(db.chain_of_custody.find(
        {'evidence_id': evidence_id}).sort('timestamp', 1))
    for c in custody_chain:
        c['_id'] = str(c['_id'])

    # Audit logs for this evidence
    logs = list(db.audit_logs.find(
        {'evidence_id': evidence_id}).sort('timestamp', -1).limit(20))
    for l in logs:
        l['_id'] = str(l['_id'])

    # Log VIEW action
    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': evidence_id,
        'action': 'VIEWED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"Evidence {evidence_id} viewed."
    })

    # Append to chain of custody
    last_entry = db.chain_of_custody.find_one(
        {'evidence_id': evidence_id}, sort=[('timestamp', -1)])
    prev_hash = last_entry['record_hash'] if last_entry else '0' * 64
    record_data = {'evidence_id': evidence_id, 'user_id': session['user_id'],
                   'action': 'VIEWED', 'timestamp': str(datetime.utcnow())}
    record_hash = hash_custody_record(record_data, prev_hash)
    db.chain_of_custody.insert_one({
        'custody_id': str(uuid.uuid4()),
        'evidence_id': evidence_id,
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'action': 'VIEWED',
        'timestamp': datetime.utcnow(),
        'previous_hash': prev_hash,
        'record_hash': record_hash,
        'remarks': f"Viewed by {session['user_name']}"
    })

    case = db.cases.find_one({'case_id': ev.get('case_id')})
    return render_template('evidence_detail.html', ev=ev,
                           custody_chain=custody_chain, logs=logs, case=case)

@evidence_bp.route('/evidence/<evidence_id>/download')
@login_required
def download_evidence(evidence_id):
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        flash('Evidence not found.', 'danger')
        return redirect(url_for('evidence.list_evidence'))

    encrypted_path = ev.get('encrypted_path')
    if not encrypted_path or not os.path.exists(encrypted_path):
        flash('Encrypted file not found on server.', 'danger')
        return redirect(url_for('evidence.view_evidence', evidence_id=evidence_id))

    # Decrypt to temp file
    tmp_dir = tempfile.mkdtemp()
    decrypted_path = os.path.join(tmp_dir, ev['file_name'])
    decrypt_file(encrypted_path, decrypted_path)

    # Log download
    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': evidence_id,
        'action': 'DOWNLOADED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"Evidence {evidence_id} downloaded."
    })
    last_entry = db.chain_of_custody.find_one(
        {'evidence_id': evidence_id}, sort=[('timestamp', -1)])
    prev_hash = last_entry['record_hash'] if last_entry else '0' * 64
    record_data = {'evidence_id': evidence_id, 'user_id': session['user_id'],
                   'action': 'DOWNLOADED', 'timestamp': str(datetime.utcnow())}
    record_hash = hash_custody_record(record_data, prev_hash)
    db.chain_of_custody.insert_one({
        'custody_id': str(uuid.uuid4()),
        'evidence_id': evidence_id,
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'action': 'DOWNLOADED',
        'timestamp': datetime.utcnow(),
        'previous_hash': prev_hash,
        'record_hash': record_hash,
        'remarks': f"Downloaded by {session['user_name']}"
    })

    return send_file(decrypted_path, as_attachment=True, download_name=ev['file_name'])
