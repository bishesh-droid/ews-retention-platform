"""
EWS Retention Platform - Data Catalog Generator
Systematically analyzes all raw data files and produces a comprehensive catalog
"""
import pandas as pd
import os
from datetime import datetime
import json
import numpy as np

DATA_DIR = "data/raw"

def json_serializer(obj):
    """Convert non-JSON-serializable objects to JSON-compatible formats"""
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Type {type(obj)} not serializable")

def analyze_file(filepath, filename):
    """Analyze a single Excel file and extract detailed schema information"""
    catalog = {
        "filename": filename,
        "filepath": filepath,
        "sheets": [],
        "analyzed_at": datetime.now().isoformat()
    }
    
    try:
        xl = pd.ExcelFile(filepath)
        
        for sheet_name in xl.sheet_names:
            # Try different header rows (0, 1, 2) to find the best one
            best_df = None
            best_header_row = 0
            
            for header_row in [0, 1, 2]:
                try:
                    df = pd.read_excel(filepath, sheet_name=sheet_name, header=header_row)
                    # Check for excessive "Unnamed" columns which indicates wrong header
                    unnamed_count = sum(1 for col in df.columns if 'Unnamed' in str(col))
                    if unnamed_count < len(df.columns) * 0.3:  # Less than 30% unnamed
                        best_df = df
                        best_header_row = header_row
                        break
                except:
                    continue
            
            if best_df is None:
                best_df = pd.read_excel(filepath, sheet_name=sheet_name, header=0)
                best_header_row = 0
            
            # Identify student identifier columns
            student_id_cols = []
            for col in best_df.columns:
                col_lower = str(col).lower()
                if any(x in col_lower for x in ['username', 'email', 'student', 'user id', 
                                                  'org defined id', 'learner', 'roll']):
                    student_id_cols.append(col)
            
            # Identify time-related columns
            time_cols = []
            for col in best_df.columns:
                col_lower = str(col).lower()
                if any(x in col_lower for x in ['date', 'week', 'time', 'day', 'month', 
                                                  'trimester', 'semester', 'timestamp']):
                    time_cols.append(col)
            
            # Analyze column data types and sample values
            columns_info = []
            for col in best_df.columns:
                col_info = {
                    "name": col,
                    "dtype": str(best_df[col].dtype),
                    "null_count": int(best_df[col].isnull().sum()),
                    "null_percentage": round(float(best_df[col].isnull().sum()) / len(best_df) * 100, 2),
                    "unique_count": int(best_df[col].nunique()),
                    "sample_values": [str(x) for x in best_df[col].dropna().head(3).tolist()]
                }
                columns_info.append(col_info)
            
            sheet_info = {
                "sheet_name": sheet_name,
                "header_row": best_header_row,
                "shape": best_df.shape,
                "row_count": best_df.shape[0],
                "column_count": best_df.shape[1],
                "student_identifier_columns": student_id_cols,
                "time_columns": time_cols,
                "columns": columns_info
            }
            
            catalog["sheets"].append(sheet_info)
        
        return catalog
    
    except Exception as e:
        catalog["error"] = str(e)
        return catalog

def main():
    """Generate comprehensive data catalog for all files"""
    files = [
        "B.S and M.Sc Live Summary Data C-1, Trimester 1.xlsx",
        "B.S and M.Sc Summary Data Trimester 2.xlsx",
        "Engagement_Analysis.xlsx",
        "Graded Quiz 1 Status 9 feb.xlsx",
        "Graded quiz 1 10 feb 4_51 pm.xlsx",
        "Learner usage week 3.xlsx",
        "Week 1-2 Student Engagement Analysis.xlsx",
        "_Trimester-1 2025 Attendance Quiz-Assignment-Exam 5Jan2025.xlsx",
        "graded quiz 1 10 feb 11_15 AM.xlsx",
        "graded quiz 1 10 feb complete.xlsx"
    ]
    
    full_catalog = {
        "generated_at": datetime.now().isoformat(),
        "total_files": len(files),
        "files": []
    }
    
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        print(f"Analyzing: {filename}")
        
        if os.path.exists(filepath):
            catalog = analyze_file(filepath, filename)
            full_catalog["files"].append(catalog)
            
            # Print summary
            print(f"  ✓ Sheets: {len(catalog.get('sheets', []))}")
            for sheet in catalog.get('sheets', []):
                print(f"    - {sheet['sheet_name']}: {sheet['row_count']} rows, {sheet['column_count']} cols")
                if sheet['student_identifier_columns']:
                    print(f"      Student IDs: {', '.join(sheet['student_identifier_columns'][:3])}")
        else:
            print(f"  ✗ File not found")
            full_catalog["files"].append({
                "filename": filename,
                "error": "File not found"
            })
        
        print()
    
    # Save catalog as JSON
    output_path = "data/data_catalog.json"
    with open(output_path, 'w') as f:
        json.dump(full_catalog, f, indent=2, default=json_serializer)
    
    print(f"✓ Catalog saved to: {output_path}")
    
    # Also create a summary
    print("\n" + "="*80)
    print("DATA CATALOG SUMMARY")
    print("="*80)
    
    total_sheets = sum(len(f.get('sheets', [])) for f in full_catalog['files'])
    total_rows = sum(sheet['row_count'] for f in full_catalog['files'] 
                     for sheet in f.get('sheets', []))
    
    print(f"Total Files: {len(full_catalog['files'])}")
    print(f"Total Sheets: {total_sheets}")
    print(f"Total Data Rows: {total_rows:,}")
    print()
    
    # Identify all unique student identifier patterns
    all_student_id_cols = set()
    for file_cat in full_catalog['files']:
        for sheet in file_cat.get('sheets', []):
            all_student_id_cols.update(sheet.get('student_identifier_columns', []))
    
    print("Student Identifier Columns Found:")
    for col in sorted(all_student_id_cols):
        print(f"  - {col}")
    
    return full_catalog

if __name__ == "__main__":
    catalog = main()
