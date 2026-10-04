import os
import uuid
import tempfile
import zipfile
import io
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, send_file, jsonify, Response)
from werkzeug.utils import secure_filename
from database import get_db
from routes.auth import login_required, role_required
from security.crypto_utils import (compute_sha256, encrypt_file,
                                    decrypt_file, decrypt_to_bytes,
                                    hash_custody_record, hash_password,
                                    verify_password)
from config import Config

evidence_bp = Blueprint('evidence', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def get_preview_info(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'}:
        return 'image', f'image/{ext if ext != "jpg" else "jpeg"}'
    elif ext == 'pdf':
        return 'pdf', 'application/pdf'
    elif ext in {'txt', 'log', 'csv', 'json', 'xml', 'eml', 'msg', 'py', 'js', 'html', 'css', 'sql', 'md'}:
        return 'text', 'text/plain; charset=utf-8'
    elif ext in {'mp4', 'webm', 'mov', 'mkv', 'avi'}:
        return 'video', f'video/{ext if ext != "mov" else "quicktime"}'
    elif ext in {'mp3', 'wav', 'aac', 'ogg', 'flac'}:
        return 'audio', f'audio/{ext if ext != "mp3" else "mpeg"}'
    elif ext in {'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}:
        return 'document', 'application/octet-stream'
    elif ext in {'zip', 'tar', 'gz', '7z', 'rar'}:
        return 'archive', 'application/octet-stream'
    else:
        return 'file', 'application/octet-stream'

def is_evidence_unlocked(ev, code=None):
    """Check if evidence is unlocked either via session, lack of access code, or matching code."""
    access_code_hash = ev.get('access_code_hash')
    if not access_code_hash:
        return True
    
    unlocked_list = session.get('unlocked_evidence', [])
    if ev.get('evidence_id') in unlocked_list:
        return True
        
    if code and verify_password(code, access_code_hash):
        if 'unlocked_evidence' not in session:
            session['unlocked_evidence'] = []
        if ev.get('evidence_id') not in session['unlocked_evidence']:
            session['unlocked_evidence'].append(ev.get('evidence_id'))
            session.modified = True
        return True
        
    return False

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
    unlocked_set = set(session.get('unlocked_evidence', []))
    for e in evidence_list:
        e['_id'] = str(e['_id'])
        preview_type, _ = get_preview_info(e.get('file_name', ''))
        e['preview_type'] = preview_type
        e['is_image'] = preview_type == 'image'
        e['has_access_code'] = bool(e.get('access_code_hash'))
        e['is_unlocked'] = not e['has_access_code'] or (e['evidence_id'] in unlocked_set)

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
        access_code = request.form.get('access_code', '').strip()
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
        access_code_hash = hash_password(access_code) if access_code else None

        evidence_doc = {
            'evidence_id': evidence_id,
            'case_id': case_id,
            'file_name': original_filename,
            'file_type': evidence_type or ext.upper(),
            'file_size': file_size,
            'encrypted_path': encrypted_path,
            'sha256_hash': sha256_hash,
            'encrypted': True,
            'access_code_hash': access_code_hash,
            'has_access_code': bool(access_code_hash),
            'uploaded_by': session['user_id'],
            'uploaded_by_name': session['user_name'],
            'uploaded_at': datetime.utcnow(),
            'status': 'pending_verification',
            'remarks': remarks
        }
        db.evidence.insert_one(evidence_doc)

        # Auto-unlock for the uploader in this session
        if 'unlocked_evidence' not in session:
            session['unlocked_evidence'] = []
        session['unlocked_evidence'].append(evidence_id)
        session.modified = True

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
            'remarks': f"Evidence uploaded: {original_filename} (Code Protected: {'Yes' if access_code else 'No'})"
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
            'details': f"Uploaded {original_filename} for case {case_id} (Protected with Access Code: {'Yes' if access_code else 'No'})"
        })

        flash(f'Evidence {evidence_id} uploaded & encrypted successfully! SHA-256: {sha256_hash[:16]}...', 'success')
        return redirect(url_for('evidence.view_evidence', evidence_id=evidence_id))

    return render_template('upload.html', cases=cases)

@evidence_bp.route('/evidence/<evidence_id>/verify-code', methods=['POST'])
@login_required
def verify_evidence_code(evidence_id):
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        return jsonify({'success': False, 'message': 'Evidence not found.'}), 404

    access_code_hash = ev.get('access_code_hash')
    if not access_code_hash:
        return jsonify({'success': True, 'message': 'Evidence does not require an access code.'})

    data = request.get_json(silent=True) or request.form
    entered_code = (data.get('access_code') or '').strip()

    if not entered_code:
        return jsonify({'success': False, 'message': 'Please enter the access code.'}), 400

    if verify_password(entered_code, access_code_hash):
        if 'unlocked_evidence' not in session:
            session['unlocked_evidence'] = []
        if evidence_id not in session['unlocked_evidence']:
            session['unlocked_evidence'].append(evidence_id)
            session.modified = True

        # Log successful unlock audit
        db.audit_logs.insert_one({
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'evidence_id': evidence_id,
            'action': 'ACCESS_CODE_VERIFIED',
            'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow(),
            'status': 'SUCCESS',
            'details': f"Access code verified successfully for {evidence_id}"
        })
        return jsonify({
            'success': True,
            'message': 'Access code verified successfully!',
            'preview_url': url_for('evidence.inline_evidence', evidence_id=evidence_id),
            'download_url': url_for('evidence.download_evidence', evidence_id=evidence_id)
        })
    else:
        # Log failed attempt
        db.audit_logs.insert_one({
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'evidence_id': evidence_id,
            'action': 'ACCESS_CODE_FAILED',
            'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow(),
            'status': 'FAILED',
            'details': f"Incorrect access code entered for {evidence_id}"
        })
        return jsonify({'success': False, 'message': 'Incorrect access code. Access denied.'}), 403

@evidence_bp.route('/evidence/<evidence_id>/inline')
@login_required
def inline_evidence(evidence_id):
    """In-browser preview is disabled for all evidence types to preserve forensic integrity."""
    return Response(
        "In-browser preview is disabled for all evidence types to protect forensic integrity. Evidence remains encrypted at rest.",
        status=403,
        mimetype="text/plain"
    )

@evidence_bp.route('/evidence/<evidence_id>')
@login_required
def view_evidence(evidence_id):
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        flash('Evidence not found.', 'danger')
        return redirect(url_for('evidence.list_evidence'))
    ev['_id'] = str(ev['_id'])

    preview_type, _ = get_preview_info(ev.get('file_name', ''))
    has_access_code = bool(ev.get('access_code_hash'))
    is_unlocked = is_evidence_unlocked(ev)

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
                           custody_chain=custody_chain, logs=logs, case=case,
                           preview_type=preview_type, is_image=(preview_type == 'image'),
                           has_access_code=has_access_code,
                           is_unlocked=is_unlocked)

