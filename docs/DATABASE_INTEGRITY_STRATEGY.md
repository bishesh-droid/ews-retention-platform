# Database Integrity Strategy

## Overview

This document describes the data safety strategy for enforcing strict database integrity in the EWS Retention Platform PostgreSQL database.

## Issues Addressed

### 1. Critical User Fields Allow NULL

**Problem:** Core authentication fields in the `users` table could accept NULL values, compromising data integrity.

**Fields Affected:**
- `username` - Required for identification
- `email` - Required for communication
- `hashed_password` - Required for authentication
- `role` - Required for RBAC authorization

**Solution:** Migration 014 adds `NOT NULL` constraints with safe backfill.

### 2. Prediction.risk_score is Nullable

**Problem:** The core ML output field `risk_score` could be NULL, breaking risk analysis queries.

**Solution:** Migration 014 adds `NOT NULL` constraint with backfill to 0.0 (neutral/lowest risk).

### 3. Deprecated datetime.utcnow Usage

**Problem:** `datetime.utcnow()` is deprecated (Python 3.12+) and returns naive timestamps.

**Solution:**
- Models updated to use `datetime.now(timezone.utc)`
- Migration 014 + 015 convert all TIMESTAMP columns to TIMESTAMPTZ

---

## Migration Strategy

### Migration 014: Core Tables (users, predictions)

**Revision:** `014` → depends on `013`

#### Step 1: Backfill NULL Values

Before adding constraints, existing NULL values are filled with safe defaults:

| Table | Column | Backfill Value | Rationale |
|-------|--------|----------------|-----------|
| users | username | `''` (empty string) | Should not exist, safe fallback |
| users | email | `''` (empty string) | Should not exist, safe fallback |
| users | hashed_password | `''` (empty string) | Should not exist, safe fallback |
| users | role | `'student'` | Safest default role |
| users | is_active | `TRUE` | Preserve access for existing users |
| users | is_superuser | `FALSE` | Default non-admin |
| predictions | risk_score | `0.0` | Neutral/lowest risk |
| predictions | engagement_score | `0.0` | Neutral engagement |
| predictions | retention_likelihood | `'unknown'` | Explicit unknown state |
| predictions | student_id | DELETE orphans | Orphan records removed |

#### Step 2: Add NOT NULL Constraints

```python
op.alter_column('users', 'username', nullable=False)
op.alter_column('users', 'email', nullable=False)
op.alter_column('users', 'hashed_password', nullable=False)
op.alter_column('users', 'role', nullable=False)
op.alter_column('predictions', 'risk_score', nullable=False)
```

#### Step 3: Add Check Constraints

```python
# Role validation
op.create_check_constraint(
    'check_valid_role', 'users',
    "role IN ('student', 'faculty', 'admin', 'retention team')"
)

# Risk score range (0-100 scale)
op.create_check_constraint(
    'check_risk_score_range', 'predictions',
    'risk_score >= 0.0 AND risk_score <= 100.0'
)
```

#### Step 4: Convert Timestamps to TIMESTAMPTZ

```python
op.execute("""
    ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ
    USING created_at AT TIME ZONE 'UTC'
""")
```

---

### Migration 015: Remaining Tables

**Revision:** `015` → depends on `014`

Extends timezone-aware timestamps to all remaining tables:

- `audit_logs`
- `student_responses`
- `ingestion_runs`
- `raw_events`
- `intervention_logs`
- `risk_snapshots`
- `goals`
- `dim_students`, `dim_courses`
- `fact_academic_performance`, `fact_engagement`, `fact_consistency`, `fact_intent_responsiveness`
- `data_lineage`
- `course_content_registry`

---

## Data Safety Guarantees

### 1. No Data Loss

- NULL values are backfilled BEFORE constraints are added
- Orphan prediction records are deleted (not valid without student)
- All existing data is preserved with sensible defaults

### 2. Safe Defaults

| Scenario | Default | Why |
|----------|---------|-----|
| Missing user role | `'student'` | Least privilege default |
| Missing risk_score | `0.0` | Neutral/lowest risk |
| Missing timestamp | Current UTC time | Accurate record of migration |
| Missing engagement_score | `0.0` | Neutral baseline |

### 3. Reversible

Both migrations include `downgrade()` functions that:
- Remove check constraints
- Allow NULLs again
- Convert TIMESTAMPTZ back to TIMESTAMP (loses timezone info)

---

## Model Changes

### Updated Files

All model files now import and use timezone-aware datetimes:

```python
from datetime import datetime, timezone

# Correct usage:
timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# OR for database-side default:
from sqlalchemy import func
timestamp = Column(DateTime, server_default=func.now())
```

### Files Modified

| File | Changes |
|------|---------|
| `backend/database/models/user.py` | Already correct (uses `datetime.now(timezone.utc)`) |
| `backend/database/models/prediction.py` | Already correct (uses `datetime.now(timezone.utc)`) |
| `backend/database/models/audit.py` | Fixed: `datetime.utcnow` → `datetime.now(timezone.utc)` |
| `backend/database/models/feature.py` | Fixed: `datetime.utcnow` → `datetime.now(timezone.utc)` |
| `backend/database/models/ingestion_run.py` | Fixed: `datetime.utcnow` → `datetime.now(timezone.utc)` |
| `backend/database/models/event.py` | Fixed: `datetime.utcnow` → `datetime.now(timezone.utc)` |
| `backend/database/models/intervention_log.py` | Fixed: `datetime.utcnow` → `datetime.now(timezone.utc)` |
| `backend/database/models/goals_and_risks.py` | Fixed: `datetime.utcnow` → `datetime.now(timezone.utc)` |
| `backend/database/models/canonical.py` | Fixed: all `datetime.utcnow` → `datetime.now(timezone.utc)` |
| `backend/database/models/course_content_registry.py` | Fixed: `datetime.utcnow` → `datetime.now(timezone.utc)` |

---

## Running the Migrations

```bash
# Check current migration status
alembic current

# Upgrade to latest (includes 014 and 015)
alembic upgrade head

# Verify constraints are in place
psql -d your_db -c "\d users"
psql -d your_db -c "\d predictions"
```

---

## Verification

After migration, verify:

```sql
-- Check NOT NULL constraints on users
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('username', 'email', 'hashed_password', 'role');

-- Check risk_score is NOT NULL
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_name = 'predictions'
AND column_name = 'risk_score';

-- Check timestamp columns are TIMESTAMPTZ
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name = 'created_at';
```

Expected output:
- `is_nullable = 'NO'` for all critical fields
- `udt_name = 'timestamptz'` for timestamp columns

---

## Future Prevention

### SQLAlchemy Model Best Practices

```python
# ALWAYS use timezone-aware datetimes
from datetime import datetime, timezone

class MyModel(Base):
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

# ALWAYS specify nullable=False for required fields
username = Column(String, nullable=False)
```

### Pre-commit Hook

Add a check to prevent `datetime.utcnow` in new code:

```bash
# .pre-commit-hooks/check-datetime.sh
if grep -r "datetime.utcnow" backend/database/models/; then
    echo "ERROR: datetime.utcnow is deprecated. Use datetime.now(timezone.utc)"
    exit 1
fi
```
