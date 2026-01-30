# Biomass Processing Dashboard - Implementation Summary

> **For complete setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

## Quick Overview

This project implements an interactive Grafana dashboard for biomass processing optimization with:

✅ **Real-time calculations** - Multivariate interpolation using SciPy  
✅ **Database persistence** - Every calculation stored in SQLite with timestamps  
✅ **Historical tracking** - View last 100 calculations in sortable table  
✅ **REST API backend** - FastAPI service with multiple endpoints  
✅ **Interactive variables** - Continuous textbox inputs (not discrete sliders)  

---

## System Architecture

```
Grafana Dashboard (localhost:3000)
    ↓ Variables: fuel_price, commodity_cost, energy_price, weather_index
    ↓ Infinity Datasource Plugin (HTTP GET)
    ↓
FastAPI Backend (localhost:8000)
    ├─ /calculate - Interpolates & stores in database
    ├─ /results/latest - Most recent calculation
    └─ /results/history - Last 100 calculations
    ↓
SQLite Database (biomass_results.db)
```

---

## What's Running

### 1. FastAPI Service (Port 8000)
**File**: `c:\biomass-api\main.py`

**Endpoints**:
- `GET /` - Health check
- `GET /calculate?fuel_price=X&commodity_cost=Y&energy_price=Z&weather_index=W` - Calculate & store
- `GET /results/latest` - Most recent result
- `GET /results/history` - Historical results (last 100)
- `GET /results/clear` - Clear database (testing only)

**Start command**:
```powershell
cd c:\biomass-api
python main.py
```

### 2. Grafana Server (Port 3000)
**Dashboard URL**: http://localhost:3000/d/biomass-optimizer

**Credentials**: Use your Grafana admin credentials

**Start command**:
```powershell
cd "c:\Program Files\GrafanaLabs\grafana"
.\bin\grafana-server.exe
```

---

## Dashboard Panels

### Panel 1: Calculated Output (Stat Panel)
- Shows large numeric result from interpolation
- Updates when variables change
- Queries: `/calculate` endpoint with all 4 variables

### Panel 2: Historical Calculation Results (Table)
- Displays last 100 calculations with timestamps
- Sorted by most recent first
- Columns: Timestamp, Fuel Price, Commodity Cost, Energy Price, Weather Index, Calculated Output
- Queries: `/results/history` endpoint

### Panel 3: Current Input Values (Table)
- Shows current variable values being used
- Confirms inputs are being sent correctly
- Queries: `/calculate` endpoint (same as Panel 1)

### Variables (Top of Dashboard)
- **fuel_price**: Textbox, typically 0-10
- **commodity_cost**: Textbox, typically 0-20  
- **energy_price**: Textbox, typically 0-5
- **weather_index**: Textbox, typically 0-100

All variables trigger panel refresh on change (`refresh: 1`)

---

## Key Technical Details

### Interpolation Method
**RBFInterpolator** (SciPy) with thin plate spline kernel
- Can extrapolate beyond training data range
- Handles 4-dimensional input space
- Smooth continuous output

**Why RBF instead of LinearND?**
- `LinearNDInterpolator` only works within convex hull of training data
- Points outside return NaN → falls back to mean value
- `RBFInterpolator` can extrapolate, giving varied results for all inputs

### Database Schema
```sql
CREATE TABLE calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    fuel_price REAL NOT NULL,
    commodity_cost REAL NOT NULL,
    energy_price REAL NOT NULL,
    weather_index REAL NOT NULL,
    calculated_output REAL NOT NULL
);
```

### Datasource Configuration
**Type**: Infinity Plugin (yesoreyeram-infinity-datasource v3.7.0)  
**UID**: `biomass_calc_api`  
**URL**: `http://127.0.0.1:8000` (must use 127.0.0.1, not localhost)  
**Config file**: `c:\Program Files\GrafanaLabs\grafana\conf\provisioning\datasources\biomass-api.yaml`

### Panel Query Configuration
All panels use:
- `type: json`
- `format: table`
- `parser: backend`
- `source: url`
- Explicit `columns` array with selectors for each field

