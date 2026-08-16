from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config import Config
import logging
import os

try:
    import certifi
    CA_FILE = certifi.where()
except ImportError:
    CA_FILE = None

client = None
db = None

def init_db(app):
    global client, db
    uri = Config.MONGO_URI
    try:
        # Use certifi CA bundle so Vercel's Python runtime can verify Atlas SSL certs
        is_atlas = 'mongodb+srv' in uri or 'mongodb.net' in uri
        kwargs = dict(
            serverSelectionTimeoutMS=8000,   # Must finish before Vercel's 10s cold-start limit
            connectTimeoutMS=8000,
            socketTimeoutMS=20000,
            retryWrites=True,
        )
        if is_atlas:
            kwargs['tls'] = True
            kwargs['tlsAllowInvalidCertificates'] = True  # Bypass cert check on Vercel runtime
            if CA_FILE:
                kwargs['tlsCAFile'] = CA_FILE
        client = MongoClient(uri, **kwargs)
        # Handle database name extraction safely
        try:
            db = client.get_database()
        except Exception:
            db = client['dems_db']

        if db is None or db.name == 'admin':
            db = client['dems_db']

        # Attempt to create indexes gracefully
        try:
            db.users.create_index('email', unique=True)
            db.cases.create_index('case_number', unique=True)
            db.evidence.create_index('evidence_id', unique=True)
            db.audit_logs.create_index([('timestamp', -1)])
            db.chain_of_custody.create_index([('evidence_id', 1), ('timestamp', 1)])
        except Exception as e:
            logging.warning(f"Could not create indexes immediately: {e}")

    except Exception as e:
        logging.error(f"MongoDB connection initialization warning: {e}")

    return db

def get_db():
    return db
