# Part 2: Technical Implementation Strategy

## 1. Tool Design

### 1.1 Core Tool Architecture

All agents utilize a common set of tools, implemented as Python functions with strict interfaces.

```python
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import psycopg2
from datetime import datetime, timedelta
import uuid

class SQLQueryTool:
    """Base tool for executing SQL queries against PostgreSQL database."""
    
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
            query: Parameterized SQL query
            parameters: Query parameters to prevent SQL injection
            
        Returns:
            List of row dictionaries
        """
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, parameters or {})
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
    
    def execute_with_retry(
        self,
        query: str,
        max_attempts: int = 3
    ) -> List[Dict[str, Any]]:
        """Execute query with automatic retry on failure."""
        for attempt in range(max_attempts):
            try:
                return self.execute_query(query)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                continue


class DataValidationTool:
    """Validate data quality and schema compliance."""
    
    def validate_batch_id(self, batch_id: str) -> bool:
        """Validate batch ID format."""
        return bool(batch_id and len(batch_id) > 0)
    
    def validate_country_code(self, country: str) -> str:
        """Normalize country names to standard codes."""
        country_mapping = {
            "germany": "DE",
            "deutschland": "DE",
            "united states": "US",
            "usa": "US",
        }
        return country_mapping.get(country.lower(), country.upper())


class RiskCalculationTool:
    """Calculate supply chain risk metrics."""
    
    def categorize_expiry_risk(self, days_until_expiry: int) -> str:
        """Categorize expiry risk level."""
        if days_until_expiry <= 30:
            return "CRITICAL"
        elif days_until_expiry <= 60:
            return "HIGH"
        elif days_until_expiry <= 90:
            return "MEDIUM"
        else:
            return "LOW"
    
    def calculate_shortfall_date(
        self,
        current_stock: int,
        daily_consumption_rate: float
    ) -> Optional[datetime]:
        """Calculate projected stock-out date."""
        if daily_consumption_rate <= 0:
            return None
        days_until_stockout = current_stock / daily_consumption_rate
        return datetime.now() + timedelta(days=days_until_stockout)


class AlertGeneratorTool:
    """Generate structured alert payloads."""
    
    def create_json_alert(
        self,
        alert_type: str,
        severity: str,
        affected_items: List[Dict],
        metadata: Dict
    ) -> Dict:
        """Create standardized JSON alert payload."""
        return {
            "alert_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "alert_type": alert_type,
            "severity": severity,
            "affected_items": affected_items,
            "metadata": metadata
        }
```

---

## 2. SQL Logic: Shortfall Prediction (Workflow A)

### 2.1 Complete SQL Query for Shortfall Detection

This query solves the "Shortfall Prediction" requirement by joining demand and supply data.