**Example**:
```json
{
  "type": "json",
  "format": "table",
  "parser": "backend",
  "url": "http://127.0.0.1:8000/calculate?fuel_price=${fuel_price}&...",
  "columns": [
    {"selector": "fuel_price", "text": "Fuel Price", "type": "number"},
    {"selector": "calculated_output", "text": "Calculated Output", "type": "number"}
  ]
}
```

---

## Testing the System

### 1. Verify API is running
```powershell
curl http://127.0.0.1:8000/
```
Expected: `{"status": "ok", ...}`

### 2. Test calculation with different values
```powershell
# Low values
curl "http://127.0.0.1:8000/calculate?fuel_price=1&commodity_cost=5&energy_price=1&weather_index=40"
# Expected output: ~42.02

# High values  
curl "http://127.0.0.1:8000/calculate?fuel_price=4&commodity_cost=15&energy_price=2.5&weather_index=85"
# Expected output: ~56.89
```

Values should be **different**, proving interpolation is working.

### 3. Check database has records
```powershell
curl http://127.0.0.1:8000/results/history
```
Expected: Array of calculation records with timestamps

### 4. Test dashboard interactivity
1. Open http://localhost:3000/d/biomass-optimizer
2. Change `fuel_price` from 2 to 4
3. Press Enter
4. **Verify**:
   - Calculated Output updates (should change from ~50 to ~57)
   - Historical table adds new row at top
   - FastAPI logs show GET request with new parameters

---

## File Locations

| Component | Path |
|-----------|------|
| FastAPI Service | `c:\biomass-api\main.py` |
| Training Data | `c:\biomass-api\sample_data.csv` |
| Database | `c:\biomass-api\biomass_results.db` |
| Dashboard JSON | `c:\biomass-api\biomass-dashboard.json` |
| Requirements | `c:\biomass-api\requirements.txt` |
| Datasource Config | `c:\Program Files\GrafanaLabs\grafana\conf\provisioning\datasources\biomass-api.yaml` |
| Infinity Plugin | `c:\Program Files\GrafanaLabs\grafana\data\plugins\yesoreyeram-infinity-datasource\` |

---

## Common Issues & Solutions

### Issue: Dashboard shows "No data"
**Solution**: 
1. Verify datasource URL is `http://127.0.0.1:8000` (not localhost)
2. Check panel query has `format: table` and `type: json`
3. Ensure `columns` array is defined with selectors

### Issue: All calculations return same value (e.g., 51.44)
**Solution**: Using `RBFInterpolator` instead of `LinearNDInterpolator` (already fixed in current code)

### Issue: Variables don't trigger updates
**Solution**: Set variable `refresh: 1` and dashboard auto-refresh to 10s

### Issue: "Datasource not found"
**Solution**: 
1. Install Infinity plugin: `grafana-cli plugins install yesoreyeram-infinity-datasource`
2. Restart Grafana completely
3. Verify datasource UID matches in both datasource config and dashboard JSON

---

## Extending the System

### Add More Variables
1. Add column to `sample_data.csv`
2. Update interpolator input array in `main.py`
3. Add parameter to `/calculate` endpoint
4. Add variable to dashboard JSON
5. Update panel queries with new variable

### Add Multiple Datasets
```python
@app.get("/calculate")
def calculate(..., dataset: str = "default"):
    df = pd.read_csv(f"datasets/{dataset}.csv")
    # Rest of interpolation logic
```

### Add Time-Series Panel
- Create `/results/timeseries` endpoint with grouped data
- Add "Time series" panel type to dashboard
- Show trending over time

---

## Requirements Met

| Original Requirement | Status |
|---------------------|--------|
| User provides numerical input | ✅ Textbox variables (continuous) |
| Send to backend | ✅ Infinity datasource → FastAPI |
| Backend processes input | ✅ SciPy RBFInterpolator |
| Results written to database | ✅ SQLite with auto-persist |
| Display results in panel | ✅ 3 panels (stat + 2 tables) |
| Multiple variables | ✅ 4 variables (easily extensible) |
| Historical results | ✅ Last 100 calculations displayed |

---

## Quick Start Commands

