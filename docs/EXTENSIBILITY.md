# EWS Platform - Extensibility Guide

## Adding New Data Sources

### 1. Create a New Plugin

All data source plugins implement the `DataSourcePlugin` interface:

```python
# backend/ingestion/plugins/my_new_source.py

from backend.ingestion.plugins import DataSourcePlugin
import pandas as pd


class MyNewSourcePlugin(DataSourcePlugin):
    
    def extract(self) -> pd.DataFrame:
        """Extract data from source (file, API, database)"""
        # Your extraction logic
        return df
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform to canonical schema"""
        # Normalize columns, coerce types, validate
        return transformed_df
    
    def load(self, df: pd.DataFrame, db: Session):
        """Load into canonical tables"""
        # Insert into dim_students, fact_engagement, etc.
        pass
```

### 2. Register Plugin in Pipeline

```python
# backend/ingestion/pipeline.py

from backend.ingestion.plugins.my_new_source import MyNewSourcePlugin

# In run() method:
plugin = MyNewSourcePlugin()
plugin_data = plugin.extract()
transformed = plugin.transform(plugin_data)
plugin.load(transformed, self.db)
```

## Extending the Canonical Schema

### Adding New Fact Table

1. **Define Model** in `backend/database.py`:

```python
class FactNewMetric(Base):
    __tablename__ = "fact_new_metric"
    
    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(255), ForeignKey("dim_students.student_id"))
    # ... other fields
    data_snapshot_date = Column(Date, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

2. **Run Migration**:

```bash
python3 -c "from backend.database import init_db; init_db()"
```

3. **Create Signal Computer**:

```python
# backend/features/new_metric_signal.py

class NewMetricSignal(SignalComputer):
    def compute(self, db_session, student_id, trimester):
        # Query FactNewMetric
        # Compute sub-metrics
        # Return signal value 0-100
        pass
```

4. **Add to Risk Scorer**:

```python
# backend/features/risk_scorer.py

self.signal_weights = {
    'academic_performance': 0.35,
    'engagement': 0.30,
    'new_metric': 0.15,  # NEW
    ...
}
```

## Creating Custom Signals

### Example: Peer Interaction Signal

```python
# backend/features/peer_interaction_signal.py

from backend.features.signal_computer import SignalComputer

class PeerInteractionSignal(SignalComputer):
    
    def __init__(self):
        weights = {
            'discussion_replies': 0.4,
            'group_project_participation': 0.3,
            'peer_review_completion': 0.3
        }
        super().__init__(weights)
    
    def compute(self, db_session, student_id, trimester):
        # Query relevant fact tables
        # Compute weighted score
        # Return 0-100 value
        pass
```

## Data Source Examples

### Excel Files

```python
# Already implemented in backend/ingestion/pipeline.py
df = pd.read_excel(file_path, sheet_name=sheet_name)
```

### CSV Files

```python
df = pd.read_csv(file_path)
```

### API Integration

```python
import requests

response = requests.get('https://api.lms.com/students')
df = pd.DataFrame(response.json())
```

### Database Connection

```python
from sqlalchemy import create_engine

engine = create_engine('postgresql://user:pass@host/db')
df = pd.read_sql('SELECT * FROM students', engine)
```

## Best Practices

1. **Always Use Type Coercion**: Use `TypeCoercer` for all raw data
2. **Validate Inputs**: Use `StudentValidator` and `MetricValidator`
3. **Log Errors**: Use `IngestionErrorLogger` for data quality issues
4. **Track Lineage**: Insert records into `DataLineage` table
5. **Preserve Timestamps**: Always use `data_snapshot_date` for temporal tracking
6. **NULL vs 0**: Use `NULL` for missing data, `0` for confirmed zero values
7. **Bounds Checking**: Risk scores must be 0-100, use `max(0, min(100, score))`
