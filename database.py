from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config import Config
import logging
import os

client = None
db = None

def init_db(app):
    global client, db
    uri = Config.MONGO_URI
    try:
        # On Vercel (serverless), use TLS with relaxed cert validation
        # and a longer timeout since cold starts take more time
        is_atlas = 'mongodb+srv' in uri or 'mongodb.net' in uri
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=15000,
            socketTimeoutMS=30000,
            tls=is_atlas,
            tlsAllowInvalidCertificates=False,
            retryWrites=True,
        )
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
