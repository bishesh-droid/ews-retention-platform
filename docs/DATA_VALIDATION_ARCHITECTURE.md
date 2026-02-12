# EWS Data Validation Architecture
## Correctness-First Parsing & Validation Pipeline

**Philosophy**: Treat all input data as untrusted. Fail loudly. Never silently drop or misalign data.

---

## STEP 1: FILE-LEVEL VALIDATION (Pre-Parse Guards)

### 1.1 File Integrity Checks

**Before any parsing begins:**

```
FILE VALIDATION PIPELINE:
1. File existence & readability check
2. File extension validation (.xlsx, .csv only)
3. File size sanity check (0 bytes = reject, >100MB = warning)
4. MIME type verification (not just extension)
5. Encoding detection (UTF-8, UTF-16, Latin-1)
6. Virus/malware scan marker check
```

**Rejection Criteria:**
- Empty files → `ERROR: File contains 0 bytes`
- Wrong extension → `ERROR: Expected .xlsx or .csv, got .pdf`
- Unreadable encoding → `ERROR: Failed to decode with UTF-8/UTF-16/Latin-1`
- Corrupted file → `ERROR: File header indicates corruption`

### 1.2 Excel-Specific Pre-Parse Validation

**For .xlsx files:**

```python
XLSX_VALIDATION_CHECKLIST:
1. Sheet name enumeration
   - Verify workbook.sheetnames is accessible
   - Check for reserved/special characters in sheet names
   - Detect blank/hidden sheets

2. Header row detection
   - Scan first 5 rows for most likely header
   - Criteria: fewest nulls, most unique values, string-heavy
   - Warn if header candidates in rows 2-5

3. Merged cell detection
   - Scan range A1:ZZ100 for merged cells
   - REJECT if data columns contain merges
   - Allow only in title/summary regions

4. Hidden row/column detection
   - Flag hidden rows in data region
   - REJECT if hidden rows interspersed with data

5. Trailing summary detection
   - Detect "Total", "Average", "Grand Total" rows
   - Mark row_limit to exclude from parsing

6. Formula detection
   - Identify cells with formulas vs values
   - Use formula.value not formula.text
```

**Rejection Rules:**
- Merged cells in data region → `ERROR: Merged cells detected in rows 10-50, columns B-E`
- No valid header found → `ERROR: Unable to detect header row in first 5 rows`
- All sheets hidden → `ERROR: No visible sheets in workbook`

### 1.3 CSV-Specific Pre-Parse Validation

**For .csv files:**

```python
CSV_VALIDATION_CHECKLIST:
1. Delimiter detection
   - Try: comma, semicolon, tab, pipe
   - Validate consistency across all rows
   - REJECT if delimiter changes mid-file

2. Quote character detection
   - Detect double-quote, single-quote
   - Ensure balanced quotes

3. Line ending detection
   - \n, \r\n, \r
   - Normalize before parsing

4. Column count consistency
   - Count delimiters per row
   - REJECT if >5% variance in column counts

5. Encoding validation
   - BOM detection (UTF-8, UTF-16)
   - Fallback encoding attempts
```

**Rejection Rules:**
- Inconsistent delimiters → `ERROR: Row 45 has 12 columns, but row 1 has 8 columns`
- Unbalanced quotes → `ERROR: Unterminated quote starting at row 23`
- Encoding failure → `ERROR: Row 67 contains non-UTF-8 bytes`

### 1.4 Header Normalization

**Column name standardization:**

```python
HEADER_NORMALIZATION:
1. Trim whitespace
2. Lowercase conversion
3. Replace non-alphanumeric with underscore
4. Remove duplicate underscores
5. Prepend "col_" if starts with digit
6. Detect duplicates → append _1, _2, etc.

Example:
"  Student Email   " → "student_email"
"Quiz Score (%)" → "quiz_score_percent"
"2023 Grade" → "col_2023_grade"
```

**Duplicate column detection:**
```
BEFORE: ["Email", "Email", "Score"]
AFTER:  ["email", "email_1", "score"]
LOG:    WARNING: Duplicate column "Email" renamed to "email_1"
```

**Missing column detection:**
```
If any column is blank/null:
→ ERROR: Column 5 has no header. Provide header or remove column.
```

---

## STEP 2: SCHEMA INFERENCE & ENFORCEMENT

