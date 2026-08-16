import hashlib
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from config import Config

def compute_sha256(file_path):
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()

def encrypt_file(input_path: str, output_path: str) -> str:
    """Encrypt a file using AES-256-CBC. Returns the IV hex."""
    iv = os.urandom(16)
    cipher = AES.new(Config.AES_KEY, AES.MODE_CBC, iv)
    with open(input_path, 'rb') as f:
        plaintext = f.read()
    ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
    with open(output_path, 'wb') as f:
        f.write(iv + ciphertext)  # Prepend IV
    return iv.hex()

def decrypt_file(encrypted_path: str, output_path: str):
    """Decrypt an AES-256-CBC encrypted file."""
    with open(encrypted_path, 'rb') as f:
        raw = f.read()
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = AES.new(Config.AES_KEY, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    with open(output_path, 'wb') as f:
        f.write(plaintext)

def decrypt_to_bytes(encrypted_path: str) -> bytes:
    """Decrypt an AES-256-CBC encrypted file directly to bytes in memory."""
    with open(encrypted_path, 'rb') as f:
        raw = f.read()
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = AES.new(Config.AES_KEY, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)

def hash_custody_record(record_data: dict, previous_hash: str) -> str:
    """Generate a hash for a chain-of-custody record linked to the previous hash."""
    record_str = (
        str(record_data.get('evidence_id', '')) +
        str(record_data.get('user_id', '')) +
        str(record_data.get('action', '')) +
        str(record_data.get('timestamp', '')) +
        str(previous_hash)
    )
    return hashlib.sha256(record_str.encode()).hexdigest()

def hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False
