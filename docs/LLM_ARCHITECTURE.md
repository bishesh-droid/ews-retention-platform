# LLM System Integration - Architecture Documentation

## Overview

This document describes the architecture of the LLM (Large Language Model) integration in the Early Warning System (EWS) Retention Platform. The LLM serves as an **explainability engine**, **decision-support co-pilot**, **narrative generator**, and **pattern discovery assistant** across all user roles.

## Architecture Principles

### 1. Data Grounding
All LLM responses must be grounded in real institutional data. The system uses **Retrieval-Augmented Generation (RAG)** to ensure the LLM only references authorized, actual data.

### 2. Hallucination Prevention
Multiple layers of validation prevent the LLM from fabricating information:
- Response validation against source data
- Fabricated ID detection
- Numerical plausibility checks
- Content filtering for inappropriate suggestions
- Confidence scoring based on data quality

### 3. Role-Based Access Control (RBAC)
Strict permissions ensure users only access data they're authorized to see:
- **Students**: Own data only
- **Faculty**: Assigned students only
- **Admin**: Full institutional data
- **Sales**: Anonymized cohort data only

### 4. Transparency & Ethics
Every AI insight includes:
- "Why am I seeing this?" explanations
- Data source attribution
- Confidence levels (High/Medium/Low)
- Human override mechanisms

## System Components

### Backend Services

#### 1. `llm_service.py` - LLM Orchestrator
**Purpose**: Core interface for all LLM operations

**Key Classes**:
- `LLMOrchestrator`: Main orchestration class
- `DataRetriever`: Fetches authorized institutional data
- `PromptBuilder`: Constructs role-specific prompts
- `ResponseValidator`: Validates responses for hallucinations

**Methods**:
- `explain_risk_change(student_id, time_period)` → Explanation with sources
- `generate_student_advice(student_id, question)` → Personalized guidance
- `summarize_student_profile(student_id, for_role)` → Role-specific summary
- `suggest_interventions(student_id)` → Evidence-backed suggestions
- `analyze_cohort_patterns(filters)` → Pattern discovery
- `simulate_what_if(student_id, scenario)` → Scenario analysis
- `generate_report_narrative(report_type, data)` → Auto-generated reports

#### 2. `rag_engine.py` - Retrieval-Augmented Generation
**Purpose**: Ensures LLM only references real data

**Components**:
- `StudentDataRetriever`: Fetches student academic history
- `CohortDataRetriever`: Fetches cohort statistics
- `InstitutionalDataRetriever`: System-wide patterns
- `ContextAssembler`: Builds structured LLM context
- `GuardrailValidator`: Prevents referencing unavailable data

#### 3. `pattern_discovery.py` - Institutional Insights
**Purpose**: Detects systemic issues and blind spots

**Features**:
- Systemic issue detection (policies, subjects, scheduling)
- Cross-semester pattern analysis
- Demographic disparity identification
- Proactive insight generation

**Example Outputs**:
- "Thursday 8 AM classes have 40% higher dropout rates"
- "Attendance penalties disproportionately affect first-year STEM students"

#### 4. `intervention_intelligence.py` - Smart Recommendations
**Purpose**: Evidence-based intervention suggestions

**Capabilities**:
- Analyzes past intervention effectiveness
- Matches similar student profiles
- Calculates success probability per intervention type
- Provides reasoning for each suggestion

#### 5. `hallucination_prevention.py` - Response Validation
**Purpose**: Prevents AI from fabricating information

**Classes**:
- `HallucinationPrevention`: Validates responses against source data
- `ContentFilter`: Blocks inappropriate/harmful content
- `ConfidenceScorer`: Calculates confidence based on data quality

**Checks**:
- Fabricated student ID detection
- Numerical plausibility verification
- Uncertainty indicator analysis
- Future prediction detection

#### 6. `audit_logger.py` - Audit & Security
**Purpose**: Tracks all LLM interactions for compliance

**Classes**:
- `AuditLogger`: Logs queries, responses, and metadata
- `RoleBasedAccessControl`: Enforces permissions

**Capabilities**:
- Compliance reporting
- Anomalous usage detection
- User interaction history
- Access permission validation

### Database Schema

