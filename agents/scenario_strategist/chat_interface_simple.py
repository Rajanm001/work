"""
Scenario Strategist Agent - Simple Implementation

Answers queries using direct SQL without complex orchestration.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from typing import Dict, List
from agents.config import config
import psycopg2
from psycopg2.extras import RealDictCursor
import json


class ScenarioStrategistSimple:
    """Simplified decision support agent"""
    
    def __init__(self):
        self.config = config
        self.conversation_history = []
    
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            user=self.config.db_user,
            password=self.config.db_password,
            dbname=self.config.db_name
        )
    
    def check_batch_exists(self, lot_number: str):
        """Check if batch exists in inventory"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT trial_name, location, lot, package_type_description, expiry_date
            FROM available_inventory_report
            WHERE lot ILIKE %s
            LIMIT 1;
        """
        
        cursor.execute(query, (f"%{lot_number}%",))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return dict(result) if result else None
    
    def check_extension_feasibility(self, lot_number: str) -> Dict:
        """Check if batch can be extended"""
        batch_info = self.check_batch_exists(lot_number)
        
        if not batch_info:
            return {
                'feasible': False,
                'reason': f"Batch {lot_number} not found in inventory"
            }
        
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if previous extensions exist
        query = """
            SELECT revision_number, extension_type, status
            FROM re_evaluation
            WHERE lot ILIKE %s
            ORDER BY revision_date DESC
            LIMIT 1;
        """
        
        cursor.execute(query, (f"%{lot_number}%",))
        extension_history = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if extension_history:
            return {
                'feasible': True,
                'batch_info': batch_info,
                'extension_history': dict(extension_history),
                'recommendation': 'Extension request can be submitted. Previous extension found.'
            }
        else:
            return {
                'feasible': True,
                'batch_info': batch_info,
                'extension_history': None,
                'recommendation': 'Extension request can be submitted. No previous extensions found.'
            }
    
    def get_trial_inventory_summary(self, trial_name: str) -> List[Dict]:
        """Get inventory summary for a trial"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                trial_name,
                location,
                COUNT(*) as batch_count,
                MIN(expiry_date) as earliest_expiry,
                MAX(expiry_date) as latest_expiry
            FROM available_inventory_report
            WHERE trial_name ILIKE %s
            GROUP BY trial_name, location
            ORDER BY earliest_expiry ASC;
        """
        
        cursor.execute(query, (f"%{trial_name}%",))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [dict(row) for row in results]
    
    def get_country_shipping_timeline(self, destination: str) -> List[Dict]:
        """Get shipping timelines to a country"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT destination_country, lead_time_days_min, lead_time_days_max
            FROM ip_shipping_timelines_report
            WHERE destination_country ILIKE %s
            LIMIT 5;
        """
        
        cursor.execute(query, (f"%{destination}%",))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [dict(row) for row in results]
    
    def ask(self, question: str) -> str:
        """
        Process user question and return answer.
        
        Supports queries like:
        - "Can we extend batch LOT-123?"
        - "Show inventory for Study XYZ"
        - "Shipping timeline to Germany"
        """
        question_lower = question.lower()
        
        try:
            # Extension feasibility check
            if 'extend' in question_lower or 'extension' in question_lower:
                # Extract batch ID (simple pattern matching)
                words = question.split()
                lot_number = None
                for word in words:
                    if 'lot-' in word.lower() or len(word) > 8 and word.replace('-', '').isalnum():
                        lot_number = word
                        break
                
                if lot_number:
                    result = self.check_extension_feasibility(lot_number)
                    
                    if result['feasible']:
                        response = f"""
✅ EXTENSION FEASIBILITY: YES

Batch Information:
• Trial: {result['batch_info']['trial_name']}
• Location: {result['batch_info']['location']}
• Material: {result['batch_info']['package_type_description']}
• Current Expiry: {result['batch_info']['expiry_date']}

{result['recommendation']}

Next Steps:
1. Submit extension request to regulatory affairs
2. Provide stability data to analytical lab
3. Expected approval timeline: 4-6 weeks
"""
                        return response
                    else:
                        return f"❌ {result['reason']}"
                else:
                    return "❌ Please provide a batch/lot number (e.g., LOT-12345678)"
            
            # Inventory summary
            elif 'inventory' in question_lower or 'stock' in question_lower:
                # Extract trial name
                words = question.split()
                trial_name = None
                for i, word in enumerate(words):
                    if word.lower() in ['for', 'study', 'trial']:
                        if i + 1 < len(words):
                            trial_name = words[i + 1]
                            break
                
                if trial_name:
                    results = self.get_trial_inventory_summary(trial_name)
                    
                    if results:
                        response = f"\n📦 INVENTORY SUMMARY FOR {results[0]['trial_name']}\n\n"
                        for item in results:
                            response += f"Location: {item['location']}\n"
                            response += f"  • Batches: {item['batch_count']}\n"
                            response += f"  • Earliest Expiry: {item['earliest_expiry']}\n"
                            response += f"  • Latest Expiry: {item['latest_expiry']}\n\n"
                        return response
                    else:
                        return f"❌ No inventory found for trial '{trial_name}'"
                else:
                    return "❌ Please specify a trial name"
            
            # Shipping timeline
            elif 'shipping' in question_lower or 'timeline' in question_lower:
                # Extract country
                words = question.split()
                country = None
                for i, word in enumerate(words):
                    if word.lower() in ['to', 'for']:
                        if i + 1 < len(words):
                            country = words[i + 1]
                            break
                
                if country:
                    results = self.get_country_shipping_timeline(country)
                    
                    if results:
                        response = f"\n🚚 SHIPPING TIMELINE TO {results[0]['destination_country']}\n\n"
                        item = results[0]
                        response += f"Lead Time: {item['lead_time_days_min']}-{item['lead_time_days_max']} days\n"
                        return response
                    else:
                        return f"❌ No shipping data found for '{country}'"
                else:
                    return "❌ Please specify a destination country"
            
            else:
                return """
❓ I can help with:
• Extension feasibility: "Can we extend batch LOT-12345678?"
• Inventory summary: "Show inventory for Study ABC"
• Shipping timelines: "Shipping timeline to Germany"

Please ask a specific question.
"""
        
        except Exception as e:
            return f"❌ Error processing query: {e}"
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []


def main():
    """Interactive chat loop"""
    print("\n" + "=" * 60)
    print("Scenario Strategist - Decision Support Agent")
    print("=" * 60 + "\n")
    
    if not config.validate():
        print("✗ Configuration validation failed. Please check your .env file.")
        return
    
    agent = ScenarioStrategistSimple()
    
    print("Type your questions below (or 'quit' to exit):\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if not user_input:
                continue
            
            response = agent.ask(user_input)
            print(f"\nAgent: {response}\n")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