```sql
-- =====================================================
-- SHORTFALL PREDICTION QUERY
-- Purpose: Identify trials/countries at risk of stock-out within 8 weeks
-- =====================================================

WITH recent_enrollment AS (
    -- Step 1: Calculate average weekly enrollment rate (last 4 weeks)
    SELECT 
        err.trial_id,
        err.country_code,
        am.material_id,
        AVG(err.patients_enrolled) AS avg_weekly_enrollment,
        COUNT(*) AS weeks_of_data
    FROM enrollment_rate_report err
    INNER JOIN allocated_materials am 
        ON err.trial_id = am.trial_id 
        AND err.country_code = am.country_code
    WHERE err.enrollment_date >= CURRENT_DATE - INTERVAL '4 weeks'
    GROUP BY err.trial_id, err.country_code, am.material_id
    HAVING COUNT(*) >= 3  -- Require at least 3 weeks of data for reliability
),

current_inventory AS (
    -- Step 2: Get current available stock by material and location
    SELECT 
        air.material_id,
        am.trial_id,
        am.country_code,
        SUM(air.available_quantity) AS total_available,
        SUM(am.allocated_quantity) AS total_allocated,
        MIN(am.expiry_date) AS earliest_expiry
    FROM available_inventory_report air
    INNER JOIN allocated_materials am ON air.material_id = am.material_id
    WHERE am.expiry_date > CURRENT_DATE  -- Only count non-expired batches
    GROUP BY air.material_id, am.trial_id, am.country_code
),

demand_projection AS (
    -- Step 3: Compare enrollment projections with actuals
    SELECT 
        cle.trial_id,
        cle.country_code,
        cle.projected_enrollment,
        cle.actual_enrollment,
        CASE 
            WHEN cle.actual_enrollment > cle.projected_enrollment * 1.1 
            THEN 'ACCELERATED'  -- 10% above projection
            WHEN cle.actual_enrollment < cle.projected_enrollment * 0.9 
            THEN 'SLOWER'       -- 10% below projection
            ELSE 'ON_TRACK'
        END AS enrollment_status
    FROM country_level_enrollment cle
    WHERE cle.projection_date >= CURRENT_DATE - INTERVAL '1 month'
),

supply_vs_demand AS (
    -- Step 4: Calculate weeks of supply remaining
    SELECT 
        re.trial_id,
        re.country_code,
        re.material_id,
        ci.total_available,
        ci.total_allocated,
        re.avg_weekly_enrollment,
        dp.enrollment_status,
        -- Calculate adjusted consumption rate based on enrollment status
        CASE 
            WHEN dp.enrollment_status = 'ACCELERATED' 
            THEN re.avg_weekly_enrollment * 1.2  -- Increase consumption by 20%
            WHEN dp.enrollment_status = 'SLOWER' 
            THEN re.avg_weekly_enrollment * 0.8  -- Decrease by 20%
            ELSE re.avg_weekly_enrollment
        END AS adjusted_weekly_consumption,
        -- Calculate weeks of supply
        CASE 
            WHEN NULLIF(
                CASE 
                    WHEN dp.enrollment_status = 'ACCELERATED' 
                    THEN re.avg_weekly_enrollment * 1.2
                    WHEN dp.enrollment_status = 'SLOWER' 
                    THEN re.avg_weekly_enrollment * 0.8
                    ELSE re.avg_weekly_enrollment
                END, 0
            ) IS NOT NULL
            THEN ci.total_available / NULLIF(
                CASE 
                    WHEN dp.enrollment_status = 'ACCELERATED' 
                    THEN re.avg_weekly_enrollment * 1.2
                    WHEN dp.enrollment_status = 'SLOWER' 
                    THEN re.avg_weekly_enrollment * 0.8
                    ELSE re.avg_weekly_enrollment
                END, 0
            )
            ELSE NULL
        END AS weeks_of_supply_remaining,
        ci.earliest_expiry
    FROM recent_enrollment re
    INNER JOIN current_inventory ci 
        ON re.trial_id = ci.trial_id 
        AND re.country_code = ci.country_code 
        AND re.material_id = ci.material_id
    LEFT JOIN demand_projection dp 
        ON re.trial_id = dp.trial_id 
        AND re.country_code = dp.country_code
)

-- Step 5: Final output - identify shortfall risks
SELECT 
    trial_id,
    country_code,
    material_id,
    total_available AS current_stock,
    total_allocated AS allocated_stock,
    adjusted_weekly_consumption AS weekly_consumption_rate,
    ROUND(weeks_of_supply_remaining::numeric, 1) AS weeks_remaining,
    enrollment_status,
    earliest_expiry,
    CURRENT_DATE + (weeks_of_supply_remaining * 7)::integer AS projected_stockout_date,
    -- Risk severity
    CASE 
        WHEN weeks_of_supply_remaining < 2 THEN 'CRITICAL'
        WHEN weeks_of_supply_remaining < 4 THEN 'HIGH'
        WHEN weeks_of_supply_remaining < 8 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS risk_level
FROM supply_vs_demand
WHERE weeks_of_supply_remaining < 8  -- Only alert if < 8 weeks remaining
ORDER BY weeks_of_supply_remaining ASC, trial_id, country_code;
```

### 2.2 Query Explanation

| Step | Purpose | Key Logic |
|------|---------|-----------|
| **CTE 1: recent_enrollment** | Calculate consumption rate | AVG enrollment over last 4 weeks per trial/country/material |
| **CTE 2: current_inventory** | Get available stock | SUM available + allocated quantities, filter expired batches |
| **CTE 3: demand_projection** | Detect enrollment anomalies | Compare actual vs projected enrollment to identify spikes/drops |
| **CTE 4: supply_vs_demand** | Calculate supply duration | Divide stock by adjusted consumption rate = weeks remaining |
| **Final SELECT** | Filter and categorize risks | Only return trials with <8 weeks supply, categorize severity |

