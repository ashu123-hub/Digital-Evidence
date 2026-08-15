from pymongo import MongoClient
from config import Config

client = None
db = None

def init_db(app):
    global client, db
    client = MongoClient(Config.MONGO_URI)
    db = client.get_database()
    # Create indexes
    db.users.create_index('email', unique=True)
    db.cases.create_index('case_number', unique=True)
    db.evidence.create_index('evidence_id', unique=True)
    db.audit_logs.create_index([('timestamp', -1)])
    db.chain_of_custody.create_index([('evidence_id', 1), ('timestamp', 1)])
    return db

def get_db():
    return db
