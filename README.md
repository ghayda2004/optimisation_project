# 🚚 V2V Logistics Central Agent

## 📌 Project Overview

**V2V Logistics Central Agent** is a comprehensive logistics optimization platform designed to solve the Vehicle Routing Problem (VRP) with real-time profitability analysis. The system combines data preparation, intelligent route optimization using Google OR-Tools, financial analysis, and a FastAPI backend to deliver actionable insights for fleet managers and drivers.

### Core Features

- **Intelligent Route Optimization**: Uses Google OR-Tools to compute optimal routes considering distance, capacity, and time constraints
- **Real-time Profitability Analysis**: Calculates net profit per route accounting for fuel, labor, and handling costs
- **Dynamic Order Allocation**: Assign new orders at runtime with marginal cost analysis and admin approval workflow
- **Data Pipeline**: ETL workflows to import orders/drivers, geocode addresses, and manage data quality
- **RESTful APIs**: Admin and Driver interfaces for route management, performance tracking, and real-time order assignment
- **Visual Route Planning**: Generates interactive HTML maps with Leaflet.js for each driver's route
- **PostgreSQL Backend**: Persistent storage for orders, drivers, routes, and profitability metrics

---

## 📁 Project Structure

```
V-2-V--logistics-central-agent/
│
├── .env                              # Environment variables (DB, API keys, paths, costs)
├── run.py                            # Root launcher for FastAPI backend
├── POSTGRESQL_SETUP.md               # PostgreSQL setup guide
│
└── central_agent/
    ├── package.json                  # Node dependencies (legacy/minimal)
    ├── requirements.txt              # Python dependencies
    │
    ├── backend_agent/                # Core backend application
    │   │
    │   ├── app/
    │   │   │
    │   │   ├── main.py               # FastAPI application entry point
    │   │   │
    │   │   ├── api/                  # API route handlers
    │   │   │   ├── admin_api.py      # Admin dashboard endpoints (KPIs, routes summary)
    │   │   │   └── driver_api.py     # Driver app endpoints (current route, stats)
    │   │   │
    │   │   ├── core/                 # Configuration & database setup
    │   │   │   ├── config.py         # Environment variables loader
    │   │   │   ├── database.py       # SQLAlchemy engine & session factory
    │   │   │   └── data/             # Sample data for testing
    │   │   │       ├── drivers.csv   # Mock driver list
    │   │   │       ├── fixed_database_large.csv  # Orders dataset
    │   │   │       └── sim_results.json          # Simulation results
    │   │   │
    │   │   ├── models/               # SQLAlchemy ORM models
    │   │   │   ├── __init__.py
    │   │   │   └── models.py         # Database schema (Order, Driver, Route, etc.)
    │   │   │
    │   │   └── services/             # Business logic & algorithms
    │   │       ├── __init__.py
    │   │       ├── data_reader.py    # CSV parsing & data loading
    │   │       ├── routing.py        # OR-Tools optimization engine
    │   │       ├── profitability.py  # Financial analysis & profit calculation
    │   │       ├── database_handler.py # Database operations (UPSERT routes, profitability)
    │   │       └── map_generator.py  # HTML map generation with Leaflet.js
    │   │
    │   ├── frontend/                 # Frontend files (HTML dashboards)
    │   │   └── add/
    │   │       ├── admin/            # Admin dashboard UI
    │   │       │   └── index.html    # Admin dashboard page
    │   │       └── driver/           # Driver mobile interface
    │   │           └── index.html    # Driver app page
    │   │
    │   ├── outputs/                  # Generated outputs
    │   │   ├── map_*.html            # Generated route maps per driver
    │   │   ├── optimization_report.tex
    │   │   └── google_maps_*.html
    │   │
    │   ├── API_DOC.md                # API endpoint documentation
    │   └── node_modules/             # Node dependencies (legacy)
    │
    └── scripts/                      # Data pipeline & utilities
        ├── init_database.py          # Initialize PostgreSQL tables
        ├── pipeline.py               # Main ETL: optimize routes → save to DB → generate maps
        ├── import_csv_to_db.py       # Import orders/drivers from CSV to PostgreSQL
        ├── data_preparation.py       # Geocoding & data cleaning
        ├── simulate_scenarios.py     # Scenario simulation tools
        └── test_routing.py           # Routing validation tests

```

