# LLM Architecture & Security Documentation

## 1. Security & Authentication (RBAC)

The system now enforces Role-Based Access Control (RBAC) on sensitive LLM endpoints.

### Authentication Mechanism
Currently uses a **Simulation Mode** via the `X-User-Role` header.
- **Dev/Test**: Clients must send `X-User-Role: <role>` (e.g., `admin`, `faculty`).
- **Production Path**: This dependency `backend.api.deps.get_current_user_role` should be replaced with JWT validation logic.

### Role Hierarchy
1. **Admin**: Full access (Institutional Insights, System Patterns).
2. **Faculty**: Student access, Report generation.
3. **Student**: Own data only (via `student_id` validation).

### Secured Endpoints
| Endpoint | Required Role | Description |
|----------|---------------|-------------|
| `/api/llm/institutional-insights` | `admin` | System-wide pattern analysis. |
| `/api/llm/generate-report-narrative` | `faculty` | Executive summary generation. |

## 2. AI Ethics & Transparency

### Confidence Scoring
Every AI response includes a `confidence` field (`high`, `medium`, `low`).
- **High**: Derived from >2 direct data sources with successful cross-validation.
- **Medium**: Derived from 1 data source or speculative queries (e.g., "What-if").
- **Low**: Insufficient data or hallucination risk detected.

### UI Components
The `AiInsight` component standardizes how AI content is presented:
- **Visual Distinction**: Purple/Violet accent to separate human vs AI content.
- **Explainability**: Mandatory tooltips explaining data provenance.
- **Attribution**: Sources are always available (collapsible).
