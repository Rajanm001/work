# 🚀 Clinical Supply Chain Control Tower - Quick Start Guide

## Production-Ready Deployment Instructions

### Prerequisites

1. **Python 3.11+** installed
2. **PostgreSQL 14+** installed and running
3. **Web browser** (Chrome, Firefox, Edge)

---

## Step 1: Environment Setup

### 1.1 Create Virtual Environment

```powershell
cd "c:\Users\Rajan mishra Ji\work\clinical-supply-chain-ai"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 1.2 Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** Installing all dependencies may take 5-10 minutes.

---

## Step 2: Database Configuration

### 2.1 Configure Environment Variables

Edit the `.env` file and set your configuration:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=clinical_supply_chain
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRES_PASSWORD

# AI Provider (optional - only needed for full LLM features)
OPENAI_API_KEY=sk-your-openai-api-key
# OR
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

**Important:** Replace `YOUR_POSTGRES_PASSWORD` with your actual PostgreSQL password.

### 2.2 Create Database and Tables

```powershell
# Create database structure
python database\setup\create_database.py
python database\setup\create_tables_actual.py
```

---

## Step 3: Load Your Data

### 3.1 Verify Data Files

Your CSV files should be in: `database\data\`

```powershell
# Verify files are present
Get-ChildItem database\data\*.csv
```

### 3.2 Load Data into Database

```powershell
python database\setup\load_actual_data.py
```

This will:
- ✅ Load all 40+ CSV files
- ✅ Transform and clean data
- ✅ Create indexes for performance

**Expected time:** 2-5 minutes depending on data size.
- ✅ Verify data integrity

**Expected output:**
```
✓ Loaded 214 rows into allocated_materials_to_orders
✓ Loaded 549 rows into available_inventory_report
✓ Loaded 214 rows into enrollment_rate_report
...
✓ Successfully loaded: 9 tables
```

---

## Step 4: Start the API Server

```powershell
cd api
python main.py
```

**Expected output:**
```
Clinical Supply Chain Control Tower - API Server
================================================
Starting server on http://localhost:8000
API Documentation: http://localhost:8000/api/docs
Dashboard: http://localhost:8000/dashboard
```

Keep this terminal window open while using the dashboard.

---

## Step 5: Access the Beautiful Web Dashboard

### 5.1 Open Dashboard

Open your browser and navigate to:

```
http://localhost:8000/dashboard
```

### 5.2 Dashboard Features

✅ **Real-time Statistics**
- Total batches across all trials
- Expiring inventory alerts
- Active trial count
- Total patient enrollment

✅ **Risk Visualization**
- Interactive pie chart
- Color-coded severity levels
- Critical/High/Medium breakdown

✅ **Expiring Inventory List**
- 90-day expiry window
- Trial and location details
- Risk level badges
- Days until expiry

✅ **AI Chat Assistant** (optional if API key configured)
- Ask questions in natural language
- Get feasibility assessments
- Evidence-based recommendations

✅ **Recent Orders Tracking**
- Distribution order status
- Delivery timelines
- Trial associations

---

## Step 6: Run Autonomous Monitoring (Workflow A)

### Simplified Monitoring (Recommended for Quick Start)

```powershell
python agents\supply_watchdog\run_monitoring_simple.py
```

This will:
1. ✅ Detect batches expiring within 90 days
2. ✅ Identify shortfall risks
3. ✅ Generate JSON alert payload
4. ✅ Save alert to `agents\supply_watchdog\alerts\`

**Expected output:**
```
=============================================================
Supply Watchdog Monitoring - 2025-11-30 10:15:00
=============================================================

🔍 Detecting expiry risks...
  ✓ Found 12 expiring batches
🔍 Detecting shortfall risks...
  ✓ Found 2 potential shortfalls

=============================================================
MONITORING SUMMARY
=============================================================
✓ Expiry Risks Detected: 12
✓ Shortfall Risks Detected: 2
✓ Overall Severity: HIGH
✓ Alert saved to: agents\supply_watchdog\alerts\alert_20251130_101530.json
=============================================================
```

---

## Step 7: Test the AI Assistant (Workflow B)

### Simplified Chat Interface (Recommended)

```powershell
python agents\scenario_strategist\chat_interface_simple.py
```

Example interaction:
```
You: Can we extend batch LOT-14364098?