```powershell
# Terminal 1: Start FastAPI
cd c:\biomass-api
python main.py

# Terminal 2: Start Grafana
cd "c:\Program Files\GrafanaLabs\grafana"
.\bin\grafana-server.exe

# Browser: Open dashboard
http://localhost:3000/d/biomass-optimizer

# Test API directly
curl "http://127.0.0.1:8000/calculate?fuel_price=2&commodity_cost=8&energy_price=1.5&weather_index=60"
```

---

**For complete setup instructions from scratch, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

**Last Updated**: January 30, 2026


### ✅ Original Request vs Implementation

| Requirement | Original Plan | Updated Status |
|-------------|---------------|---|
| User provides numerical input | Slider variables | ✅ **Continuous text input variables** (no discrete limits) |
| Send to backend | API endpoints | ✅ FastAPI service |
| Backend processes input | Multivariate interpolation | ✅ CPU-intensive work (test case: multiply by 2, production: SciPy) |
| Results written to database | Not included | ✅ **SQLite database with persistent storage** |
| Display results in panel | JSON response only | ✅ **Dashboard displays both current AND historical results** |
| Multiple variables support | 4 variables included | ✅ Confirmed - easy to add more |
| Backend writes to DB | Not included | ✅ **Implemented - results auto-persist on every calculation** |

---

## Current Architecture

```
User Dashboard (Grafana)
    ↓
    Variable inputs (fuel_price, commodity_cost, energy_price, weather_index)
    ↓
    Infinity Datasource (HTTP GET)
    ↓
FastAPI Backend Service (localhost:8000)
    ├─ /calculate endpoint
    │   ├─ Accepts 4 query parameters
    │   ├─ Performs interpolation on CSV data
    │   └─ **Writes result to SQLite database** ← NEW
    │
    ├─ /results/latest (query latest DB result)
    └─ /results/history (query last 100 DB results)
    ↓
SQLite Database (biomass_results.db)
    └─ calculations table with timestamps
```

---

## What's Running Right Now

### 1. **FastAPI Service** (Port 8000)
   - Location: `c:\biomass-api\main.py`
   - Status: ✅ Running
   - Database: ✅ SQLite (`c:\biomass-api\biomass_results.db`)
   - Features:
     - `/calculate` - Accepts 4 GET parameters, interpolates, writes to DB
     - `/results/latest` - Returns most recent calculation from database
     - `/results/history` - Returns last 100 calculations from database
   - Test: `curl "http://localhost:8000/calculate?fuel_price=2.0&commodity_cost=5.0&energy_price=1.0&weather_index=50"`

### 2. **Infinity Plugin** 
   - Status: ✅ Installed (v3.7.0)
   - Datasource: ✅ Provisioned as "Biomass Calc API"

### 3. **Grafana Server** (Port 3000)
   - Status: ✅ Running and healthy
   - Ready to import dashboard

---

## Dashboard Setup

### How to Import the Dashboard

1. **Open Grafana**: http://localhost:3000 (default: admin/admin)
2. **Import Dashboard**:
   - Dashboards → New → Import
   - Upload: `c:\biomass-api\biomass-dashboard.json`
   - Select datasource: "Biomass Calc API"
   - Click Import

### Dashboard Panels

#### Panel 1: Input Variable Controls (Top)
- **fuel_price**: Continuous text input (0-10)
- **commodity_cost**: Continuous text input (0-20)
- **energy_price**: Continuous text input (0-5)
- **weather_index**: Continuous text input (0-100)

#### Panel 2: Current Input Values (Bottom Left)
- Shows the exact values currently being used
- Displays as a table

#### Panel 3: Calculated Output (Top Right)
- **Large stat display** showing latest calculated result
- Real-time value from the API response
- Color-coded background

#### Panel 4: Historical Results (Bottom Right)
- **Table of last 100 calculations**
- Shows: timestamp, all inputs, calculated_output
- Sorted by most recent first
- Demonstrates data persistence in the database

---

## Workflow Example

1. **User enters values**:
   - fuel_price = 2.5
   - commodity_cost = 7.2
   - energy_price = 1.8
   - weather_index = 73

2. **User presses Enter or panel auto-refreshes** → Grafana sends GET request to FastAPI

