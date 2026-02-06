"""
Feature Engineering Service for EWS Retention Platform.

This module contains all feature engineering functions that derive metrics
from the raw CSV columns. Every calculation is traceable back to specific
CSV columns in simulated_data.csv.

CSV Column Reference:
- absrate1-7: Absence rates for years 1-7
- nsusp1-7: Number of suspensions for years 1-7
- mobility1-7: School mobility/transfer rates for years 1-7
- q1mpa1-q4mpa7: Quarterly MPA scores (28 scores total across 7 years)
- nograd: Binary outcome (0=graduated, 1=did not graduate)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


class FeatureEngineer:
    """
    Handles all feature engineering calculations from CSV columns.
    All methods are pure functions with clear CSV column dependencies.
    """
    
    @staticmethod
    def normalize_to_scale(value: float, min_val: float, max_val: float, 
                          target_min: float = 0, target_max: float = 100) -> float:
        """
        Min-max normalize a value to target scale.
        
        Args:
            value: Value to normalize
            min_val: Minimum value in original range
            max_val: Maximum value in original range
            target_min: Target minimum (default 0)
            target_max: Target maximum (default 100)
            
        Returns:
            Normalized value clamped to [target_min, target_max]
        """
        if max_val == min_val:
            # Avoid division by zero
            return (target_min + target_max) / 2
        
        normalized = ((value - min_val) / (max_val - min_val)) * (target_max - target_min) + target_min
        return max(target_min, min(target_max, normalized))
    
    @staticmethod
    def calculate_attendance_score(student_data: Dict) -> float:
        """
        Calculate attendance score from absence rates.
        
        CSV Columns Used: absrate1, absrate2, ..., absrate7
        
        Logic:
        1. Collect all non-null absence rates across 7 years
        2. Calculate mean absence rate
        3. Convert to attendance score (higher absence = lower attendance)
        4. Normalize to 0-100 scale
        
        Returns:
            Attendance score [0-100], where 100 = perfect attendance
        """
        absence_rates = []
        for year in range(1, 8):
            absrate = student_data.get(f'absrate{year}')
            if absrate is not None:
                absence_rates.append(float(absrate))
        
        if not absence_rates:
            # No data available, return neutral score
            return 50.0
        
        # Calculate mean absence rate
        mean_absence = np.mean(absence_rates)
        
        # Find global min/max for normalization (from data observation)
        # CSV shows range from approx -22 to +37
        global_min = -25.0
        global_max = 40.0
        
        # Normalize absence rate
        normalized_absence = FeatureEngineer.normalize_to_scale(
            mean_absence, global_min, global_max, 0, 100
        )
        
        # Invert: high absence = low attendance score
        attendance_score = 100 - normalized_absence
        
        return round(attendance_score, 2)
    
    @staticmethod
    def calculate_academic_score(student_data: Dict) -> float:
        """
        Calculate academic performance score from quarterly MPA scores.
        
        CSV Columns Used: q1mpa1-q4mpa7 (28 quarterly scores across 7 years)
        
        Logic:
        1. Collect all non-null quarterly MPA scores
        2. Calculate mean MPA
        3. Normalize to 0-100 scale (assuming MPA is on 0-5 scale)
        
        Returns:
            Academic score [0-100], where 100 = perfect grades
        """
        mpa_scores = []
        for year in range(1, 8):
            for quarter in range(1, 5):
                mpa = student_data.get(f'q{quarter}mpa{year}')
                if mpa is not None:
                    mpa_scores.append(float(mpa))
        
        if not mpa_scores:
            return 50.0
        
        # Calculate mean MPA
        mean_mpa = np.mean(mpa_scores)
        
        # MPA typically ranges from -1 to 6 (observed from CSV)
        global_min = -1.0
        global_max = 6.0
        
        # Normalize to 0-100
        academic_score = FeatureEngineer.normalize_to_scale(
            mean_mpa, global_min, global_max, 0, 100
        )
        
        return round(academic_score, 2)
    
    @staticmethod
    def calculate_behavioral_score(student_data: Dict) -> float:
        """
        Calculate behavioral score from suspension counts.
        
        CSV Columns Used: nsusp1, nsusp2, ..., nsusp7
        
        Logic:
        1. Collect all non-null suspension counts
        2. Calculate mean suspensions
        3. Invert and normalize (fewer suspensions = higher behavioral score)
        
        Returns:
            Behavioral score [0-100], where 100 = no behavioral issues
        """
        suspension_counts = []
        for year in range(1, 8):
            nsusp = student_data.get(f'nsusp{year}')
            if nsusp is not None:
                suspension_counts.append(float(nsusp))
        
        if not suspension_counts:
            return 50.0
        
        # Calculate mean suspensions
        mean_suspensions = np.mean(suspension_counts)
        
        # Suspension counts range from approx -1 to 1.5 (observed from CSV)
        global_min = -1.0
        global_max = 1.5
        
        # Normalize suspensions
        normalized_suspensions = FeatureEngineer.normalize_to_scale(
            mean_suspensions, global_min, global_max, 0, 100
        )
        
        # Invert: high suspensions = low behavioral score
        behavioral_score = 100 - normalized_suspensions
        
        return round(behavioral_score, 2)
    
    @staticmethod
    def calculate_stability_score(student_data: Dict) -> float:
        """
        Calculate stability score from mobility rates.
        
        CSV Columns Used: mobility1, mobility2, ..., mobility7
        
        Logic:
        1. Collect all non-null mobility rates
        2. Calculate mean absolute mobility (direction doesn't matter)
        3. Invert and normalize (less mobility = higher stability)
        
        Returns:
            Stability score [0-100], where 100 = very stable enrollment
        """
        mobility_rates = []
        for year in range(1, 8):
            mobility = student_data.get(f'mobility{year}')
            if mobility is not None:
                mobility_rates.append(abs(float(mobility)))
        
        if not mobility_rates:
            return 50.0
        
        # Calculate mean absolute mobility
        mean_mobility = np.mean(mobility_rates)
        
        # Mobility ranges from 0 to ~3.5 (observed from CSV)
        global_min = 0.0
        global_max = 4.0
        
        # Normalize mobility
        normalized_mobility = FeatureEngineer.normalize_to_scale(
            mean_mobility, global_min, global_max, 0, 100
        )
        
        # Invert: high mobility = low stability
        stability_score = 100 - normalized_mobility
        
        return round(stability_score, 2)
    
    @staticmethod
    def calculate_trend(student_data: Dict) -> str:
        """
        Calculate academic trend by comparing recent vs. early performance.
        
        CSV Columns Used: q1mpa1-q4mpa2 (early), q1mpa6-q4mpa7 (recent)
        
        Logic:
        Compare average MPA from years 1-2 vs years 6-7
        
        Returns:
            "improving", "declining", or "stable"
        """
        # Early years (1-2)
        early_scores = []
        for year in [1, 2]:
            for quarter in range(1, 5):
                mpa = student_data.get(f'q{quarter}mpa{year}')
                if mpa is not None:
                    early_scores.append(float(mpa))
        
        # Recent years (6-7)
        recent_scores = []
        for year in [6, 7]:
            for quarter in range(1, 5):
                mpa = student_data.get(f'q{quarter}mpa{year}')
                if mpa is not None:
                    recent_scores.append(float(mpa))
        
        if not early_scores or not recent_scores:
            return "stable"
        
        early_avg = np.mean(early_scores)
        recent_avg = np.mean(recent_scores)
        
        # Threshold for meaningful change (0.5 on MPA scale)
        if recent_avg > early_avg + 0.5:
            return "improving"
        elif recent_avg < early_avg - 0.5:
            return "declining"
        else:
            return "stable"
    
    @staticmethod
    def get_year_by_year_data(student_data: Dict) -> List[Dict]:
        """
        Extract year-by-year breakdown of student data.
        
        Returns:
            List of yearly data dictionaries with all metrics
        """
        yearly_data = []
        
        for year in range(1, 8):
            year_dict = {
                "year": year,
                "absence_rate": student_data.get(f'absrate{year}'),
                "suspensions": student_data.get(f'nsusp{year}'),
                "mobility": student_data.get(f'mobility{year}'),
                "quarterly_scores": [
                    student_data.get(f'q1mpa{year}'),
                    student_data.get(f'q2mpa{year}'),
                    student_data.get(f'q3mpa{year}'),
                    student_data.get(f'q4mpa{year}')
                ]
            }
            yearly_data.append(year_dict)
        
        return yearly_data
    
    @staticmethod
    def calculate_all_features(student_data: Dict) -> Dict:
        """
        Calculate all features for a student in one pass.
        
        Args:
            student_data: Dictionary containing all CSV columns for one student
            
        Returns:
            Dictionary with all calculated features
        """
        return {
            "attendance_score": FeatureEngineer.calculate_attendance_score(student_data),
            "academic_score": FeatureEngineer.calculate_academic_score(student_data),
            "behavioral_score": FeatureEngineer.calculate_behavioral_score(student_data),
            "stability_score": FeatureEngineer.calculate_stability_score(student_data),
            "trend": FeatureEngineer.calculate_trend(student_data),
            "year_by_year": FeatureEngineer.get_year_by_year_data(student_data),
            "graduated": student_data.get('nograd', 0) == 0
        }
