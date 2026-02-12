# API Contract Specification

## Overview

This document defines the API contract between the FastAPI backend and React frontend for the EWS Retention Platform.

**CRITICAL SCALE CONVENTION**:
- `risk_score`: **0-100** (percentage scale for end-user display)  
- `signal_breakdown.*`: **0-1** (probability scale for internal metrics)
- `engagement_score`: **0-100** (percentage scale)

---

## Student Endpoints

### GET `/api/v1/students/students`

**Purpose**: Retrieve paginated list of students with risk predictions

**Query Parameters**:
| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `skip` | integer | 0 | No | Pagination offset |
| `limit` | integer | 50 | No | Page size (max 2000) |
| `sort_by` | string | "risk_score" | No | Sort field: risk_score, id, name, department |
| `order` | string | "desc" | No | Sort order: asc, desc |
| `risk_min` | float | null | No | Min risk score filter (0-100) |
| `risk_max` | float | null | No | Max risk score filter (0-100) |

**Response Schema** (200 OK):
```typescript
{
  students: Array<{
    // Identity
    id: string;  // Email or student ID
    first_name?: string | null;
    last_name?: string | null;
    department?: string | null;
    program?: string | null;
    
    // Risk Prediction (ALWAYS PRESENT)
    risk_score: number;  // 0-100 percentage ✅ CRITICAL
    risk_level: "low" | "medium" | "high" | "critical";
    risk_category: "low" | "medium" | "high";  // Same as risk_level
    
    // Engagement
    engagement_score: number;  // 0-100 percentage ✅ CRITICAL
    
    // Signal Breakdown (0-1 probabilities)
    signal_breakdown: {
      academic_signal_score: number;  // 0-1
      engagement_signal_score: number;  // 0-1
      consistency_signal_score: number;  // 0-1
      intent_signal_score: number;  // 0-1
      responsiveness_signal_score: number;  // 0-1
    };
    
    // Risk Factors
    top_risk_factors: Array<string>;  // e.g. ["Low attendance", "Declining grades"]
    
    // Metadata
    prediction_available: boolean;
    prediction_error: boolean;
    model_version?: string;
    confidence?: number;  // 0-1
    predicted_at?: string;  // ISO 8601 timestamp
  }>;
  
  total: number;  // Total student count
  page: number;  // Current page (1-indexed)
  page_size: number;  // Items per page
}
```

**Error Responses**:
- `400 Bad Request`: Invalid query parameters
- `500 Internal Server Error`: Database or prediction error

---

### GET `/api/v1/students/{student_id}`

**Purpose**: Retrieve single student detail

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `student_id` | string | Yes | Student email or ID (URL-encoded) |

**Response Schema** (200 OK):
```typescript
{
  // Same fields as in /students/students array
  id: string;
  risk_score: number;  // 0-100 ✅
  engagement_score: number;  // 0-100 ✅
  signal_breakdown: { ... };  // 0-1 probabilities
  
  // Additional details
  enrollment_data?: Array<{
    course_id: string;
    course_name: string;
    enrollment_date: string;
    status: "active" | "dropped" | "completed";
  }>;
  
  intervention_history?: Array<{
    intervention_id: string;
    date: string;
    type: string;
    outcome?: string;
  }>;
}
```

**Error Responses**:
- `404 Not Found`: Student does not exist
- `422 Unprocessable Entity`: Invalid student_id format

---

### GET `/api/v1/students/at-risk`

**Purpose**: Get list of students above risk threshold

**Query Parameters**:
| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `threshold` | float | 70.0 | No | Risk score threshold (0-100) |

**Response Schema** (200 OK):
```typescript
{
  at_risk_students: Array<StudentObject>;  // Same as /students response
  count: number;
  threshold: number;  // 0-100
}
```

---

### GET `/api/v1/students/overview`

**Purpose**: Dashboard summary statistics

**Response Schema** (200 OK):
```typescript
{
  total_students: number;
  average_risk_score: number;  // 0-100 ✅
  at_risk_count: number;  // Students with risk_score > 70
  critical_count: number;  // Students with risk_score > 85
  engagement_average: number;  // 0-100 ✅
  
  risk_distribution: {
    low: number;  // Count of students 0-30
    medium: number;  // Count of students 31-60
    high: number;  // Count of students 61-85
    critical: number;  // Count of students 86-100
  };
}
```

---

## Business Intelligence Endpoints

### GET `/api/v1/business/metrics/revenue-at-risk`

**Purpose**: Calculate revenue impact of at-risk students

**Response Schema** (200 OK):
```typescript
{
  revenue_at_risk: number;  // USD value
  high_risk_count: number;
  critical_risk_count: number;
  avg_student_ltv: number;  // USD
  retention_rate: number;  // 0-100 percentage
}
```

---

### GET `/api/v1/business/cohort-analysis`

**Purpose**: Comparative cohort performance

**Response Schema** (200 OK):
```typescript
{
  cohorts: Array<{
    name: string;  // e.g. "2024-Fall"
    size: number;
    avg_risk_score: number;  // 0-100 ✅
    retention_rate: number;  // 0-100 percentage
    top_departments: Array<string>;
  }>;
}
```

---

## Decision Endpoints

### GET `/api/v1/decisions/interventions/{student_id}`

**Purpose**: Get intervention recommendation for student