3. **FastAPI backend**:
   - Receives: `GET /calculate?fuel_price=2.5&commodity_cost=7.2&energy_price=1.8&weather_index=73`
   - Performs: SciPy LinearNDInterpolator on CSV data
   - Result: `calculated_output = 52.18`
   - **Writes to database**: Stores all inputs + output + timestamp
   - Returns JSON response

4. **Dashboard immediately displays**:
   - Stat panel: **52.18**
   - Table panel: New row added at the top with this calculation

5. **History preserved**: User can scroll through previous calculations in the historical results table

---

## Next Steps: Scaling to Your End Goal

### Current State (Test Case)
- ✅ Multivariate interpolation working
- ✅ Multiple variables supported
- ✅ Database persistence working
- ✅ Real-time dashboard updates

### Production Goal
When you have multiple datasets and want to interpolate between them:

**Backend Changes**:
1. Load multiple CSV files (different models/time periods)
2. Modify `/calculate` to:
   - Accept additional parameter: `dataset_id` or `model_version`
   - Select appropriate dataset
   - Perform interpolation
   - Write results to database with metadata

**Dashboard Changes**:
1. Add dropdown variable for "Dataset/Model" selection
2. Add time-series panel to show calculated metrics over time
3. Add comparison panels for before/after scenario analysis

**Example**:
```python
@app.get("/calculate")
def calculate(
    fuel_price: float,
    commodity_cost: float,
    energy_price: float,
    weather_index: float,
    dataset_id: str = "default"  # NEW: select which model to use
):
    # Load correct dataset
    # Perform interpolation
    # Write to database with dataset_id metadata
    # Return results
```

---

## File Locations

| Component | Path |
|-----------|------|
| FastAPI Service | `c:\biomass-api\main.py` |
| Sample CSV Data | `c:\biomass-api\sample_data.csv` |
| SQLite Database | `c:\biomass-api\biomass_results.db` |
| Dashboard JSON | `c:\biomass-api\biomass-dashboard.json` |
| Datasource Config | `c:\Program Files\GrafanaLabs\grafana\conf\provisioning\datasources\biomass-api.yaml` |
| Infinity Plugin | `c:\Program Files\GrafanaLabs\grafana\data\plugins\yesoreyeram-infinity-datasource\` |

---

## API Reference

### Calculate Endpoint
```
GET http://localhost:8000/calculate
Query Parameters:
  - fuel_price (float): Price of fuel
  - commodity_cost (float): Cost of commodity
  - energy_price (float): Price of energy
  - weather_index (float): Weather index (0-100)

Response:
{
  "fuel_price": 2.1,
  "commodity_cost": 5.3,
  "energy_price": 1.2,
  "weather_index": 68.0,
  "calculated_output": 51.44
}
```

### Latest Results Endpoint
```
GET http://localhost:8000/results/latest

Response:
{
  "timestamp": "2026-01-30T12:30:50.213597",
  "fuel_price": 2.1,
  "commodity_cost": 5.3,
  "energy_price": 1.2,
  "weather_index": 68.0,
  "calculated_output": 51.44
}
```

### History Endpoint
```
GET http://localhost:8000/results/history

Response: Array of up to 100 calculation records with timestamps
```

---

## Testing Checklist

- [ ] Grafana is running (http://localhost:3000)
- [ ] FastAPI service is running (http://localhost:8000)
- [ ] Database file exists (`c:\biomass-api\biomass_results.db`)
- [ ] Infinity datasource is configured and working
- [ ] Dashboard imported successfully
- [ ] Can change any variable and see result update within 2 seconds
- [ ] Historical results table shows new rows as you perform calculations
- [ ] Timestamp shows when each calculation was performed

---

## Key Changes Made

1. ✅ **Database Integration**: Added SQLite with persistent storage
2. ✅ **Results Endpoints**: Added `/results/latest` and `/results/history` for querying stored calculations
3. ✅ **Dashboard Updates**: Added panels for:
   - Current input values display
   - Latest calculated output (stat panel)
   - Historical results (table with all past calculations)
4. ✅ **Continuous Input**: Using text-box variables instead of sliders for truly continuous input values
5. ✅ **Grafana Restarted**: Infinity plugin loaded and ready

This implementation now fully satisfies your original requirements while providing a clean path to scale to multiple datasets and models.
