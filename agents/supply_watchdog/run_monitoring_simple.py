"""
Supply Watchdog Agent - Simple Implementation

Direct SQL queries without complex agent orchestration.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from typing import Dict, List
from agents.config import config
from tools.sql_tools import SQLQueryTool, RiskCalculationTool, AlertGeneratorTool
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor


class SupplyWatchdogSimple:
    """Simplified monitoring agent using direct SQL queries"""
    
    def __init__(self):
        self.config = config
        self.alert_tool = AlertGeneratorTool()
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            user=self.config.db_user,
            password=self.config.db_password,
            dbname=self.config.db_name
        )
    
    def detect_expiry_risks(self) -> List[Dict]:
        """Detect batches expiring within configured thresholds"""
        print("🔍 Detecting expiry risks...")
        
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query for expiring inventory
        query = """
            SELECT 
                trial_name,
                location,
                lot,
                package_type_description as material,
                expiry_date,
                EXTRACT(DAY FROM (expiry_date::date - CURRENT_DATE)) as days_until_expiry
            FROM available_inventory_report
            WHERE expiry_date IS NOT NULL
                AND expiry_date::date > CURRENT_DATE
                AND expiry_date::date <= CURRENT_DATE + INTERVAL '90 days'
            ORDER BY expiry_date ASC
            LIMIT 50;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Categorize by risk level
        risk_calculator = RiskCalculationTool(self.config)
        categorized = []
        
        for row in results:
            days = int(row['days_until_expiry'])
            risk_level = risk_calculator.categorize_expiry_risk(days)
            
            categorized.append({
                'trial_name': row['trial_name'],
                'location': row['location'],
                'lot': row['lot'],
                'material': row['material'],
                'expiry_date': str(row['expiry_date']),
                'days_until_expiry': days,
                'risk_level': risk_level
            })
        
        print(f"  ✓ Found {len(categorized)} expiring batches")
        return categorized
    
    def detect_shortfall_risks(self) -> List[Dict]:
        """Detect potential inventory shortfalls"""
        print("🔍 Detecting shortfall risks...")
        
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Simplified shortfall detection - check low inventory
        query = """
            SELECT 
                trial_name,
                location,
                COUNT(*) as batch_count,
                SUM(CASE WHEN expiry_date::date <= CURRENT_DATE + INTERVAL '30 days' THEN 1 ELSE 0 END) as expiring_soon
            FROM available_inventory_report
            WHERE expiry_date IS NOT NULL
            GROUP BY trial_name, location
            HAVING SUM(CASE WHEN expiry_date::date <= CURRENT_DATE + INTERVAL '30 days' THEN 1 ELSE 0 END) > 0
            ORDER BY expiring_soon DESC
            LIMIT 20;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        shortfalls = []
        for row in results:
            if row['expiring_soon'] >= row['batch_count'] * 0.5:  # 50%+ expiring
                shortfalls.append({
                    'trial_name': row['trial_name'],
                    'location': row['location'],
                    'total_batches': row['batch_count'],
                    'expiring_soon': row['expiring_soon'],
                    'risk_level': 'HIGH'
                })
        
        print(f"  ✓ Found {len(shortfalls)} potential shortfalls")
        return shortfalls
    
    def generate_alert(self, expiry_risks: List[Dict], shortfall_risks: List[Dict]) -> Dict:
        """Generate consolidated alert"""
        
        # Count by severity
        severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for item in expiry_risks:
            severity_counts[item['risk_level']] += 1
        
        # Determine overall severity
        if severity_counts['CRITICAL'] > 0:
            overall_severity = 'CRITICAL'
        elif severity_counts['HIGH'] > 0 or len(shortfall_risks) > 0:
            overall_severity = 'HIGH'
        elif severity_counts['MEDIUM'] > 0:
            overall_severity = 'MEDIUM'
        else:
            overall_severity = 'LOW'
        
        alert = self.alert_tool.create_json_alert(
            alert_type='daily_monitoring',
            severity=overall_severity,
            affected_items=expiry_risks[:10],  # Top 10
            metadata={
                'timestamp': datetime.now().isoformat(),
                'expiry_risk_count': len(expiry_risks),
                'shortfall_risk_count': len(shortfall_risks),
                'severity_breakdown': severity_counts
            }
        )
        
        return alert
    
    def run_monitoring(self) -> Dict:
        """Execute daily monitoring workflow"""
        print("\n" + "=" * 60)
        print(f"Supply Watchdog Monitoring - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")
        
        try:
            # Detect risks
            expiry_risks = self.detect_expiry_risks()
            shortfall_risks = self.detect_shortfall_risks()
            
            # Generate alert
            alert = self.generate_alert(expiry_risks, shortfall_risks)
            
            # Save alert
            self._save_alert(alert)
            
            # Print summary
            print("\n" + "=" * 60)
            print("MONITORING SUMMARY")
            print("=" * 60)
            print(f"✓ Expiry Risks Detected: {len(expiry_risks)}")
            print(f"✓ Shortfall Risks Detected: {len(shortfall_risks)}")
            print(f"✓ Overall Severity: {alert['severity']}")
            print(f"✓ Alert saved to: {self._get_alert_path()}")
            print("=" * 60 + "\n")
            
            return alert
            
        except Exception as e:
            print(f"✗ Error during monitoring: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def _get_alert_path(self) -> str:
        """Get path for saving alerts"""
        alert_dir = Path(__file__).parent / "alerts"
        alert_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(alert_dir / f"alert_{timestamp}.json")
    
    def _save_alert(self, alert_data: Dict):
        """Save alert to file"""
        alert_path = self._get_alert_path()
        with open(alert_path, 'w') as f:
            json.dump(alert_data, f, indent=2)


def main():
    """Main entry point"""
    # Validate configuration
    if not config.validate():
        print("✗ Configuration validation failed. Please check your .env file.")
        return
    
    # Run monitoring
    agent = SupplyWatchdogSimple()
    result = agent.run_monitoring()
    
    return result


if __name__ == "__main__":
    main()
