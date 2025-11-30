# Part 3: Edge Case Handling & Robust Error Recovery

## Overview

Production AI systems must gracefully handle data ambiguity, query failures, and unexpected scenarios. This section outlines comprehensive strategies for error handling and self-healing in the Clinical Supply Chain AI system.

---

## 1. Data Ambiguity Resolution

### 1.1 Scenario: Fuzzy Trial ID Matching

**Problem:** User asks for "Trial ABC", but database contains "Trial_ABC_v2", "ABC-2024", "trial-abc-phase3".

#### Solution 1: Fuzzy Matching with Confidence Scores

```python
from fuzzywuzzy import fuzz
from typing import List, Tuple

class FuzzyMatcher:
    def __init__(self, sql_tool: SQLQueryTool):
        self.sql_tool = sql_tool
    
    def find_trial_id(self, user_input: str, threshold: int = 80) -> List[Tuple[str, int]]:
        """
        Find trial IDs using fuzzy string matching.
        
        Args:
            user_input: User's trial identifier (e.g., "Trial ABC")
            threshold: Minimum confidence score (0-100)
            
        Returns:
            List of (trial_id, confidence_score) tuples
        """
        # Get all unique trial IDs from database
        query = """
        SELECT DISTINCT trial_id 
        FROM allocated_materials
        UNION
        SELECT DISTINCT trial_id 
        FROM enrollment_rate_report;
        """
        all_trials = self.sql_tool.execute_query(query)
        
        # Calculate fuzzy match scores
        matches = []
        for row in all_trials:
            trial_id = row['trial_id']
            
            # Try multiple matching strategies
            scores = [
                fuzz.ratio(user_input.lower(), trial_id.lower()),
                fuzz.partial_ratio(user_input.lower(), trial_id.lower()),
                fuzz.token_sort_ratio(user_input.lower(), trial_id.lower())
            ]
            max_score = max(scores)
            
            if max_score >= threshold:
                matches.append((trial_id, max_score))
        
        # Sort by confidence descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches


class TrialIDResolver:
    def __init__(self, fuzzy_matcher: FuzzyMatcher):
        self.matcher = fuzzy_matcher
    
    def resolve(self, user_input: str) -> str:
        """
        Resolve ambiguous trial ID with user confirmation.
        
        Returns: Exact trial_id or raises AmbiguityError
        """
        matches = self.matcher.find_trial_id(user_input)
        
        if len(matches) == 0:
            raise ValueError(f"No trial found matching '{user_input}'")
        
        elif len(matches) == 1:
            trial_id, confidence = matches[0]
            if confidence > 90:
                # High confidence - auto-select
                return trial_id
            else:
                # Medium confidence - confirm with user
                return self._ask_user_confirmation([trial_id])
        
        else:
            # Multiple matches - present options to user
            return self._ask_user_confirmation([m[0] for m in matches[:5]])
    
    def _ask_user_confirmation(self, options: List[str]) -> str:
        """
        Present options to user for selection.
        In production, this would integrate with chat UI.
        """
        message = "I found multiple trials. Did you mean:\n"
        for i, option in enumerate(options, 1):
            message += f"{i}. {option}\n"
        
        # In chatbot: return this message and await user response
        # For now, we'll return the first option with a note
        return {
            "status": "needs_clarification",
            "message": message,
            "options": options,
            "default": options[0]
        }
```

#### Solution 2: Semantic Search with Embeddings

For more sophisticated matching:

```python
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
import numpy as np

class SemanticTrialResolver:
    def __init__(self, sql_tool: SQLQueryTool):
        self.sql_tool = sql_tool
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = None
        self._build_index()
    
    def _build_index(self):
        """Build FAISS index of all trial IDs and metadata."""
        query = """
        SELECT 
            t.trial_id,
            t.trial_name,
            t.indication,
            t.phase
        FROM trials_metadata t;
        """
        trials = self.sql_tool.execute_query(query)
        
        # Create rich text descriptions for embedding
        texts = []
        metadatas = []
        for trial in trials:
            text = f"{trial['trial_id']} {trial['trial_name']} {trial['indication']} Phase {trial['phase']}"
            texts.append(text)
            metadatas.append(trial)
        
        self.vector_store = FAISS.from_texts(
            texts, 
            self.embeddings, 
            metadatas=metadatas
        )
    
    def resolve(self, user_input: str, top_k: int = 3) -> List[Dict]:
        """
        Use semantic similarity to find matching trials.
        
        Example:
            User: "the lung cancer study in phase 2"
            Returns: [TRIAL_LC_P2_001, ...]
        """
        results = self.vector_store.similarity_search_with_score(user_input, k=top_k)
        
        matches = []
        for doc, score in results:
            matches.append({
                "trial_id": doc.metadata['trial_id'],
                "trial_name": doc.metadata['trial_name'],
                "confidence": 1 - score  # Convert distance to similarity
            })
        
        return matches
```

#### Agent Integration

```python
TRIAL_RESOLUTION_PROMPT_ADDITION = """
## Handling Ambiguous Identifiers

When the user provides a trial ID, batch ID, or country name:

1. **First Attempt:** Try exact match in database
2. **If No Match:** Use fuzzy_match_tool to find similar identifiers
3. **If Multiple Matches:** Ask user to clarify:
   
   Response template:
   "I found multiple trials matching '{user_input}':
   1. {trial_id_1}
   2. {trial_id_2}
   
   Please specify which trial you're referring to, or provide more details."

4. **If No Matches:** Suggest closest alternatives:
   
   "I couldn't find a trial matching '{user_input}'. 
   Did you mean one of these?
   - {suggestion_1}
   - {suggestion_2}"

Never proceed with a query if you're uncertain about the identifier.
Always confirm before making critical decisions.
"""
```

---

### 1.2 Scenario: Column Name Variations

**Problem:** Different tables use inconsistent column names:
- `wh_lpn_number` vs `LPN` vs `lpn_id`
- `CountryCode` vs `country_code` vs `country`

#### Solution: Column Name Mapping Layer

```python
class ColumnNameNormalizer:
    """
    Normalize column name variations to standard names.
    """
    
    COLUMN_MAPPINGS = {
        # LPN variations
        'lpn': ['wh_lpn_number', 'LPN', 'lpn_id', 'lpn_number'],
        
        # Country variations
        'country_code': ['CountryCode', 'country_code', 'country', 'Country'],
        
        # Batch variations
        'batch_id': ['batch_id', 'BatchID', 'batch_number', 'lot_number'],
        
        # Material variations
        'material_id': ['material_id', 'MaterialID', 'product_id', 'drug_code'],
        
        # Date variations
        'expiry_date': ['expiry_date', 'ExpiryDate', 'expiration_date', 'exp_date']
    }
    
    def __init__(self, sql_tool: SQLQueryTool):
        self.sql_tool = sql_tool
        self.schema_cache = {}
    
    def get_actual_column_name(self, table_name: str, standard_name: str) -> str:
        """
        Get the actual column name used in the table.
        
        Args:
            table_name: Database table name
            standard_name: Our standard column name (e.g., 'country_code')
            
        Returns:
            Actual column name in that specific table
        """
        # Cache table schema
        if table_name not in self.schema_cache:
            self.schema_cache[table_name] = self._get_table_columns(table_name)
        
        actual_columns = self.schema_cache[table_name]
        possible_names = self.COLUMN_MAPPINGS.get(standard_name, [standard_name])
        
        # Check each possible variation
        for possible in possible_names:
            if possible in actual_columns:
                return possible
        
        # Fallback: case-insensitive match
        for actual in actual_columns:
            if actual.lower() == standard_name.lower():
                return actual
        
        raise ValueError(
            f"Column '{standard_name}' not found in table '{table_name}'. "
            f"Available columns: {actual_columns}"
        )
    
    def _get_table_columns(self, table_name: str) -> List[str]:
        """Query PostgreSQL information_schema for column names."""
        query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %(table)s;
        """
        results = self.sql_tool.execute_query(query, {'table': table_name})
        return [row['column_name'] for row in results]
    
    def normalize_query(self, query_template: str, table_name: str) -> str:
        """
        Replace standard column names with actual table-specific names.
        
        Example:
            Input:  "SELECT country_code, batch_id FROM allocated_materials"
            Output: "SELECT CountryCode, batch_number FROM allocated_materials"
        """
        normalized = query_template
        
        for standard_name in self.COLUMN_MAPPINGS.keys():
            try:
                actual_name = self.get_actual_column_name(table_name, standard_name)
                # Replace with case-sensitive actual name
                normalized = normalized.replace(f"{standard_name}", actual_name)
            except ValueError:
                # Column doesn't exist in this table - skip
                continue
        
        return normalized
```

