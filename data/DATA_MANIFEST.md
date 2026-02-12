# Data File Manifest

## Overview
This document provides a comprehensive catalog of all data files used in the EWS Retention Platform, their purpose, structure, and processing pipeline.

---

## Active Data Files

### 1. Student-Level Assessment Files

#### `graded quiz 1 10 feb complete.xlsx`
- **Type**: Student-level assessment data
- **Purpose**: Graded quiz scores and completion status
- **Student Identifier**: `Username` or `Email` column
- **Processing Pipeline**: `ingestion/pipeline.py` → `FactAcademicPerformance`
- **Expected Columns**: Username, Email, Score, Status, Timestamp
- **Refresh Frequency**: After quiz grading completion
- **Status**: ✅ Active - Authoritative version

#### `_Trimester-1 2025 Attendance Quiz-Assignment-Exam 5Jan2025.xlsx`
- **Type**: Student-level comprehensive metrics
- **Purpose**: Attendance, quiz, assignment, and exam data for Trimester 1
- **Student Identifier**: `Email` or `student_id`
- **Processing Pipeline**: `ingestion/pipeline.py` → Multiple fact tables
- **Expected Columns**: Student ID, Attendance %, Quiz Scores, Assignment Scores, Exam Scores
- **Refresh Frequency**: Weekly during trimester, final version at trimester end
- **Status**: ✅ Active

#### `Engagement_Analysis.xlsx`
- **Type**: Student-level engagement metrics
- **Purpose**: LMS engagement data (logins, content views, activity time)
- **Student Identifier**: `learner_email`
- **Processing Pipeline**: `ingestion/pipeline.py` → `FactEngagement`
- **Expected Columns**: learner_email, login_count, content_views, time_spent, last_active
- **Refresh Frequency**: Daily
- **Status**: ✅ Active

#### `Learner usage week 3.xlsx`
- **Type**: Student-level weekly usage
- **Purpose**: Detailed activity metrics for specific week
- **Student Identifier**: Expected `email` or `learner_id`
- **Processing Pipeline**: `ingestion/pipeline.py` → `FactEngagement`
- **Expected Columns**: TBD (needs schema validation)
- **Refresh Frequency**: Weekly
- **Status**: ⚠️ Needs validation - Missing from data catalog

#### `Week 1-2 Student Engagement Analysis.xlsx`
- **Type**: Student-level engagement summary
- **Purpose**: Early engagement indicators for Weeks 1-2
- **Student Identifier**: Expected `email`
- **Processing Pipeline**: `ingestion/pipeline.py` → `FactEngagement`
- **Expected Columns**: TBD (needs schema validation)
- **Refresh Frequency**: Bi-weekly
- **Status**: ⚠️ Needs validation

---

### 2. Aggregate Summary Files (NOT Student-Level)

#### `B.S and M.Sc Live Summary Data C-1, Trimester 1.xlsx`
- **Type**: Course-level aggregate
- **Purpose**: Live session attendance counts by course and week
- **Student Identifier**: ❌ None - This is aggregate data
- **Data Grain**: Course × Faculty × Week
- **Processing Pipeline**: Separate reporting pipeline (not for student risk scoring)
- **Expected Columns**: Course Name, Faculty, Week-1 through Week-13 (attendance counts)
- **Refresh Frequency**: Weekly during trimester
- **Status**: ✅ Active - For reporting only, NOT for student-level predictions
- **⚠️ Important**: Do NOT attempt to join this with student-level data

#### `B.S and M.Sc Summary Data Trimester 2.xlsx`
- **Type**: Course-level aggregate
- **Purpose**: Same as Trimester 1 but for Trimester 2
- **Student Identifier**: ❌ None - This is aggregate data
- **Data Grain**: Course × Faculty × Week (by date ranges)
- **Processing Pipeline**: Separate reporting pipeline
- **Status**: ✅ Active - For reporting only
- **⚠️ Important**: Do NOT attempt to join this with student-level data

---

## Archived Data Files

The following files have been moved to `data/archive/` as they are duplicate versions of the same data:

### `Graded Quiz 1 Status 9 feb.xlsx`
- **Reason for Archive**: Older version of same quiz data
- **Replaced By**: `graded quiz 1 10 feb complete.xlsx`
- **Archive Date**: 2026-02-12

### `Graded quiz 1 10 feb 4_51 pm.xlsx`
- **Reason for Archive**: Intermediate export, not final version
- **Replaced By**: `graded quiz 1 10 feb complete.xlsx`
- **Archive Date**: 2026-02-12

