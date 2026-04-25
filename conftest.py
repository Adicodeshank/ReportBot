# conftest.py
# Tells pytest to add the project root to Python's path
# so 'from app.database import ...' works from anywhere.
import sys
import os

sys.path.insert(0, os.path.dirname(__file__)) 