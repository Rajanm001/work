"""
FastAPI Backend for Clinical Supply Chain Control Tower
Beautiful, Production-Ready REST API
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agents.config import config
from tools.sql_tools import SQLQueryTool, RiskCalculationTool, AlertGeneratorTool
from agents.supply_watchdog.run_monitoring_simple import SupplyWatchdogSimple
from agents.scenario_strategist.chat_interface_simple import ScenarioStrategistSimple
import json
import asyncio

# Initialize FastAPI app
app = FastAPI(
    title="Clinical Supply Chain Control Tower",
    description="AI-Powered Supply Chain Risk Detection & Decision Support",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize tools and agents
sql_tool = SQLQueryTool(config.db_connection_string)
risk_tool = RiskCalculationTool(config)
alert_tool = AlertGeneratorTool()

# Global agent instances
watchdog_agent = None
strategist_agent = None


# Pydantic models
class AlertResponse(BaseModel):
    alert_id: str
    timestamp: str
    alert_type: str
    severity: str
    affected_items_count: int
    affected_items: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str


class InventorySummary(BaseModel):
    total_materials: int
    total_batches: int
    expiring_soon: int
    critical_shortfalls: int


# API Routes

@app.get("/")
async def root():
    """Root endpoint - returns API info"""
    return {
        "name": "Clinical Supply Chain Control Tower API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "dashboard": "/api/dashboard",
            "monitoring": "/api/monitoring/run",
            "chat": "/api/chat",
            "inventory": "/api/inventory",
            "alerts": "/api/alerts"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        result = sql_tool.execute_query("SELECT 1 as health;")
        db_status = "healthy" if result else "unhealthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "agents": {
            "supply_watchdog": "ready",
            "scenario_strategist": "ready"
        }
    }


@app.get("/api/dashboard")
async def get_dashboard_data():
    """Get main dashboard summary data"""
    try:
        # Get inventory summary
        inventory_query = """
        SELECT 
            COUNT(DISTINCT lot) as total_batches,
            COUNT(DISTINCT trial_name) as total_trials,
            SUM(received_packages) as total_packages,
            COUNT(*) FILTER (WHERE expiry_date < CURRENT_DATE + INTERVAL '90 days') as expiring_soon
        FROM available_inventory_report;
        """
        inventory_data = sql_tool.execute_query(inventory_query)[0]
        
        # Get enrollment summary
        enrollment_query = """
        SELECT 
            COUNT(DISTINCT trial_alias) as active_trials,
            COUNT(DISTINCT country_name) as countries,
            SUM(total_enrolled_actual) as total_patients
        FROM country_level_enrollment_report;
        """
        enrollment_data = sql_tool.execute_query(enrollment_query)[0]
        
        # Get risk summary
        risk_query = """
        SELECT 
            COUNT(*) FILTER (WHERE expiry_date < CURRENT_DATE + INTERVAL '30 days') as critical_expiry,
            COUNT(*) FILTER (WHERE expiry_date BETWEEN CURRENT_DATE + INTERVAL '30 days' 
                AND CURRENT_DATE + INTERVAL '60 days') as high_expiry,
            COUNT(*) FILTER (WHERE expiry_date BETWEEN CURRENT_DATE + INTERVAL '60 days' 
                AND CURRENT_DATE + INTERVAL '90 days') as medium_expiry
        FROM available_inventory_report
        WHERE expiry_date > CURRENT_DATE;
        """
        risk_data = sql_tool.execute_query(risk_query)[0]
        
        # Get recent orders
        orders_query = """
        SELECT 
            trial_alias,
            order_number,
            status,
            order_date,
            requested_delivery_date,
            actual_delivery_date
        FROM distribution_order_report
        ORDER BY order_date DESC
        LIMIT 10;
        """
        recent_orders = sql_tool.execute_query(orders_query)
        
        return {
            "inventory": inventory_data,
            "enrollment": enrollment_data,
            "risks": risk_data,
            "recent_orders": recent_orders,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/inventory/expiring")
async def get_expiring_inventory(days: int = 90):
    """Get inventory expiring within specified days"""
    try:
        query = f"""
        SELECT 
            trial_name,
            location,
            lot,
            package_type_description,
            expiry_date,
            received_packages,
            EXTRACT(DAY FROM (expiry_date - CURRENT_DATE)) as days_until_expiry,
            CASE 
                WHEN EXTRACT(DAY FROM (expiry_date - CURRENT_DATE)) <= 30 THEN 'CRITICAL'
                WHEN EXTRACT(DAY FROM (expiry_date - CURRENT_DATE)) <= 60 THEN 'HIGH'
                WHEN EXTRACT(DAY FROM (expiry_date - CURRENT_DATE)) <= 90 THEN 'MEDIUM'
                ELSE 'LOW'
            END as risk_level
        FROM available_inventory_report
        WHERE expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '{days} days'
            AND expiry_date > CURRENT_DATE
        ORDER BY expiry_date ASC;
        """
        
        results = sql_tool.execute_query(query)
        return {
            "count": len(results),
            "items": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/inventory/by-trial/{trial_alias}")
async def get_inventory_by_trial(trial_alias: str):
    """Get inventory for a specific trial"""
    try:
        query = """
        SELECT 
            trial_name,
            location,
            lot,
            package_type_description,
            expiry_date,
            packages_awaiting,
            received_packages,
            packages_pending_shipment,
            shipped_packages,
            min_qty,
            max_qty
        FROM available_inventory_report
        WHERE trial_name ILIKE %(pattern)s
        ORDER BY expiry_date ASC;
        """
        
        results = sql_tool.execute_query(query, {"pattern": f"%{trial_alias}%"})
        return {
            "trial": trial_alias,
            "count": len(results),
            "inventory": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/enrollment/summary")
async def get_enrollment_summary():
    """Get enrollment summary by trial and country"""
    try:
        query = """
        SELECT 
            trial_alias,
            country_name,
            enrollment_level,
            total_enrolled_forecast,
            total_enrolled_planned,
            total_enrolled_actual,
            enrollment_rate_monthly_actual,
            CASE 
                WHEN total_enrolled_actual > total_enrolled_planned * 1.1 THEN 'ACCELERATED'
                WHEN total_enrolled_actual < total_enrolled_planned * 0.9 THEN 'SLOWER'
                ELSE 'ON_TRACK'
            END as enrollment_status
        FROM country_level_enrollment_report
        ORDER BY trial_alias, country_name;
        """
        
        results = sql_tool.execute_query(query)
        return {
            "count": len(results),
            "enrollments": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitoring/run")
async def run_monitoring(background_tasks: BackgroundTasks):
    """Trigger Supply Watchdog monitoring (async)"""
    try:
        global watchdog_agent
        if not watchdog_agent:
            watchdog_agent = SupplyWatchdogSimple()
        
        # Run in background
        background_tasks.add_task(watchdog_agent.run_monitoring)
        
        return {
            "status": "started",
            "message": "Supply Watchdog monitoring initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts/latest")
async def get_latest_alerts(limit: int = 10):
    """Get latest monitoring alerts"""
    try:
        alerts_dir = Path(__file__).parent.parent / "agents" / "supply_watchdog" / "alerts"
        
        if not alerts_dir.exists():
            return {"alerts": [], "count": 0}
        
        alert_files = sorted(alerts_dir.glob("alert_*.json"), reverse=True)[:limit]
        
        alerts = []
        for file_path in alert_files:
            with open(file_path, 'r') as f:
                alert_data = json.load(f)
                alerts.append(alert_data)
        
        return {
            "count": len(alerts),
            "alerts": alerts
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_strategist(message: ChatMessage):
    """Chat with Scenario Strategist Agent"""
    try:
        global strategist_agent
        if not strategist_agent:
            strategist_agent = ScenarioStrategistSimple()
        
        response = strategist_agent.ask(message.message)
        
        return ChatResponse(
            response=response,
            conversation_id=message.conversation_id or "default",
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trials")
async def get_trials():
    """Get list of all trials"""
    try:
        query = """
        SELECT DISTINCT trial_alias as trial_id, trial_name
        FROM available_inventory_report
        ORDER BY trial_name;
        """
        
        results = sql_tool.execute_query(query)
        return {
            "count": len(results),
            "trials": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/countries")
async def get_countries():
    """Get list of all countries"""
    try:
        query = """
        SELECT DISTINCT country_name, COUNT(*) as trial_count
        FROM country_level_enrollment_report
        GROUP BY country_name
        ORDER BY country_name;
        """
        
        results = sql_tool.execute_query(query)
        return {
            "count": len(results),
            "countries": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/risk-heatmap")
async def get_risk_heatmap():
    """Get risk heatmap data by trial and country"""
    try:
        query = """
        SELECT 
            air.trial_name,
            air.location as country,
            COUNT(*) as total_batches,
            COUNT(*) FILTER (WHERE air.expiry_date < CURRENT_DATE + INTERVAL '30 days') as critical_count,
            COUNT(*) FILTER (WHERE air.expiry_date BETWEEN CURRENT_DATE + INTERVAL '30 days' 
                AND CURRENT_DATE + INTERVAL '60 days') as high_count,
            COUNT(*) FILTER (WHERE air.expiry_date BETWEEN CURRENT_DATE + INTERVAL '60 days' 
                AND CURRENT_DATE + INTERVAL '90 days') as medium_count
        FROM available_inventory_report air
        WHERE air.expiry_date > CURRENT_DATE
        GROUP BY air.trial_name, air.location
        ORDER BY critical_count DESC, high_count DESC;
        """
        
        results = sql_tool.execute_query(query)
        return {
            "heatmap_data": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for real-time updates
@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring updates"""
    await websocket.accept()
    try:
        while True:
            # Send periodic updates every 30 seconds
            await asyncio.sleep(30)
            
            # Get quick summary
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "monitoring",
                "message": "System operational"
            }
            
            await websocket.send_json(summary)
    
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket")


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Clinical Supply Chain Control Tower - API Server")
    print("=" * 60)
    print(f"\nStarting server on http://localhost:8000")
    print(f"API Documentation: http://localhost:8000/api/docs")
    print(f"Dashboard: http://localhost:8000/dashboard")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
