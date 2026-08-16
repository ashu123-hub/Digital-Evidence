import sys
import os

# Make sure project root is in path for all imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module-level app instance (already created via create_app())
from app import app  # noqa: F401

# Vercel looks for a WSGI callable named 'app' in this file