@evidence_bp.route('/evidence/<evidence_id>/download-hash')
@login_required
def download_evidence_hash(evidence_id):
    """Generate and return a .hash file for the given evidence."""
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        flash('Evidence not found.', 'danger')
        return redirect(url_for('evidence.list_evidence'))

    code = request.args.get('code')
    if not is_evidence_unlocked(ev, code):
        flash('Security Access Code is required to download the hash file.', 'danger')
        return redirect(url_for('evidence.view_evidence', evidence_id=evidence_id))

    sha256_hash = ev.get('sha256_hash', 'N/A')
    uploaded_at = ev.get('uploaded_at', '')
    downloaded_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    hash_content = (
        f"========================================\n"
        f"  DIGITAL EVIDENCE MANAGEMENT SYSTEM\n"
        f"  Evidence Hash Certificate\n"
        f"========================================\n\n"
        f"Evidence ID   : {ev.get('evidence_id', 'N/A')}\n"
        f"File Name     : {ev.get('file_name', 'N/A')}\n"
        f"File Type     : {ev.get('file_type', 'N/A')}\n"
        f"Case ID       : {ev.get('case_id', 'N/A')}\n"
        f"Uploaded By   : {ev.get('uploaded_by_name', 'N/A')}\n"
        f"Uploaded At   : {str(uploaded_at)[:19]} UTC\n"
        f"Downloaded At : {downloaded_at}\n"
        f"Downloaded By : {session.get('user_name', 'N/A')}\n\n"
        f"----------------------------------------\n"
        f"Algorithm     : SHA-256\n"
        f"Hash Value    : {sha256_hash}\n"
        f"----------------------------------------\n\n"
        f"To verify integrity:\n"
        f"  Windows : certutil -hashfile <filename> SHA256\n"
        f"  Linux   : sha256sum <filename>\n"
        f"  macOS   : shasum -a 256 <filename>\n\n"
        f"Compare the output with the Hash Value above.\n"
        f"Any mismatch indicates the file has been tampered with.\n"
        f"========================================\n"
    )

    # Log the hash download
    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': evidence_id,
        'action': 'HASH_DOWNLOADED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"Hash file downloaded for evidence {evidence_id}."
    })

    hash_filename = f"{evidence_id}_SHA256.hash"
    return Response(
        hash_content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{hash_filename}"',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'
        }
    )


@evidence_bp.route('/evidence/<evidence_id>/download')
@login_required
def download_evidence(evidence_id):
    """Raw evidence files cannot be downloaded — redirect to hash certificate download."""
    code = request.args.get('code')
    if code:
        return redirect(url_for('evidence.download_evidence_bundle', evidence_id=evidence_id, code=code))
    return redirect(url_for('evidence.download_evidence_bundle', evidence_id=evidence_id))



