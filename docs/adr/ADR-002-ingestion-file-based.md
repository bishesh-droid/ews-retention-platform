# ADR-002: Engagement Data Ingestion — File-Based vs API-Based LMS Integration

## Status

**Accepted** — Implemented in v1.1.0

## Context

Brightspace (D2L) is the Learning Management System used by BITS Pilani Digital Campus. The team evaluated integration options:

**Option A: API Integration**
- Brightspace offers REST APIs (Valence)
- Requires API credentials, OAuth setup, rate limiting management
- Real-time data available
- Data structure is normalized and consistent

**Option B: File-Based (Excel Exports)**
- Brightspace exports available as .xlsx downloads
- No API credentials required
- Data arrives weekly (batch)
- Schema varies between exports (different column names, sheet names include timestamps)
- Historical Brightspace instances at BITS have inconsistent API access policies

Current state:
- API access was requested but not approved for production use by time of V1 deadline
- Excel exports are consistently available and operations team comfortable with manual export/download workflow
- Export schema has changed twice in past trimester (column renames, sheet name changes)

## Decision

Build a **robust file-based ingestion pipeline** for V1 with the following architectural components:

1. **Header-based column lookup**: No positional assumptions (columns discovered by name variants)
2. **Dynamic sheet discovery**: Handles timestamped sheet names ("Learner Usage 2026-02-10" vs "Learner Usage main dump")
3. **CourseContentRegistry fallback**: Stores best-known content_required per course as fallback for sparse exports (E-8)
4. **Accumulative counters**: Multiple weekly exports merge into single enrollment record (max for counters, latest for dates)
5. **Program detection via Org_Defined_Id**: 2025EB*=BS, 2025EM*=MSc (not email substring)

Define the **path to API integration** as follows:
1. V1 (current): File-based with weekly manual export workflow
2. V1.5: Brightspace Data Hub integration if API access approved (automated download)
3. V2: Direct Valence API integration for near-real-time updates (daily or better)

## Consequences

### Positive

- **Works with current infrastructure**: No dependency on external API approvals
- **Schema drift tolerance**: Header-based lookup detects and adapts to column renames
- **Audit trail**: Each file is processed and logged with row counts and errors
- **Offline capable**: System can be developed and tested without live LMS connectivity
- **Operations control**: Human review of exports before ingestion provides quality gate

### Negative

- **Latency**: Data is 1-7 days stale depending on export frequency
- **Manual steps**: Operations team must download and place files (or use API upload endpoint)
- **File management**: Accumulation of weekly files in `backend/data/` requires cleanup
- **No real-time alerts**: Cannot detect same-day engagement drops

### Mitigations

- `POST /api/v1/admin/ingest` endpoint allows file upload via API (reduces manual file placement)
- IngestionRun audit log tracks every file processed with statistics
- Automatic cleanup of old exports can be added as background job
- Ghost student detection (E-4) works even with stale data by identifying zero historical engagement
