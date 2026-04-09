# API Reference

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

## Authentication

All endpoints (except health check and login) require JWT authentication.

### Obtain Token

```bash
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=SecurePass123!
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Use Token

```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1Qi..." \
  http://localhost:8000/api/v1/students
```

## Core Endpoints

### Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "2.1.0"
}
```

---

## Students

### List Students

```
GET /students?skip=0&limit=50&sort_by=risk_score&order=desc
```

**Query Parameters:**
- `skip` (int): Pagination offset
- `limit` (int): Page size (1-2000)
- `sort_by` (string): Field to sort by
- `order` (string): `asc` or `desc`
- `risk_min` (float): Minimum risk score filter
- `risk_max` (float): Maximum risk score filter

**Response:**
```json
{
  "students": [
    {
      "id": "student123",
      "first_name": "John",
      "last_name": "Doe",
      "risk_score": 75.5,
      "engagement_score": 45.2,
      "parent_department_name": "Computer Science"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50
}
```

### Get Student Detail

```
GET /students/{student_id}
```

**Response:**
```json
{
  "id": "student123",
  "first_name": "John",
  "last_name": "Doe",
  "org_defined_id": "CS2024001",
  "risk_profile": {
    "current_score": 75.5,
    "category": "High Risk",
    "trend": "increasing"
  },
  "engagement_metrics": {
    "content_completion": 45.0,
    "login_consistency": 60.0,
    "quiz_engagement": 30.0,
    "assignment_completion": 50.0
  },
  "enrollments": [...]
}
```

### Get Risk Trend

```
GET /students/{student_id}/risk-trend?limit=8
```

**Response:**
```json
[
  {
    "timestamp": "2024-01-15T00:00:00",
    "risk_score": 65.0,
    "engagement_score": 55.0
  },
  {
    "timestamp": "2024-01-08T00:00:00",
    "risk_score": 45.0,
    "engagement_score": 60.0
  }
]
```

---

## Predictions

### Generate Prediction

```
POST /predictions
{
  "student_id": "student123"
}
```

**Response:**
```json
{
  "student_id": "student123",
  "risk_score": 75.5,
  "risk_category": "High Risk",
  "confidence": 0.85,
  "factors": [
    {"name": "Low content completion", "weight": 0.30},
    {"name": "Irregular login pattern", "weight": 0.20}
  ],
  "timestamp": "2024-01-15T10:30:00"
}
```

---

## Interventions

### Create Intervention

```
POST /interventions
{
  "student_id": "student123",
  "action": "Schedule advising meeting",
  "assigned_faculty": "Dr. Smith",
  "priority": "high",
  "due_date": "2024-01-20",
  "notes": "Student showing declining engagement"
}
```

### List Interventions

```
GET /interventions?status=pending&student_id=student123
```

### Update Intervention

```
PATCH /interventions/{intervention_id}
{
  "status": "completed",
  "outcome": "Student attended meeting, agreed to study plan",
  "effectiveness_score": 8
}
```

---

## Analytics

### Get Cohort Analytics

```
GET /analytics/cohort?program=Computer%20Science&semester=Spring2024
```

**Response:**
```json
{
  "total_students": 150,
  "at_risk_count": 25,
  "risk_distribution": {
    "low": 80,
    "medium": 30,
    "high": 25,
    "critical": 15
  },
  "average_engagement": 62.5,
  "trend": "improving"
}
```

### Get Overview Statistics

```
GET /overview
```

**Response:**
```json
{
  "total_students": 500,
  "active_interventions": 45,
  "high_risk_count": 35,
  "recent_predictions": 500,
  "engagement_trend": "stable"
}
```

---

## Audit Logs (Admin Only)

### Get Audit Logs

```
GET /audit-log?skip=0&limit=50&action=READ&resource_type=student
```

**Query Parameters:**
- `user_id` (int): Filter by user
- `action` (string): READ, WRITE, DELETE
- `resource_type` (string): student, enrollment, etc.
- `resource_id` (string): Specific resource
- `start_date` (date): Filter from date
- `end_date` (date): Filter to date

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "user_id": 5,
      "user_role": "faculty",
      "action": "READ",
      "resource_type": "student",
      "resource_id": "student123",
      "ip_address": "192.168.1.100",
      "timestamp": "2024-01-15T10:30:00",
      "details": null
    }
  ],
  "total": 1500,
  "page": 1,
  "page_size": 50
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "error": "Validation error",
  "detail": "Invalid risk_score: must be between 0 and 100",
  "request_id": "req_abc123"
}
```

### 401 Unauthorized

```json
{
  "error": "Authentication required",
  "detail": "Valid JWT token required"
}
```

### 403 Forbidden

```json
{
  "error": "Access denied",
  "detail": "Faculty role required for this endpoint"
}
```

### 404 Not Found

```json
{
  "error": "Student not found",
  "detail": "Student 'student999' does not exist"
}
```

### 429 Rate Limit Exceeded

```json
{
  "error": "Rate limit exceeded",
  "detail": "5 requests per minute allowed",
  "retry_after": 60
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Login | 5/minute |
| Data Ingestion | 10/hour |
| All other endpoints | 200/minute |

Rate limit headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Data Models

### Student

```json
{
  "id": "string",
  "org_defined_id": "string",
  "first_name": "string",
  "last_name": "string",
  "email": "string",
  "is_active": true,
  "parent_department_name": "string",
  "parent_department_code": "string"
}
```

### Risk Prediction

```json
{
  "id": 1,
  "student_id": "string",
  "risk_score": 75.5,
  "engagement_score": 45.0,
  "prediction_timestamp": "2024-01-15T00:00:00",
  "model_version": "2.1.0",
  "model_type": "rule_based"
}
```

### Intervention

```json
{
  "id": 1,
  "student_id": "string",
  "action": "string",
  "assigned_faculty": "string",
  "priority": "high|medium|low",
  "status": "pending|in_progress|completed|cancelled",
  "due_date": "2024-01-20",
  "completed_at": "2024-01-18T14:30:00",
  "outcome": "string",
  "effectiveness_score": 8,
  "created_at": "2024-01-15T10:00:00"
}
```