### 2.1 Schema Inference Strategy

**Two-pass approach:**

**Pass 1: Type Inference (Sample-Based)**
```python
INFERENCE_ALGORITHM:
1. Sample 1000 rows (or 20% of file, whichever larger)
2. For each column:
   a. Count data types present (int, float, string, date, bool, null)
   b. Check percentage-like patterns ("90%", "0.9")
   c. Check email patterns
   d. Check date patterns (ISO, US, EU formats)
   e. Compute min, max, mean (if numeric)
   
3. Assign primary type based on majority:
   - If 95%+ numeric → NUMERIC
   - If 90%+ date-parseable → DATE
   - If 80%+ email format → EMAIL
   - If contains % symbols → PERCENTAGE
   - Else → STRING

4. Flag ambiguous columns (no clear majority)
```

**Pass 2: Range & Constraint Inference**
```python
CONSTRAINT_INFERENCE:
For NUMERIC columns:
  - inferred_min = min(sample) - 10% buffer
  - inferred_max = max(sample) + 10% buffer
  - allow_null = (null_count > 0)

For DATE columns:
  - earliest_date = min(sample)
  - latest_date = max(sample)
  - date_format = detected format (ISO, US, etc.)

For PERCENTAGE columns:
  - require 0 <= value <= 100 (after normalization)
  - flag if any value > 1.5 (indicates non-normalized)

For EMAIL columns:
  - require @ symbol
  - require domain with TLD
  - lowercase normalization
```

### 2.2 Schema Lock & Validation

**Schema is locked before row parsing begins:**

```json
Example Locked Schema:
{
  "source_file": "quiz_data.xlsx",
  "sheet": "Graded Quiz 1",
  "schema_version": "1.0",
  "inferred_at": "2026-02-12T11:41:35Z",
  "total_columns": 8,
  "columns": [
    {
      "index": 0,
      "name": "student_email",
      "type": "EMAIL",
      "nullable": false,
      "constraints": {
        "pattern": "^[\\w.-]+@[\\w.-]+\\.[a-z]{2,}$"
      }
    },
    {
      "index": 1,
      "name": "quiz_score",
      "type": "PERCENTAGE",
      "nullable": true,
      "constraints": {
        "min": 0.0,
        "max": 100.0
      }
    },
    {
      "index": 2,
      "name": "submission_date",
      "type": "DATE",
      "nullable": false,
      "constraints": {
        "format": "YYYY-MM-DD",
        "min": "2025-01-01",
        "max": "2026-12-31"
      }
    }
  ]
}
```

**Schema saved to**: `data/schemas/{filename}_schema.json`

### 2.3 Schema Violation Handling

**Per-row validation against locked schema:**

```python
ROW_VALIDATION_RULES:
For each cell (row_idx, col_idx, value):
  
  1. NULL check:
     if value is NULL and not column.nullable:
       → REJECT row with "Required field missing: {column.name}"
  
  2. Type check:
     if column.type == NUMERIC:
       if not is_numeric(value):
         → REJECT row with "Non-numeric value in {column.name}: '{value}'"
     
     if column.type == EMAIL:
       if not matches_pattern(value, column.constraints.pattern):
         → REJECT row with "Invalid email format: '{value}'"
     
     if column.type == DATE:
       if not parse_date(value, column.constraints.format):
         → REJECT row with "Unparseable date: '{value}'"
  
  3. Range check (if applicable):
     if column.type == NUMERIC or PERCENTAGE:
       if value < column.constraints.min or value > column.constraints.max:
         → REJECT row with "{column.name} out of bounds: {value} (allowed: {min}-{max})"
  
  4. No implicit casting:
     "90" as string ≠ 90 as number
     Must explicitly coerce after type validation
```

**Rejected rows → Quarantine Table:**
```
quarantine_data/
  ├── quiz_data_rejected.csv
  └── quiz_data_errors.jsonl
```

Each quarantined row includes:
- Original row number
- Column that failed
- Failure reason
- Original value
- Expected type/range

---

## STEP 3: ROW-LEVEL PARSING SAFETY

### 3.1 Row Integrity Guards

**Pre-parse row validation:**

