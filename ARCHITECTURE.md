# 🏗️ System Architecture

## Overview

The Clinical Supply Chain Control Tower is built using a **multi-agent architecture** that enables autonomous monitoring and intelligent decision support for pharmaceutical supply chains spanning 50+ countries.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interfaces                         │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Web Dashboard  │  │  REST API    │  │  CLI Tools     │  │
│  │  (HTML/CSS/JS)  │  │  (FastAPI)   │  │  (Python)      │  │
│  └────────┬────────┘  └──────┬───────┘  └────────┬───────┘  │
└───────────┼──────────────────┼──────────────────┼───────────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  • 15+ REST endpoints                                │    │
│  │  • WebSocket for real-time updates                  │    │
│  │  • Background task scheduling                        │    │
│  │  • Request validation (Pydantic)                     │    │
│  │  • OpenAPI documentation                             │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────▲──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
┌───────────▼────────────┐           ┌───────────▼────────────┐
│   Supply Watchdog      │           │  Scenario Strategist   │
│      Agent             │           │      Agent             │
│                        │           │                        │
│  • Autonomous          │           │  • Conversational AI   │
│  • Scheduled runs      │           │  • Natural language    │
│  • Expiry detection    │           │  • 3-step validation   │
│  • Shortfall forecast  │           │  • Evidence-based      │
│  • Alert generation    │           │  • Context awareness   │
└───────────┬────────────┘           └───────────┬────────────┘
            │                                     │
            └──────────────────┬──────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                       Tools Layer                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  • SQL Query Tool (self-healing)                     │    │
│  │  • Risk Calculator (expiry/shortfall)                │    │
│  │  • Validation Tool (data quality)                    │    │
│  │  • Fuzzy Matching (ambiguous IDs)                    │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────▲──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                   PostgreSQL Database                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  40+ Tables:                                         │    │
│  │  • available_inventory_report (549 rows)             │    │
│  │  • allocated_materials_to_orders (214 rows)          │    │
│  │  • enrollment_rate_report (214 rows)                 │    │
│  │  • country_level_enrollment (104 rows)               │    │
│  │  • re_evaluation (212 rows)                          │    │
│  │  • regulatory_information_management (58 rows)       │    │
│  │  • material_country_requirements (313 rows)          │    │
│  │  • ip_shipping_timelines (214 rows)                  │    │
│  │  • distribution_order_report (214 rows)              │    │
│  │  • ... and 31 more tables                            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Layer

#### Web Dashboard
- **Technology**: HTML5, TailwindCSS, Chart.js
- **Features**:
  - Real-time KPI monitoring
  - Interactive risk distribution charts
  - Expiring inventory table with color-coded alerts
  - Embedded AI chat interface
  - Auto-refresh every 60 seconds
- **Design**: Modern glass-effect with gradient backgrounds

### 2. API Layer (FastAPI)

#### Key Endpoints
```python
GET  /api/dashboard              # Complete dashboard data
GET  /api/inventory/expiring     # Filter batches by expiry
GET  /api/enrollment/summary     # Enrollment statistics
GET  /api/alerts/latest          # Recent monitoring alerts
POST /api/monitoring/run         # Trigger Supply Watchdog
POST /api/chat                   # Chat with Scenario Strategist
WS   /ws/monitoring              # Real-time updates
```

#### Features
- Async/await for high performance
- Pydantic models for request validation
- Background task scheduling
- CORS configuration
- OpenAPI/Swagger documentation
- Error handling and logging

### 3. Agent Layer

#### Supply Watchdog Agent (Workflow A)

**Purpose**: Autonomous monitoring for proactive risk detection

**Capabilities**:
1. **Expiry Detection**
   - Scans 549+ inventory batches
   - 3-tier categorization (Critical: 30d, High: 60d, Medium: 90d)
   - Cross-references with allocation status

2. **Shortfall Prediction**
   - 8-week demand forecasting
   - Enrollment velocity analysis
   - Inventory vs. demand gap calculation
   - Country-specific lead time consideration

3. **Alert Generation**
   - Structured JSON format
   - Severity levels (critical/high/medium)
   - Actionable recommendations
   - SMTP-ready for email notifications

**Execution**: Scheduled via cron or on-demand via API

#### Scenario Strategist Agent (Workflow B)

**Purpose**: Conversational AI for complex decision support

**Capabilities**:
1. **Natural Language Understanding**
   - Parses user queries
   - Extracts entities (batch IDs, countries, studies)
   - Handles ambiguous references

2. **3-Step Validation**
   - **Technical**: Data availability, batch status
   - **Regulatory**: Country regulations, shelf-life rules
   - **Logistical**: Shipping timelines, feasibility

3. **Evidence-Based Responses**
   - Cites specific database tables
   - References historical data
   - Provides confidence scores
   - Maintains conversation context

**Execution**: Interactive via CLI or embedded in web dashboard

### 4. Tools Layer

#### SQL Query Tool
- Parameterized queries (injection-proof)
- Self-healing with 3-layer error recovery
- Dynamic schema retrieval
- Connection pooling