#### `llm_queries` Table
Tracks all LLM interactions:
```sql
CREATE TABLE llm_queries (
    id INTEGER PRIMARY KEY,
    user_id STRING,
    user_role STRING,  -- 'student', 'faculty', 'admin', 'sales'
    query_type STRING,  -- 'explain_risk', 'advice', etc.
    input_data TEXT,  -- JSON of parameters
    response TEXT,
    confidence STRING,  -- 'high', 'medium', 'low'
    sources TEXT,  -- JSON array of data sources
    timestamp DATETIME
);
```

#### `llm_insights` Table
Stores discovered institutional insights:
```sql
CREATE TABLE llm_insights (
    id INTEGER PRIMARY KEY,
    insight_type STRING,
    title STRING,
    content TEXT,
    source_data TEXT,  -- JSON of evidence
    confidence STRING,
    visibility STRING,  -- 'public', 'admin_only'
    created_at DATETIME,
    dismissed BOOLEAN
);
```

#### `pattern_discoveries` Table
Stores systemic patterns and blind spots:
```sql
CREATE TABLE pattern_discoveries (
    id INTEGER PRIMARY KEY,
    pattern_type STRING,
    title STRING,
    description TEXT,
    severity STRING,  -- 'low', 'medium', 'high', 'critical'
    affected_cohort STRING,  -- JSON
    root_cause STRING,
    suggested_action STRING,
    supporting_data TEXT,  -- JSON statistics
    confidence STRING,
    discovered_at DATETIME,
    acknowledged BOOLEAN
);
```

### Frontend Components

#### AI-Generated Content Components
- `ReportAISummary.jsx`: Executive summaries for reports
- `ChartExplainerTooltip.jsx`: Contextual chart explanations
- `WhyAmISeeingThis.jsx`: Transparency explanations
- `ConfidenceBadge.jsx`: Visual confidence indicators
- `RiskChangeExplainer.jsx`: Risk score change narratives
- `MicroGoalsSuggester.jsx`: Personalized weekly goals
- `WhatIfSimulatorPanel.jsx`: Scenario simulation UI
- `AIStudentSummary.jsx`: Faculty-facing student summaries
- `PriorityQueuePanel.jsx`: Smart student prioritization
- `RevenueRiskTranslator.jsx`: Academic risk → business impact
- `SystemPatternDetector.jsx`: Institutional insights visualization

### API Endpoints

#### Student-Facing
- `POST /api/llm/explain-risk-change`: Why risk score changed
- `POST /api/llm/student-advice`: Personalized guidance
- `POST /api/llm/what-if-simulation`: Scenario analysis
- `GET /api/llm/weekly-brief/{student_id}`: Weekly summary

#### Faculty-Facing
- `POST /api/llm/faculty-summary`: Student profile summary
- `POST /api/llm/intervention-suggestions`: Smart interventions
- `GET /api/llm/prioritize-students`: Priority queue
- `GET /api/llm/similar-students/{student_id}`: Similar profiles

#### Sales/Retention
- `POST /api/llm/cohort-analysis`: Cohort patterns
- `GET /api/llm/revenue-risk-translation`: Revenue impact
- `GET /api/llm/dropout-pattern-explanation`: Dropout insights

#### Admin/Institutional
- `GET /api/llm/institutional-insights`: System-wide patterns
- `POST /api/llm/pattern-discovery`: Run discovery algorithms
- `POST /api/llm/generate-report-narrative`: Auto-generate reports
- `GET /api/llm/intervention-effectiveness`: Intervention analytics

## Design System

### AI-Specific Typography
Located in `design-system.css`, the system includes:

**AI Text Styling**:
- `.ai-text`: Standard AI-generated content (purple-tinted)
- `.ai-heading`: AI section headers
- `.ai-badge`: "AI-Generated" labels
- `.data-metric`: System metrics (monospace, distinct from AI)

**Confidence Indicators**:
- `.confidence-high`: Green badge (90%+ confidence)
- `.confidence-medium`: Amber badge (60-89%)
- `.confidence-low`: Gray badge (<60%)

**Source Attribution**:
- `.source-badge`: Italicized citations
- `.source-attribution-section`: Expandable source details
- `.source-list`: Bulleted source references

**Trust-Building Elements**:
- `.ai-insights-card`: Subtle purple border and gradient
- `.authority-marker`: Top border for institutional insights
- `.why-seeing-this`: Dashed border transparency box

### Color Coding
- **AI Content**: Purple accent (`#8B5CF6`)
- **Human Decisions**: Blue accent (`#3B82F6`)
- **Data Metrics**: Neutral monospace
- **Warnings**: Calm amber (not alarming red)