```python
ROW_INTEGRITY_CHECKS:
1. Column count consistency
   if row.column_count != schema.total_columns:
     → REJECT: "Row {idx} has {actual} columns, expected {expected}"

2. Student identifier presence (critical field)
   student_id_col = get_column_by_name("student_email")
   if is_null(row[student_id_col]):
     → REJECT: "Row {idx} missing student identifier"

3. Whitespace-only detection
   for each cell in row:
     if cell.strip() == "" and cell != "":
       → NORMALIZE: Convert to explicit NULL

4. Special value detection
   for each cell in row:
     if cell in ["N/A", "n/a", "NA", "#N/A", "null", "NULL", "None"]:
       → NORMALIZE: Convert to NULL
     if cell in ["#DIV/0!", "#VALUE!", "#REF!"]:
       → REJECT: "Row {idx} contains Excel error: {cell}"
```

### 3.2 Numeric Safety Guards

**For all numeric fields:**

```python
NUMERIC_GUARDS:
1. Negative value detection (where inappropriate)
   if column.name in ["attendance_percentage", "quiz_score", "login_count"]:
     if value < 0:
       → REJECT: "{column.name} cannot be negative: {value}"

2. Percentage range enforcement
   if column.type == PERCENTAGE:
     if value > 100.0:
       → REJECT: "Percentage > 100: {value}%"
     if value < 0.0:
       → REJECT: "Percentage < 0: {value}%"

3. Infinity/NaN detection
   if is_nan(value) or is_inf(value):
     → REJECT: "Invalid numeric value: {value}"

4. Scientific notation normalization
   "1.5e2" → 150.0 (explicit conversion with validation)

5. Locale-dependent number parsing
   "1,234.56" (US) vs "1.234,56" (EU)
   → Use schema.locale setting
   → Explicitly parse with locale rules
```

### 3.3 Timestamp Sanity Checks

**For all date/datetime fields:**

```python
TIMESTAMP_GUARDS:
1. Future date detection
   if value > datetime.now() + grace_period(7 days):
     → WARN: "Future timestamp detected: {value}"
     → Optional: REJECT if strict mode

2. Ancient date detection
   if value < datetime(2000, 1, 1):
     → REJECT: "Implausible date: {value}"

3. Timestamp ordering validation (when contextually required)
   if column.name == "submission_date":
     if value < course_start_date or value > course_end_date:
       → REJECT: "Submission outside course period: {value}"

4. Excel epoch bug detection
   if value == datetime(1900, 1, 1) or value == datetime(1904, 1, 1):
     → WARN: "Potential Excel epoch bug, verify manually"
```

### 3.4 Quarantine System

**All rejected rows stored with full context:**

```json
{
  "source_file": "quiz_data.xlsx",
  "sheet": "Graded Quiz 1",
  "row_number": 45,
  "quarantine_reason": "SCHEMA_VIOLATION",
  "failed_column": "quiz_score",
  "failure_message": "Non-numeric value in quiz_score: 'absent'",
  "original_row": {
    "student_email": "john@example.com",
    "quiz_score": "absent",
    "submission_date": "2025-02-10"
  },
  "quarantined_at": "2026-02-12T11:45:00Z"
}
```

**Quarantine reporting:**
- Summary stats (% rows quarantined)
- Top failure reasons
- Manual review queue

**No silent drops. Ever.**

---

## STEP 4: CROSS-FILE CONSISTENCY CHECKS

### 4.1 Student ID Alignment

**After parsing all files:**

```python
STUDENT_ID_CONSISTENCY:
1. Extract all unique student IDs from each file
   student_ids_quiz = set(quiz_df['student_email'])
   student_ids_attendance = set(attendance_df['student_email'])
   student_ids_engagement = set(engagement_df['student_email'])

2. Compute set differences
   orphan_quiz = student_ids_quiz - student_ids_attendance
   orphan_attendance = student_ids_attendance - student_ids_quiz

3. Report mismatches
   if orphan_quiz:
     → WARN: "{len(orphan_quiz)} students in quiz data but not attendance"
     → LOG: List of orphan IDs
   
   if orphan_attendance:
     → WARN: "{len(orphan_attendance)} students in attendance but not quiz"

4. Cross-reference with master roster (dim_students)
   unregistered = all_student_ids - dim_students.student_id
   if unregistered:
     → ERROR: "{len(unregistered)} student IDs not in master roster"
     → REJECT: Must reconcile before proceeding
```

### 4.2 Duplicate Student Detection

**Detect duplicates within and across files:**