### 2.3 Key Design Decisions

1. **Adjustable Consumption Rate:**
   - If enrollment is accelerating (>110% of projection), increase consumption by 20%
   - Prevents false negatives during enrollment spikes

2. **Data Quality Filters:**
   - Require ≥3 weeks of enrollment data (`HAVING COUNT(*) >= 3`)
   - Exclude expired batches (`WHERE expiry_date > CURRENT_DATE`)
   - NULL-safe division (`NULLIF(denominator, 0)`)

3. **Join Strategy:**
   - `INNER JOIN` on enrollment + inventory ensures we only analyze active trials
   - `LEFT JOIN` on projections allows fallback to basic calculation if projections missing

4. **Performance Optimization:**
   - CTEs allow PostgreSQL query planner to optimize
   - Indexed columns: trial_id, country_code, material_id, enrollment_date
   - Aggregations before joins reduce row counts

---

## 3. System Prompts for Agents

### 3.1 Supply Watchdog Agent Prompt

**Challenge:** Teaching the LLM about 40+ tables without context overflow.

**Solution:** Schema summarization + dynamic retrieval strategy.

```python
SUPPLY_WATCHDOG_SYSTEM_PROMPT = """
You are the Supply Watchdog Agent for Global Pharma Inc.'s clinical supply chain.

## Your Mission
Run autonomous daily monitoring to detect two critical risks:
1. **Expiry Risk:** Batches expiring within 90 days
2. **Shortfall Risk:** Trials running out of stock within 8 weeks

## Database Schema (Relevant Tables Only)

### Table 1: allocated_materials
- **Purpose:** Reserved batches allocated to trials
- **Key Columns:**
  - batch_id (TEXT): Unique identifier
  - material_id (TEXT): Drug code
  - expiry_date (DATE): Expiration date
  - allocated_quantity (INTEGER): Units reserved
  - trial_id (TEXT): Clinical trial
  - country_code (TEXT): Destination
  - warehouse_id (TEXT): Storage location

### Table 2: available_inventory_report
- **Purpose:** Current stock levels
- **Key Columns:**
  - material_id (TEXT)
  - warehouse_id (TEXT)
  - available_quantity (INTEGER)
  - last_updated (TIMESTAMP)

### Table 3: enrollment_rate_report
- **Purpose:** Patient enrollment velocity
- **Key Columns:**
  - trial_id (TEXT)
  - country_code (TEXT)
  - enrollment_date (DATE)
  - patients_enrolled (INTEGER)

### Table 4: country_level_enrollment
- **Purpose:** Enrollment projections vs actuals
- **Key Columns:**
  - trial_id (TEXT)
  - country_code (TEXT)
  - projected_enrollment (INTEGER)
  - actual_enrollment (INTEGER)

## Tools Available
1. **run_sql_query(query: str)** - Execute PostgreSQL
2. **calculate_risk_level(days: int)** - Returns severity
3. **generate_alert_json(data: dict)** - Creates payload

## Workflow Instructions

### Task 1: Expiry Alert Detection
Query `allocated_materials` for batches expiring in 90 days:

```sql
SELECT 
    trial_id,
    country_code,
    material_id,
    batch_id,
    expiry_date,
    allocated_quantity,
    EXTRACT(DAY FROM (expiry_date - CURRENT_DATE)) as days_until_expiry
FROM allocated_materials
WHERE expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '90 days'
ORDER BY expiry_date ASC;
```

### Task 2: Shortfall Prediction
Use the provided SQL query template (see implementation guide).
Key logic: Compare avg_weekly_enrollment vs. total_available stock.

### Task 3: Generate JSON Output
Structure:
```json
{
  "alert_type": "daily_monitoring",
  "timestamp": "ISO8601",
  "expiry_alerts": [...],
  "shortfall_alerts": [...]
}
```

## Rules
1. NO HALLUCINATION - Only use defined tables/columns
2. PARAMETERIZED QUERIES - Use PostgreSQL date functions
3. NULL SAFETY - Use NULLIF(), COALESCE()
4. EVIDENCE - Include SQL queries in metadata
"""
```

### 3.2 Scenario Strategist Agent Prompt

