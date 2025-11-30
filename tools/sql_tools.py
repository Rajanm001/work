"""
Common tools used by all agents
"""

from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from datetime import datetime
import uuid
import json


class SQLQueryTool:
    """Execute SQL queries against PostgreSQL database"""
    
    def __init__(self, connection_string: str):
        self.conn_string = connection_string
    
    def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as list of dictionaries.
        
        Args:
            query: SQL query (parameterized if needed)
            parameters: Query parameters
            
        Returns:
            List of row dictionaries
        """
        start_time = time.time()
        
        try:
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, parameters or {})
                    
                    # Check if query returns results
                    if cursor.description is None:
                        return []
                    
                    results = [dict(row) for row in cursor.fetchall()]
                    
                    execution_time = (time.time() - start_time) * 1000
                    print(f"[SQL] Query executed in {execution_time:.2f}ms, {len(results)} rows returned")
                    
                    return results
        
        except psycopg2.Error as e:
            print(f"[SQL ERROR] {e}")
            raise


class RiskCalculationTool:
    """Calculate supply chain risk metrics"""
    
    def __init__(self, config):
        self.config = config
    
    def categorize_expiry_risk(self, days_until_expiry: int) -> str:
        """Categorize expiry risk level"""
        if days_until_expiry <= self.config.expiry_critical_days:
            return "CRITICAL"
        elif days_until_expiry <= self.config.expiry_high_days:
            return "HIGH"
        elif days_until_expiry <= self.config.expiry_medium_days:
            return "MEDIUM"
        else:
            return "LOW"
    
    def calculate_shortfall_severity(self, weeks_remaining: float) -> str:
        """Calculate shortfall severity"""
        if weeks_remaining < 2:
            return "CRITICAL"
        elif weeks_remaining < 4:
            return "HIGH"
        elif weeks_remaining < self.config.shortfall_horizon_weeks:
            return "MEDIUM"
        else:
            return "LOW"


class AlertGeneratorTool:
    """Generate structured alert payloads"""
    
    def create_json_alert(
        self,
        alert_type: str,
        severity: str,
        affected_items: List[Dict],
        metadata: Dict
    ) -> Dict:
        """Create standardized JSON alert payload"""
        return {
            "alert_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "alert_type": alert_type,
            "severity": severity,
            "affected_items_count": len(affected_items),
            "affected_items": affected_items,
            "metadata": metadata
        }
    
    def format_alert_email(self, alert_data: Dict) -> str:
        """Format alert data as email body"""
        lines = [
            "=" * 60,
            "CLINICAL SUPPLY CHAIN ALERT",
            "=" * 60,
            f"Alert ID: {alert_data['alert_id']}",
            f"Timestamp: {alert_data['timestamp']}",
            f"Severity: {alert_data['severity']}",
            f"Alert Type: {alert_data['alert_type']}",
            "",
            f"Total Affected Items: {alert_data['affected_items_count']}",
            "",
            "=" * 60,
            "DETAILS",
            "=" * 60,
            ""
        ]
        
        for i, item in enumerate(alert_data['affected_items'][:50], 1):
            lines.append(f"{i}. {json.dumps(item, indent=2)}")
            lines.append("")
        
        if alert_data['affected_items_count'] > 50:
            lines.append(f"... and {alert_data['affected_items_count'] - 50} more items")
        
        lines.extend([
            "",
            "=" * 60,
            "METADATA",
            "=" * 60,
            json.dumps(alert_data['metadata'], indent=2)
        ])
        
        return "\n".join(lines)


class DataValidationTool:
    """Validate data quality"""
    
    def validate_batch_id(self, batch_id: str) -> bool:
        """Validate batch ID format"""
        return bool(batch_id and len(batch_id) > 0)
    
    def validate_country_code(self, country: str) -> str:
        """Normalize country names to codes"""
        country_mapping = {
            "germany": "DE",
            "deutschland": "DE",
            "united states": "US",
            "usa": "US",
            "united kingdom": "GB",
            "uk": "GB",
            "france": "FR",
            "spain": "ES",
            "italy": "IT",
            "canada": "CA",
            "australia": "AU",
            "japan": "JP",
            "china": "CN",
            "india": "IN",
        }
        
        normalized = country_mapping.get(country.lower())
        if normalized:
            return normalized
        
        # If already a code (2 letters), return uppercase
        if len(country) == 2:
            return country.upper()
        
        return country
    
    def check_data_freshness(
        self, 
        table_name: str, 
        timestamp_column: str,
        sql_tool: SQLQueryTool,
        max_age_hours: int = 24
    ) -> Tuple[bool, str]:
        """Check if data is fresh"""
        query = f"""
        SELECT 
            MAX({timestamp_column}) as last_update,
            EXTRACT(HOUR FROM (CURRENT_TIMESTAMP - MAX({timestamp_column}))) as hours_ago
        FROM {table_name};
        """
        
        try:
            result = sql_tool.execute_query(query)[0]
            hours_ago = float(result.get('hours_ago', 999))
            
            if hours_ago > max_age_hours:
                return False, f"Data is {hours_ago:.1f} hours old (threshold: {max_age_hours}h)"
            
            return True, f"Data is current ({hours_ago:.1f} hours old)"
        
        except Exception as e:
            return False, f"Could not check freshness: {e}"