```python
DUPLICATE_DETECTION:
1. Within-file duplicates
   duplicates = df[df.duplicated(subset=['student_email'], keep=False)]
   if len(duplicates) > 0:
     → ERROR: "File {filename} contains duplicate student records"
     → LOG: List duplicates with row numbers

2. Cross-file duplicate time periods
   For attendance_week1.xlsx and attendance_week2.xlsx:
     if week1_dates overlap week2_dates:
       → ERROR: "Overlapping time periods in attendance files"

3. Multiple records for same student-date
   For fact tables with (student_id, metric_date) as key:
     if df.duplicated(subset=['student_id', 'metric_date']).any():
       → ERROR: "Duplicate records for student-date combination"
       → STRATEGY: Take latest by data_snapshot_date OR reject for manual resolution
```

### 4.3 Time Range Validation

**Ensure temporal consistency:**

```python
TIME_RANGE_CHECKS:
1. Course period validation
   min_date = df['date'].min()
   max_date = df['date'].max()
   
   if min_date < COURSE_START or max_date > COURSE_END:
     → WARN: "Data outside course period: {min_date} to {max_date}"

2. Sequential file validation
   For weekly files (week1.xlsx, week2.xlsx, ...):
     week1_max = week1_df['date'].max()
     week2_min = week2_df['date'].min()
     
     if week2_min <= week1_max:
       → ERROR: "Week 2 data overlaps with Week 1"

3. Snapshot timestamp validation
   For snapshot files with timestamps in filename:
     filename_date = parse_date_from_filename("quiz_snapshot_2025-02-10.xlsx")
     data_max_date = df['submission_date'].max()
     
     if data_max_date > filename_date:
       → ERROR: "Data contains dates after snapshot date"
```

### 4.4 Aggregate Count Validation

**Cross-check totals:**

```python
AGGREGATE_VALIDATION:
1. Quiz count per student
   Expected: 4 quizzes per student (from syllabus)
   
   actual_counts = df.groupby('student_email')['quiz_name'].nunique()
   mismatches = actual_counts[actual_counts != 4]
   
   if len(mismatches) > 0:
     → WARN: "{len(mismatches)} students have ≠4 quizzes"
     → LOG: Which students, actual counts

2. Attendance session count
   Expected: 12 sessions per course
   
   actual_sessions = df.groupby('course_id')['session_date'].nunique()
   if any(actual_sessions != 12):
     → WARN: "Some courses have ≠12 attendance sessions"

3. Enrollment count validation
   total_enrolled = roster_df.shape[0]
   quiz_unique_students = quiz_df['student_email'].nunique()
   
   if quiz_unique_students > total_enrolled:
     → ERROR: "More students in quiz data than enrolled"
```

### 4.5 Mismatch Reporting

**All cross-file issues logged to:**

```
data/validation_reports/
  └── cross_file_consistency_report.json
```

**Report structure:**
```json
{
  "validation_timestamp": "2026-02-12T12:00:00Z",
  "files_analyzed": 10,
  "issues": [
    {
      "severity": "ERROR",
      "category": "STUDENT_ID_MISMATCH",
      "message": "35 students in quiz data not found in master roster",
      "affected_ids": ["student1@email.com", "student2@email.com", ...],
      "resolution_required": true
    },
    {
      "severity": "WARN",
      "category": "COUNT_MISMATCH",
      "message": "12 students have ≠4 quizzes",
      "details": {"student_a": 3, "student_b": 5, ...}
    }
  ]
}
```

**Proceed only if:**
- No ERROR-level issues
- All WARN-level issues acknowledged

---

## STEP 5: NORMALIZATION & STANDARDIZATION

### 5.1 Percentage Normalization

**Enforce 0-100 scale universally:**

```python
PERCENTAGE_NORMALIZATION:
Rule: All percentages stored as 0-100 (not 0-1)

Input formats:
  "90%"   → 90.0
  "90.5%" → 90.5
  "0.9"   → 90.0 (if detected as 0-1 scale)
  90      → 90.0
  0.9     → 90.0 (if column is PERCENTAGE type)

Detection heuristic:
  if column.type == PERCENTAGE:
    if all values <= 1.5:
      # Assume 0-1 scale
      value = value * 100
    strip "%" if present
    
Validation post-normalization:
  assert 0 <= value <= 100
  if not: REJECT
```