#### Usage in Agents

```python
class RobustSQLTool:
    def __init__(self, sql_tool: SQLQueryTool):
        self.sql_tool = sql_tool
        self.normalizer = ColumnNameNormalizer(sql_tool)
    
    def execute_normalized_query(self, query_template: str, table_name: str) -> List[Dict]:
        """
        Execute query with automatic column name normalization.
        """
        try:
            # Normalize column names
            actual_query = self.normalizer.normalize_query(query_template, table_name)
            
            # Execute
            return self.sql_tool.execute_query(actual_query)
        
        except Exception as e:
            # If normalization fails, try original query
            return self.sql_tool.execute_query(query_template)
```

---

## 2. SQL Query Error Recovery (Self-Healing)

### 2.1 Scenario: Agent Generates Invalid SQL

**Problem:** LLM generates SQL with syntax errors or references non-existent columns.

#### Solution: Multi-Layer Error Recovery

```python
from typing import Optional
import re

class SelfHealingSQLAgent:
    """
    SQL agent with automatic error detection and correction.
    """
    
    def __init__(self, sql_tool: SQLQueryTool, llm: ChatOpenAI):
        self.sql_tool = sql_tool
        self.llm = llm
        self.max_retries = 3
    
    def execute_with_healing(self, query: str, context: str) -> List[Dict]:
        """
        Execute SQL with automatic error recovery.
        
        Args:
            query: SQL query to execute
            context: Original user request for context
            
        Returns:
            Query results
        """
        for attempt in range(self.max_retries):
            try:
                # Attempt execution
                results = self.sql_tool.execute_query(query)
                return results
            
            except psycopg2.Error as e:
                error_message = str(e)
                
                # Analyze error type
                if "syntax error" in error_message.lower():
                    query = self._fix_syntax_error(query, error_message)
                
                elif "column" in error_message.lower() and "does not exist" in error_message.lower():
                    query = self._fix_column_error(query, error_message)
                
                elif "relation" in error_message.lower() and "does not exist" in error_message.lower():
                    query = self._fix_table_error(query, error_message)
                
                else:
                    # Unknown error - ask LLM to regenerate
                    query = self._regenerate_with_llm(query, error_message, context)
                
                # Log the correction attempt
                print(f"[Attempt {attempt + 1}] Correcting SQL error: {error_message}")
                print(f"[Attempt {attempt + 1}] New query: {query}")
        
        # All retries exhausted
        raise RuntimeError(f"Failed to execute query after {self.max_retries} attempts")
    
    def _fix_syntax_error(self, query: str, error_msg: str) -> str:
        """Fix common syntax errors."""
        
        # Common fix 1: Missing closing parenthesis
        open_parens = query.count('(')
        close_parens = query.count(')')
        if open_parens > close_parens:
            query += ')' * (open_parens - close_parens)
        
        # Common fix 2: Missing semicolon
        if not query.strip().endswith(';'):
            query += ';'
        
        # Common fix 3: Double semicolons
        query = query.replace(';;', ';')
        
        return query
    
    def _fix_column_error(self, query: str, error_msg: str) -> str:
        """Fix column name errors using schema inspection."""
        
        # Extract the problematic column name from error
        # Example error: 'column "wrong_name" does not exist'
        match = re.search(r'column "([^"]+)" does not exist', error_msg)
        if not match:
            return query
        
        wrong_column = match.group(1)
        
        # Extract table name from query
        table_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if not table_match:
            return query
        
        table_name = table_match.group(1)
        
        # Get actual columns from table
        normalizer = ColumnNameNormalizer(self.sql_tool)
        try:
            actual_columns = normalizer._get_table_columns(table_name)
            
            # Find closest match using fuzzy matching
            from fuzzywuzzy import process
            best_match, score = process.extractOne(wrong_column, actual_columns)
            
            if score > 70:  # Reasonable confidence
                # Replace wrong column with correct one
                query = query.replace(wrong_column, best_match)
                return query
        
        except Exception:
            pass
        
        return query
    
    def _fix_table_error(self, query: str, error_msg: str) -> str:
        """Fix table name errors."""
        
        # Extract wrong table name
        match = re.search(r'relation "([^"]+)" does not exist', error_msg)
        if not match:
            return query
        
        wrong_table = match.group(1)
        
        # Get list of all tables
        all_tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public';
        """
        tables = self.sql_tool.execute_query(all_tables_query)
        table_names = [t['table_name'] for t in tables]
        
        # Find closest match
        from fuzzywuzzy import process
        best_match, score = process.extractOne(wrong_table, table_names)
        
        if score > 70:
            query = query.replace(wrong_table, best_match)
        
        return query
    
    def _regenerate_with_llm(self, failed_query: str, error_msg: str, context: str) -> str:
        """
        Ask LLM to regenerate query given the error.
        """
        correction_prompt = f"""
The following SQL query failed with an error:

QUERY:
{failed_query}

ERROR:
{error_msg}

ORIGINAL REQUEST:
{context}

Please generate a corrected SQL query that:
1. Fixes the error mentioned above
2. Still answers the original request
3. Uses only valid PostgreSQL syntax

Return ONLY the corrected SQL query, no explanation.
"""
        
        response = self.llm.predict(correction_prompt)
        
        # Extract SQL from response (in case LLM adds extra text)
        sql_pattern = r'```sql\n(.*?)\n```'
        match = re.search(sql_pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return response.strip()
```

