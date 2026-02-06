import pandas as pd
import numpy as np
import logging

# Configure logger
logger = logging.getLogger(__name__)

def create_features(df):
    features_df = df.copy()
    for year in range(1, 8):
        mpa_cols = [f'q{q}mpa{year}' for q in range(1, 5)]
        features_df[f'mpa_avg_{year}'] = df[mpa_cols].mean(axis=1)
        for metric in ['absrate', 'nsusp', 'mobility']:
            col = f'{metric}{year}'
            features_df[f'{metric}_avg_{year}'] = df[col]
    for metric in ['mpa_avg', 'absrate_avg', 'nsusp_avg', 'mobility_avg']:
        years = [5, 6, 7]
        values = features_df[[f'{metric}_{y}' for y in years]].values
        x = np.array(years)
        valid_mask = ~np.isnan(values)
        slopes = []
        for i in range(values.shape[0]):
            if np.sum(valid_mask[i]) > 1:
                y_i = values[i][valid_mask[i]]
                x_i = x[valid_mask[i]]
                A = np.vstack([x_i, np.ones(len(x_i))]).T
                m, c = np.linalg.lstsq(A, y_i, rcond=None)[0]
                slopes.append(m)
            else:
                slopes.append(0)
        features_df[f'{metric}_trend_3yr'] = slopes
    feature_cols = [col for col in features_df.columns if 'avg' in col or 'trend' in col]
    target_col = 'nograd'
    final_df = features_df[feature_cols + [target_col]].copy()
    
    # Enhanced imputation with validation
    for col in feature_cols:
        if final_df[col].isnull().any():
            median_val = final_df[col].median()
            
            # Check if median is NaN (entire column is null)
            if np.isnan(median_val):
                logger.warning(f"Column '{col}' is entirely null. Filling with 0.0")
                fill_value = 0.0
            else:
                fill_value = median_val
            
            null_count = final_df[col].isnull().sum()
            final_df.loc[:, col] = final_df[col].fillna(fill_value)
            logger.info(f"Imputed {null_count} NaN values in '{col}' with {fill_value:.3f}")
    
    # Final validation: ensure no NaN or Inf remain
    if final_df[feature_cols].isnull().any().any():
        logger.error("NaN values still present after imputation!")
        remaining_nulls = final_df[feature_cols].isnull().sum()
        logger.error(f"Remaining nulls: {remaining_nulls[remaining_nulls > 0]}")
    
    if np.isinf(final_df[feature_cols].values).any():
        logger.error("Inf values detected in features!")
        final_df.replace([np.inf, -np.inf], 0.0, inplace=True)
        logger.warning("Replaced Inf values with 0.0")
    
    return final_df
if __name__ == '__main__':
    try:
        # Use centralized data path
        from config import SAMPLE_DATA_PATH
        raw_data_path = SAMPLE_DATA_PATH
        print(f"Loading data from {raw_data_path}")
        df = pd.read_csv(raw_data_path)
        for col in df.columns:
            if col != 'id':
                df[col] = pd.to_numeric(df[col], errors='coerce')
        features = create_features(df)
        print("Feature engineering complete.")
        print("Shape of the feature DataFrame:", features.shape)
        print("Features created:", features.columns.tolist())
        print("\nFirst 5 rows of features:")
        print(features.head())
    except FileNotFoundError:
        print("Error: The data file was not found.")
        print("Please ensure 'frontend/public/data/student_data_test.csv' exists.")
    except Exception as e:
        print(f"An error occurred: {e}")