**No frontend conversion:**
- Backend stores: 85.5
- Frontend displays: "85.5%" ← simple append, no calculation

### 5.2 Date Format Standardization

**Single canonical format: ISO 8601**

```python
DATE_NORMALIZATION:
Input formats accepted:
  - "2025-02-10" (ISO)
  - "02/10/2025" (US)
  - "10/02/2025" (EU)
  - "10-Feb-2025"
  - Excel serial (44321)

Step 1: Parse with detected format
Step 2: Convert to Python datetime
Step 3: Store as ISO string: "2025-02-10"

Database storage:
  - SQLite DATE columns: ISO string
  - PostgreSQL: Native DATE type
  
API response:
  - Always ISO 8601: "2025-02-10T14:30:00Z"

Frontend:
  - Receives ISO
  - Formats per locale using i18n library
  - Never parses dates itself
```

### 5.3 Time Granularity Alignment

**Enforce consistent time granularity:**

```python
TIME_GRANULARITY_RULES:
1. Daily data (attendance, logins)
   - Store as DATE (no time component)
   - Aggregate multiple events per day

2. Weekly data (engagement summaries)
   - Store week_number (1-52) + year
   - Store week_start_date (always Monday)

3. Trimester data (academic periods)
   - Store trimester ("T1-2025", "T2-2025")
   - Store start_date and end_date

Normalization:
  If raw data has timestamps for daily data:
    → TRUNCATE to date
  
  If raw data has mixed granularity:
    → REJECT, require source correction
```

### 5.4 Unit Standardization

**Enforce consistent units:**

```python
UNIT_STANDARDS:
Time duration:
  - Always minutes
  - Input: seconds → divide by 60
  - Input: hours → multiply by 60
  - Storage: INTEGER (minutes)
  - API: Return minutes + unit label

File size:
  - Always bytes
  - Input: KB → multiply by 1024
  - Input: MB → multiply by 1024²
  - Storage: BIGINT (bytes)
  - API: Return bytes, frontend formats

Scores:
  - Always 0-100 scale
  - No conversion for display
```

**Unit detection:**
```python
If column.name contains "time" or "duration":
  if max(values) < 500:
    # Likely hours
    WARN: "Suspected hours, converting to minutes"
  elif max(values) > 100000:
    # Likely seconds
    WARN: "Suspected seconds, converting to minutes"
```

**Ambiguity = ERROR:**
- Cannot guess units
- Require explicit metadata or reject

### 5.5 No Frontend Transformations

**Strict contract:**

```
BACKEND outputs:
  - risk_score: 75.5 (float, 0-100)
  - attendance_percentage: 85.0 (float, 0-100)
  - time_spent: 120 (int, minutes)
  - submission_date: "2025-02-10" (ISO string)

FRONTEND receives:
  - Exactly as above
  - NO calculations allowed
  - Display only:
    * 75.5 → "75.5%"
    * 120 → "2 hours"
    * "2025-02-10" → "Feb 10, 2025"

Forbidden frontend logic:
  ❌ risk_score * 100  (assumes 0-1 scale)
  ❌ time_spent / 60   (assumes seconds)
  ❌ Date parsing      (assumes format)
```

---

## STEP 6: DATA QUALITY METRICS

### 6.1 Automated Quality Metrics

**Per-file metrics:**

```json
{
  "file": "quiz_data.xlsx",
  "validation_timestamp": "2026-02-12T12:00:00Z",
  "metrics": {
    "total_rows_scanned": 1500,
    "valid_rows": 1462,
    "quarantined_rows": 38,
    "valid_row_percentage": 97.47,
    
    "field_completeness": {
      "student_email": 100.0,
      "quiz_score": 95.3,
      "submission_date": 98.8
    },
    
    "schema_drift": {
      "new_columns": [],
      "missing_columns": [],
      "type_changes": []
    },
    
    "outliers": {
      "quiz_score": {
        "below_threshold": 3,
        "above_threshold": 0
      }
    },
    
    "duplicate_rows": 0,
    "null_percentage_by_column": {
      "student_email": 0.0,
      "quiz_score": 4.7,
      "submission_date": 1.2
    }
  }
}
```

### 6.2 Cross-File Variance Checks

**Detect anomalies across file versions:**