#### Integration with Agents

```python
# Add to agent's tool set
tools = [
    Tool(
        name="run_sql_query",
        func=self_healing_sql.execute_with_healing,
        description="Execute SQL with automatic error correction"
    )
]
```

---

### 2.2 Query Validation Before Execution

**Prevention is better than cure:**

```python
class SQLValidator:
    """
    Validate SQL queries before execution.
    """
    
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 
        'INSERT', 'UPDATE', 'GRANT', 'REVOKE'
    ]
    
    def validate(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query for safety and correctness.
        
        Returns:
            (is_valid, error_message)
        """
        query_upper = query.upper()
        
        # Check 1: Read-only enforcement
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False, f"Forbidden keyword detected: {keyword}. Only SELECT queries allowed."
        
        # Check 2: Must start with SELECT or WITH
        if not (query_upper.strip().startswith('SELECT') or query_upper.strip().startswith('WITH')):
            return False, "Query must start with SELECT or WITH"
        
        # Check 3: Balanced parentheses
        if query.count('(') != query.count(')'):
            return False, "Unbalanced parentheses"
        
        # Check 4: No multiple statements (SQL injection prevention)
        if ';' in query[:-1]:  # Allow single trailing semicolon
            return False, "Multiple statements not allowed"
        
        # Check 5: No comments (potential injection vector)
        if '--' in query or '/*' in query:
            return False, "SQL comments not allowed"
        
        return True, None
    
    def explain_plan(self, query: str, sql_tool: SQLQueryTool) -> Dict:
        """
        Get query execution plan without running the query.
        Useful for detecting expensive operations.
        """
        explain_query = f"EXPLAIN (FORMAT JSON) {query}"
        result = sql_tool.execute_query(explain_query)
        return result[0]
```

