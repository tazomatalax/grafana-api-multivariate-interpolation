# Biomass Processing Optimizer - Interactive Dashboard

Real-time biomass processing facility optimization dashboard with multivariate interpolation, database persistence, and historical tracking.

![System Architecture](https://img.shields.io/badge/Stack-FastAPI%20%2B%20Grafana%20%2B%20SQLite-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success)

---

## Features

- 🎯 **Real-time Calculations** - Multivariate interpolation using SciPy RBF
- 💾 **Database Persistence** - Every calculation stored with timestamp in SQLite
- 📊 **Interactive Dashboard** - Grafana-based UI with live variable inputs
- 📈 **Historical Tracking** - View and analyze last 100 calculations
- 🔌 **REST API** - Clean FastAPI endpoints for integration
- 🚀 **Easy Extension** - Add variables, datasets, or models with minimal code

---

## Quick Start

### Prerequisites
- Python 3.8+
- Grafana 11.x
- Windows OS (or adapt paths for Linux/Mac)

### Installation

```powershell
# 1. Install Python dependencies
cd c:\biomass-api
pip install -r requirements.txt

# 2. Start the API service
python main.py

# 3. Install Grafana Infinity plugin
cd "c:\Program Files\GrafanaLabs\grafana"
.\bin\grafana-cli.exe plugins install yesoreyeram-infinity-datasource

# 4. Start Grafana
.\bin\grafana-server.exe

# 5. Import dashboard
# Open http://localhost:3000
# Dashboards → Import → Upload biomass-dashboard.json
```

**📚 Detailed setup instructions**: [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## Usage

### Access the Dashboard

**URL**: http://localhost:3000/d/biomass-optimizer  
**Credentials**: Use your Grafana admin credentials (default: admin/admin)

### Adjust Variables

At the top of the dashboard, enter values for:
- **Fuel Price** (0-10)
- **Commodity Cost** (0-20)
- **Energy Price** (0-5)
- **Weather Index** (0-100)

Press Enter after changing any value to trigger calculation.

### View Results

- **Calculated Output** - Large stat panel showing interpolated result
- **Current Input Values** - Table confirming your inputs
- **Historical Results** - Table of last 100 calculations with timestamps

---

## Architecture

```
┌─────────────────────────────────────────┐
│   Grafana Dashboard (localhost:3000)    │
│   - 4 textbox variables                 │
│   - 3 result panels                     │
└────────────────┬────────────────────────┘
                 │ HTTP GET (Infinity Plugin)
                 ↓
┌─────────────────────────────────────────┐
│   FastAPI Backend (localhost:8000)      │
│   - /calculate endpoint                 │
│   - /results/latest                     │
│   - /results/history                    │
│   - SciPy RBFInterpolator               │
└────────────────┬────────────────────────┘
                 │ SQLite write
                 ↓
┌─────────────────────────────────────────┐
│   SQLite Database                       │
│   (biomass_results.db)                  │
│   - calculations table                  │
│   - timestamp, inputs, outputs          │
└─────────────────────────────────────────┘
```

---

## API Endpoints

### Calculate
```http
GET /calculate?fuel_price=2&commodity_cost=8&energy_price=1.5&weather_index=60
```

**Response**:
```json
{
  "fuel_price": 2.0,
  "commodity_cost": 8.0,
  "energy_price": 1.5,
  "weather_index": 60.0,
  "calculated_output": 49.23
}
```

### Latest Result
```http
GET /results/latest
```

Returns most recent calculation with timestamp.

### History
```http
GET /results/history
```

Returns array of last 100 calculations.

**Full API documentation**: See [SETUP_GUIDE.md](SETUP_GUIDE.md#api-reference)

---

## Project Structure

```
c:\biomass-api\
├── main.py                    # FastAPI backend service
├── requirements.txt           # Python dependencies
├── sample_data.csv           # Training data for interpolation
├── biomass_results.db        # SQLite database (auto-created)
├── biomass-dashboard.json    # Grafana dashboard definition
├── README.md                 # This file
├── SETUP_GUIDE.md           # Complete installation guide
└── IMPLEMENTATION_SUMMARY.md # Technical overview
```

---

## Technology Stack

- **Backend**: FastAPI 0.104.1 + Uvicorn
- **Interpolation**: SciPy 1.11.4 (RBFInterpolator)
- **Database**: SQLite 3
- **Data Processing**: Pandas 2.1.3 + NumPy 1.26.2
- **Frontend**: Grafana 11.2.2
- **Datasource**: Infinity Plugin v3.7.0

---

## Key Implementation Details

### Why RBFInterpolator?

Initially used `LinearNDInterpolator`, but it only works within the convex hull of training data. Points outside return NaN, causing all extrapolated values to fall back to the mean.

**Solution**: `RBFInterpolator` with thin plate spline kernel can extrapolate beyond training data, producing varied results across the full input space.

### Why 127.0.0.1 instead of localhost?

Grafana's server-side plugin context sometimes has DNS resolution issues with "localhost". Using `127.0.0.1` directly ensures reliable connectivity.

### Why format: "table"?

The Infinity datasource requires `format: "table"` for array responses to properly parse JSON into rows. Using `format: "json"` caused panels to display "No data" despite successful API calls.

---

## Extending the System

### Add More Variables

**Example**: Add `transportation_cost`

1. **Update CSV**:
   ```csv
   fuel_price,commodity_cost,energy_price,weather_index,transportation_cost,output_metric
   2.0,8.0,1.5,60,10.5,48.3
   ```

2. **Update main.py**:
   ```python
   @app.get("/calculate")
   def calculate(..., transportation_cost: float):
       input_point = np.array([[fuel_price, ..., transportation_cost]])
   ```

3. **Add dashboard variable** in `biomass-dashboard.json`

4. **Update panel queries** to include new parameter

### Multiple Datasets

Support different models/scenarios:

```python
@app.get("/calculate")
def calculate(..., dataset: str = "default"):
    df = pd.read_csv(f"datasets/{dataset}.csv")
    # Build interpolator and calculate
```

Add dropdown variable in dashboard to select dataset.

---

## Testing

### Verify API
```powershell
curl http://127.0.0.1:8000/
```

### Test Calculation
```powershell
curl "http://127.0.0.1:8000/calculate?fuel_price=2&commodity_cost=8&energy_price=1.5&weather_index=60"
```

### Check Database
```powershell
curl http://127.0.0.1:8000/results/history
```

### Test Interpolation
```powershell
# Low values → low output
curl "http://127.0.0.1:8000/calculate?fuel_price=1&commodity_cost=5&energy_price=1&weather_index=40"

# High values → high output
curl "http://127.0.0.1:8000/calculate?fuel_price=4&commodity_cost=15&energy_price=2.5&weather_index=85"
```

Outputs should be different (e.g., ~42 vs ~57), proving interpolation works.

---

## Troubleshooting

### Dashboard shows "No data"
- ✅ Verify API is running: `curl http://127.0.0.1:8000/`
- ✅ Check datasource URL uses `127.0.0.1` (not localhost)
- ✅ Ensure panel queries have `format: "table"` and `parser: "backend"`

### All calculations return same value
- ✅ Verify using `RBFInterpolator` (not LinearND)
- ✅ Check `sample_data.csv` has varied data points
- ✅ Restart FastAPI service

### Variables don't trigger updates
- ✅ Set variable `refresh: 1` in dashboard JSON
- ✅ Enable dashboard auto-refresh (10s)

**More troubleshooting**: [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting)

---

## Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete installation and configuration guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical overview and architecture details

---

## Requirements Met

| Requirement | Implementation |
|-------------|----------------|
| User numerical input | ✅ Continuous textbox variables (no discrete limits) |
| Send to backend | ✅ Infinity datasource → FastAPI REST API |
| Backend processing | ✅ SciPy RBFInterpolator (CPU-intensive) |
| Database persistence | ✅ SQLite with auto-write on every calculation |
| Display in panels | ✅ 3 panels: stat, current inputs, historical table |
| Multiple variables | ✅ 4 variables (easily extensible to N variables) |
| Historical results | ✅ Last 100 calculations with timestamps |

---

## License

This project is provided as-is for internal use in biomass processing optimization.

---

## Support

For issues or questions:
1. Check [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting)
2. Review FastAPI logs: Terminal running `python main.py`
3. Check Grafana logs: `c:\Program Files\GrafanaLabs\grafana\data\log\grafana.log`
4. Verify API directly with `curl` commands

---

**Last Updated**: January 30, 2026  
**Version**: 1.0  
**Status**: Production Ready ✅
