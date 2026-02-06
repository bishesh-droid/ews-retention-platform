# Testing Guide

## Setup

### 1. Create Virtual Environment (Recommended)

```bash
cd /home/duffer/Music/ews-retention-platform
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- `xgboost` - Primary ML model
- `imbalanced-learn` - SMOTE for class imbalance
- `schedule` - Automated job scheduling
- `fastapi` - Backend API framework

### 3. Initialize Database

The database will be initialized automatically on first run, but you can manually trigger it:

```bash
cd backend
python3 -m backend.database
```

## Testing Backend APIs

### Start the Backend Server

```bash
cd /home/duffer/Music/ews-retention-platform
uvicorn backend.main:app --reload --port 8000
```

### Test Event Ingestion

```bash
# Test LMS event
curl -X POST "http://localhost:8000/events/lms" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "S001",
    "event_source": "lms",
    "event_type": "assignment_submit",
    "event_data": {"assignment_id": "A101", "score": 85, "max_score": 100}
  }'

# Test Zoom event
curl -X POST "http://localhost:8000/events/zoom" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "S001",
    "event_source": "zoom",
    "event_type": "class_attend",
    "event_data": {"duration_minutes": 45, "join_delay_minutes": 2}
  }'
```

### Test Feature Engineering

```bash
# Compute features for a student
curl -X POST "http://localhost:8000/features/compute?student_id=S001"

# Get engineered features
curl "http://localhost:8000/features/S001"

# Get signal summary for academic performance
curl "http://localhost:8000/features/signal-summary/academic"
```

### Test Predictions with Signal Breakdown

```bash
# Get prediction with intervention recommendation
curl "http://localhost:8000/predictions/S001?include_decisions=true"

# Get batch predictions
curl "http://localhost:8000/predictions/batch?include_decisions=false"
```

### Test Decision Engine

```bash
# Get intervention recommendation
curl "http://localhost:8000/decisions/S001"

# Get pending interventions by priority
curl "http://localhost:8000/decisions/pending/list?priority=high"
```

### Test Feedback Loop

```bash
# Record student response
curl -X POST "http://localhost:8000/feedback/response" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "S001",
    "intervention_id": 1,
    "responded": true,
    "response_time_hours": 12.5,
    "behavioral_change_detected": true,
    "engagement_change_7days": 0.20,
    "attendance_change_7days": 0.15
  }'

# Get effectiveness metrics
curl "http://localhost:8000/feedback/effectiveness?days_lookback=30"
```

## Testing ML Model

### Train XGBoost Model

```bash
# Ensure you're in the virtual environment
cd /home/duffer/Music/ews-retention-platform

# Train model
python3 -m models.train_model
```

Expected output:
- Training metrics (accuracy, precision, recall, F1)
- Feature importance rankings
- Model saved to `models/saved_models/retention_model_xgboost.joblib`

### Test Prediction Script

```bash
# Run standalone prediction test
python3 -m models.predict
```

Expected output:
- Risk score (0-1)
- Signal breakdown (5 categories)
- Top risk factors with contributions

## Testing Scheduler

### Run Scheduler (Manual Test)

```bash
# Start scheduler service
python3 -m backend.services.scheduler
```

Scheduled jobs:
- Daily at 02:00: Feature computation
- Daily at 03:00: Prediction generation
- Weekly (Sunday) at 04:00: Model retraining

To test immediately:
```python
from backend.services.scheduler import compute_features_for_all_students
compute_features_for_all_students()
```

## Testing Frontend

### Start Frontend Development Server

```bash
cd frontend
npm install  # First time only
npm start
```

### Test New Components

1. **SignalBreakdown Component**
   - Navigate to student profile page
   - Verify 5 signal bars are displayed
   - Check color coding (green/yellow/red)

2. **InterventionCard Component**
   - View student with risk > 30%
   - Verify intervention recommendation shown
   - Check priority badge display

3. **SignalRadarChart Component**
   - Open student details
   - Verify radar chart renders with 5 axes
   - Check tooltip on hover

## End-to-End Testing

### Complete Data Flow Test

1. **Ingest Events**
   ```bash
   # Send multiple events for student S001
   curl -X POST "http://localhost:8000/events/lms" -H "Content-Type: application/json" -d '{"student_id": "S001", "event_source": "lms", "event_type": "login", "event_data": {}}'
   ```

2. **Compute Features**
   ```bash
   curl -X POST "http://localhost:8000/features/compute?student_id=S001"
   ```

3. **Generate Prediction**
   ```bash
   curl "http://localhost:8000/predictions/S001?include_decisions=true"
   ```

4. **Execute Intervention**
   ```bash
   # Based on recommendation from step 3
   curl -X POST "http://localhost:8000/decisions/execute" -H "Content-Type: application/json" -d '{...}'
   ```

5. **Record Response**
   ```bash
   curl -X POST "http://localhost:8000/feedback/response" -H "Content-Type: application/json" -d '{...}'
   ```

6. **View in Frontend**
   - Open http://localhost:3000
   - Navigate to student S001
   - Verify signal breakdown displayed
   - Check intervention recommendation

## Common Issues

### XGBoost Import Error
```bash
# Install in virtual environment
source venv/bin/activate
pip install xgboost
```

### Database Schema Changes
```bash
# Delete and reinitialize database
rm backend/ews_platform.db
python3 -m backend.main
```

### Frontend Component Not Displaying
```bash
# Clear cache and restart
cd frontend
rm -rf node_modules/.cache
npm start
```

## Performance Testing

### Batch Prediction Speed

```bash
time curl "http://localhost:8000/predictions/batch"
```

Expected: < 5 seconds for 100 students

### Feature Computation Speed

```bash
# Time single student
time curl -X POST "http://localhost:8000/features/compute?student_id=S001"
```

Expected: < 1 second per student

## Success Criteria

✅ Backend APIs return 200 status codes
✅ Signal breakdown contains 5 categories (academic, engagement, consistency, intent, responsiveness)
✅ Intervention recommendations match risk thresholds
✅ Feedback loop tracks behavioral changes
✅ Frontend components render without errors
✅ Scheduler jobs execute successfully
✅ ML model training completes without errors
