import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db
from routes.auth import login_required
from security.crypto_utils import compute_sha256, decrypt_file, hash_custody_record
from config import Config
from datetime import datetime
import tempfile

verification_bp = Blueprint('verification', __name__)

@verification_bp.route('/verify/<evidence_id>', methods=['GET', 'POST'])
@login_required
def verify_evidence(evidence_id):
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        flash('Evidence not found.', 'danger')
        return redirect(url_for('evidence.list_evidence'))
    ev['_id'] = str(ev['_id'])
    result = None

    if request.method == 'POST':
        stored_hash = ev.get('sha256_hash')
        encrypted_path = ev.get('encrypted_path')

        if not encrypted_path or not os.path.exists(encrypted_path):
            flash('Encrypted evidence file is missing. Cannot verify.', 'danger')
            return render_template('verification.html', ev=ev, result=None)

        # Decrypt to temp, compute hash
        tmp_dir = tempfile.mkdtemp()
        decrypted_path = os.path.join(tmp_dir, ev['file_name'])
        try:
            decrypt_file(encrypted_path, decrypted_path)
            current_hash = compute_sha256(decrypted_path)
        except Exception as e:
            flash(f'Decryption error: {str(e)}', 'danger')
            return render_template('verification.html', ev=ev, result=None)
        finally:
            if os.path.exists(decrypted_path):
                os.remove(decrypted_path)

        is_verified = stored_hash == current_hash
        result = {
            'stored_hash': stored_hash,
            'current_hash': current_hash,
            'verified': is_verified,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        }

        # Update evidence status
        new_status = 'verified' if is_verified else 'tampered'
        db.evidence.update_one({'evidence_id': evidence_id},
                               {'$set': {'status': new_status, 'last_verified': datetime.utcnow()}})

        # Audit log
        db.audit_logs.insert_one({
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'evidence_id': evidence_id,
            'action': 'VERIFIED' if is_verified else 'TAMPERING_DETECTED',
            'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow(),
            'status': 'SUCCESS' if is_verified else 'ALERT',
            'details': f"Hash match: {is_verified}. Stored: {stored_hash[:16]}... Current: {current_hash[:16]}..."
        })

        # Chain of custody
        last_entry = db.chain_of_custody.find_one(
            {'evidence_id': evidence_id}, sort=[('timestamp', -1)])
        prev_hash = last_entry['record_hash'] if last_entry else '0' * 64
        record_data = {'evidence_id': evidence_id, 'user_id': session['user_id'],
                       'action': 'VERIFIED', 'timestamp': str(datetime.utcnow())}
        record_hash = hash_custody_record(record_data, prev_hash)
        db.chain_of_custody.insert_one({
            'custody_id': str(uuid.uuid4()),
            'evidence_id': evidence_id,
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'action': 'VERIFIED' if is_verified else 'TAMPERING_DETECTED',
            'timestamp': datetime.utcnow(),
            'previous_hash': prev_hash,
            'record_hash': record_hash,
            'remarks': f"Verification {'passed' if is_verified else 'FAILED - tampering detected'} by {session['user_name']}"
        })

    return render_template('verification.html', ev=ev, result=result)


@verification_bp.route('/verify/upload/<evidence_id>', methods=['POST'])
@login_required
def verify_with_file(evidence_id):
    """Verify evidence by uploading the original file and comparing hashes."""
    db = get_db()
    ev = db.evidence.find_one({'evidence_id': evidence_id})
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, 'uploaded_for_verify')
    file.save(tmp_path)
    uploaded_hash = compute_sha256(tmp_path)
    os.remove(tmp_path)

    stored_hash = ev.get('sha256_hash')
    is_verified = stored_hash == uploaded_hash

    return jsonify({
        'verified': is_verified,
        'stored_hash': stored_hash,
        'uploaded_hash': uploaded_hash
    })