#### Risk Calculator
- Expiry risk scoring algorithm
- Shortfall prediction model
- Enrollment velocity analysis
- Statistical forecasting

#### Validation Tool
- Data quality checks
- Schema validation
- Constraint verification
- Integrity enforcement

#### Fuzzy Matching
- Levenshtein distance for ambiguous IDs
- Semantic similarity for text matching
- Confidence scoring
- Multiple match resolution

### 5. Database Layer (PostgreSQL)

#### Schema Design

**40+ interconnected tables** organized by domain:

**Inventory Domain**
- `available_inventory_report` - Current stock levels
- `allocated_materials_to_orders` - Reserved batches
- `material_country_requirements` - Regulatory constraints

**Demand Domain**
- `enrollment_rate_report` - Patient enrollment rates
- `country_level_enrollment_report` - Country forecasts
- `distribution_order_report` - Order tracking

**Regulatory Domain**
- `re_evaluation` - Shelf-life extensions
- `regulatory_information_management` - Submissions
- `material_country_requirements` - Country rules

**Logistics Domain**
- `ip_shipping_timelines_report` - Lead times
- `distribution_order_report` - Shipping status

#### Data Volume
- **Total Tables**: 40+
- **Total Rows**: 2,000+
- **Key Table**: `available_inventory_report` (549 rows)

## Data Flow

### Workflow A: Daily Monitoring

```
1. Cron Trigger (6 AM daily)
   ↓
2. Supply Watchdog Agent starts
   ↓
3. Query inventory from PostgreSQL
   ↓
4. Calculate expiry risks
   ↓
5. Query enrollment data
   ↓
6. Forecast shortfalls (8 weeks)
   ↓
7. Generate structured alerts (JSON)
   ↓
8. Save to files + Send emails
   ↓
9. Update dashboard via WebSocket
```

### Workflow B: Interactive Chat

```
1. User enters query in dashboard
   ↓
2. POST /api/chat request
   ↓
3. Scenario Strategist Agent receives query
   ↓
4. Extract entities (batch, country, study)
   ↓
5. Fuzzy matching for ambiguous IDs
   ↓
6. Query relevant database tables
   ↓
7. Technical validation (data check)
   ↓
8. Regulatory validation (rules check)
   ↓
9. Logistical validation (feasibility)
   ↓
10. Generate evidence-based response
   ↓
11. Return to user with citations
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML5, TailwindCSS, Chart.js | User interface |
| **API** | FastAPI 0.108+ | REST/WebSocket server |
| **Backend** | Python 3.11+ | Business logic |
| **Database** | PostgreSQL 14+ | Data persistence |
| **Data Processing** | Pandas, NumPy | Analytics |
| **ORM** | SQLAlchemy | Database abstraction |
| **Validation** | Pydantic | Data validation |

## Scalability Considerations

### Horizontal Scaling
- **API Layer**: Deploy multiple FastAPI instances behind load balancer
- **Database**: PostgreSQL read replicas for query load distribution
- **Agents**: Distribute monitoring across multiple workers

### Vertical Scaling
- **Database**: Increase PostgreSQL resources for larger datasets
- **API**: Async operations minimize resource per request
- **Caching**: Redis for frequently accessed data

### Performance Optimization
- Database indexing on frequently queried columns
- Connection pooling to minimize overhead
- Background tasks for long-running operations
- WebSocket for real-time updates (no polling)

## Security

### Authentication
- API key authentication for endpoints
- Role-based access control (RBAC)
- Session management

### Data Protection
- Parameterized SQL queries (injection-proof)
- Input validation with Pydantic
- Environment variable for credentials
- HTTPS for API communication

### Compliance
- HIPAA considerations for patient data
- Audit logging for all actions
- Data retention policies

## Monitoring & Observability

### Logging
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized log aggregation

### Metrics
- API response times
- Database query performance
- Agent execution duration
- Alert generation rates

### Health Checks
- `/health` endpoint for API status
- Database connection monitoring
- Background task status

## Deployment

### Development
```bash
python scripts/setup_complete.py
python api/main.py
```

### Production
- Docker containerization
- Kubernetes orchestration
- CI/CD pipeline
- Database migrations

## Future Enhancements

1. **Machine Learning**
   - Demand forecasting with LSTM/Prophet
   - Anomaly detection for unusual patterns
   - Automated root cause analysis

2. **Additional Agents**
   - Procurement Agent (automated ordering)
   - Compliance Agent (regulatory monitoring)
   - Analytics Agent (business intelligence)

3. **Integrations**
   - ERP system integration
   - Email notification system
   - Slack/Teams alerts
   - Mobile app

4. **Advanced Features**
   - What-if scenario simulation
   - Multi-tenancy for multiple pharma companies
   - Advanced analytics dashboard
   - Predictive maintenance

---

**Designed and Implemented by Rajan Mishra**  
*AI/ML Engineer | Full-Stack Developer*