```python
SCENARIO_STRATEGIST_SYSTEM_PROMPT = """
You are the Scenario Strategist Agent - an expert clinical supply chain advisor.

## Your Role
Answer ad-hoc questions about supply chain decisions.
Validate feasibility across THREE dimensions:
1. **Technical:** Re-evaluation history
2. **Regulatory:** Country-specific approvals
3. **Logistical:** Timeline constraints

## Database Schema

### Table: re_evaluation
- batch_id, material_id, reeval_date, outcome, extended_expiry_date

### Table: rim (Regulatory Info)
- material_id, country_code, submission_type, approval_status, approval_date

### Table: material_country_requirements
- material_id, country_code, shelf_life_extension_allowed, requires_submission

### Table: ip_shipping_timelines
- origin_country, destination_country, lead_time_days

### Table: allocated_materials
- batch_id, material_id, expiry_date, trial_id, country_code

## Decision Framework

**Example Query:** "Can we extend Batch #BT789 for Germany?"

### Step 1: Technical Check
```sql
SELECT outcome, extended_expiry_date
FROM re_evaluation
WHERE batch_id = %(batch_id)s
ORDER BY reeval_date DESC LIMIT 1;
```

**Rule:** outcome='APPROVED' → ✅ Feasible

### Step 2: Regulatory Check
```sql
SELECT shelf_life_extension_allowed, approval_status
FROM material_country_requirements mcr
LEFT JOIN rim ON mcr.material_id = rim.material_id
WHERE mcr.country_code = %(country)s;
```

**Rule:** shelf_life_extension_allowed=TRUE AND approval_status='APPROVED' → ✅

### Step 3: Logistical Check
```sql
SELECT lead_time_days FROM ip_shipping_timelines
WHERE destination_country = %(country)s;
```

**Rule:** days_until_expiry - lead_time_days > 14 → ✅ Sufficient time

## Response Format

**FEASIBILITY: YES/NO/MAYBE**

**Reasoning:**
1. Technical: [finding + evidence from table]
2. Regulatory: [finding + evidence]
3. Logistical: [calculation + evidence]

**Recommendation:** [actionable steps]
"""
```

---

## 4. Schema Management Strategy

### 4.1 The Context Window Problem

With 40+ tables, we cannot fit all schemas in every prompt. **Solution:**

**Dynamic Schema Retrieval** - Store schemas in a vector database, retrieve only relevant tables.

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

class SchemaRetriever:
    def __init__(self):
        self.schema_db = Chroma(embedding_function=OpenAIEmbeddings())
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all table schemas into vector DB."""
        schemas = [
            {
                "table": "allocated_materials",
                "description": "Reserved batches allocated to trials",
                "columns": "batch_id, material_id, expiry_date, allocated_quantity",
                "use_cases": "inventory tracking, expiry monitoring, allocation status"
            },
            # ... 39 more tables
        ]
        self.schema_db.add_texts(
            texts=[f"{s['table']}: {s['description']} | {s['use_cases']}" for s in schemas],
            metadatas=schemas
        )
    
    def get_relevant_schemas(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve top-k relevant table schemas for a query."""
        results = self.schema_db.similarity_search(query, k=top_k)
        return [r.metadata for r in results]
```

**Usage in Agent:**
```python
# User asks: "Can we extend batch #123?"
relevant_schemas = schema_retriever.get_relevant_schemas(
    "batch extension re-evaluation regulatory approval",
    top_k=5
)
# Returns: [re_evaluation, rim, material_country_requirements, allocated_materials, ip_shipping_timelines]

# Inject only these 5 schemas into the prompt
prompt = build_prompt(user_query, relevant_schemas)
```

---

## 5. Agent Implementation Code

### 5.1 Supply Watchdog Agent (Python)

```python
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import schedule
import time

