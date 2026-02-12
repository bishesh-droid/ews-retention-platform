# API Endpoint Mapping

This document maps the canonical data model to frontend API endpoints.

## Overview Statistics

**Endpoint**: `GET /api/v1/canonical/overview/statistics`

**Data源**: 
- `dim_students` table (count)
- `predictions` table with latest risk scores

**Response Schema**:
```json
{
  "total_students": 1303,
  "high_risk_count": 247,
  "medium_risk_count": 412,
  "low_risk_count": 644,
  "average_risk_score": 42.3,
  "last_updated": "2026-02-12T10:30:00Z"
}
```

## Student List

**Endpoint**: `GET /api/v1/canonical/students?sort=risk_score&order=desc&limit=100&offset=0`

**Data Source**: 
- `dim_students` JOIN `predictions` (latest)

**Response Schema**:
```json
{
  "students": [
    {
      "student_id": "student@example.com",
      "student_name": "John Doe",
      "program": "BS",
      "risk_score": 87.5,
      "risk_level": "Critical"
    }
  ],
  "total": 1303,
  "page": 1
}
```

## Student Detail with Signals

**Endpoint**: `GET /api/v1/canonical/students/{student_id}/signals`

**Data Source**:
- `fact_academic_performance` (academic signal)
- `fact_engagement` (engagement signal)
- `fact_consistency` (consistency signal)  
- `fact_intent_responsiveness` (intent signal)

**Response Schema**:
```json
{
  "student_id": "student@example.com",
  "overall_risk_score": 75.5,
  "risk_level": "High",
  "confidence": 0.9,
  "signals": {
    "academic_performance": {
      "value": 82.0,
      "sub_metrics": {
        "quiz_completion_rate": 85.0,
        "quiz_average_score": 72.0,
        "exam_participation": 100.0,
        "exam_score": 68.0
      }
    },
    "engagement": {
      "value": 65.0,
      "sub_metrics": {
        "attendance_rate": 78.0,
        "platform_time": 56.0,
        "content_interaction": 48.0
      }
    }
  }
}
```

## Component → API Mapping

### Dashboard Page
- **Overview Cards** → `/api/v1/canonical/overview/statistics`
- **Risk Distribution Chart** → `/api/v1/canonical/overview/statistics`
- **Priority Alerts** → `/api/v1/canonical/students?risk_level=Critical&limit=5`

### Students Page
- **Student Table** → `/api/v1/canonical/students?sort=<field>&order=<asc|desc>&limit=<n>&offset=<m>`
- **Filters** → Same endpoint with query parameters

### Student Profile Page
- **Student Info** → `/api/v1/canonical/students/{student_id}`
- **Signal Breakdown** → `/api/v1/canonical/students/{student_id}/signals`
- **Trend Charts** → `/api/v1/canonical/students/{student_id}/trends?metric=engagement&period=8weeks`