```python
VARIANCE_DETECTION:
Compare current file with historical baseline:

1. Row count variance
   expected_rows = historical_avg ± 20%
   if actual_rows outside range:
     → WARN: "Unusual row count: {actual} (expected ~{expected})"

2. Value distribution drift
   For numeric columns:
     current_mean = df['quiz_score'].mean()
     historical_mean = 75.5
     if abs(current_mean - historical_mean) > 10:
       → WARN: "Mean quiz score shifted: {current_mean} vs {historical_mean}"

3. Null rate drift
   current_null_rate = df['quiz_score'].isnull().mean()
   historical_null_rate = 0.05
   if current_null_rate > historical_null_rate * 2:
     → WARN: "Null rate increased: {current_null_rate*100}%"

4. Unique value counts
   For categorical columns:
     current_unique = df['program'].nunique()
     historical_unique = 2 (BS, MSc)
     if current_unique != historical_unique:
       → ERROR: "New program values detected, verify before proceeding"
```

### 6.3 Outlier Detection

**Statistical outlier flagging:**

```python
OUTLIER_DETECTION:
For numeric columns (quiz_score, attendance_percentage, etc.):

Method 1: IQR-based
  Q1 = percentile(25)
  Q3 = percentile(75)
  IQR = Q3 - Q1
  lower_bound = Q1 - 1.5 * IQR
  upper_bound = Q3 + 1.5 * IQR
  
  outliers = values < lower_bound OR values > upper_bound
  
Method 2: Domain-specific bounds
  For attendance_percentage:
    if value < 20 or value > 100:
      → FLAG as outlier
  
  For quiz_score:
    if value < 10 or value == 100:
      → FLAG (suspicious: too low or perfect score)

Outlier actions:
  - Log outlier count
  - Do NOT auto-remove
  - Flag for manual review
  - Include in data quality report
```

### 6.4 Quality Metrics Dashboard

**Expose metrics internally:**

```
Internal Endpoint:
GET /internal/data-quality/metrics

Response:
{
  "last_ingestion": "2026-02-12T12:00:00Z",
  "overall_quality_score": 96.5,
  
  "per_file_summary": [
    {
      "file": "quiz_data.xlsx",
      "valid_percentage": 97.5,
      "issues": 2,
      "last_validated": "2026-02-12T12:00:00Z"
    }
  ],
  
  "data_freshness": {
    "newest_data_date": "2026-02-11",
    "staleness_days": 1
  },
  
  "audit_trail": {
    "total_files_processed": 10,
    "total_rows_ingested": 125000,
    "total_rows_quarantined": 324,
    "quarantine_rate": 0.26
  }
}
```

**Quality score calculation:**
```python
quality_score = (
  0.4 * valid_rows_percentage +
  0.3 * (1 - null_rate) +
  0.2 * (1 - outlier_rate) +
  0.1 * cross_file_consistency_score
)
```

---

## STEP 7: SAFE OUTPUT CONTRACT

### 7.1 Canonical Parsed Dataset

**Immutable validated tables:**

```
data/canonical/
  ├── dim_students.parquet        # Validated student roster
  ├── dim_courses.parquet          # Validated course catalog
  ├── fact_academic.parquet        # Validated assessments
  ├── fact_engagement.parquet      # Validated engagement
  └── metadata.json                # Provenance + validation summary
```

**Immutability guarantee:**
- Once written, never modified
- New ingestion → new timestamped version
- Version history preserved

### 7.2 Provenance Metadata

**Every row includes:**

```python
CANONICAL_ROW_SCHEMA:
{
  # Business data
  "student_id": "john@example.com",
  "quiz_score": 85.5,
  "submission_date": "2025-02-10",
  
  # Provenance (mandatory)
  "source_file": "quiz_data.xlsx",
  "source_sheet": "Graded Quiz 1",
  "source_row_number": 47,
  "ingested_at": "2026-02-12T12:00:00Z",
  "validation_passed": true,
  "schema_version": "1.0"
}
```

**Metadata file:**
```json
{
  "dataset_name": "fact_academic",
  "created_at": "2026-02-12T12:00:00Z",
  "source_files": [
    {
      "filename": "quiz_data.xlsx",
      "rows_ingested": 1462,
      "rows_quarantined": 38,
      "sha256": "abc123..."
    }
  ],
  "schema_version": "1.0",
  "validation_summary": {
    "quality_score": 97.5,
    "issues": 2
  }
}
```