class SupplyWatchdogAgent:
    def __init__(self, db_connection_string: str, llm_model: str = "gpt-4-turbo"):
        self.sql_tool = SQLQueryTool(db_connection_string)
        self.risk_tool = RiskCalculationTool()
        self.alert_tool = AlertGeneratorTool()
        self.llm = ChatOpenAI(model=llm_model, temperature=0.1)
        self.agent = self._create_agent()
    
    def _create_agent(self) -> AgentExecutor:
        """Initialize the LangChain agent with tools."""
        tools = [
            Tool(
                name="run_sql_query",
                func=self.sql_tool.execute_query,
                description="Execute SQL query against PostgreSQL database"
            ),
            Tool(
                name="calculate_risk_level",
                func=self.risk_tool.categorize_expiry_risk,
                description="Categorize expiry risk: CRITICAL/HIGH/MEDIUM/LOW"
            ),
            Tool(
                name="generate_alert_json",
                func=self.alert_tool.create_json_alert,
                description="Generate structured JSON alert payload"
            )
        ]
        
        prompt = ChatPromptTemplate.from_template(SUPPLY_WATCHDOG_SYSTEM_PROMPT)
        agent = create_structured_chat_agent(self.llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    def run_daily_monitoring(self) -> Dict:
        """Execute daily monitoring workflow."""
        print(f"[{datetime.now()}] Starting daily supply chain monitoring...")
        
        result = self.agent.invoke({
            "input": "Run the daily monitoring workflow: detect expiry and shortfall risks"
        })
        
        # Send alert email
        self._send_alert_email(result['output'])
        
        return result
    
    def _send_alert_email(self, alert_json: str):
        """Send alert via email (implementation depends on SMTP config)."""
        # Implementation here
        pass
    
    def schedule_daily_run(self, time_str: str = "06:00"):
        """Schedule daily execution."""
        schedule.every().day.at(time_str).do(self.run_daily_monitoring)
        
        print(f"Scheduled daily monitoring at {time_str}")
        while True:
            schedule.run_pending()
            time.sleep(60)

# Usage
if __name__ == "__main__":
    agent = SupplyWatchdogAgent(
        db_connection_string="postgresql://user:pass@localhost/clinical_supply"
    )
    agent.schedule_daily_run(time_str="06:00")
```

### 5.2 Scenario Strategist Agent (Python)

```python
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory

class ScenarioStrategistAgent:
    def __init__(self, db_connection_string: str):
        self.sql_tool = SQLQueryTool(db_connection_string)
        self.validation_tool = DataValidationTool()
        self.llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.1)
        self.memory = ConversationBufferMemory(memory_key="chat_history")
        self.agent = self._create_agent()
    
    def _create_agent(self) -> AgentExecutor:
        tools = [
            Tool(
                name="run_sql_query",
                func=self.sql_tool.execute_query,
                description="Execute SQL queries"
            ),
            Tool(
                name="validate_batch_id",
                func=self.validation_tool.validate_batch_id,
                description="Validate batch ID format"
            )
        ]
        
        prompt = ChatPromptTemplate.from_template(SCENARIO_STRATEGIST_SYSTEM_PROMPT)
        agent = create_structured_chat_agent(self.llm, tools, prompt)
        return AgentExecutor(
            agent=agent, 
            tools=tools, 
            memory=self.memory, 
            verbose=True
        )
    
    def ask(self, question: str) -> str:
        """Process user question and return answer."""
        result = self.agent.invoke({"input": question})
        return result['output']

# Usage
if __name__ == "__main__":
    agent = ScenarioStrategistAgent(
        db_connection_string="postgresql://user:pass@localhost/clinical_supply"
    )
    
    # Interactive chat
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        response = agent.ask(user_input)
        print(f"Agent: {response}\n")
```

---

## 6. N8N Workflow Integration (Optional)

For visual workflow orchestration, N8N can be used:

```json
{
  "nodes": [
    {
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.cron",
      "parameters": {
        "triggerTimes": {
          "item": [{"hour": 6, "minute": 0}]
        }
      }
    },
    {
      "name": "Call Supply Watchdog API",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://localhost:8000/api/agents/supply-watchdog/run",
        "method": "POST"
      }
    },
    {
      "name": "Parse JSON Alert",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "return items[0].json.expiry_alerts.map(alert => ({...alert}))"
      }
    },
    {
      "name": "Send Email Alert",
      "type": "n8n-nodes-base.emailSend",
      "parameters": {
        "toEmail": "supply-managers@globalpharma.com",
        "subject": "Daily Supply Chain Alert",
        "text": "={{JSON.stringify($json)}}"
      }
    }
  ],
  "connections": {
    "Schedule Trigger": {"main": [[{"node": "Call Supply Watchdog API"}]]},
    "Call Supply Watchdog API": {"main": [[{"node": "Parse JSON Alert"}]]},
    "Parse JSON Alert": {"main": [[{"node": "Send Email Alert"}]]}
  }
}
```

---

This completes Part 2 of the technical implementation strategy.