**Response Schema** (200 OK):
```typescript
{
  student_id: string;
  risk_score: number;  // 0-100 ✅
  
  threshold_category: "low" | "medium" | "high" | "critical";
  action_type: "no_action" | "gentle_reminder" | "mentor_outreach" | "urgent_intervention";
  
  channels: Array<"email" | "whatsapp" | "in_app" | "phone">;
  assigned_team: "self_service" | "automated" | "academic_mentor" | "dept_head";
  
  priority: "low" | "medium" | "high" | "urgent";
  urgency: "none" | "low" | "medium" | "high";
  
  description: string;  // Human-readable action description
  estimated_outreach_time?: string;  // e.g. "within 48 hours"
}
```

---

## AI Recommendation Endpoints

### POST `/api/v1/recommendations/ai-advice`

**Purpose**: Get Gemini-powered personalized recommendations

**Request Body**:
```typescript
{
  student_id: string;
  context?: string;  // Optional context hint
}
```

**Response Schema** (200 OK):
```typescript
{
  student_id: string;
  advice: string;  // Natural language recommendation
  
  recommended_actions: Array<{
    title: string;
    description: string;
    priority: "low" | "medium" | "high";
  }>;
  
  resources: Array<{
    title: string;
    url: string;
    type: "video" | "article" | "practice" | "tutoring";
  }>;
  
  generated_at: string;  // ISO 8601 timestamp
}
```

---

## Frontend Integration Guidelines

### 1. Display Risk Scores

**✅ CORRECT** (use backend value AS-IS):
```javascript
// Backend returns risk_score: 75.3 (0-100)
<div>{student.risk_score.toFixed(1)}%</div>
// Displays: 75.3%
```

**❌ WRONG** (do NOT transform or recalculate):
```javascript
// ❌ DO NOT DO THIS
const risk = student.risk_score / 100;  // NO!
const risk = 100 - student.engagement;  // NO!
```

### 2. Display Signal Breakdown

**✅ CORRECT** (signals are 0-1, convert for display):
```javascript
// Backend returns signal_breakdown.academic_signal_score: 0.68 (0-1)
<div>Academic: {(student.signal_breakdown.academic_signal_score * 100).toFixed(0)}%</div>
// Displays: Academic: 68%
```

**❌ WRONG** (do NOT derive signals from raw scores):
```javascript
// ❌ DO NOT DO THIS
const academic = student.quiz_score / 100;  // NO!
```

### 3. Risk Level Display

**✅ CORRECT** (use backend risk_level or risk_category):
```javascript
<Badge color={getLevelColor(student.risk_level)}>
  {student.risk_level.toUpperCase()}
</Badge>
```

**❌ WRONG** (do NOT recompute risk level):
```javascript
// ❌ DO NOT DO THIS
const level = student.risk_score > 50 ? 'high' : 'low';  // NO!
```

### 4. Engagement Score

**✅ CORRECT** (backend calculates, frontend displays):
```javascript
// Backend returns engagement_score: 67.8 (0-100)
<div>Engagement: {student.engagement_score.toFixed(1)}%</div>
```

**❌ WRONG** (do NOT derive from risk):
```javascript
// ❌ DO NOT DO THIS
const engagement = 100 - student.risk_score;  // NO!
```

---

## Validation Rules

### Backend Guarantees

The backend **ALWAYS** ensures:
1. `risk_score` is in range [0.0, 100.0]
2. `signal_breakdown.*` values are in range [0.0, 1.0]
3. `engagement_score` is in range [0.0, 100.0]
4. No NaN, Inf, or null in numeric fields
5. `risk_level` matches `risk_score` (low: 0-30, medium: 31-60, high: 61-85, critical: 86-100)

### Frontend Assumptions

The frontend can safely assume:
1. Every student in `/students/students` has `risk_score` field (never null)
2. `signal_breakdown` is always present (use default 0.5 if missing)
3. Risk scores are **percentages (0-100)**, not probabilities (0-1)
4. Signal scores are **probabilities (0-1)**, not percentages

---

## Error Handling

### Standard Error Format

```typescript
{
  error: string;  // Error type
  message: string;  // Human-readable message
  details?: any;  // Additional context
}
```

### Common Error Cases

#### Invalid Query Parameters (400)
```json
{
  "error": "ValidationError",
  "message": "risk_min must be between 0 and 100",
  "details": {"field": "risk_min", "value": 150}
}
```

#### Student Not Found (404)
```json
{
  "error": "NotFoundError",
  "message": "Student with id 'invalid@example.com' not found"
}
```

#### Prediction Failure (500)
```json
{
  "error": "PredictionError",
  "message": "ML model prediction failed",
  "details": {"fallback_used": true, "risk_score": 50.0}
}
```

---

## Schema Evolution Guidelines

### Adding New Fields
- Add as **optional** fields first (e.g., `new_field?: type`)
- Document in this spec
- After frontend adopts, make required

### Changing Existing Fields
- ⚠️ **BREAKING CHANGE** - requires version bump
- Deprecation process:
  1. Add new field (e.g., `risk_score_v2`)
  2. Keep old field for 1 release cycle
  3. Remove old field, rename new field

### Removing Fields
- Mark as `@deprecated` for 1 release
- Log warnings when frontend accesses deprecated field
- Remove in next major version

---

## Testing Checklist

### Backend Unit Tests
- [ ] `risk_score` always 0-100
- [ ] `signal_breakdown` always 0-1
- [ ] No NaN/Inf values
- [ ] Pagination works correctly
- [ ] Filters work correctly

### Integration Tests
- [ ] Frontend can fetch and display `/students/students`
- [ ] Frontend can fetch and display `/students/{id}`
- [ ] Charts correctly visualize `signal_breakdown` (multiply by 100 for display)
- [ ] Risk level badges match `risk_score` ranges

---

**Last Updated**: 2026-02-12  
**Version**: 1.0  
**Status**: ✅ Implemented (risk score standardization complete)
