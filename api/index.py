# This is an alternative if the above doesn't work
from fastapi import FastAPI
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import from main
from main import app
