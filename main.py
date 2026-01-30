"""
FastAPI service for biomass processing facility optimization.
Accepts variables (fuel_price, commodity_cost, energy_price, weather_index)
and performs multivariate interpolation on CSV data.
Results are persisted to SQLite database and can be queried for historical data.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from scipy.interpolate import LinearNDInterpolator, RBFInterpolator
import json
import sqlite3
from datetime import datetime
from pathlib import Path

app = FastAPI(title="Biomass Optimizer API")

# Initialize SQLite database
DB_PATH = "biomass_results.db"

def init_db():
    """Create results table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            fuel_price REAL NOT NULL,
            commodity_cost REAL NOT NULL,
            energy_price REAL NOT NULL,
            weather_index REAL NOT NULL,
            calculated_output REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def store_result(fuel_price, commodity_cost, energy_price, weather_index, calculated_output):
    """Store calculation result in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO calculations (timestamp, fuel_price, commodity_cost, energy_price, weather_index, calculated_output)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, fuel_price, commodity_cost, energy_price, weather_index, calculated_output))
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Add CORS middleware to allow requests from Grafana
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load CSV data at startup
try:
    df = pd.read_csv("sample_data.csv")
    print(f"Loaded {len(df)} data points from sample_data.csv")
except FileNotFoundError:
    print("ERROR: sample_data.csv not found. Place it in the same directory as main.py")
    df = None

# Prepare interpolator on startup
interpolator = None
try:
    if df is not None and len(df) > 0:
        # Extract input features and output
        X = df[["fuel_price", "commodity_cost", "energy_price", "weather_index"]].values
        y = df["output_metric"].values
        
        # Use RBFInterpolator for extrapolation beyond training data
        # It can handle values outside the training range better than LinearND
        interpolator = RBFInterpolator(X, y, kernel='thin_plate_spline', smoothing=0.0)
        print(f"Interpolator initialized with {len(X)} data points")
except Exception as e:
    print(f"ERROR initializing interpolator: {e}")


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Biomass Optimizer API",
        "endpoint": "/calculate?fuel_price=2.0&commodity_cost=5.0&energy_price=1.0&weather_index=50"
    }


@app.get("/calculate")
def calculate(
    fuel_price: float,
    commodity_cost: float,
    energy_price: float,
    weather_index: float
):
    """
    Calculate output metric based on input variables.
    
    Performs multivariate interpolation on CSV data and stores result in database.
    
    Args:
        fuel_price: Price of fuel (0-10)
        commodity_cost: Cost of commodity (0-20)
        energy_price: Price of energy (0-5)
        weather_index: Weather index (0-100)
    
    Returns:
        JSON with all inputs echoed back + calculated_output
    """
    
    if interpolator is None:
        return {
            "error": "Interpolator not initialized",
            "fuel_price": fuel_price,
            "commodity_cost": commodity_cost,
            "energy_price": energy_price,
            "weather_index": weather_index
        }
    
    try:
        # Prepare input point for interpolation
        input_point = np.array([[fuel_price, commodity_cost, energy_price, weather_index]])
        
        # Perform interpolation (RBF expects 2D input)
        calculated_output = float(interpolator(input_point)[0])
        
        # Round to 2 decimals
        calculated_output = round(calculated_output, 2)
        
        # Store result in database
        store_result(fuel_price, commodity_cost, energy_price, weather_index, calculated_output)
        
        return {
            "fuel_price": fuel_price,
            "commodity_cost": commodity_cost,
            "energy_price": energy_price,
            "weather_index": weather_index,
            "calculated_output": calculated_output
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "fuel_price": fuel_price,
            "commodity_cost": commodity_cost,
            "energy_price": energy_price,
            "weather_index": weather_index
        }


@app.get("/health")
def health():
    """Health check for orchestration."""
    return {"status": "healthy"}


@app.get("/results/latest")
def get_latest_result():
    """Get the most recent calculation result from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, fuel_price, commodity_cost, energy_price, weather_index, calculated_output
            FROM calculations
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        else:
            return {"message": "No results yet"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/results/history")
def get_results_history():
    """Get all calculation results from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, fuel_price, commodity_cost, energy_price, weather_index, calculated_output
            FROM calculations
            ORDER BY id DESC
            LIMIT 100
        """)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}


@app.get("/results/clear")
def clear_results():
    """Clear all results from database (for testing)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM calculations")
        conn.commit()
        conn.close()
        return {"status": "Database cleared"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
