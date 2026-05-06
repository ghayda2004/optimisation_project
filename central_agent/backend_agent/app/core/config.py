"""
FILE 1: config.py
Single job: Load all .env variables and expose them as constants for the entire project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# API Keys
ORS_API_KEY = os.getenv("ORS_API_KEY")

# Data Source Paths
CSV_ORDERS_PATH = os.getenv("CSV_ORDERS_PATH", "data/orders.csv")
CSV_DRIVERS_PATH = os.getenv("CSV_DRIVERS_PATH", "data/drivers.csv")

# Cost and Rate Constants (Converted to float for calculations)
FUEL_RATE = float(os.getenv("FUEL_RATE", 0.0))       # Cost per km
HOURLY_RATE = float(os.getenv("HOURLY_RATE", 0.0))   # Driver cost per hour
HANDLING_COST = float(os.getenv("HANDLING_COST", 0.0)) # Cost per stop

# Project Root (Optional utility)
BASE_DIR = Path(__file__).resolve().parent

def validate_config():
    """Simple check to ensure critical variables are present."""
    missing = []
    if not DATABASE_URL: missing.append("DATABASE_URL")
    if not ORS_API_KEY: missing.append("ORS_API_KEY")
    
    if missing:
        print(f"WARNING: Missing environment variables: {', '.join(missing)}")

validate_config()