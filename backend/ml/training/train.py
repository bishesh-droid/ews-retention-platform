import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import xgboost as xgb
import joblib
import os
from backend.ml.features.feature_engineering import create_features
from backend.ml.training.evaluate import evaluate_model
from backend.ml.config import MODELS_DIR

def train_and_save_model(data_path, model_dir=MODELS_DIR, use_xgboost=True):
    """
    Train and save ML model for student retention prediction
    
    Args:
        data_path: Path to student data CSV
        model_dir: Directory to save models
        use_xgboost: If True, use XGBoost; if False, use Random Forest
    """
    print("Loading data...")
    df = pd.read_csv(data_path)
    
    # Convert all columns except 'id' to numeric
    for col in df.columns:
        if col != 'id':
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Create features
    print("Engineering features...")
    features_df = create_features(df)
    
    X = features_df.drop('nograd', axis=1)
    y = features_df['nograd']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Class distribution: {y.value_counts().to_dict()}")
    
    # Train primary model (XGBoost or Random Forest)
    if use_xgboost:
        print("\n=== Training XGBoost Model (Primary) ===")
        from imblearn.pipeline import Pipeline
        from imblearn.over_sampling import SMOTE
        
        xgb_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            eval_metric='auc',
            random_state=42,
            use_label_encoder=False
        )
        
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('smote', SMOTE(random_state=42)),
            ('classifier', xgb_model)
        ])
        
        print("Training XGBoost...")
        pipeline.fit(X_train, y_train)
        print("Training complete.")
        
        print("\n=== Evaluating XGBoost on test data ===")
        evaluate_model(pipeline, X_test, y_test)
        
        # Feature importance
        print("\n=== Top 10 Feature Importances ===")
        feature_importance = pipeline.named_steps['classifier'].feature_importances_
        feature_names = X.columns
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': feature_importance
        }).sort_values('importance', ascending=False)
        
        print(importance_df.head(10))
        
        # Save XGBoost model
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        model_path = os.path.join(model_dir, 'retention_model_xgboost.joblib')
        joblib.dump(pipeline, model_path)
        print(f"\nXGBoost model saved to {model_path}")
        
        # Save feature importance
        importance_path = os.path.join(model_dir, 'feature_importance.csv')
        importance_df.to_csv(importance_path, index=False)
        print(f"Feature importance saved to {importance_path}")
        
    else:
        print("\n=== Training Random Forest Model ===")
        from imblearn.pipeline import Pipeline
        from imblearn.over_sampling import SMOTE
        
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('smote', SMOTE(random_state=42)),
            ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        
        print("Training Random Forest...")
        pipeline.fit(X_train, y_train)
        print("Training complete.")
        
        print("\n=== Evaluating Random Forest on test data ===")
        evaluate_model(pipeline, X_test, y_test)
        
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        model_path = os.path.join(model_dir, 'retention_model.joblib')
        joblib.dump(pipeline, model_path)
        print(f"\nRandom Forest model saved to {model_path}")
    
    # Train Logistic Regression baseline for interpretability
    print("\n=== Training Logistic Regression Baseline ===")
    from imblearn.pipeline import Pipeline
    from imblearn.over_sampling import SMOTE
    
    lr_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42)),
        ('classifier', LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'))
    ])
    
    print("Training Logistic Regression...")
    lr_pipeline.fit(X_train, y_train)
    print("Training complete.")
    
    print("\n=== Evaluating Logistic Regression on test data ===")
    evaluate_model(lr_pipeline, X_test, y_test)
    
    # Save Logistic Regression baseline
    lr_path = os.path.join(model_dir, 'retention_model_logreg.joblib')
    joblib.dump(lr_pipeline, lr_path)
    print(f"\nLogistic Regression baseline saved to {lr_path}")
    
    # Print coefficients for interpretability
    print("\n=== Top 10 Logistic Regression Coefficients (Risk Factors) ===")
    coefficients = lr_pipeline.named_steps['classifier'].coef_[0]
    coef_df = pd.DataFrame({
        'feature': X.columns,
        'coefficient': coefficients
    }).sort_values('coefficient', key=abs, ascending=False)
    print(coef_df.head(10))


if __name__ == '__main__':
    from config import SAMPLE_DATA_PATH
    raw_data_path = SAMPLE_DATA_PATH
    
    # Check for alternative data paths
    if not os.path.exists(raw_data_path):
        print(f"Warning: Data file not found at {raw_data_path}")
        # Try local fallback
        raw_data_path = 'backend/data/simulated_data.csv'
    
    try:
        # Train XGBoost as primary model
        train_and_save_model(raw_data_path, use_xgboost=True)
    except FileNotFoundError:
        print(f"Error: Data file not found at {raw_data_path}")
    except Exception as e:
        print(f"An error occurred during training: {e}")
        import traceback
        traceback.print_exc()

