"""
Type coercion utilities for normalizing raw data
"""
import pandas as pd
from datetime import datetime
from typing import Optional


class TypeCoercer:
    """Coerce raw data types to canonical format"""
    
    @staticmethod
    def coerce_email(value) -> Optional[str]:
        """Normalize email to lowercase, strip whitespace"""
        if pd.isna(value):
            return None
        return str(value).strip().lower()
    
    @staticmethod
    def coerce_percentage(value) -> Optional[float]:
        """
        Convert percentage to 0-100 float, handle various formats
        Handles: "90%", "90 %", "0.9", 90.0
        """
        if pd.isna(value):
            return None
            
        try:
            # Handle "90%", "90 %", etc.
            str_val = str(value).strip().replace('%', '').strip()
            float_val = float(str_val)
            
            # If 0-1 range, convert to 0-100
            if 0 <= float_val <= 1:
                return float_val * 100
            elif 0 <= float_val <= 100:
                return float_val
            else:
                # Out of bounds → NULL
                return None
                
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def coerce_date(value) -> Optional[datetime]:
        """Parse various date formats"""
        if pd.isna(value):
            return None
            
        try:
            return pd.to_datetime(value)
        except:
            return None
    
    @staticmethod
    def coerce_int(value) -> Optional[int]:
        """Convert to integer, handle NULL"""
        if pd.isna(value):
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def coerce_float(value) -> Optional[float]:
        """Convert to float, handle NULL"""
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def coerce_bool(value) -> bool:
        """Convert to boolean"""
        if pd.isna(value):
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', 'yes', '1', 't', 'y']
        return bool(value)