---

## 3. Data Quality Issues

### 3.1 Scenario: Missing or NULL Data

```python
class DataQualityChecker:
    """
    Detect and handle data quality issues.
    """
    
    def check_enrollment_data_completeness(
        self, 
        trial_id: str, 
        sql_tool: SQLQueryTool
    ) -> Dict:
        """
        Check if enrollment data is sufficient for forecasting.
        """
        query = """
        SELECT 
            COUNT(*) as total_weeks,
            COUNT(CASE WHEN patients_enrolled IS NULL THEN 1 END) as null_weeks,
            MIN(enrollment_date) as first_date,
            MAX(enrollment_date) as last_date,
            AVG(patients_enrolled) as avg_enrollment
        FROM enrollment_rate_report
        WHERE trial_id = %(trial_id)s
        AND enrollment_date >= CURRENT_DATE - INTERVAL '8 weeks';
        """
        
        result = sql_tool.execute_query(query, {'trial_id': trial_id})[0]
        
        issues = []
        
        if result['total_weeks'] < 3:
            issues.append({
                "severity": "HIGH",
                "message": f"Insufficient data: only {result['total_weeks']} weeks available"
            })
        
        if result['null_weeks'] > 0:
            issues.append({
                "severity": "MEDIUM",
                "message": f"{result['null_weeks']} weeks have missing enrollment data"
            })
        
        if result['avg_enrollment'] is None or result['avg_enrollment'] == 0:
            issues.append({
                "severity": "CRITICAL",
                "message": "No enrollment activity detected"
            })
        
        return {
            "trial_id": trial_id,
            "data_quality": "GOOD" if len(issues) == 0 else "POOR",
            "issues": issues,
            "metadata": result
        }
    
    def handle_missing_data(self, data_quality_report: Dict) -> str:
        """
        Generate appropriate response when data is insufficient.
        """
        if data_quality_report['data_quality'] == 'POOR':
            messages = [
                f"⚠️ Data Quality Issue for {data_quality_report['trial_id']}:",
                ""
            ]
            
            for issue in data_quality_report['issues']:
                messages.append(f"- [{issue['severity']}] {issue['message']}")
            
            messages.append("")
            messages.append("Recommendation: Please verify data completeness before proceeding.")
            
            return "\n".join(messages)
        
        return "Data quality check passed"
```

---

### 3.2 Scenario: Stale Data

```python
class DataFreshnessChecker:
    """
    Monitor data freshness and alert when data is stale.
    """
    
    def check_inventory_freshness(self, sql_tool: SQLQueryTool) -> Dict:
        """
        Check when inventory data was last updated.
        """
        query = """
        SELECT 
            MAX(last_updated) as most_recent_update,
            EXTRACT(HOUR FROM (CURRENT_TIMESTAMP - MAX(last_updated))) as hours_ago
        FROM available_inventory_report;
        """
        
        result = sql_tool.execute_query(query)[0]
        hours_ago = float(result['hours_ago'])
        
        if hours_ago > 24:
            return {
                "status": "STALE",
                "message": f"⚠️ Inventory data is {hours_ago:.1f} hours old. Results may be outdated.",
                "last_update": result['most_recent_update']
            }
        elif hours_ago > 12:
            return {
                "status": "AGING",
                "message": f"ℹ️ Inventory data is {hours_ago:.1f} hours old.",
                "last_update": result['most_recent_update']
            }
        else:
            return {
                "status": "FRESH",
                "message": "✓ Inventory data is current",
                "last_update": result['most_recent_update']
            }
```

---

## 4. Graceful Degradation

When complete data is unavailable, provide partial answers:

```python
class GracefulDegradationHandler:
    """
    Provide best-effort answers when data is incomplete.
    """
    
    def generate_partial_response(
        self,
        requested_data: str,
        available_data: Dict,
        missing_data: List[str]
    ) -> str:
        """
        Create transparent response about data limitations.
        """
        response = [
            f"I was able to retrieve the following information about {requested_data}:",
            "",
            "✓ Available data:",
        ]
        
        for key, value in available_data.items():
            response.append(f"  - {key}: {value}")
        
        response.extend([
            "",
            "⚠️ Unable to retrieve:",
        ])
        
        for missing in missing_data:
            response.append(f"  - {missing} (data not available in system)")
        
        response.extend([
            "",
            "Recommendation: Decisions should consider these data gaps."
        ])
        
        return "\n".join(response)

# Example usage in agent
if regulatory_data is None:
    return graceful_handler.generate_partial_response(
        requested_data="Batch #123 extension feasibility",
        available_data={
            "Technical Check": "✓ Previous re-evaluation successful",
            "Logistical Check": "✓ Sufficient time (21 days)"
        },
        missing_data=[
            "Regulatory approval status (RIM table empty for this country)",
            "Country-specific requirements"
        ]
    )
```

---

## 5. Monitoring & Logging for Production

```python
import logging
from datetime import datetime
import json

class AgentMonitor:
    """
    Comprehensive logging and monitoring for agent behavior.
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(agent_name)
        self.execution_log = []
    
    def log_query_execution(
        self,
        query: str,
        execution_time_ms: float,
        rows_returned: int,
        success: bool,
        error: Optional[str] = None
    ):
        """Log all SQL query executions."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "query": query[:200],  # Truncate long queries
            "execution_time_ms": execution_time_ms,
            "rows_returned": rows_returned,
            "success": success,
            "error": error
        }
        
        self.execution_log.append(log_entry)
        
        if success:
            self.logger.info(f"Query executed successfully: {rows_returned} rows in {execution_time_ms}ms")
        else:
            self.logger.error(f"Query failed: {error}")
    
    def log_agent_decision(
        self,
        user_query: str,
        agent_response: str,
        evidence_tables: List[str],
        confidence_score: float
    ):
        """Log agent's decision-making process."""
        decision_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "user_query": user_query,
            "agent_response": agent_response[:500],
            "evidence_tables": evidence_tables,
            "confidence_score": confidence_score
        }
        
        self.logger.info(f"Decision made with confidence {confidence_score:.2f}")
        
        # Store for audit trail
        self.execution_log.append(decision_log)
    
    def export_audit_trail(self, filepath: str):
        """Export complete audit trail for compliance."""
        with open(filepath, 'w') as f:
            json.dump(self.execution_log, f, indent=2)
```

---

## 6. Circuit Breaker Pattern

Prevent cascading failures:

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """
    Implement circuit breaker pattern for database connections.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        """
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage
circuit_breaker = CircuitBreaker()

def execute_query_with_circuit_breaker(query: str):
    return circuit_breaker.call(sql_tool.execute_query, query)
```

---

## Summary: Edge Case Handling Strategies

| Edge Case | Detection Method | Resolution Strategy |
|-----------|------------------|---------------------|
| **Ambiguous IDs** | Fuzzy matching score < 90% | Present options to user for clarification |
| **Column name variations** | Schema inspection | Automatic normalization via mapping table |
| **Invalid SQL syntax** | Database error exception | Multi-layer correction: regex fixes → LLM regeneration |
| **Missing columns** | PostgreSQL error | Fuzzy match against actual schema |
| **Wrong table names** | Database error | Suggest closest match from information_schema |
| **Stale data** | Timestamp comparison | Display warning, continue with caveat |
| **Insufficient data** | Row count < threshold | Graceful degradation with partial answer |
| **Database connection failure** | Circuit breaker | Temporary rejection, automatic recovery |
| **Query timeout** | Execution time > threshold | Query simplification or result pagination |

---

This comprehensive edge case handling ensures the system remains robust and user-friendly in production environments.