### `graded quiz 1 10 feb 11_15 AM.xlsx`
- **Reason for Archive**: Intermediate export, not final version
- **Replaced By**: `graded quiz 1 10 feb complete.xlsx`
- **Archive Date**: 2026-02-12

---

## Data Quality Guidelines

### 1. Student Identifier Requirements

All **student-level** data files MUST contain at least one of these identifier columns:
- `email` (preferred)
- `learner_email`
- `Username`
- `student_id`

Files without student identifiers are treated as **aggregate** data and processed separately.

### 2. File Naming Conventions

**For Assessment Files**:
- Format: `{assessment_type}_{date}_FINAL.xlsx`
- Example: `graded_quiz_1_2025-02-10_FINAL.xlsx`
- Always include "FINAL" or "complete" in the authoritative version

**For Engagement Files**:
- Format: `{data_type}_{period}.xlsx`
- Example: `Learner_usage_week_3.xlsx`

**For Aggregate Reports**:
- Clearly indicate "Summary" or "Report" in filename
- Example: `BS_MSc_Live_Summary_Trimester_1.xlsx`

### 3. Data Validation

All files undergo validation via `backend/ingestion/row_validators.py`:
- ✅ Column count validation
- ✅ Required field presence
- ✅ Excel error detection (`#DIV/0!`, `#VALUE!`, `#N/A`)
- ✅ Numeric bounds checking (percentages 0-100, no negative scores)
- ✅ Timestamp sanity checks
- ✅ Email format validation

Failed validation → Rows sent to quarantine (`backend/ingestion/quarantine.py`)

### 4. Percentage Format

**Standard**: Store percentages as **decimals (0-1)**
- Example: 75% stored as `0.75`
- Validation: `0.0 <= value <= 1.0`
- Normalization: `backend/ingestion/transformers.py` handles both formats

### 5. Missing Data Representation

**Allowed representations**:
- Empty cell (null)
- `NA`
- `N/A`
- `-` (hyphen)

**Forbidden**:
- `0` to represent missing (unless actually zero)
- Random text
- Excel errors

---

## Processing Pipelines

### Student-Level Data Processing Flow

```
Raw Data File (.xlsx/.csv)
    ↓
[Validation Layer] (row_validators.py, validators.py)
    ↓
[Pass] → Ingestion Pipeline → Star Schema DB
    ↓                              ↓
[Fail] → Quarantine             DimStudent
           ↓                        ↓
       Error Log              FactEngagement
                                  ↓
                            FactAcademicPerformance
```

### Aggregate Data Processing Flow

```
Aggregate Summary File
    ↓
[Validation - Schema Only]
    ↓
Reporting Database (separate from student DB)
    ↓
Business Intelligence Dashboards
```

---

## Data Refresh Schedule

| File Type | Frequency | Automation |
|-----------|-----------|------------|
| Quiz/Exam Scores | After grading completion | Manual upload |
| Engagement Analytics | Daily | Automated (LMS export) |
| Attendance Records | Weekly | Automated |
| Summary Reports | Weekly | Automated |

---

## File Access & Security

- **Location**: `data/raw/` (production), `data/archive/` (historical)
- **Permissions**: Read-only for ingestion pipeline
- **Backup**: Daily backup to `data/backups/YYYY-MM-DD/`
- **PII Protection**: All files contain student PII, treat as confidential
- **Retention**: Raw files kept for 7 years per institutional policy

---

## Troubleshooting

### Issue: "Student identifier not found"
**Cause**: File lacks required ID column
**Solution**: 
1. Verify file is student-level (not aggregate)
2. Check for columns: `email`, `learner_email`, `Username`, `student_id`
3. If aggregate file, move to separate reporting pipeline

### Issue: "Duplicate student records"
**Cause**: Multiple rows for same student
**Solution**:
1. Check if file contains time-series data (multiple timestamps)
2. If duplicates, use latest record only
3. Check for different course sections (same student, different courses is OK)

### Issue: "Percentage validation failed"
**Cause**: Value outside 0-1 or 0-100 range
**Solution**:
1. Check if percentages stored as decimals or integers
2. Run normalization: `transformers.normalize_percentage(value)`
3. Verify source data quality

---

## Changelog

### 2026-02-12
- **Action**: Moved duplicate quiz files to archive
- **Files Archived**: 3 intermediate quiz exports
- **Reason**: Prevent double-counting, clarify data lineage
- **Impact**: Single authoritative quiz file remains

### 2026-02-12
- **Action**: Created this manifest
- **Purpose**: Document data sources and processing rules
- **Benefit**: Improved data governance and onboarding

---

## Contact

For questions about data files or to report data quality issues:
- **Data Engineering Team**: [Contact info]
- **Issue Tracker**: GitHub Issues with `data-quality` label