@evidence_bp.route('/evidence/<evidence_id>/download-bundle')
@login_required
def download_evidence_bundle(evidence_id):
    """Return only the SHA-256 hash certificate — the evidence file is never decrypted or sent."""
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        flash('Evidence not found.', 'danger')
        return redirect(url_for('evidence.list_evidence'))

    code = request.args.get('code')
    if not is_evidence_unlocked(ev, code):
        flash('Security Access Code is required.', 'danger')
        return redirect(url_for('evidence.view_evidence', evidence_id=evidence_id))

    # Build hash certificate — NO decryption of evidence file, image stays encrypted
    sha256_hash = ev.get('sha256_hash', 'N/A')
    uploaded_at = ev.get('uploaded_at', '')
    downloaded_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    hash_content = (
        f"========================================\n"
        f"  DIGITAL EVIDENCE MANAGEMENT SYSTEM\n"
        f"  Evidence Hash Certificate\n"
        f"========================================\n\n"
        f"Evidence ID   : {ev.get('evidence_id', 'N/A')}\n"
        f"File Name     : {ev.get('file_name', 'N/A')}\n"
        f"File Type     : {ev.get('file_type', 'N/A')}\n"
        f"Case ID       : {ev.get('case_id', 'N/A')}\n"
        f"Uploaded By   : {ev.get('uploaded_by_name', 'N/A')}\n"
        f"Uploaded At   : {str(uploaded_at)[:19]} UTC\n"
        f"Downloaded At : {downloaded_at}\n"
        f"Downloaded By : {session.get('user_name', 'N/A')}\n\n"
        f"----------------------------------------\n"
        f"Algorithm     : SHA-256\n"
        f"Hash Value    : {sha256_hash}\n"
        f"----------------------------------------\n\n"
        f"NOTE: The evidence file remains encrypted on the server.\n"
        f"      This certificate is issued for integrity verification only.\n\n"
        f"To verify integrity (when you have the original file):\n"
        f"  Windows : certutil -hashfile \"{ev.get('file_name')}\" SHA256\n"
        f"  Linux   : sha256sum \"{ev.get('file_name')}\"\n"
        f"  macOS   : shasum -a 256 \"{ev.get('file_name')}\"\n\n"
        f"Compare the output with the Hash Value above.\n"
        f"Any mismatch indicates the file has been tampered with.\n"
        f"========================================\n"
    )

    # Audit log — only hash issued, evidence file NOT touched
    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': evidence_id,
        'action': 'HASH_DOWNLOADED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"Hash certificate downloaded for {evidence_id} (evidence file NOT decrypted)."
    })
    last_entry = db.chain_of_custody.find_one(
        {'evidence_id': evidence_id}, sort=[('timestamp', -1)])
    prev_hash_val = last_entry['record_hash'] if last_entry else '0' * 64
    record_data = {'evidence_id': evidence_id, 'user_id': session['user_id'],
                   'action': 'HASH_DOWNLOADED', 'timestamp': str(datetime.utcnow())}
    record_hash = hash_custody_record(record_data, prev_hash_val)
    db.chain_of_custody.insert_one({
        'custody_id': str(uuid.uuid4()),
        'evidence_id': evidence_id,
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'action': 'HASH_DOWNLOADED',
        'timestamp': datetime.utcnow(),
        'previous_hash': prev_hash_val,
        'record_hash': record_hash,
        'remarks': f"Hash certificate issued to {session['user_name']} — evidence remains encrypted."
    })

    hash_filename = f"{evidence_id}_SHA256.hash"
    return Response(
        hash_content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{hash_filename}"',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'
        }
    )


@evidence_bp.route('/evidence/<evidence_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'investigator')
def delete_evidence(evidence_id):
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        return jsonify({'success': False, 'message': 'Evidence not found.'}), 404

    # Remove encrypted file from disk
    encrypted_path = ev.get('encrypted_path')
    if encrypted_path and os.path.exists(encrypted_path):
        try:
            os.remove(encrypted_path)
        except Exception:
            pass  # log but do not block deletion

    case_id = ev.get('case_id')

    # Remove evidence record
    db.evidence.delete_one({'evidence_id': evidence_id})

    # Remove chain of custody records
    db.chain_of_custody.delete_many({'evidence_id': evidence_id})

    # Audit log the deletion
    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': evidence_id,
        'action': 'DELETED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"Evidence {evidence_id} ({ev.get('file_name')}) permanently deleted by {session['user_name']}."
    })

    return jsonify({'success': True, 'message': f"Evidence {evidence_id} deleted successfully.", 'case_id': case_id})
