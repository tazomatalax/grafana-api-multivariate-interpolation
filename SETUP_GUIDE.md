# Biomass Processing Dashboard - Complete Setup Guide

> **Interactive Grafana dashboard for biomass processing optimization with real-time calculations, database persistence, and historical tracking.**

This guide provides step-by-step instructions to replicate the entire setup from scratch.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Testing & Verification](#testing--verification)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)
8. [Extending the System](#extending-the-system)

---

## System Overview

### Architecture

```
User Dashboard (Grafana)
    ↓
    Variable inputs (fuel_price, commodity_cost, energy_price, weather_index)
    ↓
    Infinity Datasource Plugin (HTTP GET)
    ↓
FastAPI Backend Service (localhost:8000)
    ├─ /calculate endpoint
    │   ├─ Accepts 4 query parameters
    │   ├─ Performs multivariate interpolation (SciPy)
    │   └─ Writes result to SQLite database
    │
    ├─ /results/latest (most recent calculation)
    └─ /results/history (last 100 calculations)
    ↓
SQLite Database (biomass_results.db)
    └─ calculations table with timestamps
```

### Key Features

- **Real-time calculations**: Users adjust variables → backend interpolates → results display instantly
- **Database persistence**: Every calculation stored with timestamp
- **Historical tracking**: View all past calculations in a sortable table
- **Multivariate interpolation**: Uses SciPy RBFInterpolator for smooth extrapolation
- **Extensible**: Easy to add more variables or datasets

---

## Prerequisites

### Required Software

1. **Python 3.8+**
   - Install from: https://www.python.org/downloads/
   - Verify: `python --version`

2. **Grafana v11.x**
   - Download: https://grafana.com/grafana/download
   - Windows installer recommended

3. **Git** (optional, for cloning)
   - Download: https://git-scm.com/downloads

### Python Packages

All required packages are in `requirements.txt`:
```
fastapi==0.104.1
uvicorn==0.24.0
pandas==2.1.3
numpy==1.26.2
scipy==1.11.4
```

---

## Installation Steps

### Step 1: Set Up the Project Directory

```powershell
# Create project directory
mkdir c:\biomass-api
cd c:\biomass-api
```

### Step 2: Create Python Files

#### 2.1 Create `main.py` (FastAPI Backend)

```python
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
from scipy.interpolate import RBFInterpolator
import sqlite3
from datetime import datetime

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
```

#### 2.2 Create `requirements.txt`

```
fastapi==0.104.1
uvicorn==0.24.0
pandas==2.1.3
numpy==1.26.2
scipy==1.11.4
```

#### 2.3 Create `sample_data.csv` (Training Data)

```csv
fuel_price,commodity_cost,energy_price,weather_index,output_metric
0.5,1.0,0.5,20,35.2
0.8,2.5,0.8,30,38.5
1.2,3.0,1.0,40,42.1
1.5,5.0,1.2,50,45.8
2.0,6.0,1.5,60,48.3
2.5,8.0,1.8,70,51.2
3.0,10.0,2.0,80,54.6
3.5,12.0,2.3,85,57.1
4.0,15.0,2.5,90,59.8
4.5,18.0,3.0,95,62.4
5.0,20.0,3.5,100,65.1
```

**Note**: Add more rows with varied data points for better interpolation accuracy. The system works with any number of rows.



### Step 3: Install Python Dependencies

```powershell
cd c:\biomass-api
pip install -r requirements.txt
```

### Step 4: Start the FastAPI Service

```powershell
cd c:\biomass-api
python main.py
```

**Expected output**:
```
Database initialized at biomass_results.db
Loaded 11 data points from sample_data.csv
Interpolator initialized with 11 data points
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verify API is working**:
```powershell
curl "http://127.0.0.1:8000/calculate?fuel_price=2&commodity_cost=8&energy_price=1.5&weather_index=60"
```

Expected response:
```json
{
  "fuel_price": 2.0,
  "commodity_cost": 8.0,
  "energy_price": 1.5,
  "weather_index": 60.0,
  "calculated_output": 49.23
}
```

---

## Configuration

### Step 5: Install Grafana Infinity Plugin

The Infinity datasource plugin allows Grafana to query REST APIs directly.

```powershell
cd "c:\Program Files\GrafanaLabs\grafana"
.\bin\grafana-cli.exe plugins install yesoreyeram-infinity-datasource
```

**Expected output**:
```
✔ Downloaded and extracted yesoreyeram-infinity-datasource v3.7.0
```

### Step 6: Configure the Infinity Datasource

Create datasource configuration file:

**File**: `c:\Program Files\GrafanaLabs\grafana\conf\provisioning\datasources\biomass-api.yaml`

```yaml
apiVersion: 1

datasources:
  - name: Biomass Calc API
    type: yesoreyeram-infinity-datasource
    uid: biomass_calc_api
    access: proxy
    url: http://127.0.0.1:8000
    isDefault: false
    editable: true
    jsonData:
      httpMethod: GET
```

**Important**: Use `127.0.0.1` instead of `localhost` to avoid DNS resolution issues.

### Step 7: Restart Grafana

```powershell
cd "c:\Program Files\GrafanaLabs\grafana"
# Stop any running Grafana processes
Get-Process | Where-Object {$_.ProcessName -like "grafana*"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
# Start Grafana
.\bin\grafana-server.exe
```

Verify Grafana is running at: http://localhost:3000

### Step 8: Copy Dashboard JSON

Save the following as `c:\biomass-api\biomass-dashboard.json` (see full JSON in the repository or use the version provided in this directory).

**Key dashboard components**:

1. **Variables Section** (4 textbox inputs):
   - fuel_price
   - commodity_cost
   - energy_price
   - weather_index

2. **Panel 1**: Stat panel showing "Calculated Output"
   - Displays large numeric result
   - Queries: `/calculate` endpoint

3. **Panel 2**: Table showing "Historical Calculation Results"
   - Displays last 100 calculations
   - Queries: `/results/history` endpoint

4. **Panel 3**: Table showing "Current Input Values"
   - Displays current variable values
   - Queries: `/calculate` endpoint

### Step 9: Import the Dashboard

1. Open http://localhost:3000 with your Grafana admin credentials
2. Navigate to: **Dashboards → New → Import**
3. Click "Upload JSON file"
4. Select: `c:\biomass-api\biomass-dashboard.json`
5. Select datasource: **Biomass Calc API**
6. Click **Import**

---

## Testing & Verification

### Test 1: API Health Check

```powershell
curl http://127.0.0.1:8000/
```

Expected: `{"status": "ok", ...}`

### Test 2: Calculate Endpoint

```powershell
curl "http://127.0.0.1:8000/calculate?fuel_price=3&commodity_cost=10&energy_price=2&weather_index=75"
```

Expected: JSON with `calculated_output` value

### Test 3: Database Persistence

```powershell
# Make multiple calculations
curl "http://127.0.0.1:8000/calculate?fuel_price=1&commodity_cost=5&energy_price=1&weather_index=40"
curl "http://127.0.0.1:8000/calculate?fuel_price=2&commodity_cost=8&energy_price=1.5&weather_index=60"
curl "http://127.0.0.1:8000/calculate?fuel_price=4&commodity_cost=15&energy_price=2.5&weather_index=85"

# Check history
curl http://127.0.0.1:8000/results/history
```

Expected: Array of 3+ calculation records with timestamps

### Test 4: Dashboard Interactivity

1. Open dashboard: http://localhost:3000/d/biomass-optimizer
2. Change `fuel_price` from 2 to 4
3. Press Enter
4. **Expected behavior**:
   - ✅ "Calculated Output" stat updates within 2 seconds
   - ✅ "Current Input Values" table shows new value
   - ✅ "Historical Calculation Results" adds new row at top
5. Verify FastAPI logs show the GET request:
   ```
   INFO: 127.0.0.1:xxxxx - "GET /calculate?fuel_price=4&commodity_cost=... HTTP/1.1" 200 OK
   ```

### Test 5: Different Input Values Produce Different Outputs

```powershell
# Test with low values
curl -s "http://127.0.0.1:8000/calculate?fuel_price=1&commodity_cost=5&energy_price=1&weather_index=40" | ConvertFrom-Json | Select-Object calculated_output

# Test with high values
curl -s "http://127.0.0.1:8000/calculate?fuel_price=4&commodity_cost=15&energy_price=2.5&weather_index=85" | ConvertFrom-Json | Select-Object calculated_output
```

Expected: Two different `calculated_output` values (e.g., 42.02 vs 56.89)

---

## Troubleshooting

### Issue 1: "Connection refused" when accessing API

**Symptoms**: Dashboard shows "No data" or "Connection refused"

**Solutions**:
1. Verify FastAPI is running:
   ```powershell
   Get-Process python
   ```
2. Check if port 8000 is accessible:
   ```powershell
   curl http://127.0.0.1:8000/
   ```
3. Restart FastAPI service:
   ```powershell
   cd c:\biomass-api
   python main.py
   ```

### Issue 2: Dashboard shows "No data"

**Symptoms**: Panels display "No data" despite API working

**Solutions**:
1. **Check datasource configuration**:
   - Grafana → Configuration → Data sources → Biomass Calc API
   - Verify URL is `http://127.0.0.1:8000` (not localhost)
   - Click "Save & test"

2. **Check panel queries**:
   - Edit panel → Query tab
   - Verify `type: json` and `format: table`
   - Verify `parser: backend`
   - Ensure `columns` array has selectors defined

3. **Browser console errors**:
   - Press F12 in browser
   - Check Console tab for errors
   - Look for CORS or network errors

### Issue 3: Calculated output doesn't change

**Symptoms**: All calculations return the same value (e.g., 51.44)

**Cause**: Using `LinearNDInterpolator` which returns NaN for points outside training data convex hull

**Solution**: Switch to `RBFInterpolator` (already done in the code above)

### Issue 4: "Interpolator not initialized"

**Symptoms**: API returns error about missing interpolator

**Solutions**:
1. Verify `sample_data.csv` exists in same directory as `main.py`
2. Check CSV has correct column names:
   ```
   fuel_price,commodity_cost,energy_price,weather_index,output_metric
   ```
3. Add more data rows (minimum 5-10 for good interpolation)
4. Restart FastAPI service

### Issue 5: Infinity plugin not found

**Symptoms**: Datasource type "yesoreyeram-infinity-datasource" not available

**Solutions**:
1. Install plugin:
   ```powershell
   cd "c:\Program Files\GrafanaLabs\grafana"
   .\bin\grafana-cli.exe plugins install yesoreyeram-infinity-datasource
   ```
2. Verify installation:
   ```powershell
   ls "c:\Program Files\GrafanaLabs\grafana\data\plugins\yesoreyeram-infinity-datasource"
   ```
3. Restart Grafana completely

### Issue 6: Dashboard variables don't trigger updates

**Symptoms**: Changing variables doesn't refresh panels

**Solutions**:
1. Check variable `refresh` property is set to `1` (on variable change)
2. Verify panel queries reference variables correctly:
   ```
   ${fuel_price}  (not $fuel_price or {fuel_price})
   ```
3. Set dashboard auto-refresh: Top right → Refresh picker → "10s"

---

## API Reference

### Endpoints

#### GET /
Health check endpoint
```json
Response: {"status": "ok", "service": "Biomass Optimizer API"}
```

#### GET /calculate
Perform calculation and store in database

**Query Parameters**:
- `fuel_price` (float): Fuel price, typically 0-10
- `commodity_cost` (float): Commodity cost, typically 0-20
- `energy_price` (float): Energy price, typically 0-5
- `weather_index` (float): Weather index, typically 0-100

**Example Request**:
```
GET http://127.0.0.1:8000/calculate?fuel_price=2.5&commodity_cost=8&energy_price=1.8&weather_index=70
```

**Example Response**:
```json
{
  "fuel_price": 2.5,
  "commodity_cost": 8.0,
  "energy_price": 1.8,
  "weather_index": 70.0,
  "calculated_output": 51.23
}
```

#### GET /results/latest
Get most recent calculation from database

**Example Response**:
```json
{
  "timestamp": "2026-01-30T13:45:22.123456",
  "fuel_price": 2.5,
  "commodity_cost": 8.0,
  "energy_price": 1.8,
  "weather_index": 70.0,
  "calculated_output": 51.23
}
```

#### GET /results/history
Get last 100 calculations from database

**Example Response**:
```json
[
  {
    "timestamp": "2026-01-30T13:45:22.123456",
    "fuel_price": 2.5,
    "commodity_cost": 8.0,
    "energy_price": 1.8,
    "weather_index": 70.0,
    "calculated_output": 51.23
  },
  ...
]
```

#### GET /results/clear
Clear all calculations (for testing)

**Example Response**:
```json
{"status": "Database cleared"}
```

---

## Extending the System

### Adding More Variables

**1. Update CSV data** - Add new column:
```csv
fuel_price,commodity_cost,energy_price,weather_index,transportation_cost,output_metric
2.0,8.0,1.5,60,10.5,48.3
```

**2. Update `main.py`** - Add parameter to `/calculate`:
```python
@app.get("/calculate")
def calculate(
    fuel_price: float,
    commodity_cost: float,
    energy_price: float,
    weather_index: float,
    transportation_cost: float  # NEW
):
    input_point = np.array([[fuel_price, commodity_cost, energy_price, weather_index, transportation_cost]])
    # ... rest of code
```

**3. Update database schema** - Add column to table:
```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS calculations (
        ...existing columns...,
        transportation_cost REAL NOT NULL
    )
""")
```

**4. Add dashboard variable**:
- Edit dashboard JSON → `templating.list` array
- Add new textbox variable for `transportation_cost`

**5. Update panel queries**:
- Add `&transportation_cost=${transportation_cost}` to URL queries

### Adding Multiple Datasets

To support multiple interpolation models:

**1. Organize CSV files**:
```
c:\biomass-api\datasets\
    model_2024.csv
    model_2025.csv
    scenario_optimistic.csv
    scenario_pessimistic.csv
```

**2. Update backend to select dataset**:
```python
@app.get("/calculate")
def calculate(
    fuel_price: float,
    commodity_cost: float,
    energy_price: float,
    weather_index: float,
    dataset: str = "default"  # NEW: select model
):
    # Load appropriate CSV based on dataset parameter
    df = pd.read_csv(f"datasets/{dataset}.csv")
    # Build interpolator
    # Perform calculation
```

**3. Add dataset selector to dashboard**:
- Add dropdown variable for dataset selection
- Options: model_2024, model_2025, scenario_optimistic, etc.

### Adding Time-Series Visualization

**1. Create new endpoint for time-series data**:
```python
@app.get("/results/timeseries")
def get_timeseries():
    """Get all calculations grouped by hour/day for trending"""
    # Query database with time grouping
    # Return aggregated results
```

**2. Add time-series panel to dashboard**:
- Panel type: "Time series" or "Graph"
- Query: `/results/timeseries` endpoint
- X-axis: timestamp
- Y-axis: calculated_output

### Comparison Panels

Add panels to compare scenarios side-by-side:

**1. Create comparison endpoint**:
```python
@app.get("/compare")
def compare(
    scenario_a: str,
    scenario_b: str,
    fuel_price: float,
    commodity_cost: float,
    energy_price: float,
    weather_index: float
):
    # Calculate with both datasets
    # Return both results for comparison
```

**2. Add comparison table panel**:
- Shows results from multiple scenarios
- Highlights differences
- Calculates percentage changes

---

## File Structure Summary

```
c:\biomass-api\
├── main.py                    # FastAPI backend service
├── requirements.txt           # Python dependencies
├── sample_data.csv           # Training data for interpolation
├── biomass_results.db        # SQLite database (auto-created)
├── biomass-dashboard.json    # Grafana dashboard definition
└── SETUP_GUIDE.md           # This file

c:\Program Files\GrafanaLabs\grafana\
├── conf\provisioning\datasources\
│   └── biomass-api.yaml      # Infinity datasource configuration
└── data\plugins\
    └── yesoreyeram-infinity-datasource\  # Infinity plugin
```

---

## Success Checklist

- [ ] Python 3.8+ installed
- [ ] Grafana 11.x installed and running on port 3000
- [ ] All Python packages installed (`pip install -r requirements.txt`)
- [ ] `sample_data.csv` created with at least 10 rows
- [ ] FastAPI service running on port 8000
- [ ] API health check successful (`curl http://127.0.0.1:8000/`)
- [ ] Infinity plugin installed (`grafana-cli plugins install yesoreyeram-infinity-datasource`)
- [ ] Datasource configured (`biomass-api.yaml` created)
- [ ] Grafana restarted after plugin installation
- [ ] Dashboard imported successfully
- [ ] Variables visible at top of dashboard
- [ ] Changing variables triggers API calls (check FastAPI logs)
- [ ] Calculated output updates with different input values
- [ ] Historical results table shows multiple rows
- [ ] Database file created (`biomass_results.db` exists)

---

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SciPy Interpolation Guide**: https://docs.scipy.org/doc/scipy/tutorial/interpolate.html
- **Grafana Infinity Plugin**: https://grafana.com/grafana/plugins/yesoreyeram-infinity-datasource/
- **SQLite Documentation**: https://www.sqlite.org/docs.html

---

## Support & Troubleshooting

If you encounter issues not covered in this guide:

1. **Check FastAPI logs** - Look for error messages in the terminal running `python main.py`
2. **Check Grafana logs** - Located at `c:\Program Files\GrafanaLabs\grafana\data\log\grafana.log`
3. **Browser console** - Press F12 and check for JavaScript errors
4. **Test API directly** - Use `curl` or Postman to verify API responses
5. **Verify file permissions** - Ensure Python can write to `biomass_results.db`

---

**Last Updated**: January 30, 2026  
**Version**: 1.0  
**Author**: Biomass Optimization Team