## Security Model

### Access Control Matrix

| Feature                    | Student | Faculty | Admin | Sales |
|----------------------------|---------|---------|-------|-------|
| Own risk explanation       | ✅      | ✅      | ✅    | ❌    |
| Other student profiles     | ❌      | ✅*     | ✅    | ❌    |
| Cohort analysis            | ❌      | ❌      | ✅    | ✅    |
| Institutional insights     | ❌      | ❌      | ✅    | ✅†   |
| Revenue data               | ❌      | ❌      | ✅    | ✅    |

\* Faculty can only see assigned students  
† Sales sees anonymized data only

### Guardrails

1. **Data Grounding**: LLM can only reference RAG-retrieved data
2. **Validation Layer**: Responses checked before display
3. **Confidence Thresholds**: Low-confidence outputs flagged
4. **Content Filtering**: Inappropriate responses blocked
5. **Audit Logging**: All queries logged with metadata

## Prompt Engineering Strategy

### Prompt Structure
All prompts follow this template:

```
[ROLE CONTEXT]
You are advising a {user_role} in an academic early warning system.

[DATA GROUNDING]
You have access to the following verified data:
{structured_data}

[CONSTRAINTS]
- Only reference the data provided
- Use calm, non-alarming language
- Cite sources for all claims
- Express uncertainty when data is limited

[TASK]
{specific_question_or_request}

[OUTPUT FORMAT]
Provide:
1. Direct answer
2. Supporting evidence (cite sources)
3. Confidence level (high/medium/low)
```

### Role-Specific Variations

**Student Prompts**:
- Empathetic, encouraging tone
- Focus on actionable micro-goals
- Avoid alarming language
- Celebrate progress

**Faculty Prompts**:
- Analytical, data-driven
- Prioritize efficiency (time-saving)
- Evidence-based recommendations
- Similar student case studies

**Sales Prompts**:
- Business language (avoid jargon)
- Revenue/churn focus
- Cohort comparisons
- Executive summaries

**Admin Prompts**:
- Systemic insights
- Root cause analysis
- Policy impact assessment
- Cross-cohort patterns

## Competitive Moat

### Features That Improve Over Time
1. **Pattern Discovery Accuracy**: More semesters = better detection
2. **Intervention Recommendations**: Historical effectiveness unique to institution
3. **Cohort Predictions**: Cross-semester trends impossible to replicate
4. **Personalized Advice**: Student similarity matching improves with data

### Lock-In Factors
- Historical context learned from institution-specific data
- Custom intervention strategies become training data
- Faculty trust built through accurate suggestions
- Data network effects (more users → better insights)

## Testing Strategy

### Unit Tests (`test_llm_services.py`)
- Hallucination detection
- Content filtering
- Confidence scoring
- RBAC permissions
- Audit logging

### Integration Tests
- End-to-end LLM query flows
- API endpoint validation
- Response format verification
- Error handling

### Manual Verification
- Real student scenario testing
- Hallucination checks
- Sensitivity to edge cases
- UI/UX validation

## Ethical Considerations

### Bias Mitigation
- Demographic disparity detection
- Regular audit of intervention suggestions
- Faculty oversight on all AI recommendations

### Privacy Safeguards
- Students see only own data
- Audit logs for all access
- Anonymization for sales team

### Human Oversight
- All AI suggestions labeled clearly
- Faculty can override any recommendation
- Escalation protocols for sensitive topics

## Deployment Notes

### Environment Variables
```bash
GOOGLE_API_KEY=<gemini_api_key>
DATABASE_URL=sqlite:///./sql_app.db
LOG_LEVEL=INFO
```

### Dependencies
- Google Gemini API (LLM)
- SQLAlchemy (ORM)
- FastAPI (backend)
- React + Bootstrap (frontend)

### Performance
- LLM response time: <3 seconds
- Confidence calculation: <100ms
- RAG data retrieval: <500ms

## Future Enhancements

1. **Multi-LLM Support**: Allow switching between Gemini and GPT-4
2. **Fine-Tuning**: Train custom model on institutional data
3. **Real-Time Updates**: WebSocket for live LLM streaming
4. **Mobile App**: Extend to iOS/Android with push notifications
5. **Voice Interface**: Voice-activated AI advisor for students

---

**Document Version**: 1.0  
**Last Updated**: February 4, 2026  
**Maintained By**: Development Team