Agent: 
✅ EXTENSION FEASIBILITY: YES

Batch Information:
• Trial: Shake Study
• Location: Saint Kitts and Nevis
• Material: Dog Patch
• Current Expiry: 2028-06-06

Extension request can be submitted. Previous extension found.

Next Steps:
1. Submit extension request to regulatory affairs
2. Provide stability data to analytical lab
3. Expected approval timeline: 4-6 weeks
```

### Supported Query Types:

1. **Extension Feasibility**
   - "Can we extend batch LOT-12345678?"
   
2. **Inventory Summary**
   - "Show inventory for Study Shake"
   
3. **Shipping Timelines**
   - "Shipping timeline to Zimbabwe"

---

## Step 8: Access API Documentation

Navigate to: `http://localhost:8000/api/docs`

This provides:
- 📚 Interactive API documentation (Swagger UI)
- 🧪 Test endpoints directly
- 📋 Request/response schemas
- 🔍 All available endpoints

### Key Endpoints:

```
GET  /api/dashboard              - Dashboard summary data
GET  /api/inventory/expiring     - Expiring inventory list
GET  /api/enrollment/summary     - Enrollment statistics
POST /api/monitoring/run         - Trigger monitoring
POST /api/chat                   - Chat with AI assistant
GET  /api/alerts/latest          - Get recent alerts
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Dashboard (HTML/JS)                  │
│              Beautiful, Responsive, Real-time UI             │
└─────────────────────────────────────────────────────────────┘
                              ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                  │
│          RESTful API + WebSocket + Background Tasks          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────┬──────────────────────────────┐
│   Supply Watchdog Agent      │  Scenario Strategist Agent   │
│   (Autonomous Monitoring)    │  (Conversational Assistant)  │
└──────────────────────────────┴──────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│     SQL Tools (Direct Database Queries + Risk Calculation)   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                PostgreSQL Database (40+ Tables)              │
│         Clinical Trial Data, Inventory, Enrollment           │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Issue: Database Connection Error

**Solution:**
```powershell
# Check PostgreSQL is running
Get-Service postgresql*

# Restart if needed
Restart-Service postgresql-x64-14

# Verify connection
psql -U postgres -d clinical_supply_chain
```

### Issue: API Key Not Working

**Solution:**
```powershell
# Verify .env file
Get-Content .env | Select-String "API_KEY"

# Ensure no quotes around the key
# Correct:   OPENAI_API_KEY=sk-abc123
# Incorrect: OPENAI_API_KEY="sk-abc123"
```

### Issue: Port Already in Use

**Solution:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process
taskkill /PID <process_id> /F

# Or change port in api/main.py
uvicorn.run("main:app", port=8001)
```

---

## Production Deployment Checklist

- [ ] Set strong database password
- [ ] Use environment-specific .env files
- [ ] Enable HTTPS (use reverse proxy like Nginx)
- [ ] Set up database backups
- [ ] Configure email alerts
- [ ] Enable logging and monitoring
- [ ] Set up rate limiting
- [ ] Implement authentication (JWT)
- [ ] Use production-grade WSGI server (Gunicorn/uWSGI)
- [ ] Set up Docker containers (optional)
- [ ] Configure CI/CD pipeline

---

## Support & Documentation

📖 **Full Documentation:** `docs/architecture/`
- Part 1: Architecture Design
- Part 2: Technical Implementation
- Part 3: Edge Case Handling

🐛 **Issue Tracking:** Create issues in your repository

📧 **Contact:** Your team's email

---

## Success Indicators

After setup, you should see:

✅ **Dashboard loads** with real-time statistics  
✅ **Expiring inventory** displayed with risk levels  
✅ **AI chat** responds to queries  
✅ **Monitoring run** generates alerts  
✅ **API documentation** accessible  
✅ **Database queries** execute in <500ms  

---

**🎉 Congratulations! Your Clinical Supply Chain Control Tower is operational!**