### 7.3 API Contract

**Frontend MUST use canonical API, never raw files:**

```
ALLOWED:
  GET /api/v1/canonical/students
  GET /api/v1/canonical/students/{id}/signals

FORBIDDEN:
  Direct access to data/raw/*.xlsx
  Direct access to data/canonical/*.parquet
```

**API guarantees:**
1. **Type safety**: All fields have declared types
2. **Range safety**: Numeric fields within documented bounds
3. **Null handling**: Nullable fields explicitly marked
4. **No silent errors**: 500 if data integrity compromised
5. **Provenance available**: Metadata endpoints for audit

### 7.4 Version Control

**Immutable snapshots:**

```
data/canonical/versioned/
  ├── v1_2026-02-10_12-00/
  │   ├── fact_academic.parquet
  │   └── metadata.json
  └── v2_2026-02-11_12-00/
      ├── fact_academic.parquet
      └── metadata.json

Current symlink → v2_2026-02-11_12-00/
```

**API always serves "current" version:**
- Automatic rollback if new version fails validation
- Historical versions queryable via `/api/v1/canonical/versions`

---

## STEP 8: FAILURE MODES & RECOVERY

### 8.1 Partial File Failure

**Scenario**: 20 out of 1500 rows fail validation

**Behavior:**
```
PARTIAL_FAILURE_STRATEGY:
1. Quarantine failed rows
2. Ingest valid rows to canonical table
3. Return status code: 206 Partial Success
4. Include error report in response:
   {
     "status": "PARTIAL_SUCCESS",
     "valid_rows": 1480,
     "quarantined_rows": 20,
     "quarantine_file": "data/quarantine/quiz_data_rejected.csv",
     "error_summary": "Top failures: Non-numeric quiz scores (15), Missing emails (5)"
   }

5. Notify admin via:
   - Email alert
   - Dashboard warning
   - Slack notification (if configured)

6. Require manual review before next ingestion
```

**NO silent partial success:**
- Every partial failure logged
- Manual acknowledgment required
- Quarantine review process mandatory

### 8.2 New Columns Appear

**Scenario**: File suddenly has "final_exam" column

**Behavior:**
```
NEW_COLUMN_DETECTION:
1. Schema comparison detects new column
2. HALT ingestion immediately
3. ERROR: "Schema drift detected: New column 'final_exam'"
4. Actions required:
   a. Update schema definition
   b. Define column type and constraints
   c. Decide: backfill historical data OR ignore for old records
   d. Re-run ingestion with updated schema

Automatic handling: FORBIDDEN
```

**Why halt?**
- New column may indicate data source change
- May require new analytics logic
- May affect downstream ML models
- Better safe than sorry

### 8.3 Columns Disappear

**Scenario**: "attendance_percentage" column missing from file

**Behavior:**
```
MISSING_COLUMN_DETECTION:
1. Schema comparison detects missing column
2. Check if column is REQUIRED or OPTIONAL
3. If REQUIRED:
   → ERROR: "Required column missing: attendance_percentage"
   → REJECT entire file
   → Notify admin immediately
4. If OPTIONAL:
   → WARN: "Optional column missing: attendance_percentage"
   → Continue with NULL values for that column
   → Log degraded data quality
```

**Required vs Optional:**
- Required: student_id, primary metrics
- Optional: supplementary fields, computed fields

### 8.4 Values Shift Units

**Scenario**: Time values suddenly 10x larger (hours → minutes)

**Detection:**
```
UNIT_SHIFT_DETECTION:
1. Compare value distributions to historical baseline
2. Detect: mean(current) / mean(historical) ≈ 60x
3. HALT ingestion
4. ERROR: "Suspected unit change in 'time_spent': Values 60x larger than baseline"
5. Require manual confirmation:
   - Are units changed?
   - Update schema with new unit
   - Apply conversion factor
6. Re-run ingestion

Automatic conversion: FORBIDDEN (too risky)
```

### 8.5 Late or Incomplete Data

**Scenario**: Weekly file uploaded 3 days late, missing last 2 days of data

