# EWS Retention Platform - Setup and Deployment

## Quick Start

### 1. Environment Setup

```bash
# Navigate to project directory
cd /home/duffer/Music/ews-retention-platform

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Initialization

The database will auto-initialize on first run. To manually initialize:

```bash
python3 -c "from backend.database import init_db; init_db()"
```

### 3. Train ML Model

```bash
# Train XGBoost model (recommended)
python3 -m models.train_model
```

This will create:
- `models/saved_models/retention_model_xgboost.joblib` (Primary model)
- `models/saved_models/retention_model_logreg.joblib` (Baseline)
- `models/saved_models/feature_importance.csv` (Feature rankings)

### 4. Start Backend Server

```bash
# Development mode with auto-reload
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

### 5. Start Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm start
```

Frontend will be available at: `http://localhost:3000`

### 6. Start Scheduler (Optional)

```bash
# In a separate terminal
source venv/bin/activate
python3 -m backend.services.scheduler
```

Scheduled jobs:
- Feature computation: Daily at 02:00
- Predictions: Daily at 03:00
- Model retraining: Weekly (Sunday) at 04:00

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                            │
│  LMS  │  Zoom  │  Website  │  Email/WhatsApp  │  Marketing  │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              Event Ingestion APIs                            │
│         POST /events/{lms|zoom|website|...}                  │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Raw Events DB                               │
│        (student_id, event_source, event_type, data)         │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│           Feature Engineering Service                        │
│    Computes 5 Signal Categories:                            │
│    • Academic Performance                                    │
│    • Engagement                                              │
│    • Consistency                                             │
│    • Intent                                                  │
│    • Responsiveness                                          │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│             Engineered Features DB                           │
│         (18 features organized by signal category)          │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                XGBoost ML Model                              │
│          (Trained on historical data)                        │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              Predictions DB                                  │
│   • Overall risk score (0-1)                                 │
│   • Signal breakdown scores (5 categories)                   │
│   • Top risk factors                                         │
│   • Model version                                            │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              Decision Engine                                 │
│   Risk Thresholds:                                           │
│   • <30%: No action                                          │
│   • 30-60%: Gentle reminder (email)                          │
│   • 60-80%: Mentor outreach (faculty)                        │
│   • >80%: Urgent intervention (sales + WhatsApp)             │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│            Interventions DB                                  │
│   • Triggered interventions                                  │
│   • Channels used                                            │
│   • Assigned team                                            │
│   • Effectiveness score                                      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│          Student Responses DB                                │
│   • Response tracking                                        │
│   • Behavioral changes                                       │
│   • Retention outcome                                        │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼ (Feedback Loop)
┌─────────────────────────────────────────────────────────────┐
│  Weekly Model Retraining (incorporates new data)            │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Event Ingestion
- `POST /events/lms` - LMS activities
- `POST /events/zoom` - Zoom attendance
- `POST /events/website` - Website activity
- `POST /events/communication` - Email/WhatsApp
- `POST /events/marketing` - Campaign data
- `GET /events/{student_id}` - Get student events

### Features
- `GET /features/{student_id}` - Get engineered features
- `POST /features/compute` - Compute features (single/batch)
- `GET /features/signal-summary/{category}` - Signal statistics

### Predictions
- `GET /predictions/{student_id}` - Get prediction with signals
- `GET /predictions/batch` - Batch predictions

### Decisions
- `GET /decisions/{student_id}` - Get intervention recommendation
- `POST /decisions/execute` - Execute intervention
- `GET /decisions/pending/list` - Get pending interventions

### Feedback
- `POST /feedback/response` - Record student response
- `GET /feedback/effectiveness` - Get effectiveness metrics
- `GET /feedback/{student_id}/history` - Get feedback history

## Frontend Components

### New Components Created
1. **SignalBreakdown.jsx** - Bar chart visualization of 5 signals
2. **InterventionCard.jsx** - Displays intervention recommendations
3. **SignalRadarChart.jsx** - Radar chart for signal analysis

### Updated Pages
- **Dashboard** - Shows signal summary statistics
- **Student Profile** - Displays signal breakdown and recommendations

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=sqlite:///./backend/ews_platform.db

# ML Model
MODEL_PATH=models/saved_models/retention_model_xgboost.joblib

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Scheduler
ENABLE_SCHEDULER=true
FEATURE_COMPUTATION_TIME=02:00
PREDICTION_GENERATION_TIME=03:00
MODEL_RETRAINING_DAY=sunday
MODEL_RETRAINING_TIME=04:00
```

## Deployment

### Production Deployment

1. **Backend (FastAPI)**
   ```bash
   # Install production server
   pip install gunicorn
   
   # Run with gunicorn
   gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

2. **Frontend (React)**
   ```bash
   cd frontend
   npm run build
   # Serve build folder with nginx or similar
   ```

3. **Scheduler (Background Process)**
   ```bash
   # Use systemd service or supervisor
   # Example systemd service file:
   [Unit]
   Description=EWS Scheduler
   After=network.target
   
   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/path/to/ews-retention-platform
   ExecStart=/path/to/venv/bin/python -m backend.services.scheduler
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

### Docker Deployment (Optional)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - ./backend:/app/backend
    environment:
      - DATABASE_URL=sqlite:///./backend/ews_platform.db

  scheduler:
    build: .
    command: python -m backend.services.scheduler
    volumes:
      - ./models:/app/models
      - ./backend:/app/backend

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

## Monitoring

### Logs

- Backend logs: Check uvicorn/gunicorn output
- Scheduler logs: Check `scheduler.log` (configure in scheduler.py)
- ML model metrics: Saved in `models/saved_models/training_metrics.json`

### Metrics to Monitor

1. **API Performance**
   - Response times for /predictions endpoint
   - Batch prediction throughput

2. **ML Model**
   - Prediction accuracy
   - Signal score distributions
   - Feature importance changes

3. **Interventions**
   - Effectiveness rates by threshold category
   - Response rates
   - Behavioral change rates

4. **Scheduler**
   - Job completion times
   - Failed job counts

## Troubleshooting

See [TESTING.md](file:///home/duffer/Music/ews-retention-platform/TESTING.md) for detailed troubleshooting guide.

## Support

For issues or questions, refer to:
- System Architecture: [system_architecture.md](file:///home/duffer/.gemini/antigravity/brain/87ef57aa-ea1c-41f1-8fa9-5fb81287c62d/system_architecture.md)
- Implementation Walkthrough: [walkthrough.md](file:///home/duffer/.gemini/antigravity/brain/87ef57aa-ea1c-41f1-8fa9-5fb81287c62d/walkthrough.md)
- Testing Guide: [TESTING.md](file:///home/duffer/Music/ews-retention-platform/TESTING.md)
