import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/dems_db'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ENCRYPTED_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'encrypted_evidence')
    REPORTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB

    ALLOWED_EXTENSIONS = {
        'jpg', 'jpeg', 'png', 'gif', 'bmp',
        'mp4', 'avi', 'mov', 'mkv',
        'mp3', 'wav', 'aac',
        'pdf', 'txt', 'log', 'csv',
        'zip', 'tar', 'gz',
        'eml', 'msg',
        'doc', 'docx', 'xls', 'xlsx'
    }

    # AES-256 encryption key (32 bytes)
    AES_KEY = os.environ.get('AES_KEY') or b'DEMS_AES256_KEY_32BYTES_SECURE!!'[:32]
    AES_KEY = AES_KEY if isinstance(AES_KEY, bytes) else AES_KEY.encode()[:32]
    AES_KEY = AES_KEY.ljust(32, b'0')[:32]

    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