**Behavior:**
```
LATE_DATA_HANDLING:
1. Detect late arrival via expected schedule
2. WARN: "File arrived 3 days late"
3. Check completeness:
   - Expected date range: 2026-02-03 to 2026-02-09
   - Actual date range: 2026-02-03 to 2026-02-07
4. PARTIAL_DATA flag set to TRUE
5. Store with metadata:
   {
     "is_complete": false,
     "missing_date_range": "2026-02-08 to 2026-02-09",
     "expected_arrival": "2026-02-10",
     "actual_arrival": "2026-02-13"
   }
6. Frontend shows: "Incomplete data" indicator
7. Admin notified: "Missing 2 days of data"

Automatic backfill: YES (when late data arrives)
  - Re-run ingestion
  - Merge with existing partial data
  - Mark as complete
```

### 8.6 Fail Loudly, Fail Safely

**Core Principles:**

1. **Loud Failures**
   - Every error logged to persistent storage
   - Admins notified immediately (email, Slack, dashboard)
   - Frontend shows "Data validation in progress" banner
   - No optimistic assumptions

2. **Safe Degradation**
   - Partial failures → Serve last known good data
   - Schema drift → Halt, don't guess
   - Missing data → Mark as incomplete, show warning
   - Never interpolate or fabricate data

3. **Manual Override Gates**
   - Critical failures require admin approval to proceed
   - Quarantined data requires review before re-ingestion
   - Schema changes require explicit version bump

4. **Audit Trail**
   - Every decision logged (automated and manual)
   - Rollback capability for last 10 versions
   - Immutable append-only logs

**Example Error Response:**
```json
{
  "status": "ERROR",
  "error_code": "SCHEMA_DRIFT",
  "message": "File validation failed: New column detected",
  "details": {
    "file": "quiz_data.xlsx",
    "expected_columns": 8,
    "actual_columns": 9,
    "new_columns": ["final_exam"],
    "action_required": "Update schema and re-upload"
  },
  "timestamp": "2026-02-12T12:00:00Z",
  "admin_contact": "data-team@company.com"
}
```

---

## GUARANTEES PROVIDED TO FRONTEND

### ✅ Absolute Guarantees

1. **Type Safety**
   - Every field has documented type
   - No unexpected types (guaranteed by validation)
   - Null-safety explicitly declared

2. **Range Safety**
   - Percentages: Always 0-100
   - Risk scores: Always 0-100, never -1
   - Dates: Within documented bounds
   - Counts: Always ≥0

3. **Completeness Indicators**
   - Missing data flagged explicitly
   - Partial datasets marked clearly
   - No silent nulls without reason

4. **Consistency**
   - Student IDs consistent across endpoints
   - Time periods non-overlapping
   - No duplicate records

5. **Provenance**
   - Every data point traceable to source
   - Timestamp of last update available
   - Quality score published

### ❌ Frontend Must NOT

1. **Parse or transform data**
   - No date parsing
   - No unit conversion
   - No scale transformation (0-1 to 0-100)

2. **Handle missing data**
   - Backend provides defaults or nulls
   - Frontend displays, not imputes

3. **Validate inputs**
   - Backend validates all writes
   - Frontend only provides UI feedback

4. **Access raw files**
   - Only canonical API allowed
   - No direct file system access

### 📊 SLA Commitments

- **Data freshness**: < 24 hours from source to API
- **Validation accuracy**: 100% (no false positives)
- **Uptime**: 99.9% for canonical API
- **Error notification**: < 5 minutes from detection

---

## SUMMARY: DEFENSE IN DEPTH

```
Layer 1: FILE VALIDATION
  ↓ (Reject corrupted, invalid files)

Layer 2: SCHEMA INFERENCE & LOCK
  ↓ (Establish type contracts)

Layer 3: ROW-LEVEL VALIDATION
  ↓ (Quarantine bad rows, never drop)

Layer 4: CROSS-FILE CONSISTENCY
  ↓ (Detect mismatches, reject conflicts)

Layer 5: NORMALIZATION
  ↓ (Standardize units, formats)

Layer 6: QUALITY METRICS
  ↓ (Measure and report quality)

Layer 7: CANONICAL OUTPUT
  ↓ (Immutable, auditable, versioned)

Layer 8: FAIL-SAFE MECHANISMS
  ↓ (Halt on ambiguity, notify loudly)

────────────────────────────────
FRONTEND: Receives 100% valid data
```

**Zero tolerance for silent errors.**  
**Every anomaly is caught, logged, and resolved before reaching production.**