---

## 🧠 Database Schema

### Tables Overview

The PostgreSQL database contains 5 core tables that work together to track the complete logistics lifecycle:

#### 1. **orders** table
Stores customer delivery orders with their details and status.

```sql
CREATE TABLE orders (
    id INT PRIMARY KEY,
    reference VARCHAR(100),
    expediteur VARCHAR(200),              -- Customer name
    adresse_destinataire VARCHAR(500),    -- Delivery address
    lat FLOAT NOT NULL,                   -- Latitude
    lng FLOAT NOT NULL,                   -- Longitude
    delivery_value FLOAT DEFAULT 0.0,     -- Revenue from this order
    frais_livraison FLOAT DEFAULT 0.0,    -- Delivery fee
    poids FLOAT,                          -- Weight in kg
    gouvernorat VARCHAR(100),             -- Region
    status_internal VARCHAR(50) DEFAULT 'pending',  -- pending, assigned, completed
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. **drivers** table
Contains driver information, capacity, and current location.

```sql
CREATE TABLE drivers (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    vehicle_capacity FLOAT DEFAULT 500.0, -- kg
    current_lat FLOAT,
    current_lng FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3. **routes** table
Represents planned delivery routes assigned to drivers.

```sql
CREATE TABLE routes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    driver_id INT FOREIGN KEY → drivers.id,
    total_distance_km FLOAT DEFAULT 0.0,
    total_duration_min FLOAT DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'planned',    -- planned, in_progress, completed
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 4. **route_stops** table
Defines the sequence of delivery stops within each route.

```sql
CREATE TABLE route_stops (
    id INT PRIMARY KEY AUTO_INCREMENT,
    route_id INT FOREIGN KEY → routes.id,
    order_id INT FOREIGN KEY → orders.id,
    stop_sequence INT NOT NULL,            -- Order within the route (1, 2, 3, ...)
    arrived_at TIMESTAMP
);
```

#### 5. **route_profitability** table
Financial summary for each route including revenue, costs, and net profit.

```sql
CREATE TABLE route_profitability (
    id INT PRIMARY KEY AUTO_INCREMENT,
    route_id INT FOREIGN KEY → routes.id,
    total_revenue FLOAT DEFAULT 0.0,        -- Sum of delivery values
    total_cost FLOAT DEFAULT 0.0,           -- Fuel + labor + handling
    gain_net FLOAT DEFAULT 0.0,             -- Revenue - Cost
    margin_pct FLOAT DEFAULT 0.0,           -- (Profit / Revenue) * 100
    calculated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🛠 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend Framework** | FastAPI | RESTful API endpoints |
| **ORM & Database** | SQLAlchemy + PostgreSQL | Data persistence & relationships |
| **Route Optimization** | Google OR-Tools | VRP solver with Haversine distance |
| **Data Processing** | Pandas | CSV parsing & data cleaning |
| **Mapping & Visualization** | Leaflet.js + OSRM | Interactive route maps |
| **Frontend** | HTML5 + CSS | Admin & Driver dashboards |
| **Environment Management** | Python-dotenv | Configuration via .env |
| **Server** | Uvicorn | ASGI server for FastAPI |

---

## 🚀 Installation & Setup

### Prerequisites

- **Python 3.8+**
- **PostgreSQL 12+**
- **.env file** configured (see below)
- Windows PowerShell or Linux/macOS terminal

### Step 1: Clone and Navigate

```bash
cd V-2-V--logistics-central-agent
```

### Step 2: Create Python Virtual Environment

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r central_agent\requirements.txt
```

**Key packages installed:**
- `fastapi` & `uvicorn` — Web framework
- `sqlalchemy` & `psycopg2-binary` — Database ORM & PostgreSQL driver
- `pandas` — Data processing
- `ortools` — Route optimization
- `python-dotenv` — Environment management

### Step 4: Configure PostgreSQL & .env

#### Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the logistics database
CREATE DATABASE logistics_db;

# Exit
\q
```

#### Create `.env` file at repository root

```env
# PostgreSQL Connection
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/logistics_db

# Python Path
PYTHONPATH=./central_agent/backend_agent

# Data Source Paths (relative to central_agent/backend_agent)
CSV_ORDERS_PATH=data/fixed_database_large.csv
CSV_DRIVERS_PATH=data/drivers.csv

# Financial Parameters (for profitability calculations)
FUEL_RATE=0.356                 # TND per km
HOURLY_RATE=5.0                 # TND per hour (driver wage)
HANDLING_COST=0.0               # TND per stop

# Optional API Keys
ORS_API_KEY=your_api_key_here   # OpenRouteService (optional)
TELEGRAM_BOT_TOKEN=your_token   # Telegram bot (optional)
```

### Step 5: Initialize Database Tables

```powershell
python central_agent\scripts\init_database.py
```

This creates the following tables:
- `orders`
- `drivers`
- `routes`
- `route_stops`
- `route_profitability`

### Step 6: Import Data (Optional)

To load sample orders and drivers into the database:

```powershell
cd central_agent
python scripts\import_csv_to_db.py
cd ..
```

### Step 7: Start the FastAPI Backend

From the repository root:

```powershell
python run.py
```

**OR directly with uvicorn:**

```powershell
cd central_agent
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 8: Access the Application

Open your browser:

- **API Home**: `http://127.0.0.1:8000/`
- **API Documentation (Swagger UI)**: `http://127.0.0.1:8000/docs`
- **Alternative API Docs (ReDoc)**: `http://127.0.0.1:8000/redoc`

---

## 📡 API Endpoints Reference

### Admin Dashboard API (`/api/admin`)

#### 1. Get Summary KPIs
```
GET /api/admin/summary
```

**Response Example:**
```json
{
  "active_drivers": 5,
  "total_routes": 12,
  "total_colis": 245,
  "gain_total": 1250.50,
  "marge_moyenne": 18.5
}
```

**Description:**
- Returns real-time KPI aggregates across all routes
- `gain_total`: Sum of net profit from all routes
- `marge_moyenne`: Average profit margin percentage

---

#### 2. Get All Routes with Details
```
GET /api/admin/routes
```

**Response Example:**
```json
[
  {
    "route_id": 1,
    "driver_name": "Livreur Ahmad",
    "nb_colis": 15,
    "distance": 45.2,
    "gain_net": 85.30,
    "margin_pct": 22.1,
    "status": "planned",
    "map_url": "outputs/map_driver_1.html"
  }
]
```

**Description:**
- Lists all routes with profitability metrics
- `map_url`: Link to the generated Leaflet map
- Useful for fleet-wide monitoring

---

### Admin Dynamic Order Allocation API (`/api/admin`)

#### 3. Propose New Order (Get Suitable Drivers)
```
POST /api/admin/propose-order
```

**Query Parameters:**
- `reference`: Order reference code (string)
- `customer_name`: Customer name (string)
- `address`: Delivery address (string)
- `lat`: Latitude (float)
- `lng`: Longitude (float)
- `delivery_value`: Delivery payment value (float, in TND)

**Response Example:**
```json
{
  "order": {
    "reference": "CMD-2024-0101",
    "customer": "Sophia Store",
    "address": "Rue de la Paix 123, Tunis",
    "lat": 36.8065,
    "lng": 10.1957,
    "value": 8.00
  },
  "feasible_drivers": [
    {
      "driver_id": 1,
      "driver_name": "Livreur Ahmad",
      "is_feasible": true,
      "marginal_profit": 4.85,
      "distance_added_km": 12.5,
      "marginal_cost": 3.15,
      "fuel_cost": 4.44,
      "labor_cost": 1.04,
      "handling_cost": 0.0,
      "best_position": 3,
      "current_distance_km": 42.0,
      "new_distance_km": 54.5,
      "current_stops": 8,
      "new_stops": 9
    }
  ],
  "infeasible_drivers": [
    {
      "driver_id": 2,
      "driver_name": "Livreur Karim",
      "is_feasible": false,
      "distance_added_km": 18.5
    }
  ],
  "best_driver_id": 1,
  "best_driver_name": "Livreur Ahmad",
  "status": "ready_for_confirmation"
}
```

**Description:**
- Calculates marginal cost for inserting the order into each active driver's route
- Returns drivers sorted by profit (highest first, marked as "best")
- `marginal_profit`: Net profit added by including this order in the route
- `is_feasible`: Whether adding this order respects route constraints (150km max distance, 8-hour max time)
- `best_position`: Optimal insertion position in the delivery sequence
- Admin sees all options and can confirm with best driver or choose alternative

---

#### 4. Confirm Order Assignment (Assign to Chosen Driver)
```
POST /api/admin/confirm-order
```

**Query Parameters:**
- `reference`: Order reference code (string)
- `customer_name`: Customer name (string)
- `address`: Delivery address (string)
- `lat`: Latitude (float)
- `lng`: Longitude (float)
- `delivery_value`: Delivery payment value (float, in TND)
- `driver_id`: Selected driver ID (integer)

**Response Example:**
```json
{
  "success": true,
  "message": "Order assigned to Livreur Ahmad",
  "order": {
    "id": 12345,
    "reference": "CMD-2024-0101",
    "status": "assigned"
  },
  "route": {
    "route_id": 5,
    "driver_name": "Livreur Ahmad",
    "total_distance_km": 54.5,
    "total_duration_min": 220,
    "num_stops": 9,
    "total_revenue": 156.00,
    "net_profit": 89.15,
    "margin_pct": 21.3
  }
}
```

**Description:**
- Executes the order assignment to the chosen driver
- Creates order in database with status `"assigned"`
- Inserts order as RouteStop in driver's current route at optimal position
- Recalculates route metrics (distance, duration, profitability)
- Returns updated route information showing new totals
- Next step for driver: Route appears on mobile app with new stop in sequence

---

### Driver Mobile API (`/api/driver`)

#### 1. Get Current Route for Driver
```
GET /api/driver/{driver_id}/route
```

**Path Parameter:**
- `driver_id`: Unique driver ID (integer)

**Response Example:**
```json
{
  "driver_name": "Livreur Ahmad",
  "nb_colis": 12,
  "total_distance": 42.5,
  "total_duration": 180,
  "gain_net": 75.20,
  "map_url": "https://www.google.com/maps/dir/...",
  "stops": [
    {
      "stop_sequence": 1,
      "order_id": 101,
      "reference": "CMD-2024-0101",
      "expediteur": "Sophia Store",
      "adresse": "Rue de la Paix 123, Tunis",
      "gouvernorat": "Tunis",
      "delivery_value": 8.00,
      "lat": 36.8065,
      "lng": 10.1957,
      "nav_url": "https://www.google.com/maps/search/?api=1&query=36.8065,10.1957"
    }
  ]
}
```

**Description:**
- Retrieves the driver's current planned route
- Includes stop-by-stop details for navigation
- `map_url`: Google Maps URL for turn-by-turn navigation
- `nav_url`: Per-stop navigation link

---

#### 2. Get Driver Personal Statistics
```
GET /api/driver/{driver_id}/stats
```

**Path Parameter:**
- `driver_id`: Unique driver ID (integer)

**Response Example:**
```json
{
  "total_routes_done": 47,
  "total_colis_delivered": 580,
  "total_gain": 4250.75,
  "avg_margin": 19.3
}
```

**Description:**
- Lifetime statistics for a specific driver
- `total_gain`: Sum of all net profits across routes
- `avg_margin`: Average profit margin percentage

---

## 🔄 Data Pipeline Workflow

The system follows this end-to-end workflow:

```
1. DATA PREPARATION (Batch)
   ├─ CSV Import (orders, drivers)
   ├─ Data Cleaning (handle nulls, format coordinates)
   └─ Geocoding (convert addresses to lat/lng)
              ↓
2. ROUTE OPTIMIZATION (Batch)
   ├─ Distance Matrix (Haversine formula)
   ├─ OR-Tools VRP Solver
   │  ├─ Constraints: capacity, distance, time (24h max per percel)
   │  ├─ Minimize: total distance & time
   │  └─ Output: optimized routes
   └─ Route Sequencing (assign stops in order)
              ↓
3. PROFITABILITY ANALYSIS
   ├─ Calculate Revenue (sum of delivery values per route)
   ├─ Calculate Costs:
   │  ├─ Fuel Cost = distance × fuel_rate
   │  ├─ Labor Cost = duration × hourly_rate
   │  ├─ Handling Cost = nb_stops × handling_cost
   │  └─ Total Cost = sum of above
   ├─ Net Profit = Revenue - Total Cost
   └─ Profit Margin = (Net Profit / Revenue) × 100
              ↓
4. DATABASE STORAGE
   ├─ Save Routes (routes table)
   ├─ Save Stop Sequences (route_stops table)
   └─ Save Profitability (route_profitability table)
              ↓
5. MAP GENERATION
   ├─ Create Leaflet.js HTML map per driver
   ├─ Fetch route geometry from OSRM
   ├─ Plot depot and delivery stops
   └─ Output: interactive HTML files in /outputs
              ↓
6. API SERVING
   ├─ Admin queries KPIs & routes
   ├─ Drivers fetch current route & navigation
   └─ Frontend renders dashboards
              ↓
7. DYNAMIC ORDER ALLOCATION (Real-time)
   ├─ Admin adds new order
   ├─ System proposes suitable drivers (marginal cost calculation)
   ├─ Display feasible drivers ranked by profit
   ├─ Admin confirms assignment
   ├─ Order inserted at optimal position in chosen route
   ├─ Route metrics recalculated
   └─ Driver sees new stop on mobile app immediately
```

---

## 📊 Key Services Deep Dive

### 1. **data_reader.py** — Data Loading
**Responsibility:** Load orders and drivers from CSV files

**Key Functions:**
- `get_orders_from_csv()`: Reads CSV, maps column names, validates coordinates
- `get_drivers_mock()`: Returns hardcoded driver list for testing

**Example:**
```python
orders = get_orders_from_csv()
# Returns: [{"id": 1, "lat": 36.8065, "lng": 10.1957, "delivery_value": 8.0, ...}]
```

---

### 2. **routing.py** — OR-Tools Optimization
**Responsibility:** Compute optimal routes using Google OR-Tools VRP solver

**Key Constraints:**
- **Distance**: Max 150 km per vehicle (DISTANCE_MAX_M)
- **Time**: Max 8 hours per vehicle (TEMPS_MAX_SEC)
- **Capacity**: Each vehicle has a max weight capacity (in kg)

**Key Functions:**
- `get_distance_matrix()`: Haversine formula for lat/lng distance
- `optimize_routes()`: Main VRP solver
  - Creates routing model with capacity/distance/time dimensions
  - Uses PATH_CHEAPEST_ARC first solution + GUIDED_LOCAL_SEARCH
  - Returns optimized route assignments

**Output Example:**
```python
{
  "driver_id": 1,
  "driver_name": "Livreur Ahmad",
  "total_distance_km": 42.5,
  "total_duration_min": 180,
  "order_ids": [101, 102, 103, 104, 105],
  "full_orders": [...]
}
```

---

### 3. **profitability.py** — Financial Analysis
**Responsibility:** Calculate profit metrics for each route

**Key Function:**
```python
calculate_net_profit(
    base_revenue,           # Sum of delivery values
    distance_km,            # Total route distance
    estimated_time_hours,   # Total route time
    fuel_cost_per_km,       # From config
    driver_hourly_wage,     # From config
    vehicle_wear_per_km,    # Optional
    tolls_and_fees          # Handling costs
)
```

**Returns:**
```python
{
  "net_profit": 85.30,
  "total_costs": 62.70,
  "profit_margin_percentage": 22.1,
  "breakdown": {
    "revenue": 148.00,
    "fuel_cost": 15.10,
    "labor_cost": 40.00,
    "wear_cost": 5.00,
    "tolls_and_fees": 2.60
  },
  "is_profitable": True
}
```

---

### 4. **database_handler.py** — Database Operations
**Responsibility:** UPSERT routes, stops, and profitability to PostgreSQL

**Key Functions:**
- `save_results_to_db()`: Inserts or updates routes & stops
  - If a planned route exists for driver, it updates it (UPSERT)
  - Otherwise creates a new route
  - Returns list of saved route IDs
  
- `save_profitability()`: Inserts profitability metrics

**Logic:**
```
For each route:
  1. Check if route "planned" exists for driver
  2. If YES: Update distance/duration, delete old stops, add new stops
  3. If NO: Create new route, add stops
  4. Mark orders as "assigned"
  5. Save profitability data
  6. Commit transaction
```

---

### 5. **dynamic_allocation.py** — Real-time Order Assignment
**Responsibility:** Calculate marginal cost and assign new orders to best driver at runtime

**Key Constraints:**
- Distance: Max 150 km per vehicle (must not be exceeded)
- Time: Max 8 hours per vehicle
- Feasibility: Driver must have capacity for new order

**Key Functions:**
- `haversine_distance()`: Calculate distance between two points (lat/lng)
- `find_optimal_insertion_position()`: Determine best place to insert order in route sequence
  - Returns position and distance added
- `calculate_marginal_cost_per_driver()`: Evaluate cost/profit for each active driver
  - Returns sorted list: [{driver_id, driver_name, marginal_profit, is_feasible, best_position, cost_breakdown, ...}]
  - Highest profit driver first (suitable for admin decision)
- `assign_order_to_driver()`: Execute the assignment
  - Creates order in database
  - Adds RouteStop to driver's route
  - Updates route metrics and profitability
  - Returns success status

**Marginal Cost Calculation:**
```
Marginal Profit = Delivery Value - (New Fuel Cost + New Labor Cost)
Where:
  New Fuel Cost = distance_added × fuel_rate
  New Labor Cost = duration_added × hourly_rate
  
Positive marginal profit = order worth adding
Negative = unprofitable but feasible
Infeasible = exceeds distance/time constraints
```

**Output Structure:**
```json
{
  "driver_id": 1,
  "driver_name": "Livreur Ahmad",
  "marginal_profit": 4.85,
  "is_feasible": true,
  "best_position": 3,
  "distance_added_km": 12.5,
  "fuel_cost": 4.44,
  "labor_cost": 1.04,
  "handling_cost": 0.0,
  "current_distance_km": 42.0,
  "new_distance_km": 54.5,
  "current_stops": 8,
  "new_stops": 9
}
```

---

### 6. **map_generator.py** — Map Visualization
**Responsibility:** Generate interactive HTML maps with route visualization

**Features:**
- Uses Leaflet.js for map rendering
- Fetches OpenStreetMap tiles
- Calls OSRM (Open Source Routing Machine) for turn-by-turn route geometry
- Displays depot (blue marker) and stops (green markers)
- Shows summary stats (packages, distance, profit) in header

**Output:** HTML file saved to `outputs/map_driver_{driver_id}.html`

**Example Map Header:**
```
Chauffeur: Livreur Ahmad  |  📦 12 colis  |  📍 42.5 km  |  💰 Gain: 75.20 DT
```

---

## 🔧 Scripts & Utilities

### **pipeline.py** — Main Execution
The main orchestrator that ties everything together:

```bash
cd central_agent
python scripts/pipeline.py
```

**What it does:**
1. Loads orders from CSV
2. Loads drivers (mock)
3. Optimizes routes (OR-Tools)
4. Calculates profitability for each route
5. Generates Leaflet maps
6. Saves to PostgreSQL
7. Logs results

---

### **init_database.py** — Database Initialization
Creates all tables in PostgreSQL:

```bash
python scripts/init_database.py
```

**Ensures:**
- All SQLAlchemy models are reflected in the database
- Tables are created if they don't exist
- Indexes and foreign keys are set up

---

### **import_csv_to_db.py** — Data Import
Imports orders and drivers from CSV into PostgreSQL:

```bash
python scripts/import_csv_to_db.py
```

**Process:**
1. Reads CSV files using pandas
2. Cleans data (handles commas in decimals, nulls)
3. Creates Order/Driver objects
4. Inserts into database
5. Commits transaction

---

## 🎨 Frontend Components

The project includes two frontend dashboards in `central_agent/backend_agent/frontend/add/`:

### **Admin Dashboard** (`admin/index.html`)
Features for fleet managers:
- **KPI summary** (active drivers, total routes, profit)
- **Route list** with profitability metrics
- **Map viewer** for each route with stop details
- **Download optimization reports**
- **🆕 Ajouter Colis (Add Order)** section:
  - Form to enter new order details (reference, customer, address, coordinates, value)
  - "Voir Chauffeurs Adaptés" button triggers marginal cost calculation
  - Modal displays all suitable drivers ranked by profit
  - ⭐ Best driver auto-selected (highest marginal profit)
  - Admin can click alternative driver to select different one
  - "Confirmer Attribution" button executes assignment
  - Success confirmation shows updated route metrics

### **Driver App** (`driver/index.html`)
Mobile-friendly interface for drivers:
- Current route display
- Stop-by-stop breakdown
- Google Maps navigation URLs
- Personal statistics & earnings
- Performance history
- Real-time updates when new orders assigned (driver route refreshes with new stops)

*Note: These are HTML templates; they need to be served by the FastAPI backend or accessed locally.*

---

## 📝 Configuration Deep Dive

### **.env Variables**

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://postgres:pass@localhost:5432/logistics_db` |
| `PYTHONPATH` | Python import path | `./central_agent/backend_agent` |
| `CSV_ORDERS_PATH` | Orders data file | `data/fixed_database_large.csv` |
| `CSV_DRIVERS_PATH` | Drivers data file | `data/drivers.csv` |
| `FUEL_RATE` | Cost per km | `0.356` (TND) |
| `HOURLY_RATE` | Driver wage per hour | `5.0` (TND) |
| `HANDLING_COST` | Cost per delivery stop | `0.0` (TND) |
| `ORS_API_KEY` | OpenRouteService API | `your_key` (optional) |
| `TELEGRAM_BOT_TOKEN` | Telegram notifications | `your_token` (optional) |

### **app/core/config.py** — Configuration Loader

Loads all `.env` variables at startup and validates critical ones:

```python
DATABASE_URL = os.getenv("DATABASE_URL")
FUEL_RATE = float(os.getenv("FUEL_RATE", 0.0))
HOURLY_RATE = float(os.getenv("HOURLY_RATE", 0.0))
CSV_ORDERS_PATH = os.getenv("CSV_ORDERS_PATH")
```

---

## 🚀 Common Workflows

### Workflow 1: Full Pipeline (Data → Optimize → Save → Map)

```bash
# 1. Activate environment
.\.venv\Scripts\Activate.ps1

# 2. Run main pipeline
cd central_agent
python scripts/pipeline.py

# 3. Start API
cd ..
python run.py

# 4. Open browser to http://127.0.0.1:8000/docs
```

---

### Workflow 2: Import New Data

```bash
# 1. Place your CSV files in central_agent/backend_agent/app/core/data/
# 2. Update CSV paths in .env
# 3. Run import script
python central_agent/scripts/import_csv_to_db.py
# 4. Run pipeline
python central_agent/scripts/pipeline.py
```

---

### Workflow 3: Query API for Specific Driver

```powershell
# Using PowerShell/curl
$driverId = 1
curl http://127.0.0.1:8000/api/driver/$driverId/route
curl http://127.0.0.1:8000/api/driver/$driverId/stats
```

---

### Workflow 4: Dynamic Order Assignment (Real-time)

```bash
# 1. Admin opens dashboard at http://127.0.0.1:8000/frontend/add/admin/index.html
# 2. Clicks "Ajouter Colis" in sidebar
# 3. Fills order form:
#    - Reference: CMD-2024-0101
#    - Customer: Sophia Store
#    - Address: Rue de la Paix 123, Tunis
#    - Lat/Lng: 36.8065, 10.1957
#    - Value: 8.00 DT
# 4. Clicks "Voir Chauffeurs Adaptés"
#    → System calls POST /api/admin/propose-order
#    → Returns sorted driver list with marginal profit breakdown
# 5. Admin sees modal with feasible/infeasible drivers
#    → Best driver (⭐) auto-selected
#    → Can click alternative driver if desired
# 6. Clicks "Confirmer Attribution"
#    → System calls POST /api/admin/confirm-order
#    → Order created and inserted at optimal route position
#    → Route metrics recalculated
# 7. Success notification shows new route info
# 8. Driver app auto-refreshes and shows new stop in sequence
```

**Cost Calculation Breakdown:**
- Admin sees for each driver:
  - ✅ **Marginal Profit**: +4.85 DT (order is worth adding)
  - 📍 **Distance Added**: 12.5 km
  - ⛽ **Fuel Cost**: 4.44 DT (distance × 0.356 TND/km)
  - 👤 **Labor Cost**: 1.04 DT (time × 5 TND/hour)
  - 📦 **Handling**: 0 DT
  - ✗ **Infeasible**: Drivers exceeding 150km limit shown as unavailable

**Result:**
- Order assigned to most profitable driver
- Route automatically resequenced
- Driver sees updated route on mobile
- Admin dashboard shows new order in "Voir Routes"

---

## 🔍 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| **"DATABASE_URL not set"** | Missing `.env` | Create `.env` with valid `DATABASE_URL` |
| **"Connection refused"** | PostgreSQL not running | Start PostgreSQL: `psql -U postgres` |
| **"No such table: orders"** | Tables not created | Run `python scripts/init_database.py` |
| **"CSV file not found"** | Wrong path in `.env` | Verify `CSV_ORDERS_PATH` points to existing file |
| **"Port 8000 already in use"** | Another app using port | Use `uvicorn app.main:app --port 8001` |
| **"Module not found: ortools"** | Dependency missing | Run `pip install -r central_agent/requirements.txt` |

---

## 📈 Performance Metrics

The system tracks and calculates:

| Metric | Calculation | Purpose |
|--------|-----------|---------|
| **Total Revenue** | Σ delivery_value | Income from all orders |
| **Fuel Cost** | distance_km × fuel_rate | Vehicle fuel expenses |
| **Labor Cost** | duration_hours × hourly_rate | Driver salary per route |
| **Net Profit** | Revenue - Total Costs | Bottom line profit |
| **Profit Margin** | (Net Profit / Revenue) × 100 | Profitability percentage |
| **Route Distance** | Haversine sum | Kilometers traveled |
| **Route Duration** | Distance/speed + stops | Total time (hours) |

---

## 📚 File Locations Cheat Sheet

| Component | Location |
|-----------|----------|
| Main API | `central_agent/backend_agent/app/main.py` |
| Admin endpoints | `central_agent/backend_agent/app/api/admin_api.py` |
| Driver endpoints | `central_agent/backend_agent/app/api/driver_api.py` |
| Dynamic allocation | `central_agent/backend_agent/app/services/dynamic_allocation.py` |
| Database models | `central_agent/backend_agent/app/models/models.py` |
| Route optimizer | `central_agent/backend_agent/app/services/routing.py` |
| Profit calculator | `central_agent/backend_agent/app/services/profitability.py` |
| Admin dashboard | `central_agent/backend_agent/frontend/add/admin/index.html` |
| Driver app | `central_agent/backend_agent/frontend/add/driver/index.html` |
| Main pipeline | `central_agent/scripts/pipeline.py` |
| Sample data | `central_agent/backend_agent/app/core/data/` |
| Generated maps | `central_agent/backend_agent/outputs/` |
| Environment config | `.env` (root) |

---

## 🎯 Next Steps

1. ✅ **Verify Installation**: Run `python run.py` and visit `http://127.0.0.1:8000/docs`
2. 📊 **Test Pipeline**: Run `python central_agent/scripts/pipeline.py`
3. 📡 **Query APIs**: Use Swagger UI or curl to test endpoints
4. 🗺️ **View Maps**: Check `central_agent/backend_agent/outputs/map_driver_*.html`
5. 📈 **Monitor Routes**: Check admin dashboard at `/api/admin/summary`
6. 🚗 **Driver View**: Check driver route at `/api/driver/1/route`

---

## 📞 Support & Documentation

- **API Docs**: `http://127.0.0.1:8000/docs` (interactive Swagger UI)
- **Backend Doc**: `central_agent/backend_agent/API_DOC.md`
- **PostgreSQL Guide**: `POSTGRESQL_SETUP.md`
- **Config Template**: `.env` file

---

**Status**: Active Development | Last Updated: May 2026
